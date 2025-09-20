from datetime import datetime, timedelta
from typing import List, Optional
from .schedule import Schedule
from util import time


class ExponentialSchedule(Schedule):
    """A schedule with exponentially increasing intervals between tasks.
    
    This schedule creates tasks with increasing intervals based on powers of a base number.
    The interval between tasks grows as: base^1, base^2, base^3, etc. days.
    
    Args:
        start: The datetime when the schedule begins.
        base: The base number for exponential growth (e.g., base=2 creates intervals
              of 2, 4, 8, 16... days).
    """
    def __init__(self, start: datetime, base: int):
        super().__init__(start)
        self.base = base

    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous exponentially scheduled tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look back from now.
            
        Returns:
            List of previous exponentially scheduled task datetimes, ordered
            from earliest to latest.
        """
        current = datetime.now()
        days = timespan // time.DAY
        cutoff = current - timedelta(days=days)
        tasks = []
        while True:
            prev_task = self.get_previous_task(current)
            if prev_task is None or prev_task < cutoff:
                break
            tasks.append(prev_task)
            current = prev_task
        return tasks


    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the previous exponentially scheduled task before the given datetime.

        Args:
            from_dt: Reference datetime to look back from.

        Returns:
            The previous exponentially scheduled occurrence, or None if from_dt
            is at or before the start date.
        """
        if from_dt <= self.start:
            return None

        days_diff = (from_dt - self.start).days
        exp = 1
        cumulative_days = 0

        while True:
            next_cumulative = cumulative_days + (self.base ** exp)
            if next_cumulative >= days_diff:
                break
            cumulative_days = next_cumulative
            exp += 1

        if cumulative_days == 0:
            return self.start

        return self.start + timedelta(days=cumulative_days)


    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming exponentially scheduled tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look ahead from now.
            
        Returns:
            List of future exponentially scheduled task datetimes, ordered
            from earliest to latest.
        """
        current = datetime.now()
        days = timespan // time.DAY
        cutoff = current + timedelta(days=days)
        tasks = []
        while True:
            next_task = self.get_next_task(current)
            if next_task is None or next_task > cutoff:
                break
            tasks.append(next_task)
            current = next_task
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next exponentially scheduled task on or after the given datetime.
        
        Args:
            from_dt: Reference datetime to look ahead from.
            
        Returns:
            The next exponentially scheduled occurrence. The interval from the
            start date follows the pattern: base^1, base^2, base^3, etc. days.
        """
        if from_dt < self.start:
            return self.start
        
        days_diff = (from_dt - self.start).days
        exp = 1
        cumulative_days = 0
        
        while cumulative_days <= days_diff:
            cumulative_days += self.base ** exp
            exp += 1
        
        return self.start + timedelta(days=cumulative_days)

    def get_scale(self) -> int:
        # Base 3 would give streak tolerance of 2 days, base 2 gives 1 day
        return (self.base - 1) * time.DAY