# Feature 04: Past Days on Index Page

## Goal

Show overdue / past-due tasks on the Index page in addition to upcoming ones, so
the user can see at a glance what they missed and act on it without navigating to the
calendar.

---

## Current State

`IndexPage._build_upcoming_tasks_section()` calls:

```python
get_upcoming_tasks(habits, timespan=30*24*60*60, include_manual=True, include_completed=True)
```

`get_upcoming_tasks` in `task/service.py` only looks forward:

```python
next_tasks = schedule.get_next_tasks(timespan)
# plus: filters manual tasks where task_date >= today
```

There is no function to retrieve tasks from the past, even though all schedule types
expose `get_previous_tasks(timespan)` which is already used by `CalendarPage`.

---

## New Function: `get_past_tasks`

Location: `src/core/task/service.py` (alongside `get_upcoming_tasks`)

```python
def get_past_tasks(
    habits: list[Habit],
    lookback_seconds: int,
    include_manual: bool = True,
    include_completed: bool = True,
) -> list[Task]:
    """
    Return tasks scheduled within the past `lookback_seconds` seconds,
    sorted ascending (oldest first).
    """
    tasks: list[Task] = []
    now = datetime.now()
    cutoff = now - timedelta(seconds=lookback_seconds)

    for habit in habits:
        schedule = habit.get_schedule()
        past_dts = schedule.get_previous_tasks(lookback_seconds)

        checker = habit.build_completion_checker(cutoff, now)
        for scheduled_dt in past_dts:
            if scheduled_dt.date() < now.date():   # strictly past (today shown by upcoming)
                task = Task.from_habit(habit, scheduled_dt, checker=checker)
                if include_completed or not task.completed:
                    tasks.append(task)

    if include_manual:
        yesterday = now.date() - timedelta(days=1)
        cutoff_date = cutoff.date()
        for manual_task in ManualTask.select().where(
            ManualTask.deleted_at.is_null() &
            (ManualTask.scheduled_at >= cutoff) &
            (ManualTask.scheduled_at < datetime.combine(now.date(), time.min))
        ):
            task = Task.from_manual_task(manual_task)
            if include_completed or not task.completed:
                tasks.append(task)

    return sorted(tasks, key=lambda t: t.scheduled_at)
```

Export `get_past_tasks` from `core/task/__init__.py`.

---

## Configurable Lookback

How many days back to show is stored in settings:

```
SettingsService.get('index.past_days', 0)
```

Default `0` means no past tasks are shown (backward-compatible with current behavior).
The Settings page exposes a spin box (range 0–90, step 1) labelled "Show past N days".

---

## Index Page Changes

`IndexPage.build_content()` is extended to prepend a past-tasks section before the
upcoming tasks section.

```python
def build_content(self):
    layout = self.layout()
    habits = ...

    title = self._create_section_header("Tasks")
    layout.addWidget(title)

    past_days = SettingsService.get('index.past_days', 0)
    if past_days > 0:
        self._build_past_tasks_section(layout, habits, past_days)

    self._build_upcoming_tasks_section(layout, habits)
    layout.addStretch()
```

`_build_past_tasks_section` works identically to `_build_upcoming_tasks_section` but
calls `get_past_tasks()` and uses `past_days * 86400` as the lookback. The section is
headed by a separator with a label like "Past" to visually distinguish it from upcoming.

---

## Visual Treatment

Past tasks use the same `HabitCard` component already used for upcoming tasks.
The urgency color logic in `_get_urgency_color` already handles overdue tasks
(returns `"rgb(160, 50, 50)"` for `hours_until < 0`), so no additional styling is needed.

Completed past tasks are shown with a muted style (already handled by `HabitCard`'s
completed state rendering).

---

## No Migration Needed

No new database tables. `get_previous_tasks()` already works on all schedule types.
The only schema dependency is the `AppSetting` table introduced in Feature 01.

---

## Export from task module

Update `src/core/task/__init__.py`:

```python
from .service import get_upcoming_tasks, get_past_tasks
__all__ = ['Task', 'TaskType', 'get_upcoming_tasks', 'get_past_tasks']
```

---

## Implementation Steps

1. Write `get_past_tasks()` in `task/service.py`.
2. Export from `task/__init__.py`.
3. Extend `IndexPage.build_content()` to call `_build_past_tasks_section()` when
   `index.past_days > 0`.
4. Implement `IndexPage._build_past_tasks_section()`.
5. Add "Show past N days" spin box to Settings page (Feature 01 dependency).
