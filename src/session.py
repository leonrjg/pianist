import logging
import threading
import time
from datetime import datetime
from enum import Enum

from habit.habit import Habit
from habit.habit_tracker import HabitTracker
from habit.log import Log
from util.time import MINUTE

MAX_IDLE_FACTOR = 3

class SessionStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"


class Session:
    """
    Thread-safe shared state for a habit tracking session.

    It manages real-time activity tracking,
    automatic pause/resume based on inactivity, and persists session data
    to the database for streak and analytics calculations.

    The session coordinates multiple tracking threads (I/O, window monitoring)
    and maintains timing data including active time, idle time, and pause states.
    """

    def __init__(self, habit: Habit):
        self.habit = habit
        self.start_time = time.time()
        self.shutdown_event = threading.Event()
        self.elapsed_lock = threading.Lock()
        self.updating_thread = None
        self.tracking_thread = None
        self.log = None
        self.trackers = self._load_trackers() or []

        self.state = SessionStatus.ACTIVE
        self.state_lock = threading.Lock()
        self.pause_start_time = None
        self.total_paused_time = 0
        self.transition_reason = None

    def _load_trackers(self):
        """Load all enabled trackers for this habit."""
        def get_habit_trackers(habit):
            """Get all enabled trackers for a habit."""
            return HabitTracker.select().where((HabitTracker.habit == habit) & (HabitTracker.is_enabled == True))

        trackers = []
        for habit_tracker in get_habit_trackers(self.habit):
            try:
                logging.info(f"Loading tracker {habit_tracker.tracker} with config: {habit_tracker.config}")
                trackers.append(habit_tracker.tracker_instance)
            except ValueError as e:
                logging.error(f"Warning: Could not load tracker {habit_tracker.tracker}: {e}")
        return trackers

    def is_paused(self):
        """Check if the session is currently paused."""
        return self.state == SessionStatus.PAUSED

    def is_ended(self):
        """Check if the session has ended."""
        return self.state == SessionStatus.ENDED

    def start(self):
        """Start background threads for logging and tracking."""
        self.updating_thread = threading.Thread(target=self.update_progress, daemon=True)
        self.tracking_thread = threading.Thread(target=self.track, daemon=False)
        self.updating_thread.start()
        self.tracking_thread.start()

    def update_progress(self):
        """Background thread that manages database logging."""
        def update_record():
            self.log.end = datetime.now()
            self.log.idle_time = self.total_paused_time
            self.log.save()

        # Insert initial log record
        self.log = Log.create(
            habit=self.habit,
            start=datetime.now(),
        )

        # Update end time every minute
        while not self.shutdown_event.wait(timeout=1*MINUTE):
            if not self.is_active():
                break
            update_record()

        # Final update on shutdown
        if self.log:
            update_record()

    def track(self):
        """Background thread for querying trackers."""
        inactivity_threshold = self.habit.inactivity_threshold

        while not self.shutdown_event.wait(timeout=5):
            if not self.is_active() or not self.trackers:
                break
                
            # Check tracker activity status
            all_trackers_active = all(tracker.is_active() for tracker in self.trackers)

            if all_trackers_active and self.is_paused():
                self._resume()
            elif not all_trackers_active and not self.is_paused():
                # Check if we should pause due to inactivity
                for tracker in self.trackers:
                    if tracker.get_last_active():
                        if time.time() - tracker.get_last_active() >= inactivity_threshold:
                            self._pause(tracker.__class__.__name__)
            elif self.is_paused() and time.time() - self.pause_start_time > MAX_IDLE_FACTOR * inactivity_threshold:
                self.end()

    def get_elapsed_time(self) -> int:
        """Get the elapsed time in seconds since the session started, excluding paused time."""
        with self.elapsed_lock:
            total_time = time.time() - self.start_time
            paused_time = self.total_paused_time
            
            # If currently paused, add the current pause duration
            if self.is_paused() and self.pause_start_time:
                paused_time += time.time() - self.pause_start_time
                
            return int(total_time - paused_time)

    def end(self, ended_by: str = None):
        """Signal all threads to end and update the log."""
        with self.state_lock:
            # If we're ending while paused, add current pause time to total
            if self.is_paused() and self.pause_start_time:
                self.total_paused_time += time.time() - self.pause_start_time
                self.pause_start_time = None
            self.state = SessionStatus.ENDED
            self.transition_reason = ended_by
        
        if self.log:
            self.log.ended_by = ended_by
            self.log.idle_time = int(self.total_paused_time)

        self.shutdown_event.set()

    def join(self):
        """Wait for background threads to finish."""
        if self.updating_thread:
            self.updating_thread.join()
        if self.tracking_thread:
            self.tracking_thread.join()

    def is_active(self) -> bool:
        """Check if the session is still active."""
        return not self.shutdown_event.is_set()
    
    def _pause(self, reason=None):
        """Transition session to paused state."""
        with self.state_lock:
            if self.state == SessionStatus.ACTIVE:
                self.state = SessionStatus.PAUSED
                self.pause_start_time = time.time()
                self.transition_reason = reason
    
    def _resume(self, reason=None):
        """Transition session from paused to active state."""
        with self.state_lock:
            if self.is_paused():
                if self.pause_start_time:
                    self.total_paused_time += time.time() - self.pause_start_time
                    self.pause_start_time = None
                self.state = SessionStatus.ACTIVE
                self.transition_reason = reason

    def get_status(self) -> SessionStatus:
        """Get current session state thread-safely."""
        with self.state_lock:
            return self.state

    def get_transition_reason(self) -> str | None:
        """Get the reason for the last state transition."""
        with self.state_lock:
            return self.transition_reason
