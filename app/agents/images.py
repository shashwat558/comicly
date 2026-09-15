"""Shared image helpers: ref-stack fetching + Gemini image generation."""

from __future__ import annotations

import asyncio
import io

import httpx
from google import genai
from PIL import Image

from app.core.config import get_settings


def genai_client() -> genai.Client:
    s = get_settings()
    if not s.google_api_key or s.google_api_key == "changeme":
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    return genai.Client(api_key=s.google_api_key)


async def _fetch_one(url: str, size: int = 1024) -> Image.Image | None:
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
            img.thumbnail((size, size))
            return img
    except Exception:

        return None


async def fetch_ref_images(urls: list[str], cap: int, size: int = 1024) -> list[Image.Image]:
    """Fetch up to `cap` reference images, skipping dead URLs. Order preserved."""
    out: list[Image.Image] = []
    for url in (urls or [])[:cap]:
        if not url:
            continue
        img = await _fetch_one(url, size=size)
        if img is not None:
            out.append(img)
        if len(out) >= cap:
            break
    return out


def build_ref_url_stack(
    state: dict,
    *,
    include_draft_as_ref: bool = False,
) -> list[str]:
    """Assemble the ref-stack URLs: sheets + style refs + prev frames, capped at 14.

    Order matters: character sheets first (identity), then style refs, then
    previous frames (continuity), then the draft itself for hero/fix editing.
    """
    s = get_settings()
    urls: list[str] = []


    sheet_urls: list[str] = []
    for c in state.get("casting_out", []) or []:
        if isinstance(c, dict) and c.get("sheet_url"):
            sheet_urls.append(c["sheet_url"])
    for c in state.get("characters", []) or []:
        if isinstance(c, dict):
            for key in ("sheet_image_url", "reference_image_url"):
                u = c.get(key)
                if u and u not in sheet_urls:
                    sheet_urls.append(u)
    for u in (state.get("char_ref_urls", []) or []):
        if u and u not in sheet_urls:
            sheet_urls.append(u)
    urls.extend(sheet_urls[: s.max_char_refs])


    style_urls = list(state.get("style_ref_urls", []) or [])
    urls.extend(style_urls[: s.max_style_refs])


    prev_urls = list(state.get("prev_frame_urls", []) or [])
    urls.extend(prev_urls[: s.max_prev_frames])


    urls = urls[: s.max_ref_images]
    _ = include_draft_as_ref
    return urls


def extract_image_bytes(response) -> bytes | None:
    candidate = (response.candidates or [None])[0] if hasattr(response, "candidates") else None
    parts = getattr(getattr(candidate, "content", None), "parts", None) or []
    if not parts:
        parts = getattr(response, "parts", []) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None and getattr(inline, "data", None):
            raw = inline.data
            return raw if isinstance(raw, bytes) else bytes(raw)
        if hasattr(part, "as_bytes") and callable(part.as_bytes):
            try:
                return part.as_bytes()
            except Exception:
                continue
    return None


async def generate_image_bytes(
    model: str,
    prompt: str,
    ref_images: list[Image.Image] | None = None,
    extra_images: list[Image.Image] | None = None,
) -> bytes:
    """Call Gemini image model with prompt + ref images. Raises on no-image."""
    client = genai_client()
    contents: list = [prompt]
    for img in (ref_images or []) + (extra_images or []):
        contents.append(img)

    def _generate():
        return client.models.generate_content(model=model, contents=contents)

    response = await asyncio.to_thread(_generate)
    image_bytes = extract_image_bytes(response)
    if image_bytes is None:
        text = ""
        try:
            text = str(getattr(response, "text", ""))[:500]
        except Exception:
            pass
        raise RuntimeError(f"Image model {model} returned no image. {text}")
    return image_bytes


def pil_from_bytes(data: bytes, size: int = 1024) -> Image.Image:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img.thumbnail((size, size))
    return img
