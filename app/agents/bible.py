"""Style bible: page 1 locks art direction + 1 generated style ref (cheap draft model)."""

from __future__ import annotations

from langchain.agents import create_agent

from app.agents.images import fetch_ref_images, generate_image_bytes
from app.agents.io import StyleBible
from app.agents.llm import invoke_structured, text_llm
from app.agents.prompts import build_style_bible_prompt
from app.agents.state import AgentState
from app.core.config import get_settings
from app.services import image_store


async def bible_node(state: AgentState) -> AgentState:
    page_no = int(state.get("page_no", 1))
    existing_bible = state.get("style_bible") or {}
    style = dict(state.get("style_lock", {}) or {})
    style_refs = list(state.get("style_ref_urls", []) or [])


    if page_no != 1 or existing_bible:
        bible = dict(existing_bible) if existing_bible else {
            "art_style": style.get("art_style", ""),
            "lighting": style.get("lighting", ""),
            "palette": list(style.get("palette", []) or []),
            "realism": style.get("realism", "stylized"),
            "rendering_mode": style.get("rendering_mode", ""),
            "seed_anchor": int(style.get("seed_anchor", 123456)),
            "notes": "",
        }
        return {**state, "style_bible": bible, "style_lock": style, "style_ref_urls": style_refs}

    prompt = build_style_bible_prompt(
        reader=state.get("reader_out", {}) or {}, style=style, page_no=page_no
    )
    agent = create_agent(model=text_llm(0.0), response_format=StyleBible)
    try:
        locked = invoke_structured(agent, prompt)
    except Exception:
        locked = {}
    bible = {
        "art_style": locked.get("art_style") or style.get("art_style", ""),
        "lighting": locked.get("lighting") or style.get("lighting", ""),
        "palette": locked.get("palette") or list(style.get("palette", []) or []),
        "realism": locked.get("realism") or style.get("realism", "stylized"),
        "rendering_mode": locked.get("rendering_mode") or style.get("rendering_mode", ""),
        "seed_anchor": int(locked.get("seed_anchor") or style.get("seed_anchor", 123456)),
        "notes": str(locked.get("notes") or ""),
    }

    style.update({k: bible[k] for k in ("art_style", "lighting", "palette", "realism", "rendering_mode", "seed_anchor") if bible.get(k)})


    if not style_refs:
        try:
            settings = get_settings()
            ref_prompt = (
                f"Style reference, no characters, no text, no watermark. "
                f"{bible.get('art_style')}, lighting {bible.get('lighting')}, "
                f"palette {bible.get('palette')}. {bible.get('notes')}"
            )
            prev_imgs = await fetch_ref_images(list(state.get("prev_frame_urls", []) or []), cap=1)
            img_bytes = await generate_image_bytes(
                settings.gemini_draft_image_model, ref_prompt, prev_imgs
            )
            key, url = await image_store.upload_style_ref(
                book_id=str(state["book_id"]), name="bible-v1", data=img_bytes
            )
            style_refs = [url]
            _ = key
        except Exception:
            style_refs = []

    return {**state, "style_bible": bible, "style_lock": style, "style_ref_urls": style_refs}
