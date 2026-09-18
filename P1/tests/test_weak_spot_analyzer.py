"""
tests/test_weak_spot_analyzer.py
Unit tests for the weak spot analyzer.
"""
import pytest

from src.features.weak_spot_analyzer import WeakSpotAnalyzer, _WEAK_THRESHOLD
from src.models import QuizAttempt, UserProfile


def _make_attempt(topic: str, is_correct: bool) -> QuizAttempt:
    a = QuizAttempt()
    a.topic = topic
    a.is_correct = is_correct
    return a


@pytest.fixture
def analyzer():
    return WeakSpotAnalyzer()


class TestAnalyze:
    def test_empty_history_returns_empty(self, analyzer):
        result = analyzer.analyze([])
        assert result == {}

    def test_skips_topics_below_min_attempts(self, analyzer):
        # Only 2 attempts — below the minimum of 3
        history = [
            _make_attempt("Math", True),
            _make_attempt("Math", False),
        ]
        result = analyzer.analyze(history)
        assert "Math" not in result

    def test_computes_correct_accuracy(self, analyzer):
        history = [
            _make_attempt("Math", True),
            _make_attempt("Math", True),
            _make_attempt("Math", False),
        ]
        result = analyzer.analyze(history)
        assert "Math" in result
        assert abs(result["Math"] - 2/3) < 0.01

    def test_100_percent_accuracy(self, analyzer):
        history = [_make_attempt("Science", True)] * 5
        result = analyzer.analyze(history)
        assert result["Science"] == 1.0

    def test_zero_percent_accuracy(self, analyzer):
        history = [_make_attempt("History", False)] * 4
        result = analyzer.analyze(history)
        assert result["History"] == 0.0

    def test_multiple_topics(self, analyzer):
        history = (
            [_make_attempt("Math", True)] * 3 +
            [_make_attempt("Science", False)] * 3
        )
        result = analyzer.analyze(history)
        assert "Math" in result and "Science" in result


class TestGetWeakTopics:
    def test_returns_topics_below_threshold(self, analyzer):
        accuracy_map = {"Math": 0.4, "Science": 0.9, "History": 0.55}
        weak = analyzer.get_weak_topics(accuracy_map)
        assert "Math" in weak
        assert "History" in weak
        assert "Science" not in weak

    def test_sorted_weakest_first(self, analyzer):
        accuracy_map = {"Math": 0.4, "History": 0.2, "English": 0.5}
        weak = analyzer.get_weak_topics(accuracy_map)
        assert weak[0] == "History"  # 0.2 is weakest

    def test_empty_accuracy_map(self, analyzer):
        assert analyzer.get_weak_topics({}) == []

    def test_all_strong_returns_empty(self, analyzer):
        accuracy_map = {"Math": 0.9, "Science": 0.85}
        assert analyzer.get_weak_topics(accuracy_map) == []


class TestGenerateReport:
    def test_returns_list_of_dicts(self, analyzer):
        accuracy_map = {"Math": 0.4, "Science": 0.9}
        report = analyzer.generate_report(accuracy_map)
        assert isinstance(report, list)
        assert len(report) == 2

    def test_weak_topic_has_red_status(self, analyzer):
        accuracy_map = {"Math": 0.3}
        report = analyzer.generate_report(accuracy_map)
        assert "🔴" in report[0]["Status"]

    def test_strong_topic_has_green_status(self, analyzer):
        accuracy_map = {"Science": 0.95}
        report = analyzer.generate_report(accuracy_map)
        assert "🟢" in report[0]["Status"]


class TestUpdateProfile:
    def test_updates_weak_topics_in_profile(self, analyzer):
        profile = UserProfile()
        # Add enough attempts to trigger analysis
        for _ in range(4):
            profile.quiz_history.append(_make_attempt("Math", False))
        for _ in range(4):
            profile.quiz_history.append(_make_attempt("Science", True))

        analyzer.update_profile(profile)
        assert "Math" in profile.weak_topics
        assert "Science" not in profile.weak_topics
