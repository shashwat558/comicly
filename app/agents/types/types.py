from typing import Any, Dict, List, Optional, TypedDict
import datetime

class ReaderOutput(TypedDict):
    summary: str
    scene: str
    key_visuals: List[str]
    entities: List[str]
    emotions: str
    actions:  List[str]
    dialogue_summary: str
    themes: List[str]
    tension_level: float

class DirectorOutput(TypedDict):
    images_prompt: str
class StorySummary(TypedDict):
    summary: str
    current: str
    tone: str
    active_threads: List[str]

class ArtistOutput(TypedDict):
    image_url: str
class IndividualCharacterSummary(TypedDict):
    appearance: str
    traits: List[str]
    status: str
    emotion: str

CharactersSummary = Dict[str, IndividualCharacterSummary]
    
class VisualStyle(TypedDict):
    art_style: str
    lighting: str
    palette: List[str]
    realism: str
    
class IndividualCharacterRelationship(TypedDict):
    trust: float
    last_interaction: str
    mood: str
    

Relationships = Dict[str, IndividualCharacterRelationship]
    
class SystemMeta(TypedDict):
    last_image_url: str
    page_number: int
    timestamp: datetime
    last_updated_by: str
class MemoryAgentOutput(TypedDict):
    story: StorySummary
    characters: CharactersSummary
    visual_style: VisualStyle
    relationships: Relationships
    meta: SystemMeta
    

class AgentState(TypedDict):
    page_text: Optional[str]
    page_number: int
    prev_image_url: Optional[str]
    director_output: Optional[DirectorOutput]
    current_image_url: Optional[str]
    reader_output: Optional[ReaderOutput]
    artist_output: Optional[ArtistOutput]
    memory: Optional[MemoryAgentOutput]
    visual_prompt: Optional[str]
    image_metadata: Optional[Dict[str, Any]]
    