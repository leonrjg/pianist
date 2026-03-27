import uuid
from datetime import datetime
from peewee import *
from core.db import BaseModel
from typing import Optional, List


class Mood(BaseModel):
    """
    Represents a mood type with symbol and description.

    Args:
        id: Unique identifier for the mood.
        symbol: Emoji/symbol representing the mood (e.g., '🟢', '🟣').
        description: Human-readable description of the mood.
        display_order: Order for displaying in UI.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    symbol = CharField()
    description = CharField()
    display_order = IntegerField(default=0)
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)
    
    @staticmethod
    def get_all_ordered() -> List['Mood']:
        """Get all moods ordered by display_order."""
        return list(Mood.select().where(Mood.deleted_at.is_null()).order_by(Mood.display_order))
    
    @staticmethod
    def get_last_mood_log() -> Optional['MoodLog']:
        """Get the most recently logged mood, or None."""
        from .mood_log import MoodLog
        try:
            return (MoodLog
                   .select()
                   .where(MoodLog.deleted_at.is_null())
                   .order_by(MoodLog.start.desc())
                   .get())
        except MoodLog.DoesNotExist:
            return None
    
    def can_delete(self) -> bool:
        """Check if this mood can be deleted (no logs reference it)."""
        return self.logs.count() == 0
    
    def get_recent_logs(self, limit: int = 20) -> List['MoodLog']:
        """Get recent logs for this mood."""
        return list(self.logs.order_by(self.logs.model.start.desc()).limit(limit))
