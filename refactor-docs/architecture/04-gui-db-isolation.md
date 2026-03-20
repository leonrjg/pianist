# Refactor 04: Extract All Database Access from the GUI

## Problem Summary

Document 02 introduced `HabitService` to own the habit list and remove direct `Habit.select()` calls from the piano window. That boundary was never extended to the rest of the application. Every other entity — reminders, logs, mood, notes, manual tasks, and habit trackers — is still queried directly from widget and manager code.

The cost of this became concrete during the soft-delete migration (data model task 4): the `deleted_at IS NULL` filter had to be patched in approximately 30 scattered call sites across the GUI. Any widget written in the future that queries a model directly will silently skip the filter. The fix is structural: put the filter in one place per entity and make it impossible for the GUI to bypass it.

---

## Goal

Every database query and write initiated by the GUI must go through a service class. Widget and manager code must not import ORM models for the purpose of querying or mutating data. The boundary is enforced by convention and code review: GUI code reads and writes through services; core and CLI code may use the ORM directly.

---

## Current State of Direct DB Access in the GUI

The following is a complete inventory of GUI code that currently queries or mutates the database directly, grouped by entity.

### `Reminder`
| Site | Operation |
|---|---|
| `gui/managers/reminder_manager.py` | 3× `Reminder.select()` — scheduled firing |
| `gui/widgets/sheet_pages/reminder_page.py` | `Reminder.select()` — list view; `Reminder.get()` — trigger |
| `gui/widgets/sheet_pages/reminder_detail_page.py` | `Reminder.get()` — load for edit; `reminder.save()` — soft-delete; `reminder.save()` — update |
| `gui/widgets/piano_window.py` | `Reminder.get()` — notification handler |

### `Log`
| Site | Operation |
|---|---|
| `gui/widgets/sheet_pages/activity_card.py` | 2× `Log.select()` — session list display; `log.save()` — soft-delete |
| `gui/managers/session_manager.py` | `Log.create()` — start session; `log.save()` — finalize |

### `ManualTask`
| Site | Operation |
|---|---|
| `gui/services/habit_service.py` | `ManualTask.select()`, `ManualTask.create()`, `task.save()` — toggle completion |
| `gui/widgets/sheet_pages/calendar_page.py` | `ManualTask.select()` — calendar display |
| `gui/widgets/sheet_pages/index_page.py` | `ManualTask.update()`, `ManualTask.select()`, `ManualTask.create()` — toggle completion |

### `Mood` / `MoodLog`
| Site | Operation |
|---|---|
| `gui/widgets/sheet_pages/mood_page.py` | `Mood.select()`, `Mood.create()`, `mood.save()` (soft-delete), `MoodLog.save()` (soft-delete) — full CRUD |

### `HabitTracker`
| Site | Operation |
|---|---|
| `gui/managers/auto_session_manager.py` | `HabitTracker.select()` — window matching |
| `gui/widgets/sheet_pages/habit_detail_page.py` | `HabitTracker.update()` (soft-delete), `HabitTracker.insert()` — save trackers |

### `Note`
| Site | Operation |
|---|---|
| `gui/widgets/notes_widget.py` | `Habit.get()`, calls `Note.get_global_note()` / `Note.get_habit_note()` |

`Note` already has class-method accessors (`get_global_note`, `get_habit_note`) that encapsulate the query. This is the right pattern — it just needs to be consistently used and the widget should not need to import `Habit` for the lookup.

---

## Design

### One service class per domain

Each domain gets a service class that owns all reads and writes for that domain. Services live in `src/core/` (they are domain logic, not GUI logic) and are instantiated once at startup, then passed to the GUI as dependencies.

```
src/core/
  reminder/service.py      # already exists (fire logic) — extend with query methods
  habit/service.py         # move HabitService here from gui/services/
  mood/service.py          # new
  notes/service.py         # new (thin wrapper over Note class methods)
  task/service.py          # already exists (get_upcoming_tasks) — extend with mutations
```

