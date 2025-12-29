from app.agents.types import AgentState
from langgraph.graph import StateGraph , END

from reader_agent import reader_agent

 
graph = StateGraph(AgentState)
graph.add_node("reader_agent", reader_agent);

graph.set_entry_point("reader_agent")
app = graph.compile();
initial_state = {
    "page_number": 1,
    "page_text": """
    Alice walks into the abandoned library. Dust floats in the air.
    She feels a strange presence watching her.
    """,
    "memory_agent_output": {
        "story": "A mysterious journey through forgotten places",
        "characters": {
            "Alice": {
                "appearance": "Young woman with a lantern",
                "traits": ["curious", "brave"]
            }
        },
        "relationships": {
            "Alice": []
        }
    }
}

result = app.invoke(initial_state)


