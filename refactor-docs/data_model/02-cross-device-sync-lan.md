## LAN Transport Design

---

### Architecture Overview

```
SyncService (singleton, background)
├── DiscoveryService     ← mDNS: finds peers automatically
├── SyncServer           ← HTTP server: serves deltas to peers
└── SyncClient           ← HTTP client: pushes to and pulls from peers
```

The app runs a lightweight HTTP server in a background thread from startup. Discovery is continuous. Sync never blocks the UI.

---

### 1. Discovery — mDNS (Zeroconf)

Each instance advertises itself on the LAN and listens for others:

```
Service type:  _pianistgui._tcp.local.
Port:          47832  (fixed, configurable)
TXT record:    {device_id, device_name, app_version}
```

**Library:** `zeroconf` (pure Python, no system daemon dependency)

**Lifecycle:**
- On startup: advertise self, start browsing for peers
- On peer found: record peer in `Device` table, trigger delta sync
- On peer lost: mark `Device.last_seen`, stop pushing (will retry on rediscovery)
- On shutdown: unregister advertisement

This is identical to how LocalSend works. Discovery is passive — no user action needed, no IP configuration.

---

### 2. HTTP Server — Sync Endpoints

Three endpoints, bound to `0.0.0.0:47832` (LAN-accessible, not internet-routable by default):

```
GET  /sync/info
GET  /sync/delta?since=<ISO-timestamp>
POST /sync/push
```

#### `GET /sync/info`
Identity handshake. Returns:
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "device_name": "Leon's MacBook",
  "app_version": "1.0.0"
}
```

#### `GET /sync/delta?since=2026-03-18T10:00:00`
Returns all records modified after `since`, including tombstones:
```json
{
  "device_id": "...",
  "generated_at": "2026-03-19T12:00:00",
  "records": [
    {"table": "habit",   "data": {"id": "uuid", "name": "Piano", "deleted_at": null, "updated_at": "...", ...}},
    {"table": "log",     "data": {"id": "uuid", "habit_id": "uuid", "start": "...", ...}},
    {"table": "mood_log","data": {"id": "uuid", "deleted_at": "2026-03-19T11:00:00", ...}}
  ]
}
```

Query: `WHERE updated_at > since` across all sync-enabled tables, including `deleted_at IS NOT NULL` records (tombstones must propagate).

#### `POST /sync/push`
Accepts the same `records` format. Used for immediate live push after a local write. The receiving end runs the same LWW merge. Returns `200 OK` or an error.

---

### 3. Sync Client — Two Modes

**Delta sync** (on peer reconnect / startup):
```
1. GET /sync/info                         ← verify identity
2. t = SyncState.last_sync_at[peer.id]    ← when did we last sync this peer?
3. GET /sync/delta?since=t                ← get their changes
4. merge(incoming_records)                ← LWW merge locally
5. POST /sync/push  ← our delta since t   ← send our changes to them
6. SyncState[peer.id].last_sync_at = now()
```

**Live push** (on every local write):
```
for each active peer:
    POST /sync/push  [{table, data}]     ← fire-and-forget, non-blocking
    (if failed: skip — delta sync on next reconnect will catch it)
```

Live push latency is typically <100ms on LAN. Failed pushes are silently deferred — the delta sync on reconnect is the safety net.

---

### 4. Merge Logic

```python
def merge_record(table: str, incoming: dict):
    existing = db_get(table, id=incoming["id"])
    
    if existing is None:
        db_insert(table, incoming)
        return
    
    if incoming["updated_at"] > existing["updated_at"]:
        db_update(table, incoming)
    elif incoming["updated_at"] == existing["updated_at"]:
        # Clock tie: deterministic tiebreaker (avoids divergence)
        if incoming["device_id"] > existing["device_id"]:
            db_update(table, incoming)
    # else: local is newer, discard
```

Deletion propagation is automatic: if `incoming["deleted_at"]` is set and wins LWW, the local record gets `deleted_at` set. All queries add `WHERE deleted_at IS NULL`.

---

### 5. Security Model

**Threat model:** single user, personal LAN. Not a shared/multi-user scenario.

- Bind server to LAN interface only (not loopback, not internet) — prevents internet exposure
- Optional **PIN pairing**: on first contact with a new device, the user sees a 4-digit PIN that must be confirmed on the other device. After pairing, the `Device` record is marked `trusted=True`. Subsequent syncs proceed automatically. Unknown devices are rejected.
- No TLS required for LAN (optional, adds complexity, minimal security benefit on a home network). Can be added later.

---

### 6. Implementation Stack

| Component | Library | Rationale |
|---|---|---|
| mDNS discovery | `zeroconf` | Pure Python, cross-platform, same as LocalSend uses |
| HTTP server | `Flask` + `threading` | Already in Python ecosystem, simple, synchronous is fine |
| HTTP client | `requests` | Already used (AnkiConnect) |
| Background execution | `threading.Thread` | Non-blocking, daemon thread so it dies with the app |

Flask runs in a daemon thread. All DB writes from incoming sync go through the same Peewee connection (use `pragmas={'journal_mode': 'WAL'}` in `SqliteDatabase` to allow concurrent reads while the sync thread writes).

---

### 7. Sync Scope — What Gets Synced

| Table | Synced | Notes |
|---|---|---|
| `Habit` | ✅ | Full LWW |
| `Log` | ✅ | Append-only, union |
| `HabitTracker` | ✅ | Full LWW |
| `ManualTask` | ✅ | Full LWW |
| `Mood` | ✅ | Full LWW |
| `MoodLog` | ✅ | Append-only, union |
| `Reminder` | ✅ | Full LWW (SR state travels with it) |
| `ReminderLog` | ✅ | Append-only, union |
| `Note` | ✅ | Full LWW |
| `Device` | ✅ | Partial — peers share their known devices (gossip) |
| `SyncState` | ❌ | Local only — each device tracks its own sync cursors |
| `Migration` | ❌ | Local only |

---

### 8. Edge Cases

**Clock skew:** If Device B's clock is 5 minutes ahead, its writes always "win" LWW even if they're older. Acceptable trade-off for general public; fixing this requires NTP checks or vector clocks (too complex). Document it as a known limitation.

**First sync (brand new device):** `SyncState` has no entry for any peer → `since` defaults to Unix epoch → full DB transfer. This is correct and safe; deduplication handles it.

**Tombstone cleanup:** Never hard-delete during active sync. Tombstones older than 180 days can be purged in a future maintenance migration — this only matters if a device is offline for >180 days, which is a non-scenario for a productivity app.

**Schema version mismatch:** Include `app_version` in `/sync/info`. If peers are on incompatible schema versions, log a warning and skip sync. Don't try to transform across versions — just wait until both devices update.

**Large initial sync:** Compress delta responses with gzip (`Content-Encoding: gzip`). On a LAN, even 10MB of JSON transfers in <1s, so this is an optimization, not a requirement.

---

### Summary

The entire sync system is: mDNS for zero-config discovery + 3 HTTP endpoints + one merge function + two local tables (`Device`, `SyncState`). No daemon, no broker, no accounts. Devices appear and disappear freely. The delta cursor (`last_sync_at`) ensures nothing is ever lost regardless of how long a device was offline.
