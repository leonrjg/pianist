# Refactor Design

Addresses the issues catalogued in `orm-query-debt.md`. Refactors are grouped by
root cause so that changes which share a fix are not duplicated. Cross-cutting
effects are called out explicitly under each entry.

---

## R1 — Targeted query for `is_task_completed` + eliminate `_schedule_cache`

**Debt issues addressed:** #1, #2, #3 (root cause of all three)

### Root cause

`is_task_completed` loads every bucket in the habit's history (`get_activity_buckets()`
with no date bound), scans them in Python to find the one window that contains
the requested task datetime, then issues a second query for ManualTask. The cache
in `HabitService` and the `build_completion_checker` pre-fetch exist solely because
this call is too expensive to run live.

### Fix

Replace the full-history load inside `is_task_completed` with a bounded aggregate
query that answers the same question in a single round-trip:

```python
# In Habit — replaces the get_activity_buckets() + _find_bucket_for_task() block
def _is_window_completed_by_log(self, min_threshold: datetime, max_threshold: datetime) -> bool:
    from core.habit.log import Log
    duration_expr = ...  # same expression currently used in get_activity_buckets
    net = (Log.select(fn.SUM(duration_expr))
               .where(
                   (Log.habit == self) &
                   (Log.start >= min_threshold) &
                   (Log.start < max_threshold) &
                   Log.end.is_null(False) &
                   Log.deleted_at.is_null()
               )
               .scalar()) or 0
    return net >= (self.allocated_time or 0)
```

`is_task_completed` then becomes two cheap, bounded queries:

1. The aggregate above (one scalar result, no Python scan).
2. `ManualTask.exists()` — already bounded, unchanged.

### Downstream: `build_completion_checker`

`build_completion_checker` (habit.py:174) currently calls `get_activity_buckets()`
with no date bound, loading the full log history for the habit even though the
caller always supplies a `[start, end]` window. After R2 adds the `since` parameter,
this call must be updated to pass `since=start`, bounding the bucket load to the
relevant window.

Beyond that, `build_completion_checker` can be simplified further: instead of
pre-loading all buckets and scanning them in a closure, it can issue a single batch
query computing completion for all task datetimes at once via a set of window
aggregates, returning a `{task_dt: bool}` map. Either approach eliminates the
full-history load; the batch variant is preferable when checking more than a handful
of tasks (e.g. `calendar_page.py:454`, which checks a ±60-day window per habit).

### Downstream: `HabitService._schedule_cache`

Once `is_task_completed` costs two bounded queries instead of a full bucket load
per call, there is no longer a performance reason to cache its result. Remove
`_schedule_cache`, `_rebuild_schedule_cache`, and `_rebuild_schedule_cache_for_habit`
entirely. `get_next_task_info` becomes a direct call: compute the next task from
the schedule (pure Python, no DB) and call `is_task_completed` on it.

### Downstream: `analytics.get_upcoming_tasks` / `get_tasks_in_range`

Both functions call `habit.is_task_completed(task)` inside a loop without even
using `build_completion_checker`. After R1 each per-task call is two bounded
queries rather than a full history load, which fixes the worst of the N+1 cost.
These functions are eliminated entirely by R5 (see below), which is the complete fix.

---

## R2 — Add `since` bound to `get_activity_buckets`

**Debt issues addressed:** #5, #7

### Root cause

`get_activity_buckets()` has no lower-date bound, so every caller receives the
habit's entire log history regardless of the time window it cares about.
`get_streak` / `get_longest_streak` then walk that list in Python. `HabitStatsPage`
loads the full history and slices it in Python after the fact.

### Fix

Add an optional `since: datetime = None` parameter to `get_activity_buckets`.
When provided, append `Log.start >= since` to the WHERE clause before the GROUP BY.

```python
def get_activity_buckets(self, size: int = None, limit: int = None,
                         since: datetime = None) -> list[Bucket]:
    ...
    q = (Log.select(...)
             .where((Log.habit == self) & (Log.end.is_null(False)) & Log.deleted_at.is_null())
             .group_by(bucket)
             ...)
    if since:
        q = q.where(Log.start >= since)
    ...
```

