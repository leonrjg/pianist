import json
from datetime import datetime
from typing import Dict, Any
from urllib.parse import parse_qs
from peewee import *
from db import BaseModel
from .habit import Habit


class HabitTracker(BaseModel):
    """
    Junction table linking habits to their enabled trackers.
    
    Args:
        habit: Foreign key reference to the habit
        tracker: Type of tracker ('window', 'io', etc.)
        config: JSON string containing tracker-specific configuration
        is_enabled: Whether this tracker is currently enabled for the habit
        created_at: When this tracker was added to the habit
    """
    class Meta:
        primary_key = CompositeKey('habit', 'tracker')

    habit = ForeignKeyField(Habit, backref='trackers')
    tracker = CharField()
    config = TextField(null=True)
    is_enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)

    def get_config(self) -> Dict[str, Any]:
        """Parse and return the config as a dictionary."""
        if self.config:
            return json.loads(str(self.config))
        return {}
    
    @property
    def tracker_instance(self):
        """Get actual Tracker instance."""
        from tracker.io import IOTracker
        from tracker.window import WindowTracker
        
        config = self.get_config()
        if self.tracker == 'io':
            return IOTracker()
        elif self.tracker == 'window':
            return WindowTracker(config.get('keywords', []))
        else:
            raise ValueError(f"Unknown tracker type: {self.tracker}")
    
    @classmethod
    def create_json_config(cls, config_string: str) -> str:
        """Parse URL query string format configuration and return JSON."""
        return json.dumps(parse_qs(config_string) or {})