import json
from datetime import datetime
from typing import Any

from PyQt6.QtCore import QObject, pyqtSignal

from core.config import get_device_id


class _SettingsSignals(QObject):
    changed = pyqtSignal(str, object)  # key, value


_signals = _SettingsSignals()


DEFAULTS = {
    'theme.active': 'wood',
    'sounds.enabled': True,
    'window.opacity': 1.0,
    'calendar.ical_sources_visible': True,
    'reminders.enabled': True,
    'reminders.global_window_enabled': False,
    'reminders.global_window_start_minute': 0,
    'reminders.global_window_end_minute': 1440,
    'reminders.show_habit_linked_on_page': False,
    'session.timeout_seconds': 1800,
    'session.min_duration_seconds': 0,
    'session.idle_nudge_seconds': 0,
}


class SettingsService:
    """Read/write app settings with automatic sync propagation."""

    signals = _signals

    @classmethod
    def get(cls, key: str, default: Any = None) -> Any:
        from core.settings.setting import AppSetting
        try:
            row = AppSetting.get(AppSetting.key == key)
            return json.loads(row.value)
        except AppSetting.DoesNotExist:
            if default is None:
                return DEFAULTS.get(key)
            return default

    @classmethod
    def set(cls, key: str, value: Any) -> None:
        from core.settings.setting import AppSetting
        from core.sync.merge import live_push_instance
        encoded = json.dumps(value)
        now = datetime.now()
        device_id = get_device_id()

        row, created = AppSetting.get_or_create(
            key=key,
            defaults={'value': encoded, 'device_id': device_id},
        )
        if not created:
            row.value = encoded
            row.updated_at = now
            row.device_id = device_id
            row.save()

        live_push_instance(row, 'appsetting')
        _signals.changed.emit(key, value)

    @classmethod
    def get_all(cls) -> dict:
        from core.settings.setting import AppSetting
        result = dict(DEFAULTS)
        for row in AppSetting.select().where(AppSetting.deleted_at.is_null()):
            result[row.key] = json.loads(row.value)
        return result
