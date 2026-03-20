import uuid
from datetime import datetime
from typing import Optional

from peewee import *
from core.db import BaseModel
from .habit import Habit

class Log(BaseModel):
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    habit = ForeignKeyField(Habit, backref='logs', on_delete='CASCADE')
    start: datetime = DateTimeField(index=True)
    end: Optional[datetime] = DateTimeField(null=True, index=True)
    started_by = CharField(null=True)
    ended_by = CharField(null=True)
    idle_time: int = IntegerField(default=0)
    offset: int = IntegerField(default=0)  # Manual time adjustment in seconds
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)
