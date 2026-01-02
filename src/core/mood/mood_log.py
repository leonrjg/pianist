from datetime import datetime, timedelta
from typing import Optional, List
from peewee import *
from core.db import BaseModel
from .mood import Mood


class MoodLog(BaseModel):
    """
    Represents a logged mood entry with time range.
    
    Args:
        id: Unique identifier for the log.
        mood: Foreign key to Mood.
        start: When this mood started.
        end: When this mood ended (defaults to 1 hour from start).
        ended_by: Reason for ending ('new_mood', 'expired', 'manual', etc.).
    """
    id = AutoField()
    mood = ForeignKeyField(Mood, backref='logs', on_delete='CASCADE')
    start: datetime = DateTimeField(index=True)
    end: Optional[datetime] = DateTimeField(null=True, index=True)
    ended_by = CharField(null=True)
    
    @staticmethod
    def log_new_mood(mood: Mood, ended_by_reason: str = 'new_mood') -> 'MoodLog':
        """
        Log a new mood, ending the current one if it exists.
        
        Args:
            mood: The Mood to log.
            ended_by_reason: Reason for ending previous mood (default: 'new_mood').
            
        Returns:
            The newly created MoodLog.
        """
        now = datetime.now()
        
        # End current mood if exists
        current = Mood.get_current_mood_log()
        if current:
            current.end_now(ended_by_reason)
        
        # Create new log with 1 hour duration
        new_log = MoodLog.create(
            mood=mood,
            start=now,
            end=now + timedelta(hours=1),
            ended_by=None
        )
        
        return new_log
    
    def end_now(self, reason: str = 'manual'):
        """
        End this mood log immediately.
        
        Args:
            reason: Reason for ending ('manual', 'new_mood', etc.).
        """
        self.end = datetime.now()
        self.ended_by = reason
        self.save()
    
    @staticmethod
    def get_recent_logs(limit: int = 20) -> List['MoodLog']:
        """
        Get recent mood logs across all moods.
        
        Args:
            limit: Maximum number of logs to return.
            
        Returns:
            List of MoodLog instances ordered by start time (descending).
        """
        return list(MoodLog
                   .select()
                   .order_by(MoodLog.start.desc())
                   .limit(limit))
    
    def get_duration_seconds(self) -> int:
        """
        Calculate the duration of this mood log in seconds.
        
        Returns:
            Duration in seconds, or 0 if end is None.
        """
        if not self.end:
            return 0
        return int((self.end - self.start).total_seconds())
    
    def is_active(self) -> bool:
        """Check if this mood log is currently active."""
        if not self.end:
            return False
        return self.end > datetime.now()