**`get_streak` / `get_longest_streak`:** Pass `since=self._schedule.start` as the
lower bound (no log can legally exist before the habit started, so this is lossless
for correct data and eliminates any orphaned rows from consideration). For
`get_streak`, which walks backwards from now, a tighter bound such as
`since = datetime.now() - timedelta(days=365)` can be used if streak length is
known to be bounded; that is a separate decision.

**`HabitStatsPage._build_summary_section` and `StatsPage._build_summary_section`:**
The cutoff date is known before the query runs. Pass it directly:

```python
cutoff_date = datetime.now() - timedelta(days=days_back)
buckets = self.habit.get_activity_buckets(since=cutoff_date)
# No Python filtering needed — remove the list comprehension
```

**`HabitStatsPage._build_calendar` and `StatsPage._build_calendar`:** Same pattern
— pass the days_back cutoff as `since`. `StatsPage._build_calendar` collects buckets
across all habits in a loop; each `get_activity_buckets(since=cutoff_date)` call
eliminates the discarded rows at the source.

**`HabitStatsPage._build_habit_stats_section` (`StatsPage`):** `stats_page.py:169`
calls `get_activity_buckets()` per habit with no bound to compute total_time and
session count for the stats cards. Pass `since=cutoff_date` here too; the cutoff
is determined by the same time-range dropdown that drives `_build_calendar`.

**`_build_activity_section` (both pages):** Both callers immediately slice the result
to `[:10]` in Python. The `limit` parameter already exists on `get_activity_buckets`.
Pass `limit=10` and remove the slice — no `since` is needed here since the goal is
the 10 most recent buckets regardless of date.

---

## R3 — Push `archived` predicate into the DB query

**Debt issues addressed:** #6, #9

### Root cause

`HabitService.load()` and `reorder_visible_habits()` load all non-deleted habits
then drop the archived ones in a Python list comprehension. `RepertoirePage` calls
`get_all_non_deleted()` (which returns both active and archived) and then filters
in Python for whichever view the user selected.

### Fix

**`HabitService.load()` and `reorder_visible_habits()`:** Add `Habit.archived == False`
to the WHERE clause. Deleted rows are already excluded; archived rows should be too:

```python
Habit.select()
     .where(Habit.deleted_at.is_null() & (Habit.archived == False))
     .order_by(Habit.display_order, Habit.id)
```

**`HabitService.get_all_non_deleted()`:** Add an `archived: bool | None = None`
parameter. When provided, append the predicate to the query:

```python
@classmethod
def get_all_non_deleted(cls, archived: bool | None = None) -> List[Habit]:
    q = Habit.select().where(Habit.deleted_at.is_null()).order_by(Habit.display_order, Habit.name)
    if archived is not None:
        q = q.where(Habit.archived == archived)
    return list(q)
```

**`RepertoirePage`:** Replace the post-load filter with a targeted call:

```python
habits = self.service.get_all_non_deleted(archived=self._show_archived_only)
```

**`StatsPage` (stats_page.py:50):** `build_content` calls `get_all_non_deleted()`
with no filter, so archived habits are included in all aggregate statistics. Since
the page displays active-habit performance, pass `archived=False`:

```python
habits = self.service.get_all_non_deleted(archived=False)
```

The Python list comprehensions in `RepertoirePage` are removed entirely.

---

## R4 — `MoodService.create_mood`: scalar aggregate

**Debt issue addressed:** #4

### Fix

One-line change. Replace the full-table hydration:

```python
# Before
moods = Mood.select().where(Mood.deleted_at.is_null())
max_order = max((m.display_order for m in moods), default=0)

# After
max_order = Mood.select(fn.MAX(Mood.display_order)).where(Mood.deleted_at.is_null()).scalar() or 0
```

---

## R5 — `task/service.get_upcoming_tasks`: push date filter into query

**Debt issue addressed:** #8

### Fix

The full `ManualTask` table is loaded before date filtering. `get_past_tasks` and
`get_manual_tasks_in_range` in the same file already apply date predicates at the
query level. Align `get_upcoming_tasks` to match:

```python
# Replace the unfiltered query + Python date check with:
manual_tasks = ManualTask.select().where(
    ManualTask.deleted_at.is_null() &
    (ManualTask.scheduled_at >= start_of_today) &
    (ManualTask.scheduled_at <= cutoff) &
    (ManualTask.title.is_null(False) | ManualTask.completed_at.is_null())
)
for manual_task in manual_tasks:
    ...
```

