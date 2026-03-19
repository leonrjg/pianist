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
    """
    type: TaskType
    scheduled_at: datetime
    title: str
    habit: Optional['Habit']
    completed: bool
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    source_id: Optional[int] = None

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
    def from_habit(cls, habit: 'Habit', scheduled_at: datetime) -> 'Task':
        """
        Create a Task from a habit and scheduled datetime.

        Args:
            habit: The habit this task belongs to
            scheduled_at: When the task is scheduled

        Returns:
            Task instance representing this scheduled habit task
        """
        return cls(
            type=TaskType.HABIT,
            scheduled_at=scheduled_at,
            title=habit.name,
            habit=habit,
            completed=habit.is_task_completed(scheduled_at),
            completed_at=None,  # Habit tasks don't track exact completion time
            created_at=habit.created_at,
            source_id=habit.id
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
            source_id=manual_task.id
        )
