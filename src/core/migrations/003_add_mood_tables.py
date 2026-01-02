"""
Migration 003: Add mood and mood_log tables

This migration adds mood tracking functionality with default mood types.
"""

from peewee import CharField, IntegerField, DateTimeField, ForeignKeyField
from playhouse.migrate import SqliteMigrator, migrate
from core.db import db


def up():
    """Apply the migration"""
    # Create mood table
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS mood (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol VARCHAR(255) NOT NULL,
            description VARCHAR(255) NOT NULL,
            display_order INTEGER DEFAULT 0
        )
    ''')
    
    # Create mood_log table
    db.execute_sql('''
        CREATE TABLE IF NOT EXISTS mood_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mood_id INTEGER NOT NULL,
            start DATETIME NOT NULL,
            end DATETIME,
            ended_by VARCHAR(255),
            FOREIGN KEY (mood_id) REFERENCES mood(id) ON DELETE CASCADE
        )
    ''')
    
    # Create indexes
    db.execute_sql('CREATE INDEX IF NOT EXISTS mood_log_start ON mood_log(start)')
    db.execute_sql('CREATE INDEX IF NOT EXISTS mood_log_end ON mood_log(end)')
    
    # Insert default moods
    default_moods = [
        ('🟣', 'Wired', 0),
        ('🟢', 'Stable', 1),
        ('🟡', 'High maintenance', 2),
        ('🗿', 'Procrastination', 3),
        ('🟧', 'Unable to sustain mental effort', 4),
        ('🟥', 'Unable to sustain mental or physical effort', 5),
    ]
    
    for symbol, description, order in default_moods:
        db.execute_sql(
            'INSERT INTO mood (symbol, description, display_order) VALUES (?, ?, ?)',
            (symbol, description, order)
        )
    
    print("Migration 003: Added mood and mood_log tables with default moods")


def down():
    """Rollback the migration"""
    db.execute_sql('DROP TABLE IF EXISTS mood_log')
    db.execute_sql('DROP TABLE IF EXISTS mood')
    print("Migration 003: Removed mood and mood_log tables")


if __name__ == '__main__':
    db.connect()
    up()
