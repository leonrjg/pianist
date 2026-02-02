"""
Migration 009: Add schedule_step field to habit table

This migration adds the schedule_step field to support "every N intervals" scheduling
(e.g., every 3 days, every 2 weeks) for regular schedules.
"""

from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    migrator = SqliteMigrator(db)

    # Add schedule_step field to habit table
    schedule_step_field = IntegerField(default=1)

    migrate(
        migrator.add_column('habit', 'schedule_step', schedule_step_field)
    )

    print("Migration 009: Added schedule_step field to habit table")


def down():
    """Rollback the migration"""
    migrator = SqliteMigrator(db)

    migrate(
        migrator.drop_column('habit', 'schedule_step')
    )

    print("Migration 009: Removed schedule_step field from habit table")


if __name__ == '__main__':
    db.connect()
    up()
