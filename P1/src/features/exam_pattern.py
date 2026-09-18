"""
src/features/exam_pattern.py
Analyzes uploaded past exam papers to predict topic frequency and question types.
"""
from __future__ import annotations

from typing import Dict, List

from src.models import Chunk

_ANALYSIS_PROMPT = """You are an exam pattern analyst.
Analyze the following past exam paper(s) and identify:
1. The most frequently tested TOPICS (list them with frequency counts if possible)
2. The most common QUESTION TYPES (MCQ, Short Answer, Long Answer, True/False, etc.)
3. Any patterns in how questions are structured

Output format:
TOPICS:
- <topic name>: <frequency or "appears frequently">
...

QUESTION TYPES:
- <type>: <observations>
...

PATTERNS:
- <observation>

Reference exam content:
{context}
"""

_MIN_PAPERS_WARNING = 2


def analyze_papers(
    paper_chunks_list: List[List[Chunk]],
    watsonx_client,
) -> dict:
    """
    Analyze a list of past exam papers to extract topic frequency and question types.

    Args:
        paper_chunks_list: List of chunk lists, one per uploaded paper.
        watsonx_client: WatsonxClient instance.

    Returns:
        dict with keys: "topics", "question_types", "patterns", "paper_count", "warning"
    """
    paper_count = len(paper_chunks_list)
    warning = None
    if paper_count < _MIN_PAPERS_WARNING:
        warning = (
            f"Only {paper_count} paper uploaded. "
            "For more reliable predictions, upload at least 2-3 past papers."
        )

    # Flatten all chunks with paper labels
    context_parts = []
    for i, chunks in enumerate(paper_chunks_list, 1):
        paper_text = "\n".join(c.content[:400] for c in chunks[:6])
        context_parts.append(f"--- PAPER {i} ---\n{paper_text}")

    context = "\n\n".join(context_parts)
    prompt = _ANALYSIS_PROMPT.format(context=context)

    raw = watsonx_client.generate_text(prompt, params={"max_new_tokens": 900})
    parsed = _parse_analysis(raw)
    parsed["paper_count"] = paper_count
    parsed["warning"] = warning
    return parsed


def _parse_analysis(raw: str) -> dict:
    """Parse the structured analysis output from the LLM."""
    import re

    result = {"topics": [], "question_types": [], "patterns": []}

    topic_section = re.search(r"TOPICS:\s*(.*?)(?:QUESTION TYPES:|$)", raw, re.DOTALL | re.IGNORECASE)
    qt_section = re.search(r"QUESTION TYPES:\s*(.*?)(?:PATTERNS:|$)", raw, re.DOTALL | re.IGNORECASE)
    pat_section = re.search(r"PATTERNS:\s*(.*)", raw, re.DOTALL | re.IGNORECASE)

    def _parse_list(text: str) -> List[str]:
        items = []
        for line in text.strip().splitlines():
            line = line.strip().lstrip("-•*").strip()
            if line:
                items.append(line)
        return items

    if topic_section:
        result["topics"] = _parse_list(topic_section.group(1))
    if qt_section:
        result["question_types"] = _parse_list(qt_section.group(1))
    if pat_section:
        result["patterns"] = _parse_list(pat_section.group(1))

    return result
