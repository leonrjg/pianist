# Refactor 01: Replace Process-Based Sessions with Thread-Based Sessions

## Problem Summary

Session tracking currently runs in separate OS processes. This was motivated by a desire to
isolate session logic from Qt, but it introduces a cascade of problems: concurrent SQLite
writes from multiple processes, a polling-based process monitor that creates race conditions,
stale liveness detection, incomplete process cleanup, and database log records that can be
orphaned if a worker process is killed unexpectedly.

These are not incidental bugs — they are structural consequences of the process boundary.
Fixing them piecemeal leaves the underlying cause intact.

## Goal

Run session tracking in threads within the main process. The `Session` class and all tracker
implementations are already free of Qt dependencies; they only need to not block the event
loop, which threads satisfy equally well.

---

## Requirements

### 1. SessionManager owns thread lifecycle, not process lifecycle

Replace `SessionProcessManager` with a `SessionManager` that starts, monitors, and stops
threads. The manager is the authoritative record of which habits have active sessions.
Thread liveness is queryable directly (`thread.is_alive()`), eliminating the polling loop
and the staleness problem that came with it.

The manager must be thread-safe: its internal session registry can be read from the UI
thread and written by the monitoring path. Use a lock consistently.

### 2. Session threads compute; they do not persist (in the GUI context)

This is the central constraint of this refactor **for the GUI**.

A session thread is responsible for:
- Tracking elapsed time
- Detecting activity/inactivity via trackers
- Knowing when to pause and resume

A session thread is **not** responsible for:
- Creating database records
- Saving elapsed time updates
- Writing log entries at any point

All database operations flow back to the main thread. Session threads post state change
events (session started, elapsed time updated, session ended) via a callback provided at
construction time; the `SessionManager` receives these callbacks and handles persistence
on the main thread. The `SessionManager` may bridge these callbacks to Qt signals for UI
updates, but `Session` itself has no knowledge of Qt or signals (see requirement 6).

This eliminates concurrent SQLite writers, orphaned log records, and the need for the
worker process to reconnect to the database.

**Important:** This constraint applies to the `SessionManager` in the GUI, not to `Session`
itself. See requirement 6.

### 3. Session state communication is one-directional and explicit

Session threads emit events upward to the main thread. They do not call back into the main
thread directly, and the main thread does not read internal session state directly.

The event contract should be narrow and stable:
- `session_started(habit_id)`
- `elapsed_updated(habit_id, elapsed_seconds)`
- `session_paused(habit_id, reason)`
- `session_resumed(habit_id)`
- `session_ended(habit_id, total_elapsed, idle_time)`

The main thread (via the `SessionManager`) listens to these events and takes all consequent
actions: updating the UI, writing the log, emitting signals to other components.

### 4. Commanding sessions is via method call, not IPC queues

The current design puts commands (`stop`, `adjust_time`, `get_elapsed`) on a multiprocessing
queue because process boundaries require serialization. With threads, commanding a session
is a direct method call on the `Session` object. The object must implement those methods
in a thread-safe way, but there is no queue, no serialization, and no TOCTOU race between
`empty()` and `get_nowait()`.

Elapsed time can be queried synchronously when needed, or continuously emitted on a timer
within the session thread. Choose one: do not mix pull and push, as the current design does.
A push model (the thread emits elapsed time every N seconds) is simpler and sufficient.

### 5. Shutdown is deterministic

Stopping a session sends a cancellation signal to the thread (via a threading.Event) and
then joins it with a reasonable timeout. If the thread does not exit within the timeout,
it is a bug in the session logic, not a lifecycle management failure.

On application close, all session threads are stopped and joined before the event loop exits.
No thread is abandoned. No database write is left in flight.

### 6. The `Session` class remains a self-contained domain object

`Session` should have no knowledge of signals, queues, or the UI. It models the concept of
a practice session: it tracks time, responds to tracker activity, and transitions through
states. How its events are communicated outward is the `SessionManager`'s concern.

**`Session` must remain usable standalone.** The CLI (`cli.py`) uses `Session` directly:
it creates one, calls `start()`, polls `get_elapsed_time()` in a blocking loop, calls
`end()` and `join()`. There is no event loop, no manager, no signals. The CLI runs a
single session in a single process on the main thread — the concurrency problems that
motivate this refactor do not exist there.

This means `Session` must retain its current self-contained persistence capability (the
`update_progress` thread that writes `Log` records). That behavior is not removed from
`Session`; it is **bypassed** in the GUI context by the `SessionManager`, which intercepts
lifecycle events and handles persistence itself rather than letting the session thread
write to the database.

Concretely, `Session` can accept an optional callback or persistence strategy at
construction time. When none is provided (CLI usage), it writes `Log` records itself as
it does today. When a persistence handler is provided (GUI usage via `SessionManager`),
it delegates to that handler instead. The default is self-sufficient; the override exists
for contexts that need external control.

The separation keeps `Session` testable without a running application, usable from the
CLI without a service layer, and composable differently in the GUI.

---

## What This Refactor Retires

- `multiprocessing` usage for sessions (the `spawn` start method can also be removed from `main()`)
- The `session_worker_process` function
- The result queue / command queue IPC pattern
- The process monitoring loop in `SessionProcessManager.run()`
- The `('elapsed', habit_id, data)` message protocol
- Database connection setup inside the worker process

---

## Quality Criteria

A successful implementation satisfies all of the following:

- **No concurrent SQLite writes.** In the GUI, only the main thread writes to the database.
  In the CLI, `Session` writes from its own thread, but only one session runs at a time
  in a single process — there is no concurrency problem to solve.
- **No polling for liveness.** Session active/inactive status is authoritative and immediately consistent.
- **Deterministic shutdown.** All threads are joined on close. No zombie threads.
- **No session state leaks.** A session that ends (normally or on crash) always produces a
  complete, closed log record. The main thread writes the final record in the `session_ended`
  handler, which is guaranteed to run because it is in the main process.
- **`Session` has no imports from the UI layer.** The boundary is strictly one direction.
- **`SessionManager` is the only GUI-side place that knows sessions exist.** No other
  GUI component should hold a reference to a `Session` object or call its methods directly.
- **The CLI continues to work.** `cli.py play` and `cli.py hit` use `Session` directly
  without a `SessionManager`, and they continue to function identically. No CLI code
  changes are required by this refactor.
