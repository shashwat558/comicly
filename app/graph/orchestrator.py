
from langgraph.graph import StateGraph , END
from typing import TypedDict, Dict, List
import datetime
from app.agents.reader_agent import reader_agent

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

class StorySummary(TypedDict):
    summary: str
    current: str
    tone: str
    active_threads: List[str]

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
    page_text: str
    prev_image_url: str
    current_image_url: str
    reader_output: ReaderOutput
    memory_agent_output: MemoryAgentOutput
    visual_prompt: str
    image_metadata: str
    page_number: int
    memory: dict

 
graph = StateGraph(AgentState)
graph.add_node("reader_agent", reader_agent);

graph.set_entry_point("reader_agent")
app = graph.compile();
initial_state = {
    "page_number": 1,
    "page_text": "...",

    "prev_image_url": "",
    "current_image_url": "",

    "reader_output": None,
    "visual_prompt": "",
    "image_metadata": "",

    "memory": {
        "story": {
            "summary": "Beginning of the story",
            "current": "",
            "tone": "neutral",
            "active_threads": []
        },
        "characters": {},
        "visual_style": {
            "art_style": "unknown",
            "lighting": "neutral",
            "palette": [],
            "realism": "unknown"
        },
        "relationships": {},
        "meta": {
            "last_image_url": "",
            "page_number": 0,
            "timestamp": '',
            "last_updated_by": "system"
        }
    }
}


result = app.invoke(initial_state)


