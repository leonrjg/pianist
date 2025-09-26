"""Tests for src.cli module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner
from peewee import DoesNotExist

from src.cli import cli, save, delete, play, stats, _display_habit_stats, _display_all_habits_stats


class TestSaveCommand:
    """Test save command functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('src.cli.db')
    @patch('src.cli.Habit')
    @patch('src.cli.HabitTracker')
    def test_save_new_habit_minimal(self, mock_habit_tracker, mock_habit, mock_db):
        """Test saving a new habit with minimal parameters."""
        mock_habit_instance = Mock()
        mock_habit_instance.name = 'test-habit'
        mock_habit_instance.schedule = 'daily'
        mock_habit.get_or_none.return_value = None
        mock_habit.create.return_value = mock_habit_instance

        result = self.runner.invoke(save, ['test-habit', '--schedule', 'daily'])

        assert result.exit_code == 0
        assert "Saved habit 'test-habit' with schedule 'daily'" in result.output
        mock_habit.get_or_none.assert_called_once()
        mock_habit.create.assert_called_once_with(name='test-habit', schedule='daily')
        mock_habit_instance.save.assert_called_once()

    @patch('src.cli.db')
    @patch('src.cli.Habit')
    @patch('src.cli.HabitTracker')
    def test_save_existing_habit_with_duration_and_timeout(self, mock_habit_tracker, mock_habit, mock_db):
        """Test updating existing habit with duration and timeout."""
        mock_saved_habit = Mock()
        mock_habit.get_or_none.return_value = mock_saved_habit
        
        result = self.runner.invoke(save, [
            'existing-habit', '--schedule', 'weekly', 
            '--duration', '30', '--timeout', '120'
        ])
        
        assert result.exit_code == 0
        assert mock_saved_habit.allocated_time == 1800  # 30 minutes * 60
        assert mock_saved_habit.inactivity_threshold == 120
        mock_saved_habit.save.assert_called_once()

    @patch('src.cli.db')
    @patch('src.cli.Habit')
    @patch('src.cli.HabitTracker')
    def test_save_with_trackers(self, mock_habit_tracker, mock_habit, mock_db):
        """Test saving habit with trackers."""
        mock_saved_habit = Mock()
        mock_habit.get_or_none.return_value = mock_saved_habit
        mock_habit_tracker.create_json_config.return_value = {'test': 'config'}
        
        result = self.runner.invoke(save, [
            'habit-with-trackers', '--schedule', 'hourly',
            '--track', 'io', '--track', 'window',
            '--track-args', 'key=value&key2=value2'
        ])
        
        assert result.exit_code == 0
        assert mock_habit_tracker.insert.call_count == 2


class TestDeleteCommand:
    """Test delete command functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('src.cli.Habit')
    def test_delete_existing_habit(self, mock_habit):
        """Test successful deletion of existing habit."""
        mock_habit_instance = Mock()
        mock_habit.get.return_value = mock_habit_instance
        
        result = self.runner.invoke(delete, ['test-habit'])
        
        assert result.exit_code == 0
        assert "Successfully deleted habit 'test-habit'" in result.output
        mock_habit_instance.delete_instance.assert_called_once()

    @patch('src.cli.Habit')
    def test_delete_nonexistent_habit(self, mock_habit):
        """Test deletion of nonexistent habit."""
        mock_habit.get.side_effect = DoesNotExist()
        
        result = self.runner.invoke(delete, ['nonexistent'])
        
        assert result.exit_code == 1
        assert "does not exist" in result.output


class TestPlayCommand:
    """Test play command functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('src.cli.Habit')
    def test_play_nonexistent_habit(self, mock_habit):
        """Test playing nonexistent habit."""
        mock_habit.get.side_effect = DoesNotExist()
        
        result = self.runner.invoke(play, ['nonexistent'])
        
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch('src.cli.Session')
    @patch('src.cli.Habit')
    @patch('src.cli.time.sleep')
    @patch('src.cli.get_friendly_elapsed')
    def test_play_habit_interrupted(self, mock_get_friendly_elapsed, mock_sleep, mock_habit, mock_session_class):
        """Test playing habit that gets interrupted."""
        mock_habit_instance = Mock()
        mock_habit.get.return_value = mock_habit_instance

        mock_session = Mock()
        mock_session.is_active.side_effect = [True, False]  # First True, then False
        mock_session.get_elapsed_time.return_value = 60
        mock_session.start_time = 1000.0  # Mock start time as float
        mock_session.log = None
        mock_session_class.return_value = mock_session

        mock_get_friendly_elapsed.return_value = "1m"
        mock_sleep.side_effect = KeyboardInterrupt()  # Simulate Ctrl+C

        result = self.runner.invoke(play, ['test-habit'], input='\n')

        assert result.exit_code == 0
        mock_session.start.assert_called_once()
        mock_session.end.assert_called_once()
        mock_session.join.assert_called_once()


