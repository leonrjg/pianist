import uuid
from datetime import datetime
from typing import Optional


def _parse_dt(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except ValueError:
        return None


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
    }


def serialize_row(instance, table_name: str) -> dict:
    """Serialize a model instance to a JSON-safe dict."""
    row = {}
    for name in instance._meta.fields:
        val = instance.__data__.get(name)
        if isinstance(val, datetime):
            val = val.isoformat()
        elif isinstance(val, uuid.UUID):
            val = str(val)
        row[name] = val
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
    for field_name in model._meta.fields:
        if field_name in incoming:
            setattr(existing, field_name, incoming[field_name])
    existing.save()


def _insert(model, incoming: dict) -> None:
    data = {k: v for k, v in incoming.items() if k in model._meta.fields}
    model.create(**data)
