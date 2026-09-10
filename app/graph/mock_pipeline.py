import io
import re

from PIL import Image, ImageDraw

from app.agents.state import AgentState
from app.services import image_store


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
    # same seed math as the real director so mock frames line up
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
    }
    await emit("directing", 40)
    chars = state.get("characters", [])
    lock = ", ".join(c.get("name", "") for c in chars) or ", ".join(names) or "cast"
    director_out = {
        "image_prompt": f"(mock) cinematic frame p{page_no}, {lock}, neon alley, rain reflections",
        "negatives": "text, watermark",
        "framing": "cinematic wide shot",
        "seed": seed,
    }
    await emit("rendering", 65)
    img = Image.new("RGB", (1024, 576), (11, 15, 26))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 984, 536], outline=(255, 45, 149), width=3)
    d.text((70, 90), f"MOCK FRAME  p{page_no}  seed {seed}", fill=(0, 230, 168))
    d.text((70, 130), f"cast: {lock}"[:90], fill=(200, 200, 200))
    d.text((70, 160), (style.get("art_style", "neo-noir") or "")[:80], fill=(150, 150, 150))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    key, url = await image_store.upload_frame(state["book_id"], page_no, buf.getvalue())
    await emit("saving", 85)
    deltas = [
        {"name": n, "appearance": f"{n}, consistent look (mock)", "traits": [], "visual_anchors": [n]}
        for n in names
    ]
    story = dict(state.get("story", {}))
    story["current"] = reader_out["summary"][:500]
    if not story.get("summary"):
        story["summary"] = reader_out["summary"][:500]
    await emit("done", 100)
    return {
        **state,
        "reader_out": reader_out,
        "director_out": director_out,
        "seed": seed,
        "image_key": key,
        "image_url": url,
        "updated_story": story,
        "updated_relationships": dict(state.get("relationships", {})),
        "updated_characters": deltas,
    }
