"""
Drawer Animation Manager - Handles drawer reveal/hide animations.

Manages the window mask animation that creates the smooth drawer reveal effect.
The drawer is always painted at a fixed position, and this manager controls which
portion of the window is visible through an animated mask.
"""

from PyQt6.QtCore import QTimer, QEasingCurve, pyqtSignal, QObject
from PyQt6.QtGui import QRegion
from ..constants import PianoLayout, Animations


class DrawerAnimationManager(QObject):
    """Manages drawer reveal/hide animation using window masks"""

    # Signal emitted when animation completes
    animation_finished = pyqtSignal()

    def __init__(self, window):
        """
        Initialize drawer animation manager.

        Args:
            window: The parent window (QWidget) to apply masks to
        """
        super().__init__(window)
        self.window = window

        # Animation state
        self._mask_offset = 0  # Current mask offset (0 = hidden, drawer_width = visible)
        self._mask_target = 0  # Target offset for animation
        self._mask_start = 0  # Starting offset for animation
        self._mask_progress = 0.0  # Animation progress (0.0 to 1.0)
        self._mask_duration = Animations.FALLBOARD_SLIDE_DURATION
        self._drawer_width = 0  # Current drawer width (dynamic)

        # Animation timer
        self._mask_timer = QTimer(self)
        self._mask_timer.setInterval(16)  # ~60 FPS
        self._mask_timer.timeout.connect(self._animate_frame)

    def start_animation(self, opening: bool, drawer_width: int):
        """
        Start drawer reveal/hide animation.

        Args:
            opening: True to reveal drawer, False to hide it
            drawer_width: Width of the drawer in pixels
        """
        self._drawer_width = drawer_width
        self._mask_target = drawer_width if opening else 0
        self._mask_start = self._mask_offset
        self._mask_progress = 0.0

        # Stop existing animation if running
        if self._mask_timer.isActive():
            self._mask_timer.stop()

        # Start new animation
        self._mask_timer.start()

    def _animate_frame(self):
        """
        Animate a single frame of the drawer reveal/hide.

        Updates the window mask to show progressively more or less of the left edge,
        creating a smooth drawer reveal effect. The mask hides the leftmost part of
        the window (where the drawer is painted) and gradually reveals it.
        """
        self._mask_progress += 16 / self._mask_duration

        if self._mask_progress >= 1.0:
            # Animation complete - set final state
            self._mask_offset = self._mask_target
            self._mask_timer.stop()
            self._apply_mask()
            self.animation_finished.emit()
        else:
            # Calculate eased progress for smooth animation
            ease = QEasingCurve(QEasingCurve.Type.InOutQuad)
            eased_progress = ease.valueForProgress(self._mask_progress)

            # Interpolate current mask offset
            offset_delta = self._mask_target - self._mask_start
            self._mask_offset = int(self._mask_start + offset_delta * eased_progress)

            # Apply mask and trigger repaint
            self._apply_mask()

    def _apply_mask(self):
        """
        Apply the current mask to the window.

        The mask hides the leftmost part of the window (where the drawer is painted)
        and gradually reveals it.
        """
        # Always get current drawer width from geometry model for consistency
        current_drawer_width = self.window.geometry_model.toggleable_drawer_width

        # Calculate visible region start position
        visible_start_x = current_drawer_width - self._mask_offset

        # Create and apply mask
        visible_region = QRegion(
            visible_start_x, 0,
            self.window.width() - visible_start_x, self.window.height()
        )
        self.window.setMask(visible_region)
        self.window.update()

    def initialize_state(self, drawer_visible: bool):
        """
        Initialize mask state without animation.

        Args:
            drawer_visible: Whether drawer should be visible
        """
        # Get current drawer width from window's geometry model
        self._drawer_width = self.window.geometry_model.toggleable_drawer_width
        self._mask_offset = self._drawer_width if drawer_visible else 0
        self._apply_mask()

    def cleanup(self):
        """Stop any running animations"""
        if self._mask_timer.isActive():
            self._mask_timer.stop()
