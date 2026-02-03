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
    toggleable_drawer_toggled = pyqtSignal(bool)  # toggleable_drawer_visible
    key_pressed = pyqtSignal(int)  # key_index
    key_released = pyqtSignal(int)  # key_index
    scrolled = pyqtSignal(int)  # new scroll_offset

    def __init__(self):
        super().__init__()

        # ===== Toggleable Drawer State =====
        self._toggleable_drawer_visible = False

        # ===== Window State =====
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
        self._press_local_x = 0  # Local (widget) coordinates of press
        self._press_local_y = 0
        self._window_was_moved = False  # Track if window actually moved during drag

        # ===== Double-Click State =====
        self._last_click_time = 0  # For double-click detection

        # ===== Session State =====
        # Maps habit_id -> time display string (e.g., "5m 23s")
        self._time_displays: Dict[int, str] = {}

        # ===== Habit Data =====
        self._num_habits = 0  # Total number of habits loaded

        # ===== Key Reorder State =====
        self._dragged_key_index: Optional[int] = None  # Index of key being dragged
        self._drag_current_y: int = 0  # Current Y position during drag
        self._drop_target_index: Optional[int] = None  # Target position for drop

        # ===== Resize State =====
        self._is_resizing = False
        self._resize_edge = None  # 'left', 'top-left', 'bottom-left'
        self._resize_start_rect = None  # QRect

        # ===== Mood Bar State =====
        self._mood_bar_visible = False

        # ===== Notes Widget State =====
        self._notes_visible = False

        # ===== Task Completion Hover State =====
        self._hovered_checkmark_index: Optional[int] = None  # Index of key with checkmark being hovered

    def start_resize(self, edge: str, start_rect, drag_start_x: int, drag_start_y: int):
        """Start window resize operation"""
        self._is_resizing = True
        self._resize_edge = edge
        self._resize_start_rect = start_rect
        self._drag_start_x = drag_start_x
        self._drag_start_y = drag_start_y

    def end_resize(self):
        """End window resize operation"""
        self._is_resizing = False
        self._resize_edge = None
        self._resize_start_rect = None

    # ===== Toggleable Drawer Properties =====

    @property
    def toggleable_drawer_visible(self) -> bool:
        return self._toggleable_drawer_visible

    @toggleable_drawer_visible.setter
    def toggleable_drawer_visible(self, value: bool):
        if self._toggleable_drawer_visible != value:
            self._toggleable_drawer_visible = value
            self.toggleable_drawer_toggled.emit(value)

    def toggle_toggleable_drawer(self):
        """Toggle the toggleable drawer visibility state"""
        self.toggleable_drawer_visible = not self._toggleable_drawer_visible

    # ===== Window Properties =====

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

    def start_drag(self, x: int, y: int, local_x: int = 0, local_y: int = 0, reset_moved_flag: bool = True):
        """
        Start a drag operation.

        Args:
            x, y: Global coordinates of drag start
            local_x, local_y: Local (widget) coordinates of drag start
            reset_moved_flag: If True, reset the window_was_moved flag (for initial press).
                             If False, keep the flag (for position updates during drag).
        """
        self._drag_start_x = x
        self._drag_start_y = y
        if local_x != 0 or local_y != 0:  # Only update local coords if provided
            self._press_local_x = local_x
            self._press_local_y = local_y
        self._is_dragging = False  # Not yet confirmed as drag
        if reset_moved_flag:
            self._window_was_moved = False  # Reset window moved flag only on initial press

    def get_drag_start(self) -> tuple[int, int]:
        """Get drag start position (global coordinates)"""
        return self._drag_start_x, self._drag_start_y

    def get_press_local(self) -> tuple[int, int]:
        """Get press position in local (widget) coordinates"""
        return self._press_local_x, self._press_local_y

    def end_drag(self):
        """End drag operation"""
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._press_local_x = 0
        self._press_local_y = 0
        self._window_was_moved = False

    @property
    def window_was_moved(self) -> bool:
        """Check if window was actually moved during this drag"""
        return self._window_was_moved

    def mark_window_moved(self):
        """Mark that the window was moved during this drag"""
        self._window_was_moved = True

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

    # ===== Key Reorder Properties =====

    @property
    def dragged_key_index(self) -> Optional[int]:
        """Index of the key currently being dragged"""
        return self._dragged_key_index

    @property
    def drag_current_y(self) -> int:
        """Current Y position during key drag"""
        return self._drag_current_y

    @property
    def drop_target_index(self) -> Optional[int]:
        """Target index for dropping the dragged key"""
        return self._drop_target_index

    def start_key_drag(self, key_index: int, y_position: int):
        """
        Start dragging a key.

        Args:
            key_index: Index of the key being dragged
            y_position: Initial Y position
        """
        self._dragged_key_index = key_index
        self._drag_current_y = y_position
        self._drop_target_index = None

    def update_key_drag(self, y_position: int, target_index: Optional[int] = None):
        """
        Update key drag position.

        Args:
            y_position: Current Y position
            target_index: Index where the key would be dropped
        """
        self._drag_current_y = y_position
        self._drop_target_index = target_index

    def end_key_drag(self):
        """End key drag operation"""
        self._dragged_key_index = None
        self._drag_current_y = 0
        self._drop_target_index = None

    def is_dragging_key(self) -> bool:
        """Check if currently dragging a key"""
        return self._dragged_key_index is not None

    # ===== Mood Bar Properties =====

    @property
    def mood_bar_visible(self) -> bool:
        return self._mood_bar_visible

    @mood_bar_visible.setter
    def mood_bar_visible(self, value: bool):
        self._mood_bar_visible = value

    def toggle_mood_bar(self):
        """Toggle mood bar visibility"""
        self._mood_bar_visible = not self._mood_bar_visible

    # ===== Notes Widget Properties =====

    @property
    def notes_visible(self) -> bool:
        return self._notes_visible

    @notes_visible.setter
    def notes_visible(self, value: bool):
        self._notes_visible = value

    def toggle_notes(self):
        """Toggle notes widget visibility"""
        self._notes_visible = not self._notes_visible

    # ===== Task Completion Hover Properties =====

    @property
    def hovered_checkmark_index(self) -> Optional[int]:
        """Get the index of the key whose checkmark is being hovered"""
        return self._hovered_checkmark_index

    @hovered_checkmark_index.setter
    def hovered_checkmark_index(self, value: Optional[int]):
        """Set the index of the key whose checkmark is being hovered"""
        self._hovered_checkmark_index = value

    # ===== State Reset =====

    def reset(self):
        """Reset all state to initial values"""
        self._toggleable_drawer_visible = False
        self._pressed_key_index = None
        self._scroll_offset = 0
        self._max_scroll_offset = 0
        self._scrolling_enabled = False
        self._scroll_accumulator = 0.0
        self._is_dragging = False
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._press_local_x = 0
        self._press_local_y = 0
        self._last_click_time = 0
        self._time_displays.clear()
        self._is_fading_out = False
        self._dragged_key_index = None
        self._drag_current_y = 0
        self._drop_target_index = None
        self._mood_bar_visible = False
        self._notes_visible = False
        self._hovered_checkmark_index = None