class TestStatsCommand:
    """Test stats command functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('src.cli._display_habit_stats')
    @patch('src.cli.Habit')
    def test_stats_specific_habit(self, mock_habit, mock_display_habit_stats):
        """Test stats for specific habit."""
        mock_habit_instance = Mock()
        mock_habit.get.return_value = mock_habit_instance
        
        result = self.runner.invoke(stats, ['test-habit'])
        
        assert result.exit_code == 0
        mock_display_habit_stats.assert_called_once_with(mock_habit_instance)

    @patch('src.cli.Habit')
    def test_stats_nonexistent_habit(self, mock_habit):
        """Test stats for nonexistent habit."""
        mock_habit.get.side_effect = DoesNotExist()
        
        result = self.runner.invoke(stats, ['nonexistent'])
        
        assert result.exit_code == 1
        assert "does not exist" in result.output

    @patch('src.cli._display_all_habits_stats')
    @patch('src.cli.Habit')
    def test_stats_all_habits(self, mock_habit, mock_display_all_habits_stats):
        """Test stats for all habits."""
        mock_habit.select.return_value = [Mock(), Mock()]
        
        result = self.runner.invoke(stats, [])
        
        assert result.exit_code == 0
        mock_display_all_habits_stats.assert_called_once()

    @patch('src.cli.Habit')
    def test_stats_no_habits(self, mock_habit):
        """Test stats when no habits exist."""
        mock_habit.select.return_value = []
        
        result = self.runner.invoke(stats, [])
        
        assert result.exit_code == 0
        assert "No habits found" in result.output


class TestDisplayFunctions:
    """Test display helper functions."""

    @patch('src.cli.click.echo')
    @patch('src.cli.get_friendly_datetime')
    @patch('src.cli.get_friendly_elapsed')
    @patch('src.cli.analytics')
    def test_display_habit_stats_complete(self, mock_analytics, mock_get_friendly_elapsed, 
                                        mock_get_friendly_datetime, mock_echo):
        """Test _display_habit_stats with complete habit data."""
        # Setup mock habit
        mock_habit = Mock()
        mock_habit.name = 'test-habit'
        mock_habit.schedule = 'daily'
        mock_habit.allocated_time = 3600
        mock_habit.inactivity_threshold = 300
        
        # Setup schedule mock
        from datetime import datetime
        mock_schedule = Mock()
        mock_schedule.get_scale.return_value = 86400
        mock_schedule.get_next_task.return_value = Mock()
        mock_schedule.start = datetime(2023, 1, 1, 12, 0, 0)
        mock_schedule.get_previous_tasks.return_value = [Mock(), Mock()]
        mock_habit.get_schedule.return_value = mock_schedule
        
        # Setup trackers mock
        mock_tracker = Mock()
        mock_tracker.tracker = 'io'
        mock_tracker.get_config.return_value = ''
        mock_habit.trackers.where.return_value = [mock_tracker]
        
        # Setup buckets mock
        mock_bucket = Mock()
        mock_bucket.start = Mock()
        mock_bucket.end = Mock()
        mock_bucket.net_duration = 1800
        mock_bucket.sessions = 2
        mock_habit.get_activity_buckets.return_value = [mock_bucket]
        
        # Setup habit methods
        mock_habit.get_streak.return_value = 5
        mock_habit.get_longest_streak.return_value = 10
        
        # Setup mock returns
        mock_get_friendly_datetime.return_value = 'Yesterday'
        mock_get_friendly_elapsed.return_value = '30m'
        mock_analytics.get_time_spent.return_value = 7200
        mock_analytics.get_completion_rate.return_value = 0.85
        
        _display_habit_stats(mock_habit)
        
        # Verify function was called
        assert mock_echo.call_count > 0

    @patch('src.cli.click.echo')
    @patch('src.cli.analytics')
    def test_display_all_habits_stats(self, mock_analytics, mock_echo):
        """Test _display_all_habits_stats with multiple habits."""
        # Setup mock habits
        mock_habit1 = Mock()
        mock_habit1.name = 'habit1'
        mock_habit1.schedule = 'daily'
        mock_habit1.get_longest_streak.return_value = 5
        mock_schedule1 = Mock()
        mock_schedule1.get_scale.return_value = 86400
        mock_habit1.get_schedule.return_value = mock_schedule1
        
        mock_habit2 = Mock()
        mock_habit2.name = 'habit2'
        mock_habit2.schedule = 'weekly'
        mock_habit2.get_longest_streak.return_value = 3
        mock_schedule2 = Mock()
        mock_schedule2.get_scale.return_value = 604800
        mock_habit2.get_schedule.return_value = mock_schedule2
        
        habits = [mock_habit1, mock_habit2]
        
        # Setup analytics mocks
        mock_analytics.group_habits_by_schedule.return_value = [
            ('daily', [mock_habit1]),
            ('weekly', [mock_habit2])
        ]
        mock_analytics.get_habit_with_longest_streak.return_value = mock_habit1
        
        _display_all_habits_stats(habits)
        
        # Verify function was called
        assert mock_echo.call_count > 0


class TestCliGroup:
    """Test CLI group functionality."""

    def setup_method(self):
        """Set up test runner."""
        self.runner = CliRunner()

    @patch('src.cli.initialize_database')
    def test_cli_no_command_shows_help(self, mock_init_db):
        """Test CLI without command shows help."""
        result = self.runner.invoke(cli, [])
        
        assert result.exit_code == 0
        assert "Usage:" in result.output
        mock_init_db.assert_not_called()

    @patch('src.cli.initialize_database')
    def test_cli_with_command_initializes_database(self, mock_init_db):
        """Test CLI with command initializes database."""
        with patch('src.cli.Habit'):
            result = self.runner.invoke(cli, ['stats'])
            
            mock_init_db.assert_called_once()