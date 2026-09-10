from langchain.agents import create_agent

from app.agents.io import ReaderOutput
from app.agents.llm import text_llm
from app.agents.prompts import build_reader_prompt
from app.agents.state import AgentState


def reader_node(state: AgentState) -> AgentState:
    prompt = build_reader_prompt(
        story=state.get("story", {}),
        characters=state.get("characters", []),
        relationships=state.get("relationships", {}),
        page_text=state.get("page_text", ""),
    )
    # low temp so the same page reads the same way every run
    agent = create_agent(model=text_llm(0.3), response_format=ReaderOutput)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("Reader agent returned no structured output")
    data = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
    return {**state, "reader_out": data}
