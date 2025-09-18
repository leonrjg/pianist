from abc import ABC, abstractmethod


class Tracker(ABC):
    def __init__(self):
        self.last_active = None
    
    @abstractmethod
    def is_active(self) -> bool:
        pass

    def get_last_active(self) -> int:
        return self.last_active