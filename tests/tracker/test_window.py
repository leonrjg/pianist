"""Tests for src.tracker.window module."""
import pytest
import time
from unittest.mock import Mock, patch
from src.tracker.window import WindowTracker


class TestWindowTracker:
    """Test WindowTracker functionality."""

    def test_init_stores_keywords(self):
        """Test __init__ stores keywords list."""
        keywords = ['vim', 'emacs', 'code']
        tracker = WindowTracker(keywords)
        
        assert tracker.keywords == keywords

    @patch('src.tracker.window.pywinctl.getAllTitles')
    @patch('src.tracker.window.pywinctl.getAllAppsNames')
    def test_get_active_windows_success(self, mock_get_apps, mock_get_titles):
        """Test _get_active_windows returns combined titles and app names."""
        mock_get_titles.return_value = ['Window Title 1', 'Window Title 2']
        mock_get_apps.return_value = ['App1', 'App2']
        
        result = WindowTracker._get_active_windows()
        
        expected = ['Window Title 1', 'Window Title 2', 'App1', 'App2']
        assert result == expected

    @patch('src.tracker.window.pywinctl.getAllTitles')
    @patch('src.tracker.window.pywinctl.getAllAppsNames')
    @patch('src.tracker.window.logging.error')
    def test_get_active_windows_exception(self, mock_log_error, mock_get_apps, mock_get_titles):
        """Test _get_active_windows returns empty list on exception."""
        mock_get_titles.side_effect = Exception("Test exception")
        
        result = WindowTracker._get_active_windows()
        
        assert result == []
        mock_log_error.assert_called_once_with("Failed to get window titles")

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_true_when_keyword_matches(self, mock_get_windows):
        """Test is_active returns True when keyword found in window titles."""
        mock_get_windows.return_value = ['Visual Studio Code', 'Firefox', 'Terminal']
        
        with patch('src.tracker.window.time.time', return_value=123456789):
            tracker = WindowTracker(['code', 'vim'])
            
            result = tracker.is_active()
            
        assert result is True
        assert tracker.last_active == 123456789

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_false_when_no_keyword_matches(self, mock_get_windows):
        """Test is_active returns False when no keywords match."""
        mock_get_windows.return_value = ['Firefox', 'Chrome', 'Safari']
        with patch('src.tracker.window.time.time', return_value=1000):
            tracker = WindowTracker(['vim', 'emacs'])
            initial_last_active = tracker.last_active

            result = tracker.is_active()

            assert result is False
            # last_active should not be updated (remains the same as initial value)
            assert tracker.last_active == initial_last_active

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_case_insensitive_matching(self, mock_get_windows):
        """Test is_active performs case-insensitive keyword matching."""
        mock_get_windows.return_value = ['VISUAL STUDIO CODE', 'firefox']
        
        with patch('src.tracker.window.time.time', return_value=987654321):
            tracker = WindowTracker(['code', 'vim'])
            
            result = tracker.is_active()
            
        assert result is True
        assert tracker.last_active == 987654321

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_partial_matching(self, mock_get_windows):
        """Test is_active matches keywords as substrings."""
        mock_get_windows.return_value = ['My Code Editor', 'Web Browser']
        
        with patch('src.tracker.window.time.time', return_value=555555555):
            tracker = WindowTracker(['code'])
            
            result = tracker.is_active()
            
        assert result is True
        assert tracker.last_active == 555555555

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_empty_windows_list(self, mock_get_windows):
        """Test is_active returns False when window list is empty."""
        mock_get_windows.return_value = []
        tracker = WindowTracker(['vim', 'code'])
        
        result = tracker.is_active()
        
        assert result is False

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_multiple_keyword_matches(self, mock_get_windows):
        """Test is_active returns True when any keyword matches."""
        mock_get_windows.return_value = ['Notepad', 'Visual Studio Code']
        
        with patch('src.tracker.window.time.time', return_value=111111111):
            tracker = WindowTracker(['vim', 'code', 'emacs'])
            
            result = tracker.is_active()
            
        assert result is True
        assert tracker.last_active == 111111111

    @patch('src.tracker.window.WindowTracker._get_active_windows')
    def test_is_active_updates_last_active_as_int(self, mock_get_windows):
        """Test is_active sets last_active as integer timestamp."""
        mock_get_windows.return_value = ['Code Editor']
        
        with patch('src.tracker.window.time.time', return_value=123.456):
            tracker = WindowTracker(['code'])
            
            result = tracker.is_active()
            
        assert result is True
        assert tracker.last_active == 123  # Should be int, not float

    def test_empty_keywords_list(self):
        """Test WindowTracker with empty keywords list."""
        tracker = WindowTracker([])
        
        # Should not match anything
        with patch('src.tracker.window.WindowTracker._get_active_windows', return_value=['Any Window']):
            result = tracker.is_active()
            
        assert result is False