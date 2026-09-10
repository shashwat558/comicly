from typing import Any


def character_block(characters: list[dict[str, Any]]) -> str:
    if not characters:
        return "No established characters yet. Identify any new characters precisely."
    lines = []
    for c in characters:
        anchors = ", ".join(c.get("visual_anchors", []) or []) or c.get("appearance", "")
        lines.append(f"- {c.get('name')}: {anchors} (traits: {', '.join(c.get('traits', []))})")
    return "\n".join(lines)


def style_block(style: dict[str, Any]) -> str:
    return (
        f"Art style: {style.get('art_style')}\n"
        f"Lighting: {style.get('lighting')}\n"
        f"Color palette: {style.get('palette')}\n"
        f"Realism: {style.get('realism')}\n"
        f"Rendering: {style.get('rendering_mode')}"
    )


def build_reader_prompt(story: dict, characters: list[dict], relationships: dict, page_text: str) -> str:
    return f"""You are a literary analyst for a visual adaptation.
Previously: {story.get('summary', '')}
Active threads: {story.get('active_threads', [])}
Known characters:
{character_block(characters)}
Relationships: {relationships}

CURRENT PAGE:
{page_text}

Extract: summary, scene (1 sentence), key_visuals (concrete drawable nouns), entities, emotions, actions, dialogue_summary, themes, tension_level 0-1.
Be concrete and visual. Name characters consistently."""


def build_director_prompt(reader: dict, style: dict, characters: list[dict], page_no: int) -> str:
    base = f"""You are a film director. Write ONE drawable image prompt (no story recap).
Story: {reader.get('summary')}
Scene: {reader.get('scene')}
Entities: {reader.get('entities')}
Emotions: {reader.get('emotions')}
Actions: {reader.get('actions')}
Key visuals: {reader.get('key_visuals')}

CHARACTER LOCKS (must match exactly):
{character_block(characters)}

STYLE LOCK (do not change):
{style_block(style)}
"""
    if page_no == 1:
        return base + "\nThis is the opening shot: establish world, cast appearance, mood. Cinematic composition."
    return base + "\nContinuation shot: same cast faces/clothes, same style. Show what changed. Cinematic framing."


def build_artist_prompt(director: dict, style: dict, characters: list[dict]) -> str:
    return f"""Skilled illustrator. Draw exactly this scene, no text/bubbles/watermark.

SCENE: {director.get('image_prompt')}
FRAMING: {director.get('framing', 'cinematic wide shot')}
AVOID: {director.get('negatives', '')}

CHARACTER LOCKS (identical faces/clothes every page):
{character_block(characters)}

STYLE LOCK:
{style_block(style)}

Keep character faces, hairstyles, clothing colors identical to references. Same palette and lighting."""


def build_memory_prompt(reader: dict, story: dict, characters: list[dict], relationships: dict, page_no: int) -> str:
    # appearances must stay put here or faces drift between pages
    return f"""You maintain story continuity across pages. Current page no: {page_no}
Page reading: {reader}
Prior story: {story}
Prior characters: {character_block(characters)}
Prior relationships: {relationships}

Return updated story {{summary, current, tone, active_threads}}, relationships, and character deltas {{name, appearance (stable!), traits, visual_anchors (short drawable tags: hair, clothes, colors)}}.
Appearance strings must be STABLE across pages - only refine, never rename the look."""
