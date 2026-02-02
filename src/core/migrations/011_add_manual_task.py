"""
Migration 011: Add manual_task table

This migration adds a manual_task table to support manually marking scheduled tasks as complete.
"""

from core.db import db


def up():
    """Apply the migration"""
    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS manual_task (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            title TEXT,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habit (id) ON DELETE CASCADE
        )
    """)

    # Index for faster lookups
    db.execute_sql("""
        CREATE INDEX IF NOT EXISTS manual_task_habit_completed
        ON manual_task (habit_id, completed_at)
    """)

    print("Migration 011: Added manual_task table")


def down():
    """Rollback the migration"""
    db.execute_sql("DROP INDEX IF EXISTS manual_task_habit_completed")
    db.execute_sql("DROP TABLE IF EXISTS manual_task")
    print("Migration 011: Removed manual_task table")


if __name__ == '__main__':
    db.connect()
    up()
