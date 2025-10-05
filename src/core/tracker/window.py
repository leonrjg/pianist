import logging
import time
from typing import List
import pywinctl
from .tracker import Tracker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class WindowTracker(Tracker):
    def __init__(self, keywords: List[str]):
        """Initialize window tracker with target keywords."""
        super().__init__()
        self.keywords = keywords

    @staticmethod
    def get_help(**kwargs) -> str:
        """Get help message to explain tracker arguments to users."""
        keywords = kwargs.get("keywords", [])
        active_windows = WindowTracker._get_active_windows()
        focused_window = WindowTracker._get_focused_window()
        match = WindowTracker._is_keyword_in_title(keywords, focused_window)
        return (
            "WindowTracker monitors the focused window for specified keywords.\n"
            f"Current keywords: {', '.join(keywords)}\n"
            f"All windows:\n {'\n'.join(active_windows)}\n"
            f"Focused window: {focused_window}\n"
            f"Current tracking state: {'KEYWORD MATCH!' if match else 'No match'}\n"
            "To configure, provide a list of keywords to match window titles or app names."
        )

    @staticmethod
    def _get_focused_window() -> str:
        """Get the title of the currently focused window."""
        return pywinctl.getActiveWindowTitle()

    @staticmethod
    def _get_active_windows() -> list[str]:
        """Get all active window titles and app names."""
        try:
            return pywinctl.getAllTitles() + pywinctl.getAllAppsNames()
        except:
            logging.error("Failed to get window titles")
            return []

    @staticmethod
    def _is_keyword_in_title(keywords: List[str], title: str) -> bool:
        """Check if any keyword is in the given title."""
        return any(keyword.lower() in title.lower() for keyword in keywords)

    def is_active(self) -> bool:
        """Check if any active window matches target keywords."""
        """
        for title in self._get_active_windows():
            if any(keyword.lower() in title.lower() for keyword in self.keywords):
                self.last_active = int(time.time())
                return True
        return False
        """
        is_active = self._is_keyword_in_title(self.keywords, self._get_focused_window())
        if is_active:
            self.last_active = int(time.time())
        return is_active
