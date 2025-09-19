from datetime import datetime, timedelta
from unittest.mock import patch

from src.schedule.hourly import HourlySchedule
from src.util.time import HOUR


class TestHourlySchedule:
    def test_get_previous_task_returns_none_when_from_dt_at_start(self):
        """Test get_previous_task returns None at exact start time."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_previous_task(start) is None

    def test_get_previous_task_returns_none_when_from_dt_before_start(self):
        """Test get_previous_task returns None for datetime before start."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_previous_task(start - timedelta(hours=1)) is None

    def test_get_previous_task_returns_none_when_less_than_hour_since_start(self):
        """Test get_previous_task returns None when less than one hour passed."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_previous_task(start + timedelta(minutes=30)) is None

    def test_get_previous_task_returns_start_when_exactly_one_hour_later(self):
        """Test get_previous_task returns start time exactly one hour later."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        result = schedule.get_previous_task(start + timedelta(hours=1))
        assert result == start

    def test_get_previous_task_returns_correct_hour_multiple_hours_later(self):
        """Test get_previous_task returns correct hour for multiple hours later."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        result = schedule.get_previous_task(start + timedelta(hours=3, minutes=30))
        assert result == start + timedelta(hours=2)

    def test_get_next_task_returns_start_when_from_dt_before_start(self):
        """Test get_next_task returns start time when before start."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_next_task(start - timedelta(hours=1)) == start

    def test_get_next_task_returns_next_hour_when_after_start(self):
        """Test get_next_task returns next hour when after start."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        result = schedule.get_next_task(start + timedelta(minutes=30))
        assert result == start + timedelta(hours=1)

    def test_get_next_task_returns_correct_next_hour_multiple_hours_later(self):
        """Test get_next_task returns correct next hour for multiple hours later."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        result = schedule.get_next_task(start + timedelta(hours=2, minutes=15))
        assert result == start + timedelta(hours=3)

    def test_get_previous_tasks_empty_when_zero_timespan(self):
        """Test get_previous_tasks returns empty list for zero timespan."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_previous_tasks(0) == []

    @patch('src.schedule.hourly.datetime')
    def test_get_previous_tasks_returns_correct_count(self, mock_datetime):
        """Test get_previous_tasks returns correct number of tasks."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        mock_datetime.now.return_value = start + timedelta(hours=3)
        tasks = schedule.get_previous_tasks(HOUR * 2)  # 2 hours back
        assert len(tasks) == 2

    @patch('src.schedule.hourly.datetime')
    def test_get_previous_tasks_ordered_most_recent_first(self, mock_datetime):
        """Test get_previous_tasks returns tasks in reverse chronological order."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        mock_datetime.now.return_value = start + timedelta(hours=3)
        tasks = schedule.get_previous_tasks(HOUR * 3)
        assert tasks[0] > tasks[1]  # Most recent first

    def test_get_scale_returns_hour_constant(self):
        """Test that get_scale returns HOUR constant."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)
        assert schedule.get_scale() == HOUR

    def test_get_previous_task_get_next_task_consistency(self):
        """Test consistency between get_previous_task and get_next_task methods."""
        start = datetime(2023, 1, 1, 10, 0)
        schedule = HourlySchedule(start)

        # Start from a scheduled task time
        t1 = schedule.get_next_task(start + timedelta(hours=2))

        # Go forward 3 steps
        t2 = schedule.get_next_task(t1)
        t3 = schedule.get_next_task(t2)
        t4 = schedule.get_next_task(t3)

        # Go backward 3 steps - should return to t1
        back1 = schedule.get_previous_task(t4)
        back2 = schedule.get_previous_task(back1)
        back3 = schedule.get_previous_task(back2)

        assert back1 == t3
        assert back2 == t2
        assert back3 == t1