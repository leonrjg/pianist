"""
Animation Manager - Centralizes all animations in the piano interface.

This manager handles:
- Window fade in/out animations
- Fallboard slide animations
- Future animations can be added here

Benefits:
- Single source of truth for animation state
- Easy to pause/stop all animations
- Consistent animation behavior
"""

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
from PyQt6.QtWidgets import QWidget

from ..constants import Animations


class AnimationManager(QObject):
    """Manages all animations for the piano window"""

    # Signals
    fade_finished = pyqtSignal()  # Emitted when fade animation completes
    slide_finished = pyqtSignal()  # Emitted when slide animation completes

    def __init__(self, window: QWidget):
        super().__init__()
        self.window = window

        # Fade animation (for hiding window)
        self.fade_animation = QPropertyAnimation(window, b"windowOpacity")
        self.fade_animation.setDuration(Animations.FADE_DURATION)
        self.fade_animation.setEasingCurve(self._get_easing_curve(Animations.FADE_EASING))
        self.fade_animation.finished.connect(self.fade_finished.emit)

        # Fallboard slide animation (for extending/retracting window)
        self.slide_animation = QPropertyAnimation(window, b"geometry")
        self.slide_animation.setDuration(Animations.FALLBOARD_SLIDE_DURATION)
        self.slide_animation.setEasingCurve(self._get_easing_curve(Animations.SLIDE_EASING))
        self.slide_animation.finished.connect(self.slide_finished.emit)

    def _get_easing_curve(self, curve_name: str) -> QEasingCurve.Type:
        """Convert string curve name to QEasingCurve.Type"""
        return getattr(QEasingCurve.Type, curve_name, QEasingCurve.Type.InOutQuad)

    # ===== Fade Animations =====

    def fade_out(self, target_opacity: float = Animations.WINDOW_OPACITY_HIDDEN):
        """Fade the window out"""
        self.fade_animation.setStartValue(self.window.windowOpacity())
        self.fade_animation.setEndValue(target_opacity)
        self.fade_animation.start()

    def fade_in(self, target_opacity: float = Animations.WINDOW_OPACITY_NORMAL):
        """Fade the window in"""
        self.fade_animation.setStartValue(self.window.windowOpacity())
        self.fade_animation.setEndValue(target_opacity)
        self.fade_animation.start()

    def is_fading(self) -> bool:
        """Check if a fade animation is running"""
        return self.fade_animation.state() == QPropertyAnimation.State.Running

    def stop_fade(self):
        """Stop the current fade animation"""
        if self.is_fading():
            self.fade_animation.stop()

    # ===== Slide Animations =====

    def slide_window(self, new_geometry: QRect):
        """Slide the window to a new geometry"""
        self.slide_animation.setStartValue(self.window.geometry())
        self.slide_animation.setEndValue(new_geometry)
        self.slide_animation.start()

    def extend_window_left(self, extend_by: int):
        """Extend the window to the left by a specified amount"""
        current = self.window.geometry()
        new_geometry = QRect(
            current.x() - extend_by,
            current.y(),
            current.width() + extend_by,
            current.height()
        )
        self.slide_window(new_geometry)

    def retract_window_left(self, retract_by: int):
        """Retract the window from the left by a specified amount"""
        current = self.window.geometry()
        new_geometry = QRect(
            current.x() + retract_by,
            current.y(),
            current.width() - retract_by,
            current.height()
        )
        self.slide_window(new_geometry)

    def is_sliding(self) -> bool:
        """Check if a slide animation is running"""
        return self.slide_animation.state() == QPropertyAnimation.State.Running

    def stop_slide(self):
        """Stop the current slide animation"""
        if self.is_sliding():
            self.slide_animation.stop()

    # ===== General Animation Control =====

    def stop_all(self):
        """Stop all animations"""
        self.stop_fade()
        self.stop_slide()

    def is_animating(self) -> bool:
        """Check if any animation is running"""
        return self.is_fading() or self.is_sliding()
