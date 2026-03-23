from .manager import ThemeManager


def current_theme():
    return ThemeManager.get_instance().current


__all__ = ['ThemeManager', 'current_theme']
