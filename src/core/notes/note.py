"""
Note model for storing user notes.

Notes can be either global (habit_id=null) or associated with specific habits.
"""

import uuid
from datetime import datetime
from typing import Optional
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit


class Note(BaseModel):
    """
    Represents a user note or quick thought.

    Args:
        id: Unique identifier for the note.
        habit_id: Foreign key to Habit (nullable). Null indicates global note.
        content: Text content of the note.
        kind: Discriminator — 'note' for regular notes, 'thought' for quick thoughts.
        created_at: Timestamp when the note was created.
        updated_at: Timestamp when the note was last updated.
    """

    KIND_NOTE = 'note'
    KIND_THOUGHT = 'thought'

    id = UUIDField(primary_key=True, default=uuid.uuid4)
    habit = ForeignKeyField(Habit, null=True, backref='notes', on_delete='CASCADE')
    title = CharField(default='Default note')
    content = TextField(default='')
    kind = CharField(default=KIND_NOTE)
    display_order = IntegerField(default=0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    device_id = CharField(default='')
    deleted_at = DateTimeField(null=True)

    @classmethod
    def _active_notes(cls):
        return cls.select().where(cls.deleted_at.is_null())

    @classmethod
    def _notes_for_habit(cls, habit: Optional[Habit]):
        query = cls._active_notes().where(cls.kind == cls.KIND_NOTE)
        if habit is None:
            query = query.where(cls.habit.is_null())
        else:
            query = query.where(cls.habit == habit)
        return query.order_by(cls.display_order, cls.created_at, cls.id)

    @classmethod
    def list_thoughts(cls):
        """List all non-deleted thoughts in reverse chronological order."""
        return (
            cls._active_notes()
            .where(cls.kind == cls.KIND_THOUGHT)
            .order_by(cls.created_at.desc(), cls.id.desc())
        )

    @classmethod
    def create_thought(cls, content: str) -> 'Note':
        """Create a quick thought (no habit association, no title needed)."""
        return cls.create(habit=None, title='', content=content, kind=cls.KIND_THOUGHT)

    @classmethod
    def get_global_note(cls) -> 'Note':
        """
        Get or create the global note (habit_id=null).

        Returns:
            The global Note instance.
        """
        note = cls.list_global_notes().first()
        if note is None:
            note = cls.create_global_note(title='Default note')
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
        note = cls.list_habit_notes(habit).first()
        if note is None:
            note = cls.create_habit_note(habit, title='Default note')
        return note

    @classmethod
    def get_active_by_id(cls, note_id) -> 'Note':
        """Get a non-deleted note by id."""
        return cls.get((cls.id == note_id) & cls.deleted_at.is_null())

    @classmethod
    def list_global_notes(cls):
        """List all non-deleted global notes."""
        return cls._notes_for_habit(None)

    @classmethod
    def list_habit_notes(cls, habit: Habit):
        """List all non-deleted notes for a habit."""
        return cls._notes_for_habit(habit)

    @classmethod
    def create_global_note(cls, title: Optional[str] = None, content: str = '') -> 'Note':
        """Create a global note."""
        return cls._create_note(None, title, content)

    @classmethod
    def create_habit_note(cls, habit: Habit, title: Optional[str] = None, content: str = '') -> 'Note':
        """Create a note for a habit."""
        return cls._create_note(habit, title, content)

    @classmethod
    def _create_note(cls, habit: Optional[Habit], title: Optional[str], content: str) -> 'Note':
        title = title or cls._next_note_title(habit)
        max_order = (
            cls._notes_for_habit(habit)
            .order_by(cls.display_order.desc())
            .first()
        )
        display_order = (max_order.display_order + 1) if max_order else 0
        return cls.create(habit=habit, title=title, content=content, display_order=display_order)

    @classmethod
    def _next_note_title(cls, habit: Optional[Habit]) -> str:
        existing_titles = {note.title for note in cls._notes_for_habit(habit)}
        if 'New note' not in existing_titles:
            return 'New note'

        index = 2
        while f'New note {index}' in existing_titles:
            index += 1
        return f'New note {index}'

    def rename(self, title: str) -> None:
        """Rename the note and update its timestamp."""
        self.title = title.strip() or 'Untitled note'
        self.updated_at = datetime.now()
        self.save()

    def update_content(self, content: str) -> None:
        """
        Update the note content and timestamp.

        Args:
            content: The new content for the note.
        """
        self.content = content
        self.updated_at = datetime.now()
        self.save()
