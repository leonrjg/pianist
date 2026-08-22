"""
Migration 024: Add snooze_until column to reminder table

Holds a user-initiated deferral floor. next_fire_at remains schedule-owned;
snooze_until is owned by the user's snooze action. A reminder fires only when
now >= next_fire_at AND (snooze_until is null OR now >= snooze_until).
"""

from peewee import DateTimeField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.add_column('reminder', 'snooze_until', DateTimeField(null=True))
    )
    print("Migration 024: Added snooze_until column to reminder table")


def down():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.drop_column('reminder', 'snooze_until')
    )
    print("Migration 024: Removed snooze_until column from reminder table")


if __name__ == '__main__':
    db.connect()
    up()
