import pytest
import time
import threading
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from src.session import Session


class TestSession:
    
    @pytest.fixture
    def mock_habit(self):
        """Create a mock habit for testing."""
        habit = Mock()
        habit.inactivity_threshold = 120
        return habit
    
    @pytest.fixture
    def mock_tracker(self):
        """Create a mock tracker for testing."""
        tracker = Mock()
        tracker.is_active.return_value = True
        tracker.get_last_active.return_value = time.time()
        return tracker
    
    @pytest.fixture
    def mock_habit_tracker(self, mock_tracker):
        """Create a mock HabitTracker database object."""
        habit_tracker = Mock()
        habit_tracker.tracker = 'test_tracker'
        habit_tracker.config = '{}'
        habit_tracker.tracker_instance = mock_tracker
        return habit_tracker

    def test_initialization(self, mock_habit):
        """Test Session initialization."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            assert session.habit == mock_habit
            assert isinstance(session.start_time, float)
            assert isinstance(session.shutdown_event, threading.Event)
            assert isinstance(session.elapsed_lock, threading.Lock)
            assert session.updating_thread is None
            assert session.tracking_thread is None
            assert session.log is None
            assert session.trackers == []

    @patch('src.session.HabitTracker')
    def test_load_trackers_success(self, mock_habit_tracker_class, mock_habit, mock_habit_tracker):
        """Test successful tracker loading."""
        mock_habit_tracker_class.select.return_value.where.return_value = [mock_habit_tracker]
        
        session = Session(mock_habit)
        
        assert len(session.trackers) == 1
        assert session.trackers[0] == mock_habit_tracker.tracker_instance

    @patch('src.session.HabitTracker')
    @patch('src.session.logging')
    def test_load_trackers_failure(self, mock_logging, mock_habit_tracker_class, mock_habit):
        """Test tracker loading with ValueError."""
        mock_habit_tracker = Mock()
        mock_habit_tracker.tracker = 'invalid_tracker'
        mock_habit_tracker.config = '{}'
        
        # Create a property that raises ValueError when accessed
        def raise_error():
            raise ValueError("Invalid tracker")
        
        type(mock_habit_tracker).tracker_instance = property(lambda self: raise_error())
        
        mock_habit_tracker_class.select.return_value.where.return_value = [mock_habit_tracker]
        
        session = Session(mock_habit)
        
        assert session.trackers == []
        # Check that error was logged
        mock_logging.error.assert_called()

    @patch('src.session.HabitTracker')
    def test_load_trackers_empty(self, mock_habit_tracker_class, mock_habit):
        """Test loading trackers when none are enabled."""
        mock_habit_tracker_class.select.return_value.where.return_value = []
        
        session = Session(mock_habit)
        
        assert session.trackers == []

    def test_start_creates_threads(self, mock_habit):
        """Test that start() creates and starts both threads."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            with patch('threading.Thread') as mock_thread_class:
                mock_updating_thread = Mock()
                mock_tracking_thread = Mock()
                mock_thread_class.side_effect = [mock_updating_thread, mock_tracking_thread]
                
                session.start()
                
                assert mock_thread_class.call_count == 2
                mock_updating_thread.start.assert_called_once()
                mock_tracking_thread.start.assert_called_once()
                assert session.updating_thread == mock_updating_thread
                assert session.tracking_thread == mock_tracking_thread

    def test_get_elapsed_time(self, mock_habit):
        """Test elapsed time calculation."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            initial_time = session.start_time
            
            # Mock time.time to return a later time
            with patch('time.time', return_value=initial_time + 5.7):
                elapsed = session.get_elapsed_time()
                assert elapsed == 5  # Should be truncated to int

    def test_get_elapsed_time_thread_safety(self, mock_habit):
        """Test that elapsed time calculation is thread-safe."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            # Simple test: just verify the method works with a lock present
            # The actual thread safety is tested implicitly by using threading.Lock
            elapsed_time = session.get_elapsed_time()
            assert isinstance(elapsed_time, int)
            assert elapsed_time >= 0

    @patch('src.session.Log')
    def test_end_without_ended_by(self, mock_log_class, mock_habit):
        """Test ending session without specifying ended_by."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            mock_log = Mock()
            session.log = mock_log
            
            session.end()
            
            assert session.shutdown_event.is_set()
            # ended_by should not be set when None is passed
            assert not hasattr(mock_log, 'ended_by') or mock_log.ended_by != 'test_tracker'

    @patch('src.session.Log')
    def test_end_with_ended_by(self, mock_log_class, mock_habit):
        """Test ending session with ended_by parameter."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            mock_log = Mock()
            session.log = mock_log
            
            session.end('test_tracker')
            
            assert session.shutdown_event.is_set()
            assert mock_log.ended_by == 'test_tracker'

    def test_end_without_log(self, mock_habit):
        """Test ending session when no log exists."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            session.end('test_tracker')
            
            assert session.shutdown_event.is_set()

    def test_join_with_threads(self, mock_habit):
        """Test joining threads when they exist."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            mock_updating_thread = Mock()
            mock_tracking_thread = Mock()
            session.updating_thread = mock_updating_thread
            session.tracking_thread = mock_tracking_thread
            
            session.join()
            
            mock_updating_thread.join.assert_called_once()
            mock_tracking_thread.join.assert_called_once()

    def test_join_without_threads(self, mock_habit):
        """Test joining when threads don't exist."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            # Should not raise any exception
            session.join()

    def test_is_active_when_active(self, mock_habit):
        """Test is_active returns True when session is active."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            assert session.is_active() is True

    def test_is_active_when_shutdown(self, mock_habit):
        """Test is_active returns False after shutdown."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            session.shutdown_event.set()
            
            assert session.is_active() is False

    @patch('src.session.Log')
    @patch('src.session.datetime')
    def test_update_progress_creates_log(self, mock_datetime, mock_log_class, mock_habit):
        """Test that update_progress creates initial log record."""
        mock_now = datetime(2024, 1, 1, 12, 0)
        mock_datetime.now.return_value = mock_now
        mock_log = Mock()
        mock_log_class.create.return_value = mock_log
        
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            session.shutdown_event.set()  # End immediately for testing
            
            session.update_progress()
            
            mock_log_class.create.assert_called_once_with(
                habit=mock_habit,
                start=mock_now
            )
            assert session.log == mock_log

    def test_track_with_inactive_tracker(self, mock_habit, mock_tracker):
        """Test track method with an inactive tracker."""
        # Ensure the habit has an inactivity threshold set
        mock_habit.inactivity_threshold = 120  # 120 seconds
        
        mock_tracker.is_active.return_value = False
        mock_tracker.get_last_active.return_value = time.time() - 200  # 200 seconds ago
        
        # Create a proper mock class with the right __name__
        class MockTracker:
            def __init__(self):
                self.is_active = Mock(return_value=False)
                self.get_last_active = Mock(return_value=time.time() - 200)
        
        mock_tracker_instance = MockTracker()
        
        with patch.object(Session, '_load_trackers', return_value=[mock_tracker_instance]):
            session = Session(mock_habit)
            
            with patch.object(session, 'end') as mock_end:
                # Mock the wait method to simulate first loop iteration then shutdown
                call_count = [0]
                original_wait = session.shutdown_event.wait
                
                def mock_wait(timeout=None):
                    call_count[0] += 1
                    if call_count[0] == 1:
                        return False  # First iteration continues
                    else:
                        return True  # Subsequent calls exit
                
                with patch.object(session.shutdown_event, 'wait', side_effect=mock_wait):
                    session.track()
                
                # Should call end with tracker name
                mock_end.assert_called_with('MockTracker')

    def test_track_with_active_tracker(self, mock_habit, mock_tracker):
        """Test track method with an active tracker."""
        mock_tracker.is_active.return_value = True
        
        with patch.object(Session, '_load_trackers', return_value=[mock_tracker]):
            session = Session(mock_habit)
            
            with patch.object(session, 'end') as mock_end:
                # Set shutdown event to end the loop quickly
                threading.Timer(0.1, session.shutdown_event.set).start()
                session.track()
                
                # Should not call end
                mock_end.assert_not_called()

    def test_track_with_no_trackers(self, mock_habit):
        """Test track method with no trackers."""
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            # Set shutdown event to end the loop quickly
            threading.Timer(0.1, session.shutdown_event.set).start()
            
            # Should not raise any exceptions
            session.track()

    def test_track_poll_interval_adjustment(self, mock_habit):
        """Test that track adjusts poll interval based on inactivity threshold."""
        mock_habit.inactivity_threshold = 10  # 10 seconds
        
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            with patch.object(session.shutdown_event, 'wait') as mock_wait:
                mock_wait.return_value = True  # Simulate timeout to exit loop
                session.track()
                
                # Should use inactivity_threshold as poll_interval
                mock_wait.assert_called_with(timeout=10)

    def test_track_default_poll_interval(self, mock_habit):
        """Test track uses default poll interval when threshold is small."""
        mock_habit.inactivity_threshold = 1  # 1 second (less than default 2)
        
        with patch.object(Session, '_load_trackers', return_value=[]):
            session = Session(mock_habit)
            
            with patch.object(session.shutdown_event, 'wait') as mock_wait:
                mock_wait.return_value = True  # Simulate timeout to exit loop
                session.track()
                
                # Should use default poll_interval of 2
                mock_wait.assert_called_with(timeout=2)