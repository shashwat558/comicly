from langchain_google_genai import ChatGoogleGenerativeAI

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
