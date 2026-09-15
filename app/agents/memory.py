from langchain.agents import create_agent

from app.agents.io import MemoryOutput
from app.agents.llm import invoke_structured, text_llm
from app.agents.prompts import build_memory_prompt
from app.agents.state import AgentState


def memory_node(state: AgentState) -> AgentState:
    prompt = build_memory_prompt(
        reader=state.get("reader_out", {}),
        story=state.get("story", {}),
        characters=state.get("characters", []),
        relationships=state.get("relationships", {}),
        page_no=state.get("page_no", 1),
    )
    agent = create_agent(model=text_llm(0.0), response_format=MemoryOutput)
    data = invoke_structured(agent, prompt)
    story = data.get("story") or state.get("story", {})

    try:
        story = dict(story)
        story["last_drift_score"] = float(state.get("drift_score", 0.0) or 0.0)
        story["last_critic_passed"] = bool(state.get("critic_passed", True))
    except Exception:
        pass
    return {
        **state,
        "updated_story": story,
        "updated_relationships": data.get("relationships", state.get("relationships", {})),
        "updated_characters": data.get("characters", []),
    }
