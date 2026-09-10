from app.agents.prompts import build_artist_prompt, build_director_prompt, character_block
from app.services.ingest import chunk_text


def test_chunk_text_respects_boundaries():
    text = "\n\n".join([f"Paragraph {i} with some story content about Alex." for i in range(20)])
    chunks = chunk_text(text, target=900, hard_max=1200)
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c.strip()) > 0


def test_character_block_stable():
    chars = [{"name": "Alex", "appearance": "short dark hair, trench coat", "traits": ["witty"], "visual_anchors": ["short dark hair", "trench coat #222"]}]
    block = character_block(chars)
    assert "Alex" in block and "trench coat" in block


def test_director_prompt_locks_style():
    reader = {"summary": "Alex enters alley", "scene": "neon alley", "entities": ["Alex"], "emotions": "tense", "actions": ["walks"], "key_visuals": ["neon"]}
    style = {"art_style": "neo-noir", "lighting": "rim", "palette": ["#000"], "realism": "stylized", "rendering_mode": "frame"}
    p1 = build_director_prompt(reader, style, [], 1)
    p2 = build_director_prompt(reader, style, [], 5)
    assert "neo-noir" in p1 and "neo-noir" in p2
    assert "opening shot" in p1.lower()
    assert "continuation" in p2.lower()


def test_artist_prompt_no_text():
    d = {"image_prompt": "alley", "framing": "wide", "negatives": "text"}
    s = {"art_style": "noir", "lighting": "x", "palette": [], "realism": "y", "rendering_mode": "z"}
    p = build_artist_prompt(d, s, [])
    assert "no text" in p.lower()
