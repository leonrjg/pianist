# Feature 01: Rich Settings

## Goal

Replace the stub `SettingsPage` with a real, functional settings system. Gather all
configurable values currently hardcoded across the codebase and expose them through a
key/value store that participates in cross-device sync.

---

## Current State

- `settings_page.py` is a stub displaying static "etc" text and a CSV export link.
- Configurable values are scattered as hardcoded constants:
  - `constants.py`: `PianoLayout.*`, `Animations.*`, `Interactions.*`, `Audio.SOUND_FILES`
  - `base_page.py`: inline stylesheet color strings
  - `index_page.py`: `timespan = 30 * 24 * 60 * 60` (30-day lookback), urgency color thresholds
  - `db.py`: db path
  - `auto_session_manager.py`, `sound_manager.py`: various intervals/toggles
- No persistence mechanism for user preferences.

---

## New Model: `AppSetting`

Location: `src/core/settings/setting.py`

```
AppSetting
  id           UUIDField (PK)
  key          CharField (unique)
  value        TextField         # JSON-encoded value
  created_at   DateTimeField
  updated_at   DateTimeField
  device_id    CharField
  deleted_at   DateTimeField (null)
```

The `key` namespace uses dotted notation: `theme.active`, `index.past_days`,
`sounds.enabled`, `window.opacity`, etc.

Values are JSON-encoded so a single field holds strings, ints, booleans, and lists.

---

## New Service: `SettingsService`

Location: `src/core/settings/service.py`

Responsibilities:
- `get(key, default)` — read + JSON-decode value, return default if missing.
- `set(key, value)` — JSON-encode, upsert the row, update `updated_at`, set
  `device_id`, then call `SyncClient.live_push()` for the record.
- `get_all()` — return all non-deleted settings.

The service is stateless (class methods), mirroring the pattern used by `TaskService`,
`NoteService`, etc.

---

## Settings to Expose (initial set)

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `theme.active` | str | `"vintage"` | Active UI theme name |
| `index.past_days` | int | `0` | How many past days to show on index page |
| `index.future_days` | int | `30` | How many future days to look ahead |
| `sounds.enabled` | bool | `true` | Whether sound effects play |
| `window.opacity` | float | `1.0` | Global window opacity |
| `calendar.ical_sources_visible` | bool | `true` | Show ICAL events on calendar |
| `reminders.enabled` | bool | `true` | Global on/off for reminders |

This list is extensible; adding a new setting requires only a constant key string and
a default in the service — no schema change.

---

## Migration

File: `src/core/migrations/015_add_settings_table.py`

Creates the `appsetting` table with the same syncable schema as other models.

---

## Sync Integration

`AppSetting` must be added to `get_model_registry()` in `sync/merge.py`.

On every `SettingsService.set()` call, `SyncClient.live_push()` propagates the new
value to all connected peers immediately. On a full delta sync, changed settings are
merged with LWW (last-write-wins on `updated_at`), same as all other models.

Conflict note: if two devices write different themes simultaneously, LWW picks the one
with the later `updated_at`. This is intentional — settings are user-scoped preferences
and the probability of a conflict worth resolving differently is negligible.

---

## Settings Page Rebuild

The rebuilt `SettingsPage` renders controls grouped by category. Each control reads
its current value from `SettingsService.get()` and calls `SettingsService.set()` on
change.

Groups:
1. **Appearance** — theme selector (dropdown), window opacity (slider or spin box)
2. **Index page** — past days (spin box), future days (spin box)
3. **Sounds** — enabled toggle
4. **Reminders** — global enabled toggle
5. **Calendar** — ICAL sources list (links to per-source toggle), ICAL visibility toggle
6. **Export** — existing CSV link (keep)

All controls use the existing `VintageButton`, `VintageDropdown`, and
`vintage_form_widgets` components so they inherit theme styling automatically.

---

## Implementation Steps

1. Create `src/core/settings/` package (`__init__.py`, `setting.py`, `service.py`).
2. Write migration `015_add_settings_table.py`.
3. Register `AppSetting` in `sync/merge.py`.
4. Rebuild `settings_page.py` with the grouped controls described above.
5. Replace each hardcoded configurable value at its call site with a
   `SettingsService.get(KEY, DEFAULT)` call (starting with the keys listed in the
   table above; leave deeper constants like `PianoLayout` dimensions for a later pass).
