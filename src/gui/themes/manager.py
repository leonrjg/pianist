from .theme import Theme
from .wood import VINTAGE_THEME
from .sakura import SAKURA_THEME
from .midori import MIDORI_THEME

_REGISTRY: dict[str, Theme] = {
    'wood': VINTAGE_THEME,
    'sakura': SAKURA_THEME,
    'midori': MIDORI_THEME,
}


class ThemeManager:
    _instance: 'ThemeManager | None' = None

    @classmethod
    def get_instance(cls) -> 'ThemeManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def current(self) -> Theme:
        try:
            from core.settings.service import SettingsService
            name = SettingsService.get('theme.active', 'wood')
        except Exception:
            name = 'wood'
        return _REGISTRY.get(name, VINTAGE_THEME)

    def apply(self, app) -> None:
        """
        Signal all open SheetPages and the piano window to re-apply the active theme.
        Called after the user changes the theme in settings.
        """
        if app is None:
            return
        for widget in app.allWidgets():
            if hasattr(widget, '_setup_style') and callable(widget._setup_style):
                widget._setup_style()
                widget.update()
            if hasattr(widget, 'refresh') and callable(widget.refresh):
                try:
                    widget.refresh()
                except Exception:
                    pass
