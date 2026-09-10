import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.book import Page
from app.models.frame import Frame
from app.models.user import User
from app.routes.v1.books import owned_book
from app.schemas.v1.book import FrameOut, PageOut

router = APIRouter()


@router.get("/{book_id}/pages", response_model=list[PageOut])
async def list_pages(
    book_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    rows = (await db.execute(
        select(Page).where(Page.book_id == book_id)
        .order_by(Page.page_no)
        .offset((page - 1) * size).limit(size)
    )).scalars().all()
    return [PageOut.model_validate(r) for r in rows]


@router.get("/{book_id}/pages/{page_no}", response_model=PageOut)
async def get_page(
    book_id: uuid.UUID,
    page_no: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    row = (await db.execute(
        select(Page).where(Page.book_id == book_id, Page.page_no == page_no)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Page not found")
    return PageOut.model_validate(row)


@router.get("/{book_id}/frames/{page_no}", response_model=FrameOut)
async def get_frame(
    book_id: uuid.UUID,
    page_no: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    row = (await db.execute(
        select(Frame).where(Frame.book_id == book_id, Frame.page_no == page_no)
    )).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "Frame not generated yet")
    return FrameOut(
        page_no=row.page_no, image_url=row.image_url, status=row.status,
        seed=row.seed, reader_out=row.reader_out, director_out=row.director_out,
    )
