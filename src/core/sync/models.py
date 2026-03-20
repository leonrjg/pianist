import uuid
from datetime import datetime
from peewee import *
from core.db import BaseModel


class Device(BaseModel):
    """Registry of known sync peers (local + discovered on LAN)."""
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()        # e.g. "Leon's MacBook"
    is_self = BooleanField()  # True for the local device
    last_seen = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)


class SyncState(BaseModel):
    """Tracks the last successful sync timestamp per remote peer (local only, never synced)."""
    device_id = UUIDField(primary_key=True)
    last_sync_at = DateTimeField()

    class Meta:
        table_name = 'syncstate'
