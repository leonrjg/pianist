"""
ICalCalendarLoader - Feeds iCal events into any TaskCalendarWidget.

Attach one instance to a TaskCalendarWidget to keep its iCal indicators
up to date as the user navigates months. Lifetime is tied to the calendar
widget via Qt parent ownership.
"""
import logging
from datetime import datetime, timedelta
from PyQt6.QtCore import QDate, QObject

logger = logging.getLogger(__name__)

_BUFFER_DAYS = 60


class ICalCalendarLoader(QObject):
    """Loads iCal events for the visible month window and pushes them to a TaskCalendarWidget."""

    def __init__(self, calendar):
        super().__init__(calendar)
        self._calendar = calendar
        calendar.currentPageChanged.connect(self._reload)
        self._reload(calendar.yearShown(), calendar.monthShown())

    def _reload(self, year: int, month: int):
        try:
            from core.settings.service import SettingsService
            from core.ical.service import ICalService

            if not SettingsService.get('calendar.ical_sources_visible', True):
                self._calendar.set_ical_events({})
                return

            center = datetime(year, month, 15)
            start = center - timedelta(days=_BUFFER_DAYS)
            end = center + timedelta(days=_BUFFER_DAYS)

            ical_by_date = {}
            for event in ICalService.get_events_in_range(start, end):
                d = event.start
                while d <= event.end:
                    qd = QDate(d.year, d.month, d.day)
                    if qd not in ical_by_date:
                        ical_by_date[qd] = []
                    ical_by_date[qd].append(event)
                    d += timedelta(days=1)

            self._calendar.set_ical_events(ical_by_date)
        except Exception:
            logger.exception("Failed to load iCal events for calendar")
