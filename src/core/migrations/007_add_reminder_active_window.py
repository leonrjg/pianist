"""
Migration 007: Add active time window to reminders
"""

from core.db import db


def up():
    """Apply the migration"""
    db.execute_sql('ALTER TABLE reminder ADD COLUMN active_start_minute INTEGER DEFAULT 0')
    db.execute_sql('ALTER TABLE reminder ADD COLUMN active_end_minute INTEGER DEFAULT 1440')
    print("Migration 007: Added reminder active window columns")


def down():
    """Rollback the migration"""
    print("Migration 007: No-op (SQLite does not support DROP COLUMN)")


if __name__ == '__main__':
    db.connect()
    up()
