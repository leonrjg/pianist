"""
Task service for retrieving and managing tasks from all sources.
"""

from datetime import datetime, timedelta
from typing import List
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from .task import Task, TaskType


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

    # Get habit-scheduled tasks
    for habit in habits:
        schedule = habit.get_schedule()
        next_tasks = schedule.get_next_tasks(timespan)

        for scheduled_dt in next_tasks:
            if scheduled_dt.date() >= now.date():
                task = Task.from_habit(habit, scheduled_dt)
                if include_completed or not task.completed:
                    tasks.append(task)

    # Get manual tasks
    if include_manual:
        # Use date comparison to match habit task behavior
        # Manual tasks are created at midnight, so we filter by date not exact time
        today = now.date()
        cutoff_date = cutoff.date()

        query = ManualTask.select()

        # Only get custom tasks (has title) or incomplete habit completions
        query = query.where(
            (ManualTask.title.is_null(False)) |
            (ManualTask.completed_at.is_null())
        )

        for manual_task in query:
            task_date = manual_task.scheduled_at.date()
            # Include tasks from today onwards, within the timespan
            if today <= task_date <= cutoff_date:
                task = Task.from_manual_task(manual_task)
                if include_completed or not task.completed:
                    tasks.append(task)

    return sorted(tasks, key=lambda t: t.scheduled_at)
