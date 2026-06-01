"""
Migration 019: Add note titles and ordering.

Supports multiple named notes in the same global or habit scope.
"""

from core.db import db


def _column_exists(table: str, column: str) -> bool:
    rows = db.execute_sql(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def up():
    """Apply the migration."""
    if not _column_exists('note', 'title'):
        db.execute_sql("ALTER TABLE note ADD COLUMN title VARCHAR(255) NOT NULL DEFAULT 'Default note'")

    if not _column_exists('note', 'display_order'):
        db.execute_sql("ALTER TABLE note ADD COLUMN display_order INTEGER NOT NULL DEFAULT 0")

    rows = db.execute_sql("""
        SELECT id, habit_id
        FROM note
        WHERE deleted_at IS NULL
        ORDER BY habit_id IS NOT NULL, habit_id, created_at, id
    """).fetchall()

    counts_by_scope = {}
    for note_id, habit_id in rows:
        scope = habit_id or '__global__'
        index = counts_by_scope.get(scope, 0)
        title = 'Default note' if index == 0 else f'Note {index + 1}'
        db.execute_sql(
            "UPDATE note SET title = ?, display_order = ? WHERE id = ?",
            (title, index, note_id)
        )
        counts_by_scope[scope] = index + 1

    db.execute_sql("CREATE INDEX IF NOT EXISTS note_habit_display_order ON note (habit_id, display_order)")

    print("Migration 019: Added note titles and display order")


def down():
    """SQLite cannot drop columns without rebuilding the table."""
    print("Migration 019: down migration is not supported")


if __name__ == '__main__':
    db.connect()
    up()
