import pytest
from datetime import datetime
from unittest.mock import Mock
from src.analytics import (
    get_habit_with_longest_streak,
    group_habits_by_schedule,
    get_time_spent,
    get_completion_rate
)
from src.habit.bucket import Bucket


class TestGetHabitWithLongestStreak:
    
    def test_single_habit(self):
        """Test with a single habit."""
        habit = Mock()
        habit.get_longest_streak.return_value = 5
        result = get_habit_with_longest_streak([habit])
        assert result == habit
    
    def test_multiple_habits_different_streaks(self):
        """Test with multiple habits having different streak lengths."""
        habit1 = Mock()
        habit1.get_longest_streak.return_value = 3
        habit2 = Mock()
        habit2.get_longest_streak.return_value = 7
        habit3 = Mock()
        habit3.get_longest_streak.return_value = 2
        
        result = get_habit_with_longest_streak([habit1, habit2, habit3])
        assert result == habit2
    
    def test_multiple_habits_same_streak(self):
        """Test with multiple habits having the same longest streak."""
        habit1 = Mock()
        habit1.get_longest_streak.return_value = 5
        habit2 = Mock()
        habit2.get_longest_streak.return_value = 5
        
        result = get_habit_with_longest_streak([habit1, habit2])
        # Should return one of them (max() behavior with ties)
        assert result in [habit1, habit2]
    
    def test_zero_streaks(self):
        """Test with habits having zero streaks."""
        habit1 = Mock()
        habit1.get_longest_streak.return_value = 0
        habit2 = Mock()
        habit2.get_longest_streak.return_value = 0
        
        result = get_habit_with_longest_streak([habit1, habit2])
        assert result in [habit1, habit2]
    
    def test_empty_list_raises_error(self):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError):
            get_habit_with_longest_streak([])


class TestGroupHabitsBySchedule:
    
    def test_single_schedule_type(self):
        """Test grouping habits with the same schedule."""
        habit1 = Mock()
        habit1.schedule = 'daily'
        habit2 = Mock()
        habit2.schedule = 'daily'
        
        # Convert groupby result immediately to avoid consumption issues
        result = [(schedule, list(group)) for schedule, group in group_habits_by_schedule([habit1, habit2])]
        assert len(result) == 1
        schedule, habits_list = result[0]
        assert schedule == 'daily'
        assert habits_list == [habit1, habit2]
    
    def test_multiple_schedule_types(self):
        """Test grouping habits with different schedules."""
        habit1 = Mock()
        habit1.schedule = 'daily'
        habit2 = Mock()
        habit2.schedule = 'weekly'
        habit3 = Mock()
        habit3.schedule = 'daily'
        
        # Convert groupby result immediately to avoid consumption issues
        result = [(schedule, list(group)) for schedule, group in group_habits_by_schedule([habit1, habit2, habit3])]
        assert len(result) == 2
        
        # Convert to dict for easier testing
        result_dict = {schedule: habits for schedule, habits in result}
        
        assert 'daily' in result_dict
        assert 'weekly' in result_dict
        assert len(result_dict['daily']) == 2
        assert len(result_dict['weekly']) == 1
        assert habit1 in result_dict['daily']
        assert habit3 in result_dict['daily']
        assert habit2 in result_dict['weekly']
    
    def test_empty_list(self):
        """Test grouping empty list."""
        result = list(group_habits_by_schedule([]))
        assert result == []
    
    def test_sorting_by_schedule(self):
        """Test that habits are sorted by schedule before grouping."""
        habit1 = Mock()
        habit1.schedule = 'weekly'
        habit2 = Mock()
        habit2.schedule = 'daily'
        habit3 = Mock()
        habit3.schedule = 'monthly'
        
        result = list(group_habits_by_schedule([habit1, habit2, habit3]))
        schedules = [schedule for schedule, _ in result]
        assert schedules == sorted(['weekly', 'daily', 'monthly'])


class TestGetTimeSpent:
    
    def test_single_bucket(self):
        """Test time calculation with single bucket."""
        bucket = Bucket(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
            net_duration=3600
        )
        assert get_time_spent([bucket]) == 3600
    
    def test_multiple_buckets(self):
        """Test time calculation with multiple buckets."""
        bucket1 = Bucket(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
            net_duration=1800
        )
        bucket2 = Bucket(
            start=datetime(2024, 1, 2),
            end=datetime(2024, 1, 2),
            net_duration=2400
        )
        bucket3 = Bucket(
            start=datetime(2024, 1, 3),
            end=datetime(2024, 1, 3),
            net_duration=600
        )
        assert get_time_spent([bucket1, bucket2, bucket3]) == 4800
    
    def test_empty_buckets_list(self):
        """Test time calculation with empty list."""
        assert get_time_spent([]) == 0
    
    def test_zero_duration_buckets(self):
        """Test time calculation with zero duration buckets."""
        bucket1 = Bucket(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
            net_duration=0
        )
        bucket2 = Bucket(
            start=datetime(2024, 1, 2),
            end=datetime(2024, 1, 2),
            net_duration=0
        )
        assert get_time_spent([bucket1, bucket2]) == 0
    
    def test_mixed_duration_buckets(self):
        """Test time calculation with mix of zero and positive durations."""
        bucket1 = Bucket(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 1),
            net_duration=0
        )
        bucket2 = Bucket(
            start=datetime(2024, 1, 2),
            end=datetime(2024, 1, 2),
            net_duration=1200
        )
        assert get_time_spent([bucket1, bucket2]) == 1200


class TestGetTaskVsScheduleRatio:
    
    def test_normal_ratio(self):
        """Test normal case where buckets < previous_tasks."""
        assert get_completion_rate(3, 5) == 0.6
    
    def test_perfect_ratio(self):
        """Test case where buckets equals previous_tasks."""
        assert get_completion_rate(5, 5) == 1.0
    
    def test_over_completion(self):
        """Test case where buckets > previous_tasks (capped at 1)."""
        assert get_completion_rate(7, 5) == 1.0
    
    def test_zero_previous_tasks(self):
        """Test edge case where previous_tasks is 0."""
        assert get_completion_rate(3, 0) == 1.0
    
    def test_zero_buckets_zero_previous(self):
        """Test edge case where both values are 0."""
        assert get_completion_rate(0, 0) == 0.0
    
    def test_zero_buckets_nonzero_previous(self):
        """Test case where buckets is 0 but previous_tasks > 0."""
        assert get_completion_rate(0, 5) == 0.0
    
    def test_fractional_values(self):
        """Test with fractional results."""
        assert get_completion_rate(1, 3) == pytest.approx(0.3333, rel=1e-3)
        assert get_completion_rate(2, 7) == pytest.approx(0.2857, rel=1e-3)