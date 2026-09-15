"""Critic: VLM judge scoring identity / style / prompt match, with drift metric."""

from __future__ import annotations

import json
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.images import genai_client, pil_from_bytes
from app.agents.io import CriticOutput
from app.agents.prompts import build_critic_prompt
from app.agents.state import AgentState
from app.core.config import get_settings


def parse_critic_json(raw: str) -> dict:
    """Parse critic JSON robustly: fenced blocks, leading prose, trailing text."""
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty critic response")
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]
    return json.loads(text)


def verdict_from_scores(
    identity: float, style: float, prompt_m: float, threshold: float
) -> dict:
    def clamp(v) -> float:
        try:
            return max(0.0, min(1.0, float(v)))
        except (TypeError, ValueError):
            return 0.0

    identity, style, prompt_m = clamp(identity), clamp(style), clamp(prompt_m)
    drift = 1.0 - min(identity, style, prompt_m)
    passed = min(identity, style, prompt_m) >= threshold
    return {
        "identity_match": identity, "style_match": style, "prompt_match": prompt_m,
        "drift_score": round(drift, 4), "passed": passed,
    }


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def _judge(prompt: str, image) -> str:
    client = genai_client()
    s = get_settings()
    resp = client.models.generate_content(
        model=s.gemini_text_model,
        contents=[prompt + "\nReturn ONLY JSON: {identity_match, style_match, prompt_match, fix_notes}.", image],
        config={"response_mime_type": "application/json"},
    )
    text = getattr(resp, "text", "") or ""
    if not text.strip():

        try:
            cands = getattr(resp, "candidates", []) or []
            parts = getattr(getattr(cands[0], "content", None), "parts", []) or []
            text = "".join(getattr(p, "text", "") or "" for p in parts)
        except Exception:
            text = ""
    if not text.strip():
        raise RuntimeError("Critic model returned empty response")
    return text


async def critic_node(state: AgentState) -> AgentState:
    import asyncio

    settings = get_settings()
    threshold = float(settings.critic_pass_threshold)
    max_retries = int(settings.critic_max_retries)
    attempt = int(state.get("critic_attempt", 0) or 0)

    draft_bytes = state.get("draft_image_bytes") or state.get("image_bytes")
    if draft_bytes is None:
        raise RuntimeError("Critic has no image to judge")

    prompt = build_critic_prompt(
        reader=state.get("reader_out", {}) or {},
        director=state.get("director_out", {}) or {},
        characters=state.get("characters", []) or [],
        style=state.get("style_lock", {}) or {},
    )
    image = pil_from_bytes(bytes(draft_bytes))

    raw = await asyncio.to_thread(_judge, prompt, image)
    try:
        parsed = parse_critic_json(raw)
    except Exception as e:
        raise RuntimeError(f"Critic returned unparseable output: {str(raw)[:300]} ({e})")

    verdict = verdict_from_scores(
        parsed.get("identity_match", 0), parsed.get("style_match", 0),
        parsed.get("prompt_match", 0), threshold,
    )
    fix_notes = str(parsed.get("fix_notes", "") or "")
    flagged = False
    if not verdict["passed"] and attempt >= max_retries:

        flagged = True
    critic_out = {
        **verdict,
        "fix_notes": fix_notes if not verdict["passed"] else "",
        "flagged": flagged,
        "attempt": attempt,
        "threshold": threshold,
    }

    CriticOutput(
        identity_match=critic_out["identity_match"], style_match=critic_out["style_match"],
        prompt_match=critic_out["prompt_match"], drift_score=critic_out["drift_score"],
        passed=critic_out["passed"], fix_notes=critic_out["fix_notes"], flagged=flagged,
    )
    return {
        **state, "critic_out": critic_out, "drift_score": critic_out["drift_score"],
        "critic_passed": verdict["passed"], "critic_flagged": flagged,
        "fix_notes": critic_out["fix_notes"],
        "retry_count": attempt,
    }
