Problem: I want this app's data to be portable across devices, as is vital in a habit tracking, tasks and productivity app. A main
  server like Anki requires resources and public trust that the project doesn't have, therefore I'm interested in the LocalSend
  model (seamless LAN data transfer). My idea is having the app's instances in N devices constantly sync between each other, but
  being able to "live" without the others if not available (and sync everything once available again). For this, we need to
  adjust the app's data model to support this and eliminate any chance of merge conflicts which the user cannot solve, as this
  is a open source product for the general public. Analyze this app's data model and determine a new model that supports the
  distributed design.

Proposed design:

---

## Current Data Model — Entities

| Entity | PK Type | Key Relations | Mutability |
|---|---|---|---|
| `Habit` | `AutoField` (int) | — | Mutable (user edits config) |
| `Log` | `AutoField` (int) | → Habit | **Immutable event** (append-only session) |
| `HabitTracker` | Composite `(habit, tracker)` | → Habit | Mutable (enable/disable) |
| `ManualTask` | `AutoField` (int) | → Habit (opt.) | Mutable (complete/delete) |
| `Mood` | `AutoField` (int) | — | Mutable |
| `MoodLog` | `AutoField` (int) | → Mood | **Immutable event** |
| `Reminder` | `AutoField` (int) | → Habit (soft, int) | Mutable (SR state updates) |
| `ReminderLog` | `AutoField` (int) | → Reminder | **Immutable event** |
| `Note` | `AutoField` (int) | → Habit (opt.) | Mutable (content edits) |

---

## Core Problems with Current Model

### 1. Integer auto-increment PKs cause collisions
Device A creates `Habit(id=3)` offline. Device B creates `Habit(id=3)` offline. They refer to completely different entities. Every table has this problem.

### 2. No tombstoning — deletions are invisible
If Device A deletes a `Habit`, Device B will re-create it on next sync because it has no record the deletion ever happened.

### 3. No `updated_at` on most tables
`Log`, `HabitTracker`, `ManualTask`, `Mood`, `MoodLog`, `ReminderLog`, `Note` have no update timestamp. There is no way to determine which version is newer during a sync.

### 4. `Reminder.habit_id` is a raw `IntegerField` (soft link)
It stores an integer that references a `Habit` by integer PK, bypassing FK constraints. In a distributed model, integer PKs are meaningless across devices.

### 5. `Habit.name` has a `unique=True` constraint
Two devices can independently create habits with different UUIDs but the same name. This constraint must move from DB-enforced to application-enforced (or dropped).

---

## Design Principles for the New Model

Two classes of data behave completely differently:

**Mutable entities** — `Habit`, `Mood`, `Reminder`, `Note`, `HabitTracker`, `ManualTask`
→ Use **Last-Write-Wins (LWW)** keyed on `updated_at`. No user-visible merge conflicts. The device with the most recent write wins.

**Immutable events** — `Log`, `MoodLog`, `ReminderLog`
→ These are append-only timestamped facts. Two devices recording sessions at the same time produce two *distinct* sessions, not a conflict. Sync = union by UUID. No merging needed.

LWW is the right choice here (not vector clocks, OT, or CRDTs) because:
- Conflicts on this type of data are rare and low-stakes (the user was at one machine)
- General public cannot be expected to resolve merge dialogs
- The truly important data (`Log`, `MoodLog`) is conflict-free by nature

---

## Proposed New Model

### Universal additions to every table

```python
import uuid

# Replace all:    id = AutoField()
# With:           id = UUIDField(primary_key=True, default=uuid.uuid4)

# Add to all tables:
device_id  = CharField()          # UUID of the device that created this record
updated_at = DateTimeField(...)   # Already on Habit/Reminder; add to all others
deleted_at = DateTimeField(null=True)  # Tombstone — NULL means not deleted
```

The `deleted_at` tombstone is the key to propagating deletions. Records are **never hard-deleted** from the database while sync is active. A record with `deleted_at` set is "dead" but still replicates.

---

### Table-by-table changes

**`Habit`**
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
+ device_id:    CharField
+ deleted_at:   DateTimeField(null=True)
~ updated_at:   already exists ✓
~ name:         remove unique=True constraint (identity is UUID now, not name)
```

**`Log`** *(immutable event)*
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- habit:        FK(int)    →  FK(UUID)
+ device_id:    CharField
+ deleted_at:   DateTimeField(null=True)  # for rare manual deletions to propagate
+ updated_at:   DateTimeField(default=datetime.now)
```

