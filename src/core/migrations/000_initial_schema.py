"""
Migration 000: Create initial schema

Creates the three base tables (habit, log, habittracker) as they existed
before migration 001. Subsequent migrations apply incremental changes on top.

Uses CREATE TABLE IF NOT EXISTS so this is safe to run against an existing
database — it becomes a no-op and the migration is simply recorded as applied.
"""

from core.db import db


def up():
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS "habit" (
            "id"                    INTEGER NOT NULL PRIMARY KEY,
            "name"                  VARCHAR(255) NOT NULL UNIQUE,
            "schedule"              VARCHAR(255) NOT NULL,
            "created_at"            DATETIME NOT NULL,
            "updated_at"            DATETIME NOT NULL,
            "started_at"            DATETIME NOT NULL,
            "inactivity_threshold"  INTEGER NOT NULL DEFAULT 120,
            "allocated_time"        INTEGER,
            "archived"              INTEGER NOT NULL DEFAULT 0
        )
    ''')
    db.execute_sql('CREATE INDEX IF NOT EXISTS "habit_schedule" ON "habit" ("schedule")')

    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS "log" (
            "id"            INTEGER NOT NULL PRIMARY KEY,
            "habit_id"      INTEGER NOT NULL REFERENCES "habit" ("id") ON DELETE CASCADE,
            "start"         DATETIME NOT NULL,
            "end"           DATETIME,
            "started_by"    VARCHAR(255),
            "ended_by"      VARCHAR(255),
            "idle_time"     INTEGER NOT NULL DEFAULT 0
        )
    ''')
    db.execute_sql('CREATE INDEX IF NOT EXISTS "log_start" ON "log" ("start")')
    db.execute_sql('CREATE INDEX IF NOT EXISTS "log_end" ON "log" ("end")')

    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS "habittracker" (
            "habit_id"      INTEGER NOT NULL REFERENCES "habit" ("id") ON DELETE CASCADE,
            "tracker"       VARCHAR(255) NOT NULL,
            "config"        TEXT,
            "is_enabled"    INTEGER NOT NULL DEFAULT 1,
            "created_at"    DATETIME NOT NULL,
            PRIMARY KEY ("habit_id", "tracker")
        )
    ''')

    print("Migration 000: Created initial schema")


def down():
    db.execute_sql('DROP TABLE IF EXISTS "habittracker"')
    db.execute_sql('DROP TABLE IF EXISTS "log"')
    db.execute_sql('DROP TABLE IF EXISTS "habit"')
    print("Migration 000: Dropped initial schema")
