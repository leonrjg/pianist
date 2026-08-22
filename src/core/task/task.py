from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.habit.habit import Habit
    from core.habit.manual_task import ManualTask


class TaskType(Enum):
    """Type of task."""
    HABIT = "habit"      # Computed from habit schedule
    MANUAL = "manual"    # User-created manual task


@dataclass(frozen=True)
class Task:
    """
    Unified task representation for both habit-scheduled and manual tasks.

    Immutable value object that provides a common interface for displaying
    and working with tasks from different sources.

    Attributes:
        type: Whether this is a habit-scheduled or manual task
        scheduled_at: When the task is scheduled/due
        title: Display name for the task
        habit: Associated habit (None for standalone manual tasks)
        completed: Whether the task has been completed
        completed_at: When the task was completed (None if not completed)
        created_at: When the task record was created
        source_id: ID of the source object (habit.id or manual_task.id)
        display_order: Ordering of the backing object (habit or manual task) in the
            unified piano-key sequence. Lower sorts first.
    """
    type: TaskType
    scheduled_at: datetime
    title: str
    habit: Optional['Habit']
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    source_id: Optional[int] = None
    display_order: int = 0

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue (scheduled in past and not completed)."""
        return not self.completed and self.scheduled_at < datetime.now()

    @property
    def is_habit_task(self) -> bool:
        """Check if this is a habit-scheduled task."""
        return self.type == TaskType.HABIT

    @property
    def is_manual_task(self) -> bool:
        """Check if this is a manual task."""
        return self.type == TaskType.MANUAL

    @classmethod
    def from_habit(cls, habit: 'Habit', scheduled_at: datetime, checker=None) -> 'Task':
        """
        Create a Task from a habit and scheduled datetime.

        Args:
            habit: The habit this task belongs to
            scheduled_at: When the task is scheduled
            checker: Optional pre-built completion checker from habit.build_completion_checker().
                     Pass this when creating many tasks for the same habit to avoid
                     repeated DB queries. Falls back to habit.is_task_completed() if omitted.

        Returns:
            Task instance representing this scheduled habit task
        """
        completed = checker(scheduled_at) if checker is not None else habit.is_task_completed(scheduled_at)
        return cls(
            type=TaskType.HABIT,
            scheduled_at=scheduled_at,
            title=habit.name,
            habit=habit,
            completed=completed,
            completed_at=None,  # Habit tasks don't track exact completion time
            created_at=habit.created_at,
            source_id=habit.id,
            display_order=habit.display_order,
        )

    @classmethod
    def from_manual_task(cls, manual_task: 'ManualTask') -> 'Task':
        """
        Create a Task from a ManualTask database record.

        Args:
            manual_task: The ManualTask instance

        Returns:
            Task instance representing this manual task
        """
        return cls(
            type=TaskType.MANUAL,
            scheduled_at=manual_task.scheduled_at,
            title=manual_task.title or (manual_task.habit.name if manual_task.habit else "Untitled"),
            habit=manual_task.habit,
            completed=manual_task.completed_at is not None,
            completed_at=manual_task.completed_at,
            created_at=manual_task.created_at,
            source_id=manual_task.id,
            display_order=manual_task.display_order,
        )
