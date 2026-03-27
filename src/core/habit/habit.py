import uuid
from datetime import datetime
from datetime import timedelta
from typing import Optional

from peewee import *
from core.schedule.schedule import Schedule
from core.db import BaseModel

from core.schedule.daily import DailySchedule
from core.schedule.exponential import ExponentialSchedule
from core.schedule.weekly import WeeklySchedule
from core.schedule.monthly import MonthlySchedule
from core.schedule.hourly import HourlySchedule

from .bucket import Bucket
from ..util.time import get_naive_timestamp


class Habit(BaseModel):
    """
    Represents a habit with scheduling and tracking details.

    Args:
        id: Unique identifier for the habit.
        name: Name of the habit.
        schedule: Schedule type (e.g., 'hourly', 'daily', 'weekly', 'monthly', 'exponential_3').
        created_at: Timestamp when the habit was created.
        updated_at: Timestamp when the habit was last updated.
        started_at: Timestamp when the habit tracking started.
        ended_at: Timestamp when the habit tracking ended (if applicable).
        inactivity_threshold: Time in seconds to consider inactivity (only relevant for trackers).
        allocated_time: Total allocated time for the habit in seconds (minimum time to qualify for streaks).
        visible: Whether the habit appears as a piano key (True) or only in drawer lists (False).
        archived: Whether the habit is archived (retired but historical data preserved).
        note: Markdown notes for the habit.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()
    schedule: str = CharField(index=True)
    schedule_step = IntegerField(default=1)
    created_at = DateTimeField(default=datetime.now().date())
    updated_at = DateTimeField(default=datetime.now().date())
    started_at = DateTimeField(default=datetime.now().date())
    ended_at = DateTimeField(null=True)
    inactivity_threshold = IntegerField(default=120)
    allocated_time: Optional[int] = IntegerField(null=True)
    display_order = IntegerField(default=0)
    visible = BooleanField(default=True)
    archived = BooleanField(default=False)
    note = TextField(null=True)
    device_id = CharField(default='')
    deleted_at = DateTimeField(null=True)
    
    def __init__(self, *args, **kwargs):
        """Initialize habit with schedule instance."""
        super().__init__(*args, **kwargs)
        self._schedule: Schedule = self._get_schedule()

    def get_schedule(self) -> Schedule:
        """Get the Schedule instance for this habit."""
        return self._schedule

    def _get_schedule(self) -> Schedule:
        """Get actual Schedule instance based on schedule type."""
        # Use ended_at if set, otherwise use a far future date
        end = self.ended_at if self.ended_at else datetime(2100, 1, 1)

        # Get step value, with backward compatibility fallback
        step = self.schedule_step if hasattr(self, 'schedule_step') else 1

        registry = {
            'hourly': lambda: HourlySchedule(start=self.started_at, end=end, step=step),
            'daily': lambda: DailySchedule(start=self.started_at, end=end, step=step),
            'weekly': lambda: WeeklySchedule(start=self.started_at, end=end, step=step),
            'monthly': lambda: MonthlySchedule(start=self.started_at, end=end, step=step),
            'exponential_3': lambda: ExponentialSchedule(start=self.started_at, end=end, base=3),
        }

        if self.schedule not in registry:
            raise ValueError(f"Unknown schedule type: {self.schedule}")

        return registry[self.schedule]()

    def get_activity_buckets(self, size: int = None, limit: int = None, since: datetime = None) -> list[Bucket]:
        """
            Get log buckets of the given `size` in seconds.
            Returns: Descending list of Buckets ordered by start date.
        """
        from core.habit.log import Log

        if not size:
            size = self._schedule.get_scale()

        def date_to_int(dt: DateTimeField):
            return fn.strftime('%s', dt).cast('INTEGER')

        bucket = (date_to_int(Log.start) / size).cast('INTEGER')

        duration = Case(None, [(Log.end.is_null(), 0)],
                        default=(date_to_int(Log.end) - date_to_int(Log.start) - fn.COALESCE(Log.idle_time, 0) + fn.COALESCE(Log.offset, 0)))

        where_clause = (Log.habit == self) & (Log.end.is_null(False)) & Log.deleted_at.is_null()
        if since:
            where_clause = where_clause & (Log.start >= since)

        rows = (Log.select(
            fn.MIN(Log.start).alias('start'),
            fn.MAX(Log.end).alias('end'),
            fn.SUM(duration).alias('net_duration'),
            fn.COUNT().alias('row_count'))
            .group_by(bucket)
            .where(where_clause)
            .limit(limit)
            .order_by(fn.MIN(Log.start).desc()))

        return list(map(lambda r: Bucket(start=r.start, end=r.end, net_duration=r.net_duration, sessions=r.row_count), rows))

    def get_streak(self) -> int:
        """
        Calculate the current streak of consecutive completed periods.

        A streak counts consecutive periods where the habit was completed
        without breaking, starting from the most recent period.

        Returns:
            Number of consecutive completed periods from present backwards.
        """
        buckets = self.get_activity_buckets(since=self._schedule.start)
        if not buckets:
            return 0

        streak = 0
        task = self._schedule.get_next_task(datetime.now()) or self._schedule.start
        while task and task >= self._schedule.start:
            bucket = self._find_bucket_for_task(buckets, task)
            if bucket and self._qualifies_for_streak(bucket):
                streak += 1
            elif task < datetime.now():
                break
            task = self._schedule.get_previous_task(task)

        return streak

    def get_longest_streak(self) -> int:
        """
        Calculate the longest streak of completed tasks in the habit's history.
        Compare activity buckets against the habit's schedule to find the maximum consecutive completion count.

        Returns:
            Maximum number of consecutive periods completed in habit history.
        """
        buckets = self.get_activity_buckets(since=self._schedule.start)
        if not buckets:
            return 0

        longest_streak, current_streak = 0, 0
        task = self._schedule.get_next_task(buckets[0].start)
        while task and task >= self._schedule.start:
            bucket = self._find_bucket_for_task(buckets, task)
            if bucket and self._qualifies_for_streak(bucket):
                current_streak += 1
            else:
                longest_streak = max(current_streak, longest_streak)
                current_streak = 0
            task = self._schedule.get_previous_task(task)

        return max(current_streak, longest_streak)

    def build_completion_checker(self, start: datetime, end: datetime):
        """
        Return a callable that checks completion for any task datetime in [start, end].

        Fetches activity buckets and manual completions once, so callers checking
        many tasks avoid N DB queries.
        """
        from core.habit.manual_task import ManualTask
        buckets = self.get_activity_buckets(since=start)
        manual_completions = set(
            mt.scheduled_at.replace(microsecond=0)
            for mt in ManualTask.select(ManualTask.scheduled_at).where(
                (ManualTask.habit == self) &
                (ManualTask.scheduled_at >= start) &
                (ManualTask.scheduled_at <= end) &
                (ManualTask.completed_at.is_null(False)) &
                ManualTask.deleted_at.is_null()
            )
        )

        def checker(task: datetime) -> bool:
            bucket = self._find_bucket_for_task(buckets, task)
            if bucket and self._qualifies_for_streak(bucket):
                return True
            return task.replace(microsecond=0) in manual_completions

        return checker

    def _is_window_completed_by_log(self, min_threshold: datetime, max_threshold: datetime) -> bool:
        """Check if any tracked session in [min_threshold, max_threshold) meets the completion threshold."""
        from core.habit.log import Log

        def date_to_int(dt):
            return fn.strftime('%s', dt).cast('INTEGER')

        duration_expr = Case(None, [(Log.end.is_null(), 0)],
                             default=(date_to_int(Log.end) - date_to_int(Log.start)
                                      - fn.COALESCE(Log.idle_time, 0)
                                      + fn.COALESCE(Log.offset, 0)))

        net = (Log.select(fn.SUM(duration_expr))
               .where(
                   (Log.habit == self) &
                   (Log.start >= min_threshold) &
                   (Log.start < max_threshold) &
                   Log.end.is_null(False) &
                   Log.deleted_at.is_null()
               )
               .scalar())
        if net is None:
            return False
        return net >= (self.allocated_time or 0)

    def is_task_completed(self, task: datetime) -> bool:
        """
        Check if the habit's task for the given datetime has been completed.

        Checks both actual tracked sessions (via activity buckets) and manual completions.

        Args:
            task: The datetime of the scheduled task to check.

        Returns:
            True if the task was completed (either tracked or manually), False otherwise.
        """
        unit = self._schedule.get_scale()
        min_threshold = task - timedelta(seconds=int(get_naive_timestamp(task)) % unit)
        max_threshold = min_threshold + timedelta(seconds=unit)

        if self._is_window_completed_by_log(min_threshold, max_threshold):
            return True

        from core.habit.manual_task import ManualTask
        normalized_task = task.replace(microsecond=0)
        return ManualTask.select().where(
            (ManualTask.habit == self) &
            (ManualTask.scheduled_at == normalized_task) &
            (ManualTask.completed_at.is_null(False)) &
            ManualTask.deleted_at.is_null()
        ).exists()

    def _find_bucket_for_task(self, buckets: list[Bucket], task: datetime) -> Optional[Bucket]:
        """Find the bucket that contains the given task datetime, if any."""
        unit = self._schedule.get_scale()
        # Get lower boundary of the unit containing the task
        min_threshold = task - timedelta(seconds=int(get_naive_timestamp(task)) % unit)
        # Get upper boundary of the unit
        max_threshold =  min_threshold + timedelta(seconds=unit)

        for bucket in buckets:
            # Buckets are descending, so if we go below min_threshold, stop searching
            if bucket.start < min_threshold:
                break
            if min_threshold <= bucket.start <= max_threshold:
                return bucket
        return None

    @staticmethod
    def completion_rate(completed: int, scheduled: int) -> float:
        if completed == 0 and scheduled == 0:
            return 0.0
        if scheduled == 0:
            return 1.0
        return min(completed / scheduled, 1.0)

    @classmethod
    def with_longest_streak(cls, habits: list['Habit']) -> 'Habit':
        return max(habits, key=lambda h: h.get_longest_streak())

    @classmethod
    def grouped_by_schedule(cls, habits: list['Habit']):
        from itertools import groupby
        return groupby(
            sorted(habits, key=lambda h: h.schedule),
            key=lambda h: h.schedule)

    @classmethod
    def sorted_by_completion_rate(cls, habits: list['Habit']) -> list[tuple['Habit', float]]:
        from core.util.time import get_timespan
        habit_rates = []
        for habit in habits:
            schedule = habit.get_schedule()
            previous_tasks = len(schedule.get_previous_tasks(get_timespan(schedule.start)))
            buckets = len(habit.get_activity_buckets())
            rate = Habit.completion_rate(buckets, previous_tasks)
            habit_rates.append((habit, rate))
        return sorted(habit_rates, key=lambda x: x[1], reverse=True)

    def _qualifies_for_streak(self, bucket: Bucket) -> bool:
        """Check if the given bucket qualifies for streak counting."""
        if self.allocated_time and bucket.net_duration < (self.allocated_time or 0):
            return False
        if bucket.start <= self._schedule.start + timedelta(seconds=self._schedule.get_scale()):
            return True
        return True
