"""Tests for src.habit.habit module."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from src.habit.habit import Habit
from src.habit.bucket import Bucket


class TestHabitSchedule:
    """Test schedule-related functionality."""

    def test_get_schedule_unknown_raises_error(self):
        """Test _get_schedule raises ValueError for unknown schedule type."""
        habit = Mock()
        habit.schedule = 'invalid'
        habit.started_at = datetime(2023, 1, 1, 12, 0, 0)
        
        with pytest.raises(ValueError, match="Unknown schedule type: invalid"):
            Habit._get_schedule(habit)


class TestHabitStreaks:
    """Test streak-related functionality."""

    @pytest.fixture
    def mock_habit(self):
        """Create a mock habit for testing."""
        habit = Mock()
        habit.allocated_time = 3600
        habit._schedule = Mock()
        habit._schedule.start = datetime(2023, 1, 1, 12, 0, 0)
        habit._schedule.get_scale.return_value = 3600
        return habit

    def test_get_streak_no_buckets(self, mock_habit):
        """Test get_streak returns 0 when no activity buckets exist."""
        mock_habit.get_activity_buckets.return_value = []
        
        result = Habit.get_streak(mock_habit)
        assert result == 0

    def test_get_streak_with_qualifying_buckets(self, mock_habit):
        """Test get_streak counts consecutive qualifying buckets."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        buckets = [
            Bucket(start_time - timedelta(days=1), start_time - timedelta(days=1)),
            Bucket(start_time, start_time)
        ]
        
        mock_habit.get_activity_buckets.return_value = buckets
        mock_habit._schedule.get_previous_task.side_effect = [
            start_time, start_time - timedelta(days=1), None
        ]
        
        with patch.object(Habit, '_qualifies_for_streak', side_effect=[True]):
            with patch('src.habit.habit.datetime') as mock_dt:
                mock_dt.now.return_value = start_time + timedelta(days=1)
                
                result = Habit.get_streak(mock_habit)
                assert result == 1

    def test_get_longest_streak_no_buckets(self, mock_habit):
        """Test get_longest_streak returns 0 when no buckets exist."""
        mock_habit.get_activity_buckets.return_value = []
        
        result = Habit.get_longest_streak(mock_habit)
        assert result == 0

    def test_qualifies_for_streak_early_bucket(self, mock_habit):
        """Test _qualifies_for_streak returns True for early buckets."""
        bucket = Bucket(
            mock_habit._schedule.start + timedelta(seconds=1800),
            mock_habit._schedule.start + timedelta(seconds=1800)
        )
        task = datetime(2023, 1, 2, 12, 0, 0)
        
        result = Habit._qualifies_for_streak(mock_habit, bucket, task)
        assert result is True

    def test_qualifies_for_streak_not_scheduled(self, mock_habit):
        """Test _qualifies_for_streak returns False when task not scheduled."""
        mock_habit._schedule.is_task_scheduled.return_value = False
        
        bucket = Bucket(datetime(2023, 1, 5, 12, 0, 0), datetime(2023, 1, 5, 12, 0, 0))
        task = datetime(2023, 1, 6, 12, 0, 0)
        
        result = Habit._qualifies_for_streak(mock_habit, bucket, task)
        assert result is False

    def test_qualifies_for_streak_insufficient_duration(self, mock_habit):
        """Test _qualifies_for_streak returns False for insufficient duration."""
        mock_habit._schedule.is_task_scheduled.return_value = True
        mock_habit.allocated_time = 3600
        
        bucket = Bucket(
            datetime(2023, 1, 5, 12, 0, 0), 
            datetime(2023, 1, 5, 12, 0, 0), 
            net_duration=1800
        )
        task = datetime(2023, 1, 6, 12, 0, 0)
        
        result = Habit._qualifies_for_streak(mock_habit, bucket, task)
        assert result is False

    def test_qualifies_for_streak_no_allocated_time_requirement(self, mock_habit):
        """Test _qualifies_for_streak with no allocated time requirement."""
        mock_habit._schedule.is_task_scheduled.return_value = True
        mock_habit.allocated_time = None
        
        bucket = Bucket(
            datetime(2023, 1, 5, 12, 0, 0),
            datetime(2023, 1, 5, 12, 0, 0),
            net_duration=100
        )
        task = datetime(2023, 1, 6, 12, 0, 0)
        
        result = Habit._qualifies_for_streak(mock_habit, bucket, task)
        assert result is True

    def test_qualifies_for_streak_meets_all_conditions(self, mock_habit):
        """Test _qualifies_for_streak returns True when all conditions met."""
        mock_habit._schedule.is_task_scheduled.return_value = True
        mock_habit.allocated_time = 1800
        
        bucket = Bucket(
            datetime(2023, 1, 5, 12, 0, 0),
            datetime(2023, 1, 5, 12, 0, 0),
            net_duration=3600
        )
        task = datetime(2023, 1, 6, 12, 0, 0)
        
        result = Habit._qualifies_for_streak(mock_habit, bucket, task)
        assert result is True


