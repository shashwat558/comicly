
from copy import deepcopy

from langgraph.graph import StateGraph

from app.agents.reader_agent import reader_agent
from app.agents.types.types import AgentState


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("reader_agent", reader_agent)
    graph.set_entry_point("reader_agent")
    return graph.compile()


graph_app = build_graph()

_DEFAULT_STATE: AgentState = {
    "page_number": 1,
    "page_text": "Panel 1: Alex arrives at the neon-lit alley and notices a mysterious shadow.",
    "prev_image_url": "https://example.com/images/page0.png",
    "current_image_url": "https://example.com/images/page1.png",
    "reader_output": {
        "summary": "A tense opening: Alex discovers evidence of a missing person.",
        "highlights": ["Alex", "mysterious shadow", "neon alley"],
        "tone": "suspenseful",
    },
    "visual_prompt": "Cinematic alley at dusk, rain-slick cobbles, neon signs, dramatic rim lighting on the protagonist.",
    "image_metadata": {
        "width": 2048,
        "height": 1152,
        "format": "png",
        "camera": "35mm",
        "fps": None,
    },
    "memory": {
        "story": {
            "summary": "Beginning of the story: a missing-person mystery in a neon city.",
            "current": "Alex finds a cufflink stained with red paint near the dumpster.",
            "tone": "suspenseful",
            "active_threads": ["missing_person", "old_rivalry"],
        },
        "characters": {
            "Alex": {
                "role": "protagonist",
                "age": 29,
                "description": "Weathered private investigator, quick-witted, wearing a long coat.",
                "visuals": {"hair": "short dark", "clothing": "trench coat", "palette": ["#222222", "#6ea8ff"]},
            },
            "Mira": {
                "role": "ally",
                "age": 26,
                "description": "Tech-savvy friend who feeds Alex leads.",
                "visuals": {"hair": "long purple", "clothing": "hoodie", "palette": ["#6b2b6e", "#ffd166"]},
            },
        },
        "visual_style": {
            "art_style": "neo-noir",
            "lighting": "high-contrast, rim and neon",
            "palette": ["#0b0f1a", "#ff2d95", "#00e6a8"],
            "realism": "stylized",
        },
        "relationships": {
            "Alex->Mira": "trusted_contact",
            "Alex->Unknown": "suspect",
        },
        "meta": {
            "last_image_url": "https://example.com/images/page0.png",
            "page_number": 1,
            "timestamp": "2026-01-06T12:00:00Z",
            "last_updated_by": "developer",
        },
    },
}


def get_default_state() -> AgentState:
    return deepcopy(_DEFAULT_STATE)


def run_graph(state: AgentState) -> AgentState:
    return graph_app.invoke(state)


if __name__ == "__main__":
    result = run_graph(get_default_state())
    print("Invocation result:", result)


