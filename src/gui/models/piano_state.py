"""
Piano State Model - Manages all application state.

This model holds all mutable state for the piano interface, making it easy to:
- Track what's currently happening in the application
- Reset or save state
- Test state transitions
- Debug state-related issues
"""

from typing import Optional, Dict
from PyQt6.QtCore import QObject, pyqtSignal


class PianoState(QObject):
    """Manages all state for the piano interface"""

    # Signals emitted when state changes
    fallboard_toggled = pyqtSignal(bool)  # fallboard_visible
    key_pressed = pyqtSignal(int)  # key_index
    key_released = pyqtSignal(int)  # key_index
    scrolled = pyqtSignal(int)  # new scroll_offset
    window_resized = pyqtSignal(int, int)  # width, height

    def __init__(self):
        super().__init__()

        # ===== Fallboard State =====
        self._fallboard_visible = False

        # ===== Window State =====
        self._window_width = 0
        self._window_height = 0
        self._is_fading_out = False

        # ===== Key Press State =====
        self._pressed_key_index: Optional[int] = None  # Index of currently visually pressed key

        # ===== Scroll State =====
        self._scroll_offset = 0  # Current scroll position
        self._max_scroll_offset = 0  # Maximum possible scroll
        self._scrolling_enabled = False  # Whether scrolling is needed
        self._scroll_accumulator = 0.0  # For smooth scrolling

        # ===== Drag State =====
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

        # ===== Double-Click State =====
        self._last_click_time = 0  # For double-click detection

        # ===== Session State =====
        # Maps habit_id -> time display string (e.g., "5m 23s")
        self._time_displays: Dict[int, str] = {}

        # ===== Habit Data =====
        self._num_habits = 0  # Total number of habits loaded

    # ===== Fallboard Properties =====

    @property
    def fallboard_visible(self) -> bool:
        return self._fallboard_visible

    @fallboard_visible.setter
    def fallboard_visible(self, value: bool):
        if self._fallboard_visible != value:
            self._fallboard_visible = value
            self.fallboard_toggled.emit(value)

    def toggle_fallboard(self):
        """Toggle the drawer visibility state"""
        self.fallboard_visible = not self._fallboard_visible

    # ===== Window Properties =====

    @property
    def window_width(self) -> int:
        return self._window_width

    @property
    def window_height(self) -> int:
        return self._window_height

    def set_window_size(self, width: int, height: int):
        """Update window dimensions"""
        if self._window_width != width or self._window_height != height:
            self._window_width = width
            self._window_height = height
            self.window_resized.emit(width, height)

    @property
    def is_fading_out(self) -> bool:
        return self._is_fading_out

    @is_fading_out.setter
    def is_fading_out(self, value: bool):
        self._is_fading_out = value

    # ===== Key Press Properties =====

    @property
    def pressed_key_index(self) -> Optional[int]:
        return self._pressed_key_index

    def press_key(self, index: int):
        """Mark a key as pressed"""
        self._pressed_key_index = index
        self.key_pressed.emit(index)

    def release_key(self):
        """Release the currently pressed key"""
        if self._pressed_key_index is not None:
            released = self._pressed_key_index
            self._pressed_key_index = None
            self.key_released.emit(released)

    def is_key_pressed(self, index: int) -> bool:
        """Check if a specific key is currently pressed"""
        return self._pressed_key_index == index

    # ===== Scroll Properties =====

    @property
    def scroll_offset(self) -> int:
        return self._scroll_offset

    @scroll_offset.setter
    def scroll_offset(self, value: int):
        # Clamp to valid range
        value = max(0, min(value, self._max_scroll_offset))
        if self._scroll_offset != value:
            self._scroll_offset = value
            self.scrolled.emit(value)

    @property
    def max_scroll_offset(self) -> int:
        return self._max_scroll_offset

    @max_scroll_offset.setter
    def max_scroll_offset(self, value: int):
        self._max_scroll_offset = max(0, value)
        # Re-clamp current offset
        self.scroll_offset = self._scroll_offset

    @property
    def scrolling_enabled(self) -> bool:
        return self._scrolling_enabled

    @scrolling_enabled.setter
    def scrolling_enabled(self, value: bool):
        self._scrolling_enabled = value

    @property
    def scroll_accumulator(self) -> float:
        return self._scroll_accumulator

    @scroll_accumulator.setter
    def scroll_accumulator(self, value: float):
        self._scroll_accumulator = value

    def can_scroll_up(self) -> bool:
        """Check if can scroll up"""
        return self._scrolling_enabled and self._scroll_offset > 0

    def can_scroll_down(self) -> bool:
        """Check if can scroll down"""
        return self._scrolling_enabled and self._scroll_offset < self._max_scroll_offset

    # ===== Drag Properties =====

    @property
    def is_dragging(self) -> bool:
        return self._is_dragging

    @is_dragging.setter
    def is_dragging(self, value: bool):
        self._is_dragging = value

    def start_drag(self, x: int, y: int):
        """Start a drag operation"""
        self._drag_start_x = x
        self._drag_start_y = y
        self._is_dragging = False  # Not yet confirmed as drag

    def get_drag_start(self) -> tuple[int, int]:
        """Get drag start position"""
        return self._drag_start_x, self._drag_start_y

    def end_drag(self):
        """End drag operation"""
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0

    # ===== Double-Click Properties =====

    @property
    def last_click_time(self) -> float:
        return self._last_click_time

    @last_click_time.setter
    def last_click_time(self, value: float):
        self._last_click_time = value

    # ===== Session Properties =====

    def set_time_display(self, habit_id: int, time_text: str):
        """Set time display for a habit"""
        self._time_displays[habit_id] = time_text

    def get_time_display(self, habit_id: int) -> Optional[str]:
        """Get time display for a habit"""
        return self._time_displays.get(habit_id)

    def clear_time_display(self, habit_id: int):
        """Clear time display for a habit"""
        if habit_id in self._time_displays:
            del self._time_displays[habit_id]

    def has_active_session(self, habit_id: int) -> bool:
        """Check if habit has an active session"""
        return habit_id in self._time_displays

    # ===== Habit Data Properties =====

    @property
    def num_habits(self) -> int:
        return self._num_habits

    @num_habits.setter
    def num_habits(self, value: int):
        self._num_habits = value

    # ===== State Reset =====

    def reset(self):
        """Reset all state to initial values"""
        self._fallboard_visible = False
        self._pressed_key_index = None
        self._scroll_offset = 0
        self._max_scroll_offset = 0
        self._scrolling_enabled = False
        self._scroll_accumulator = 0.0
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._last_click_time = 0
        self._time_displays.clear()
        self._is_fading_out = False
