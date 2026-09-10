import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models.book import Book, Page
from app.models.character import Character
from app.models.frame import Frame
from app.schemas.v1.book import BookDetail, BookListItem, CharacterOut, FrameOut
from app.services.ingest import enc, parse_book

router = APIRouter()


@router.post("/upload", response_model=BookDetail, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form("Unknown"),
    db: AsyncSession = Depends(get_db),
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
async def list_books(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Book).order_by(Book.created_at.desc()))).scalars().all()
    return [BookListItem.model_validate(r) for r in rows]


@router.get("/{book_id}", response_model=BookDetail)
async def get_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    style = book.style_lock
    return BookDetail(
        id=book.id, title=book.title, author=book.author,
        total_pages=book.total_pages, status=book.status,
        style_lock=style,  # type: ignore[arg-type]
    )


@router.get("/{book_id}/characters", response_model=list[CharacterOut])
async def list_characters(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Character).where(Character.book_id == book_id))).scalars().all()
    return [CharacterOut.model_validate(r) for r in rows]


@router.get("/{book_id}/frames", response_model=list[FrameOut])
async def list_frames(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
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
async def delete_book(book_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    book = await db.get(Book, book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    await db.delete(book)
    await db.commit()
