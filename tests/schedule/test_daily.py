"""Tests for src.schedule.daily module."""
import pytest
from datetime import datetime, timedelta
from src.schedule.daily import DailySchedule
from src.util.time import DAY


@pytest.fixture
def daily_schedule():
    """Create a DailySchedule starting at 2023-01-01 12:00:00."""
    start = datetime(2023, 1, 1, 12, 0, 0)
    return DailySchedule(start)


class TestDailySchedule:
    
    def test_get_scale(self, daily_schedule):
        """Test that get_scale returns DAY constant."""
        assert daily_schedule.get_scale() == DAY
    
    def test_get_previous_task_before_start(self, daily_schedule):
        """Test get_previous_task returns None for datetime before start."""
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        assert daily_schedule.get_previous_task(before_start) is None
    
    def test_get_previous_task_at_start(self, daily_schedule):
        """Test get_previous_task returns None at exact start time."""
        at_start = datetime(2023, 1, 1, 12, 0, 0)
        assert daily_schedule.get_previous_task(at_start) is None
    
    def test_get_previous_task_one_day_later(self, daily_schedule):
        """Test get_previous_task returns previous day's task."""
        one_day_later = datetime(2023, 1, 2, 12, 0, 0)
        result = daily_schedule.get_previous_task(one_day_later)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_previous_task_multiple_days_later(self, daily_schedule):
        """Test get_previous_task returns correct day for multiple days later."""
        five_days_later = datetime(2023, 1, 6, 15, 30, 0)
        result = daily_schedule.get_previous_task(five_days_later)
        expected = datetime(2023, 1, 5, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_before_start(self, daily_schedule):
        """Test get_next_task returns start time when before start."""
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        result = daily_schedule.get_next_task(before_start)
        expected = datetime(2023, 1, 1, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_at_start(self, daily_schedule):
        """Test get_next_task returns same time when at start."""
        at_start = datetime(2023, 1, 1, 12, 0, 0)
        result = daily_schedule.get_next_task(at_start)
        expected = datetime(2023, 1, 2, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_same_day_after_start_time(self, daily_schedule):
        """Test get_next_task returns today's task when after start time."""
        same_day_later = datetime(2023, 1, 1, 15, 0, 0)
        result = daily_schedule.get_next_task(same_day_later)
        expected = datetime(2023, 1, 2, 12, 0, 0)
        assert result == expected
    
    def test_get_next_task_next_day(self, daily_schedule):
        """Test get_next_task returns next day's task when on different day."""
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
        """Test get_previous_tasks returns correct number of tasks."""
        # Mock datetime.now() to be 7 days after start
        current_time = datetime(2023, 1, 8, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            @staticmethod
            def today():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = timespan_days * DAY
        result = daily_schedule.get_previous_tasks(timespan_seconds)
        assert len(result) == expected_count
    
    def test_get_previous_tasks_ordering(self, daily_schedule, monkeypatch):
        """Test get_previous_tasks returns tasks in reverse chronological order."""
        # Mock datetime.now() to be 5 days after start
        current_time = datetime(2023, 1, 6, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            @staticmethod
            def today():
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
        """Test get_next_tasks returns correct number of future tasks."""
        # Mock datetime.now() to be at start
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            @staticmethod
            def today():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = timespan_days * DAY
        result = daily_schedule.get_next_tasks(timespan_seconds)
        assert len(result) == expected_count
    
    def test_get_next_tasks_ordering(self, daily_schedule, monkeypatch):
        """Test get_next_tasks returns tasks in chronological order."""
        # Mock datetime.now() to be at start
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            @staticmethod
            def today():
                return datetime(2024, 1, 1, 12, 0, 0)
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        monkeypatch.setattr('src.schedule.daily.datetime', MockDateTime())
        
        timespan_seconds = 3 * DAY
        result = daily_schedule.get_next_tasks(timespan_seconds)
        
        # Should be ordered from earliest to latest
        expected = [
            datetime(2023, 1, 2, 12, 0, 0),
            datetime(2023, 1, 3, 12, 0, 0),
            datetime(2023, 1, 4, 12, 0, 0),
        ]
        assert result == expected
    
    def test_edge_case_leap_year(self):
        """Test daily schedule behavior during leap year."""
        # Test with leap year date
        start = datetime(2024, 2, 28, 10, 0, 0)
        schedule = DailySchedule(start)

        # Test next task after leap day
        leap_day = datetime(2024, 2, 29, 15, 0, 0)
        result = schedule.get_next_task(leap_day)
        expected = datetime(2024, 3, 1, 10, 0, 0)
        assert result == expected
    
    def test_edge_case_dst_transition(self):
        """Test daily schedule behavior during daylight saving time transition."""
        # Test around daylight saving time transition (if applicable)
        start = datetime(2023, 3, 12, 2, 30, 0)  # DST transition date in US
        schedule = DailySchedule(start)

        next_day = datetime(2023, 3, 13, 1, 0, 0)
        result = schedule.get_next_task(next_day)
        expected = datetime(2023, 3, 13, 2, 30, 0)
        assert result == expected

    def test_get_previous_task_get_next_task_consistency(self):
        """Test consistency between get_previous_task and get_next_task methods."""
        start = datetime(2023, 1, 1, 12, 0, 0)
        schedule = DailySchedule(start)

        # Start from a scheduled task time
        t1 = schedule.get_next_task(start + timedelta(days=3))

        # Go forward 3 steps
        t2 = schedule.get_next_task(t1)
        t3 = schedule.get_next_task(t2)
        t4 = schedule.get_next_task(t3)

        # Go backward 3 steps - should return to original tasks
        back1 = schedule.get_previous_task(t4)
        back2 = schedule.get_previous_task(back1)
        back3 = schedule.get_previous_task(back2)

        assert back1 == t3
        assert back2 == t2
        assert back3 == t1