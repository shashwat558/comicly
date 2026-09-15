from langchain.agents import create_agent

from app.agents.io import DirectorOutput
from app.agents.llm import invoke_structured, text_llm
from app.agents.prompts import build_director_prompt
from app.agents.state import AgentState

_LAYOUT_FOR_COUNT = {1: "single", 2: "grid-2", 3: "vertical-strip", 4: "grid-4"}


def _clamp_panels(raw: int | None) -> int:
    try:
        n = int(raw or 1)
    except (TypeError, ValueError):
        n = 1
    return max(1, min(4, n))


def director_node(state: AgentState) -> AgentState:
    panels = _clamp_panels(state.get("panels", 1))
    prompt = build_director_prompt(
        reader=state.get("reader_out", {}),
        style=state.get("style_lock", {}),
        characters=state.get("characters", []),
        page_no=int(state.get("page_no", 1)),
        panels=panels,
    )

    agent = create_agent(model=text_llm(0.0), response_format=DirectorOutput)
    data = invoke_structured(agent, prompt)


    anchor = int(state.get("style_lock", {}).get("seed_anchor", 123456))
    data["seed"] = (anchor * 7919 + int(state.get("page_no", 1)) * 104729) % 2000000000


    got = data.get("panels") or []
    norm: list[dict] = []
    for i in range(panels):
        if i < len(got):
            p = got[i] if isinstance(got[i], dict) else {}
            norm.append({
                "index": i + 1,
                "prompt": str(p.get("prompt") or data.get("image_prompt", "")),
                "camera": str(p.get("camera") or "cinematic medium shot"),
                "dialogue": str(p.get("dialogue") or ""),
                "characters": list(p.get("characters") or []),
            })
        else:
            norm.append({
                "index": i + 1,
                "prompt": str(data.get("image_prompt", "")),
                "camera": "cinematic medium shot",
                "dialogue": "",
                "characters": list((state.get("reader_out", {}) or {}).get("resolved_characters", []) or []),
            })
    data["panels"] = norm
    data["panel_count"] = panels
    data["layout"] = _LAYOUT_FOR_COUNT[panels]
    return {**state, "director_out": data, "seed": data["seed"], "panels": panels}
