import uuid
from datetime import datetime
from peewee import *
from core.db import BaseModel
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask


class Reminder(BaseModel):
    """
    Reminder with stochastic or fixed-time scheduling.

    Supports three action types: open_link, random_line, show_text.
    Can optionally be linked to a habit for context.
    """
    id = UUIDField(primary_key=True, default=uuid.uuid4)
    name = CharField()
    reminder_type = CharField()  # 'stochastic' or 'fixed'
    habit = ForeignKeyField(Habit, null=True, on_delete='SET NULL', backref='reminders')
    manual_task = ForeignKeyField(ManualTask, null=True, on_delete='SET NULL', backref='reminders')

    # Action
    action_type = CharField()  # 'open_link', 'random_line', 'show_text'
    action_payload = TextField()  # URL, file path, or text
    notification_method = CharField(default='desktop')  # 'desktop', 'none'

    # Legacy scheduling fields retained for existing databases
    ease_factor = FloatField(default=2.5)
    interval_days = IntegerField(default=1)

    # Stochastic-specific
    target_rate_per_week = FloatField(null=True)
    weight = FloatField(default=1.0)

    # Scheduling
    last_fired_at = DateTimeField(null=True)
    next_fire_at = DateTimeField(null=True)
    fixed_time_minute = IntegerField(null=True)  # minutes from midnight for fixed reminders
    active_start_minute = IntegerField(default=0)  # minutes from midnight
    active_end_minute = IntegerField(default=1440)  # minutes from midnight
    context_config = TextField(default='{}')  # JSON for context modifiers
    bypass_anti_spam = BooleanField(default=False)
    is_enabled = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    device_id = CharField(default='')
    deleted_at = DateTimeField(null=True)
