from datetime import datetime, timedelta
from typing import List, Optional
from .schedule import Schedule
from util import time


class WeeklySchedule(Schedule):
    """A schedule that repeats tasks every 7 days from the start date.
    
    This schedule calculates task occurrences based on weekly intervals
    from the initial start datetime, ensuring tasks always fall on the
    same day of the week as the start date.
    """
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous weekly tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look back from now.
            
        Returns:
            List of previous weekly task datetimes, ordered from most recent
            to oldest. Stops at the start date.
        """
        now = datetime.now()
        days = timespan // time.DAY
        weeks = days // 7
        
        tasks = []
        current = now
        for _ in range(weeks):
            prev_task = self.get_previous_task(current)
            if prev_task:
                tasks.append(prev_task)
                current = prev_task
        return tasks

    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the previous weekly task before the given datetime.
        
        Args:
            from_dt: Reference datetime to look back from.
            
        Returns:
            The previous weekly occurrence, or None if from_dt is at or
            before the start date.
        """
        if from_dt <= self.start:
            return None
        
        weeks_since_start = (from_dt - self.start).days // 7
        if weeks_since_start == 0:
            return None
        
        return self.start + timedelta(weeks=weeks_since_start - 1)

    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming weekly tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look ahead from now.
            
        Returns:
            List of future weekly task datetimes, ordered from earliest
            to latest.
        """
        now = datetime.now()
        days = timespan // time.DAY
        weeks = days // 7
        
        tasks = []
        current = now
        for _ in range(weeks):
            next_task = self.get_next_task(current)
            if next_task:
                tasks.append(next_task)
                current = next_task + timedelta(days=1)
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next weekly task on or after the given datetime.
        
        Args:
            from_dt: Reference datetime to look ahead from.
            
        Returns:
            The next weekly occurrence.
        """
        if from_dt < self.start:
            return self.start

        weeks_since_start = (from_dt - self.start).days // 7
        return self.start + timedelta(weeks=weeks_since_start + 1)

    def get_scale(self) -> int:
        return time.WEEK