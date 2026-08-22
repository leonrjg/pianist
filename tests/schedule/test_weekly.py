from datetime import datetime, timedelta
from unittest.mock import patch
from src.core.schedule.weekly import WeeklySchedule
from src.core.util import time

FAR_END = datetime(2100, 1, 1, 10, 0)


class TestWeeklySchedule:
    
    def test_get_previous_task_same_week(self):
        """Test get_previous_task returns the start occurrence for a from_dt later the same week.

        start (01-01) is the most recent occurrence strictly before from_dt (01-05),
        consistent with test_get_previous_task_next_week.
        """
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 5, 15, 0)  # Sunday same week

        result = schedule.get_previous_task(from_dt)

        assert result == start
    
    def test_get_previous_task_before_start(self):
        """Test get_previous_task returns None when from_dt is before start."""
        start = datetime(2025, 1, 8, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 1, 15, 0)  # Previous Wednesday
        
        result = schedule.get_previous_task(from_dt)
        
        assert result is None
    
    def test_get_previous_task_next_week(self):
        """Test get_previous_task returns previous week occurrence."""
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 8, 15, 0)  # Next Wednesday
        
        result = schedule.get_previous_task(from_dt)
        
        assert result == start
    
    def test_get_previous_task_multiple_weeks(self):
        """Test get_previous_task returns correct previous week."""
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 15, 15, 0)  # Two weeks later
        
        result = schedule.get_previous_task(from_dt)
        
        expected = datetime(2025, 1, 8, 10, 0)  # One week after start
        assert result == expected
    
    def test_get_next_task_before_start(self):
        """Test get_next_task returns start when from_dt is before start."""
        start = datetime(2025, 1, 8, 10, 0)
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 1, 15, 0)
        
        result = schedule.get_next_task(from_dt)
        
        assert result == start
    
    def test_get_next_task_same_date(self):
        """Test get_next_task returns same occurrence when from_dt matches scheduled week."""
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 8, 8, 0)  # Same day next week, earlier time
        
        result = schedule.get_next_task(from_dt)
        
        expected = datetime(2025, 1, 8, 10, 0)
        assert result == expected
    
    def test_get_next_task_after_scheduled_week(self):
        """Test get_next_task returns next week when from_dt is after current week occurrence."""
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        from_dt = datetime(2025, 1, 9, 15, 0)  # Thursday after first Wednesday
        
        result = schedule.get_next_task(from_dt)
        
        expected = datetime(2025, 1, 15, 10, 0)  # Next Wednesday
        assert result == expected
    
    @patch('src.core.schedule.weekly.datetime')
    def test_get_previous_tasks(self, mock_datetime):
        """Test get_previous_tasks returns correct number of tasks."""
        mock_datetime.now.return_value = datetime(2025, 1, 29, 12, 0)
        
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)
        timespan = 21 * time.DAY  # 3 weeks
        
        result = schedule.get_previous_tasks(timespan)
        
        expected = [
            datetime(2025, 1, 22, 10, 0),  # Most recent
            datetime(2025, 1, 15, 10, 0),
            datetime(2025, 1, 8, 10, 0)   # Oldest
        ]
        assert result == expected
    
    @patch('src.core.schedule.weekly.datetime')
    def test_get_next_tasks(self, mock_datetime):
        """Test get_next_tasks returns correct number of future tasks."""
        mock_datetime.now.return_value = datetime(2025, 1, 1, 8, 0)  # Before first task
        
        start = datetime(2025, 1, 1, 10, 0)
        schedule = WeeklySchedule(start, FAR_END)
        timespan = 14 * time.DAY  # 2 weeks
        
        result = schedule.get_next_tasks(timespan)
        
        expected = [
            datetime(2025, 1, 1, 10, 0),   # Start date
            datetime(2025, 1, 8, 10, 0)   # Next week
        ]
        assert result == expected
    
    @patch('src.core.schedule.weekly.datetime')
    def test_get_previous_tasks_empty(self, mock_datetime):
        """Test get_previous_tasks returns empty list when now is before any occurrence."""
        mock_datetime.now.return_value = datetime(2025, 1, 1, 9, 0)  # Before start (10:00)

        start = datetime(2025, 1, 1, 10, 0)
        schedule = WeeklySchedule(start, FAR_END)
        timespan = 7 * time.DAY

        result = schedule.get_previous_tasks(timespan)

        assert result == []
    
    def test_get_scale(self):
        """Test get_scale returns one week (7 days)."""
        start = datetime(2025, 1, 1, 10, 0)
        schedule = WeeklySchedule(start, FAR_END)

        result = schedule.get_scale()

        assert result == time.DAY * 7

    def test_get_previous_task_get_next_task_consistency(self):
        """Test consistency between get_previous_task and get_next_task methods."""
        start = datetime(2025, 1, 1, 10, 0)  # Wednesday
        schedule = WeeklySchedule(start, FAR_END)

        # Start from a scheduled task time
        t1 = schedule.get_next_task(start + timedelta(weeks=2))

        # Go forward 3 steps, using slightly offset times to avoid exact matches
        t2 = schedule.get_next_task(t1 + timedelta(seconds=1))
        t3 = schedule.get_next_task(t2 + timedelta(seconds=1))
        t4 = schedule.get_next_task(t3 + timedelta(seconds=1))

        # Go backward 3 steps - should return to original tasks
        back1 = schedule.get_previous_task(t4)
        back2 = schedule.get_previous_task(back1)
        back3 = schedule.get_previous_task(back2)

        assert back1 == t3
        assert back2 == t2
        assert back3 == t1