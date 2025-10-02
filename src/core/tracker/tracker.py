import time
from abc import ABC, abstractmethod


class Tracker(ABC):
    def __init__(self):
        """Initialize tracker with current timestamp."""
        self.last_active: int = int(time.time())
    
    @abstractmethod
    def is_active(self) -> bool:
        pass

    def get_last_active(self) -> int:
        """Get timestamp of last detected activity."""
        return self.last_active