import logging
import time
from typing import List
import pywinctl
from .tracker import Tracker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class WindowTracker(Tracker):
    def __init__(self, keywords: List[str]):
        super().__init__()
        self.keywords = keywords

    @staticmethod
    def _get_active_windows() -> list[str]:
        try:
            return pywinctl.getAllTitles() + pywinctl.getAllAppsNames()
        except:
            logging.error("Failed to get window titles")
            return []

    def is_active(self) -> bool:
        for title in self._get_active_windows():
            if any(keyword.lower() in title.lower() for keyword in self.keywords):
                self.last_active = int(time.time())
                return True
        return False
