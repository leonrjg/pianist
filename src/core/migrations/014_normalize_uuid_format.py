"""
Migration 014: Normalize UUID storage to hex format (no dashes)

Peewee's UUIDField.db_value() converts uuid.UUID objects to .hex (32 chars,
no dashes) when building queries. Migration 013 used str(uuid.uuid4()) which
produces the dashed format ('xxxxxxxx-xxxx-...'), causing all WHERE id = ?
lookups to miss. This migration strips dashes from every UUID column so that
stored values match what Peewee generates in SQL parameters.

Affected columns:
  - id (PK) on every migrated table
  - FK reference columns: habit_id, mood_id, reminder_id
  - syncstate.device_id (FK to device.id)
  - device_id (CharField, for consistency)
"""

from core.db import db

_STRIP = "REPLACE({col}, '-', '')"


def _normalize(table, col):
    db.execute_sql(
        f'UPDATE "{table}" SET "{col}" = REPLACE("{col}", \'-\', \'\')'
        f' WHERE "{col}" IS NOT NULL AND "{col}" LIKE \'%-%\''
    )


def up():
    # PK columns
    for tbl in ('habit', 'mood', 'reminder', 'log', 'habittracker',
                'manual_task', 'mood_log', 'reminder_log', 'note', 'device'):
        _normalize(tbl, 'id')

    # FK reference columns
    for tbl, col in [
        ('log',          'habit_id'),
        ('habittracker', 'habit_id'),
        ('manual_task',  'habit_id'),
        ('reminder',     'habit_id'),
        ('note',         'habit_id'),
        ('mood_log',     'mood_id'),
        ('reminder_log', 'reminder_id'),
        ('syncstate',    'device_id'),
    ]:
        _normalize(tbl, col)

    # device_id (CharField) — normalize for consistency
    for tbl in ('habit', 'log', 'habittracker', 'manual_task',
                'mood', 'mood_log', 'reminder', 'reminder_log', 'note'):
        _normalize(tbl, 'device_id')

    print("Migration 014: Normalized all UUID columns to hex format (no dashes)")
