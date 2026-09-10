from pydantic import BaseModel, Field


class ReaderOutput(BaseModel):
    summary: str = Field(description="What happens on this page, 2-4 sentences")
    scene: str = Field(description="Location/setting in one sentence")
    key_visuals: list[str] = Field(default_factory=list, description="Concrete visual elements")
    entities: list[str] = Field(default_factory=list, description="Characters/objects mentioned")
    emotions: str = Field(default="neutral", description="Dominant emotional tone")
    actions: list[str] = Field(default_factory=list, description="What characters do")
    dialogue_summary: str = Field(default="", description="Key speech exchanges")
    themes: list[str] = Field(default_factory=list)
    tension_level: float = Field(default=0.5, ge=0, le=1)


class DirectorOutput(BaseModel):
    image_prompt: str = Field(description="Vivid drawable scene description, no story explanation")
    negatives: str = Field(default="text, words, letters, speech bubbles, watermark, blurry, deformed hands")
    framing: str = Field(default="cinematic wide shot")
    seed: int = Field(default=0)


class CharacterDelta(BaseModel):
    name: str
    appearance: str = ""
    traits: list[str] = Field(default_factory=list)
    visual_anchors: list[str] = Field(default_factory=list)


class MemoryOutput(BaseModel):
    story: dict = Field(default_factory=dict)
    relationships: dict = Field(default_factory=dict)
    characters: list[CharacterDelta] = Field(default_factory=list)
