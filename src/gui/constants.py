"""
Constants for the Piano GUI application.
All magic numbers, colors, and configuration values are centralized here.
"""

from PyQt6.QtGui import QColor


class PianoLayout:
    """Layout dimensions and positioning constants"""

    # Frame dimensions
    FRAME_WIDTH_EXTENDED = 90  # Full width with fallboard
    FALLBOARD_WIDTH = 25  # Width of the fallboard panel
    HINGE_OFFSET = 65  # Position where hinges attach (FRAME_WIDTH_EXTENDED - FALLBOARD_WIDTH)

    # Window dimensions
    DEFAULT_WINDOW_WIDTH = 280
    DEFAULT_WINDOW_HEIGHT = 315
    MIN_WINDOW_WIDTH = 250
    MIN_WINDOW_HEIGHT = 200

    # Keys
    KEY_HEIGHT = 40  # Height of each piano key
    KEYS_START_X_EXTENDED = 95  # Left edge of keys when fallboard visible
    KEYS_START_X_RETRACTED = 70  # Left edge of keys when fallboard hidden (95 - 25)
    BLACK_KEY_WIDTH_RATIO = 0.45  # Black key width as ratio of white key width
    BLACK_KEY_HEIGHT_RATIO = 0.5  # Black key height as ratio of white key height

    # Right frame and controls
    RIGHT_FRAME_WIDTH = 40

    # Keybed (black strip between frame and keys)
    KEYBED_WIDTH = 5

    # Padding
    FRAME_PADDING_VERTICAL = 60  # Top and bottom padding
    FALLBOARD_PADDING_VERTICAL = 10  # Padding around fallboard

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
    CONTROL_BUTTON_MINIMIZE_Y = 40
    CONTROL_BUTTON_CLICK_RADIUS = 10  # Click detection radius
    CONTROL_X_OFFSET = 40  # From right edge

    # Scroll indicators
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
    BLACK_KEY = QColor(26, 25, 22)
    BLACK_KEY_SHINE = QColor(42, 41, 37)
    BLACK_KEY_TEXT = QColor(180, 180, 180)
    KEY_GAP = QColor(26, 26, 26)

    # Wood frame
    WOOD_DARK = QColor(61, 40, 23)
    WOOD_MEDIUM = QColor(92, 61, 46)
    WOOD_LIGHT = QColor(122, 80, 64)
    WOOD_HIGHLIGHT = QColor(141, 95, 74)

    # Fallboard
    FALLBOARD = QColor(44, 24, 16)

    # Brass elements
    BRASS = QColor(184, 134, 11)
    BRASS_LIGHT = QColor(218, 165, 32)

    # Text
    TEXT_PRIMARY = QColor(74, 74, 74)

    # Keybed
    KEYBED = QColor(10, 10, 10)

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
    WINDOW_OPACITY_NORMAL = 0.97
    WINDOW_OPACITY_HIDDEN = 0.0


class Interactions:
    """User interaction constants"""

    # Dragging
    DRAG_THRESHOLD = 5  # Minimum pixels to consider it a drag

    # Double-click
    DOUBLE_CLICK_THRESHOLD = 200  # milliseconds
    DOUBLE_CLICK_HIDE_DURATION = 5  # seconds to hide window

    # Click detection zones (radii/tolerances)
    CONTROL_BUTTON_CLICK_RADIUS = 10
    HINGE_CLICK_TOLERANCE = 8  # Padding around hinge for click detection


class Audio:
    """Sound effect configuration"""

    SOUND_FILES = {
        'start': "gui/sounds/play.wav",
        'end': "gui/sounds/stop.wav"
    }


class Session:
    """Session management constants"""

    # Update frequency
    TIME_UPDATE_INTERVAL = 1000  # milliseconds (1 second)

    # Process management
    PROCESS_CLEANUP_TIMEOUT = 3000  # milliseconds
    PROCESS_MONITOR_INTERVAL = 100  # milliseconds
