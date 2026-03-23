"""
Constants for the Piano GUI application.
All magic numbers, colors, and configuration values are centralized here.
"""

from PyQt6.QtGui import QColor
from gui.themes.color import parse_color as _parse_rgb


def make_font(family: str, pt: int, weight=None) -> 'QFont':
    """Create a QFont with platform-normalised point size and rendering hints.

    Equivalent to QFont(family, pt[, weight]) but applies font_pt() scaling and,
    on Windows, PreferNoHinting so the font matches the app-level rendering style
    (QFont(family, pt) constructs from scratch and does not inherit the app
    font's hinting preference, unlike the no-arg QFont() constructor).
    """
    import sys
    from PyQt6.QtGui import QFont
    font = QFont(family, font_pt(pt)) if weight is None else QFont(family, font_pt(pt), weight)
    if sys.platform == 'win32':
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    return font


# Maximum bump applied on Windows at DPR=1.0 to compensate for the lower visual
# weight of 1x rendering vs Mac Retina (2x). Fades linearly to zero as DPR
# approaches 2.0, so HiDPI Windows displays get no unnecessary inflation.
_WIN_FONT_BUMP_MAX = 1.22


def font_pt(pt: int) -> int:
    """Convert a Mac-native point size to the equivalent size on the current platform.

    Qt maps point sizes to pixels using the screen's logical DPI (72 on macOS, 96 on
    Windows), so the same point value renders 33% larger on Windows. This normalises
    against macOS's 72 DPI baseline so all platforms produce the same physical size,
    then applies a DPR-proportional bump on Windows to compensate for the lower visual
    weight of sub-Retina rendering.
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        return pt
    screen = app.primaryScreen()
    dpi = screen.logicalDotsPerInch()
    scaled = pt * 72 / dpi
    if sys.platform == 'win32':
        dpr = screen.devicePixelRatio()
        bump = 1.0 + (_WIN_FONT_BUMP_MAX - 1.0) * max(0.0, min(1.0, 2.0 - dpr))
        scaled *= bump
    return max(6, round(scaled))


_piano_colors_cache: tuple = (None, None)  # (theme, colors_class)


def piano_colors():
    """Return a theme-aware PianoColors-compatible object."""
    global _piano_colors_cache
    try:
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        if _piano_colors_cache[0] is t:
            return _piano_colors_cache[1]

        class _Colors:
            WHITE_KEY = _parse_rgb(t.white_key)
            WHITE_KEY_PRESSED = _parse_rgb(t.white_key).darker(108)
            WHITE_KEY_SHADOW = _parse_rgb(t.white_key).darker(115)
            BLACK_KEY = _parse_rgb(t.black_key)
            BLACK_KEY_SHINE = _parse_rgb(t.black_key).lighter(160)
            BLACK_KEY_TEXT = _parse_rgb(t.black_key_text_color)
            FRAME_DARK = _parse_rgb(t.frame_dark)
            FRAME_MEDIUM = _parse_rgb(t.frame_medium)
            FRAME_LIGHT = _parse_rgb(t.frame_light)
            FRAME_HIGHLIGHT = _parse_rgb(t.frame_light).lighter(110)
            ACCENT = _parse_rgb(t.accent)
            ACCENT_LIGHT = _parse_rgb(t.accent_light)
            TEXT_PRIMARY = _parse_rgb(t.key_label_color)
            BACKGROUND = _parse_rgb(t.frame_dark).darker(130)

        _piano_colors_cache = (t, _Colors)
        return _Colors
    except Exception:
        return PianoColors


class PianoLayout:
    """Layout dimensions and positioning constants"""

    # ===== Component Widths (the values you actually want to change) =====
    TOGGLEABLE_DRAWER_WIDTH = 275  # Width of the toggleable drawer panel (music sheet panel)
    FALLBOARD_WIDTH = 30  # Width of the fallboard (narrow brown indicator panel)
    CONTROL_PANEL_WIDTH = 35  # Width of the control panel (right side)

    # ===== Derived/Computed Values (don't change these directly) =====
    # The hinge is positioned at the right edge of the toggleable drawer
    HINGE_OFFSET = TOGGLEABLE_DRAWER_WIDTH

    # Window dimensions
    DEFAULT_WINDOW_WIDTH = 300  # Default width (can be larger than minimum)
    DEFAULT_WINDOW_HEIGHT = 315
    MIN_KEYS_WIDTH = 90
    MIN_WINDOW_WIDTH = int(3 * (FALLBOARD_WIDTH + MIN_KEYS_WIDTH + CONTROL_PANEL_WIDTH))
    MIN_WINDOW_HEIGHT = 160

    # Keys
    KEY_HEIGHT = 40  # Height of each piano key
    BLACK_KEY_WIDTH_RATIO = 0.55  # Black key width as ratio of white key width
    BLACK_KEY_HEIGHT_RATIO = 0.5  # Black key height as ratio of white key height

    # Padding
    FRAME_PADDING_VERTICAL = 60  # Top and bottom padding
    TOGGLEABLE_DRAWER_PADDING_VERTICAL = 10  # Padding around toggleable drawer

    # Hinge elements
    HINGE_SIZE = 8
    HINGE_TOP_Y = 50
    HINGE_BOTTOM_OFFSET = 50  # From bottom

    # Pedals (decorative on right side)
    PEDAL_SIZE = 10
    PEDAL_SPACING = 25
    PEDAL_X_OFFSET = 25  # From right edge

    # Window controls
    CONTROL_BUTTON_SIZE = 16
    CONTROL_BUTTON_CLOSE_Y = 20
    CONTROL_BUTTON_REORDER_Y = 44
    CONTROL_BUTTON_MOOD_Y = 68
    CONTROL_BUTTON_CLICK_RADIUS = 10  # Click detection radius
    CONTROL_X_OFFSET = 40  # From right edge

    # Window appearance
    WINDOW_BORDER_RADIUS = 6  # Rounded corner radius

    # Fallboard (narrow brown panel with indicator dots)
    FALLBOARD_DOT_SIZE = 8  # Size of indicator dots on fallboard
    SCROLL_INDICATOR_X = 15
    SCROLL_TRACK_WIDTH = 4
    SCROLL_TRACK_PADDING = 20
    SCROLL_THUMB_MIN_HEIGHT = 8
    SCROLL_ARROW_SIZE = 6


class PianoColors:
    """Fallback color scheme (wood defaults) for piano interface"""

    # Piano keys
    WHITE_KEY = QColor(253, 252, 248)
    WHITE_KEY_PRESSED = QColor(245, 243, 237)
    WHITE_KEY_SHADOW = QColor(232, 230, 224)
    BLACK_KEY = QColor(48, 48, 44)
    BLACK_KEY_SHINE = QColor(80, 80, 74)
    BLACK_KEY_TEXT = QColor(180, 180, 180)

    # Frame
    FRAME_DARK = QColor(61, 40, 23)
    FRAME_MEDIUM = QColor(92, 61, 46)
    FRAME_LIGHT = QColor(122, 80, 64)
    FRAME_HIGHLIGHT = QColor(141, 95, 74)

    # Accent elements
    ACCENT = QColor(184, 134, 11)
    ACCENT_LIGHT = QColor(218, 165, 32)

    # Text
    TEXT_PRIMARY = QColor(74, 74, 74)

    # Background
    BACKGROUND = QColor(26, 26, 26)


class Animations:
    """Animation timing and behavior constants"""

    # Durations (milliseconds)
    FADE_DURATION = 300
    FALLBOARD_SLIDE_DURATION = 300
    KEY_PRESS_DURATION = 400

    # Easing curves (use QEasingCurve.Type enum)
    FADE_EASING = "InOutQuad"
    SLIDE_EASING = "InOutQuad"

    # Opacity values
    WINDOW_OPACITY_NORMAL = 1
    WINDOW_OPACITY_HIDDEN = 0.0

    # Reorder mode animations
    PULSE_INTERVAL = 250 # milliseconds between pulse updates
    PULSE_MIN_SCALE = 0.99  # Minimum scale (98%)
    PULSE_MAX_SCALE = 1.005  # Maximum scale (102%)
    PULSE_SPEED = 0.02  # Speed of scale change per interval
    KEY_DRAG_OPACITY = 0.6  # Opacity of dragged key during reorder


class Interactions:
    """User interaction constants"""

    # Dragging
    DRAG_THRESHOLD = 5  # Minimum pixels to consider it a drag
    CLICK_TOLERANCE = 5  # Maximum distance between press and release for a click
    KEY_REORDER_THRESHOLD = 8  # Minimum vertical pixels to start key reorder

    # Double-click
    DOUBLE_CLICK_THRESHOLD = 200  # milliseconds
    DOUBLE_CLICK_HIDE_DURATION = 5  # seconds to hide window

    # Click detection zones (radii/tolerances)
    CONTROL_BUTTON_CLICK_RADIUS = 10
    HINGE_CLICK_TOLERANCE = 8  # Padding around hinge for click detection
    PEDAL_CLICK_RADIUS = 12  # Click detection radius for pedals

    # Resize detection zones
    RESIZE_EDGE_THRESHOLD = 8  # Pixels from edge for straight edge resizing
    RESIZE_CORNER_THRESHOLD = 20  # Pixels from corner for diagonal resizing


class Audio:
    """Sound effect configuration"""

    SOUND_FILES = {
        'start': "gui/sounds/play.wav",
        'end': "gui/sounds/stop.wav",
        'drawer': "gui/sounds/drawer.wav",
        'page': "gui/sounds/page.wav",
        'thunk': "gui/sounds/thunk.wav",
        'notification': "gui/sounds/notification.wav",
    }


class Session:
    """Session management constants"""

    # Update frequency
    TIME_UPDATE_INTERVAL = 1000  # milliseconds (1 second)

    # Process management
    PROCESS_CLEANUP_TIMEOUT = 3000  # milliseconds
    PROCESS_MONITOR_INTERVAL = 100  # milliseconds
