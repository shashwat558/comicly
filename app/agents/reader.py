from langchain.agents import create_agent
from pydantic import BaseModel, Field

from app.agents.io import ReaderOutput
from app.agents.llm import invoke_structured, text_llm
from app.agents.prompts import build_reader_prompt
from app.agents.state import AgentState


def reader_node(state: AgentState) -> AgentState:
    prompt = build_reader_prompt(
        story=state.get("story", {}),
        characters=state.get("characters", []),
        relationships=state.get("relationships", {}),
        page_text=state.get("page_text", ""),
    )


    agent = create_agent(model=text_llm(0.0), response_format=ReaderOutput)
    data = invoke_structured(agent, prompt)
    data.setdefault("resolved_characters", [])
    data.setdefault("pronoun_map", {})

    ents = list(data.get("entities", []) or [])
    for name in data.get("resolved_characters", []) or []:
        if name and name not in ents:
            ents.append(name)
    data["entities"] = ents
    return {**state, "reader_out": data}


class _ReaderCompat(BaseModel):
    """Loose fallback, never used for output - documents required keys."""

    summary: str = ""
    scene: str = ""
    key_visuals: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
