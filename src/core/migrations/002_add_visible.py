"""
Migration 002: Add visible column to habit table

This migration adds a visible column to control whether habits appear as piano keys.
"""

from peewee import BooleanField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.add_column('habit', 'visible', BooleanField(default=True))
    )
    print("Migration 002: Added visible column to habit table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column('habit', 'visible')
    )
    print("Migration 002: Removed visible column from habit table")


if __name__ == '__main__':
    db.connect()
    up()
