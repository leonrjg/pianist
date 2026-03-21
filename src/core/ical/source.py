from peewee import CharField, BooleanField
from core.db import SyncableModel


class ICalSource(SyncableModel):
    """
    A registered local .ics file to show on the calendar.

    Syncs across devices — the path is expected to exist on each device
    (e.g. system holiday calendars at the same OS path).
    """
    name = CharField()
    path = CharField()
    color = CharField(default='rgb(180, 100, 120)')
    enabled = BooleanField(default=True)

    class Meta:
        table_name = 'ical_source'
