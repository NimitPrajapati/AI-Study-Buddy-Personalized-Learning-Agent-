"""
tests/test_quiz_engine.py
Unit tests for quiz engine logic (no LLM calls).
"""
import pytest

from src.features.quiz_engine import QuizEngine, _parse_questions
from src.models import QuizAttempt, UserProfile


@pytest.fixture
def engine():
    return QuizEngine()


@pytest.fixture
def profile():
    return UserProfile()


# ---------------------------------------------------------------------------
# adjust_difficulty
# ---------------------------------------------------------------------------

class TestAdjustDifficulty:
    def test_stays_easy_with_no_history(self, engine):
        assert engine.adjust_difficulty("easy", []) == "easy"

    def test_moves_up_after_3_correct(self, engine):
        result = engine.adjust_difficulty("easy", [True, True, True])
        assert result == "medium"

    def test_moves_to_hard_after_3_correct_from_medium(self, engine):
        result = engine.adjust_difficulty("medium", [True, True, True])
        assert result == "hard"

    def test_stays_hard_at_max(self, engine):
        result = engine.adjust_difficulty("hard", [True, True, True])
        assert result == "hard"

    def test_moves_down_after_2_wrong(self, engine):
        result = engine.adjust_difficulty("medium", [False, False])
        assert result == "easy"

    def test_stays_easy_at_min_wrong(self, engine):
        result = engine.adjust_difficulty("easy", [False, False])
        assert result == "easy"

    def test_stays_same_with_mixed(self, engine):
        result = engine.adjust_difficulty("medium", [True, False, True])
        assert result == "medium"

    def test_2_correct_not_enough_to_go_up(self, engine):
        result = engine.adjust_difficulty("easy", [True, True])
        assert result == "easy"

    def test_1_wrong_not_enough_to_go_down(self, engine):
        result = engine.adjust_difficulty("medium", [False])
        assert result == "medium"


# ---------------------------------------------------------------------------
# award_xp
# ---------------------------------------------------------------------------

class TestAwardXP:
    def test_correct_no_streak(self, engine):
        assert engine.award_xp(True, 0) == 10

    def test_correct_low_streak(self, engine):
        assert engine.award_xp(True, 2) == 10

    def test_correct_streak_3_plus(self, engine):
        assert engine.award_xp(True, 3) == 15  # 10 + 5 bonus

    def test_correct_streak_5(self, engine):
        assert engine.award_xp(True, 5) == 15

    def test_wrong_answer_zero_xp(self, engine):
        assert engine.award_xp(False, 10) == 0

    def test_wrong_answer_with_streak_still_zero(self, engine):
        assert engine.award_xp(False, 3) == 0


# ---------------------------------------------------------------------------
# evaluate_answer
# ---------------------------------------------------------------------------

class TestEvaluateAnswer:
    def _make_question(self, correct="A"):
        return {
            "question_id": "q1",
            "question_text": "What is 2+2?",
            "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
            "correct_answer": correct,
            "difficulty": "easy",
            "topic": "Math",
        }

    def test_correct_answer(self, engine):
        q = self._make_question("A")
        assert engine.evaluate_answer(q, "A") is True

    def test_wrong_answer(self, engine):
        q = self._make_question("A")
        assert engine.evaluate_answer(q, "B") is False

    def test_lowercase_accepted(self, engine):
        q = self._make_question("B")
        assert engine.evaluate_answer(q, "b") is True

    def test_full_option_text_accepted(self, engine):
        q = self._make_question("C")
        assert engine.evaluate_answer(q, "C) 5") is True

    def test_empty_answer_is_wrong(self, engine):
        q = self._make_question("A")
        assert engine.evaluate_answer(q, "") is False


# ---------------------------------------------------------------------------
# record_attempt
# ---------------------------------------------------------------------------

class TestRecordAttempt:
    def _make_question(self):
        return {
            "question_id": "q1",
            "question_text": "Q?",
            "options": ["A) X", "B) Y"],
            "correct_answer": "A",
            "difficulty": "easy",
            "topic": "Biology",
        }

    def test_correct_increments_xp(self, engine, profile):
        q = self._make_question()
        engine.record_attempt(profile, q, "A", True)
        assert profile.xp_points > 0

    def test_correct_increments_streak(self, engine, profile):
        q = self._make_question()
        engine.record_attempt(profile, q, "A", True)
        assert profile.current_streak == 1

    def test_wrong_resets_streak(self, engine, profile):
        q = self._make_question()
        engine.record_attempt(profile, q, "A", True)
        engine.record_attempt(profile, q, "B", False)
        assert profile.current_streak == 0

    def test_attempt_added_to_history(self, engine, profile):
        q = self._make_question()
        engine.record_attempt(profile, q, "A", True)
        assert len(profile.quiz_history) == 1
        assert profile.quiz_history[0].topic == "Biology"

    def test_multiple_correct_streak_grows(self, engine, profile):
        q = self._make_question()
        for _ in range(4):
            engine.record_attempt(profile, q, "A", True)
        assert profile.current_streak == 4


# ---------------------------------------------------------------------------
# _parse_questions
# ---------------------------------------------------------------------------

class TestParseQuestions:
    def test_parses_valid_block(self):
        raw = (
            "Q: What is photosynthesis?\n"
            "A) Process of making food using sunlight\n"
            "B) Process of respiration\n"
            "C) Cell division\n"
            "D) DNA replication\n"
            "Answer: A\n"
            "Topic: Biology\n"
        )
        questions = _parse_questions(raw, "easy")
        assert len(questions) == 1
        assert questions[0]["correct_answer"] == "A"
        assert questions[0]["topic"] == "Biology"
        assert questions[0]["difficulty"] == "easy"

    def test_parses_multiple_blocks(self):
        raw = (
            "Q: Question 1?\n"
            "A) Option A\nB) Option B\nC) Option C\nD) Option D\n"
            "Answer: B\nTopic: Math\n\n"
            "Q: Question 2?\n"
            "A) Option A\nB) Option B\nC) Option C\nD) Option D\n"
            "Answer: C\nTopic: Science\n"
        )
        questions = _parse_questions(raw, "medium")
        assert len(questions) == 2

    def test_invalid_block_skipped(self):
        raw = "Not a valid question format"
        questions = _parse_questions(raw, "hard")
        assert questions == []
