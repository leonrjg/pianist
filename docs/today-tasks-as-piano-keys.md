# Proposal: Show Today's Due Tasks as Piano Keys

## Goal

In addition to habits explicitly marked "show as piano key" (`Habit.visible`), the
piano should surface **everything due today** as keys, rendered as a block **on top**
of (before) the existing visible-habit keys.

"Due today" must include:

- Habit-scheduled occurrences whose next task falls on the current date.
- **Standalone manual tasks** (no associated habit) scheduled for today.

Standalone-task keys are **non-startable** (clicking does not start a session — there is
no habit to track) but otherwise look like normal keys, **including the black key**, and
their completion checkmark must work.

## Where keys come from today

The piano key list has a single source: `HabitService.get_visible_habits()`
([`service.py:52`](../src/core/habit/service.py)), which returns
`[h for h in self._habits if h.visible]` ordered by `display_order`. It is consumed in
two GUI spots:

- [`piano_window.py:78`](../src/gui/widgets/piano_window.py) — initial `num_habits`.
- [`piano_window.py:378`](../src/gui/widgets/piano_window.py) —
  `update_keys_for_window_size()` builds the `self.keys` dict list in order.

`KeyPainter.draw_keys` ([`key_painter.py:43`](../src/gui/painters/key_painter.py))
renders that list top-to-bottom, so **ordering is entirely determined by the source
list** — no painter change is needed to get the "today on top" effect.

Each key is a dict:

```python
{'label': str, 'habit': Habit|None,
 'task_datetime': datetime|None, 'is_completed': bool}
```

Today, `habit=None` means exactly one thing: an **empty padding slot**
([`piano_window.py:406`](../src/gui/widgets/piano_window.py),
[`:411`](../src/gui/widgets/piano_window.py),
[`:428`](../src/gui/widgets/piano_window.py)).

## What "due today" already uses elsewhere

The music-sheet **index page** already shows today's tasks. It does **not** use any
`get_due_today_habits`-style helper. It calls `get_upcoming_tasks(...)` from
`core.task.service` ([`index_page.py:157`](../src/gui/widgets/sheet_pages/index_page.py)),
then groups the result by day and treats the "today" bucket as the group where
`task.scheduled_at.date() == today`
([`index_page.py:166`](../src/gui/widgets/sheet_pages/index_page.py)).

Key facts about `get_upcoming_tasks`
([`service.py`](../src/core/task/service.py)):

- Returns **`Task` value objects, not `Habit` objects**
  ([`task.py`](../src/core/task/task.py)) — a unified type covering both habit-scheduled
  occurrences and standalone manual tasks.
- "Today onward" is enforced via `scheduled_dt.date() >= now.date()`.
- Completion is resolved through `habit.build_completion_checker(...)`.
- **Includes standalone manual tasks** where `habit is None`.

**Decision: reuse `get_upcoming_tasks`.** Do not write fresh schedule logic, and do not
add a `get_due_today_habits` that returns habits — standalone tasks have no habit to
return.

## The central design problem

A standalone task has `habit is None`. So does an empty padding slot. Once habit-less
tasks become keys, **`habit=None` carries two different meanings**, and that ambiguity
ripples through every consumer of the key dict.

This is an ownership-boundary problem (per repo global rules: fix the cause, don't
overload a field). The fix is to give the key dict an **explicit task identity** that is
independent of `habit`:

```python
{'label': str,
 'habit': Habit|None,            # None now means "no habit" (standalone or padding)
 'task': Task|None,              # NEW: the Task this key represents; None for padding
 'task_datetime': datetime|None,
 'is_completed': bool}
```

- **Padding slot:** `habit=None, task=None`.
- **Standalone-task key:** `habit=None, task=<Task>`.
- **Habit key:** `habit=<Habit>, task=<Task or None>` (existing visible-habit keys may
  keep `task=None` and rely on `get_next_task_info`, as today).

A consumer distinguishes "real key vs. padding" by `task is not None or habit is not
None`, never by `habit` alone.

## Core changes (`src/core/habit/service.py`)

**1. Today's task rows**, built on the existing function:

