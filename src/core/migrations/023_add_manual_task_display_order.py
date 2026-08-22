"""
Migration 023: Add display_order column to manual_task table

Gives standalone manual tasks a position in the unified piano-key ordering, so a
manual task and a habit share one ordering authority and any key can be reordered
above or below any other.
"""

from peewee import IntegerField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.add_column('manual_task', 'display_order', IntegerField(default=0))
    )
    print("Migration 023: Added display_order column to manual_task table")


def down():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.drop_column('manual_task', 'display_order')
    )
    print("Migration 023: Removed display_order column from manual_task table")


if __name__ == '__main__':
    db.connect()
    up()
