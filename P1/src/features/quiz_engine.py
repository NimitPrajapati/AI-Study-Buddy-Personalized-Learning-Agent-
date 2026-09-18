"""
src/features/quiz_engine.py
Adaptive-difficulty quiz engine with XP and streak tracking.
"""
from __future__ import annotations

import re
import uuid
from typing import List, Optional, Tuple

from src.document_ingestion import retrieve_relevant_chunks
from src.models import Chunk, QuizAttempt, UserProfile

# Difficulty thresholds
_UP_THRESHOLD = 3    # consecutive correct → go up one level
_DOWN_THRESHOLD = 2  # consecutive wrong → go down one level

_DIFFICULTY_LADDER = ["easy", "medium", "hard"]

# XP awards
_XP_CORRECT = 10
_XP_STREAK_BONUS = 5  # added when streak >= 3
_XP_WRONG = 0

_QUESTION_PROMPT = """You are a quiz question generator for students.
Generate {n} multiple-choice questions at {difficulty} difficulty level about: {topic}
Use ONLY the following reference notes as the source.

Format EACH question EXACTLY like this:
Q: <question text>
A) <option A>
B) <option B>
C) <option C>
D) <option D>
Answer: <correct letter only, e.g. A>
Topic: <one short topic label>

---

Reference notes:
{context}
"""


class QuizEngine:
    """Manages question generation, evaluation, difficulty adjustment, and XP."""

    def generate_questions(
        self,
        topic: str,
        difficulty: str,
        all_chunks: List[Chunk],
        watsonx_client,
        n: int = 5,
    ) -> List[dict]:
        """
        Generate n MCQ questions at the given difficulty level.

        Returns:
            List of question dicts with keys: question_id, question_text, options,
            correct_answer, difficulty, topic.
        """
        relevant = retrieve_relevant_chunks(topic, all_chunks, top_k=5)
        if not relevant:
            relevant = all_chunks[:5]

        context = "\n\n---\n\n".join(
            f"[{c.section_heading}]\n{c.content[:600]}" for c in relevant
        )

        prompt = _QUESTION_PROMPT.format(
            n=n,
            difficulty=difficulty,
            topic=topic,
            context=context,
        )

        raw = watsonx_client.generate_text(prompt)
        return _parse_questions(raw, difficulty)

    def evaluate_answer(self, question: dict, user_answer: str) -> bool:
        """Return True if user_answer matches the correct answer (case-insensitive)."""
        correct = question.get("correct_answer", "").strip().upper()
        user = user_answer.strip().upper()
        # Accept "A", "a", "A) text", etc.
        user_letter = user[0] if user else ""
        return user_letter == correct[0] if correct else False

    def adjust_difficulty(
        self, current: str, recent_results: List[bool]
    ) -> str:
        """
        Apply threshold rules to decide the next difficulty level.

        Rules:
          - 3 consecutive correct → move up one level
          - 2 consecutive wrong  → move down one level
          - Otherwise stay the same
        """
        if not recent_results:
            return current

        idx = _DIFFICULTY_LADDER.index(current) if current in _DIFFICULTY_LADDER else 0

        # Check last N results
        if len(recent_results) >= _UP_THRESHOLD:
            if all(recent_results[-_UP_THRESHOLD:]):
                idx = min(idx + 1, len(_DIFFICULTY_LADDER) - 1)
                return _DIFFICULTY_LADDER[idx]

        if len(recent_results) >= _DOWN_THRESHOLD:
            if not any(recent_results[-_DOWN_THRESHOLD:]):
                idx = max(idx - 1, 0)
                return _DIFFICULTY_LADDER[idx]

        return current

    def award_xp(self, is_correct: bool, streak: int) -> int:
        """Return XP earned for this answer."""
        if not is_correct:
            return _XP_WRONG
        xp = _XP_CORRECT
        if streak >= 3:
            xp += _XP_STREAK_BONUS
        return xp

    def record_attempt(
        self,
        profile: UserProfile,
        question: dict,
        user_answer: str,
        is_correct: bool,
    ) -> QuizAttempt:
        """Create a QuizAttempt, update profile XP/streak, and store it."""
        attempt = QuizAttempt(
            question_id=question.get("question_id", str(uuid.uuid4())),
            question_text=question.get("question_text", ""),
            difficulty=question.get("difficulty", "easy"),
            options=question.get("options", []),
            correct_answer=question.get("correct_answer", ""),
            user_answer=user_answer,
            is_correct=is_correct,
            topic=question.get("topic", "General"),
        )

        if is_correct:
            profile.current_streak += 1
            profile.xp_points += self.award_xp(is_correct, profile.current_streak)
        else:
            profile.current_streak = 0

        profile.quiz_history.append(attempt)
        return attempt


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_questions(raw: str, difficulty: str) -> List[dict]:
    """Parse LLM output into a list of question dicts."""
    questions: List[dict] = []
    blocks = re.split(r"\n(?=Q:)", raw.strip())

    for block in blocks:
        block = block.strip()
        if not block.startswith("Q:"):
            continue

        q_match = re.search(r"Q:\s*(.+)", block)
        a_match = re.search(r"A\)\s*(.+)", block)
        b_match = re.search(r"B\)\s*(.+)", block)
        c_match = re.search(r"C\)\s*(.+)", block)
        d_match = re.search(r"D\)\s*(.+)", block)
        ans_match = re.search(r"Answer:\s*([ABCD])", block, re.IGNORECASE)
        topic_match = re.search(r"Topic:\s*(.+)", block)

        if not (q_match and ans_match):
            continue

        options = []
        for label, m in [("A", a_match), ("B", b_match), ("C", c_match), ("D", d_match)]:
            if m:
                options.append(f"{label}) {m.group(1).strip()}")

        questions.append({
            "question_id": str(uuid.uuid4()),
            "question_text": q_match.group(1).strip(),
            "options": options,
            "correct_answer": ans_match.group(1).strip().upper(),
            "difficulty": difficulty,
            "topic": topic_match.group(1).strip() if topic_match else "General",
        })

    return questions
