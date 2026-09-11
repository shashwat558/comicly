import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StyleLock(BaseModel):
    art_style: str = "neo-noir cinematic"
    lighting: str = "high-contrast, rim and neon"
    palette: list[str] = Field(default_factory=lambda: ["#0b0f1a", "#ff2d95", "#00e6a8"])
    realism: str = "stylized"
    seed_anchor: int = 123456
    rendering_mode: str = "single cinematic frame, no text, no speech bubbles"


class BookListItem(BaseModel):
    id: uuid.UUID
    title: str
    author: str
    total_pages: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PageOut(BaseModel):
    page_no: int
    text: str
    tokens: int
    pdf_page: int | None = None

    model_config = {"from_attributes": True}


class CharacterOut(BaseModel):
    name: str
    appearance: str
    traits: list[str] = []
    visual_anchors: list[str] = []
    reference_image_url: str | None = None
    first_page: int = 1
    last_seen_page: int = 1

    model_config = {"from_attributes": True}


class FrameOut(BaseModel):
    page_no: int
    image_url: str | None = None
    status: str = "done"
    seed: int | None = None
    reader_out: dict | None = None
    director_out: dict | None = None

    model_config = {"from_attributes": True}


class BookDetail(BaseModel):
    id: uuid.UUID
    title: str
    author: str
    total_pages: int
    status: str
    style_lock: StyleLock | None = None
    kind: str = "txt"
    has_source: bool = False

    model_config = {"from_attributes": True}
