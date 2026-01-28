

def build_reader_prompt(story, characters, relationships, page_text):
    return f"""
       You are a literary analyst and story interpreter.
       Your goal is to understand a book page in context of the ongoing story.
       Read the current page carefully and summarize what is happening, who is involved, and what emotions are expressed.
       
       previously in the story: {story['summary']}
       Active thread: {story['active_threads']}
       known characters: {characters}
       Key relationships: {relationships}
       current_page: {page_text}
       
       Instructions:

       Identify key events and describe them briefly.

       Describe the main scene or setting in one sentence.

       List important visual cues (objects, atmosphere, colors, environment).

       List all named or implied entities.

      Describe the dominant emotional tone (fear, joy, tension, calm).

"""

def build_director_prompt(reader_output, visual_style, page_number):
    if page_number == 1:
        style_instructions = f"""
        You are a film director creating the opening shot of a visual story.

        Based on the story understanding below, describe a single cinematic scene that introduces the world and characters.

        Focus on:

        atmosphere and mood

        spatial composition

        character presence and body language

        lighting and environment

        Do not assume an established art style.
        Do not reference any previous images.
        Do not explain the story — only describe what should be drawn.

        Story context:
        {reader_output.summary}

        Scene setting:
        {reader_output.scene}

        Characters present:
        {reader_output.entities}

        Emotional tone:
        {reader_output.emotions}
        
        Actions:
        {reader_output.actions}

        Key visual elements:
        {reader_output.key_visuals}

        Write one concise but vivid visual description suitable for an image generation model.
                """
        return style_instructions
    else:
        style_instructions = f"""
        You are a film director continuing a visual story.

        Describe the next scene as a continuation of the previous image, maintaining strict visual consistency.

        The overall visual style of the story is already established.
        You must apply it, not redefine it.

        Established visual style (for consistency):

        Art style: {visual_style["art_style"]}

        Lighting: {visual_style["lighting"]}

        Color palette: {visual_style["palette"]}  
        Realism level: {visual_style["realism"]}

        Focus on:

        what has changed since the last scene

        character movement, posture, or expression

        evolving mood within the same style

        cinematic framing

        Do not introduce a new art style.
        Do not restate or modify the visual style.
        Do not explain the story.

        Story context:
        {reader_output.summary}

        Scene setting:
        {reader_output.scene}

        Characters present:
        {reader_output.entities}

        Emotional tone:
        {reader_output.emotions}

        Key visual elements:
        {reader_output.key_visuals}

        Write one concise but vivid visual description suitable for an image generation model.
                """
        return style_instructions


def build_artist_prompt(director_output, visual_style, prev_image_url=None):
    base_prompt = f"""
You are a skilled artist translating a director's vision into a compelling image.

Based on the director's detailed scene description below, create an image that captures the intended mood, composition, and visual elements.

Director's scene description:
{director_output.image_prompt}

Established visual style (for consistency):
- Art style: {visual_style["art_style"]}
- Lighting: {visual_style["lighting"]}
- Color palette: {visual_style["palette"]}
- Realism level: {visual_style["realism"]}

Instructions:

1. Ensure the new image reflects the director's vision accurately.
2. Maintain visual consistency with the previous image in terms of character appearance, setting, and style.
3. Focus on key elements highlighted by the director.
4. Create a cohesive scene that flows naturally from the previous frame.
5. Pay attention to character positioning, expressions, and the overall narrative flow.
6. Ensure lighting and mood align with the established visual style.
"""
    
    if prev_image_url:
        base_prompt += f"\nReference the previous image above for visual continuity and style consistency."
    
    return base_prompt