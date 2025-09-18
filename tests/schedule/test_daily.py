"""Tests for src.schedule.daily module."""
import pytest
from datetime import datetime
from src.schedule.daily import DailySchedule
from src.util.time import DAY


@pytest.fixture
def daily_schedule():
    """Create a DailySchedule starting at 2023-01-01 12:00:00."""
    start = datetime(2023, 1, 1, 12, 0, 0)
    return DailySchedule(start)


class TestDailySchedule:
    
    def test_get_scale(self, daily_schedule):
        assert daily_schedule.get_scale() == DAY
    
    def test_get_previous_task_before_start(self, daily_schedule):
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        assert daily_schedule.get_previous_task(before_start) is None
    
    def test_get_previous_task_at_start(self, daily_schedule):
        at_start = datetime(2023, 1, 1, 12, 0, 0)
        assert daily_schedule.get_previous_task(at_start) is None
    
    def test_get_previous_task_one_day_later(self, daily_schedule):
        one_day_later = datetime(2023, 1, 2, 12, 0, 0)
        result = daily_schedule.get_previous_task(one_day_later)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_previous_task_multiple_days_later(self, daily_schedule):
        five_days_later = datetime(2023, 1, 6, 15, 30, 0)
        result = daily_schedule.get_previous_task(five_days_later)
        expected = datetime(2023, 1, 5, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_before_start(self, daily_schedule):
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        result = daily_schedule.get_next_task(before_start)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_at_start(self, daily_schedule):
        at_start = datetime(2023, 1, 1, 12, 0, 0)
        result = daily_schedule.get_next_task(at_start)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_same_day_after_start_time(self, daily_schedule):
        same_day_later = datetime(2023, 1, 1, 15, 0, 0)
        result = daily_schedule.get_next_task(same_day_later)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_next_day(self, daily_schedule):
        next_day = datetime(2023, 1, 2, 8, 0, 0)
        result = daily_schedule.get_next_task(next_day)
        expected = datetime(2023, 1, 2, 12, 0, 0)
        assert result == expected
    
    @pytest.mark.parametrize("timespan_days,expected_count", [
        (1, 1),
        (3, 3),
        (7, 7),
        (0, 0),
    ])
    def test_get_previous_tasks_count(self, daily_schedule, timespan_days, expected_count, monkeypatch):
        # Mock datetime.now() to be 7 days after start
        current_time = datetime(2023, 1, 8, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = timespan_days * DAY
        result = daily_schedule.get_previous_tasks(timespan_seconds)
        assert len(result) == expected_count
    
    def test_get_previous_tasks_ordering(self, daily_schedule, monkeypatch):
        # Mock datetime.now() to be 5 days after start
        current_time = datetime(2023, 1, 6, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = 3 * DAY
        result = daily_schedule.get_previous_tasks(timespan_seconds)
        
        # Should be ordered from most recent to oldest
        expected = [
            datetime(2023, 1, 5, 12, 0, 0),  # Most recent
            datetime(2023, 1, 4, 12, 0, 0),
            datetime(2023, 1, 3, 12, 0, 0),  # Oldest
        ]
        assert result == expected
    
    @pytest.mark.parametrize("timespan_days,expected_count", [
        (1, 1),
        (3, 3),
        (7, 7),
        (0, 0),
    ])
    def test_get_next_tasks_count(self, daily_schedule, timespan_days, expected_count, monkeypatch):
        # Mock datetime.now() to be at start
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = timespan_days * DAY
        result = daily_schedule.get_next_tasks(timespan_seconds)
        assert len(result) == expected_count
    
    def test_get_next_tasks_ordering(self, daily_schedule, monkeypatch):
        # Mock datetime.now() to be at start
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = 3 * DAY
        result = daily_schedule.get_next_tasks(timespan_seconds)
        
        # Should be ordered from earliest to latest
        expected = [
            datetime(2023, 1, 1, 12, 0, 0),  # Earliest
            datetime(2023, 1, 2, 12, 0, 0),
            datetime(2023, 1, 3, 12, 0, 0),  # Latest
        ]
        assert result == expected
    
    def test_edge_case_leap_year(self):
        # Test with leap year date
        start = datetime(2024, 2, 28, 10, 0, 0)
        schedule = DailySchedule(start)
        
        # Test next task after leap day
        leap_day = datetime(2024, 2, 29, 15, 0, 0)
        result = schedule.get_next_task(leap_day)
        expected = datetime(2024, 2, 29, 10, 0, 0)
        assert result == expected
    
    def test_edge_case_dst_transition(self):
        # Test around daylight saving time transition (if applicable)
        start = datetime(2023, 3, 12, 2, 30, 0)  # DST transition date in US
        schedule = DailySchedule(start)
        
        next_day = datetime(2023, 3, 13, 1, 0, 0)
        result = schedule.get_next_task(next_day)
        expected = datetime(2023, 3, 13, 2, 30, 0)
        assert result == expected