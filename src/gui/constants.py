"""
Constants for the Piano GUI application.
All magic numbers, colors, and configuration values are centralized here.
"""

from PyQt6.QtGui import QColor


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
    MIN_WINDOW_WIDTH = TOGGLEABLE_DRAWER_WIDTH + FALLBOARD_WIDTH + MIN_KEYS_WIDTH + CONTROL_PANEL_WIDTH
    MIN_WINDOW_HEIGHT = 160

    # Keys
    KEY_HEIGHT = 40  # Height of each piano key
    BLACK_KEY_WIDTH_RATIO = 0.5  # Black key width as ratio of white key width
    BLACK_KEY_HEIGHT_RATIO = 0.5  # Black key height as ratio of white key height

    # Padding
    FRAME_PADDING_VERTICAL = 60  # Top and bottom padding
    TOGGLEABLE_DRAWER_PADDING_VERTICAL = 10  # Padding around toggleable drawer

    # Brass elements
    BRASS_HINGE_SIZE = 8
    BRASS_HINGE_TOP_Y = 50
    BRASS_HINGE_BOTTOM_OFFSET = 50  # From bottom

    # Pedals (decorative on right side)
    PEDAL_SIZE = 10
    PEDAL_SPACING = 25
    PEDAL_X_OFFSET = 25  # From right edge

    # Window controls
    CONTROL_BUTTON_SIZE = 16
    CONTROL_BUTTON_CLOSE_Y = 20
    CONTROL_BUTTON_REORDER_Y = 44
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
    """Color scheme for piano interface"""

    # Piano keys
    WHITE_KEY = QColor(253, 252, 248)
    WHITE_KEY_PRESSED = QColor(245, 243, 237)
    WHITE_KEY_SHADOW = QColor(232, 230, 224)
    BLACK_KEY = QColor(20, 20, 18)
    BLACK_KEY_SHINE = QColor(55, 55, 50)
    BLACK_KEY_TEXT = QColor(180, 180, 180)
    KEY_GAP = QColor(26, 26, 26)

    # Wood frame
    WOOD_DARK = QColor(61, 40, 23)
    WOOD_MEDIUM = QColor(92, 61, 46)
    WOOD_LIGHT = QColor(122, 80, 64)
    WOOD_HIGHLIGHT = QColor(141, 95, 74)

    # Brass elements
    BRASS = QColor(184, 134, 11)
    BRASS_LIGHT = QColor(218, 165, 32)

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
    }


class Session:
    """Session management constants"""

    # Update frequency
    TIME_UPDATE_INTERVAL = 1000  # milliseconds (1 second)

    # Process management
    PROCESS_CLEANUP_TIMEOUT = 3000  # milliseconds
    PROCESS_MONITOR_INTERVAL = 100  # milliseconds
