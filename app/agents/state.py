from typing import Any, Literal, TypedDict

QualityMode = Literal["draft", "pro", "auto"]


class AgentState(TypedDict, total=False):
    book_id: str
    page_no: int
    page_text: str
    style_lock: dict[str, Any]

    style_bible: dict[str, Any]
    style_ref_urls: list[str]
    characters: list[dict[str, Any]]
    story: dict[str, Any]
    relationships: dict[str, Any]
    prev_frame_urls: list[str]
    char_ref_urls: list[str]
    seed: int

    quality: QualityMode
    panels: int

    reader_out: dict[str, Any]
    director_out: dict[str, Any]

    casting_out: list[dict[str, Any]]

    draft_image_bytes: bytes
    draft_image_key: str
    draft_image_url: str

    critic_out: dict[str, Any]
    drift_score: float
    critic_attempt: int
    critic_passed: bool
    critic_flagged: bool
    fix_notes: str

    hero_image_url: str
    hero_image_key: str
    pro_calls_used: int
    image_bytes: bytes
    image_key: str
    image_url: str
    quality_used: str
    retry_count: int
    panel_layout: dict[str, Any]
    updated_story: dict[str, Any]
    updated_relationships: dict[str, Any]
    updated_characters: list[dict[str, Any]]
    job_id: str
    request_id: str
