from core.db import db


def up():
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS "appsetting" (
            "id"         TEXT NOT NULL PRIMARY KEY,
            "key"        VARCHAR(255) NOT NULL UNIQUE,
            "value"      TEXT NOT NULL,
            "created_at" DATETIME NOT NULL,
            "updated_at" DATETIME NOT NULL,
            "device_id"  VARCHAR(255) NOT NULL DEFAULT '',
            "deleted_at" DATETIME
        )
    ''')
    print("Migration 015: Created appsetting table")


def down():
    db.execute_sql('DROP TABLE IF EXISTS "appsetting"')
    print("Migration 015: Dropped appsetting table")
