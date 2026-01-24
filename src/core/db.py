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
    from core.mood.mood import Mood
    from core.mood.mood_log import MoodLog
    from core.reminder.reminder import Reminder
    from core.reminder.reminder_log import ReminderLog
    from core.notes.note import Note
    from core.migrations.runner import run_migrations

    db.connect()
    db.create_tables([Habit, Log, HabitTracker, Mood, MoodLog, Reminder, ReminderLog, Note])

    # Run any pending migrations
    run_migrations()

    # Start WindowMonitor if any habit uses it
    _initialize_window_monitor()

# TODO: Extract to a better place
def _initialize_window_monitor():
    """Start WindowMonitor if any habit has WindowTracker configured."""
    import logging
    from core.habit.habit_tracker import HabitTracker
    from core.tracker.window_monitor import WindowMonitor

    has_window_tracker = HabitTracker.select().where(
        (HabitTracker.tracker == 'window') &
        (HabitTracker.is_enabled == True)
    ).exists()

    if has_window_tracker:
        WindowMonitor.get_instance()
        logging.info("WindowMonitor initialized")


if __name__ == '__main__':
    initialize_database()