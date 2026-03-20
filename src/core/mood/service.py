"""
Mood Service - owns all mood reads and writes for the GUI.
"""

from datetime import datetime
from typing import List, Optional

from .mood import Mood
from .mood_log import MoodLog


class MoodService:

    @classmethod
    def get_all(cls) -> List[Mood]:
        """All non-deleted moods ordered by display_order."""
        return Mood.get_all_ordered()

    @classmethod
    def get_current_log(cls) -> Optional[MoodLog]:
        """The currently active mood log, or None."""
        return Mood.get_current_mood_log()

    @classmethod
    def get_recent_logs(cls, limit: int = 15) -> List[MoodLog]:
        """Recent mood logs across all moods."""
        return MoodLog.get_recent_logs(limit=limit)

    @classmethod
    def log_mood(cls, mood: Mood) -> MoodLog:
        """Start a new mood log, ending the current one if any."""
        return MoodLog.log_new_mood(mood)

    @classmethod
    def end_mood_log(cls, log: MoodLog, reason: str = 'manual') -> None:
        """End an active mood log."""
        log.end_now(reason)

    @classmethod
    def create_mood(cls, symbol: str, description: str) -> Mood:
        """Create a new mood with the next available display_order."""
        moods = Mood.select().where(Mood.deleted_at.is_null())
        max_order = max((m.display_order for m in moods), default=0)
        return Mood.create(
            symbol=symbol,
            description=description,
            display_order=max_order + 1
        )

    @classmethod
    def update_mood_symbol(cls, mood: Mood, new_symbol: str) -> None:
        """Update the symbol of a mood."""
        mood.symbol = new_symbol
        mood.updated_at = datetime.now()
        mood.save()

    @classmethod
    def update_mood_description(cls, mood: Mood, new_description: str) -> None:
        """Update the description of a mood."""
        mood.description = new_description
        mood.updated_at = datetime.now()
        mood.save()

    @classmethod
    def move_mood_up(cls, mood: Mood) -> None:
        """Move a mood one position earlier in display order."""
        moods = Mood.get_all_ordered()
        idx = next((i for i, m in enumerate(moods) if m.id == mood.id), None)
        if idx is None or idx == 0:
            return
        moods[idx].display_order, moods[idx - 1].display_order = (
            moods[idx - 1].display_order, moods[idx].display_order
        )
        moods[idx].save()
        moods[idx - 1].save()

    @classmethod
    def move_mood_down(cls, mood: Mood) -> None:
        """Move a mood one position later in display order."""
        moods = Mood.get_all_ordered()
        idx = next((i for i, m in enumerate(moods) if m.id == mood.id), None)
        if idx is None or idx == len(moods) - 1:
            return
        moods[idx].display_order, moods[idx + 1].display_order = (
            moods[idx + 1].display_order, moods[idx].display_order
        )
        moods[idx].save()
        moods[idx + 1].save()

    @classmethod
    def delete_mood(cls, mood: Mood) -> None:
        """Soft-delete a mood."""
        mood.deleted_at = datetime.now()
        mood.updated_at = datetime.now()
        mood.save()

    @classmethod
    def delete_log(cls, log: MoodLog) -> None:
        """Soft-delete a mood log."""
        log.deleted_at = datetime.now()
        log.updated_at = datetime.now()
        log.save()
