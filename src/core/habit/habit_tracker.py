import json
import uuid
from datetime import datetime
from typing import Dict, Any
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit


class HabitTracker(BaseModel):
    """
    Junction table linking habits to their enabled trackers.

    Args:
        id: UUID primary key.
        habit: Foreign key reference to the habit
        tracker: Type of tracker ('window', 'io', etc.)
        config: JSON string containing tracker-specific configuration
        is_enabled: Whether this tracker is currently enabled for the habit
        created_at: When this tracker was added to the habit
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    habit = ForeignKeyField(Habit, backref='trackers', on_delete='CASCADE')
    tracker = CharField()
    config = TextField(null=True)
    is_enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)

    class Meta:
        indexes = (
            (('habit', 'tracker'), True),  # unique-together
        )

    def get_config(self) -> Dict[str, Any]:
        """Parse and return the config as a dictionary."""
        if self.config:
            return json.loads(str(self.config))
        return {}
