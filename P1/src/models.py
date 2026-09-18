"""
src/models.py
All dataclasses for the AI Study Buddy application.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Chunk:
    """A single retrievable segment of a parsed document."""
    chunk_id: str = field(default_factory=_new_id)
    doc_id: str = ""
    page_number: int = 0          # 0 for TXT files
    section_heading: str = "Unknown"
    content: str = ""


@dataclass
class Document:
    """A user-uploaded study document and its parsed chunks."""
    doc_id: str = field(default_factory=_new_id)
    file_name: str = ""
    file_type: str = ""           # "pdf" or "txt"
    raw_text: str = ""
    chunks: List[Chunk] = field(default_factory=list)
    content_hash: str = ""        # MD5 for duplicate detection
    upload_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class QuizAttempt:
    """A single question answered by the user during a quiz."""
    question_id: str = field(default_factory=_new_id)
    question_text: str = ""
    difficulty: str = "easy"      # "easy" | "medium" | "hard"
    options: List[str] = field(default_factory=list)
    correct_answer: str = ""
    user_answer: str = ""
    is_correct: bool = False
    topic: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class UserProfile:
    """Per-session learner profile tracking progress and performance."""
    user_id: str = field(default_factory=_new_id)
    quiz_history: List[QuizAttempt] = field(default_factory=list)
    weak_topics: List[str] = field(default_factory=list)
    xp_points: int = 0
    current_streak: int = 0
    revision_schedule: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class QuizRoom:
    """A multiplayer quiz session."""
    room_code: str = ""
    host_id: str = ""
    participants: List[str] = field(default_factory=list)
    questions: List[dict] = field(default_factory=list)
    answers: Dict[str, List[dict]] = field(default_factory=dict)
    leaderboard: Dict[str, int] = field(default_factory=dict)
    status: str = "waiting"       # "waiting" | "active" | "finished"
    current_question_index: int = 0
