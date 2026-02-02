"""
ManualTask model - Represents manually completed scheduled tasks.
"""

from datetime import datetime
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit


class ManualTask(BaseModel):
    """
    Represents a manually marked completion of a scheduled task.

    This allows users to mark tasks as complete without tracking actual session time.
    Useful for tasks done offline or when tracking wasn't available.

    Args:
        habit: The habit this manual completion belongs to.
        title: Custom description (nullable - reserved for future custom task feature).
        created_at: When the user marked this task complete.
        completed_at: The scheduled task datetime that was marked complete.
    """
    id = AutoField()
    habit = ForeignKeyField(Habit, backref='manual_tasks', on_delete='CASCADE')
    title = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    completed_at = DateTimeField()

    class Meta:
        table_name = 'manual_task'
        indexes = (
            (('habit', 'completed_at'), False),  # Index for fast lookups
        )
