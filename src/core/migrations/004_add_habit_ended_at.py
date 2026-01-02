"""
Migration 004: Add ended_at field to habit table

This migration adds the ended_at field to track when a habit was ended.
"""

from peewee import DateTimeField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)
    
    # Add ended_at field to habit table
    ended_at_field = DateTimeField(null=True)
    
    migrate(
        migrator.add_column('habit', 'ended_at', ended_at_field)
    )
    
    print("Migration 004: Added ended_at field to habit table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)
    
    migrate(
        migrator.drop_column('habit', 'ended_at')
    )
    
    print("Migration 004: Removed ended_at field from habit table")


if __name__ == '__main__':
    db.connect()
    up()
