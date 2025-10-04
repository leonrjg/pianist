from peewee import *

db = SqliteDatabase('habits.db')

class BaseModel(Model):
    """
    Base model class for all database entities.

    Provides common database configuration for all Peewee models
    used in the habit tracking application.
    """
    class Meta:
        database = db

def initialize_database():
    """
    Initialize the SQLite database with all required tables.

    Create the database schema for habits, logs, and a junction table for habit trackers.
    Also runs any pending migrations for schema changes.
    """
    from core.habit.habit import Habit
    from core.habit.log import Log
    from core.habit.habit_tracker import HabitTracker
    from core.migrations.runner import run_migrations

    db.connect()
    db.create_tables([Habit, Log, HabitTracker])

    # Run any pending migrations
    run_migrations()


if __name__ == '__main__':
    initialize_database()