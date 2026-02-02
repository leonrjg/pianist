from datetime import datetime, timedelta
from typing import List, Optional
from .regular import RegularSchedule
from core.util import time


class HourlySchedule(RegularSchedule):
    """A schedule that repeats tasks every N hours from the start date."""
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous hourly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look back from now.

        Returns:
            List of previous hourly task datetimes, ordered from most recent
            to oldest.
        """
        now = datetime.now()
        hours = timespan // (time.HOUR * self.step)

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
        intervals_since_start = hours_since_start // self.step
        if intervals_since_start == 0:
            return None

        return self.start + timedelta(hours=(intervals_since_start - 1) * self.step)

    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming hourly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look ahead from now.

        Returns:
            List of upcoming hourly task datetimes, ordered from earliest
            to latest.
        """
        now = datetime.now()
        hours = timespan // (time.HOUR * self.step)

        tasks = []
        current = now
        for _ in range(hours):
            next_task = self.get_next_task(current)
            tasks.append(next_task)
            current = next_task
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next hourly task after the given datetime.

        Args:
            from_dt: Reference datetime to look ahead from.

        Returns:
            Datetime of next occurrence, or None if past end date.
        """
        if from_dt < self.start:
            return self.start

        hours_since_start = int((from_dt - self.start).total_seconds() // 3600)
        intervals_since_start = hours_since_start // self.step
        next_task = self.start + timedelta(hours=(intervals_since_start + 1) * self.step)

        if next_task.date() > self.end.date():
            return None
        return next_task

    def get_scale(self) -> int:
        return time.HOUR * self.step

