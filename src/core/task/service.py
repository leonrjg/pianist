"""
Task service for retrieving and managing tasks from all sources.
"""

from datetime import datetime, timedelta, date, time
from typing import List, Optional

from core.db import db
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from .task import Task, TaskType


class TaskService:
    """Service for manual-task reads and writes. All methods are class methods."""

    @classmethod
    def get_manual_tasks_in_range(cls, start: datetime, end: datetime) -> List[ManualTask]:
        """Get all non-deleted manual tasks scheduled within [start, end]."""
        return list(ManualTask.select().where(
            (ManualTask.scheduled_at >= start) &
            (ManualTask.scheduled_at <= end) &
            ManualTask.deleted_at.is_null()
        ))

    @classmethod
    def create_standalone_task(
        cls,
        title: str,
        scheduled_at: datetime,
        reminder_at: Optional[datetime] = None
    ) -> ManualTask:
        """Create a standalone (habit=None) manual task, optionally with a fixed reminder."""
        with db.atomic():
            task = ManualTask.create(
                habit=None,
                title=title,
                scheduled_at=scheduled_at,
                completed_at=None
            )
            if reminder_at is not None:
                from core.reminder.service import ReminderService
                ReminderService.create_fixed_for_manual_task(task, reminder_at)
            return task

    @classmethod
    def toggle_standalone_task_completion(cls, scheduled_at: datetime, completed: bool) -> None:
        """Toggle completed_at on the standalone manual task at the given datetime."""
        normalized_dt = scheduled_at.replace(microsecond=0)
        task = ManualTask.select().where(
            (ManualTask.scheduled_at == normalized_dt) &
            ManualTask.habit.is_null() &
            ManualTask.deleted_at.is_null()
        ).first()
        if task:
            task.completed_at = datetime.now() if completed else None
            task.updated_at = datetime.now()
            task.save()


def get_past_tasks(
    habits: List[Habit],
    lookback_seconds: int,
    include_manual: bool = True,
    include_completed: bool = True,
) -> List[Task]:
    """
    Get tasks scheduled within the past `lookback_seconds` seconds (strictly before today).

    Args:
        habits: List of habits to query
        lookback_seconds: How many seconds back to look
        include_manual: Whether to include standalone manual tasks
        include_completed: Whether to include already-completed tasks

    Returns:
        List of Task objects sorted ascending by scheduled_at
    """
    tasks: List[Task] = []
    now = datetime.now()
    cutoff = now - timedelta(seconds=lookback_seconds)
    today_start = datetime.combine(now.date(), time.min)

    for habit in habits:
        schedule = habit.get_schedule()
        past_dts = schedule.get_previous_tasks(lookback_seconds)
        checker = habit.build_completion_checker(cutoff, today_start)
        for scheduled_dt in past_dts:
            if scheduled_dt < today_start:
                task = Task.from_habit(habit, scheduled_dt, checker=checker)
                if include_completed or not task.completed:
                    tasks.append(task)

    if include_manual:
        for manual_task in ManualTask.select().where(
            ManualTask.deleted_at.is_null() &
            (ManualTask.scheduled_at >= cutoff) &
            (ManualTask.scheduled_at < today_start)
        ):
            task = Task.from_manual_task(manual_task)
            if include_completed or not task.completed:
                tasks.append(task)

    return sorted(tasks, key=lambda t: t.scheduled_at)


def get_upcoming_tasks(
    habits: List[Habit],
    timespan: int,
    include_manual: bool = True,
    include_completed: bool = True
) -> List[Task]:
    """
    Get all upcoming tasks from habits and manual tasks.

    Args:
        habits: List of habits to get scheduled tasks from
        timespan: How many seconds ahead to look
        include_manual: Whether to include standalone manual tasks
        include_completed: Whether to include already-completed tasks

    Returns:
        List of Task objects sorted by scheduled_at datetime
    """
    tasks: List[Task] = []
    now = datetime.now()
    cutoff = now + timedelta(seconds=timespan)
    start_of_today = datetime.combine(now.date(), time.min)

    # Get habit-scheduled tasks
    for habit in habits:
        schedule = habit.get_schedule()
        next_tasks = schedule.get_next_tasks(timespan)

        checker = habit.build_completion_checker(start_of_today, cutoff)
        for scheduled_dt in next_tasks:
            if scheduled_dt.date() >= now.date():
                task = Task.from_habit(habit, scheduled_dt, checker=checker)
                if include_completed or not task.completed:
                    tasks.append(task)

    if include_manual:
        for manual_task in ManualTask.select().where(
            ManualTask.deleted_at.is_null() &
            (ManualTask.scheduled_at >= start_of_today) &
            (ManualTask.scheduled_at <= cutoff) &
            (ManualTask.title.is_null(False) | ManualTask.completed_at.is_null())
        ):
            task = Task.from_manual_task(manual_task)
            if include_completed or not task.completed:
                tasks.append(task)

    return sorted(tasks, key=lambda t: t.scheduled_at)
