import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import get_current_user
from app.models.book import Book, Page
from app.models.character import Character
from app.models.frame import Frame
from app.models.user import User
from app.schemas.v1.book import BookDetail, BookListItem, CharacterOut, FrameOut
from app.services.ingest import enc, parse_book

router = APIRouter()


async def owned_book(db: AsyncSession, user: User, book_id: uuid.UUID) -> Book:
    # 404 either way so nobody can probe other users' ids
    book = await db.get(Book, book_id)
    if book is None or book.owner_id != user.id:
        raise HTTPException(404, "Book not found")
    return book


@router.post("/upload", response_model=BookDetail, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form("Unknown"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    settings = get_settings()
    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb}MB limit")
    try:
        kind, chunks = parse_book(file.filename or "", file.content_type or "", data)
    except ValueError as e:
        raise HTTPException(400, str(e))

    book = Book(
        owner_id=user.id,
        title=title.strip() or (file.filename or "Untitled"),
        author=author.strip() or "Unknown",
        book_metadata={"filename": file.filename, "content_type": file.content_type, "kind": kind},
        status="ready",
        total_pages=len(chunks),
    )
    db.add(book)
    await db.flush()
    for i, chunk in enumerate(chunks, start=1):
        db.add(Page(book_id=book.id, page_no=i, text=chunk, tokens=len(enc.encode(chunk))))
    await db.commit()
    await db.refresh(book)
    return BookDetail(
        id=book.id, title=book.title, author=book.author,
        total_pages=book.total_pages, status=book.status, style_lock=None,
    )


@router.get("", response_model=list[BookListItem])
async def list_books(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(Book).where(Book.owner_id == user.id).order_by(Book.created_at.desc())
        )
    ).scalars().all()
    return [BookListItem.model_validate(r) for r in rows]


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    book = await owned_book(db, user, book_id)
    style = book.style_lock
    return BookDetail(
        id=book.id, title=book.title, author=book.author,
        total_pages=book.total_pages, status=book.status,
        style_lock=style,  # type: ignore[arg-type]
    )


@router.get("/{book_id}/characters", response_model=list[CharacterOut])
async def list_characters(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    rows = (await db.execute(select(Character).where(Character.book_id == book_id))).scalars().all()
    return [CharacterOut.model_validate(r) for r in rows]


@router.get("/{book_id}/frames", response_model=list[FrameOut])
async def list_frames(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await owned_book(db, user, book_id)
    rows = (await db.execute(
        select(Frame).where(Frame.book_id == book_id).order_by(Frame.page_no)
    )).scalars().all()
    out = []
    for r in rows:
        out.append(FrameOut(
            page_no=r.page_no, image_url=r.image_url, status=r.status,
            seed=r.seed, reader_out=r.reader_out, director_out=r.director_out,
        ))
    return out


@router.delete("/{book_id}", status_code=204)
async def delete_book(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    book = await owned_book(db, user, book_id)
    await db.delete(book)
    await db.commit()
    return None
