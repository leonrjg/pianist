import uuid
from datetime import datetime
from typing import Optional, List
from peewee import *
from core.db import BaseModel
from .mood import Mood


class MoodLog(BaseModel):
    """
    Represents a mood beacon — a point-in-time mood tag.

    Args:
        id: Unique identifier for the log.
        mood: Foreign key to Mood.
        start: When this mood was logged.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    mood = ForeignKeyField(Mood, backref='logs', on_delete='CASCADE')
    start: datetime = DateTimeField(index=True)
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)

    class Meta:
        table_name = 'mood_log'

    @staticmethod
    def log_new_mood(mood: Mood) -> 'MoodLog':
        """Log a mood beacon."""
        return MoodLog.create(
            mood=mood,
            start=datetime.now(),
        )

    @staticmethod
    def get_recent_logs(limit: int = 20) -> List['MoodLog']:
        """Get recent mood logs across all moods, ordered by start time (descending)."""
        return list(MoodLog
                   .select()
                   .where(MoodLog.deleted_at.is_null())
                   .order_by(MoodLog.start.desc())
                   .limit(limit))
