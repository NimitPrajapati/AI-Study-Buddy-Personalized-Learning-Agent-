"""
tests/test_multiplayer_quiz.py
Unit tests for the multiplayer quiz manager.
"""
import pytest

from src.exceptions import QuizNotStartedError, RoomFullError, RoomNotFoundError
from src.features.multiplayer_quiz import MultiplayerQuizManager
from src.models import QuizRoom


@pytest.fixture
def manager():
    return MultiplayerQuizManager()


@pytest.fixture
def rooms():
    return {}


@pytest.fixture
def sample_questions():
    return [
        {
            "question_id": "q1",
            "question_text": "What is 2+2?",
            "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
            "correct_answer": "B",
            "difficulty": "easy",
            "topic": "Math",
        },
        {
            "question_id": "q2",
            "question_text": "What is 3x3?",
            "options": ["A) 6", "B) 8", "C) 9", "D) 12"],
            "correct_answer": "C",
            "difficulty": "easy",
            "topic": "Math",
        },
    ]


class TestCreateRoom:
    def test_creates_room_with_code(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        assert room.room_code in rooms
        assert len(room.room_code) == 6
        assert room.room_code.isalnum()

    def test_host_is_participant(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        assert "host1" in room.participants

    def test_status_is_waiting(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        assert room.status == "waiting"

    def test_questions_stored(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        assert len(room.questions) == len(sample_questions)


class TestJoinRoom:
    def test_join_existing_room(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        updated_room = rooms[room.room_code]
        assert "player1" in updated_room.participants

    def test_join_nonexistent_raises(self, manager, rooms):
        with pytest.raises(RoomNotFoundError):
            manager.join_room("XXXXXX", "player1", rooms)

    def test_join_creates_leaderboard_entry(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        assert "player1" in rooms[room.room_code].leaderboard

    def test_duplicate_join_idempotent(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        manager.join_room(room.room_code, "player1", rooms)
        assert rooms[room.room_code].participants.count("player1") == 1


class TestStartQuiz:
    def test_start_with_two_participants(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        manager.start_quiz(room.room_code, rooms)
        assert rooms[room.room_code].status == "active"

    def test_start_with_one_raises(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        with pytest.raises(QuizNotStartedError):
            manager.start_quiz(room.room_code, rooms)

    def test_start_nonexistent_raises(self, manager, rooms):
        with pytest.raises(RoomNotFoundError):
            manager.start_quiz("XXXXXX", rooms)


class TestSubmitAnswer:
    def test_correct_answer_awards_xp(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        manager.start_quiz(room.room_code, rooms)
        xp, correct = manager.submit_answer(room.room_code, "host1", 0, "B", rooms)
        assert correct is True
        assert xp > 0

    def test_wrong_answer_zero_xp(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        manager.start_quiz(room.room_code, rooms)
        xp, correct = manager.submit_answer(room.room_code, "host1", 0, "A", rooms)
        assert correct is False
        assert xp == 0

    def test_submit_before_start_raises(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        with pytest.raises(QuizNotStartedError):
            manager.submit_answer(room.room_code, "host1", 0, "B", rooms)


class TestGetLeaderboard:
    def test_leaderboard_sorted_by_score(self, manager, rooms, sample_questions):
        room = manager.create_room("host1", "Host", sample_questions, rooms)
        manager.join_room(room.room_code, "player1", rooms)
        manager.start_quiz(room.room_code, rooms)
        manager.submit_answer(room.room_code, "host1", 0, "B", rooms)  # Correct
        manager.submit_answer(room.room_code, "player1", 0, "A", rooms)  # Wrong

        leaderboard = manager.get_leaderboard(room.room_code, rooms)
        assert leaderboard[0][0] == "host1"  # host1 has higher score

    def test_nonexistent_room_raises(self, manager, rooms):
        with pytest.raises(RoomNotFoundError):
            manager.get_leaderboard("XXXXXX", rooms)
