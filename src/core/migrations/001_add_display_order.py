"""
Migration 001: Add display_order column to habit table

This migration adds a display_order column to allow custom ordering of habits.
"""

from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.add_column('habit', 'display_order', IntegerField(default=0))
    )
    print("Migration 001: Added display_order column to habit table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column('habit', 'display_order')
    )
    print("Migration 001: Removed display_order column from habit table")


if __name__ == '__main__':
    db.connect()
    up()
