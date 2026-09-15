import io
import re

from PIL import Image, ImageDraw

from app.agents.state import AgentState
from app.services import image_store

_LAYOUT_FOR_COUNT = {1: "single", 2: "grid-2", 3: "vertical-strip", 4: "grid-4"}


def _names(text: str) -> list[str]:
    cands = re.findall(r"\b[A-Z][a-z]{2,}\b", text or "")
    seen: list[str] = []
    for c in cands:
        if c not in seen and c not in {"The", "And", "But", "For", "With", "From"}:
            seen.append(c)
    return seen[:4]


async def run_mock_pipeline(state: AgentState, on_progress=None) -> AgentState:
    async def emit(stage: str, pct: int):
        if on_progress is None:
            return
        res = on_progress(stage, pct)
        if hasattr(res, "__await__"):
            await res

    page_no = int(state.get("page_no", 1))
    text = state.get("page_text", "")
    names = _names(text)
    style = state.get("style_lock", {})
    quality = str(state.get("quality", "auto") or "auto")
    try:
        panels = max(1, min(4, int(state.get("panels", 1) or 1)))
    except (TypeError, ValueError):
        panels = 1

    anchor = int(style.get("seed_anchor", 123456))
    seed = (anchor * 7919 + page_no * 104729) % 2000000000

    await emit("reading", 10)
    reader_out = {
        "summary": f"(mock) Page {page_no}: " + text[:220],
        "scene": "(mock) neon-lit city street",
        "key_visuals": ["neon signs", "rain-slick street", "night crowd"][:3],
        "entities": names,
        "emotions": "tense",
        "actions": ["walks", "watches"],
        "dialogue_summary": "",
        "themes": ["survival"],
        "tension_level": 0.6,
        "resolved_characters": names,
        "pronoun_map": {},
    }
    await emit("directing", 30)
    chars = state.get("characters", [])
    lock = ", ".join(c.get("name", "") for c in chars) or ", ".join(names) or "cast"
    panel_list = [
        {
            "index": i + 1,
            "prompt": f"(mock) panel {i + 1}/{panels} p{page_no}, {lock}, neon alley",
            "camera": "cinematic medium shot",
            "dialogue": "",
            "characters": names,
        }
        for i in range(panels)
    ]
    director_out = {
        "image_prompt": f"(mock) cinematic frame p{page_no}, {lock}, neon alley, rain reflections",
        "negatives": "text, watermark",
        "framing": "cinematic wide shot",
        "seed": seed,
        "panels": panel_list,
        "panel_count": panels,
        "layout": _LAYOUT_FOR_COUNT[panels],
    }
    await emit("casting", 45)
    casting_out = [
        {"name": n, "appearance": f"{n}, consistent look (mock)", "visual_anchors": [n],
         "palette": [], "is_new": False, "sheet_url": None, "sheet_key": None, "sheet_version": 0}
        for n in names
    ]
    style_bible = state.get("style_bible") or {
        "art_style": style.get("art_style", "neo-noir"),
        "lighting": style.get("lighting", ""),
        "palette": list(style.get("palette", []) or []),
        "realism": style.get("realism", "stylized"),
        "rendering_mode": style.get("rendering_mode", ""),
        "seed_anchor": anchor,
        "notes": "(mock) locked on page 1",
    }
    await emit("drafting", 60)
    img = Image.new("RGB", (1024, 576), (11, 15, 26))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 984, 536], outline=(255, 45, 149), width=3)
    d.text((70, 90), f"MOCK FRAME  p{page_no}  seed {seed}", fill=(0, 230, 168))
    d.text((70, 130), f"cast: {lock}"[:90], fill=(200, 200, 200))
    d.text((70, 160), (style.get("art_style", "neo-noir") or "")[:80], fill=(150, 150, 150))
    d.text((70, 190), f"quality={quality} panels={panels}", fill=(150, 150, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    draft_bytes = buf.getvalue()
    draft_key, draft_url = await image_store.upload_draft(
        state["book_id"], page_no, 0, draft_bytes
    )
    await emit("critiquing", 72)
    critic_out = {
        "identity_match": 0.95, "style_match": 0.93, "prompt_match": 0.94,
        "drift_score": 0.05, "passed": True, "fix_notes": "",
        "flagged": False, "attempt": 0, "threshold": 0.75,
    }
    await emit("hero", 85)

    key, url = await image_store.upload_frame(state["book_id"], page_no, draft_bytes)
    quality_used = "pro" if quality == "pro" else "draft"
    await emit("saving", 93)
    deltas = [
        {"name": n, "appearance": f"{n}, consistent look (mock)", "traits": [], "visual_anchors": [n]}
        for n in names
    ]
    story = dict(state.get("story", {}))
    story["current"] = reader_out["summary"][:500]
    if not story.get("summary"):
        story["summary"] = reader_out["summary"][:500]
    story["last_drift_score"] = critic_out["drift_score"]
    story["last_critic_passed"] = True
    await emit("done", 100)
    return {
        **state,
        "reader_out": reader_out,
        "director_out": director_out,
        "casting_out": casting_out,
        "style_bible": style_bible,
        "style_ref_urls": list(state.get("style_ref_urls", []) or []),
        "seed": seed,
        "draft_image_bytes": draft_bytes,
        "draft_image_key": draft_key,
        "draft_image_url": draft_url,
        "critic_out": critic_out,
        "drift_score": critic_out["drift_score"],
        "critic_passed": True,
        "critic_flagged": False,
        "critic_attempt": 0,
        "retry_count": 0,
        "panel_layout": {
            "panel_count": panels, "layout": _LAYOUT_FOR_COUNT[panels], "panels": panel_list,
        },
        "image_bytes": draft_bytes,
        "image_key": key,
        "image_url": url,
        "quality_used": quality_used,
        "updated_story": story,
        "updated_relationships": dict(state.get("relationships", {})),
        "updated_characters": deltas,
    }
