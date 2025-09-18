"""Tests for src.tracker.io module."""
import pytest
import time
from unittest.mock import Mock, patch
from src.tracker.io import IOTracker, EPSILON


class TestIOTracker:
    """Test IOTracker functionality."""

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_init_starts_listeners(self, mock_keyboard, mock_mouse):
        """Test __init__ starts mouse and keyboard listeners."""
        mock_mouse_listener = Mock()
        mock_keyboard_listener = Mock()
        mock_mouse.Listener.return_value = mock_mouse_listener
        mock_keyboard.Listener.return_value = mock_keyboard_listener
        
        tracker = IOTracker()
        
        mock_mouse.Listener.assert_called_once()
        mock_keyboard.Listener.assert_called_once()
        mock_mouse_listener.start.assert_called_once()
        mock_keyboard_listener.start.assert_called_once()
        
        assert tracker._mouse_listener == mock_mouse_listener
        assert tracker._keyboard_listener == mock_keyboard_listener

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_pulse_function_updates_last_active(self, mock_keyboard, mock_mouse):
        """Test that the pulse function updates last_active timestamp."""
        with patch('src.tracker.io.time.time', return_value=123456789):
            tracker = IOTracker()
            
            # Get the pulse function that was passed to the listeners
            pulse_func = mock_mouse.Listener.call_args[1]['on_move']
            
            pulse_func()
            
            assert tracker.last_active == 123456789

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_is_active_true_when_recent_activity(self, mock_keyboard, mock_mouse):
        """Test is_active returns True when recent activity detected."""
        with patch('src.tracker.io.time.time', side_effect=[1000, 1002]):
            tracker = IOTracker()
            pulse_func = mock_mouse.Listener.call_args[1]['on_move']
            pulse_func()  # Sets last_active to 1000
            
            # Current time is 1002, difference is 2 seconds < EPSILON (5)
            result = tracker.is_active()
            assert result is True

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_is_active_false_when_old_activity(self, mock_keyboard, mock_mouse):
        """Test is_active returns False when activity is too old."""
        with patch('src.tracker.io.time.time', side_effect=[1000, 1010]):
            tracker = IOTracker()
            pulse_func = mock_mouse.Listener.call_args[1]['on_move']
            pulse_func()  # Sets last_active to 1000
            
            # Current time is 1010, difference is 10 seconds > EPSILON (5)
            result = tracker.is_active()
            assert result is False

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_is_active_false_when_no_activity(self, mock_keyboard, mock_mouse):
        """Test is_active returns falsy value when no activity recorded."""
        with patch('src.tracker.io.time.time', return_value=1000):
            tracker = IOTracker()
            # Don't trigger any pulse events
            
            result = tracker.is_active()
            assert not result  # Should be falsy (None in this case)

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard') 
    def test_pulse_works_for_keyboard_listener(self, mock_keyboard, mock_mouse):
        """Test that keyboard listener also triggers pulse function."""
        with patch('src.tracker.io.time.time', return_value=987654321):
            tracker = IOTracker()
            
            # Get the pulse function that was passed to the keyboard listener
            pulse_func = mock_keyboard.Listener.call_args[1]['on_press']
            
            pulse_func()
            
            assert tracker.last_active == 987654321

    @patch('src.tracker.io.mouse')
    @patch('src.tracker.io.keyboard')
    def test_epsilon_boundary_condition(self, mock_keyboard, mock_mouse):
        """Test is_active at exactly EPSILON boundary."""
        with patch('src.tracker.io.time.time', side_effect=[1000, 1000 + EPSILON]):
            tracker = IOTracker()
            pulse_func = mock_mouse.Listener.call_args[1]['on_move']
            pulse_func()  # Sets last_active to 1000
            
            # Current time is exactly EPSILON seconds later
            result = tracker.is_active()
            assert result is False  # >= EPSILON should be False