The `today <= task_date <= cutoff_date` Python guard and the `task_date` local
variable are removed.

---

## R6 — Dissolve `analytics.py`; integrate as class methods

**Requested as part of the brief. Also addresses debt issue #3 (N+1 in analytics functions).**

### Current functions and their new homes

| Function | New location | Rationale |
|---|---|---|
| `get_time_spent(buckets)` | `Bucket.total_net_duration(buckets)` — class method on `Bucket` | Operates entirely on `Bucket` data; no habit state needed. |
| `get_completion_rate(completed, scheduled)` | `Habit.completion_rate(completed, scheduled)` — static method on `Habit` | Pure calculation, but semantically about a single habit's ratio; belongs on the model. |
| `get_habit_with_longest_streak(habits)` | `Habit.with_longest_streak(habits)` — class method on `Habit` | Selects from a collection of `Habit` objects using `Habit` behaviour. |
| `group_habits_by_schedule(habits)` | `Habit.grouped_by_schedule(habits)` — class method on `Habit` | Groups `Habit` objects by a `Habit` attribute. |
| `sort_habits_by_completion_rate(habits)` | `Habit.sorted_by_completion_rate(habits)` — class method on `Habit` | Ranks `Habit` objects; depends only on habit and schedule data. |
| `get_upcoming_tasks(habits, timespan)` | **Deleted** — consolidate with `task/service.get_upcoming_tasks` | The analytics version calls `is_task_completed` per task (N+1, no batch) and returns plain dicts. The task-service version already uses `build_completion_checker` (batch) and returns typed `Task` objects. Callers of the analytics version are migrated to the task service. |
| `get_tasks_in_range(habits, timespan)` | **Deleted** — consolidate with `task/service` | Same reason as above. A `get_tasks_in_range` equivalent already exists in `TaskService.get_manual_tasks_in_range`; habit-scheduled tasks in a range can be added there or as a new `task/service` function. |

**Latent bug in `stats_page.py:149`:** `_build_champion_section` calls
`analytics.get_completion_rate(champion)` passing a single `Habit` object, but the
function signature is `get_completion_rate(buckets: int, previous_tasks: int)`. This
call currently fails silently — the surrounding `except: pass` suppresses the
`TypeError` at runtime. When dissolving `analytics.py`, fix the caller to compute
and pass the correct arguments:

```python
schedule = champion.get_schedule()
previous_tasks = len(schedule.get_previous_tasks(get_timespan(schedule.start)))
completed_buckets = len(champion.get_activity_buckets())
completion_rate = Habit.completion_rate(completed_buckets, previous_tasks)
```

After migrating all callers, delete `core/analytics.py` and remove the
`from core import analytics` import from all files that reference it
(`stats_page.py`, `habit_stats_page.py`, `calendar_page.py`, `cli/cli.py`).

---

## Cross-cutting summary

The table below shows which refactors overlap so that implementation order can
be planned without duplication.

| Debt issue | Primary fix | Secondary benefit from another refactor |
|---|---|---|
| #1 `_schedule_cache` | R1 (targeted query makes cache redundant) | — |
| #2 `is_task_completed` full load | R1 (bounded aggregate query) | — |
| #3 `build_completion_checker` pre-fetch; analytics N+1 | R1 (cheaper is_task_completed); R6 (delete analytics functions) | — |
| #4 `MoodService` Python max | R4 | — |
| #5 `get_streak` full load | R2 (`since` bound) | — |
| #6 `HabitService.load` Python archive filter | R3 | — |
| #7 `HabitStatsPage` Python date slice | R2 (`since` bound passed from UI) | — |
| #8 `get_upcoming_tasks` full ManualTask load | R5 | — |
| #9 `RepertoirePage` Python archive filter | R3 (`archived` param on service method) | — |
| analytics.py dissolution | R6 | R1 (fixes analytics N+1 before deletion) |

**Suggested implementation order:** R4 (isolated, trivial) → R3 (two service callsites,
no model changes) → R5 (one function, no model changes) → R2 (add `since`/`limit`
to one method; update callers in `habit.py`, `habit_stats_page.py`, `stats_page.py`) →
R1 (core query change; eliminates cache and simplifies checker) → R6 (depends on R1
having fixed N+1 before deletion; fix latent `get_completion_rate` bug as part of
caller migration).
