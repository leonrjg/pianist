"""
Migration 018: Add fixed-time reminder fields

Adds support for fixed-time reminders linked either to recurring habits or
standalone manual tasks.
"""

from core.db import db


def up():
    """Apply the migration."""
    db.execute_sql("ALTER TABLE reminder ADD COLUMN fixed_time_minute INTEGER")
    db.execute_sql("ALTER TABLE reminder ADD COLUMN manual_task_id TEXT REFERENCES manual_task (id) ON DELETE SET NULL")
    db.execute_sql("CREATE INDEX IF NOT EXISTS reminder_manual_task_id ON reminder (manual_task_id)")
    print("Migration 018: Added fixed-time reminder fields")


def down():
    """SQLite cannot drop columns without rebuilding the table."""
    print("Migration 018: down migration is not supported")


if __name__ == '__main__':
    db.connect()
    up()
