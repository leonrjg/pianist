"""
Migration 017: Simplify mood_log to beacon model

Removes the session-based `end` and `ended_by` columns from mood_log.
Moods are now point-in-time beacons, not time ranges.
"""

from core.db import db


def up():
    rows = db.execute_sql('SELECT id, mood_id, start, device_id, updated_at, deleted_at FROM mood_log').fetchall()

    db.execute_sql('DROP TABLE IF EXISTS mood_log_new')
    db.execute_sql('''
        CREATE TABLE mood_log_new (
            id         TEXT NOT NULL PRIMARY KEY,
            mood_id    TEXT NOT NULL REFERENCES mood (id) ON DELETE CASCADE,
            start      DATETIME NOT NULL,
            device_id  TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME
        )
    ''')

    for row in rows:
        db.execute_sql(
            'INSERT INTO mood_log_new (id, mood_id, start, device_id, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?)',
            row
        )

    db.execute_sql('DROP TABLE mood_log')
    db.execute_sql('ALTER TABLE mood_log_new RENAME TO mood_log')
    db.execute_sql('CREATE INDEX IF NOT EXISTS mood_log_start ON mood_log (start)')

    print(f"Migration 017: Converted mood_log to beacon model ({len(rows)} rows migrated)")
