from pathlib import Path
from peewee import *

_db_path = Path.home() / '.pianist' / 'habits.db'
_db_path.parent.mkdir(parents=True, exist_ok=True)

db = SqliteDatabase(str(_db_path), pragmas={'journal_mode': 'WAL'})

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
    Initialize the SQLite database.

    Connects to the database and runs all pending migrations.
    Migrations own the schema entirely: table creation, column additions,
    and seed data are all handled by migration files in core/migrations/.
    """
    from core.migrations.runner import run_migrations

    db.connect()
    run_migrations()

    from core.sync.service import SyncService
    SyncService.get_instance().start()

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
        (HabitTracker.is_enabled == True) &
        HabitTracker.deleted_at.is_null()
    ).exists()

    if has_window_tracker:
        WindowMonitor.get_instance()
        logging.info("WindowMonitor initialized")


if __name__ == '__main__':
    initialize_database()