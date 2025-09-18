"""Tests for src.schedule.exponential module."""
import pytest
from datetime import datetime, timedelta
from src.schedule.exponential import ExponentialSchedule
from src.util.time import DAY


@pytest.fixture
def exp_schedule():
    """Create an ExponentialSchedule with base 2 starting at 2023-01-01 12:00:00."""
    start = datetime(2023, 1, 1, 12, 0, 0)
    return ExponentialSchedule(start, base=2)


class TestExponentialSchedule:
    
    def test_get_scale(self, exp_schedule):
        assert exp_schedule.get_scale() == DAY
    
    def test_init(self):
        start = datetime(2023, 1, 1, 12, 0, 0)
        schedule = ExponentialSchedule(start, base=3)
        assert schedule.start == start
        assert schedule.base == 3
    
    def test_get_previous_task_before_start(self, exp_schedule):
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        assert exp_schedule.get_previous_task(before_start) is None
    
    def test_get_previous_task_at_start(self, exp_schedule):
        at_start = datetime(2023, 1, 1, 12, 0, 0)
        assert exp_schedule.get_previous_task(at_start) is None
    
    def test_get_previous_task_sequence(self, exp_schedule):
        # With base=2: intervals are 2, 4, 8, 16... days
        # Tasks at: start + 2, start + 6, start + 14, start + 30...
        
        # From day 3 (after first task at day 2)
        from_dt = datetime(2023, 1, 4, 12, 0, 0)
        result = exp_schedule.get_previous_task(from_dt)
        expected = datetime(2023, 1, 3, 12, 0, 0)  # start + 2 days
        assert result == expected
        
        # From day 7 (after second task at day 6)
        from_dt = datetime(2023, 1, 8, 12, 0, 0)
        result = exp_schedule.get_previous_task(from_dt)
        expected = datetime(2023, 1, 7, 12, 0, 0)  # start + 6 days
        assert result == expected
    
    def test_get_next_task_before_start(self, exp_schedule):
        before_start = datetime(2022, 12, 31, 11, 0, 0)
        result = exp_schedule.get_next_task(before_start)
        expected = datetime(2023, 1, 1, 12, 0, 0)  # start
        assert result == expected
    
    def test_get_next_task_sequence(self, exp_schedule):
        # With base=2: intervals are 2, 4, 8, 16... days
        # Tasks at: start + 2, start + 6, start + 14, start + 30...
        
        # From start
        result = exp_schedule.get_next_task(exp_schedule.start)
        expected = datetime(2023, 1, 3, 12, 0, 0)  # start + 2 days
        assert result == expected
        
        # From day 2
        from_dt = datetime(2023, 1, 3, 12, 0, 0)
        result = exp_schedule.get_next_task(from_dt)
        expected = datetime(2023, 1, 7, 12, 0, 0)  # start + 6 days
        assert result == expected
        
        # From day 6
        from_dt = datetime(2023, 1, 7, 12, 0, 0)
        result = exp_schedule.get_next_task(from_dt)
        expected = datetime(2023, 1, 15, 12, 0, 0)  # start + 14 days
        assert result == expected
    
    def test_get_previous_tasks(self, exp_schedule):
        # Mock datetime.now() to be several days after start  
        current_time = datetime(2023, 1, 10, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        import src.schedule.exponential
        original_datetime = src.schedule.exponential.datetime
        src.schedule.exponential.datetime = MockDateTime()
        
        try:
            # The implementation calculates backwards from start date
            # With base=2: tasks at start-2, start-6, start-14 days
            timespan_seconds = 20 * DAY
            result = exp_schedule.get_previous_tasks(timespan_seconds)
            
            # Should find tasks going backwards from start date
            expected = [
                datetime(2022, 12, 26, 12, 0, 0),  # start - 6 days (2^2 + 2^1)
                datetime(2022, 12, 30, 12, 0, 0),  # start - 2 days (2^1)
            ]
            assert result == expected
        finally:
            src.schedule.exponential.datetime = original_datetime
    
    def test_get_next_tasks(self, exp_schedule):
        # Mock datetime.now() to be at start
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        import src.schedule.exponential
        original_datetime = src.schedule.exponential.datetime
        src.schedule.exponential.datetime = MockDateTime()
        
        try:
            # Look ahead 20 days: should find tasks at days 2, 6, 14
            timespan_seconds = 20 * DAY
            result = exp_schedule.get_next_tasks(timespan_seconds)
            
            expected = [
                datetime(2023, 1, 3, 12, 0, 0),   # start + 2 days
                datetime(2023, 1, 7, 12, 0, 0),   # start + 6 days
                datetime(2023, 1, 15, 12, 0, 0),  # start + 14 days
            ]
            assert result == expected
        finally:
            src.schedule.exponential.datetime = original_datetime
    
    def test_different_base_values(self):
        start = datetime(2023, 1, 1, 12, 0, 0)
        
        # Test base=3: intervals are 3, 9, 27... days
        schedule_3 = ExponentialSchedule(start, base=3)
        result = schedule_3.get_next_task(start)
        expected = datetime(2023, 1, 4, 12, 0, 0)  # start + 3 days
        assert result == expected
        
        # Test base=1: intervals are 1, 1, 1... days (edge case)
        schedule_1 = ExponentialSchedule(start, base=1)
        result = schedule_1.get_next_task(start)
        expected = datetime(2023, 1, 2, 12, 0, 0)  # start + 1 day
        assert result == expected
    
    def test_large_timespan_protection(self, exp_schedule):
        # Test infinite loop protection in get_previous_tasks
        current_time = datetime(2023, 1, 1, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        import src.schedule.exponential
        original_datetime = src.schedule.exponential.datetime
        src.schedule.exponential.datetime = MockDateTime()
        
        try:
            # Very large timespan should not cause infinite loop
            large_timespan = 10000 * DAY
            result = exp_schedule.get_previous_tasks(large_timespan)
            assert isinstance(result, list)
            assert len(result) <= 20  # Due to exp > 20 protection
        finally:
            src.schedule.exponential.datetime = original_datetime
    
    def test_edge_case_zero_timespan(self, exp_schedule):
        current_time = datetime(2023, 1, 10, 12, 0, 0)
        
        class MockDateTime:
            @staticmethod
            def now():
                return current_time
            def __call__(self, *args, **kwargs):
                return datetime(*args, **kwargs)
        
        import src.schedule.exponential
        original_datetime = src.schedule.exponential.datetime
        src.schedule.exponential.datetime = MockDateTime()
        
        try:
            result = exp_schedule.get_previous_tasks(0)
            assert result == []
            
            result = exp_schedule.get_next_tasks(0)
            assert result == []
        finally:
            src.schedule.exponential.datetime = original_datetime