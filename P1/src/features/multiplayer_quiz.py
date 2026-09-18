"""
src/features/multiplayer_quiz.py
Turn-based multiplayer quiz session management.
Rooms are stored in Streamlit session_state.rooms.
"""
from __future__ import annotations

import random
import string
from typing import Dict, List, Optional, Tuple

from src.exceptions import (
    QuizNotStartedError,
    RoomFullError,
    RoomNotFoundError,
)
from src.models import QuizRoom

_MAX_PARTICIPANTS = 10
_MIN_PARTICIPANTS = 2
_XP_PER_CORRECT = 15
_STREAK_BONUS = 5


def _generate_room_code() -> str:
    """Generate a random 6-character alphanumeric room code."""
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=6))


class MultiplayerQuizManager:
    """Manages creation, joining, and answer submission for multiplayer quiz rooms."""

    def create_room(
        self,
        host_id: str,
        host_name: str,
        questions: List[dict],
        rooms: Dict[str, QuizRoom],
    ) -> QuizRoom:
        """
        Create a new quiz room.

        Args:
            host_id: The host's user ID.
            host_name: Display name for the host.
            questions: Pre-generated question dicts.
            rooms: The shared rooms dict from session_state.

        Returns:
            The newly created QuizRoom.
        """
        code = _generate_room_code()
        # Ensure uniqueness
        while code in rooms:
            code = _generate_room_code()

        room = QuizRoom(
            room_code=code,
            host_id=host_id,
            participants=[host_id],
            questions=questions,
            answers={host_id: []},
            leaderboard={host_id: 0},
            status="waiting",
        )
        rooms[code] = room
        return room

    def join_room(
        self,
        room_code: str,
        user_id: str,
        rooms: Dict[str, QuizRoom],
    ) -> QuizRoom:
        """
        Add a participant to an existing room.

        Raises:
            RoomNotFoundError: if the code doesn't exist.
            RoomFullError: if the room is at capacity.
        """
        if room_code not in rooms:
            raise RoomNotFoundError(
                f"Room '{room_code}' not found. Check the code and try again."
            )
        room = rooms[room_code]

        if len(room.participants) >= _MAX_PARTICIPANTS:
            raise RoomFullError(
                f"Room '{room_code}' is full ({_MAX_PARTICIPANTS} participants max)."
            )

        if user_id not in room.participants:
            room.participants.append(user_id)
            room.answers[user_id] = []
            room.leaderboard[user_id] = 0

        return room

    def start_quiz(
        self,
        room_code: str,
        rooms: Dict[str, QuizRoom],
    ) -> QuizRoom:
        """
        Start the quiz. Requires at least MIN_PARTICIPANTS.

        Raises:
            RoomNotFoundError: if room doesn't exist.
            QuizNotStartedError: if too few participants.
        """
        if room_code not in rooms:
            raise RoomNotFoundError(f"Room '{room_code}' not found.")

        room = rooms[room_code]
        if len(room.participants) < _MIN_PARTICIPANTS:
            raise QuizNotStartedError(
                f"Need at least {_MIN_PARTICIPANTS} participants to start. "
                f"Currently {len(room.participants)} joined."
            )

        room.status = "active"
        return room

    def submit_answer(
        self,
        room_code: str,
        user_id: str,
        question_idx: int,
        user_answer: str,
        rooms: Dict[str, QuizRoom],
    ) -> Tuple[int, bool]:
        """
        Submit a participant's answer for a question.

        Returns:
            (xp_earned, is_correct) tuple.

        Raises:
            RoomNotFoundError, QuizNotStartedError.
        """
        if room_code not in rooms:
            raise RoomNotFoundError(f"Room '{room_code}' not found.")

        room = rooms[room_code]
        if room.status != "active":
            raise QuizNotStartedError("The quiz has not started yet.")

        if question_idx >= len(room.questions):
            return 0, False

        question = room.questions[question_idx]
        correct = question.get("correct_answer", "").strip().upper()
        user_letter = user_answer.strip().upper()[:1]
        is_correct = user_letter == correct[:1]

        # Calculate XP with streak
        user_answers = room.answers.get(user_id, [])
        streak = 0
        for prev in reversed(user_answers):
            if prev.get("is_correct"):
                streak += 1
            else:
                break

        xp = _XP_PER_CORRECT if is_correct else 0
        if is_correct and streak >= 2:
            xp += _STREAK_BONUS

        room.leaderboard[user_id] = room.leaderboard.get(user_id, 0) + xp
        room.answers.setdefault(user_id, []).append({
            "question_idx": question_idx,
            "user_answer": user_answer,
            "is_correct": is_correct,
            "xp": xp,
        })

        return xp, is_correct

    def get_leaderboard(
        self,
        room_code: str,
        rooms: Dict[str, QuizRoom],
    ) -> List[Tuple[str, int]]:
        """
        Return participants sorted by score descending.

        Returns:
            List of (user_id, score) tuples.
        """
        if room_code not in rooms:
            raise RoomNotFoundError(f"Room '{room_code}' not found.")
        room = rooms[room_code]
        return sorted(room.leaderboard.items(), key=lambda x: x[1], reverse=True)

    def finish_room(self, room_code: str, rooms: Dict[str, QuizRoom]) -> None:
        """Mark a room as finished."""
        if room_code in rooms:
            rooms[room_code].status = "finished"
