from peewee import CharField, TextField
from core.db import SyncableModel


class AppSetting(SyncableModel):
    """
    Key/value store for user preferences that syncs across devices.

    Keys use dotted notation: 'theme.active', 'index.past_days', etc.
    Values are JSON-encoded so a single column stores strings, ints, bools, and lists.
    """
    key = CharField(unique=True)
    value = TextField()

    class Meta:
        table_name = 'appsetting'
