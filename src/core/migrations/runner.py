"""
Migration runner for database schema changes.

Tracks which migrations have been applied and runs pending migrations.
"""

import os
import importlib.util
from peewee import Model, CharField, IntegerField, DateTimeField
from datetime import datetime
from core.db import db, BaseModel


class Migration(BaseModel):
    """Track which migrations have been applied"""
    name = CharField(unique=True)
    applied_at = DateTimeField(default=datetime.now)


def get_migration_files():
    """Get all migration files in order"""
    migrations_dir = os.path.dirname(__file__)
    files = []

    for filename in os.listdir(migrations_dir):
        if filename.endswith('.py') and filename[0].isdigit():
            files.append(filename)

    return sorted(files)


def get_applied_migrations():
    """Get set of already applied migration names"""
    try:
        return set(m.name for m in Migration.select())
    except:
        # Migration table doesn't exist yet
        return set()


def run_migrations():
    """Run all pending migrations"""
    # Ensure migrations table exists
    db.create_tables([Migration], safe=True)

    applied = get_applied_migrations()
    migration_files = get_migration_files()

    for filename in migration_files:
        migration_name = filename[:-3]  # Remove .py extension

        if migration_name in applied:
            continue

        # Load and run the migration
        migrations_dir = os.path.dirname(__file__)
        filepath = os.path.join(migrations_dir, filename)

        spec = importlib.util.spec_from_file_location(migration_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Run the migration
        module.up()

        # Record that it was applied
        Migration.create(name=migration_name)

        print(f"Applied migration: {migration_name}")


if __name__ == '__main__':
    db.connect()
    run_migrations()
