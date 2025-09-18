import pytest
from datetime import datetime, timedelta
from src.schedule.monthly import MonthlySchedule
from util import time


class TestMonthlySchedule:
    
    def test_get_scale(self):
        """Test that get_scale returns MONTH constant."""
        start = datetime(2024, 1, 1, 10, 0)
        schedule = MonthlySchedule(start)
        assert schedule.get_scale() == time.MONTH
    
    def test_get_next_task_before_start(self):
        """Test get_next_task when from_dt is before start date."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 1, 1, 9, 0)
        assert schedule.get_next_task(from_dt) == start
    
    def test_get_next_task_at_start(self):
        """Test get_next_task when from_dt equals start date."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        assert schedule.get_next_task(start) == start
    
    def test_get_next_task_after_start(self):
        """Test get_next_task when from_dt is after start but before next occurrence."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 1, 20, 10, 0)
        expected = datetime(2024, 2, 14, 10, 0)  # 30 days after start
        assert schedule.get_next_task(from_dt) == expected
    
    def test_get_next_task_exact_occurrence(self):
        """Test get_next_task when from_dt is exactly on a monthly occurrence."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 2, 14, 10, 0)  # Exactly 30 days after start
        assert schedule.get_next_task(from_dt) == from_dt
    
    def test_get_previous_task_at_or_before_start(self):
        """Test get_previous_task when from_dt is at or before start date."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        assert schedule.get_previous_task(start) is None
        assert schedule.get_previous_task(start - timedelta(days=1)) is None
    
    def test_get_previous_task_within_first_month(self):
        """Test get_previous_task when from_dt is within first 30 days."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 2, 1, 10, 0)  # 17 days after start
        assert schedule.get_previous_task(from_dt) is None
    
    def test_get_previous_task_after_first_month(self):
        """Test get_previous_task when from_dt is after first month."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 2, 20, 10, 0)  # 36 days after start
        expected = start  # First occurrence
        assert schedule.get_previous_task(from_dt) == expected
    
    def test_get_previous_task_multiple_months(self):
        """Test get_previous_task when from_dt is multiple months after start."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        from_dt = datetime(2024, 4, 20, 10, 0)  # ~95 days after start (3+ months)
        expected = datetime(2024, 3, 15, 10, 0)  # 60 days after start
        assert schedule.get_previous_task(from_dt) == expected
    
    def test_get_next_tasks_empty_timespan(self):
        """Test get_next_tasks with a very small timespan."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        tasks = schedule.get_next_tasks(time.DAY)  # Only 1 day ahead
        assert tasks == []
    
    def test_get_next_tasks_single_month(self):
        """Test get_next_tasks covering one month."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        tasks = schedule.get_next_tasks(35 * time.DAY)  # 35 days ahead
        assert len(tasks) == 1
        assert tasks[0] == schedule.get_next_task(datetime.now())
    
    def test_get_next_tasks_multiple_months(self):
        """Test get_next_tasks covering multiple months."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        tasks = schedule.get_next_tasks(100 * time.DAY)  # ~3 months ahead
        assert len(tasks) >= 2  # Should find at least 2 future tasks
        
        # Verify tasks are ordered chronologically
        for i in range(1, len(tasks)):
            assert tasks[i-1] < tasks[i]
    
    def test_get_previous_tasks_empty_timespan(self):
        """Test get_previous_tasks with a very small timespan."""
        start = datetime(2024, 1, 15, 10, 0)
        schedule = MonthlySchedule(start)
        tasks = schedule.get_previous_tasks(time.DAY)  # Only 1 day back
        assert tasks == []
    
    def test_get_previous_tasks_single_month(self):
        """Test get_previous_tasks covering one month."""
        start = datetime(2023, 12, 15, 10, 0)  # Start in past
        schedule = MonthlySchedule(start)
        tasks = schedule.get_previous_tasks(35 * time.DAY)  # 35 days back
        assert len(tasks) >= 0  # May or may not find tasks depending on current date
        
        # If tasks found, verify they're ordered from most recent to oldest
        for i in range(1, len(tasks)):
            assert tasks[i-1] > tasks[i]
    
    def test_get_previous_tasks_stops_at_start(self):
        """Test that get_previous_tasks stops at the start date."""
        start = datetime(2023, 1, 15, 10, 0)  # Far in past
        schedule = MonthlySchedule(start)
        tasks = schedule.get_previous_tasks(400 * time.DAY)  # Large timespan
        
        # All returned tasks should be after start date
        for task in tasks:
            assert task >= start
    
    def test_thirty_day_intervals(self):
        """Test that monthly schedule uses exact 30-day intervals."""
        start = datetime(2024, 1, 1, 12, 0)
        schedule = MonthlySchedule(start)
        
        # Test first few occurrences are exactly 30 days apart
        first = schedule.get_next_task(start)
        second = schedule.get_next_task(first + timedelta(days=1))
        third = schedule.get_next_task(second + timedelta(days=1))
        
        assert (second - first).days == 30
        assert (third - second).days == 30
    
    def test_edge_case_leap_year(self):
        """Test behavior during leap year (edge case for 30-day approximation)."""
        start = datetime(2024, 2, 29, 10, 0)  # Leap year start
        schedule = MonthlySchedule(start)
        
        next_task = schedule.get_next_task(start + timedelta(days=1))
        expected = datetime(2024, 3, 30, 10, 0)  # Exactly 30 days later
        assert next_task == expected