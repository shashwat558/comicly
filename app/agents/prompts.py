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
Be concrete and visual. Name characters consistently.

PRONOUN RESOLUTION (required): map every pronoun or vague mention on this page
("she", "he", "they", "the detective", ...) to its canonical character name.
Return resolved_characters (canonical names present) and pronoun_map
(raw mention -> canonical name). Never draw the wrong person: when in doubt,
prefer a known character over inventing a new one, and list genuinely new
names in entities so casting can sheet them."""


def build_director_prompt(
    reader: dict,
    style: dict,
    characters: list[dict],
    page_no: int,
    panels: int = 1,
) -> str:
    resolved = reader.get("resolved_characters") or []
    pronoun_map = reader.get("pronoun_map") or {}
    base = f"""You are a film director. Write ONE drawable image prompt (no story recap).
Story: {reader.get('summary')}
Scene: {reader.get('scene')}
Entities: {reader.get('entities')}
Resolved cast on this page: {resolved}
Pronoun map: {pronoun_map}
Emotions: {reader.get('emotions')}
Actions: {reader.get('actions')}
Key visuals: {reader.get('key_visuals')}

CHARACTER LOCKS (must match exactly):
{character_block(characters)}

STYLE LOCK (do not change):
{style_block(style)}

COMIC PANELS: break this page into exactly {panels} panel(s) (1-4).
Return panels[] with index, prompt (drawable, per-panel), camera (e.g. close-up,
medium shot, wide establishing, dutch angle, over-the-shoulder), dialogue
(what text sits in that panel, may be empty), characters (canonical names in
that panel). panel_count must equal {panels}. layout: single for 1,
grid-2 for 2, vertical-strip for 3, grid-4 for 4. image_prompt stays the
full-page summary used for single-frame renders.
"""
    if page_no == 1:
        return base + "\nThis is the opening shot: establish world, cast appearance, mood. Cinematic composition."
    return base + "\nContinuation shot: same cast faces/clothes, same style. Show what changed. Cinematic framing."


def build_artist_prompt(
    director: dict,
    style: dict,
    characters: list[dict],
    fix_notes: str = "",
    is_hero: bool = False,
) -> str:
    panels = director.get("panels") or []
    panel_text = ""
    if panels:
        bits = []
        for p in panels:
            if isinstance(p, dict):
                bits.append(
                    f"Panel {p.get('index')}: {p.get('prompt')} "
                    f"[camera: {p.get('camera')}] [cast: {p.get('characters', [])}]"
                )
            else:
                bits.append(str(p))
        panel_text = "PANEL BREAKDOWN (respect framing per panel):\n" + "\n".join(bits) + "\n\n"
    fix_text = f"\nFIX NOTES FROM CRITIC (must apply): {fix_notes}\n" if fix_notes else ""
    hero_text = (
        "\nHERO PASS: studio-quality final. Refine faces, hands, lighting; "
        "keep identity and palette identical to references.\n"
        if is_hero
        else ""
    )
    return f"""Skilled illustrator. Draw exactly this scene, no text/bubbles/watermark.

SCENE: {director.get('image_prompt')}
{panel_text}FRAMING: {director.get('framing', 'cinematic wide shot')}
AVOID: {director.get('negatives', '')}
{fix_text}{hero_text}
CHARACTER LOCKS (identical faces/clothes every page):
{character_block(characters)}

STYLE LOCK:
{style_block(style)}

Keep character faces, hairstyles, clothing colors identical to references. Same palette and lighting."""


def build_memory_prompt(reader: dict, story: dict, characters: list[dict], relationships: dict, page_no: int) -> str:

    return f"""You maintain story continuity across pages. Current page no: {page_no}
Page reading: {reader}
Prior story: {story}
Prior characters: {character_block(characters)}
Prior relationships: {relationships}

Return updated story {{summary, current, tone, active_threads}}, relationships, and character deltas {{name, appearance (stable!), traits, visual_anchors (short drawable tags: hair, clothes, colors)}}.
Appearance strings must be STABLE across pages - only refine, never rename the look.
RULES:
- Only record outfit/appearance changes the story actually motivates (new scene, time skip, stated change). Otherwise keep appearance byte-identical.
- Merge resolved_characters/pronoun_map from the reader so "she" never becomes a new character.
- Keep active_threads short (<=6): close resolved threads, carry open ones."""


def build_casting_prompt(
    reader: dict, characters: list[dict], page_no: int
) -> str:
    known = ", ".join(c.get("name", "") for c in characters) or "(none yet)"
    return f"""You are a casting director for a comic adaptation. Page no: {page_no}
Page reading: {reader}
Known cast: {known}
Known sheets:
{character_block(characters)}

Decide which characters appear on THIS page and which are NEW (first appearance).
Return a list of {{name, appearance, visual_anchors, palette, is_new}}.
- is_new=true ONLY for characters never seen before (check known cast + resolved_characters).
- appearance: one stable sentence (face, hair, outfit, colors). visual_anchors: 3-6 short drawable tags.
- For returning characters set is_new=false and echo their locked appearance unchanged.
- Use resolved_characters/pronoun_map from the reader; do not invent duplicates ("the detective" == Alex)."""


def build_style_bible_prompt(reader: dict, style: dict, page_no: int) -> str:
    return f"""You lock the visual bible for the whole book from page 1. Page no: {page_no}
Opening reading: {reader}
Requested style: {style_block(style)}

Return {{art_style, lighting, palette (3-6 hex), realism, rendering_mode, seed_anchor, notes}}.
- Keep the requested style unless the page demands otherwise; make it concrete and drawable.
- notes: 1-2 sentences of locked direction (e.g. rain-slick neon noir, rim light always magenta from left).
- seed_anchor: keep the input value."""


def build_sheet_prompt(casting: dict, style: dict) -> str:
    anchors = ", ".join(casting.get("visual_anchors", []) or [])
    palette = casting.get("palette") or style.get("palette")
    return f"""Character reference sheet, single image, plain neutral background, no text, no watermark.
Character: {casting.get('name')}: {casting.get('appearance')} [{anchors}]
Palette swatches along the bottom: {palette}
STYLE: {style.get('art_style')}, {style.get('lighting')}, {style.get('realism')}
Show: front portrait, 3/4 headshot, full outfit. Identical face, hair, clothing colors across views. Studio turnaround."""


def build_critic_prompt(
    reader: dict, director: dict, characters: list[dict], style: dict
) -> str:
    return f"""You are a strict visual-continuity judge for comic frames. Score the DRAFT image (attached) 0-1 on:
- identity_match: faces/hairstyles/outfits match CHARACTER LOCKS + sheets. Any drift (hair color, outfit swap, wrong person) lowers this hard.
- style_match: palette/lighting/art style match STYLE LOCK.
- prompt_match: image shows SCENE + panel breakdown (right cast, action, setting).
Page reading: {reader}
Director asked: {director.get('image_prompt')}
Panels: {director.get('panels', [])}
CHARACTER LOCKS:
{character_block(characters)}
STYLE LOCK:
{style_block(style)}
Return identity_match, style_match, prompt_match, drift_score (= 1 - min of the three),
passed (all >= threshold), fix_notes (one concrete drawable fix when failed, e.g.
"Mira's hair drifted purple->black, restore long purple + hoodie #6b2b6e"), flagged=false.
Be strict on identity, lenient on background detail."""
