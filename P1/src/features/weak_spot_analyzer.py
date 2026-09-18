"""
src/features/weak_spot_analyzer.py
Analyzes quiz history to identify topics where the student struggles.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Tuple

from src.models import QuizAttempt, UserProfile

_WEAK_THRESHOLD = 0.60   # Below 60% accuracy = weak topic
_MIN_ATTEMPTS = 3        # Need at least this many attempts for reliable stats


class WeakSpotAnalyzer:
    """Computes per-topic accuracy from quiz history."""

    def analyze(self, quiz_history: List[QuizAttempt]) -> Dict[str, float]:
        """
        Compute accuracy per topic from quiz history.

        Returns:
            Dict mapping topic name -> accuracy (0.0 to 1.0).
            Only topics with at least MIN_ATTEMPTS are included.
        """
        topic_correct: Dict[str, int] = defaultdict(int)
        topic_total: Dict[str, int] = defaultdict(int)

        for attempt in quiz_history:
            topic = attempt.topic or "General"
            topic_total[topic] += 1
            if attempt.is_correct:
                topic_correct[topic] += 1

        accuracy: Dict[str, float] = {}
        for topic, total in topic_total.items():
            if total >= _MIN_ATTEMPTS:
                accuracy[topic] = topic_correct[topic] / total

        return accuracy

    def get_weak_topics(
        self,
        accuracy_map: Dict[str, float],
        threshold: float = _WEAK_THRESHOLD,
    ) -> List[str]:
        """Return topics below the accuracy threshold, sorted weakest first."""
        weak = [
            topic for topic, acc in accuracy_map.items()
            if acc < threshold
        ]
        return sorted(weak, key=lambda t: accuracy_map[t])

    def generate_report(
        self, accuracy_map: Dict[str, float]
    ) -> List[Dict[str, object]]:
        """
        Generate a sortable report list for display.

        Returns:
            List of dicts: {topic, accuracy, attempts, status}
        """
        # We need to reconstruct attempt counts — store them alongside accuracy
        rows = []
        for topic, acc in sorted(accuracy_map.items(), key=lambda x: x[1]):
            status = "🔴 Weak" if acc < _WEAK_THRESHOLD else "🟢 Good"
            rows.append({
                "Topic": topic,
                "Accuracy": f"{acc*100:.0f}%",
                "Status": status,
            })
        return rows

    def update_profile(self, profile: UserProfile) -> None:
        """Recompute and update profile.weak_topics from quiz history."""
        accuracy_map = self.analyze(profile.quiz_history)
        profile.weak_topics = self.get_weak_topics(accuracy_map)
