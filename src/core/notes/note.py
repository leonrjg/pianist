"""
Note model for storing user notes.

Notes can be either global (habit_id=null) or associated with specific habits.
"""

from datetime import datetime
from typing import Optional
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit


class Note(BaseModel):
    """
    Represents a user note.

    Args:
        id: Unique identifier for the note.
        habit_id: Foreign key to Habit (nullable). Null indicates global note.
        content: Text content of the note.
        created_at: Timestamp when the note was created.
        updated_at: Timestamp when the note was last updated.
    """
    id = AutoField()
    habit = ForeignKeyField(Habit, null=True, backref='notes', on_delete='CASCADE')
    content = TextField(default='')
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    @classmethod
    def get_global_note(cls) -> 'Note':
        """
        Get or create the global note (habit_id=null).

        Returns:
            The global Note instance.
        """
        note = cls.select().where(cls.habit.is_null()).first()
        if note is None:
            note = cls.create(habit=None, content='')
        return note

    @classmethod
    def get_habit_note(cls, habit: Habit) -> 'Note':
        """
        Get or create a note for a specific habit.

        Args:
            habit: The Habit instance to get the note for.

        Returns:
            The Note instance for the habit.
        """
        note = cls.select().where(cls.habit == habit).first()
        if note is None:
            note = cls.create(habit=habit, content='')
        return note

    def update_content(self, content: str) -> None:
        """
        Update the note content and timestamp.

        Args:
            content: The new content for the note.
        """
        self.content = content
        self.updated_at = datetime.now()
        self.save()
