from datetime import datetime
from .schedule import Schedule


class RegularSchedule(Schedule):
    """Abstract base class for regular interval schedules.

    This class extends Schedule to add support for a step parameter,
    which allows schedules to repeat every N intervals (e.g., every 3 days,
    every 2 weeks).

    Args:
        start: The datetime when the schedule begins.
        end: The datetime when the schedule ends.
        step: The interval step (e.g., 1 for every interval, 2 for every other, etc.).
    """
    def __init__(self, start: datetime, end: datetime, step: int = 1):
        super().__init__(start, end)
        self.step = step
