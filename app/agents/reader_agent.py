from app.agents.types import AgentState
from prompts import build_reader_prompt
from langchain.agents import create_agent
from schemas import ReaderOutputSchema
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv;
import os


load_dotenv();

gemini_api_key = os.getenv("GOOGLE_API_KEY");
print(gemini_api_key)
def reader_agent(state: AgentState) -> AgentState:
    """_summary_
       This agent reads the text and extract different key points for the director agent

    Args:
        state (AgentState): For getting state information such as page_text, story, characters etc. 

    Returns:
        AgentState: Returns summary, scene, key_visuals etc.
    """
    page_number = state['page_number']  
    story = state['memory_agent_output']['story']
    characters = state['memory_agent_output']['characters']
    relationships = state['memory_agent_output']['relationships']
    page_text = state['page_text']

    prompt = build_reader_prompt(story=story, characters=characters, relationships=relationships, page_text=page_text)
    print(prompt);
    
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
    })
    
    print(result)
    
    print(result["structured_response"])
    

