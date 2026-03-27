from .manager import ThemeManager
from .themed_widget import ThemedWidget


def current_theme():
    return ThemeManager.get_instance().current


__all__ = ['ThemeManager', 'ThemedWidget', 'current_theme']