```python
from datetime import date
from core.task import get_upcoming_tasks

DAY = 24 * 60 * 60

def get_today_task_rows(self) -> list[Task]:
    """Tasks (habit-scheduled or standalone) due on the current local date."""
    today = date.today()
    tasks = get_upcoming_tasks(
        self._habits, timespan=DAY,
        include_manual=True, include_completed=True,
    )
    return [t for t in tasks if t.scheduled_at.date() == today]
```

**2. The combined, ordered key source**, deduped:

```python
def get_piano_key_rows(self) -> list[Task]:
    """Today's tasks first, then 'show as piano key' habits, deduped."""
    today_rows = self.get_today_task_rows()

    # Dedup must handle both keyed-by-habit and keyed-by-manual-task rows.
    seen_habit_ids = {t.habit.id for t in today_rows if t.habit is not None}

    visible_rows = [
        Task.from_habit(h, info_dt)            # adapt visible habit into a row
        for h in self.get_visible_habits()
        if h.id not in seen_habit_ids
        for info_dt in [self._next_task_dt(h)]  # reuse get_next_task_info logic
    ]
    return today_rows + visible_rows
```

## GUI changes (`src/gui/widgets/piano_window.py`)

### 1. Point the widget at the new source

Replace `get_visible_habits()` with the new row source at
[`:78`](../src/gui/widgets/piano_window.py) and
[`:378`](../src/gui/widgets/piano_window.py), and populate the new `'task'` field when
building each key dict.

### 2. Recompute scroll/count math

`update_keys_for_window_size` derives `scrolling_enabled` and `max_scroll_offset` from
`num_actual_habits` ([`:387`](../src/gui/widgets/piano_window.py)). Prepending N today
rows changes that count. Recompute counts from the combined row list, not from the
visible-habit count.

### 3. Checkmark hit-test: relax the habit requirement

`_get_checkmark_index_at_point` currently requires `key_data.get('habit')` **and**
`task_datetime` ([`:504`](../src/gui/widgets/piano_window.py)). Change the guard to
"has a task" (`task_datetime` present), so standalone-task keys are clickable for
completion.

### 4. Completion toggle: branch on habit presence

`_toggle_task_completion` calls `self.service.toggle_task_completion(habit, …)`
([`:542`](../src/gui/widgets/piano_window.py)), which is habit-mandatory. For a
standalone task, route instead to
`TaskService.toggle_standalone_task_completion(scheduled_at, new_state)` — the exact path
the index page already uses
([`index_page.py:299`](../src/gui/widgets/sheet_pages/index_page.py)). Branch on whether
the key's row has a habit.

### 5. Reorder: uniform via key dict

`perform_key_reorder` currently indexes into `get_visible_habits()` using the raw key
index ([`:970`](../src/gui/widgets/piano_window.py)), which breaks once the today-block
is prepended.

**Fix: read the `habit` or `manual_task` reference directly from the key dict** instead
of looking up by index. The reorder then updates `display_order` on whichever object
backs the key — `Habit` or `ManualTask` — with no index arithmetic.

This requires adding `display_order` to `ManualTask` (new column + migration) and
populating it when building key dicts in `get_piano_key_rows`. Every key is then
reorderable uniformly; no pinning, no offset, no special cases.

## Painter: (almost) no change required

- The black key is drawn unconditionally for every index in the non-padding range
  ([`key_painter.py:50`](../src/gui/painters/key_painter.py)), so **"keep the black key"
  needs no work** — provided the today-block sits in the non-padding index range (it
  does; it is prepended before padding).
- `draw_time_display` reads `state.get_time_display(habit.id)`
  ([`key_painter.py:294`](../src/gui/painters/key_painter.py)). Guarded by `if habit`, a
  standalone key simply renders a black key with **no** time text — which is the desired
  look.
- `draw_task_checkmark` already keys off `task_datetime` + `is_completed`
  ([`key_painter.py:362`](../src/gui/painters/key_painter.py)); once standalone keys
  carry those fields, the checkmark renders correctly with no painter change.

## Open decisions

1. **Completed standalone tasks** — `get_upcoming_tasks(include_completed=True)` returns
   them, and a titled-but-completed manual task is included
   ([`service.py:144`](../src/core/task/service.py)). Should a completed one-off task
   still occupy a key (filled checkmark) for the rest of the day, or drop off once
   checked? This matters more than for habits, since a one-off is "finished forever" once
   done, unlike a recurring habit.
