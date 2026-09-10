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
    last_frame = (
        await db.execute(
            select(Frame)
            .where(Frame.book_id == book_id)
            .order_by(desc(Frame.page_no))
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "book": book,
        "characters": list(chars),
        "story": dict(snap.story) if snap else {"summary": "", "current": "", "tone": "", "active_threads": []},
        "relationships": dict(snap.relationships) if snap else {},
        "version": snap.version if snap else 0,
        "last_frame": last_frame,
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
