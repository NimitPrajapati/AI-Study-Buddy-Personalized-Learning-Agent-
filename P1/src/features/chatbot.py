"""
src/features/chatbot.py
RAG-based doubt-solving chatbot with mandatory source citations.
"""
from __future__ import annotations

from typing import List, Tuple

from src.document_ingestion import retrieve_relevant_chunks
from src.exceptions import OutOfScopeQueryError, WatsonxAPIError
from src.models import Chunk

_SYSTEM_PROMPT = """You are a helpful study assistant. You MUST answer ONLY from the provided
reference notes. Do NOT use any external knowledge.

Rules:
1. Every factual claim MUST be supported by the provided notes.
2. At the end of your answer, always include a "**Sources:**" line listing the page numbers
   and section headings you used (e.g., "**Sources:** Page 3 | Section: Photosynthesis").
3. If the question cannot be answered from the provided notes, reply with exactly:
   "OUT_OF_SCOPE: This question is outside the uploaded notes. Please ask something
   covered in your material."
4. Be concise and clear.
"""

_OUT_OF_SCOPE_MARKER = "OUT_OF_SCOPE:"
_MIN_RETRIEVAL_SCORE = 0.02


def answer_doubt(
    query: str,
    all_chunks: List[Chunk],
    chat_history: List[dict],
    watsonx_client,
    top_k: int = 3,
) -> Tuple[str, List[Chunk]]:
    """
    Answer a doubt question using RAG over the uploaded chunks.

    Args:
        query: The student's question.
        all_chunks: All chunks from the uploaded document(s).
        chat_history: Previous conversation turns (list of role/content dicts).
        watsonx_client: WatsonxClient instance.
        top_k: Number of chunks to inject as context.

    Returns:
        (answer_text, source_chunks) tuple.

    Raises:
        OutOfScopeQueryError: if the query is outside the notes.
        WatsonxAPIError: on LLM failure.
    """
    relevant = retrieve_relevant_chunks(query, all_chunks, top_k=top_k, min_score=_MIN_RETRIEVAL_SCORE)

    if not relevant:
        raise OutOfScopeQueryError(
            "This question is outside the uploaded notes. "
            "Please ask something covered in your material."
        )

    context = _build_rag_context(relevant)

    # Build message list: system + history + current query with context
    messages: List[dict] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    # Include last 6 conversation turns for memory (3 user + 3 assistant)
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history
    messages.extend(recent_history)

    messages.append({
        "role": "user",
        "content": (
            f"Question: {query}\n\n"
            f"Reference Notes:\n{context}"
        ),
    })

    raw_answer = watsonx_client.chat(messages)

    # Check if model signalled out-of-scope
    if raw_answer.strip().startswith(_OUT_OF_SCOPE_MARKER):
        raise OutOfScopeQueryError(
            "This question is outside the uploaded notes. "
            "Please ask something covered in your material."
        )

    return raw_answer, relevant


def format_citation(chunks: List[Chunk]) -> str:
    """Return a formatted citation string from a list of source chunks."""
    parts = []
    seen = set()
    for chunk in chunks:
        key = (chunk.page_number, chunk.section_heading)
        if key not in seen:
            seen.add(key)
            if chunk.page_number > 0:
                parts.append(f"Page {chunk.page_number} | Section: {chunk.section_heading}")
            else:
                parts.append(f"Section: {chunk.section_heading}")
    return "**Sources:** " + " · ".join(parts) if parts else ""


def _build_rag_context(chunks: List[Chunk]) -> str:
    parts = []
    for chunk in chunks:
        label = f"[Page {chunk.page_number} | {chunk.section_heading}]"
        parts.append(f"{label}\n{chunk.content[:800]}")
    return "\n\n---\n\n".join(parts)