class TestHabitUtilities:
    """Test utility methods."""

    def test_get_schedule_returns_internal_schedule(self):
        """Test get_schedule method returns the internal schedule."""
        habit = Mock()
        habit._schedule = Mock()
        
        result = Habit.get_schedule(habit)
        assert result == habit._schedule


class TestHabitInit:
    """Test habit initialization."""
    
    @patch('src.habit.habit.Habit._get_schedule')
    def test_init_calls_get_schedule(self, mock_get_schedule):
        """Test __init__ calls _get_schedule to set up schedule."""
        mock_schedule = Mock()
        mock_get_schedule.return_value = mock_schedule
        
        with patch('src.habit.habit.BaseModel.__init__'):
            habit = Habit()
            
        mock_get_schedule.assert_called_once()
        assert habit._schedule == mock_schedule


class TestHabitScheduleTypes:
    """Test different schedule type creation."""
    
    @patch('schedule.hourly.HourlySchedule')
    def test_get_schedule_hourly(self, mock_hourly):
        """Test _get_schedule creates HourlySchedule for 'hourly'."""
        habit = Mock()
        habit.schedule = 'hourly'
        habit.started_at = datetime(2023, 1, 1)
        
        Habit._get_schedule(habit)
        
        mock_hourly.assert_called_once_with(start=habit.started_at)
    
    @patch('schedule.daily.DailySchedule')
    def test_get_schedule_daily(self, mock_daily):
        """Test _get_schedule creates DailySchedule for 'daily'."""
        habit = Mock()
        habit.schedule = 'daily'
        habit.started_at = datetime(2023, 1, 1)
        
        Habit._get_schedule(habit)
        
        mock_daily.assert_called_once_with(start=habit.started_at)
    
    @patch('schedule.weekly.WeeklySchedule')
    def test_get_schedule_weekly(self, mock_weekly):
        """Test _get_schedule creates WeeklySchedule for 'weekly'."""
        habit = Mock()
        habit.schedule = 'weekly'
        habit.started_at = datetime(2023, 1, 1)
        
        Habit._get_schedule(habit)
        
        mock_weekly.assert_called_once_with(start=habit.started_at)
    
    @patch('schedule.monthly.MonthlySchedule')
    def test_get_schedule_monthly(self, mock_monthly):
        """Test _get_schedule creates MonthlySchedule for 'monthly'."""
        habit = Mock()
        habit.schedule = 'monthly'
        habit.started_at = datetime(2023, 1, 1)
        
        Habit._get_schedule(habit)
        
        mock_monthly.assert_called_once_with(start=habit.started_at)
    
    @patch('schedule.exponential.ExponentialSchedule')
    def test_get_schedule_exponential(self, mock_exp):
        """Test _get_schedule creates ExponentialSchedule for 'exponential_3'."""
        habit = Mock()
        habit.schedule = 'exponential_3'
        habit.started_at = datetime(2023, 1, 1)
        
        Habit._get_schedule(habit)
        
        mock_exp.assert_called_once_with(start=habit.started_at, base=3)


class TestHabitActivityBuckets:
    """Test activity bucket functionality."""
    
    @pytest.fixture
    def mock_habit(self):
        """Create a mock habit for testing."""
        habit = Mock()
        habit._schedule = Mock()
        habit._schedule.get_scale.return_value = 3600
        return habit
    
    @patch('src.habit.habit.Log')
    def test_get_activity_buckets_uses_default_size(self, mock_log, mock_habit):
        """Test get_activity_buckets uses schedule scale as default size."""
        mock_log.select.return_value.group_by.return_value.where.return_value.limit.return_value.order_by.return_value = []
        
        Habit.get_activity_buckets(mock_habit)
        
        mock_habit._schedule.get_scale.assert_called_once()
    
    @patch('src.habit.habit.Log')
    def test_get_activity_buckets_with_custom_size(self, mock_log, mock_habit):
        """Test get_activity_buckets with custom size parameter."""
        mock_log.select.return_value.group_by.return_value.where.return_value.limit.return_value.order_by.return_value = []
        
        Habit.get_activity_buckets(mock_habit, size=1800)
        
        mock_habit._schedule.get_scale.assert_not_called()
    
    @patch('src.habit.habit.Log')
    def test_get_activity_buckets_with_limit(self, mock_log, mock_habit):
        """Test get_activity_buckets applies limit parameter."""
        mock_query = Mock()
        mock_log.select.return_value.group_by.return_value.where.return_value.limit.return_value.order_by.return_value = []
        mock_log.select.return_value.group_by.return_value.where.return_value.limit.return_value = mock_query
        
        Habit.get_activity_buckets(mock_habit, limit=10)
        
        mock_log.select.return_value.group_by.return_value.where.return_value.limit.assert_called_with(10)