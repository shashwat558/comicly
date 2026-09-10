from collections.abc import Awaitable, Callable
from typing import Any

from app.agents import artist as artist_mod
from app.agents import director as director_mod
from app.agents import memory as memory_mod
from app.agents import reader as reader_mod
from app.agents.state import AgentState

ProgressCb = Callable[[str, int], Awaitable[None] | None]


async def _emit(cb: ProgressCb | None, stage: str, pct: int) -> None:
    if cb is None:
        return
    res = cb(stage, pct)
    if isinstance(res, Awaitable):
        await res


async def run_pipeline(state: AgentState, on_progress: ProgressCb | None = None) -> AgentState:
    import asyncio

    from app.core.config import get_settings

    if get_settings().mock_generation:
        from app.graph.mock_pipeline import run_mock_pipeline

        return await run_mock_pipeline(state, on_progress=on_progress)

    # order matters, each step feeds the next
    await _emit(on_progress, "reading", 10)
    # llm calls are sync, keep them off the event loop
    state = await asyncio.to_thread(reader_mod.reader_node, dict(state))
    await _emit(on_progress, "directing", 40)
    state = await asyncio.to_thread(director_mod.director_node, dict(state))
    await _emit(on_progress, "rendering", 65)
    state = await artist_mod.artist_node(dict(state))
    await _emit(on_progress, "saving", 85)
    state = await asyncio.to_thread(memory_mod.memory_node, dict(state))
    await _emit(on_progress, "done", 100)
    return state


def build_initial_state(
    *,
    book_id: str,
    page_no: int,
    page_text: str,
    style_lock: dict[str, Any],
    characters: list[dict[str, Any]],
    story: dict[str, Any],
    relationships: dict[str, Any],
    prev_frame_urls: list[str] | None = None,
    char_ref_urls: list[str] | None = None,
    job_id: str = "",
) -> AgentState:
    return {
        "book_id": book_id,
        "page_no": page_no,
        "page_text": page_text,
        "style_lock": style_lock,
        "characters": characters,
        "story": story,
        "relationships": relationships,
        "prev_frame_urls": prev_frame_urls or [],
        "char_ref_urls": char_ref_urls or [],
        "job_id": job_id,
    }
