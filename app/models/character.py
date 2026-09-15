import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("book_id", "name", name="uq_characters_book_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    appearance: Mapped[str] = mapped_column(String(2000), default="")
    traits: Mapped[list] = mapped_column(JSONB, default=list)

    visual_anchors: Mapped[list] = mapped_column(JSONB, default=list)
    reference_image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    reference_image_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    sheet_image_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sheet_image_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sheet_version: Mapped[int] = mapped_column(Integer, default=0)
    first_page: Mapped[int] = mapped_column(Integer, default=1)
    last_seen_page: Mapped[int] = mapped_column(Integer, default=1)

    book = relationship("Book", back_populates="characters")
