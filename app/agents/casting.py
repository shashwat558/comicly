"""Casting agent: detect first-appearance characters, mint canonical sheets on Pro."""

from __future__ import annotations

from langchain.agents import create_agent
from pydantic import BaseModel, Field

from app.agents.images import build_ref_url_stack, fetch_ref_images, generate_image_bytes, pil_from_bytes
from app.agents.io import CastingSheet
from app.agents.llm import invoke_structured, text_llm
from app.agents.prompts import build_casting_prompt, build_sheet_prompt
from app.agents.state import AgentState
from app.core.config import get_settings
from app.services import image_store


class _CastingOutput(BaseModel):
    sheets: list[CastingSheet] = Field(default_factory=list)


def _slug(name: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (name or "unknown"))
    return (safe[:60] or "unknown")


async def casting_node(state: AgentState) -> AgentState:
    reader = state.get("reader_out", {}) or {}
    characters = list(state.get("characters", []) or [])
    known = {str(c.get("name", "")).strip().lower() for c in characters if c.get("name")}
    page_no = int(state.get("page_no", 1))

    prompt = build_casting_prompt(reader=reader, characters=characters, page_no=page_no)
    agent = create_agent(model=text_llm(0.0), response_format=_CastingOutput)
    try:
        data = invoke_structured(agent, prompt)
    except Exception:

        data = {"sheets": []}
    sheets_in = data.get("sheets", []) or []


    seen = {str(s.get("name", "")).strip().lower() for s in sheets_in if isinstance(s, dict)}
    for ent in reader.get("entities", []) or []:
        key = str(ent).strip().lower()
        if key and key not in known and key not in seen and len(str(ent).strip()) >= 2:
            sheets_in.append({
                "name": str(ent).strip(), "appearance": f"{str(ent).strip()}, consistent look",
                "visual_anchors": [str(ent).strip()], "palette": [], "is_new": True,
            })
            seen.add(key)

    settings = get_settings()
    out: list[dict] = []
    pro_used = int(state.get("pro_calls_used", 0) or 0)
    cap = settings.max_pro_calls_per_book or 10**9

    for s in sheets_in:
        if not isinstance(s, dict) or not str(s.get("name", "")).strip():
            continue
        name = str(s["name"]).strip()
        is_new = bool(s.get("is_new", name.lower() not in known))
        if not is_new:
            out.append({**s, "name": name, "is_new": False})
            continue

        existing = next((c for c in characters if str(c.get("name", "")).lower() == name.lower()), {})
        sheet_version = int(existing.get("sheet_version", 0) or 0) + 1
        sheet_url = existing.get("sheet_image_url")
        sheet_key = existing.get("sheet_image_key")
        if pro_used < cap:
            try:
                sheet_prompt = build_sheet_prompt(s, state.get("style_lock", {}) or {})

                ref_urls = build_ref_url_stack(state)
                ref_imgs = await fetch_ref_images(ref_urls, cap=settings.max_ref_images)
                img_bytes = await generate_image_bytes(
                    settings.gemini_sheet_image_model, sheet_prompt, ref_imgs
                )
                sheet_key, sheet_url = await image_store.upload_sheet(
                    book_id=str(state["book_id"]), name=_slug(name),
                    version=sheet_version, data=img_bytes,
                )
                pro_used += 1
            except Exception:

                sheet_url, sheet_key = sheet_url, sheet_key
        out.append({
            "name": name,
            "appearance": str(s.get("appearance", "") or ""),
            "visual_anchors": list(s.get("visual_anchors", []) or []),
            "palette": list(s.get("palette", []) or []),
            "is_new": True,
            "sheet_url": sheet_url,
            "sheet_key": sheet_key,
            "sheet_version": sheet_version,
        })


    new_sheet_urls = [c["sheet_url"] for c in out if c.get("is_new") and c.get("sheet_url")]
    char_refs = list(state.get("char_ref_urls", []) or [])
    for u in new_sheet_urls:
        if u not in char_refs:
            char_refs.append(u)
    void = pil_from_bytes
    _ = void
    return {**state, "casting_out": out, "char_ref_urls": char_refs, "pro_calls_used": pro_used}
