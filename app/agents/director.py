from langchain.agents import create_agent

from app.agents.io import DirectorOutput
from app.agents.llm import text_llm
from app.agents.prompts import build_director_prompt
from app.agents.state import AgentState


def director_node(state: AgentState) -> AgentState:
    prompt = build_director_prompt(
        reader=state.get("reader_out", {}),
        style=state.get("style_lock", {}),
        characters=state.get("characters", []),
        page_no=state.get("page_no", 1),
    )
    agent = create_agent(model=text_llm(0.5), response_format=DirectorOutput)
    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("Director agent returned no structured output")
    data = structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)

    # keep the seed inside int32 range, postgres rejects anything bigger
    anchor = int(state.get("style_lock", {}).get("seed_anchor", 123456))
    data["seed"] = (anchor * 7919 + int(state.get("page_no", 1)) * 104729) % 2000000000
    return {**state, "director_out": data, "seed": data["seed"]}
