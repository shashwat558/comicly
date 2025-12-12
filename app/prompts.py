

def build_reader_prompt(story, characters, relationships, page_text):
    return f"""
       You are a literary analyst and story interpreter.
       Your goal is to understand a book page in context of the ongoing story.
       Read the current page carefully and summarize what is happening, who is involved, and what emotions are expressed.
       
       previously in the story: {story.summary}
       Active thread: {story.active_threads}
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

