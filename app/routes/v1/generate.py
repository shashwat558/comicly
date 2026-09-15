import uuid
from urllib.parse import urlparse

from arq.connections import RedisSettings, create_pool
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.redis import publish_progress
from app.core.security import get_current_user
from app.models.book import Page
from app.models.frame import Frame
from app.models.user import User
from app.routes.v1.books import owned_book
from app.schemas.v1.generate import GenerateRequest, GenerateResponse

router = APIRouter()
_pool = None


async def get_pool():
    global _pool
    if _pool is None:
        u = urlparse(get_settings().redis_url)
        _pool = await create_pool(RedisSettings(host=u.hostname or "localhost", port=u.port or 6379))
    return _pool


@router.post("/{book_id}/generate", response_model=GenerateResponse, status_code=202)
async def enqueue_generate(
    book_id: uuid.UUID,
    body: GenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    page = (await db.execute(
        select(Page).where(Page.book_id == book_id, Page.page_no == body.page_no)
    )).scalar_one_or_none()
    if page is None:
        raise HTTPException(404, f"Page {body.page_no} not found")
    if body.page_no != 1 and body.style_override is not None:
        raise HTTPException(400, "style_override is only allowed on page 1 (style is locked after)")

    job_id = f"{book_id.hex[:8]}-{body.page_no:04d}-{uuid.uuid4().hex[:8]}"
    await publish_progress(job_id, {
        "job_id": job_id, "book_id": str(book_id), "page_no": body.page_no,
        "status": "queued", "progress": 0,
    })
    try:
        pool = await get_pool()
        await pool.enqueue_job(
            "generate_page", str(book_id), body.page_no, job_id,
            body.style_override.model_dump() if body.style_override else None,
            body.force, body.quality, body.panels, _job_id=job_id,
        )
    except Exception as e:

        await publish_progress(job_id, {
            "job_id": job_id, "book_id": str(book_id), "page_no": body.page_no,
            "status": "error", "progress": 0, "error": f"Queue unavailable: {e}",
        })
        raise HTTPException(503, f"Job queue unavailable: {e}")
    return GenerateResponse(job_id=job_id, book_id=book_id, page_no=body.page_no, status="queued")


@router.post("/{book_id}/frames/{page_no}/enhance", response_model=GenerateResponse, status_code=202)
async def enqueue_enhance(
    book_id: uuid.UUID,
    page_no: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """One-click Pro upscale of an existing frame (frontend Enhance button)."""
    await owned_book(db, user, book_id)
    frame = (await db.execute(
        select(Frame).where(Frame.book_id == book_id, Frame.page_no == page_no)
    )).scalar_one_or_none()
    if frame is None or not frame.image_url:
        raise HTTPException(404, "Frame not generated yet")
    if (frame.quality or "").lower() == "pro":
        raise HTTPException(409, "Frame is already Pro quality")

    job_id = f"{book_id.hex[:8]}-{page_no:04d}-enh-{uuid.uuid4().hex[:4]}"
    await publish_progress(job_id, {
        "job_id": job_id, "book_id": str(book_id), "page_no": page_no,
        "status": "queued", "progress": 0,
    })
    try:
        pool = await get_pool()
        await pool.enqueue_job(
            "enhance_page", str(book_id), page_no, job_id, _job_id=job_id,
        )
    except Exception as e:
        await publish_progress(job_id, {
            "job_id": job_id, "book_id": str(book_id), "page_no": page_no,
            "status": "error", "progress": 0, "error": f"Queue unavailable: {e}",
        })
        raise HTTPException(503, f"Job queue unavailable: {e}")
    return GenerateResponse(job_id=job_id, book_id=book_id, page_no=page_no, status="queued")
