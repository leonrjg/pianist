from datetime import datetime, timedelta
from typing import List, Optional
from .schedule import Schedule
from util import time


class DailySchedule(Schedule):
    """A schedule that repeats tasks every day from the start date.
    
    This schedule calculates task occurrences based on daily intervals
    from the initial start datetime, creating a task for each day.
    """
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous daily tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look back from now.
            
        Returns:
            List of previous daily task datetimes, ordered from most recent
            to oldest. Stops at the start date.
        """
        now = datetime.now()
        days = timespan // time.DAY
        
        tasks = []
        current = now
        for _ in range(days):
            prev_task = self.get_previous_task(current)
            tasks.append(prev_task)
            current = prev_task
        return tasks

    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the previous daily task before the given datetime.
        
        Args:
            from_dt: Reference datetime to look back from.
            
        Returns:
            The previous daily occurrence, or None if from_dt is at or
            before the start date.
        """
        if from_dt <= self.start:
            return None
        
        days_since_start = (from_dt - self.start).days
        if days_since_start == 0:
            return None
        
        return self.start + timedelta(days=days_since_start - 1)

    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming daily tasks within the given timespan.
        
        Args:
            timespan: Time range in seconds to look ahead from now.
            
        Returns:
            List of future daily task datetimes, ordered from earliest
            to latest.
        """
        now = datetime.now()
        days = timespan // time.DAY
        
        tasks = []
        current = now
        for _ in range(days):
            next_task = self.get_next_task(current)
            if next_task:
                tasks.append(next_task)
                current = next_task + timedelta(days=1)
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next daily task on or after the given datetime.
        
        Args:
            from_dt: Reference datetime to look ahead from.
            
        Returns:
            The next daily occurrence. If from_dt falls exactly on a
            scheduled day, returns that occurrence. Otherwise returns
            the next daily occurrence based on 1-day intervals from
            the start date.
        """
        if from_dt < self.start:
            return self.start
        
        days_since_start = (from_dt - self.start).days
        current_occurrence = self.start + timedelta(days=days_since_start)
        
        if current_occurrence.date() >= from_dt.date():
            return current_occurrence
        else:
            return self.start + timedelta(days=days_since_start + 1)

    def get_scale(self) -> int:
        return time.DAY

