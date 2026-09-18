"""
src/features/study_twin.py
"Study Twin" — simulates how a top-scoring student would approach a topic.
"""
from __future__ import annotations

from typing import List

from src.document_ingestion import retrieve_relevant_chunks
from src.models import Chunk

_TWIN_SYSTEM = """You are "Alex", a student who consistently scores 100% in every exam.
You are explaining to a friend exactly how YOU would master the given topic.
Your advice must be:
1. Specific to the notes provided — not generic study tips.
2. Structured as a step-by-step study plan.
3. Include memory tricks, mnemonics, or analogies where useful.
4. Highlight the most likely exam questions for this topic.
5. End with a "Quick Revision Checklist" of 5 bullet points.

Be warm, confident, and specific. Do NOT give generic advice.
"""


def generate_study_twin(
    topic: str,
    all_chunks: List[Chunk],
    watsonx_client,
) -> str:
    """
    Generate a "Study Twin" persona response explaining how to master a topic.

    Args:
        topic: The topic to master.
        all_chunks: All chunks from uploaded documents.
        watsonx_client: WatsonxClient instance.

    Returns:
        Markdown-formatted study plan from the "topper" persona.
    """
    relevant = retrieve_relevant_chunks(topic, all_chunks, top_k=5)
    if not relevant:
        relevant = all_chunks[:5]

    context = "\n\n---\n\n".join(
        f"[{chunk.section_heading}]\n{chunk.content[:600]}"
        for chunk in relevant
    )

    messages = [
        {"role": "system", "content": _TWIN_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\n"
                f"Here are the notes I have:\n\n{context}\n\n"
                "How would you master this topic? Give me your full study plan."
            ),
        },
    ]

    response = watsonx_client.chat(messages)
    return f"## 🎓 Study Twin: How Alex Would Master *{topic}*\n\n{response}"
