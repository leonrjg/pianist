"""
Note Service - thin wrapper over Note class methods for GUI use.
"""

from .note import Note
from core.habit.habit import Habit


class NoteService:

    @classmethod
    def get_global_note(cls) -> Note:
        """Get or create the global note."""
        return Note.get_global_note()

    @classmethod
    def get_habit_note(cls, habit: Habit) -> Note:
        """Get or create the note for a specific habit."""
        return Note.get_habit_note(habit)

    @classmethod
    def get_note_by_id(cls, note_id) -> Note:
        """Get a non-deleted note by id."""
        return Note.get_active_by_id(note_id)

    @classmethod
    def list_global_notes(cls):
        """List all non-deleted global notes."""
        return list(Note.list_global_notes())

    @classmethod
    def list_habit_notes(cls, habit: Habit):
        """List all non-deleted notes for a habit."""
        return list(Note.list_habit_notes(habit))

    @classmethod
    def create_global_note(cls, title: str = None) -> Note:
        """Create a global note."""
        return Note.create_global_note(title=title)

    @classmethod
    def create_habit_note(cls, habit: Habit, title: str = None) -> Note:
        """Create a note for a specific habit."""
        return Note.create_habit_note(habit, title=title)

    @classmethod
    def rename_note(cls, note: Note, title: str) -> None:
        """Rename a note."""
        note.rename(title)

    @classmethod
    def delete_note(cls, note: Note) -> None:
        """Soft-delete a note."""
        note.delete_note()

    @classmethod
    def create_thought(cls, content: str) -> Note:
        """Create a quick thought."""
        return Note.create_thought(content)

    @classmethod
    def list_thoughts(cls) -> list:
        """List all non-deleted thoughts in reverse chronological order."""
        return list(Note.list_thoughts())
