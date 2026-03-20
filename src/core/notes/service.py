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
