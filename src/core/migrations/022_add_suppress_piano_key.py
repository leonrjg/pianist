"""
Migration 022: Add suppress_piano_key column to habit table

Allows habits to opt out of appearing as piano keys even when they have a task due today.
"""

from peewee import BooleanField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.add_column('habit', 'suppress_piano_key', BooleanField(default=False))
    )
    print("Migration 022: Added suppress_piano_key column to habit table")


def down():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.drop_column('habit', 'suppress_piano_key')
    )
    print("Migration 022: Removed suppress_piano_key column from habit table")


if __name__ == '__main__':
    db.connect()
    up()
