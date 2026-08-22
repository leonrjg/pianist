from datetime import datetime, timedelta
from typing import List, Optional
from .regular import RegularSchedule
from core.util import time


class MonthlySchedule(RegularSchedule):
    """A schedule that repeats tasks every N*30 days from the start date.

    This schedule calculates task occurrences based on 30-day intervals
    from the initial start datetime, approximating monthly recurrence.
    """
    def get_previous_tasks(self, timespan: int) -> List[datetime]:
        """Get previous monthly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look back from now.

        Returns:
            List of previous monthly task datetimes, ordered from most recent
            to oldest. Stops at the start date.
        """
        now = datetime.now()
        days = timespan // time.DAY
        months = days // (30 * self.step)

        tasks = []
        current = now
        for _ in range(months):
            prev_task = self.get_previous_task(current)
            if prev_task:
                tasks.append(prev_task)
                current = prev_task
            else:
                break
        return tasks

    def get_previous_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the previous monthly task before the given datetime.

        Args:
            from_dt: Reference datetime to look back from.

        Returns:
            The previous monthly occurrence (30 days earlier), or None if
            from_dt is at or before the start date.
        """
        if from_dt <= self.start:
            return None

        days_since_start = (from_dt - self.start).days
        months_since_start = days_since_start // 30
        intervals_since_start = months_since_start // self.step
        if intervals_since_start == 0:
            return None

        return self.start + timedelta(days=30 * (intervals_since_start - 1) * self.step)

    def get_next_tasks(self, timespan: int) -> List[datetime]:
        """Get upcoming monthly tasks within the given timespan.

        Args:
            timespan: Time range in seconds to look ahead from now.

        Returns:
            List of future monthly task datetimes, ordered from earliest
            to latest.
        """
        cutoff = datetime.now() + timedelta(seconds=timespan)

        tasks = []
        current = datetime.now() - timedelta(days=30 * self.step)
        while True:
            next_task = self.get_next_task(current)
            if next_task is None or next_task > cutoff:
                break
            tasks.append(next_task)
            current = next_task + timedelta(days=1)
        return tasks

    def get_next_task(self, from_dt: datetime) -> Optional[datetime]:
        """Get the next monthly task on or after the given datetime.

        Args:
            from_dt: Reference datetime to look ahead from.

        Returns:
            The next monthly occurrence, or None if past end date.
        """
        if from_dt < self.start:
            return self.start

        days_since_start = (from_dt - self.start).days
        months_since_start = days_since_start // 30
        intervals_since_start = months_since_start // self.step
        next_task = self.start + timedelta(days=30 * intervals_since_start * self.step)

        # If we've already passed the calculated date, go to the next interval
        if next_task.date() < from_dt.date():
            next_task = self.start + timedelta(days=30 * (intervals_since_start + 1) * self.step)

        if next_task.date() > self.end.date():
            return None
        return next_task

    def get_scale(self) -> int:
        return time.DAY * 30 * self.step