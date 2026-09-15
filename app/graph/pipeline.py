"""LangGraph pipeline: reader -> director -> bible -> casting -> draft -> critic -> hero/final -> memory.

Stages stream over SSE as: reading, directing, casting, drafting, critiquing,
hero, saving, done. Critic failures retry the draft (Flash) up to
CRITIC_MAX_RETRIES, then accept-and-flag; Pro hero fires for quality=pro
(always) or auto+still-failing (one targeted fix).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import lru_cache
from typing import Any, Literal

from langgraph.graph import END, START, StateGraph

from app.agents import artist as artist_mod
from app.agents import bible as bible_mod
from app.agents import casting as casting_mod
from app.agents import critic as critic_mod
from app.agents import director as director_mod
from app.agents import memory as memory_mod
from app.agents import reader as reader_mod
from app.agents.state import AgentState

ProgressCb = Callable[[str, int], Awaitable[None] | None]

RouteLabel = Literal["retry", "hero", "final"]


async def _emit(cb: ProgressCb | None, stage: str, pct: int) -> None:
    if cb is None:
        return
    res = cb(stage, pct)
    if isinstance(res, Awaitable):
        await res


def _quality(state: AgentState) -> str:
    return str(state.get("quality", "auto") or "auto")


def _max_retries() -> int:
    from app.core.config import get_settings

    try:
        return int(get_settings().critic_max_retries)
    except Exception:
        return 2


def decide_route(state: AgentState) -> RouteLabel:
    """Pure routing after the critic. Tested without any API calls."""
    quality = _quality(state)
    passed = bool(state.get("critic_passed", False))
    attempt = int(state.get("critic_attempt", 0) or 0)
    if not passed and attempt < _max_retries():
        return "retry"
    if quality == "pro":
        return "hero"
    if not passed:

        return "hero" if quality == "auto" else "final"
    return "final"




async def _reader(state: AgentState) -> AgentState:
    return await asyncio.to_thread(reader_mod.reader_node, dict(state))


async def _director(state: AgentState) -> AgentState:
    return await asyncio.to_thread(director_mod.director_node, dict(state))


async def _memory(state: AgentState) -> AgentState:
    return await asyncio.to_thread(memory_mod.memory_node, dict(state))


async def _prepare_retry(state: AgentState) -> AgentState:
    return {**state, "critic_attempt": int(state.get("critic_attempt", 0) or 0) + 1}


async def _finalize(state: AgentState) -> AgentState:
    return await artist_mod.finalize_draft_as_final(dict(state))


def get_checkpointer():
    """Postgres saver when available, else in-memory.

    Crashed jobs still resume mid-book via persisted frames + memory snapshots
    (see workers/tasks.py); the checkpointer additionally resumes inside a page
    when langgraph-checkpoint-postgres is installed.
    """
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # type: ignore

        from app.core.config import get_settings

        url = get_settings().database_url
        if url.startswith("postgresql"):

            sync_url = url.replace("+asyncpg", "")
            return AsyncPostgresSaver.from_conn_string(sync_url)
    except Exception:
        pass
    try:
        from langgraph.checkpoint.memory import MemorySaver

        return MemorySaver()
    except Exception:
        return None


@lru_cache(maxsize=1)
def _compiled_graph():
    builder = StateGraph(AgentState)
    builder.add_node("reader", _reader)
    builder.add_node("director", _director)
    builder.add_node("bible", bible_mod.bible_node)
    builder.add_node("casting", casting_mod.casting_node)
    builder.add_node("draft", artist_mod.draft_node)
    builder.add_node("critic", critic_mod.critic_node)
    builder.add_node("prepare_retry", _prepare_retry)
    builder.add_node("refine", artist_mod.refine_node)
    builder.add_node("finalize", _finalize)
    builder.add_node("memory", _memory)

    builder.add_edge(START, "reader")
    builder.add_edge("reader", "director")
    builder.add_edge("director", "bible")
    builder.add_edge("bible", "casting")
    builder.add_edge("casting", "draft")
    builder.add_edge("draft", "critic")

    def _route(state: AgentState) -> str:
        return decide_route(state)

    builder.add_conditional_edges(
        "critic",
        _route,
        {"retry": "prepare_retry", "hero": "refine", "final": "finalize"},
    )
    builder.add_edge("prepare_retry", "draft")
    builder.add_edge("refine", "memory")
    builder.add_edge("finalize", "memory")
    builder.add_edge("memory", END)

    checkpointer = get_checkpointer()
    if checkpointer is not None:
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


def build_graph():
    """Return the compiled LangGraph pipeline (checkpointer attached)."""
    return _compiled_graph()


async def run_pipeline(state: AgentState, on_progress: ProgressCb | None = None) -> AgentState:
    from app.core.config import get_settings

    if get_settings().mock_generation:
        from app.graph.mock_pipeline import run_mock_pipeline

        return await run_mock_pipeline(state, on_progress=on_progress)

    graph = _compiled_graph()
    job_id = str(state.get("job_id", "") or f"{state.get('book_id')}-{state.get('page_no')}")
    config: dict[str, Any] = {
        "configurable": {"thread_id": job_id},
        "recursion_limit": 25,
    }


    node_stage = {
        "reader": ("reading", 10),
        "director": ("directing", 30),
        "bible": ("casting", 42),
        "casting": ("casting", 48),
        "draft": ("drafting", 60),
        "critic": ("critiquing", 72),
        "refine": ("hero", 85),
        "finalize": ("hero", 85),
        "memory": ("saving", 93),
    }
    await _emit(on_progress, "reading", 5)
    final: dict[str, Any] = dict(state)
    stream = graph.astream(dict(state), config=config, stream_mode="updates")
    async for update in stream:
        for node, payload in update.items():
            if isinstance(payload, dict):
                final.update(payload)
            stage = node_stage.get(node)
            if stage and on_progress is not None:

                await _emit(on_progress, stage[0], stage[1])

    director_out = final.get("director_out", {}) or {}
    final["panel_layout"] = {
        "panel_count": director_out.get("panel_count", 1),
        "layout": director_out.get("layout", "single"),
        "panels": director_out.get("panels", []),
    }
    final.setdefault("quality_used", final.get("quality", "auto"))
    final.setdefault("retry_count", int(final.get("critic_attempt", 0) or 0))
    await _emit(on_progress, "done", 100)
    return final  # type: ignore[return-value]


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
    style_bible: dict[str, Any] | None = None,
    style_ref_urls: list[str] | None = None,
    quality: str = "auto",
    panels: int = 1,
    job_id: str = "",
) -> AgentState:
    q = (quality or "auto").lower()
    if q not in ("draft", "pro", "auto"):
        q = "auto"
    try:
        p = max(1, min(4, int(panels or 1)))
    except (TypeError, ValueError):
        p = 1
    return {
        "book_id": book_id,
        "page_no": page_no,
        "page_text": page_text,
        "style_lock": style_lock,
        "style_bible": style_bible or {},
        "style_ref_urls": style_ref_urls or [],
        "characters": characters,
        "story": story,
        "relationships": relationships,
        "prev_frame_urls": prev_frame_urls or [],
        "char_ref_urls": char_ref_urls or [],
        "quality": q,  # type: ignore[typeddict-item]
        "panels": p,
        "critic_attempt": 0,
        "pro_calls_used": 0,
        "retry_count": 0,
        "job_id": job_id,
    }
