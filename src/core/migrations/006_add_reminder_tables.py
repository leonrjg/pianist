"""
Migration 006: Add reminder and reminder_log tables

This migration adds reminder system with SR and stochastic scheduling.
"""

from core.db import db


def up():
    """Apply the migration"""
    # Create reminder table
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS reminder (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            reminder_type VARCHAR(50) NOT NULL,
            habit_id INTEGER,
            action_type VARCHAR(50) NOT NULL,
            action_payload TEXT NOT NULL,
            notification_method VARCHAR(50) DEFAULT 'desktop',
            ease_factor REAL DEFAULT 2.5,
            interval_days INTEGER DEFAULT 1,
            target_rate_per_week REAL,
            weight REAL DEFAULT 1.0,
            last_fired_at DATETIME,
            next_fire_at DATETIME,
            context_config TEXT DEFAULT '{}',
            is_enabled INTEGER DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (habit_id) REFERENCES habit(id) ON DELETE SET NULL
        )
    ''')

    # Create reminder_log table
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS reminder_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reminder_id INTEGER NOT NULL,
            fired_at DATETIME NOT NULL,
            action_executed VARCHAR(255) NOT NULL,
            notification_sent INTEGER DEFAULT 0,
            feedback_rating INTEGER,
            context_modifier REAL DEFAULT 1.0,
            was_overdue INTEGER DEFAULT 0,
            FOREIGN KEY (reminder_id) REFERENCES reminder(id) ON DELETE CASCADE
        )
    ''')

    # Create indexes
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_log_fired_at ON reminder_log(fired_at)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_next_fire_at ON reminder(next_fire_at)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS reminder_is_enabled ON reminder(is_enabled)')

    print("Migration 006: Added reminder and reminder_log tables")


def down():
    """Rollback the migration"""
    db.execute_sql('DROP TABLE IF EXISTS reminder_log')
    db.execute_sql('DROP TABLE IF EXISTS reminder')
    print("Migration 006: Removed reminder and reminder_log tables")


if __name__ == '__main__':
    db.connect()
    up()