**`HabitTracker`**
```
- primary_key:  CompositeKey(habit, tracker)  →  id = UUIDField(primary_key=True, default=uuid.uuid4)
- habit:        FK(int)  →  FK(UUID)
+ device_id:    CharField
+ updated_at:   DateTimeField(default=datetime.now)
+ deleted_at:   DateTimeField(null=True)
  (keep habit+tracker as a unique-together index for lookups)
```

**`ManualTask`**
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- habit:        FK(int)    →  FK(UUID, nullable)
+ device_id:    CharField
+ updated_at:   DateTimeField(default=datetime.now)
+ deleted_at:   DateTimeField(null=True)
```

**`Mood`**
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
+ device_id:    CharField
+ updated_at:   DateTimeField(default=datetime.now)
+ deleted_at:   DateTimeField(null=True)
```

**`MoodLog`** *(immutable event)*
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- mood:         FK(int)    →  FK(UUID)
+ device_id:    CharField
+ updated_at:   DateTimeField(default=datetime.now)
+ deleted_at:   DateTimeField(null=True)
```

**`Reminder`**
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- habit_id:     IntegerField(null=True)  →  habit = ForeignKeyField(Habit, null=True) [UUID FK]
+ device_id:    CharField
+ deleted_at:   DateTimeField(null=True)
~ updated_at:   already exists ✓
```

**`ReminderLog`** *(immutable event)*
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- reminder:     FK(int)    →  FK(UUID)
+ device_id:    CharField
+ updated_at:   DateTimeField(default=datetime.now)
+ deleted_at:   DateTimeField(null=True)
```

**`Note`**
```
- id:           AutoField  →  UUIDField(primary_key=True, default=uuid.uuid4)
- habit:        FK(int)    →  FK(UUID, nullable)
+ device_id:    CharField
+ deleted_at:   DateTimeField(null=True)
~ updated_at:   already exists ✓
```

---

### Two new tables

**`Device`** — Registry of known peers (local + discovered)
```python
class Device(BaseModel):
    id         = UUIDField(primary_key=True, default=uuid.uuid4)
    name       = CharField()         # e.g. "Leon's MacBook"
    is_self    = BooleanField()      # True for the local device
    last_seen  = DateTimeField(null=True)
    created_at = DateTimeField(default=datetime.now)
```

**`SyncState`** — Tracks last successful sync per peer (never synced itself, local only)
```python
class SyncState(BaseModel):
    device_id    = UUIDField(primary_key=True)   # the peer
    last_sync_at = DateTimeField()
```

This lets each device compute the delta: "give me all records where `updated_at > SyncState.last_sync_at` for this peer." The peer responds with its delta, both sides merge with LWW.

---

## Merge Algorithm (for implementation reference)

```
for each incoming record R from peer:
    local = DB.get(R.id)
    if local is None:
        DB.insert(R)                            # new record, just insert
    elif R.updated_at > local.updated_at:
        DB.update(R)                            # peer has newer version, overwrite
    # else: local is newer, discard R

After sync:
    SyncState[peer.id].last_sync_at = now()
```

Deletion: if `R.deleted_at` is set, the merged record has `deleted_at` set. Application code filters `WHERE deleted_at IS NULL` everywhere (standard soft-delete pattern).

---

## What Does NOT Change

- The migration runner pattern (just add a new migration)
- The `Schedule` system and all schedule types
- All GUI/service code — only the model layer changes
- Peewee ORM usage

---

## Migration Path

1. Generate a stable `device_id` (UUID, stored in a local config file on first run — **not** in the DB)
2. Write a single migration that:
   - For each existing table: add `device_id`, `updated_at`, `deleted_at` columns
   - Populate `device_id` with the local device's UUID for all existing rows
   - Populate `updated_at` with `created_at` (or `now()`) for rows that lack it
   - **UUID PK migration is the hard part**: SQLite doesn't support altering column types, so this requires creating new tables with UUID PKs, copying data with `uuid4()` for each row, and updating all FK references

The UUID PK migration is the only invasive step. Everything else is additive.

---

**Summary:** The main structural change is UUID PKs + `deleted_at` + `updated_at` on all tables, plus two small new tables (`Device`, `SyncState`). The LWW merge rule is simple enough that the sync engine will be ~100 lines of logic. The LAN transport (discovery + transfer) is the larger implementation task, but it is fully decoupled from the data model.
