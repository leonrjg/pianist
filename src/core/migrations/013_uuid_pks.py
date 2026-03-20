"""
Migration 013: Convert all tables to UUID primary keys

Implements distributed data model support:
- UUID TEXT PKs on all tables (replacing auto-increment integers)
- Adds device_id, updated_at (where missing), deleted_at to all tables
- Converts Reminder.habit_id from raw int to proper FK (UUID)
- Removes UNIQUE constraint on Habit.name (identity is now UUID)
- Replaces HabitTracker composite PK with UUID PK
- Creates Device and SyncState tables
- Inserts local device row into Device table

Migration approach per table (SQLite cannot ALTER COLUMN):
  1. Create _new table with UUID PK and new columns
  2. Read all existing rows via Python, generate UUID mappings
  3. Insert rows into _new table with translated PKs/FKs
  4. Drop old table, rename _new to original name

FK references in new table DDL use the final table names (not _new).
SQLite does not enforce FKs by default, so this is safe during migration.
"""

import uuid
import socket
from datetime import datetime
from core.db import db
from core.config import get_device_id


def _fetch(table):
    cursor = db.execute_sql(f'SELECT * FROM "{table}"')
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def up():
    device_id = get_device_id()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # ------------------------------------------------------------------
    # 1. Read all existing data before any schema changes
    # ------------------------------------------------------------------
    habit_rows       = _fetch('habit')
    mood_rows        = _fetch('mood')
    reminder_rows    = _fetch('reminder')
    log_rows         = _fetch('log')
    tracker_rows     = _fetch('habittracker')
    task_rows        = _fetch('manual_task')
    moodlog_rows     = _fetch('mood_log')
    reminderlog_rows = _fetch('reminder_log')
    note_rows        = _fetch('note')

    # ------------------------------------------------------------------
    # 2. Build UUID mappings for tables that are FK targets
    # ------------------------------------------------------------------
    habit_map    = {r['id']: uuid.uuid4().hex for r in habit_rows}
    mood_map     = {r['id']: uuid.uuid4().hex for r in mood_rows}
    reminder_map = {r['id']: uuid.uuid4().hex for r in reminder_rows}

    # ------------------------------------------------------------------
    # 3. Create new tables (FK refs use final names — safe, no enforcement)
    # ------------------------------------------------------------------

    db.execute_sql('DROP TABLE IF EXISTS habit_new')
    db.execute_sql('''
        CREATE TABLE habit_new (
            id                   TEXT NOT NULL PRIMARY KEY,
            name                 VARCHAR(255) NOT NULL,
            schedule             VARCHAR(255) NOT NULL,
            created_at           DATETIME NOT NULL,
            updated_at           DATETIME NOT NULL,
            started_at           DATETIME NOT NULL,
            inactivity_threshold INTEGER NOT NULL DEFAULT 120,
            allocated_time       INTEGER,
            archived             INTEGER NOT NULL DEFAULT 0,
            display_order        INTEGER DEFAULT 0,
            visible              INTEGER DEFAULT 1,
            ended_at             DATETIME,
            note                 TEXT,
            schedule_step        INTEGER DEFAULT 1,
            device_id            TEXT NOT NULL DEFAULT '',
            deleted_at           DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS mood_new')
    db.execute_sql('''
        CREATE TABLE mood_new (
            id            TEXT NOT NULL PRIMARY KEY,
            symbol        VARCHAR(255) NOT NULL,
            description   VARCHAR(255) NOT NULL,
            display_order INTEGER DEFAULT 0,
            device_id     TEXT NOT NULL DEFAULT '',
            updated_at    DATETIME NOT NULL,
            deleted_at    DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS reminder_new')
    db.execute_sql('''
        CREATE TABLE reminder_new (
            id                   TEXT NOT NULL PRIMARY KEY,
            name                 VARCHAR(255) NOT NULL,
            reminder_type        VARCHAR(50) NOT NULL,
            habit_id             TEXT REFERENCES habit (id) ON DELETE SET NULL,
            action_type          VARCHAR(50) NOT NULL,
            action_payload       TEXT NOT NULL,
            notification_method  VARCHAR(50) DEFAULT 'desktop',
            ease_factor          REAL DEFAULT 2.5,
            interval_days        INTEGER DEFAULT 1,
            target_rate_per_week REAL,
            weight               REAL DEFAULT 1.0,
            last_fired_at        DATETIME,
            next_fire_at         DATETIME,
            context_config       TEXT DEFAULT '{}',
            is_enabled           INTEGER DEFAULT 1,
            created_at           DATETIME NOT NULL,
            updated_at           DATETIME NOT NULL,
            active_start_minute  INTEGER DEFAULT 0,
            active_end_minute    INTEGER DEFAULT 1440,
            device_id            TEXT NOT NULL DEFAULT '',
            deleted_at           DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS log_new')
    db.execute_sql('''
        CREATE TABLE log_new (
            id         TEXT NOT NULL PRIMARY KEY,
            habit_id   TEXT NOT NULL REFERENCES habit (id) ON DELETE CASCADE,
            start      DATETIME NOT NULL,
            end        DATETIME,
            started_by VARCHAR(255),
            ended_by   VARCHAR(255),
            idle_time  INTEGER NOT NULL DEFAULT 0,
            "offset"   INTEGER DEFAULT 0,
            device_id  TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS habittracker_new')
    db.execute_sql('''
        CREATE TABLE habittracker_new (
            id         TEXT NOT NULL PRIMARY KEY,
            habit_id   TEXT NOT NULL REFERENCES habit (id) ON DELETE CASCADE,
            tracker    VARCHAR(255) NOT NULL,
            config     TEXT,
            is_enabled INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            device_id  TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS manual_task_new')
    db.execute_sql('''
        CREATE TABLE manual_task_new (
            id           TEXT NOT NULL PRIMARY KEY,
            habit_id     TEXT REFERENCES habit (id) ON DELETE CASCADE,
            title        TEXT,
            scheduled_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            created_at   TIMESTAMP NOT NULL,
            device_id    TEXT NOT NULL DEFAULT '',
            updated_at   DATETIME NOT NULL,
            deleted_at   DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS mood_log_new')
    db.execute_sql('''
        CREATE TABLE mood_log_new (
            id         TEXT NOT NULL PRIMARY KEY,
            mood_id    TEXT NOT NULL REFERENCES mood (id) ON DELETE CASCADE,
            start      DATETIME NOT NULL,
            end        DATETIME,
            ended_by   VARCHAR(255),
            device_id  TEXT NOT NULL DEFAULT '',
            updated_at DATETIME NOT NULL,
            deleted_at DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS reminder_log_new')
    db.execute_sql('''
        CREATE TABLE reminder_log_new (
            id                TEXT NOT NULL PRIMARY KEY,
            reminder_id       TEXT NOT NULL REFERENCES reminder (id) ON DELETE CASCADE,
            fired_at          DATETIME NOT NULL,
            action_executed   VARCHAR(255) NOT NULL,
            notification_sent INTEGER DEFAULT 0,
            feedback_rating   INTEGER,
            context_modifier  REAL DEFAULT 1.0,
            was_overdue       INTEGER DEFAULT 0,
            device_id         TEXT NOT NULL DEFAULT '',
            updated_at        DATETIME NOT NULL,
            deleted_at        DATETIME
        )
    ''')

    db.execute_sql('DROP TABLE IF EXISTS note_new')
    db.execute_sql('''
        CREATE TABLE note_new (
            id         TEXT NOT NULL PRIMARY KEY,
            habit_id   TEXT REFERENCES habit (id) ON DELETE CASCADE,
            content    TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            device_id  TEXT NOT NULL DEFAULT '',
            deleted_at DATETIME
        )
    ''')

    # ------------------------------------------------------------------
    # 4. Migrate data into new tables
    # ------------------------------------------------------------------

    # habit — already has updated_at; populate device_id, deleted_at
    for r in habit_rows:
        db.execute_sql(
            '''INSERT INTO habit_new
               (id, name, schedule, created_at, updated_at, started_at,
                inactivity_threshold, allocated_time, archived, display_order,
                visible, ended_at, note, schedule_step, device_id, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (habit_map[r['id']], r['name'], r['schedule'], r['created_at'],
             r['updated_at'], r['started_at'], r['inactivity_threshold'],
             r['allocated_time'], r['archived'], r['display_order'], r['visible'],
             r['ended_at'], r['note'], r['schedule_step'], device_id, None)
        )

    # mood — no timestamps; updated_at = now
    for r in mood_rows:
        db.execute_sql(
            '''INSERT INTO mood_new
               (id, symbol, description, display_order, device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (mood_map[r['id']], r['symbol'], r['description'], r['display_order'],
             device_id, now, None)
        )

    # reminder — already has updated_at; habit_id int → UUID
    for r in reminder_rows:
        new_habit_id = habit_map.get(r['habit_id']) if r['habit_id'] is not None else None
        db.execute_sql(
            '''INSERT INTO reminder_new
               (id, name, reminder_type, habit_id, action_type, action_payload,
                notification_method, ease_factor, interval_days, target_rate_per_week,
                weight, last_fired_at, next_fire_at, context_config, is_enabled,
                created_at, updated_at, active_start_minute, active_end_minute,
                device_id, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (reminder_map[r['id']], r['name'], r['reminder_type'], new_habit_id,
             r['action_type'], r['action_payload'], r['notification_method'],
             r['ease_factor'], r['interval_days'], r['target_rate_per_week'],
             r['weight'], r['last_fired_at'], r['next_fire_at'], r['context_config'],
             r['is_enabled'], r['created_at'], r['updated_at'],
             r['active_start_minute'], r['active_end_minute'], device_id, None)
        )

    # log — no timestamps; updated_at = now; skip orphaned rows (dangling habit_id)
    skipped_log = 0
    for r in log_rows:
        new_habit_id = habit_map.get(r['habit_id'])
        if new_habit_id is None:
            skipped_log += 1
            continue
        db.execute_sql(
            '''INSERT INTO log_new
               (id, habit_id, start, end, started_by, ended_by, idle_time,
                "offset", device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_habit_id, r['start'], r['end'],
             r['started_by'], r['ended_by'], r['idle_time'], r['offset'],
             device_id, now, None)
        )
    if skipped_log:
        print(f"  Warning: skipped {skipped_log} log row(s) with no matching habit")

    # habittracker — composite PK → UUID PK; updated_at = created_at; skip orphans
    skipped_tracker = 0
    for r in tracker_rows:
        new_habit_id = habit_map.get(r['habit_id'])
        if new_habit_id is None:
            skipped_tracker += 1
            continue
        db.execute_sql(
            '''INSERT INTO habittracker_new
               (id, habit_id, tracker, config, is_enabled, created_at,
                device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_habit_id, r['tracker'], r['config'],
             r['is_enabled'], r['created_at'], device_id, r['created_at'], None)
        )
    if skipped_tracker:
        print(f"  Warning: skipped {skipped_tracker} habittracker row(s) with no matching habit")

    # manual_task — has created_at; updated_at = created_at
    for r in task_rows:
        new_habit_id = habit_map.get(r['habit_id']) if r['habit_id'] is not None else None
        db.execute_sql(
            '''INSERT INTO manual_task_new
               (id, habit_id, title, scheduled_at, completed_at, created_at,
                device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_habit_id, r['title'], r['scheduled_at'],
             r['completed_at'], r['created_at'], device_id, r['created_at'], None)
        )

    # mood_log — no timestamps; updated_at = now; skip orphans
    skipped_moodlog = 0
    for r in moodlog_rows:
        new_mood_id = mood_map.get(r['mood_id'])
        if new_mood_id is None:
            skipped_moodlog += 1
            continue
        db.execute_sql(
            '''INSERT INTO mood_log_new
               (id, mood_id, start, end, ended_by, device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_mood_id, r['start'], r['end'],
             r['ended_by'], device_id, now, None)
        )
    if skipped_moodlog:
        print(f"  Warning: skipped {skipped_moodlog} mood_log row(s) with no matching mood")

    # reminder_log — updated_at = fired_at; skip orphans
    skipped_reminderlog = 0
    for r in reminderlog_rows:
        new_reminder_id = reminder_map.get(r['reminder_id'])
        if new_reminder_id is None:
            skipped_reminderlog += 1
            continue
        db.execute_sql(
            '''INSERT INTO reminder_log_new
               (id, reminder_id, fired_at, action_executed, notification_sent,
                feedback_rating, context_modifier, was_overdue,
                device_id, updated_at, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_reminder_id, r['fired_at'],
             r['action_executed'], r['notification_sent'], r['feedback_rating'],
             r['context_modifier'], r['was_overdue'], device_id, r['fired_at'], None)
        )
    if skipped_reminderlog:
        print(f"  Warning: skipped {skipped_reminderlog} reminder_log row(s) with no matching reminder")

    # note — already has updated_at
    for r in note_rows:
        new_habit_id = habit_map.get(r['habit_id']) if r['habit_id'] is not None else None
        db.execute_sql(
            '''INSERT INTO note_new
               (id, habit_id, content, created_at, updated_at, device_id, deleted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (uuid.uuid4().hex, new_habit_id, r['content'], r['created_at'],
             r['updated_at'], device_id, None)
        )

    # ------------------------------------------------------------------
    # 5. Drop old tables (children first) and rename new tables
    # ------------------------------------------------------------------
    for tbl in ('reminder_log', 'mood_log', 'note', 'manual_task',
                'habittracker', 'log', 'reminder', 'mood', 'habit'):
        db.execute_sql(f'DROP TABLE "{tbl}"')
    for tbl in ('reminder_log', 'mood_log', 'note', 'manual_task',
                'habittracker', 'log', 'reminder', 'mood', 'habit'):
        db.execute_sql(f'ALTER TABLE {tbl}_new RENAME TO "{tbl}"')

    # ------------------------------------------------------------------
    # 6. Recreate indexes
    # ------------------------------------------------------------------
    db.execute_sql('CREATE INDEX IF NOT EXISTS habit_schedule ON habit (schedule)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS log_start ON log (start)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS log_end ON log ("end")')
    db.execute_sql('CREATE INDEX IF NOT EXISTS mood_log_start ON mood_log (start)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS mood_log_end ON mood_log ("end")')
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_log_fired_at ON reminder_log (fired_at)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_next_fire_at ON reminder (next_fire_at)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_is_enabled ON reminder (is_enabled)')
    db.execute_sql('CREATE UNIQUE INDEX habittracker_habit_tracker ON habittracker (habit_id, tracker)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS manual_task_habit_scheduled ON manual_task (habit_id, scheduled_at)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS manual_task_scheduled ON manual_task (scheduled_at)')

    # ------------------------------------------------------------------
    # 7. Create Device and SyncState tables; insert local device
    # ------------------------------------------------------------------
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS device (
            id         TEXT NOT NULL PRIMARY KEY,
            name       VARCHAR(255) NOT NULL,
            is_self    INTEGER NOT NULL DEFAULT 0,
            last_seen  DATETIME,
            created_at DATETIME NOT NULL
        )
    ''')

    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS syncstate (
            device_id    TEXT NOT NULL PRIMARY KEY,
            last_sync_at DATETIME NOT NULL
        )
    ''')

    hostname = socket.gethostname()
    db.execute_sql(
        'INSERT INTO device (id, name, is_self, last_seen, created_at) VALUES (?, ?, ?, ?, ?)',
        (device_id, hostname, 1, None, now)
    )

    print("Migration 013: Converted all tables to UUID primary keys")
    print(f"  habits={len(habit_rows)}, logs={len(log_rows)}, "
          f"trackers={len(tracker_rows)}, tasks={len(task_rows)}")
    print(f"  moods={len(mood_rows)}, mood_logs={len(moodlog_rows)}")
    print(f"  reminders={len(reminder_rows)}, reminder_logs={len(reminderlog_rows)}")
    print(f"  notes={len(note_rows)}")
    print(f"  Local device: {hostname} ({device_id})")
