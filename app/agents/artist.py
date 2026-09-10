import io

import httpx
from google import genai
from PIL import Image

from app.agents.prompts import build_artist_prompt
from app.agents.state import AgentState
from app.core.config import get_settings
from app.services import image_store


def _client() -> genai.Client:
    s = get_settings()
    if not s.google_api_key or s.google_api_key == "changeme":
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    return genai.Client(api_key=s.google_api_key)


async def _fetch_image(url: str) -> Image.Image | None:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(url)
            r.raise_for_status()
            img = Image.open(io.BytesIO(r.content))
            img.load()
            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            return img
    except Exception:
        # a dead ref url shouldn't fail the whole page
        return None


async def artist_node(state: AgentState) -> AgentState:
    s = get_settings()
    prompt = build_artist_prompt(
        director=state.get("director_out", {}),
        style=state.get("style_lock", {}),
        characters=state.get("characters", []),
    )
    contents: list = [prompt]
    # one prev frame + two char refs is plenty, more just adds cost
    for url in (state.get("prev_frame_urls", []) or [])[:1]:
        img = await _fetch_image(url)
        if img is not None:
            contents.append(img)
    for url in (state.get("char_ref_urls", []) or [])[:2]:
        img = await _fetch_image(url)
        if img is not None:
            contents.append(img)

    client = _client()

    import asyncio

    def _generate():
        return client.models.generate_content(model=s.gemini_image_model, contents=contents)

    response = await asyncio.to_thread(_generate)

    image_bytes: bytes | None = None
    candidate = (response.candidates or [None])[0] if hasattr(response, "candidates") else None
    parts = getattr(getattr(candidate, "content", None), "parts", None) or getattr(response, "parts", []) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            raw = inline.data
            image_bytes = raw if isinstance(raw, bytes) else bytes(raw)
            break

        if hasattr(part, "as_bytes") and callable(part.as_bytes):
            try:
                image_bytes = part.as_bytes()
                break
            except Exception:
                continue
    if image_bytes is None:
        text = ""
        try:
            text = str(getattr(response, "text", ""))[:500]
        except Exception:
            pass
        raise RuntimeError(f"Image model returned no image. {text}")

    key, url = await image_store.upload_frame(
        book_id=state["book_id"], page_no=int(state.get("page_no", 1)), data=image_bytes
    )
    return {**state, "image_bytes": image_bytes, "image_key": key, "image_url": url}
