# Feature 03: ICAL Support

## Goal

Allow the user to register one or more local `.ics` files (e.g. national holidays,
personal calendars exported from macOS Calendar, Google Calendar, etc.) and display
their events as distinct visual markers on the Calendar page.

---

## Scope

- **Local files only** for the initial implementation (no URL fetching).
- Events are read-only — no editing or creating ICAL events from within the app.
- Events appear on the `CalendarPage` calendar grid alongside task dots.
- ICAL source management lives in the Settings page.

---

## New Model: `ICalSource`

Location: `src/core/ical/source.py`

```
ICalSource
  id           UUIDField (PK)
  name         CharField         # display name, e.g. "Japanese Holidays"
  path         TextField         # absolute path to the .ics file
  color        CharField         # CSS color string, e.g. "rgb(180, 100, 120)"
  enabled      BooleanField      # whether to show this source on the calendar
  created_at   DateTimeField
  updated_at   DateTimeField
  device_id    CharField
  deleted_at   DateTimeField (null)
```

`ICalSource` is a syncable model: when the user adds a source on device A, device B
will create the same row. The `.ics` file itself is not synced — the path must exist
on each device. This is acceptable for the common case of system-provided holiday
calendars (same path across macOS devices).

---

## New Service: `ICalService`

Location: `src/core/ical/service.py`

```python
class ICalService:
    @classmethod
    def get_sources(cls) -> list[ICalSource]:
        """Return all non-deleted, enabled ICalSource rows."""

    @classmethod
    def add_source(cls, name: str, path: str, color: str) -> ICalSource:
        """Create and live-push a new ICalSource."""

    @classmethod
    def remove_source(cls, source: ICalSource) -> None:
        """Soft-delete (set deleted_at) and live-push."""

    @classmethod
    def get_events_in_range(
        cls,
        start: datetime,
        end: datetime,
    ) -> list[ICalEvent]:
        """
        Parse all enabled sources and return events overlapping [start, end].
        Results are cached per source file's mtime to avoid re-parsing on every
        calendar navigation.
        """
```

### `ICalEvent` (dataclass, no DB)

```python
@dataclass
class ICalEvent:
    title: str
    start: date      # date or datetime; all-day events use date
    end: date
    color: str       # inherited from its ICalSource
    source_name: str
```

### Parser

Use the `icalendar` library (already a standard Python library dependency or trivially
pip-installable). Iterate `cal.walk('VEVENT')`, extract `DTSTART`, `DTEND`/`DURATION`,
and `SUMMARY`. Handle all-day events (`date` not `datetime`) and recurring events
(`RRULE`) using the `recurring_ical_events` package.

If a source file does not exist or fails to parse, log a warning and continue — do not
crash the calendar.

---

## Migration

File: `src/core/migrations/016_add_ical_sources_table.py`

Creates the `ical_source` table.

---

## Sync Integration

`ICalSource` is registered in `get_model_registry()` in `sync/merge.py`.

`ICalService.add_source()` and `remove_source()` both call `SyncClient.live_push()`
after the DB write, identical to the pattern used by `NoteService`.

---

## Calendar Page Integration

`CalendarPage._load_tasks()` is extended to also call
`ICalService.get_events_in_range(start_date, end_date)` when
`SettingsService.get('calendar.ical_sources_visible', True)` is true.

ICAL events are merged into `tasks_by_date` under a distinct key so
`TaskCalendarWidget` can render them differently (different dot shape or color).

### Visual Differentiation

- Task dots: existing filled circles in the accent color.
- ICAL event dots: smaller square or diamond in the source's color, rendered below task dots.
- The popup (`TaskPopup`) shows ICAL events for the selected day in a separate section
  with an italic label "Events" and the event title + source name.

---

## Settings Page Integration

In the rebuilt Settings page (Feature 01), under a new **Calendar** group:

- **ICAL Sources** section listing each source (name, path, color swatch, enabled toggle,
  remove button).
- **Add Source** button opens a `QFileDialog` filtered to `*.ics` files; prompts for a
  display name and color; calls `ICalService.add_source()`.
- **Show ICAL events on calendar** toggle — writes `SettingsService.set('calendar.ical_sources_visible', ...)`.

---

## Dependencies

- `icalendar` — pure-Python ICS parser (add to `requirements.txt` / pip install).
- `recurring_ical_events` — handles `RRULE` expansion (same).

---

## Implementation Steps

1. `pip install icalendar recurring_ical_events`; add to `requirements.txt`.
2. Create `src/core/ical/` package (`__init__.py`, `source.py`, `service.py`).
3. Write migration `016_add_ical_sources_table.py`.
4. Register `ICalSource` in `sync/merge.py`.
5. Extend `CalendarPage._load_tasks()` to fetch and merge ICAL events.
6. Extend `TaskPopup.set_tasks()` to render an ICAL events section.
7. Extend `TaskCalendarWidget` to render ICAL dots distinctly.
8. Add ICAL source management UI to `SettingsPage`.
