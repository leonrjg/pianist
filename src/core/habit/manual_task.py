"""
ManualTask model - Represents manually created tasks and manual completions.
"""

import uuid
from datetime import datetime
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit


class ManualTask(BaseModel):
    """
    Represents a manually created task or manual completion of a scheduled task.

    Supports two use cases:
    1. Manual completion of habit-scheduled tasks (habit != None, title == None)
    2. Standalone custom tasks (title != None, habit optional)

    Args:
        habit: Optional habit this task is associated with.
        title: Custom task title (None for habit completions, required for custom tasks).
        scheduled_at: When the task is scheduled/due.
        completed_at: When the task was marked complete (None if not yet completed).
        created_at: When this task record was created.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    habit = ForeignKeyField(Habit, backref='manual_tasks', on_delete='CASCADE', null=True)
    title = TextField(null=True)
    scheduled_at = DateTimeField(index=True)
    completed_at = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
    display_order = IntegerField(default=0)
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)

    class Meta:
        table_name = 'manual_task'
        indexes = (
            (('habit', 'scheduled_at'), False),  # Fast lookups by habit+schedule
            (('scheduled_at',), False),          # Fast lookups for upcoming tasks
        )

    @property
    def is_completed(self) -> bool:
        """Check if this task has been completed."""
        return self.completed_at is not None

    @property
    def is_custom_task(self) -> bool:
        """Check if this is a standalone custom task (not a habit completion)."""
        return self.title is not None
