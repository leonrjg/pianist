import logging
import os
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List

logger = logging.getLogger(__name__)

# Cache: path -> (mtime, events_list)
_cache: dict[str, tuple[float, list]] = {}


@dataclass
class ICalEvent:
    title: str
    start: date
    end: date
    color: str
    source_name: str


class ICalService:

    @classmethod
    def get_sources(cls):
        from core.ical.source import ICalSource
        return list(ICalSource.select().where(
            ICalSource.deleted_at.is_null() & (ICalSource.enabled == True)
        ))

    @classmethod
    def add_source(cls, name: str, path: str, color: str = 'rgb(180, 100, 120)'):
        from core.ical.source import ICalSource
        from core.sync.merge import live_push_instance
        from datetime import datetime
        from core.config import get_device_id
        source = ICalSource.create(
            name=name,
            path=path,
            color=color,
            enabled=True,
            device_id=get_device_id(),
        )
        live_push_instance(source, 'ical_source')
        return source

    @classmethod
    def remove_source(cls, source) -> None:
        from core.sync.merge import live_push_instance
        source.deleted_at = datetime.now()
        source.updated_at = datetime.now()
        source.save()
        live_push_instance(source, 'ical_source')

    @classmethod
    def get_events_in_range(cls, start: datetime, end: datetime) -> List[ICalEvent]:
        events: List[ICalEvent] = []
        for source in cls.get_sources():
            events.extend(cls._load_source(source, start, end))
        return events

    @classmethod
    def _load_source(cls, source, start: datetime, end: datetime) -> List[ICalEvent]:
        path = source.path
        if not os.path.exists(path):
            logger.warning("ICAL source file not found: %s", path)
            return []

        try:
            mtime = os.path.getmtime(path)
            cached_mtime, cached_events = _cache.get(path, (None, None))
            if cached_mtime == mtime and cached_events is not None:
                all_events = cached_events
            else:
                all_events = cls._parse_file(path, source.name, source.color)
                _cache[path] = (mtime, all_events)

            start_d = start.date() if isinstance(start, datetime) else start
            end_d = end.date() if isinstance(end, datetime) else end
            return [e for e in all_events if e.end >= start_d and e.start <= end_d]
        except Exception:
            logger.exception("Failed to load ICAL source: %s", path)
            return []

    @classmethod
    def _parse_file(cls, path: str, source_name: str, color: str) -> List[ICalEvent]:
        import icalendar
        import recurring_ical_events

        with open(path, 'rb') as f:
            cal = icalendar.Calendar.from_ical(f.read())

        # Fetch a broad window so the cache covers typical navigation
        window_start = datetime.now().replace(year=datetime.now().year - 1)
        window_end = datetime.now().replace(year=datetime.now().year + 2)

        try:
            occurrences = recurring_ical_events.of(cal).between(window_start, window_end)
        except Exception:
            logger.exception("recurring_ical_events failed for %s; falling back to flat walk", path)
            occurrences = [c for c in cal.walk() if c.name == 'VEVENT']

        events = []
        for component in occurrences:
            summary = str(component.get('SUMMARY', ''))
            dtstart = component.get('DTSTART')
            dtend = component.get('DTEND')
            if dtstart is None:
                continue
            start_val = dtstart.dt
            end_val = dtend.dt if dtend else start_val

            # Normalise to date objects
            if isinstance(start_val, datetime):
                start_d = start_val.date()
            else:
                start_d = start_val
            if isinstance(end_val, datetime):
                end_d = end_val.date()
            else:
                end_d = end_val

            # icalendar DTEND for all-day events is exclusive — adjust
            if not isinstance(dtstart.dt, datetime):
                end_d = end_d - timedelta(days=1)

            events.append(ICalEvent(
                title=summary,
                start=start_d,
                end=end_d,
                color=color,
                source_name=source_name,
            ))
        return events
