from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Optional


class Schedule(ABC):
    """Abstract base class for scheduling recurring tasks.
    
    This class provides a common interface for different types of recurring schedules
    (daily, weekly, monthly, etc.) based on a starting datetime.
    
    Args:
        start: The datetime when the schedule begins.
    """
    def __init__(self, start: datetime):
        self.start = start

    @abstractmethod
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get all scheduled tasks that occurred in the past within the given timespan.
        
        Args:
            timespan: The time range in seconds to look back from now.
            
        Returns:
            List of datetime objects representing previous scheduled tasks,
            ordered from most recent to oldest.
        """
        pass

    @abstractmethod
    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the most recent scheduled task before the given datetime.
        
        Args:
            from_dt: The reference datetime to look back from.
            
        Returns:
            The datetime of the previous scheduled task, or None if no previous
            task exists (e.g., from_dt is at or before the start date).
        """
        pass

    @abstractmethod
    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get all scheduled tasks that will occur in the future within the given timespan.
        
        Args:
            timespan: The time range in seconds to look ahead from now.
            
        Returns:
            List of datetime objects representing future scheduled tasks,
            ordered from earliest to latest.
        """
        pass

    @abstractmethod
    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next scheduled task on or after the given datetime.
        
        Args:
            from_dt: The reference datetime to look ahead from.
            
        Returns:
            The datetime of the next scheduled task. If from_dt falls exactly
            on a scheduled occurrence, returns that occurrence. Otherwise,
            returns the next future occurrence based on the schedule's interval.
        """
        pass

    @abstractmethod
    def get_scale(self) -> int:
        """Get the largest time unit within the smallest interval of the schedule."""
        pass

    def is_task_scheduled(self, dt: datetime, task_dt: datetime = None) -> bool:
        """Check if the given datetime is close enough to a task to consider it checked off."""
        task_date = task_dt or self.get_next_task(dt)
        return dt >= task_date - timedelta(seconds=self.get_scale())
