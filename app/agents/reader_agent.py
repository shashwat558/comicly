import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI

from app.agents.types.types import AgentState
from app.prompts import build_reader_prompt
from app.schemas import ReaderOutputSchema

load_dotenv()

gemini_api_key = os.getenv("GOOGLE_API_KEY")
def reader_agent(state: AgentState) -> AgentState:
    page_number = state['page_number']
    if page_number == 1:
        story = {
            "summary": "",
            "current": "",
            "tone": "",
            "active_threads": []
        }
        characters = {}
        relationships = {}
        state['memory']['story'] = story
        state['memory']['characters'] = characters
        state['memory']['relationships'] = relationships

    story = state['memory']['story']
    characters = state['memory']['characters']
    relationships = state['memory']['relationships']
    page_text = state['page_text']

    prompt = build_reader_prompt(story=story, characters=characters, relationships=relationships, page_text=page_text)
    print(prompt)

    model = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash",
      temperature=1.0,
      max_tokens=None,
      timeout=None,
      max_retries=2,
    )
    agent = create_agent(
        model=model,
        response_format=ReaderOutputSchema
    )

    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    });

    state['reader_output'] = result["structured_response"]
    print("Reader Agent Output:", state['reader_output'])
    print("-----")
    return state


