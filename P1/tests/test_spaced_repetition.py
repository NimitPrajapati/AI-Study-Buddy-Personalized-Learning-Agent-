"""
tests/test_spaced_repetition.py
Unit tests for the spaced repetition scheduler.
"""
from datetime import date, timedelta

import pytest

from src.features.spaced_repetition import SpacedRepetitionScheduler


@pytest.fixture
def scheduler():
    return SpacedRepetitionScheduler()


@pytest.fixture
def today():
    return date.today()


class TestComputeSchedule:
    def test_empty_topics_returns_empty(self, scheduler):
        result = scheduler.compute_schedule([])
        assert result == {}

    def test_schedule_has_four_dates(self, scheduler, today):
        topics = ["Math", "Science", "History"]
        result = scheduler.compute_schedule(topics, start_date=today)
        assert len(result) >= 3  # At least 3 distinct dates

    def test_today_has_all_topics(self, scheduler, today):
        topics = ["Math", "Science", "History"]
        result = scheduler.compute_schedule(topics, start_date=today)
        today_str = today.isoformat()
        assert today_str in result
        assert set(topics).issubset(set(result[today_str]))

    def test_day3_has_hardest_half(self, scheduler, today):
        topics = ["A", "B", "C", "D"]  # 4 topics — half = 2
        result = scheduler.compute_schedule(topics, start_date=today)
        day3_str = (today + timedelta(days=2)).isoformat()
        assert day3_str in result
        assert len(result[day3_str]) == 2  # Half

    def test_day14_has_all_topics(self, scheduler, today):
        topics = ["Math", "Science"]
        result = scheduler.compute_schedule(topics, start_date=today)
        day14_str = (today + timedelta(days=13)).isoformat()
        assert day14_str in result
        assert set(topics).issubset(set(result[day14_str]))

    def test_single_topic(self, scheduler, today):
        result = scheduler.compute_schedule(["Only Topic"], start_date=today)
        assert len(result) > 0

    def test_dates_are_in_future_or_today(self, scheduler, today):
        topics = ["X", "Y"]
        result = scheduler.compute_schedule(topics, start_date=today)
        for date_str in result:
            d = date.fromisoformat(date_str)
            assert d >= today


class TestGetTodaysTopics:
    def test_returns_todays_topics(self, scheduler):
        from src.models import UserProfile
        profile = UserProfile()
        topics = ["Math", "Science"]
        profile.revision_schedule = scheduler.compute_schedule(topics)
        todays = scheduler.get_todays_topics(profile)
        assert set(topics).issubset(set(todays))

    def test_returns_empty_if_no_schedule(self, scheduler):
        from src.models import UserProfile
        profile = UserProfile()
        assert scheduler.get_todays_topics(profile) == []


class TestFormatScheduleForDisplay:
    def test_returns_list_of_dicts(self, scheduler, today):
        schedule = {
            today.isoformat(): ["Math"],
            (today + timedelta(days=2)).isoformat(): ["Science"],
        }
        rows = scheduler.format_schedule_for_display(schedule)
        assert isinstance(rows, list)
        assert len(rows) == 2
        assert "Date" in rows[0]
        assert "Topics to Revise" in rows[0]

    def test_today_label(self, scheduler, today):
        schedule = {today.isoformat(): ["Math"]}
        rows = scheduler.format_schedule_for_display(schedule)
        assert rows[0]["When"] == "Today"

    def test_tomorrow_label(self, scheduler, today):
        schedule = {(today + timedelta(days=1)).isoformat(): ["Science"]}
        rows = scheduler.format_schedule_for_display(schedule)
        assert rows[0]["When"] == "Tomorrow"
