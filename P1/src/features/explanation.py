"""
src/features/explanation.py
Persona-based "Explain Like I'm..." feature.
"""
from __future__ import annotations

from typing import List

from src.document_ingestion import retrieve_relevant_chunks
from src.exceptions import WatsonxAPIError
from src.models import Chunk
from src.validation import ALLOWED_PERSONAS

_PERSONA_SYSTEM_PROMPTS: dict = {
    "Professor": (
        "You are a university professor explaining a topic to your students. "
        "Be clear, structured, and use academic language. "
        "Use bullet points and examples from real life."
    ),
    "Grandma": (
        "You are a kind, wise grandma explaining something to your grandchild. "
        "Use very simple words, homely analogies (cooking, gardening, family stories), "
        "and a warm, gentle tone. Avoid jargon completely."
    ),
    "Cricket Commentator": (
        "You are an enthusiastic cricket commentator explaining a concept as if it were "
        "a cricket match. Use cricket analogies (batting, bowling, wickets, runs, innings). "
        "Be energetic and exciting!"
    ),
    "Movie Dialogue": (
        "Explain the concept entirely through a dramatic movie dialogue between two "
        "characters. Use vivid, punchy lines and make it entertaining while being accurate."
    ),
    "ELI5 (Explain Like I'm 5)": (
        "You are explaining to a 5-year-old child. Use the simplest possible words, "
        "very short sentences, and fun comparisons (toys, animals, games). "
        "No technical terms whatsoever."
    ),
    "Sherlock Holmes": (
        "You are Sherlock Holmes deducing and explaining a concept through logical "
        "deduction, observations, and dramatic revelations. Say 'Elementary!' when "
        "something is obvious. Be sharp, witty, and analytical."
    ),
    "Sports Coach": (
        "You are an energetic sports coach motivating a team while teaching a concept. "
        "Use sports metaphors, keep it upbeat, and end with a rallying call."
    ),
}

_GROUNDING_SUFFIX = (
    "\n\nIMPORTANT: Answer ONLY from the provided notes below. "
    "Do not add information that is not in the notes. "
    "If the topic is not in the notes, say so clearly."
)


def explain_topic(
    topic: str,
    persona: str,
    chunks: List[Chunk],
    watsonx_client,
) -> str:
    """
    Generate a persona-flavoured explanation of `topic` grounded in `chunks`.

    Args:
        topic: The concept or topic to explain.
        persona: One of ALLOWED_PERSONAS.
        chunks: Pre-retrieved relevant chunks (or all chunks if not pre-filtered).
        watsonx_client: A WatsonxClient instance.

    Returns:
        The explanation as a markdown string.

    Raises:
        WatsonxAPIError: on LLM failure.
        ValueError: if persona is invalid.
    """
    if persona not in ALLOWED_PERSONAS:
        raise ValueError(f"Unknown persona: {persona}")

    # Retrieve the most relevant chunks for the topic
    relevant = retrieve_relevant_chunks(topic, chunks, top_k=4)
    if not relevant:
        relevant = chunks[:3]  # Fall back to first 3 chunks if no match

    context = _build_context(relevant)
    system_prompt = _PERSONA_SYSTEM_PROMPTS[persona] + _GROUNDING_SUFFIX

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Please explain the following topic: **{topic}**\n\n"
                f"Here are the relevant notes:\n\n{context}"
            ),
        },
    ]

    return watsonx_client.chat(messages)


def _build_context(chunks: List[Chunk]) -> str:
    parts = []
    for chunk in chunks:
        label = f"[Page {chunk.page_number} | {chunk.section_heading}]"
        parts.append(f"{label}\n{chunk.content}")
    return "\n\n---\n\n".join(parts)
