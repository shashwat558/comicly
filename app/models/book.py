import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author: Mapped[str] = mapped_column(String(500), default="Unknown")
    book_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

    source_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    source_content_type: Mapped[str | None] = mapped_column(String(200), nullable=True)


    style_lock: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


    style_bible: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    pro_calls_used: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="ready")
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pages: Mapped[list["Page"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    characters: Mapped[list["Character"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    frames: Mapped[list["Frame"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    owner: Mapped["User | None"] = relationship(back_populates="books")


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (UniqueConstraint("book_id", "page_no", name="uq_pages_book_page"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    tokens: Mapped[int] = mapped_column(Integer, default=0)

    pdf_page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    book: Mapped[Book] = relationship(back_populates="pages")
