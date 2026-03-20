# Refactor Tasks — Distributed Data Model

## Phase 1: Data Model

### Task 1 — Add device identity config
Generate and persist a stable device UUID in `~/.pianist/device_id` (plain text file). Add a `get_device_id()` helper in `src/core/config.py` (or similar) that reads the file on every call, creating it with a new `uuid4()` if it doesn't exist. This UUID is the `device_id` stamped on all rows created by this device and must NOT be stored in the database.

---

### Task 2 — Write UUID PK migration
Write migration `013_uuid_pks.py`. SQLite does not support ALTER COLUMN, so the approach for each table is: (1) create a new table with UUID PK and all new columns, (2) copy existing rows assigning `uuid4()` as the new PK and updating all FK columns to the corresponding new UUIDs, (3) drop the old table, (4) rename the new table.

Tables to migrate (in FK-safe order — parents before children):
- `habit`: AutoField → UUIDField PK; remove `unique=True` on `name`
- `mood`: AutoField → UUIDField PK
- `reminder`: AutoField → UUIDField PK; replace `habit_id` IntegerField with `habit` ForeignKeyField(Habit, null=True)
- `log`: AutoField → UUIDField PK; `habit` FK now references UUID
- `habit_tracker`: CompositeKey(habit, tracker) → UUIDField PK; `habit` FK now references UUID; keep `(habit, tracker)` as a unique-together index
- `manual_task`: AutoField → UUIDField PK; `habit` FK now references UUID
- `mood_log`: AutoField → UUIDField PK; `mood` FK now references UUID
- `reminder_log`: AutoField → UUIDField PK; `reminder` FK now references UUID
- `note`: AutoField → UUIDField PK; `habit` FK now references UUID

New columns to add to ALL tables during this migration:
- `device_id CharField()` — populate with `get_device_id()` for all existing rows
- `deleted_at DateTimeField(null=True)` — NULL for all existing rows
- `updated_at DateTimeField(default=datetime.now)` — populate with `created_at` where it exists, else `datetime.now()` for tables that lack it (`log`, `habit_tracker`, `manual_task`, `mood`, `mood_log`, `reminder_log`)

New tables to create:
- `Device(id UUIDField PK, name CharField, is_self BooleanField, last_seen DateTimeField null, created_at DateTimeField)`
- `SyncState(device_id UUIDField PK, last_sync_at DateTimeField)`

Insert a row into `Device` for the local device (`is_self=True`) using `get_device_id()`.

---

### Task 3 — Update Peewee model definitions
Update all model classes to match the new schema after the migration:

- `Habit`: `id = UUIDField(primary_key=True, default=uuid.uuid4)`; remove `unique=True` from `name`
- `Log`: `id = UUIDField(primary_key=True, default=uuid.uuid4)`; add `device_id`, `updated_at`, `deleted_at`
- `HabitTracker`: replace `CompositeKey` with `id = UUIDField(primary_key=True, default=uuid.uuid4)`; add `device_id`, `updated_at`, `deleted_at`; keep `(habit, tracker)` unique index in Meta
- `ManualTask`: UUID PK; add `device_id`, `updated_at`, `deleted_at`
- `Mood`: UUID PK; add `device_id`, `updated_at`, `deleted_at`
- `MoodLog`: UUID PK; add `device_id`, `updated_at`, `deleted_at`
- `Reminder`: UUID PK; replace `habit_id = IntegerField(null=True)` with `habit = ForeignKeyField(Habit, null=True)`; remove `get_habit()` helper (now just `self.habit`); add `device_id`, `deleted_at`
- `ReminderLog`: UUID PK; add `device_id`, `updated_at`, `deleted_at`
- `Note`: UUID PK; add `device_id`, `deleted_at`

Add two new model classes `Device` and `SyncState` (e.g. in `src/core/sync/models.py`).

---

### Task 4 — Add soft-delete filtering to all queries
Every place in the codebase that queries a sync-enabled table must add `.where(Model.deleted_at.is_null())`. Affected tables: Habit, Log, HabitTracker, ManualTask, Mood, MoodLog, Reminder, ReminderLog, Note.

