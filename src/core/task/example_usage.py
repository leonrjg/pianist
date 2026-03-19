"""
Example usage of the Task abstraction.

This demonstrates how to use the unified Task interface for both
habit-scheduled tasks and manual tasks.
"""

from datetime import datetime, timedelta
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from core.task import Task, TaskType, get_upcoming_tasks


def example_basic_usage():
    """Basic usage of Task abstraction."""

    # Get all active habits
    active_habits = list(Habit.select().where(Habit.archived == False))

    # Get all upcoming tasks for the next 7 days
    tasks = get_upcoming_tasks(
        habits=active_habits,
        timespan=7 * 24 * 60 * 60,
        include_manual=True,
        include_completed=True
    )

    # Display tasks
    print("\n=== Upcoming Tasks (Next 7 Days) ===\n")

    for task in tasks:
        # Format output
        status = "✓" if task.completed else "○"
        overdue = " [OVERDUE]" if task.is_overdue else ""
        task_type = " [Manual]" if task.is_manual_task else ""

        print(f"{status} {task.title}{task_type}{overdue}")
        print(f"   Scheduled: {task.scheduled_at.strftime('%Y-%m-%d %H:%M')}")

        if task.completed and task.completed_at:
            print(f"   Completed: {task.completed_at.strftime('%Y-%m-%d %H:%M')}")

        print()


def example_creating_manual_task():
    """Example of creating a standalone manual task."""

    # Create a custom task not tied to any habit
    tomorrow = datetime.now() + timedelta(days=1)
    tomorrow = tomorrow.replace(hour=14, minute=0, second=0, microsecond=0)

    manual_task = ManualTask.create(
        habit=None,  # No habit association
        title="Call dentist for appointment",
        scheduled_at=tomorrow,
        completed_at=None  # Not completed yet
    )

    print(f"\nCreated manual task: {manual_task.title}")
    print(f"Scheduled for: {manual_task.scheduled_at}")
    print(f"Is completed: {manual_task.is_completed}")
    print(f"Is custom task: {manual_task.is_custom_task}")

    # Convert to Task object
    task = Task.from_manual_task(manual_task)
    print(f"\nTask object created:")
    print(f"  Type: {task.type.value}")
    print(f"  Title: {task.title}")
    print(f"  Overdue: {task.is_overdue}")


def example_completing_manual_task():
    """Example of completing a manual task."""

    # Find an incomplete manual task
    incomplete_task = ManualTask.select().where(
        ManualTask.completed_at.is_null()
    ).first()

    if incomplete_task:
        # Mark it complete
        incomplete_task.completed_at = datetime.now()
        incomplete_task.save()

        print(f"\nMarked task as complete: {incomplete_task.title}")
        print(f"Completed at: {incomplete_task.completed_at}")


def example_filtering_tasks():
    """Example of filtering tasks by various criteria."""

    active_habits = list(Habit.select().where(Habit.archived == False))

    # Get only incomplete tasks
    incomplete_tasks = get_upcoming_tasks(
        habits=active_habits,
        timespan=7 * 24 * 60 * 60,
        include_completed=False
    )

    print(f"\n=== Incomplete Tasks ({len(incomplete_tasks)}) ===\n")
    for task in incomplete_tasks:
        print(f"○ {task.title} - {task.scheduled_at.strftime('%Y-%m-%d')}")

    # Filter by task type
    habit_tasks = [t for t in incomplete_tasks if t.is_habit_task]
    manual_tasks = [t for t in incomplete_tasks if t.is_manual_task]

    print(f"\n  Habit tasks: {len(habit_tasks)}")
    print(f"  Manual tasks: {len(manual_tasks)}")

    # Find overdue tasks
    overdue_tasks = [t for t in incomplete_tasks if t.is_overdue]

    if overdue_tasks:
        print(f"\n=== Overdue Tasks ({len(overdue_tasks)}) ===\n")
        for task in overdue_tasks:
            print(f"! {task.title} - {task.scheduled_at.strftime('%Y-%m-%d')}")


def example_habit_task_completion():
    """Example of manually completing a habit-scheduled task."""

    # Get a habit
    habit = Habit.select().first()

    if habit:
        # Get the next scheduled task
        schedule = habit.get_schedule()
        next_task_dt = schedule.get_next_task(datetime.now())

        if next_task_dt:
            # Create a manual completion record
            normalized_dt = next_task_dt.replace(microsecond=0)

            ManualTask.create(
                habit=habit,
                title=None,  # None for habit completions
                scheduled_at=normalized_dt,
                completed_at=normalized_dt  # Completed immediately
            )

            print(f"\nMarked habit task as complete:")
            print(f"  Habit: {habit.name}")
            print(f"  Scheduled: {normalized_dt}")

            # Verify it's marked complete
            is_complete = habit.is_task_completed(normalized_dt)
            print(f"  Verified complete: {is_complete}")


if __name__ == '__main__':
    from core.db import db
    db.connect()

    print("=" * 60)
    print("Task Abstraction Examples")
    print("=" * 60)

    # Run examples
    example_basic_usage()
    # example_creating_manual_task()
    # example_completing_manual_task()
    # example_filtering_tasks()
    # example_habit_task_completion()
