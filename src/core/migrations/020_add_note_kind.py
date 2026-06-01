"""
Migration 020: Add kind column to note table.

Differentiates regular notes (kind='note') from quick thoughts (kind='thought').
Existing rows default to 'note'.
"""

from core.db import db


def _column_exists(table: str, column: str) -> bool:
    rows = db.execute_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def up():
    """Apply the migration."""
    if not _column_exists('note', 'kind'):
        db.execute_sql("ALTER TABLE note ADD COLUMN kind VARCHAR(32) NOT NULL DEFAULT 'note'")
        db.execute_sql("CREATE INDEX IF NOT EXISTS note_kind ON note (kind)")

    print("Migration 020: Added note kind column")


def down():
    """SQLite cannot drop columns without rebuilding the table."""
    print("Migration 020: down migration is not supported")


if __name__ == '__main__':
    db.connect()
    up()
