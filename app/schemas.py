from pydantic import BaseModel, Field
from typing import List
class ReaderOutputSchema(BaseModel):
    """
    Summary of current page of the story
    """
    summary: str = Field(description="The full summary of the text")
    scene: str = Field(description="location/setting")
    key_visuals: List[str] = Field(description="Concrete visual elements")
    entities: List[str] = Field(description="Characters / objects mentioned")
    emotions: str = Field(description="Dominant tone of the page")
    actions: List[str] = Field(description="Verbs / events (what character did)")
    dialogue_summary: str = Field(description="Key speech exchanges or quotes")
    themes: List[str] = Field(description="Underlying ideas (love, fear, betrayal)")
    tension_level: float = Field(description="0-1 numeric measure of drama and intensity")
    
    