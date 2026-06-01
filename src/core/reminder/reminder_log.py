import uuid
from datetime import datetime
from peewee import *
from core.db import BaseModel
from .reminder import Reminder


class ReminderLog(BaseModel):
    """
    Log of reminder firings and user feedback.

    Tracks when reminders fired, what action was executed,
    and optional user feedback for future scheduling adjustments.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    reminder = ForeignKeyField(Reminder, backref='logs', on_delete='CASCADE')
    fired_at = DateTimeField(default=datetime.now, index=True)
    action_executed = CharField()
    notification_sent = BooleanField(default=False)
    feedback_rating = IntegerField(null=True)  # Legacy reminder feedback rating
    context_modifier = FloatField(default=1.0)
    was_overdue = BooleanField(default=False)
    device_id = CharField(default='')
    updated_at = DateTimeField(default=datetime.now)
    deleted_at = DateTimeField(null=True)

    class Meta:
        table_name = 'reminder_log'
