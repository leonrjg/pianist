"""
Migration 005: Add note field to habit table

This migration adds the note field to store Markdown notes for habits.
"""

from peewee import TextField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)
    
    # Add note field to habit table
    note_field = TextField(null=True)
    
    migrate(
        migrator.add_column('habit', 'note', note_field)
    )
    
    print("Migration 005: Added note field to habit table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)
    
    migrate(
        migrator.drop_column('habit', 'note')
    )
    
    print("Migration 005: Removed note field from habit table")


if __name__ == '__main__':
    db.connect()
    up()
