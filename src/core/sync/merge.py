import uuid
from datetime import date, datetime
from typing import Optional

from peewee import DateField, DateTimeField, ForeignKeyField, UUIDField


def _parse_dt(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except ValueError:
        return None


def to_wire(field, val):
    """Convert a Python field value to a JSON-safe wire representation."""
    if val is None:
        return None
    if isinstance(field, DateTimeField):
        if isinstance(val, datetime):
            return val.isoformat()
        if isinstance(val, date):
            return datetime(val.year, val.month, val.day).isoformat()
        return val
    if isinstance(field, DateField):
        if isinstance(val, datetime):
            return val.date().isoformat()
        if isinstance(val, date):
            return val.isoformat()
        return val
    if isinstance(field, UUIDField):
        return str(val)
    if isinstance(field, ForeignKeyField):
        if isinstance(val, uuid.UUID):
            return str(val)
        return val
    return val  # bool, int, float, str — JSON handles these natively


def from_wire(field, val):
    """Convert a JSON wire value back to the Python type Peewee expects."""
    if val is None:
        return None
    if isinstance(field, DateTimeField):
        if isinstance(val, str):
            return datetime.fromisoformat(val)
        return val
    if isinstance(field, DateField):
        if isinstance(val, str):
            return date.fromisoformat(val[:10])
        return val
    if isinstance(field, UUIDField):
        if isinstance(val, str):
            return uuid.UUID(val)
        return val
    if isinstance(field, ForeignKeyField):
        return from_wire(field.rel_field, val)
    return val  # bool, int, float, str — already correct from JSON


def get_model_registry() -> dict:
    from core.habit.habit import Habit
    from core.habit.log import Log
    from core.habit.habit_tracker import HabitTracker
    from core.habit.manual_task import ManualTask
    from core.mood.mood import Mood
    from core.mood.mood_log import MoodLog
    from core.reminder.reminder import Reminder
    from core.reminder.reminder_log import ReminderLog
    from core.notes.note import Note
    from core.settings.setting import AppSetting
    from core.ical.source import ICalSource
    return {
        'habit': Habit,
        'log': Log,
        'habittracker': HabitTracker,
        'manual_task': ManualTask,
        'mood': Mood,
        'mood_log': MoodLog,
        'reminder': Reminder,
        'reminder_log': ReminderLog,
        'note': Note,
        'appsetting': AppSetting,
        'ical_source': ICalSource,
    }


def serialize_row(instance, table_name: str) -> dict:
    """Serialize a model instance to a JSON-safe dict using ISO 8601 for dates."""
    row = {}
    for name, field in instance._meta.fields.items():
        row[name] = to_wire(field, instance.__data__.get(name))
    return {'table': table_name, 'data': row}


def merge_record(table: str, incoming: dict) -> None:
    """Apply Last-Write-Wins merge for a single incoming record."""
    registry = get_model_registry()
    if table not in registry:
        return
    model = registry[table]
    record_id = incoming['id']
    inc_updated = _parse_dt(incoming.get('updated_at'))

    try:
        existing = model.get_by_id(record_id)
        ex_updated = _parse_dt(existing.updated_at)

        wins = False
        if inc_updated and ex_updated:
            if inc_updated > ex_updated:
                wins = True
            elif inc_updated == ex_updated:
                wins = str(incoming.get('device_id', '')) > str(existing.device_id)
        elif inc_updated:
            wins = True

        if wins:
            _update(model, existing, incoming)
    except model.DoesNotExist:
        _insert(model, incoming)


def _update(model, existing, incoming: dict) -> None:
    for field_name, field in model._meta.fields.items():
        if field_name in incoming:
            setattr(existing, field_name, from_wire(field, incoming[field_name]))
    existing.save()


def live_push_instance(instance, table_name: str) -> None:
    """Serialize a model instance and fire-and-forget push it to all active peers."""
    record = serialize_row(instance, table_name)
    from core.sync.service import SyncService
    SyncService.get_instance().client.live_push(record)


def _insert(model, incoming: dict) -> None:
    data = {
        field_name: from_wire(field, incoming[field_name])
        for field_name, field in model._meta.fields.items()
        if field_name in incoming
    }
    # on_conflict_replace handles the case where the remote UUID is new but a
    # unique-together constraint (e.g. HabitTracker.habit+tracker) already exists
    # locally under a different UUID assigned before first sync.
    model.insert(**data).on_conflict_replace().execute()
