import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.redis import publish_progress
from app.graph.pipeline import build_initial_state, run_pipeline
from app.models.book import Book, Page
from app.models.frame import Frame
from app.services.memory_service import (
    bump_pro_calls,
    get_book_context,
    save_snapshot,
    save_style_bible,
    upsert_casting_sheets,
    upsert_characters,
)

DEFAULT_STYLE = {
    "art_style": "neo-noir cinematic",
    "lighting": "high-contrast, rim and neon",
    "palette": ["#0b0f1a", "#ff2d95", "#00e6a8"],
    "realism": "stylized",
    "seed_anchor": 123456,
    "rendering_mode": "single cinematic frame, no text, no speech bubbles",
}


async def _progress(job_id: str, book_id: str, page_no: int):
    async def cb(stage: str, pct: int):
        await publish_progress(job_id, {
            "job_id": job_id, "book_id": book_id, "page_no": page_no,
            "status": stage, "progress": pct,
        })
    return cb


def _effective_quality(requested: str, pro_used: int) -> str:
    from app.core.config import get_settings

    q = (requested or "auto").lower()
    if q not in ("draft", "pro", "auto"):
        q = "auto"
    cap = get_settings().max_pro_calls_per_book or 0
    if cap and pro_used >= cap and q == "pro":
        return "auto"
    return q


async def generate_page(
    ctx: dict,
    book_id: str,
    page_no: int,
    job_id: str,
    style_override: dict | None = None,
    force: bool = False,
    quality: str = "auto",
    panels: int = 1,
) -> dict:
    bid = uuid.UUID(book_id)
    async with SessionLocal() as db:

        existing = (await db.execute(
            select(Frame).where(Frame.book_id == bid, Frame.page_no == page_no)
        )).scalar_one_or_none()


        if existing is not None and existing.status == "done" and not force:
            cached_q = (existing.quality or "draft").lower()
            want = (quality or "auto").lower()
            if not (want == "pro" and cached_q != "pro"):
                await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": existing.image_url})
                return {"status": "done", "image_url": existing.image_url, "cached": True}

        page = (await db.execute(
            select(Page).where(Page.book_id == bid, Page.page_no == page_no)
        )).scalar_one_or_none()
        if page is None:
            raise ValueError(f"Page {page_no} not found for book {book_id}")

        book_ctx = await get_book_context(db, bid)
        book: Book = book_ctx["book"]

        style = dict(book.style_lock) if book.style_lock else dict(DEFAULT_STYLE)
        if page_no == 1 and style_override:
            style.update(style_override)

        if page_no == 1 and not book.style_lock:
            book.style_lock = style
            await db.flush()

        bible = dict(book_ctx.get("style_bible", {}) or {})
        style_refs = list(book_ctx.get("style_ref_urls", []) or [])
        pro_used_before = int(book_ctx.get("pro_calls_used", 0) or 0)
        quality_eff = _effective_quality(quality, pro_used_before)
        try:
            panels_eff = max(1, min(4, int(panels or 1)))
        except (TypeError, ValueError):
            panels_eff = 1

        characters = [
            {"name": c.name, "appearance": c.appearance, "traits": list(c.traits or []),
             "visual_anchors": list(c.visual_anchors or []),
             "reference_image_url": c.reference_image_url,
             "sheet_image_url": getattr(c, "sheet_image_url", None),
             "sheet_image_key": getattr(c, "sheet_image_key", None),
             "sheet_version": int(getattr(c, "sheet_version", 0) or 0)}
            for c in book_ctx["characters"]
        ]
        prev_urls: list[str] = [
            f.image_url for f in (book_ctx.get("prev_frames", []) or [])
            if f.image_url
        ][:3]
        seen_refs: list[str] = []
        for c in characters:
            for key in ("sheet_image_url", "reference_image_url"):
                u = c.get(key)
                if u and u not in seen_refs:
                    seen_refs.append(u)
        char_refs = seen_refs[:5]

        state = build_initial_state(
            book_id=book_id, page_no=page_no, page_text=page.text, style_lock=style,
            characters=characters, story=book_ctx["story"],
            relationships=book_ctx["relationships"],
            prev_frame_urls=prev_urls, char_ref_urls=char_refs,
            style_bible=bible, style_ref_urls=style_refs,
            quality=quality_eff, panels=panels_eff, job_id=job_id,
        )

        state["pro_calls_used"] = pro_used_before
        cb = await _progress(job_id, book_id, page_no)
        try:
            result = await run_pipeline(state, on_progress=cb)
        except Exception as e:
            await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "error", "progress": 0, "error": str(e)[:1000]})
            raise


        frame = existing or Frame(book_id=bid, page_no=page_no)
        frame.reader_out = result.get("reader_out")
        frame.director_out = result.get("director_out")
        frame.image_key = result.get("image_key")
        frame.image_url = result.get("image_url")
        frame.seed = result.get("seed")
        frame.status = "done"
        frame.error = None
        frame.quality = str(result.get("quality_used", quality_eff) or quality_eff)[:16]
        try:
            frame.drift_score = float(result.get("drift_score")) if result.get("drift_score") is not None else None
        except (TypeError, ValueError):
            frame.drift_score = None
        frame.critic_out = result.get("critic_out")
        frame.panel_layout = result.get("panel_layout")
        frame.retry_count = int(result.get("retry_count", 0) or 0)
        frame.flagged = bool(result.get("critic_flagged", False))
        if existing is None:
            db.add(frame)
        await db.flush()


        if page_no == 1 and result.get("style_bible"):
            new_bible = dict(result["style_bible"])
            refs = list(result.get("style_ref_urls", []) or style_refs)
            if refs:
                new_bible["ref_urls"] = refs
            await save_style_bible(db, bid, new_bible, result.get("style_lock", style))

        await upsert_casting_sheets(db, bid, result.get("casting_out", []), page_no)
        await upsert_characters(db, bid, result.get("updated_characters", []), page_no)
        await save_snapshot(db, bid, page_no, result.get("updated_story", {}), result.get("updated_relationships", {}), book_ctx["version"])
        pro_used_after = int(result.get("pro_calls_used", pro_used_before) or pro_used_before)
        if pro_used_after > pro_used_before:
            await bump_pro_calls(db, bid, pro_used_after - pro_used_before)
        await db.commit()
        await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": frame.image_url})
        return {"status": "done", "image_url": frame.image_url, "seed": frame.seed}


