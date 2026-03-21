# Cross-Feature Shared Structure Analysis

## Summary

After analyzing all four features against the existing codebase, two strong structural
commonalities emerge that justify a shared base before individual feature work begins.

---

## 1. The Syncable Model Pattern

Every persistent entity in the codebase that participates in cross-device sync carries
identical boilerplate fields:

```python
id         = UUIDField(primary_key=True, default=uuid.uuid4)
created_at = DateTimeField(default=datetime.now)
updated_at = DateTimeField(default=datetime.now)
device_id  = CharField(default='')
deleted_at = DateTimeField(null=True)
```

This pattern is repeated verbatim in: `Habit`, `Log`, `Note`, `Reminder`, `ReminderLog`,
`Mood`, `MoodLog`, `ManualTask`.

Features 01 and 03 each introduce a new syncable model (`AppSetting`, `ICalSource`).
Without a shared base, that is two more copies.

### Solution: `SyncableModel` in `core/db.py`

```python
class SyncableModel(BaseModel):
    id         = UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)
    device_id  = CharField(default='')
    deleted_at = DateTimeField(null=True)
```

New models (`AppSetting`, `ICalSource`) extend `SyncableModel` instead of `BaseModel`.

**Existing models are not migrated in this pass** — doing so would require verifying
all their existing migrations still apply correctly. They continue to use `BaseModel`
with manually declared fields. Only net-new models use `SyncableModel`.

### Each syncable model also needs (invariant, not encapsulated in base class):

- A migration file in `core/migrations/`.
- Registration in `get_model_registry()` in `core/sync/merge.py`.
- A `live_push()` call in its service after every write.

---

## 2. Settings as the Shared Runtime Configuration Layer

Features 01, 02, 03, and 04 all depend on `SettingsService`:

| Feature | Settings key consumed |
|---------|----------------------|
| 01 (Settings) | *produces* all keys |
| 02 (Themes) | `theme.active` |
| 03 (ICAL) | `calendar.ical_sources_visible` |
| 04 (Past tasks) | `index.past_days` |

This creates a hard dependency ordering: **Feature 01 must be implemented first**.
Features 02, 03, and 04 must not hardcode fallback logic that duplicates what
`SettingsService` will provide — they must call `SettingsService.get(KEY, DEFAULT)`
and rely on the default.

---

## 3. Theme System as Shared UI Infrastructure

Feature 02 (Themes) is not just a feature — it is a prerequisite refactor for the UI
code used by Features 03 and 04:

- The ICAL event dots in `CalendarPage` (Feature 03) need themed colors for dot
  rendering and popup sections.
- The past-tasks section in `IndexPage` (Feature 04) uses day headers and urgency
  colors that should come from the active theme.
- The rebuilt `SettingsPage` (Feature 01) itself must render correctly in both themes.

Therefore the recommended implementation order is:

```
Feature 01 (Settings model + service + page skeleton)
  └── Feature 02 (Themes — depends on settings for active theme key)
        └── Feature 03 (ICAL — uses themed calendar rendering)
        └── Feature 04 (Past tasks — uses themed index rendering)
```

Features 03 and 04 can proceed in parallel after Feature 02 is done.

---

## 4. The Live-Push Contract

Every service that writes a syncable record must call `SyncClient.live_push()` after
the DB write. This is already the expected contract but is not formally documented or
enforced. The pattern across all four features:

```python
from core.sync.merge import serialize_row
from core.sync.service import SyncService

def _live_push(instance, table_name: str) -> None:
    record = serialize_row(instance, table_name)
    SyncService.get_instance().client.live_push(record)
```

Rather than copy-pasting this snippet into every new service, a helper should live in
`core/sync/merge.py` (or a small `core/sync/helpers.py`):

```python
def live_push_instance(instance, table_name: str) -> None:
    record = serialize_row(instance, table_name)
    from core.sync.service import SyncService
    SyncService.get_instance().client.live_push(record)
```

Both `SettingsService` (Feature 01) and `ICalService` (Feature 03) use this helper.

---

## Implementation Checklist for Shared Infrastructure

Before any feature code, complete these two items:

1. **Add `SyncableModel` to `core/db.py`** — one-line addition after `BaseModel`;
   no migration needed since no existing table changes.

2. **Add `live_push_instance()` to `core/sync/merge.py`** — avoids duplicated push
   boilerplate in every new service.

These two additions unblock all four features and reduce their per-feature boilerplate.

---

## Dependency Graph

```
[SyncableModel + live_push_instance]   <- shared prereqs
         |
         v
[Feature 01: Settings]
         |
         v
[Feature 02: Themes]
         |
    _____|_____
   |           |
   v           v
[Feature 03]  [Feature 04]
(ICAL)       (Past tasks)
```
