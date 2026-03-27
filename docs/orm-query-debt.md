# ORM Query Debt

Instances in which inefficient data retrieval has been papered over with in-memory caches,
Python-level filtering, or pre-fetch workarounds instead of being solved at the database
query layer.

---

## 1. `HabitService._schedule_cache` — explicit in-memory cache masking a missing query

**File:** `src/core/habit/service.py:32`

`HabitService` maintains a `_schedule_cache: Dict[habit_id, {task_dt, is_completed}]` that
is populated at startup and rebuilt after every mutation. The cache exists entirely because
`Habit.is_task_completed()` is too expensive to call on every UI render cycle — it issues
two separate DB queries per call. There is no ORM query that answers "what is the next
scheduled task, and has it been completed?" for a set of habits in a single round-trip.
The cache is compensating for that missing query.

**Suggested fix:** A query that joins `Log`/`ManualTask` against the expected task window per
habit, returning completion status in one shot, would make the cache unnecessary.

---

## 2. `Habit.is_task_completed` loads the full bucket history to answer a per-task question

**File:** `src/core/habit/habit.py:207`

```python
buckets = self.get_activity_buckets()        # fetches ALL aggregated log buckets
bucket  = self._find_bucket_for_task(buckets, task)   # linear Python scan
```

`get_activity_buckets()` executes a grouped aggregate over the entire `Log` table for the
habit, returns every bucket ever recorded, and then `_find_bucket_for_task` discards all
but one. A targeted query — "does any session exist whose start falls within the time
window of this specific task?" — would be a single bounded `WHERE start BETWEEN ... AND ...`
with no aggregation and no Python scan.

The second half of `is_task_completed` issues a separate `ManualTask.exists()` query,
meaning a single call always costs two DB round-trips regardless of the result of the first.

---

## 3. `build_completion_checker` is itself a pre-fetch workaround; `analytics.py` does not even use it

**Files:** `src/core/habit/habit.py:166`, `src/core/analytics.py:135, 157, 163`

`build_completion_checker()` is an intermediate workaround for the N+1 problem described
in #2: it pre-loads all buckets and manual completions for a habit once, then closes over
them so a loop can check many tasks without re-querying. Its docstring is explicit:

> *"Fetches activity buckets and manual completions once, so callers checking many tasks
> avoid N DB queries."*

This is still a pre-fetch-then-scan pattern, not a relational query — it trades N queries
for one full-history load per habit. The root fix is the same as for #1 and #2: a query
that returns completion status for a set of task datetimes directly, without loading the
full bucket history first.

The situation in `analytics.py` is worse: `get_upcoming_tasks` and `get_tasks_in_range`
call `habit.is_task_completed(task)` per task inside a loop without using even this
workaround, so they issue two DB queries per task.

---

## 4. `MoodService.create_mood` uses Python `max()` over a full table load

**File:** `src/core/mood/service.py:37`

```python
moods     = Mood.select().where(Mood.deleted_at.is_null())
max_order = max((m.display_order for m in moods), default=0)
```

All mood rows are hydrated into Python objects to compute a single aggregate. The database
can compute this directly:

```python
max_order = Mood.select(fn.MAX(Mood.display_order)).where(Mood.deleted_at.is_null()).scalar() or 0
```

---

## 5. `get_streak` / `get_longest_streak` load the full bucket history per habit

**File:** `src/core/habit/habit.py:125, 149`

Both methods call `get_activity_buckets()` with no date bound, pulling the habit's entire
log history before walking it in Python. `analytics.get_habit_with_longest_streak` calls
`get_longest_streak()` for every habit in the list, producing one full-history bucket query
per habit.

At minimum, both methods could pass a date lower-bound into `get_activity_buckets()` to
limit the scan to the range relevant for streak calculation, rather than loading records
from the habit's entire lifetime.

---

## 6. `HabitService.load()` filters `archived` in Python after a full table scan

**File:** `src/core/habit/service.py:42–43, 95–96`

```python
self._habits = [
    h for h in Habit.select().where(Habit.deleted_at.is_null())...
    if not h.archived
]
```

`archived` is an indexed boolean column. Every non-deleted habit row is loaded and the
archived ones are silently dropped in Python. The same pattern is duplicated in
`reorder_visible_habits()`. `Habit.archived == False` belongs in the WHERE clause.

---

## 7. `HabitStatsPage._build_summary_section` fetches all buckets and slices by date in Python

**File:** `src/gui/widgets/sheet_pages/habit_stats_page.py:182–183, 227`

```python
buckets          = self.habit.get_activity_buckets()           # unbounded load
filtered_buckets = [b for b in buckets if b.start >= cutoff_date]  # Python slice
```

The user selects a time range (1 month / 6 months / 1 year) from a dropdown. The cutoff
date is known before the query runs. `get_activity_buckets()` issues a grouped SQL
aggregate — adding `WHERE start >= cutoff` to that aggregate would eliminate the discarded
rows at the source. The same unbounded load recurs in `_build_calendar()`.

---

## 8. `task/service.get_upcoming_tasks` loads the full `ManualTask` table and date-filters in Python

**File:** `src/core/task/service.py:140–152`

```python
query = ManualTask.select().where(ManualTask.deleted_at.is_null())
# no date range predicate on the query ↑
for manual_task in query:
    task_date = manual_task.scheduled_at.date()
    if today <= task_date <= cutoff_date:    # ← Python filter
```

The full table is loaded before date filtering. `get_past_tasks()` in the same file and
`TaskService.get_manual_tasks_in_range()` both apply date predicates at the query level —
`get_upcoming_tasks` was not updated to match.

---

## 9. `RepertoirePage` fetches all habits and filters by `archived` in Python

**File:** `src/gui/widgets/sheet_pages/repertoire_page.py:48–54`

```python
all_habits = self.service.get_all_non_deleted()
habits     = [h for h in all_habits if h.archived]      # or: if not h.archived
```

The page always knows at render time whether it is showing the active or archived view.
Loading the full set and discarding half is unnecessary. A targeted service method or an
`archived` parameter on the existing query would restrict the result set at the DB level.

---

## Common themes

**Post-query Python filtering (6, 7, 8, 9):** A WHERE predicate that the DB could evaluate
against an index is instead applied in Python after loading the full result set. Fix:
push the predicate into the query.

**Over-broad loads to answer a narrow question (2, 5, 7):** Methods load an entire
record set (all buckets, all history) when only a slice of it is needed. Fix: add
`start`/`end` parameters to query methods and pass them through to the WHERE clause.

**In-memory caches masking a missing relational query (1, 3):** State is pre-computed and
stored in Python dicts because the underlying retrieval is too expensive to run live. Fix:
replace the multi-query approach with a single query that returns the required result
directly, making the cache redundant.

**Python aggregates over loaded rows (4):** `max()`, `sum()`, `len()` applied to a
fully-loaded queryset instead of a SQL aggregate function. Fix: use `fn.MAX`, `fn.SUM`,
`fn.COUNT` in the query so only the scalar result is transferred.
