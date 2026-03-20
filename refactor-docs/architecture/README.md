# Refactor Plan Overview

This directory contains plans for addressing the architectural and implementation issues identified
in the codebase audit. Three documents cover two structural refactors and a set of targeted one-off fixes.

## Documents

| Document | Scope | Issues addressed |
|---|---|---|
| `01-threaded-sessions.md` | Replace OS-process sessions with threads | #2, #3, #4, #5, #13 |
| `02-data-service-layer.md` | Introduce an application-level data service | #6, #8, #11 |
| `03-one-off-fixes.md` | Isolated targeted fixes | #1, #7, #9, #10, #12 |
| `04-gui-db-isolation.md` | Extract all database access from the GUI | — |

## Sequencing

The one-off fixes are independent and can be done at any time.

The two structural refactors are also **independent of each other** and can be done in
either order. They address different problem clusters, operate on different parts of the
codebase, and build different communication mechanisms:

- The session refactor (#01) produces high-frequency, transient session lifecycle events
  (elapsed time ticks, pause/resume, session end). These flow from background threads to
  the `SessionManager`.
- The data service layer (#02) produces low-frequency, persistent data change notifications
  (habit created, reordered, archived). These flow from the service to UI subscribers.

These are fundamentally different event streams and would not share a channel. Neither
refactor creates infrastructure the other depends on.

## Shared Design Principle

Both structural refactors enforce the same boundary **in the GUI context**:

> **The main thread is the sole writer to the database and the sole owner of in-memory
> application state. Background threads compute; they do not persist.**

Every issue in clusters A and B is, at its root, a violation of this principle. The refactors
restore it.

## Interface Agnosticism

The application has two interfaces: a GUI (`gui/`) and a CLI (`cli/cli.py`). The problems
addressed by these refactors exist only in the GUI — the CLI is a short-lived, single-threaded
process with no concurrency, no caching, and no stale-data issues.

The refactors are scoped accordingly:

- **`Session`** remains a self-contained domain object usable by both the GUI and CLI.
  The GUI wraps it in a `SessionManager` that intercepts persistence; the CLI uses it
  directly. No CLI code changes are required.
- **The data service layer** is a GUI-only construct. The CLI continues to use the ORM
  directly for reads and writes. The service is not a mandatory gateway — it is an
  additional layer for long-lived consumers that need caching and change notifications.
- **`initialize_database()`** is shared infrastructure. Both interfaces call it at startup.
  Moving it out of the widget constructor (refactor 02) does not change how the CLI calls it.
