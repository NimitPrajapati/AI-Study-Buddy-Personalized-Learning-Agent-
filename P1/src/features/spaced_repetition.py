"""
src/features/spaced_repetition.py
Spaced-repetition revision scheduler based on weak topics.
Uses a simplified SM-2-inspired interval pattern.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List

from src.models import UserProfile


# Day offsets for each review interval
_REVIEW_INTERVALS = [0, 2, 6, 13]  # Day 1, 3, 7, 14 (0-indexed from today)


class SpacedRepetitionScheduler:
    """Generates and manages a spaced-repetition revision schedule."""

    def compute_schedule(
        self,
        weak_topics: List[str],
        start_date: date | None = None,
    ) -> Dict[str, List[str]]:
        """
        Build a revision schedule for the given weak topics.

        Schedule pattern:
          Day 1  (today)    : all weak topics
          Day 3             : topics with accuracy < 50% (or all if subset unknown)
          Day 7             : all weak topics
          Day 14            : final review of all weak topics

        Args:
            weak_topics: Ordered list of topics (weakest first).
            start_date: The starting date (defaults to today).

        Returns:
            Dict mapping ISO date strings to lists of topics to revise.
        """
        if not weak_topics:
            return {}

        today = start_date or date.today()
        schedule: Dict[str, List[str]] = {}

        for i, offset in enumerate(_REVIEW_INTERVALS):
            review_date = today + timedelta(days=offset)
            date_str = review_date.isoformat()

            if i == 0:
                # Day 1: all topics
                topics = list(weak_topics)
            elif i == 1:
                # Day 3: most difficult half
                half = max(1, len(weak_topics) // 2)
                topics = list(weak_topics[:half])
            else:
                # Day 7 and 14: all topics again
                topics = list(weak_topics)

            if date_str in schedule:
                # Merge if dates collide
                existing = set(schedule[date_str])
                schedule[date_str] = list(existing | set(topics))
            else:
                schedule[date_str] = topics

        return schedule

    def update_on_quiz_result(
        self,
        profile: UserProfile,
        topic: str,
        is_correct: bool,
    ) -> None:
        """
        Recalculate the revision schedule after a quiz result.
        Called by the quiz engine after recording each attempt.
        """
        from src.features.weak_spot_analyzer import WeakSpotAnalyzer

        analyzer = WeakSpotAnalyzer()
        analyzer.update_profile(profile)

        # Recompute schedule from updated weak topics
        profile.revision_schedule = self.compute_schedule(profile.weak_topics)

    def get_todays_topics(self, profile: UserProfile) -> List[str]:
        """Return topics scheduled for today."""
        today_str = date.today().isoformat()
        return profile.revision_schedule.get(today_str, [])

    def format_schedule_for_display(
        self, schedule: Dict[str, List[str]]
    ) -> List[Dict[str, str]]:
        """
        Convert schedule dict into a list of rows for table display.

        Returns:
            List of dicts: {date, day_label, topics}
        """
        today = date.today()
        rows = []
        for date_str in sorted(schedule.keys()):
            topics = schedule[date_str]
            review_date = date.fromisoformat(date_str)
            delta = (review_date - today).days
            if delta == 0:
                label = "Today"
            elif delta == 1:
                label = "Tomorrow"
            elif delta < 0:
                label = f"{abs(delta)} days ago"
            else:
                label = f"In {delta} days"

            rows.append({
                "Date": date_str,
                "When": label,
                "Topics to Revise": ", ".join(topics),
            })
        return rows
