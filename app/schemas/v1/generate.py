import uuid

from pydantic import BaseModel, Field

from app.schemas.v1.book import StyleLock


class GenerateRequest(BaseModel):
    page_no: int = Field(..., ge=1)
    style_override: StyleLock | None = None
    force: bool = False


class GenerateResponse(BaseModel):
    job_id: str
    book_id: uuid.UUID
    page_no: int
    status: str = "queued"


class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    page_no: int | None = None
    image_url: str | None = None
    error: str | None = None
