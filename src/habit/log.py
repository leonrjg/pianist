from datetime import datetime
from typing import Optional

from peewee import *
from db import BaseModel
from .habit import Habit

class Log(BaseModel):
    id = AutoField()
    habit = ForeignKeyField(Habit, backref='logs', on_delete='CASCADE')
    start: datetime = DateTimeField(index=True)
    end: Optional[datetime] = DateTimeField(null=True, index=True)
    started_by = CharField(null=True)
    ended_by = CharField(null=True)
    idle_time: int = IntegerField(default=0)
