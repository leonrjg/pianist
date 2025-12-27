import logging
import time
from typing import List
import pywinctl
from .tracker import Tracker
from .window_monitor import WindowMonitor

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class WindowTracker(Tracker):
    def __init__(self, keywords: List[str]):
        """Initialize window tracker with target keywords."""
        super().__init__()
        self.keywords = keywords
        # Ensure monitor is running
        WindowMonitor.get_instance()

    @staticmethod
    def get_help(**kwargs) -> str:
        """Get help message to explain tracker arguments to users."""
        keywords = kwargs.get("keywords", [])
        active_windows = WindowTracker._get_active_windows()
        focused_window = WindowTracker._get_focused_window()
        match = WindowTracker._is_keyword_in_title(keywords, focused_window)
        keywords_list = ', '.join(keywords) if keywords else "- *None yet*"
        windows_list = '\n'.join([f"- {w}" for w in active_windows[:5]]) if active_windows else "- *None*"
        status = "✓ **MATCH**" if match else "✗ No match"
        return (
            "**WindowTracker** checks the focused window for specified keywords.\n\n"
            f"#### Your keywords\n{keywords_list}\n\n"
            f"#### Windows sample (5)\n{windows_list}\n\n"
            f"#### Focused window\n<ins>{focused_window or '*None yet*'}</ins>\n\n"
            f"#### Tracking status\n{status}\n\n"
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
        """Check if current window matches keywords."""
        title = WindowMonitor.get_current_title()
        is_active = self._is_keyword_in_title(self.keywords, title)
        if is_active:
            self.last_active = int(time.time())
        return is_active
