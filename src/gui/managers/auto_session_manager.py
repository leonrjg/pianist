import json
import logging
from typing import List

from PyQt6.QtCore import QObject, pyqtSignal

from core.habit.habit import Habit
from core.habit.habit_tracker import HabitTracker
from core.tracker.window_monitor import WindowMonitor
from core.tracker.window import WindowTracker

logger = logging.getLogger(__name__)


class AutoSessionManager(QObject):
    """Detects when habit sessions should auto-start based on window focus."""

    # Signal emitted when a habit should be started
    session_start_requested = pyqtSignal(object)  # Emits Habit object

    def __init__(self, habits: List[Habit]):
        """
        Initialize auto-session manager.

        Args:
            habits: List of all habits to monitor
        """
        super().__init__()
        self.habits = habits

        # Register for window change notifications from WindowMonitor
        WindowMonitor.get_instance()
        WindowMonitor.register_callback(self._on_window_changed)
        logger.info("AutoSessionManager initialized and listening for window changes")

    def _on_window_changed(self, title: str):
        """Called by WindowMonitor when window title changes."""
        for habit in self.habits:
            # Check if habit's WindowTracker would match this window
            if self._should_start_session(habit, title):
                logger.info(f"Auto-session detected for habit '{habit.name}' (window: {title})")
                self.session_start_requested.emit(habit)

    def _should_start_session(self, habit: Habit, title: str) -> bool:
        """Check if habit's WindowTracker would be active for this title."""
        # Get habit's WindowTracker config
        trackers = HabitTracker.select().where(
            (HabitTracker.habit == habit) &
            (HabitTracker.tracker == 'WindowTracker') &
            (HabitTracker.is_enabled == True)
        )

        for tracker in trackers:
            config = json.loads(tracker.config)
            keywords = config.get('keywords', [])

            # Reuse WindowTracker's static method (no duplication!)
            if WindowTracker._is_keyword_in_title(keywords, title):
                return True

        return False
