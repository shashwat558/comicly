
from langgraph.graph import StateGraph , END

from app.agents.reader_agent import reader_agent
from app.agents.types.types import AgentState


 
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


