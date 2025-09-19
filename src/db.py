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
    """
    from habit.habit import Habit
    from habit.log import Log
    from habit.habit_tracker import HabitTracker

    db.connect()
    db.create_tables([Habit, Log, HabitTracker])


if __name__ == '__main__':
    initialize_database()