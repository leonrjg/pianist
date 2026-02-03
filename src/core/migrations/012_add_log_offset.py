"""
Migration 012: Add offset field to log table

This migration adds the offset field to support manual time adjustments
for session durations (e.g., adding/subtracting time via +/- buttons).
"""

from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)

    # Add offset field to log table
    offset_field = IntegerField(default=0)

    migrate(
        migrator.add_column('log', 'offset', offset_field)
    )

    print("Migration 012: Added offset field to log table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column('log', 'offset')
    )

    print("Migration 012: Removed offset field from log table")


if __name__ == '__main__':
    db.connect()
    up()
