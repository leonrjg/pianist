# Task Abstraction

Unified task representation for both habit-scheduled tasks and manual tasks.

## Overview

The Task abstraction provides a clean, statically-typed interface for working with tasks from different sources:

1. **Habit Tasks**: Computed from habit schedules (daily, weekly, etc.)
2. **Manual Tasks**: User-created tasks stored in the database

## Key Components

### `Task` (core/task/task.py)

Immutable dataclass representing a task:

```python
@dataclass(frozen=True)
class Task:
    type: TaskType              # HABIT or MANUAL
    scheduled_at: datetime      # When the task is scheduled/due
    title: str                  # Display name
    habit: Optional[Habit]      # Associated habit (None for standalone tasks)
    completed: bool             # Completion status
    completed_at: Optional[datetime]
    created_at: Optional[datetime]
    source_id: Optional[int]    # ID of source object
```

**Properties:**
- `is_overdue`: Check if task is overdue
- `is_habit_task`: Check if habit-scheduled
- `is_manual_task`: Check if manual task

**Factory Methods:**
- `Task.from_habit(habit, scheduled_at)`: Create from habit schedule
- `Task.from_manual_task(manual_task)`: Create from ManualTask record

### `ManualTask` (core/habit/manual_task.py)

Database model for manual tasks and manual completions:

```python
class ManualTask(BaseModel):
    habit: Optional[Habit]       # Optional habit association
    title: Optional[str]         # Custom title (None for habit completions)
    scheduled_at: datetime       # When scheduled/due
    completed_at: Optional[datetime]  # When completed (None if incomplete)
    created_at: datetime         # When created
```

**Use Cases:**

1. **Manual Habit Completion**: `habit` set, `title` None
2. **Standalone Task**: `title` set, `habit` optional

**Properties:**
- `is_completed`: Whether completed_at is set
- `is_custom_task`: Whether this is a standalone task (has title)

### Service (core/task/service.py)

**`get_upcoming_tasks(habits, timespan, include_manual=True, include_completed=True)`**

Returns unified list of tasks from all sources, sorted by scheduled_at.

## Usage Examples

### Get All Upcoming Tasks

```python
from core.task import get_upcoming_tasks

tasks = get_upcoming_tasks(
    habits=active_habits,
    timespan=7 * 24 * 60 * 60,  # 7 days
    include_manual=True,
    include_completed=True
)

for task in tasks:
    print(f"{'✓' if task.completed else '○'} {task.title}")
    print(f"  Due: {task.scheduled_at}")
```

### Create Standalone Manual Task

```python
from core.habit.manual_task import ManualTask
from datetime import datetime, timedelta

tomorrow = datetime.now() + timedelta(days=1)

ManualTask.create(
    habit=None,
    title="Call dentist",
    scheduled_at=tomorrow,
    completed_at=None  # Not completed yet
)
```

### Mark Habit Task Complete Manually

```python
ManualTask.create(
    habit=my_habit,
    title=None,  # None for habit completions
    scheduled_at=task_datetime,
    completed_at=task_datetime  # Completed immediately
)

# Verify
assert my_habit.is_task_completed(task_datetime)
```

### Complete a Manual Task

```python
task = ManualTask.select().where(...).first()
task.completed_at = datetime.now()
task.save()
```

### Filter Tasks

```python
# Only incomplete tasks
incomplete = get_upcoming_tasks(habits, timespan, include_completed=False)

# Only habit tasks
habit_tasks = [t for t in tasks if t.is_habit_task]

# Only overdue tasks
overdue = [t for t in tasks if t.is_overdue]

# Only manual tasks
manual_tasks = [t for t in tasks if t.is_manual_task]
```

## Database Schema

**manual_task table:**

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| id | INTEGER | No | Primary key |
| habit_id | INTEGER | Yes | Foreign key to habit |
| title | TEXT | Yes | Custom task title |
| scheduled_at | TIMESTAMP | No | When scheduled/due |
| completed_at | TIMESTAMP | Yes | When completed |
| created_at | TIMESTAMP | No | When created |

**Indexes:**
- `(habit_id, scheduled_at)` - Fast habit task lookups
- `(scheduled_at)` - Fast upcoming task queries

## Migration

Run migration 012 to update the schema:

```bash
python -m core.migrations.012_update_manual_task_schema
```

This migration:
- Adds `scheduled_at` column
- Makes `completed_at` nullable
- Makes `habit_id` nullable
- Updates indexes
- Migrates existing data (all marked as completed)

## Updated Files

1. **New modules:**
   - `core/task/__init__.py`
   - `core/task/task.py`
   - `core/task/service.py`
   - `core/task/example_usage.py`

2. **Updated models:**
   - `core/habit/manual_task.py` - New schema
   - `core/habit/habit.py` - Updated `is_task_completed()`

3. **Updated UI:**
   - `gui/widgets/sheet_pages/index_page.py`
   - `gui/widgets/piano_window.py`

4. **Migration:**
   - `core/migrations/012_update_manual_task_schema.py`

## Benefits

1. **Static Typing**: Full type safety with dataclasses
2. **Immutability**: Frozen dataclass prevents mutations
3. **Clean Separation**: Clear distinction between scheduling and completion
4. **Future-Ready**: Supports standalone tasks, incomplete tasks
5. **Unified Interface**: Single API for all task types
6. **Easy Filtering**: Type-safe filtering by task properties
