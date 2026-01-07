from app.agents.types.types import AgentState
from app.prompts import build_director_prompt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from app.schemas import DirectorOutputSchema
from dotenv import load_dotenv;
import os
load_dotenv();
gemini_api_key = os.getenv("GOOGLE_API_KEY");
def director_agent(state: AgentState) -> AgentState:
    """This agent will generate the prompt for generating an image based on reader agent's output 

    Args:
        state (AgentState): Current state of the agent  

    Returns:
        AgentState: Updated state with director output
    """
    
    reader_output = state["reader_output"]
    page_number = state["page_number"]

    prompt = ""
    if page_number == 1:
        prompt = build_director_prompt(reader_output, state["memory"]["visual_style"], page_number);
    else:
        prompt = build_director_prompt(reader_output, state["memory"]["visual_style"],["visual_style"], page_number);
    
    model = ChatGoogleGenerativeAI(
      model="gemini-2.5-flash",
      temperature=1.0,
      max_tokens=None,
      timeout=None,
      max_retries=2,
    )
    
    agent = create_agent(
        model=model,
        response_format=DirectorOutputSchema
    )   
    
    result = agent.invoke({
        "messages": [{"role": "user", "content": prompt}]
    });
    
    state["director_output"] = result["structured_output"];
    return state;