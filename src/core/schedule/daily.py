from datetime import datetime, timedelta
from typing import List, Optional, Any
from .regular import RegularSchedule
from core.util import time


class DailySchedule(RegularSchedule):
    """A schedule that repeats tasks every N days from the start date.

    This schedule calculates task occurrences based on daily intervals
    from the initial start datetime, creating a task for each day (or every N days).
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
        days = timespan // (time.DAY * self.step)

        tasks = []
        current = now
        for _ in range(days):
            prev_task = self.get_previous_task(current)
            if prev_task is None:
                break
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
        intervals_since_start = days_since_start // self.step
        if intervals_since_start == 0:
            return None

        prev_task = self.start + timedelta(days=(intervals_since_start - 1) * self.step)
        if self.end and prev_task.date() > self.end.date():
            return self.get_previous_task(self.end)
        return prev_task

    def get_next_tasks(self, timespan: int) -> set[datetime]:
        """Get upcoming daily tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look ahead from now.

        Returns:
            List of future daily task datetimes, ordered from earliest
            to latest.
        """
        cutoff = datetime.now() + timedelta(seconds=timespan)

        tasks = set()
        current = datetime.now() - timedelta(days=self.step)
        while True:
            next_task = self.get_next_task(current)
            if next_task is None or next_task > cutoff:
                break
            tasks.add(next_task)
            current = next_task
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next daily task on or after the given datetime.

        Args:
            from_dt: Reference datetime to look ahead from.

        Returns:
            The next daily occurrence. If from_dt falls on a scheduled day, returns that occurrence.
            Otherwise, returns the next scheduled occurrence based on step-day intervals from
            the start date.
        """
        if from_dt < self.start:
            return self.start

        days_since_start = (from_dt - self.start).days
        intervals_since_start = days_since_start // self.step
        next_task = self.start + timedelta(days=(intervals_since_start + 1) * self.step)

        if next_task.date() > self.end.date():
            return None
        return next_task

    def get_scale(self) -> int:
        """Get the time scale for daily scheduling in seconds."""
        return time.DAY * self.step

