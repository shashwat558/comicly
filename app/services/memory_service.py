import uuid
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.character import Character
from app.models.frame import Frame, MemorySnapshot


async def get_book_context(db: AsyncSession, book_id: uuid.UUID) -> dict[str, Any]:
    book = await db.get(Book, book_id)
    if book is None:
        raise ValueError("Book not found")
    chars = (
        (await db.execute(select(Character).where(Character.book_id == book_id))).scalars().all()
    )
    snap = (
        await db.execute(
            select(MemorySnapshot)
            .where(MemorySnapshot.book_id == book_id)
            .order_by(desc(MemorySnapshot.version))
            .limit(1)
        )
    ).scalar_one_or_none()
    recent_frames = (
        await db.execute(
            select(Frame)
            .where(Frame.book_id == book_id, Frame.status == "done", Frame.image_url.is_not(None))
            .order_by(desc(Frame.page_no))
            .limit(3)
        )
    ).scalars().all()
    last_frame = recent_frames[0] if recent_frames else None
    bible = dict(book.style_bible) if getattr(book, "style_bible", None) else {}
    return {
        "book": book,
        "characters": list(chars),
        "story": dict(snap.story) if snap else {"summary": "", "current": "", "tone": "", "active_threads": []},
        "relationships": dict(snap.relationships) if snap else {},
        "version": snap.version if snap else 0,
        "last_frame": last_frame,
        "prev_frames": list(recent_frames),
        "style_bible": bible,
        "style_ref_urls": list(bible.get("ref_urls", []) or []),
        "pro_calls_used": int(getattr(book, "pro_calls_used", 0) or 0),
    }


async def save_snapshot(
    db: AsyncSession,
    book_id: uuid.UUID,
    page_no: int,
    story: dict,
    relationships: dict,
    version: int,
) -> MemorySnapshot:
    snap = MemorySnapshot(
        book_id=book_id, page_no=page_no, story=story, relationships=relationships,
        version=version + 1,
    )
    db.add(snap)
    await db.flush()
    return snap


async def save_style_bible(
    db: AsyncSession, book_id: uuid.UUID, bible: dict, style_lock: dict | None = None
) -> None:
    book = await db.get(Book, book_id)
    if book is None:
        raise ValueError("Book not found")
    book.style_bible = dict(bible or {})
    if style_lock is not None:
        book.style_lock = dict(style_lock)
    await db.flush()


async def bump_pro_calls(db: AsyncSession, book_id: uuid.UUID, n: int) -> None:
    book = await db.get(Book, book_id)
    if book is None:
        return
    book.pro_calls_used = int(getattr(book, "pro_calls_used", 0) or 0) + max(0, int(n))
    await db.flush()


async def upsert_characters(
    db: AsyncSession, book_id: uuid.UUID, chars: list[dict], page_no: int
) -> None:
    for c in chars:
        name = (c.get("name") or "").strip()
        if not name:
            continue
        existing = (
            await db.execute(
                select(Character).where(Character.book_id == book_id, Character.name == name)
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                Character(
                    book_id=book_id,
                    name=name,
                    appearance=c.get("appearance", ""),
                    traits=c.get("traits", []),
                    visual_anchors=c.get("visual_anchors", []),
                    first_page=page_no,
                    last_seen_page=page_no,
                )
            )
        else:
            if c.get("appearance"):
                existing.appearance = c["appearance"]
            if c.get("traits"):
                existing.traits = c["traits"]
            if c.get("visual_anchors"):
                existing.visual_anchors = c["visual_anchors"]
            existing.last_seen_page = page_no
    await db.flush()


async def upsert_casting_sheets(
    db: AsyncSession, book_id: uuid.UUID, casting: list[dict], page_no: int
) -> None:
    """Persist canonical sheets minted by the casting agent (first appearance)."""
    for c in casting or []:
        name = ((c.get("name") or "").strip() if isinstance(c, dict) else "")
        if not name:
            continue
        existing = (
            await db.execute(
                select(Character).where(Character.book_id == book_id, Character.name == name)
            )
        ).scalar_one_or_none()
        appearance = c.get("appearance", "") or ""
        anchors = list(c.get("visual_anchors", []) or [])
        traits: list = []
        if existing is None:
            db.add(
                Character(
                    book_id=book_id,
                    name=name,
                    appearance=appearance,
                    traits=traits,
                    visual_anchors=anchors,
                    reference_image_url=c.get("sheet_url"),
                    reference_image_key=c.get("sheet_key"),
                    sheet_image_url=c.get("sheet_url"),
                    sheet_image_key=c.get("sheet_key"),
                    sheet_version=int(c.get("sheet_version", 1) or 1),
                    first_page=page_no,
                    last_seen_page=page_no,
                )
            )
        else:
            if c.get("sheet_url"):
                existing.sheet_image_url = c["sheet_url"]
                existing.sheet_image_key = c.get("sheet_key")
                existing.reference_image_url = c["sheet_url"]
                existing.reference_image_key = c.get("sheet_key")
                try:
                    existing.sheet_version = int(c.get("sheet_version", (existing.sheet_version or 0) + 1))
                except (TypeError, ValueError):
                    pass
            if appearance and not existing.appearance:
                existing.appearance = appearance
            if anchors and not (existing.visual_anchors or []):
                existing.visual_anchors = anchors
            existing.last_seen_page = page_no
    await db.flush()
