"""
src/features/reverse_learning.py
Feynman-technique reverse learning: student explains → AI finds gaps → gap report.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from src.document_ingestion import retrieve_relevant_chunks
from src.exceptions import InsufficientExplanationError, WatsonxAPIError
from src.models import Chunk
from src.validation import MIN_RL_WORDS

_MIN_QUESTIONS = 2

_EVAL_SYSTEM = """You are a Socratic tutor assessing a student's understanding of a topic.
Your job is to:
1. Identify concepts that are MISSING or INCORRECT in the student's explanation
   compared to the reference notes.
2. Generate at least {min_q} targeted follow-up questions to probe those gaps.

Output format (use exactly this structure):
GAPS:
- <gap 1>
- <gap 2>
...

QUESTIONS:
1. <question 1>
2. <question 2>
...

Be encouraging but honest. Do not give the answers yet.
"""

_REPORT_SYSTEM = """You are a tutor providing a knowledge-gap feedback report.
Based on the student's original explanation, the identified gaps, and their answers
to follow-up questions, write a constructive report that:
1. Highlights what the student understood well.
2. Clearly explains each knowledge gap.
3. Provides the correct explanation for each gap from the reference notes.
4. Ends with 3 tips for the student to improve.

Be encouraging, specific, and concise.
"""

_VERBATIM_THRESHOLD = 0.85  # Similarity ratio to flag copy-paste


def check_minimum_length(text: str) -> None:
    """
    Raise InsufficientExplanationError if text has fewer than MIN_RL_WORDS words.
    """
    word_count = len(text.split())
    if word_count < MIN_RL_WORDS:
        raise InsufficientExplanationError(
            f"Please write at least {MIN_RL_WORDS} words "
            f"(you wrote {word_count}). Explain in your own words."
        )


def _check_verbatim(student_text: str, chunks: List[Chunk]) -> bool:
    """Return True if the student's text looks like a copy-paste from the notes."""
    student_words = set(student_text.lower().split())
    for chunk in chunks:
        chunk_words = set(chunk.content.lower().split())
        if not chunk_words:
            continue
        overlap = len(student_words & chunk_words) / max(len(student_words), 1)
        if overlap > _VERBATIM_THRESHOLD:
            return True
    return False


def evaluate_explanation(
    student_text: str,
    topic: str,
    all_chunks: List[Chunk],
    watsonx_client,
) -> dict:
    """
    Evaluate a student's explanation of a topic and identify knowledge gaps.

    Returns:
        dict with keys:
            - "gaps": List[str]
            - "questions": List[str]
            - "verbatim_warning": bool

    Raises:
        InsufficientExplanationError: if text is too short.
        WatsonxAPIError: on LLM failure.
    """
    check_minimum_length(student_text)

    relevant = retrieve_relevant_chunks(topic, all_chunks, top_k=4)
    if not relevant:
        relevant = all_chunks[:4]

    verbatim = _check_verbatim(student_text, relevant)

    context = "\n\n---\n\n".join(
        f"[{chunk.section_heading}]\n{chunk.content[:600]}"
        for chunk in relevant
    )

    system_prompt = _EVAL_SYSTEM.format(min_q=_MIN_QUESTIONS)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\n"
                f"Student's explanation:\n{student_text}\n\n"
                f"Reference notes:\n{context}"
            ),
        },
    ]

    raw = watsonx_client.chat(messages)
    gaps, questions = _parse_eval_output(raw)

    # Ensure at least MIN_QUESTIONS questions
    if len(questions) < _MIN_QUESTIONS:
        questions.extend([
            f"Can you explain more about how {topic} works?",
            f"What are the key components of {topic} according to your notes?",
        ])

    return {
        "gaps": gaps,
        "questions": questions,
        "verbatim_warning": verbatim,
    }


def generate_gap_report(
    topic: str,
    student_explanation: str,
    gaps: List[str],
    questions: List[str],
    student_answers: List[str],
    all_chunks: List[Chunk],
    watsonx_client,
) -> str:
    """
    Generate a final knowledge-gap report after the student answers follow-up questions.

    Returns:
        Markdown-formatted report string.
    """
    relevant = retrieve_relevant_chunks(topic, all_chunks, top_k=4)
    context = "\n\n---\n\n".join(
        f"[{chunk.section_heading}]\n{chunk.content[:500]}"
        for chunk in (relevant or all_chunks[:4])
    )

    qa_pairs = "\n".join(
        f"Q{i+1}: {q}\nA{i+1}: {a}"
        for i, (q, a) in enumerate(zip(questions, student_answers))
    )

    messages = [
        {"role": "system", "content": _REPORT_SYSTEM},
        {
            "role": "user",
            "content": (
                f"Topic: {topic}\n\n"
                f"Student's original explanation:\n{student_explanation}\n\n"
                f"Identified gaps:\n" + "\n".join(f"- {g}" for g in gaps) + "\n\n"
                f"Follow-up Q&A:\n{qa_pairs}\n\n"
                f"Reference notes:\n{context}"
            ),
        },
    ]

    return watsonx_client.chat(messages)


def _parse_eval_output(raw: str) -> Tuple[List[str], List[str]]:
    """Parse the structured GAPS / QUESTIONS output from the LLM."""
    gaps: List[str] = []
    questions: List[str] = []

    gap_section = re.search(r"GAPS:\s*(.*?)(?:QUESTIONS:|$)", raw, re.DOTALL | re.IGNORECASE)
    q_section = re.search(r"QUESTIONS:\s*(.*)", raw, re.DOTALL | re.IGNORECASE)

    if gap_section:
        for line in gap_section.group(1).splitlines():
            line = line.strip().lstrip("-•*").strip()
            if line:
                gaps.append(line)

    if q_section:
        for line in q_section.group(1).splitlines():
            line = re.sub(r"^\d+[\.\)]\s*", "", line.strip()).strip()
            if line:
                questions.append(line)

    return gaps, questions
