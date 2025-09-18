import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from src.habit.habit_tracker import HabitTracker


class TestHabitTracker:
    
    def test_get_config_with_valid_json(self):
        """Test get_config returns parsed JSON."""
        tracker = HabitTracker()
        tracker.config = '{"keywords": ["test"], "threshold": 30}'
        
        config = tracker.get_config()
        
        assert config == {"keywords": ["test"], "threshold": 30}
    
    def test_get_config_with_empty_config(self):
        """Test get_config returns empty dict when config is None."""
        tracker = HabitTracker()
        tracker.config = None
        
        config = tracker.get_config()
        
        assert config == {}
    
    def test_get_config_with_empty_string(self):
        """Test get_config returns empty dict when config is empty string."""
        tracker = HabitTracker()
        tracker.config = ""
        
        config = tracker.get_config()
        
        assert config == {}
    
    @patch('tracker.io.IOTracker')
    def test_tracker_instance_io(self, mock_io_tracker):
        """Test tracker_instance returns IOTracker for io type."""
        tracker = HabitTracker()
        tracker.tracker = 'io'
        tracker.config = '{}'
        
        instance = tracker.tracker_instance
        
        mock_io_tracker.assert_called_once()
    
    @patch('tracker.window.WindowTracker')
    def test_tracker_instance_window(self, mock_window_tracker):
        """Test tracker_instance returns WindowTracker with keywords."""
        tracker = HabitTracker()
        tracker.tracker = 'window'
        tracker.config = '{"keywords": ["test", "code"]}'
        
        instance = tracker.tracker_instance
        
        mock_window_tracker.assert_called_once_with(["test", "code"])
    
    @patch('tracker.window.WindowTracker')
    def test_tracker_instance_window_no_keywords(self, mock_window_tracker):
        """Test tracker_instance returns WindowTracker with empty list when no keywords."""
        tracker = HabitTracker()
        tracker.tracker = 'window'
        tracker.config = '{}'
        
        instance = tracker.tracker_instance
        
        mock_window_tracker.assert_called_once_with([])
    
    def test_tracker_instance_unknown_type(self):
        """Test tracker_instance raises ValueError for unknown tracker type."""
        tracker = HabitTracker()
        tracker.tracker = 'unknown'
        tracker.config = '{}'
        
        with pytest.raises(ValueError, match="Unknown tracker type: unknown"):
            tracker.tracker_instance
    
    def test_create_json_config_with_query_string(self):
        """Test create_json_config parses URL query string format."""
        config_string = "keywords=piano&keywords=practice&threshold=60"
        
        result = HabitTracker.create_json_config(config_string)
        parsed = json.loads(result)
        
        assert parsed == {"keywords": ["piano", "practice"], "threshold": ["60"]}
    
    def test_create_json_config_with_empty_string(self):
        """Test create_json_config returns empty dict for empty string."""
        result = HabitTracker.create_json_config("")
        parsed = json.loads(result)
        
        assert parsed == {}
    
    def test_create_json_config_with_single_param(self):
        """Test create_json_config handles single parameter."""
        config_string = "threshold=30"
        
        result = HabitTracker.create_json_config(config_string)
        parsed = json.loads(result)
        
        assert parsed == {"threshold": ["30"]}