"""
Migration 008: Add notes table

This migration creates the notes table for storing user notes.
Notes can be global (habit_id=null) or associated with specific habits.
"""

from peewee import *
from core.db import db


def up():
    """Apply the migration"""
    # Create notes table
    db.execute_sql("""
        CREATE TABLE IF NOT EXISTS note (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            content TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (habit_id) REFERENCES habit(id) ON DELETE CASCADE
        )
    """)
    
    print("Migration 008: Created notes table")


def down():
    """Rollback the migration"""
    db.execute_sql("DROP TABLE IF EXISTS note")
    print("Migration 008: Dropped notes table")


if __name__ == '__main__':
    db.connect()
    up()
