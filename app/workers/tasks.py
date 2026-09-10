import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.redis import publish_progress
from app.graph.pipeline import build_initial_state, run_pipeline
from app.models.book import Book, Page
from app.models.frame import Frame
from app.services.memory_service import get_book_context, save_snapshot, upsert_characters

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


async def generate_page(ctx: dict, book_id: str, page_no: int, job_id: str, style_override: dict | None = None, force: bool = False) -> dict:
    bid = uuid.UUID(book_id)
    async with SessionLocal() as db:

        existing = (await db.execute(
            select(Frame).where(Frame.book_id == bid, Frame.page_no == page_no)
        )).scalar_one_or_none()
        # already rendered and not forced -> hand back the cached frame
        if existing is not None and existing.status == "done" and not force:
            await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": existing.image_url})
            return {"status": "done", "image_url": existing.image_url, "cached": True}

        page = (await db.execute(
            select(Page).where(Page.book_id == bid, Page.page_no == page_no)
        )).scalar_one_or_none()
        if page is None:
            raise ValueError(f"Page {page_no} not found for book {book_id}")

        book_ctx = await get_book_context(db, bid)
        book: Book = book_ctx["book"]
        # style freezes on page 1, every later page reuses it
        style = dict(book.style_lock) if book.style_lock else dict(DEFAULT_STYLE)
        if page_no == 1 and style_override:
            style.update(style_override)

        if page_no == 1 and not book.style_lock:
            book.style_lock = style
            await db.flush()

        characters = [
            {"name": c.name, "appearance": c.appearance, "traits": list(c.traits or []),
             "visual_anchors": list(c.visual_anchors or []),
             "reference_image_url": c.reference_image_url}
            for c in book_ctx["characters"]
        ]
        prev_urls: list[str] = []
        if book_ctx["last_frame"] and book_ctx["last_frame"].image_url:
            prev_urls = [book_ctx["last_frame"].image_url]
        char_refs = [c["reference_image_url"] for c in characters if c.get("reference_image_url")][:2]

        state = build_initial_state(
            book_id=book_id, page_no=page_no, page_text=page.text, style_lock=style,
            characters=characters, story=book_ctx["story"],
            relationships=book_ctx["relationships"],
            prev_frame_urls=prev_urls, char_ref_urls=char_refs, job_id=job_id,
        )
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
        if existing is None:
            db.add(frame)
        await db.flush()


        await upsert_characters(db, bid, result.get("updated_characters", []), page_no)
        await save_snapshot(db, bid, page_no, result.get("updated_story", {}), result.get("updated_relationships", {}), book_ctx["version"])
        await db.commit()
        await publish_progress(job_id, {"job_id": job_id, "book_id": book_id, "page_no": page_no, "status": "done", "progress": 100, "image_url": frame.image_url})
        return {"status": "done", "image_url": frame.image_url, "seed": frame.seed}


from urllib.parse import urlparse

from arq.connections import RedisSettings as ARQRedisSettings

from app.core.config import get_settings


def _arq_redis_settings() -> ARQRedisSettings:
    u = urlparse(get_settings().redis_url)
    return ARQRedisSettings(host=u.hostname or "localhost", port=u.port or 6379)


class WorkerSettings:
    functions = [generate_page]
    redis_settings = _arq_redis_settings()

    @staticmethod
    async def on_startup(ctx):
        pass
