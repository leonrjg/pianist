from core.db import db


def up():
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS "ical_source" (
            "id"         TEXT NOT NULL PRIMARY KEY,
            "name"       VARCHAR(255) NOT NULL,
            "path"       VARCHAR(255) NOT NULL,
            "color"      VARCHAR(50) NOT NULL DEFAULT 'rgb(180, 100, 120)',
            "enabled"    INTEGER NOT NULL DEFAULT 1,
            "created_at" DATETIME NOT NULL,
            "updated_at" DATETIME NOT NULL,
            "device_id"  VARCHAR(255) NOT NULL DEFAULT '',
            "deleted_at" DATETIME
        )
    ''')
    print("Migration 016: Created ical_source table")


def down():
    db.execute_sql('DROP TABLE IF EXISTS "ical_source"')
    print("Migration 016: Dropped ical_source table")
