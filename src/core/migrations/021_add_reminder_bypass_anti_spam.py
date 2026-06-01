"""
Migration 021: Add bypass_anti_spam column to reminder table.

When true, the reminder skips the anti-spam gap check in ReminderManager.
Fixed-time reminders are always exempted in code; this flag covers stochastic ones.
"""

from core.db import db


def _column_exists(table: str, column: str) -> bool:
    rows = db.execute_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def up():
    if not _column_exists('reminder', 'bypass_anti_spam'):
        db.execute_sql(
            "ALTER TABLE reminder ADD COLUMN bypass_anti_spam INTEGER NOT NULL DEFAULT 0"
        )
    print("Migration 021: Added reminder.bypass_anti_spam")


def down():
    print("Migration 021: down not supported (SQLite cannot drop columns)")


if __name__ == '__main__':
    db.connect()
    up()
