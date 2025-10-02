"""
Window Size Manager - Manages window dimensions and resizing.

Coordinates window size with drawer state to ensure:
- Window is always sized to accommodate full content (drawer + keys + frame)
- Manual resizing by user respects minimum dimensions
- Drawer mask is reapplied after any resize operation
"""

from PyQt6.QtCore import QObject, pyqtSignal, QSize
from ..constants import PianoLayout


class WindowSizeManager(QObject):
    """Manages window sizing logic and constraints"""

    # Signal emitted when window should be resized
    size_changed = pyqtSignal(int, int)  # width, height

    def __init__(self, window):
        """
        Initialize window size manager.

        Args:
            window: The parent window (QWidget)
        """
        super().__init__(window)
        self.window = window

        # Track if we're programmatically resizing (to avoid feedback loops)
        self._resizing_programmatically = False

    def get_required_width(self, drawer_visible: bool) -> int:
        """
        Calculate required window width based on drawer state.

        The window is always sized to accommodate the full drawer,
        but the mask controls what's visible.

        Args:
            drawer_visible: Whether drawer is currently visible

        Returns:
            Required window width in pixels
        """
        # Window is always full width (includes space for drawer even when hidden)
        return PianoLayout.DEFAULT_WINDOW_WIDTH

    def get_minimum_width(self) -> int:
        """
        Get minimum allowed window width.

        Returns:
            Minimum width in pixels
        """
        return PianoLayout.MIN_WINDOW_WIDTH

    def get_minimum_height(self) -> int:
        """
        Get minimum allowed window height.

        Returns:
            Minimum height in pixels
        """
        return PianoLayout.MIN_WINDOW_HEIGHT

    def get_initial_size(self, drawer_visible: bool) -> QSize:
        """
        Get initial window size on startup.

        Args:
            drawer_visible: Initial drawer visibility state

        Returns:
            QSize with width and height
        """
        width = self.get_required_width(drawer_visible)
        height = PianoLayout.DEFAULT_WINDOW_HEIGHT
        return QSize(width, height)

    def validate_size(self, width: int, height: int) -> tuple[int, int]:
        """
        Validate and constrain window size to allowed dimensions.

        Args:
            width: Proposed window width
            height: Proposed window height

        Returns:
            Tuple of (validated_width, validated_height)
        """
        # Enforce minimum size
        width = max(width, self.get_minimum_width())
        height = max(height, self.get_minimum_height())

        return width, height

    def handle_user_resize(self, width: int, height: int, drawer_animation_manager) -> bool:
        """
        Handle manual window resize by user.

        Validates the new size and ensures drawer mask is maintained.

        Args:
            width: New window width
            height: New window height
            drawer_animation_manager: Manager to reapply drawer mask

        Returns:
            True if resize was handled, False if it should be ignored
        """
        # Ignore if we're doing a programmatic resize
        if self._resizing_programmatically:
            return False

        # Validate dimensions
        validated_width, validated_height = self.validate_size(width, height)

        # Check if validation changed the size
        if validated_width != width or validated_height != height:
            # Apply validated size programmatically
            self._resizing_programmatically = True
            self.window.resize(validated_width, validated_height)
            self._resizing_programmatically = False
            return False  # The programmatic resize will trigger another event

        # Reapply drawer mask after resize
        # The drawer mask needs to be recalculated for new window dimensions
        drawer_animation_manager._apply_mask()

        # Emit size changed signal
        self.size_changed.emit(validated_width, validated_height)
        return True

    def set_size_programmatically(self, width: int, height: int):
        """
        Set window size programmatically (not user-initiated).

        Args:
            width: New window width
            height: New window height
        """
        self._resizing_programmatically = True
        self.window.resize(width, height)
        self._resizing_programmatically = False
        self.size_changed.emit(width, height)
