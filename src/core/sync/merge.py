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
    """Serialize a model instance to a JSON-safe dict using Peewee's own DB encoding."""
    row = {}
    for name, field in instance._meta.fields.items():
        val = field.db_value(instance.__data__.get(name))
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


def _coerce(field, value):
    """Convert a DB-encoded value back to the Python type Peewee expects."""
    if value is None:
        return None
    return field.python_value(value)


def _update(model, existing, incoming: dict) -> None:
    for field_name, field in model._meta.fields.items():
        if field_name in incoming:
            setattr(existing, field_name, _coerce(field, incoming[field_name]))
    existing.save()


def _insert(model, incoming: dict) -> None:
    data = {
        field_name: _coerce(field, incoming[field_name])
        for field_name, field in model._meta.fields.items()
        if field_name in incoming
    }
    # on_conflict_replace handles the case where the remote UUID is new but a
    # unique-together constraint (e.g. HabitTracker.habit+tracker) already exists
    # locally under a different UUID assigned before first sync.
    model.insert(**data).on_conflict_replace().execute()
