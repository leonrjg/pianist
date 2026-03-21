"""
Theme Styles - Dynamic stylesheet helpers for themed widgets.

Replaces vintage_styles.py. All functions read from the active ThemeManager
instead of returning hardcoded vintage strings.
"""


def get_menu_stylesheet() -> str:
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current.menu_stylesheet


def get_scrollbar_stylesheet() -> str:
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current.scrollbar_stylesheet