Also update any `delete()` calls on these models to set `deleted_at = datetime.now(); updated_at = datetime.now(); save()` instead of hard-deleting.

Search for `.delete()`, `.select()`, `.get()`, `.get_by_id()` calls across `src/` to find all affected sites.

---

## Phase 2: Sync Engine

### Task 5 — Implement LWW merge engine
Create `src/core/sync/merge.py` with a `merge_record(table: str, incoming: dict)` function implementing Last-Write-Wins:

```python
existing = db_get(table, id=incoming["id"])
if existing is None:
    db_insert(table, incoming)
elif incoming["updated_at"] > existing["updated_at"]:
    db_update(table, incoming)
elif incoming["updated_at"] == existing["updated_at"] and incoming["device_id"] > existing["device_id"]:
    db_update(table, incoming)   # deterministic tiebreaker
# else: local is newer, discard
```

Deletion propagation: if `incoming["deleted_at"]` is set and the record wins LWW, the local record gets `deleted_at` set.

Include a table-name → model class registry so `merge_record` can dispatch to the right Peewee model.

---

### Task 6 — Implement HTTP sync server
Create `src/core/sync/server.py` with a Flask app running in a daemon thread on `0.0.0.0:47832`.

Three endpoints:
- `GET /sync/info` — return `{device_id, device_name, app_version}` as JSON
- `GET /sync/delta?since=<ISO-timestamp>` — query all sync-enabled tables for `updated_at > since` (including tombstones where `deleted_at IS NOT NULL`), return `{device_id, generated_at, records: [{table, data}]}`
- `POST /sync/push` — accept same `records` format, run `merge_record` for each

Enable WAL mode on the SQLite connection (`pragmas={'journal_mode': 'WAL'}` in `db.py`) so the sync thread can write while the main thread reads.

---

### Task 7 — Implement mDNS discovery service
Create `src/core/sync/discovery.py` using the `zeroconf` library.

- Advertise self as `_pianist._tcp.local.` on port 47832 with TXT record `{device_id, device_name, app_version}`
- Browse for other instances on the same service type
- On peer found: upsert into `Device` table (`last_seen = now()`), trigger a delta sync via `SyncClient`
- On peer lost: update `Device.last_seen`, stop pushing to that peer
- On shutdown: unregister advertisement

Expose `DiscoveryService.start()` and `DiscoveryService.stop()` methods.

---

### Task 8 — Implement HTTP sync client
Create `src/core/sync/client.py` with two modes:

**Delta sync** (called on peer reconnect / startup):
1. `GET /sync/info` — verify identity
2. Lookup `SyncState.last_sync_at` for this peer (default: Unix epoch if no entry)
3. `GET /sync/delta?since=t` — fetch their changes
4. Run `merge_record` for each incoming record
5. `POST /sync/push` — send our delta (records where `updated_at > t`) to them
6. Upsert `SyncState[peer.id].last_sync_at = now()`

**Live push** (called after every local write):
- For each active (reachable) peer: `POST /sync/push [{table, data}]` — fire-and-forget in a daemon thread; failures are silently skipped (delta sync will catch them on next reconnect)

Expose `SyncClient.delta_sync(peer_url: str, peer_device_id: str)` and `SyncClient.live_push(record: dict)`.

---

### Task 9 — Wire SyncService into app startup
Create `src/core/sync/service.py` with a `SyncService` singleton that owns `DiscoveryService`, `SyncServer`, and `SyncClient`.

- `SyncService.start()`: starts the HTTP server thread and the mDNS discovery service
- `SyncService.stop()`: graceful shutdown of both

Call `SyncService.start()` from `initialize_database()` in `src/core/db.py` after migrations run (so the DB schema is ready before the server accepts connections).

Also add `flask` and `zeroconf` to the project's dependency list (requirements.txt or pyproject.toml, whichever is used).
