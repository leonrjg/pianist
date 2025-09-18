import logging
import threading
import time
from datetime import datetime

from habit.habit import Habit
from habit.habit_tracker import HabitTracker
from habit.log import Log


class Session:
    """Thread-safe shared state for a habit tracking session."""

    def __init__(self, habit: Habit):
        self.habit = habit
        self.start_time = time.time()
        self.shutdown_event = threading.Event()
        self.elapsed_lock = threading.Lock()
        self.updating_thread = None
        self.tracking_thread = None
        self.log = None
        self.trackers = self._load_trackers() or []

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
            self.log.save()

        # Insert initial log record
        self.log = Log.create(
            habit=self.habit,
            start=datetime.now(),
        )

        # Update end time every minute
        while not self.shutdown_event.wait(timeout=60):
            if not self.is_active():
                break

            # Update the log record with current time
            update_record()

        # Final update on shutdown
        if self.log:
            update_record()

    def track(self):
        """Background thread for querying trackers."""
        poll_interval = 2
        inactivity_threshold = self.habit.inactivity_threshold
        if inactivity_threshold and inactivity_threshold > poll_interval:
            poll_interval = self.habit.inactivity_threshold

        while not self.shutdown_event.wait(timeout=poll_interval):
            if not self.is_active():
                break

            # Check if any tracker is inactive
            for tracker in self.trackers:
                is_active = tracker.is_active()
                inactive_duration = time.time() - (tracker.get_last_active() or 0)
                if not is_active and inactivity_threshold and inactive_duration >= inactivity_threshold:
                    tracker_name = tracker.__class__.__name__
                    self.end(tracker_name)

    def get_elapsed_time(self) -> int:
        """Get the elapsed time in seconds since the session started."""
        with self.elapsed_lock:
            return int(time.time() - self.start_time)

    def end(self, ended_by: str = None):
        """Signal all threads to end and update the log."""
        if self.log and ended_by:
            self.log.ended_by = ended_by
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