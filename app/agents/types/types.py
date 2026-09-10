import datetime
from typing import Any, TypedDict


class ReaderOutput(TypedDict):
    summary: str
    scene: str
    key_visuals: list[str]
    entities: list[str]
    emotions: str
    actions:  list[str]
    dialogue_summary: str
    themes: list[str]
    tension_level: float

class DirectorOutput(TypedDict):
    images_prompt: str
class StorySummary(TypedDict):
    summary: str
    current: str
    tone: str
    active_threads: list[str]

class ArtistOutput(TypedDict):
    image_url: str
class IndividualCharacterSummary(TypedDict):
    appearance: str
    traits: list[str]
    visual_anchor_tokens: list[str]
    status: str
    emotion: str
    first_appearance_page: 1
    last_seen_page: int

CharactersSummary = dict[str, IndividualCharacterSummary]
    
class VisualStyle(TypedDict):
    art_style: str
    lighting: str
    palette: list[str]
    realism: str
    seed_anchor: int
    rendering_mode: str
    
class IndividualCharacterRelationship(TypedDict):
    trust: float
    last_interaction: str
    mood: str
    tension_level: float
    

Relationships = dict[str, IndividualCharacterRelationship]
    
class SystemMeta(TypedDict):
    last_image_url: str
    page_number: int
    book_id: str
    memory_version: int
    checksum: str
    timestamp: datetime
    last_updated_by: str
class MemoryAgentOutput(TypedDict):
    story: StorySummary
    characters: CharactersSummary
    visual_style: VisualStyle
    relationships: Relationships
    meta: SystemMeta
    
class BookMeta(TypedDict):
    title: str
    author: str
    publication_date: str
    isbn: str

class AgentState(TypedDict):
    page_text: str | None
    page_number: int
    prev_image_url: str | None
    director_output: DirectorOutput | None
    current_image_url: str | None
    reader_output: ReaderOutput | None
    artist_output: ArtistOutput | None
    memory: MemoryAgentOutput | None
    visual_prompt: str | None
    image_metadata: dict[str, Any] | None
    book_meta: BookMeta | None
    