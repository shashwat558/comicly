from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    book_id: str
    page_no: int
    page_text: str
    style_lock: dict[str, Any]
    characters: list[dict[str, Any]]
    story: dict[str, Any]
    relationships: dict[str, Any]
    prev_frame_urls: list[str]
    char_ref_urls: list[str]
    seed: int
    reader_out: dict[str, Any]
    director_out: dict[str, Any]
    image_bytes: bytes
    image_key: str
    image_url: str
    updated_story: dict[str, Any]
    updated_relationships: dict[str, Any]
    updated_characters: list[dict[str, Any]]
    job_id: str
    request_id: str
