# One-Off Fixes

These five issues have isolated causes and do not require structural refactoring.
Each can be addressed independently in any order.

---

## Fix 1: Database path (Issue #1)

**Problem:** The database filename `'habits.db'` is relative, resolving to wherever the
process is launched from. Launching from a different directory silently creates a second,
empty database.

**Fix:** Resolve the path to an absolute location at module load time, using the user's
home directory or an OS-appropriate application data directory. The path must be the same
regardless of where the process is started.

The resolution logic belongs in `db.py`, adjacent to the `SqliteDatabase` instantiation.
It should not be scattered across callers.

---

## Fix 2: Non-atomic habit reorder (Issue #7)

**Problem:** `perform_key_reorder()` saves each habit individually in a loop. A crash
or interruption partway through leaves the `display_order` values in a permanently
inconsistent state.

**Fix:** Wrap all saves in a single database transaction. Either the entire reorder
commits or none of it does. This can be applied to the existing `perform_key_reorder()`
in `piano_window.py` immediately. If the data service layer (document 02) is implemented
later, the reorder logic would move into the service, where the transactional guarantee
is a natural fit — but this fix does not depend on that refactor.

---

## Fix 3: `WindowMonitor` callback list is not thread-safe (Issue #9)

**Problem:** `_callbacks` is a plain class-level list. `register_callback()` appends to
it from the main thread while `_poll_loop()` iterates over it in a background thread.
There is also no `unregister_callback()` method, so callbacks accumulate and are never
removed even when the registering component is destroyed.

**Fix:** Two parts:

1. Guard the list with a lock. The polling loop should take a snapshot of the list under
   the lock before iterating, so that registrations during iteration are safe.

2. Add `unregister_callback()`. Any component that registers a callback must be able to
   remove it when it is destroyed. Without this, destroyed objects remain referenced
   through the callback list, preventing garbage collection and potentially causing
   calls into dead objects.

---

## Fix 4: Migration exception handling (Issue #10)

**Problem:** `get_applied_migrations()` uses a bare `except` that swallows all errors,
including unexpected ones, and returns an empty set. This would cause every migration to
appear un-applied and be re-run. Additionally, each migration's `up()` and the corresponding
`Migration.create()` record are not in the same transaction, so a failure between the two
leaves the schema partially migrated but untracked.

**Fix:** Two parts:

1. In `get_applied_migrations()`, catch only the specific exception that indicates the
   migrations table does not yet exist. Re-raise everything else. The "table doesn't exist"
   case is expected on first run; all other failures are bugs that should surface immediately.

2. Wrap `module.up()` and `Migration.create()` in a single transaction. Either the schema
   change and its tracking record are committed together, or neither is. This makes
   migration application idempotent and safe to retry.

---

## Fix 5: Session state reads without the state lock (Issue #12)

**Problem:** `is_paused()` and `is_ended()` read `self.state` without acquiring
`self.state_lock`, while `_pause()`, `_resume()`, and `end()` write it under the lock.
Additionally, `pause_start_time` is read in `get_elapsed_time()` under `elapsed_lock` but
written in the state-transition methods under `state_lock`, meaning the two locks guard
overlapping data with no consistent acquisition order.

**Fix:** Two parts:

1. Acquire `state_lock` in `is_paused()` and `is_ended()`. These are called from the
   tracking thread and must observe consistent state.

2. Consolidate lock responsibilities. `state` and `pause_start_time` are semantically
   coupled — you cannot reason about one without the other. They should be guarded by
   the same lock. Choose one lock (`state_lock` is the better name) and acquire it
   everywhere both fields are read or written. Remove or repurpose `elapsed_lock` to
   cover only fields that are genuinely independent.
