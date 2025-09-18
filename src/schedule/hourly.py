from datetime import datetime, timedelta
from typing import List, Optional
from .schedule import Schedule
from util import time


class HourlySchedule(Schedule):
    """A schedule that repeats tasks every hour from the start date."""
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous hourly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look back from now.

        Returns:
            List of previous hourly task datetimes, ordered from most recent
            to oldest.
        """
        now = datetime.now()
        hours = timespan // time.HOUR

        tasks = []
        current = now
        for _ in range(hours):
            prev_task = self.get_previous_task(current)
            tasks.append(prev_task)
            current = prev_task
        return tasks

    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the previous hourly task before the given datetime.

        Args:
            from_dt: Reference datetime to look back from.

        Returns:
            The previous hourly occurrence, or None if from_dt is at or
            before the start date.
        """
        if from_dt <= self.start:
            return None

        hours_since_start = int((from_dt - self.start).total_seconds() // time.HOUR)
        if hours_since_start == 0:
            return None

        return self.start + timedelta(hours=hours_since_start - 1)

    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming hourly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look ahead from now.

        Returns:
            List of upcoming hourly task datetimes, ordered from earliest
            to latest.
        """
        now = datetime.now()
        hours = timespan // time.HOUR

        tasks = []
        current = now
        for _ in range(hours):
            next_task = self.get_next_task(current)
            if next_task:
                tasks.append(next_task)
                current = next_task + timedelta(seconds=1)


    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next hourly task after the given datetime.

        Args:
            from_dt: Reference datetime to look ahead from.

        Returns:
            Datetime of next occurrence.
        """
        if from_dt < self.start:
            return self.start

        hours_since_start = int((from_dt - self.start).total_seconds() // 3600)
        return self.start + timedelta(hours=hours_since_start + 1)

    def get_scale(self) -> int:
        return time.HOUR

