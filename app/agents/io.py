from typing import Literal

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


    resolved_characters: list[str] = Field(
        default_factory=list, description="Canonical character names present on this page"
    )
    pronoun_map: dict[str, str] = Field(
        default_factory=dict, description="Raw pronoun/mention -> canonical character name"
    )


class Panel(BaseModel):
    index: int = Field(description="1-based panel number on the page")
    prompt: str = Field(description="Vivid drawable description for THIS panel only")
    camera: str = Field(default="cinematic medium shot", description="Camera angle/framing")
    dialogue: str = Field(default="", description="Dialogue/narration placed in this panel, if any")
    characters: list[str] = Field(default_factory=list, description="Canonical names in this panel")


class DirectorOutput(BaseModel):
    image_prompt: str = Field(description="Vivid drawable scene description, no story explanation")
    negatives: str = Field(default="text, words, letters, speech bubbles, watermark, blurry, deformed hands")
    framing: str = Field(default="cinematic wide shot")
    seed: int = Field(default=0)

    panels: list[Panel] = Field(default_factory=list)
    panel_count: int = Field(default=1, ge=1, le=4)
    layout: str = Field(default="single", description="single | grid-2 | grid-4 | vertical-strip")


class CriticOutput(BaseModel):
    identity_match: float = Field(ge=0, le=1, description="Faces/outfits match character sheets")
    style_match: float = Field(ge=0, le=1, description="Palette/lighting match style bible")
    prompt_match: float = Field(ge=0, le=1, description="Image shows what the director asked for")
    drift_score: float = Field(ge=0, le=1, description="1 - min(identity, style, prompt); higher = more drift")
    passed: bool = Field(description="True when all scores >= threshold")
    fix_notes: str = Field(default="", description="Targeted fix when failed, e.g. hair drifted purple->black")
    flagged: bool = Field(default=False, description="True when accepted despite failing after max retries")


class CharacterDelta(BaseModel):
    name: str
    appearance: str = ""
    traits: list[str] = Field(default_factory=list)
    visual_anchors: list[str] = Field(default_factory=list)


class MemoryOutput(BaseModel):
    story: dict = Field(default_factory=dict)
    relationships: dict = Field(default_factory=dict)
    characters: list[CharacterDelta] = Field(default_factory=list)


class CastingSheet(BaseModel):
    name: str
    appearance: str = ""
    visual_anchors: list[str] = Field(default_factory=list)
    palette: list[str] = Field(default_factory=list)
    is_new: bool = Field(default=True, description="True when this page introduces the character")


class StyleBible(BaseModel):
    art_style: str = ""
    lighting: str = ""
    palette: list[str] = Field(default_factory=list)
    realism: str = "stylized"
    rendering_mode: str = ""
    seed_anchor: int = 123456
    notes: str = Field(default="", description="Extra locked direction from page 1")


QualityMode = Literal["draft", "pro", "auto"]
