# Refactor 02: Introduce an Application Data Service Layer

## Problem Summary

The UI widget currently acts as the application's data manager: it initializes the database
inside its constructor, owns the habit list, queries the database during paint-triggering
operations, and hands a static snapshot of habits to components that need live data.
The result is N+1 database queries on every visual update, stale data in dependent
components, and database initialization entangled with widget construction.

## Goal

Introduce a thin service layer that sits between the database and the UI. This layer owns
the authoritative in-memory state of the application, initializes before any UI is created,
and notifies dependents when data changes. The UI reads from this layer's cache; it does
not query the database directly for display purposes.

**Scope:** This service layer is for the GUI — a long-lived process where caching, change
notifications, and stale-data avoidance matter. The CLI is a short-lived process that runs
a single command and exits. The CLI does not need caching, subscriptions, or a service
layer. It continues to use the ORM directly. The service layer must not become a mandatory
gateway that the CLI is forced through.

---

## Requirements

### 1. The service is initialized in `main()`, before the window exists

Database initialization — connecting, running migrations, seeding initial state — belongs
to application startup, not widget construction. It has failure modes (disk full, corrupted
schema, failed migration) that should produce a clean error before any UI is rendered.

The service object is constructed in `main()`, validated, and then passed to the window
as a dependency. The window constructor receives a working, ready service; it does not
perform any database setup itself.

This directly fixes the "DB initialized in widget constructor" issue and gives the
application a natural place to handle startup failures gracefully.

### 2. The service owns the in-memory habit list

The service loads all habits from the database at startup and holds them in memory. It
exposes read-only views of this data:

- All non-archived habits, ordered
- Only visible habits (the subset shown as piano keys)
- A single habit by ID

The UI reads from these views. It does not call `Habit.select()` for display purposes.

The list is the single source of truth. Any mutation to habit data (create, update, archive,
reorder) goes through the service, which updates both the database and the in-memory list
atomically, then notifies subscribers.

### 3. The service provides change notifications

Any component that depends on the habit list — the piano window, `AutoSessionManager`,
the music sheet widget — needs to know when the list changes. The service exposes a
subscription mechanism for this.

The notification should carry enough information for subscribers to react efficiently:
at minimum, whether the change was a reorder, a metadata update, an addition, or a removal.
Subscribers that only care about "something changed" can ignore the detail; subscribers
that maintain their own derived state can update selectively.

The Qt signal/slot system is a natural fit for this, but the service should not import
from Qt if avoidable. If the notification mechanism needs to be framework-neutral (for
testability), use a simple observer list. The UI adapter layer can bridge to Qt signals.

### 4. Schedule results are cached and explicitly invalidated

Computing the next task datetime for a habit involves reconstructing the schedule object
and iterating occurrences. This is not a constant-time operation and should not happen
on every scroll or resize event.

The service (or a cache attached to it) stores the precomputed next-task datetime per
habit and marks it stale when:
- A `ManualTask` is created or deleted for that habit
- The habit's schedule configuration changes
- The date changes (midnight rollover)

The piano window's key-building logic reads from this cache. A resize or scroll operation
only re-slices which cached entries are visible; it never triggers database access.

### 5. `AutoSessionManager` queries the service, not a snapshot

`AutoSessionManager` currently stores a snapshot of habits passed at construction time.
With the service in place, it holds a reference to the service and calls
`get_all_habits()` when checking whether a window title matches. It also subscribes to
change notifications so that newly added habits are immediately eligible for auto-start
without restarting the application.

This removes the need to pass a habit list to `AutoSessionManager` at all — it becomes
a dependency on the service, not on data.

### 6. In the GUI, mutations go through the service

Within the GUI process, all writes that affect the habit list go through the service:
- Creating or archiving a habit
- Updating habit metadata
- Reordering habits (the N individual saves become one transactional operation inside the service)
- Toggling task completion (updates the cache for that habit's next task)

The service validates, persists, updates the in-memory list, and fires notifications.
No GUI caller needs to know about database transactions, cache invalidation, or notifying
other components. Those are all internal to the service.

**The CLI is not subject to this constraint.** The CLI's `save`, `delete`, and `hit`
commands write to the ORM directly. They are short-lived processes with no subscribers,
no cache, and no stale-data problem. Forcing the CLI through the service would add
mandatory indirection that solves nothing for that context. The ORM is the shared
interface that both the service (internally) and the CLI use; the service is an
additional layer for long-lived consumers, not a replacement for the ORM.

### 7. The service does not own session state

Session management (which habits are currently being tracked, elapsed times) remains in
the `SessionManager`. The data service is specifically for persistent habit and task data.
These are separate concerns and should stay separate.

The session refactor (document 01) produces session lifecycle events. The main thread
handles those events, which may include writing to the database — but that write path
does not go through the habit service. It goes to the `Log` model directly, since log
records are not part of the habit list that the service manages.

---

## What This Refactor Retires

- Direct `Habit.select()` calls from `PianoFloatingWindow` for display purposes
- `initialize_database()` being called inside `PianoFloatingWindow.__init__`
- The habit list being stored directly on the window and on `AutoSessionManager`
- `on_habit_updated_from_sheet` and `refresh_habits` as ad-hoc re-query methods
  (replaced by the service's change notification)
- Schedule recomputation inside `update_keys_for_window_size()`

---

## Quality Criteria

A successful implementation satisfies all of the following:

- **The window constructor performs no I/O.** No database access, no file access in
  `__init__`. The widget is assembled from already-initialized dependencies.
- **`update_keys_for_window_size()` accesses no database.** It reads only from the
  in-memory cache. It is safe to call on every resize and scroll event.
- **All GUI mutation paths go through the service.** No GUI component creates, modifies,
  or reorders habits by calling ORM methods directly. The CLI continues to use the ORM.
- **`AutoSessionManager` reflects habit additions at runtime.** Adding a habit while
  the app is running makes it eligible for auto-start without restarting.
- **The service is independently testable.** It can be instantiated with a test database
  and exercised without starting the Qt application.
- **Startup failures are handled before the window exists.** A migration failure or
  database connection error produces an appropriate message, not a crash inside a
  widget constructor.