async def enhance_page(ctx: dict, book_id: str, page_no: int, job_id: str) -> dict:
    """One-click Pro upscale of an existing frame (the frontend Enhance button)."""
    from app.agents import artist as artist_mod
    from app.services import image_store

    bid = uuid.UUID(book_id)
    async with SessionLocal() as db:
        frame = (await db.execute(
            select(Frame).where(Frame.book_id == bid, Frame.page_no == page_no)
        )).scalar_one_or_none()
        if frame is None or not frame.image_url:
            raise ValueError(f"Frame {page_no} not generated yet for book {book_id}")
        if (frame.quality or "").lower() == "pro":
            await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": frame.image_url})
            return {"status": "done", "image_url": frame.image_url, "cached": True}

        book_ctx = await get_book_context(db, bid)
        book: Book = book_ctx["book"]
        from app.core.config import get_settings

        cap = get_settings().max_pro_calls_per_book or 0
        pro_used = int(book_ctx.get("pro_calls_used", 0) or 0)
        if cap and pro_used >= cap:
            raise ValueError("Per-book Pro spend cap reached")

        cb = await _progress(job_id, book_id, page_no)
        await cb("hero", 20)

        try:
            current_bytes = await image_store.download_bytes(frame.image_url)
        except Exception as e:
            raise ValueError(f"Could not fetch current frame for enhance: {e}")

        characters = [
            {"name": c.name, "appearance": c.appearance, "traits": list(c.traits or []),
             "visual_anchors": list(c.visual_anchors or []),
             "reference_image_url": c.reference_image_url,
             "sheet_image_url": getattr(c, "sheet_image_url", None)}
            for c in book_ctx["characters"]
        ]
        prev_urls = [f.image_url for f in (book_ctx.get("prev_frames", []) or []) if f.image_url][:3]
        state = build_initial_state(
            book_id=book_id, page_no=page_no, page_text="",
            style_lock=dict(book.style_lock) if book.style_lock else dict(DEFAULT_STYLE),
            characters=characters, story=book_ctx["story"],
            relationships=book_ctx["relationships"],
            prev_frame_urls=prev_urls,
            char_ref_urls=[c.get("sheet_image_url") or c.get("reference_image_url") for c in characters if c.get("sheet_image_url") or c.get("reference_image_url")][:5],
            style_bible=dict(book_ctx.get("style_bible", {}) or {}),
            style_ref_urls=list(book_ctx.get("style_ref_urls", []) or []),
            quality="pro", panels=int((frame.panel_layout or {}).get("panel_count", 1) or 1),
            job_id=job_id,
        )
        state["reader_out"] = frame.reader_out or {}
        state["director_out"] = frame.director_out or {}
        state["draft_image_bytes"] = current_bytes
        state["critic_out"] = frame.critic_out or {}
        state["pro_calls_used"] = pro_used
        await cb("hero", 60)
        result = await artist_mod.refine_node(dict(state))
        await cb("saving", 90)

        frame.image_key = result.get("image_key")
        frame.image_url = result.get("image_url")
        frame.quality = "pro"
        frame.status = "done"
        frame.error = None
        await db.flush()
        await bump_pro_calls(db, bid, 1)
        await db.commit()
        await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": frame.image_url})
        return {"status": "done", "image_url": frame.image_url}


from urllib.parse import urlparse

from arq.connections import RedisSettings as ARQRedisSettings

from app.core.config import get_settings


def _arq_redis_settings() -> ARQRedisSettings:
    u = urlparse(get_settings().redis_url)
    return ARQRedisSettings(host=u.hostname or "localhost", port=u.port or 6379)


class WorkerSettings:
    functions = [generate_page, enhance_page]
    redis_settings = _arq_redis_settings()

    @staticmethod
    async def on_startup(ctx):
        pass
