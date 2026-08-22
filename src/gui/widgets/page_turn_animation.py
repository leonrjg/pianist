"""
Page Turn Animation - Handles transitions between sheet pages.
"""

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QObject, pyqtProperty, QParallelAnimationGroup, QRect
from PyQt6.QtWidgets import QGraphicsOpacityEffect


class PageTurnAnimation(QObject):
    """Manages page turn animation with slide effect"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_widget = None
        self._next_widget = None
        self._animation_group = None
        self._on_complete = None
        self._original_geometry = None

    def is_running(self):
        """Check if an animation is currently running"""
        return self._animation_group is not None and self._animation_group.state() == self._animation_group.State.Running

    def cancel(self):
        """Cancel any ongoing animation and clean up immediately"""
        if self._animation_group:
            self._animation_group.stop()
            self._animation_group = None
        
        # Clean up widgets without calling callback
        if self._current_widget:
            self._current_widget.hide()
            self._current_widget.setGraphicsEffect(None)
        
        if self._next_widget:
            self._next_widget.setGraphicsEffect(None)
            if self._original_geometry:
                self._next_widget.setGeometry(self._original_geometry)
        
        # Reset state without calling on_complete
        self._current_widget = None
        self._next_widget = None
        self._on_complete = None
        self._original_geometry = None

    def animate_transition(self, current_widget, next_widget, on_complete=None, reverse=False):
        """
        Animate transition from current to next widget with slide effect.

        Args:
            current_widget: Widget to slide out
            next_widget: Widget to slide in
            on_complete: Callback when animation completes
            reverse: If True, slide in opposite direction (for back navigation)
        """
        self._current_widget = current_widget
        self._next_widget = next_widget
        self._on_complete = on_complete

        if current_widget and next_widget:
            # Store original geometry
            self._original_geometry = current_widget.geometry()

            if reverse:
                # Going back: next widget slides in from left, current slides out to right
                next_start_x = -self._original_geometry.width()
                current_end_x = self._original_geometry.right()
            else:
                # Going forward: next widget slides in from right, current slides out to left
                next_start_x = self._original_geometry.right()
                current_end_x = -self._original_geometry.width()

            # Position next widget ready to slide in
            next_widget.setGeometry(QRect(
                next_start_x,
                self._original_geometry.y(),
                self._original_geometry.width(),
                self._original_geometry.height()
            ))
            next_widget.show()

            # Create animation group for simultaneous animations
            self._animation_group = QParallelAnimationGroup()

            # Slide current widget out
            current_slide = QPropertyAnimation(current_widget, b"geometry")
            current_slide.setDuration(180)
            current_slide.setStartValue(self._original_geometry)
            current_slide.setEndValue(QRect(
                current_end_x,
                self._original_geometry.y(),
                self._original_geometry.width(),
                self._original_geometry.height()
            ))
            current_slide.setEasingCurve(QEasingCurve.Type.InOutCubic)

            # Slide next widget in
            next_slide = QPropertyAnimation(next_widget, b"geometry")
            next_slide.setDuration(180)
            next_slide.setStartValue(QRect(
                next_start_x,
                self._original_geometry.y(),
                self._original_geometry.width(),
                self._original_geometry.height()
            ))
            next_slide.setEndValue(self._original_geometry)
            next_slide.setEasingCurve(QEasingCurve.Type.InOutCubic)

            # Add subtle fade for smoother transition
            current_effect = QGraphicsOpacityEffect()
            current_widget.setGraphicsEffect(current_effect)
            current_fade = QPropertyAnimation(current_effect, b"opacity")
            current_fade.setDuration(180)
            current_fade.setStartValue(1.0)
            current_fade.setEndValue(0.3)
            current_fade.setEasingCurve(QEasingCurve.Type.InOutQuad)

            next_effect = QGraphicsOpacityEffect()
            next_widget.setGraphicsEffect(next_effect)
            next_fade = QPropertyAnimation(next_effect, b"opacity")
            next_fade.setDuration(180)
            next_fade.setStartValue(0.3)
            next_fade.setEndValue(1.0)
            next_fade.setEasingCurve(QEasingCurve.Type.InOutQuad)

            self._animation_group.addAnimation(current_slide)
            self._animation_group.addAnimation(next_slide)
            self._animation_group.addAnimation(current_fade)
            self._animation_group.addAnimation(next_fade)

            self._animation_group.finished.connect(self._on_animation_finished)
            self._animation_group.start()
        elif next_widget:
            # No current widget, just show next
            next_widget.show()
            self._on_animation_finished()
        else:
            # Nothing to animate
            self._on_animation_finished()

    def _on_animation_finished(self):
        """Called when animation completes"""
        # Clean up current widget
        if self._current_widget:
            self._current_widget.hide()
            self._current_widget.setGraphicsEffect(None)

        # Clean up next widget effects and ensure proper positioning
        if self._next_widget:
            self._next_widget.setGraphicsEffect(None)
            if self._original_geometry:
                self._next_widget.setGeometry(self._original_geometry)

        # Call completion callback
        if self._on_complete:
            self._on_complete()

        # Cleanup
        self._current_widget = None
        self._next_widget = None
        self._on_complete = None
        self._animation_group = None
        self._original_geometry = None
