"""
src/features/story_generator.py
Converts chapter/topic content into a short story or comic-panel script.
"""
from __future__ import annotations

from typing import List

from src.document_ingestion import retrieve_relevant_chunks
from src.models import Chunk

_DISCLAIMER = (
    "\n\n---\n> ⚠️ **Disclaimer:** This narrative is based on your uploaded notes. "
    "Verify all facts before your exam."
)

_STORY_SYSTEM = """You are a creative writer who turns educational content into engaging stories.
Your job:
1. Write a short narrative story (under 400 words) that teaches the given topic/concept.
2. Every fact MUST come ONLY from the provided reference notes.
3. Use vivid characters and a simple plot to illustrate the concept.
4. End with a one-sentence moral that captures the key learning.
5. Do NOT invent facts not in the notes.
"""

_COMIC_SYSTEM = """You are a comic script writer who turns educational content into panel scripts.
Your job:
1. Format the output as numbered panels (5-8 panels).
2. Each panel has:
   - PANEL N: (scene description in one line)
   - DIALOGUE: (one character's spoken line teaching the concept)
3. Every fact MUST come ONLY from the provided reference notes.
4. Keep it engaging, visual, and educational.
5. Do NOT invent facts not in the notes.
"""


def generate_story(
    topic: str,
    style: str,
    all_chunks: List[Chunk],
    watsonx_client,
) -> str:
    """
    Generate a story or comic script from the topic using grounded notes.

    Args:
        topic: Chapter or concept to narrate.
        style: "story" or "comic".
        all_chunks: All available chunks from uploaded documents.
        watsonx_client: WatsonxClient instance.

    Returns:
        Generated narrative as a markdown string (with disclaimer).
    """
    relevant = retrieve_relevant_chunks(topic, all_chunks, top_k=5)
    if not relevant:
        relevant = all_chunks[:5]

    context = "\n\n---\n\n".join(
        f"[{chunk.section_heading}]\n{chunk.content[:700]}"
        for chunk in relevant
    )

    system_prompt = _STORY_SYSTEM if style == "story" else _COMIC_SYSTEM

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Topic / Chapter: {topic}\n\n"
                f"Reference notes:\n{context}"
            ),
        },
    ]

    result = watsonx_client.chat(messages)
    return result + _DISCLAIMER
