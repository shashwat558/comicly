import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Frame(Base):
    __tablename__ = "frames"
    __table_args__ = (UniqueConstraint("book_id", "page_no", name="uq_frames_book_page"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    reader_out: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    director_out: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    image_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    prev_frame_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # bigint because our seeds overflow int32
    seed: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="done")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    book = relationship("Book", back_populates="frames")


class MemorySnapshot(Base):
    __tablename__ = "memory_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    page_no: Mapped[int] = mapped_column(Integer, nullable=False)
    story: Mapped[dict] = mapped_column(JSONB, default=dict)
    relationships: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
