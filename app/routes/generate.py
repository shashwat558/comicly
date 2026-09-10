from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.graph.orchestrator import get_default_state, run_graph


class GenerationRequest(BaseModel):
    page_number: int = Field(..., ge=1)
    page_text: str
    memory: dict[str, Any] | None = None
    prev_image_url: str | None = None
    current_image_url: str | None = None
    reader_output: dict[str, Any] | None = None
    director_output: dict[str, Any] | None = None
    visual_prompt: str | None = None
    image_metadata: dict[str, Any] | None = None


class GenerationResponse(BaseModel):
    state: dict[str, Any]


router = APIRouter()


@router.post("/", response_model=GenerationResponse)
async def generate_page(body: GenerationRequest):
    state = get_default_state()
    state["page_number"] = body.page_number
    state["page_text"] = body.page_text

    if body.memory is not None:
        state["memory"] = body.memory
    if body.prev_image_url is not None:
        state["prev_image_url"] = body.prev_image_url
    if body.current_image_url is not None:
        state["current_image_url"] = body.current_image_url
    if body.reader_output is not None:
        state["reader_output"] = body.reader_output
    if body.director_output is not None:
        state["director_output"] = body.director_output
    if body.visual_prompt is not None:
        state["visual_prompt"] = body.visual_prompt
    if body.image_metadata is not None:
        state["image_metadata"] = body.image_metadata

    try:
        result_state = run_graph(state)
    except Exception as exc:  # pragma: no cover - passthrough
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    return {"state": result_state}
