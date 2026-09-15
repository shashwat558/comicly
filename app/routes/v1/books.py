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
    for i, (chunk, pdf_page) in enumerate(chunks, start=1):
        db.add(Page(book_id=book.id, page_no=i, text=chunk, tokens=len(enc.encode(chunk)), pdf_page=pdf_page))


    ext = {"pdf": ".pdf", "epub": ".epub", "txt": ".txt"}.get(kind, ".bin")
    content_type = file.content_type or "application/octet-stream"
    try:
        from app.core import s3 as s3core
        book.source_key = f"{book.id}/source{ext}"
        book.source_content_type = content_type
        await s3core.upload_bytes(book.source_key, data, content_type)
    except Exception as e:
        await db.rollback()
        raise HTTPException(502, f"Could not store the source file: {e}")

    await db.commit()
    await db.refresh(book)
    return BookDetail(
        id=book.id, title=book.title, author=book.author,
        total_pages=book.total_pages, status=book.status, style_lock=None,
        kind=kind, has_source=True,
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
    meta = book.book_metadata or {}
    return BookDetail(
        id=book.id, title=book.title, author=book.author,
        total_pages=book.total_pages, status=book.status,
        style_lock=style,  # type: ignore[arg-type]
        style_bible=book.style_bible,
        pro_calls_used=int(getattr(book, "pro_calls_used", 0) or 0),
        kind=str(meta.get("kind", "txt")), has_source=bool(book.source_key),
    )


@router.get("/{book_id}/source")
async def get_source(
    book_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from fastapi.responses import Response

    from app.core import s3 as s3core

    book = await owned_book(db, user, book_id)
    if not book.source_key:
        raise HTTPException(404, "No source file stored for this book, re-upload it for page view.")
    try:
        data = await s3core.download_key(book.source_key)
    except Exception:
        raise HTTPException(502, "Could not fetch the source file.")
    meta = book.book_metadata or {}
    filename = str(meta.get("filename") or f"{book.title}.pdf")
    safe = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename).strip() or "book.pdf"
    return Response(
        content=data,
        media_type=book.source_content_type or "application/octet-stream",
        headers={"Content-Disposition": f'inline; filename="{safe}"'},
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
            quality=r.quality or "auto", drift_score=r.drift_score,
            critic_out=r.critic_out, panel_layout=r.panel_layout,
            retry_count=int(r.retry_count or 0), flagged=bool(r.flagged),
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
