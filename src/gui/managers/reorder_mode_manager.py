"""
Reorder Mode Manager - Manages key reordering mode and pulse animations.

Responsibilities:
- Toggle reorder mode on/off
- Generate scale pulse values for keys during reorder mode
- Emit signals when mode changes

Follows:
- Single Responsibility Principle: Only manages reorder mode state
- Signal/Slot Pattern: Emits signals for loose coupling
- Dependency Injection: Receives parent widget as dependency
"""

import math
from typing import Dict
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ..constants import Animations


class ReorderModeManager(QObject):
    """Manages reorder mode state and pulse animations"""

    # Signals
    reorder_mode_toggled = pyqtSignal(bool)  # is_active
    pulse_updated = pyqtSignal()  # Request repaint for pulse animation

    def __init__(self, parent=None):
        """
        Initialize the reorder mode manager.

        Args:
            parent: Parent QObject for Qt memory management
        """
        super().__init__(parent)

        # ===== State =====
        self._is_reorder_mode = False
        self._num_keys = 0

        # ===== Pulse Animation =====
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._update_pulse)
        self._pulse_scales: Dict[int, float] = {}
        self._pulse_direction = 1  # 1 for growing, -1 for shrinking
        self._current_scale = 1.0

    # ===== Public Interface =====

    @property
    def is_reorder_mode(self) -> bool:
        """Check if reorder mode is active"""
        return self._is_reorder_mode

    def toggle_reorder_mode(self):
        """Toggle reorder mode on/off"""
        self._is_reorder_mode = not self._is_reorder_mode

        if self._is_reorder_mode:
            self._start_pulse()
        else:
            self._stop_pulse()

        self.reorder_mode_toggled.emit(self._is_reorder_mode)

    def set_num_keys(self, num_keys: int):
        """
        Update the number of keys to pulse.

        Args:
            num_keys: Number of keys currently visible
        """
        self._num_keys = num_keys

        # Reinitialize pulse scales if in reorder mode
        if self._is_reorder_mode:
            self._initialize_pulse_scales()

    def get_scale(self, key_index: int) -> float:
        """
        Get the current scale factor for a key.

        Args:
            key_index: Index of the key

        Returns:
            Scale factor (e.g., 1.0 = 100%, 1.02 = 102%)
        """
        if not self._is_reorder_mode:
            return 1.0

        return self._pulse_scales.get(key_index, 1.0)

    def exit_reorder_mode(self):
        """Force exit reorder mode (used when starting a session)"""
        if self._is_reorder_mode:
            self._is_reorder_mode = False
            self._stop_pulse()
            self.reorder_mode_toggled.emit(False)

    # ===== Private Methods =====

    def _start_pulse(self):
        """Start the pulse animation"""
        self._current_scale = 1.0
        self._pulse_direction = 1
        self._initialize_pulse_scales()
        self._pulse_timer.start(Animations.PULSE_INTERVAL)

    def _stop_pulse(self):
        """Stop the pulse animation"""
        self._pulse_timer.stop()
        self._pulse_scales.clear()
        self._current_scale = 1.0
        self.pulse_updated.emit()  # Trigger repaint to clear scales

    def _initialize_pulse_scales(self):
        """Initialize all keys with scale factor of 1.0"""
        self._pulse_scales.clear()
        for i in range(self._num_keys):
            self._pulse_scales[i] = self._current_scale

    def _update_pulse(self):
        """
        Update pulse scale with smooth breathing effect.

        All keys scale together in unison, creating a synchronized pulse effect.
        """
        # Update current scale
        self._current_scale += Animations.PULSE_SPEED * self._pulse_direction

        # Reverse direction at boundaries
        if self._current_scale >= Animations.PULSE_MAX_SCALE:
            self._current_scale = Animations.PULSE_MAX_SCALE
            self._pulse_direction = -1
        elif self._current_scale <= Animations.PULSE_MIN_SCALE:
            self._current_scale = Animations.PULSE_MIN_SCALE
            self._pulse_direction = 1

        # Apply same scale to all keys
        for i in range(self._num_keys):
            self._pulse_scales[i] = self._current_scale

        self.pulse_updated.emit()  # Request repaint

    # ===== Cleanup =====

    def cleanup(self):
        """Clean up resources"""
        if self._pulse_timer.isActive():
            self._pulse_timer.stop()
