"""
Tracker Help Widget - Live display of tracker help information.

This widget displays real-time help information from a tracker by calling
its get_help() method periodically without blocking the UI.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect
from PyQt6.QtCore import QTimer, QRunnable, QThreadPool, pyqtSignal, QObject, Qt
from PyQt6.QtSvgWidgets import QSvgWidget
from typing import Dict, Any
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class HelpUpdateSignals(QObject):
    """Signals for communicating from worker thread to UI thread."""
    helpUpdated = pyqtSignal(str)
    errorOccurred = pyqtSignal(str)


class HelpUpdateWorker(QRunnable):
    """Worker to fetch tracker help without blocking the UI."""

    def __init__(self, tracker_name: str, config: Dict[str, Any], widget_id: int):
        super().__init__()
        self.tracker_name = tracker_name
        self.config = config
        self.widget_id = widget_id
        self.signals = HelpUpdateSignals()
        self._cancelled = False

    def cancel(self):
        """Cancel this worker."""
        self._cancelled = True

    def run(self):
        """Fetch help text from the tracker."""
        if self._cancelled:
            return
        try:
            from core.tracker.registry import TrackerRegistry
            help_text = TrackerRegistry.get_tracker_help(self.tracker_name, self.config)
            if not self._cancelled:
                self.signals.helpUpdated.emit(help_text)
        except Exception as e:
            if not self._cancelled:
                logger.error(f"Failed to get tracker help: {e}")
                self.signals.errorOccurred.emit(str(e))


class TrackerHelpWidget(QWidget):
    """Widget that displays live tracker help information."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tracker_name = None
        self._config = {}
        self._timer = None
        self._thread_pool = QThreadPool.globalInstance()
        self._is_destroyed = False
        self._widget_id = id(self)
        self._active_workers = []

        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # Help text label with markdown support
        self._help_label = QLabel("Loading...")
        self._help_label.setWordWrap(True)
        self._help_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self._help_label.setFrameShape(QFrame.Shape.StyledPanel)
        self._help_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self._help_label)

        # Loading indicator row (bottom right)
        loading_layout = QHBoxLayout()
        loading_layout.setContentsMargins(0, 2, 10, 2)
        loading_layout.addStretch()

        icon_path = Path(__file__).parent.parent / "icons" / "loading.svg"
        self._loading_icon = QSvgWidget(str(icon_path))
        self._loading_icon.setFixedSize(16, 16)

        # Create opacity effect for the loading icon
        self._loading_opacity = QGraphicsOpacityEffect()
        self._loading_opacity.setOpacity(0.0)
        self._loading_icon.setGraphicsEffect(self._loading_opacity)

        loading_layout.addWidget(self._loading_icon)

        main_layout.addLayout(loading_layout)

    def set_tracker(self, tracker_name: str, config: Dict[str, Any]):
        """
        Set the tracker to monitor.

        Args:
            tracker_name: Name of the tracker
            config: Configuration dictionary for the tracker
        """
        self._tracker_name = tracker_name
        self._config = config
        self._update_help()

    def start_updates(self):
        """Start periodic updates of the help text."""
        if self._timer is None and not self._is_destroyed:
            self._timer = QTimer()
            self._timer.timeout.connect(self._update_help)
            self._timer.start(2500)  # Update every 2.5 seconds
            logger.info(f"Started help updates for tracker: {self._tracker_name}")
            # Do first update immediately
            self._update_help()

    def stop_updates(self):
        """Stop periodic updates of the help text."""
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
            logger.info(f"Stopped help updates for tracker: {self._tracker_name}")

        # Cancel all active workers
        for worker in self._active_workers:
            worker.cancel()
        self._active_workers.clear()

    def _set_loading(self, loading: bool):
        """Show or hide the loading indicator."""
        if self._is_destroyed:
            return
        # Use opacity effect to keep icon in layout but make invisible
        self._loading_opacity.setOpacity(1.0 if loading else 0.0)

    def _update_help(self):
        """Trigger an asynchronous help update."""
        if self._tracker_name is None or self._is_destroyed:
            return

        # Cancel all existing workers to prevent out-of-order results
        for worker in self._active_workers:
            worker.cancel()
        self._active_workers.clear()

        # Show loading indicator
        self._set_loading(True)

        # Create and run worker
        worker = HelpUpdateWorker(self._tracker_name, self._config, self._widget_id)
        worker.signals.helpUpdated.connect(self._on_help_updated, Qt.ConnectionType.QueuedConnection)
        worker.signals.errorOccurred.connect(self._on_error, Qt.ConnectionType.QueuedConnection)

        # Track active worker
        self._active_workers.append(worker)

        self._thread_pool.start(worker)

    def _on_help_updated(self, help_text: str):
        """Handle updated help text from worker thread."""
        if self._is_destroyed:
            return

        # Clean up completed workers
        self._active_workers = [w for w in self._active_workers if not w._cancelled]

        if help_text.strip():
            self._help_label.setText(help_text)
            self._help_label.show()
        else:
            self._help_label.hide()
        self._set_loading(False)

    def _on_error(self, error_message: str):
        """Handle error from worker thread."""
        if self._is_destroyed:
            return

        # Clean up completed workers
        self._active_workers = [w for w in self._active_workers if not w._cancelled]

        self._help_label.setText(f"Error: {error_message}")
        self._help_label.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 240, 240);
                color: rgb(180, 50, 50);
                padding: 10px;
                font-size: 11px;
                border: 1px solid rgb(200, 185, 160);
            }
        """)
        self._set_loading(False)

    def closeEvent(self, event):
        """Clean up resources when widget is closed."""
        # Immediately mark as destroyed to prevent new operations
        self._is_destroyed = True

        # Stop timer first (prevents new workers)
        if self._timer is not None:
            try:
                self._timer.stop()
                self._timer.timeout.disconnect()
                self._timer.deleteLater()
                self._timer = None
            except (RuntimeError, TypeError):
                pass

        # Cancel all workers
        for worker in self._active_workers:
            worker.cancel()
        self._active_workers.clear()

        super().closeEvent(event)

    def __del__(self):
        """Clean up resources when widget is destroyed."""
        self._is_destroyed = True
        # Don't try to clean up Qt objects in __del__, they may already be gone
