from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings


def text_llm(temperature: float = 0.3):
    s = get_settings()
    if not s.google_api_key or s.google_api_key == "changeme":
        raise RuntimeError("GOOGLE_API_KEY is not configured")
    return ChatGoogleGenerativeAI(
        model=s.gemini_text_model,
        temperature=temperature,
        max_retries=2,
        google_api_key=s.google_api_key,
    )


def invoke_structured(agent, prompt: str) -> dict:
    """Invoke a create_agent structured-output agent with tenacity retries."""

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
    def _call():
        return agent.invoke({"messages": [{"role": "user", "content": prompt}]})

    result = _call()
    structured = result.get("structured_response")
    if structured is None:
        raise RuntimeError("Agent returned no structured output")
    return structured.model_dump() if hasattr(structured, "model_dump") else dict(structured)
