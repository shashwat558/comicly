"""Hybrid artist: Flash drafts in seconds, Pro hero/final with the full ref stack."""

from __future__ import annotations

from app.agents.images import (
    build_ref_url_stack,
    fetch_ref_images,
    generate_image_bytes,
    pil_from_bytes,
)
from app.agents.prompts import build_artist_prompt
from app.agents.state import AgentState
from app.core.config import get_settings
from app.services import image_store


async def _render(
    state: AgentState, *, model: str, fix_notes: str = "", is_hero: bool = False,
    include_draft: bool = False,
) -> bytes:
    settings = get_settings()
    prompt = build_artist_prompt(
        director=state.get("director_out", {}),
        style=state.get("style_lock", {}),
        characters=state.get("characters", []),
        fix_notes=fix_notes,
        is_hero=is_hero,
    )
    ref_urls = build_ref_url_stack(state, include_draft_as_ref=include_draft)
    ref_images = await fetch_ref_images(ref_urls, cap=settings.max_ref_images)
    extra = []
    if include_draft and state.get("draft_image_bytes"):
        try:
            extra.append(pil_from_bytes(bytes(state["draft_image_bytes"])))
        except Exception:
            pass
    return await generate_image_bytes(model, prompt, ref_images, extra)


async def draft_node(state: AgentState) -> AgentState:
    """Cheap Flash draft. Always runs: instant feedback + critic input."""
    settings = get_settings()
    fix_notes = str(state.get("fix_notes", "") or "")
    attempt = int(state.get("critic_attempt", 0) or 0)
    image_bytes = await _render(
        state, model=settings.gemini_draft_image_model,
        fix_notes=fix_notes if attempt > 0 else "", is_hero=False,
    )
    key, url = await image_store.upload_draft(
        book_id=str(state["book_id"]), page_no=int(state.get("page_no", 1)),
        attempt=attempt, data=image_bytes,
    )
    return {
        **state, "draft_image_bytes": image_bytes,
        "draft_image_key": key, "draft_image_url": url,
    }


async def refine_node(state: AgentState) -> AgentState:
    """Pro hero / targeted fix. Draft quality re-renders on Flash; else Pro.

    Called when (a) quality == pro (always upscale), or (b) the critic failed
    and retries remain (targeted fix with critic notes).
    """
    settings = get_settings()
    quality = str(state.get("quality", "auto") or "auto")
    critic = state.get("critic_out", {}) or {}
    fix_notes = str(critic.get("fix_notes", "") or state.get("fix_notes", "") or "")
    pro_used = int(state.get("pro_calls_used", 0) or 0)
    cap = settings.max_pro_calls_per_book or 10**9

    use_pro = quality != "draft" and pro_used < cap
    model = settings.gemini_hero_image_model if use_pro else settings.gemini_draft_image_model
    image_bytes = await _render(state, model=model, fix_notes=fix_notes, is_hero=use_pro, include_draft=True)
    if use_pro:
        pro_used += 1
    key, url = await image_store.upload_frame(
        book_id=str(state["book_id"]), page_no=int(state.get("page_no", 1)), data=image_bytes
    )
    return {
        **state, "image_bytes": image_bytes, "image_key": key, "image_url": url,
        "hero_image_key": key, "hero_image_url": url,
        "quality_used": "pro" if use_pro else "draft-fix",
        "pro_calls_used": pro_used, "fix_notes": fix_notes,
    }


async def finalize_draft_as_final(state: AgentState) -> AgentState:
    """Promote an accepted draft to final without a Pro call (auto/draft path)."""
    if state.get("image_bytes"):
        return state
    draft = state.get("draft_image_bytes")
    if draft is None:
        raise RuntimeError("No draft image to finalize")

    key, url = await image_store.upload_frame(
        book_id=str(state["book_id"]), page_no=int(state.get("page_no", 1)), data=bytes(draft)
    )
    return {
        **state, "image_bytes": bytes(draft), "image_key": key, "image_url": url,
        "quality_used": "draft",
    }