`HabitTracker` and `Log` are owned by the `Habit` and `Session` domains respectively; their query methods belong on `HabitService` and `SessionManager`/a new `LogService`.

### Soft-delete is enforced at the service boundary

Every `select()` inside a service includes `Model.deleted_at.is_null()`. Every `delete` operation sets `deleted_at` and `updated_at` and saves. The GUI never sees raw ORM queries, so it cannot accidentally produce an unfiltered result.

### Services are passed as dependencies, not imported as singletons

Services are constructed in `main()` (or `initialize_database()`) and passed downward. Widget code receives a service object in its constructor or via a setter. This keeps services testable: a test can construct a service against an in-memory database and pass it to a widget without starting the Qt application.

### The CLI is not affected

The CLI continues to use the ORM directly. Services are a GUI-layer concern for the same reasons stated in document 02: the CLI is short-lived, single-threaded, and has no caching or stale-data problem. Services must not become a mandatory gateway that the CLI is forced through.

---

## Service API (per domain)

### `ReminderService` (extend existing)

```python
# Reads
get_all_active() -> List[Reminder]          # is_enabled=True, deleted_at IS NULL
get_by_id(id: UUID) -> Reminder             # deleted_at IS NULL or raise
get_due_sr(now: datetime) -> List[Reminder]
get_due_stochastic(now: datetime) -> List[Reminder]

# Writes (existing methods stay)
fire_reminder(reminder, ...) -> FireResult
reschedule(reminder, ...)
apply_feedback(reminder, quality)
delete(reminder: Reminder) -> None          # soft-delete
```

### `HabitService` (extend existing, move to `core/`)

```python
# Tracker queries (move from gui/managers/auto_session_manager.py and session.py)
get_enabled_trackers(habit: Habit) -> List[HabitTracker]
get_window_trackers(habit: Habit) -> List[HabitTracker]
save_trackers(habit: Habit, tracker_configs: List[dict]) -> None  # replaces delete+insert pattern

# Log queries (move from gui/widgets/sheet_pages/activity_card.py)
get_logs_for_bucket(habit: Habit, bucket: Bucket) -> List[Log]
delete_log(log: Log) -> None                # soft-delete
```

### `MoodService` (new)

```python
get_all() -> List[Mood]                     # deleted_at IS NULL, ordered
get_current_log() -> Optional[MoodLog]
get_recent_logs(limit: int) -> List[MoodLog]
log_mood(mood: Mood) -> MoodLog
delete_mood(mood: Mood) -> None             # soft-delete
delete_log(log: MoodLog) -> None            # soft-delete
create_mood(symbol: str, description: str) -> Mood
```

### `TaskService` (extend existing `core/task/service.py`)

```python
# Existing
get_upcoming_tasks(habits, timespan, ...) -> List[Task]

# New
toggle_habit_task(habit: Habit, scheduled_at: datetime) -> None   # create or soft-delete ManualTask
toggle_standalone_task(task: ManualTask, completed: bool) -> None
get_manual_tasks_in_range(start: date, end: date) -> List[ManualTask]
```

### `NoteService` (new, thin)

```python
get_global_note() -> Note
get_habit_note(habit: Habit) -> Note
```

---

## Migration Path

1. Create the service classes with the query/mutation methods above.
2. Update each GUI call site to use the service instead of the ORM directly.
3. Remove ORM model imports from widget files that no longer need them.
4. Move `HabitService` from `gui/services/` to `core/` and update all imports.

Each domain can be migrated independently. The order does not matter.

---

## Quality Criteria

- **No ORM `select()`, `get()`, `get_by_id()`, `create()`, `delete()`, `save()`, or `update()` calls in `src/gui/`**, with the sole exception of `Log` writes in `SessionManager` (which owns log lifecycle and has no service to delegate to, pending a future `LogService`).
- **Soft-delete is enforced in one place per entity.** Adding a new GUI view for any entity requires no thought about `deleted_at` — the service already filters it.
- **Each service is independently testable** without starting the Qt application.
- **The CLI is unchanged.** No ORM call in `src/cli/` is modified.
