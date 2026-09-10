from langchain.agents import create_agent

from app.agents.io import MemoryOutput
from app.agents.llm import text_llm
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
    agent = create_agent(model=text_llm(0.3), response_format=MemoryOutput)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("Memory agent returned no structured output")
    data = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
    return {
        **state,
        "updated_story": data.get("story", state.get("story", {})),
        "updated_relationships": data.get("relationships", state.get("relationships", {})),
        "updated_characters": data.get("characters", []),
    }
