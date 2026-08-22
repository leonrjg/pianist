"""
Migration 025: Remove note column from habit table

The habit.note field was a competing implementation of per-habit notes,
superseded by the Note model (see core/notes/note.py), which every note
editor now reads from and writes to.
"""

from peewee import TextField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.drop_column('habit', 'note')
    )
    print("Migration 025: Removed note column from habit table")


def down():
    migrator = SqliteMigrator(db)
    migrate(
        migrator.add_column('habit', 'note', TextField(null=True))
    )
    print("Migration 025: Re-added note column to habit table")


if __name__ == '__main__':
    db.connect()
    up()
