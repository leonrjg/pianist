from datetime import datetime
from datetime import timedelta
from typing import Optional

from peewee import *
from schedule.schedule import Schedule
from db import BaseModel

from .bucket import Bucket


class Habit(BaseModel):
    """
    Represents a habit with scheduling and tracking details.

    Args:
        id: Unique identifier for the habit.
        name: Name of the habit.
        created_at: Timestamp when the habit was created.
        updated_at: Timestamp when the habit was last updated.
        started_at: Timestamp when the habit tracking started.
        inactivity_threshold: Time in seconds to consider inactivity.
        allocated_time: Total allocated time for the habit in seconds.
    """
    id = AutoField()
    name = CharField(unique=True)
    schedule = CharField()
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    started_at = DateTimeField(default=datetime.now)
    inactivity_threshold = IntegerField(default=120)
    allocated_time: Optional[int] = IntegerField(null=True)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._schedule: Schedule = self._get_schedule()

    def get_schedule(self) -> Schedule:
        return self._schedule

    def _get_schedule(self) -> Schedule:
        """Get actual Tracker instance."""
        from schedule.daily import DailySchedule
        from schedule.exponential import ExponentialSchedule
        from schedule.weekly import WeeklySchedule
        from schedule.monthly import MonthlySchedule
        from schedule.hourly import HourlySchedule

        if self.schedule == 'hourly':
            return HourlySchedule(start=self.started_at)
        elif self.schedule == 'daily':
            return DailySchedule(start=self.started_at)
        elif self.schedule == 'weekly':
            return WeeklySchedule(start=self.started_at)
        elif self.schedule == 'monthly':
            return MonthlySchedule(start=self.started_at)
        elif self.schedule == 'exponential_3':
            return ExponentialSchedule(start=self.started_at, base=3)
        else:
            raise ValueError(f"Unknown schedule type: {self.schedule}")

    def get_activity_buckets(self, size: int = None, limit: int = None) -> list[Bucket]:
        """Get log buckets of the given `size` in seconds."""
        from . import Log

        if not size:
            size = self._schedule.get_scale()

        def date_to_int(dt: DateTimeField):
            return fn.strftime('%s', dt).cast('INTEGER')

        bucket = (date_to_int(Log.start) / size).cast('INTEGER')

        duration = Case(None, [(Log.end.is_null(), 0)],
                        default=(date_to_int(Log.end) - date_to_int(Log.start)))

        rows = (Log.select(
            fn.MIN(Log.start).alias('start'),
            fn.MAX(Log.start).alias('end'),
            fn.SUM(duration).alias('net_duration'),
            fn.COUNT().alias('row_count'))
            .group_by(bucket)
            .where(Log.habit == self)
            .limit(limit)
            .order_by(fn.MIN(Log.start)))

        return list(map(lambda r: Bucket(start=r.start, end=r.end, net_duration=r.net_duration, sessions=r.row_count), rows))

    def get_streak(self) -> int:
        buckets = self.get_activity_buckets()
        if not buckets:
            return 0

        streak = 0
        i = len(buckets) - 1
        task = self._schedule.get_previous_task(datetime.now())
        while task and task >= self._schedule.start and i >= 0:
            if not self._qualifies_for_streak(buckets[i], task):
                break
            streak += 1
            i -= 1
            task = self._schedule.get_previous_task(task)

        return streak

    def get_longest_streak(self) -> int:
        buckets = self.get_activity_buckets(self._schedule.get_scale())
        if not buckets:
            return 0

        longest_streak, current_streak = 0, 0
        i = len(buckets) - 1
        task = self._schedule.get_previous_task(datetime.now())
        while task and task >= self._schedule.start and i >= 0:
            if self._qualifies_for_streak(buckets[i], task):
                current_streak += 1
            else:
                longest_streak = max(current_streak, longest_streak)
                current_streak = 0
            i -= 1
            task = self._schedule.get_previous_task(task)

        if current_streak > longest_streak:
            longest_streak = current_streak

        return longest_streak

    def _qualifies_for_streak(self, bucket: Bucket, task: datetime) -> bool:
        """Check if the given bucket qualifies for streak counting."""
        if bucket.start <= self._schedule.start + timedelta(seconds=self._schedule.get_scale()):
            return True
        if not self._schedule.is_task_scheduled(bucket.start, task):
            return False
        if bucket.net_duration < (self.allocated_time or 0):
            return False
        return True

