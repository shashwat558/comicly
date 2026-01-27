from app.agents.types.types import AgentState
def artist_agent(state: AgentState) -> AgentState:
    """This agent will generate an image based on the director agent's output
        Args:
            state (AgentState): Current state of the agent
        Returns:
            AgentState: Updated state with artist output
    """
    director_output = state["director_output"];
    prev_image_url = state["prev_image_url"];
    
    
    
            
                