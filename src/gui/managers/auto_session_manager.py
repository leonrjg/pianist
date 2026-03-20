import json
import logging
from typing import Dict
from datetime import datetime

from PyQt6.QtCore import QObject, pyqtSignal

from core.habit.habit import Habit
from core.habit.service import HabitService
from core.tracker.window_monitor import WindowMonitor
from core.tracker.window import WindowTracker

logger = logging.getLogger(__name__)


class AutoSessionManager(QObject):
    """Detects when habit sessions should auto-start based on window focus."""

    # Signal emitted when a habit should be started
    session_start_requested = pyqtSignal(object)  # Emits Habit object

    # Cooldown period after manual session end (in seconds)
    MANUAL_END_COOLDOWN = 60 * 60  # 1 hour

    def __init__(self, service):
        """
        Initialize auto-session manager.

        Args:
            service: HabitService — queried live on each window change so newly
                     added habits are immediately eligible for auto-start.
        """
        super().__init__()
        self.service = service

        # Track manually ended sessions: habit_id -> timestamp
        self.manual_end_times: Dict[int, datetime] = {}

        # Register for window change notifications from WindowMonitor
        WindowMonitor.get_instance()
        WindowMonitor.register_callback(self._on_window_changed)
        logger.info("AutoSessionManager initialized and listening for window changes")

    def _on_window_changed(self, title: str):
        """Called by WindowMonitor when window title changes."""
        for habit in self.service.get_all_habits():
            # Check if habit's WindowTracker would match this window
            if self._should_start_session(habit, title):
                logger.info(f"Auto-session detected for habit '{habit.name}' (window: {title})")
                self.session_start_requested.emit(habit)

    def mark_session_manually_ended(self, habit: Habit):
        """
        Mark that a session was manually ended for this habit.
        This prevents auto-starting for the cooldown period.

        Args:
            habit: The habit whose session was manually ended
        """
        self.manual_end_times[habit.id] = datetime.now()
        logger.info(f"Marked habit '{habit.name}' as manually ended - cooldown active for {self.MANUAL_END_COOLDOWN // 60} minutes")

    def _is_in_cooldown(self, habit: Habit) -> bool:
        """
        Check if a habit is in cooldown period after manual end.

        Args:
            habit: The habit to check

        Returns:
            True if the habit is in cooldown period, False otherwise
        """
        if habit.id not in self.manual_end_times:
            return False

        end_time = self.manual_end_times[habit.id]
        elapsed = (datetime.now() - end_time).total_seconds()

        if elapsed >= self.MANUAL_END_COOLDOWN:
            # Cooldown expired, remove from tracking
            del self.manual_end_times[habit.id]
            return False

        return True

    def _should_start_session(self, habit: Habit, title: str) -> bool:
        """Check if habit's WindowTracker would be active for this title."""
        # Check if habit is in cooldown period after manual end
        if self._is_in_cooldown(habit):
            logger.debug(f"Habit '{habit.name}' is in cooldown after manual end - skipping autostart")
            return False

        # Get habit's WindowTracker config
        trackers = HabitService.get_window_trackers(habit)

        for tracker in trackers:
            config = json.loads(tracker.config)
            keywords = config.get('keywords', [])

            # Reuse WindowTracker's static method (no duplication!)
            if WindowTracker._is_keyword_in_title(keywords, title):
                return True

        return False
