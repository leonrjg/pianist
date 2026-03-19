"""
Migration 012: Update manual_task schema for scheduled tasks

Changes:
- Add scheduled_at column (when the task is scheduled/due)
- Make completed_at nullable (None for incomplete tasks)
- Make habit_id nullable (for standalone custom tasks)
- Update indexes for better query performance
- Migrate existing data (completed_at -> scheduled_at, all marked complete)
"""

from core.db import db


def up():
    """Apply the migration"""

    # Step 1: Add new scheduled_at column (nullable initially)
    db.execute_sql("""
        ALTER TABLE manual_task
        ADD COLUMN scheduled_at TIMESTAMP
    """)

    # Step 2: Copy completed_at to scheduled_at for existing records
    db.execute_sql("""
        UPDATE manual_task
        SET scheduled_at = completed_at
    """)

    # Step 3: Create new table with updated schema
    db.execute_sql("""
        CREATE TABLE manual_task_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            title TEXT,
            scheduled_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habit (id) ON DELETE CASCADE
        )
    """)

    # Step 4: Copy data to new table
    db.execute_sql("""
        INSERT INTO manual_task_new (id, habit_id, title, scheduled_at, completed_at, created_at)
        SELECT id, habit_id, title, scheduled_at, completed_at, created_at
        FROM manual_task
    """)

    # Step 5: Drop old table and rename new table
    db.execute_sql("DROP TABLE manual_task")
    db.execute_sql("ALTER TABLE manual_task_new RENAME TO manual_task")

    # Step 6: Create indexes for better query performance
    db.execute_sql("""
        CREATE INDEX IF NOT EXISTS manual_task_habit_scheduled
        ON manual_task (habit_id, scheduled_at)
    """)

    db.execute_sql("""
        CREATE INDEX IF NOT EXISTS manual_task_scheduled
        ON manual_task (scheduled_at)
    """)

    print("Migration 012: Updated manual_task schema")
    print("  - Added scheduled_at column")
    print("  - Made completed_at nullable")
    print("  - Made habit_id nullable")
    print("  - Updated indexes")


def down():
    """Rollback the migration"""

    # Recreate original schema
    db.execute_sql("""
        CREATE TABLE manual_task_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER NOT NULL,
            title TEXT,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habit (id) ON DELETE CASCADE
        )
    """)

    # Copy data back (only completed tasks with habits)
    db.execute_sql("""
        INSERT INTO manual_task_old (id, habit_id, title, created_at, completed_at)
        SELECT id, habit_id, title, created_at, scheduled_at
        FROM manual_task
        WHERE habit_id IS NOT NULL AND completed_at IS NOT NULL
    """)

    # Replace table
    db.execute_sql("DROP TABLE manual_task")
    db.execute_sql("ALTER TABLE manual_task_old RENAME TO manual_task")

    # Restore old index
    db.execute_sql("""
        CREATE INDEX IF NOT EXISTS manual_task_habit_completed
        ON manual_task (habit_id, completed_at)
    """)

    print("Migration 012: Rolled back manual_task schema")


if __name__ == '__main__':
    db.connect()
    up()
