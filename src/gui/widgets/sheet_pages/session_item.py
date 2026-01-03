"""
Session Item - Display individual session with delete option.
"""

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt

from core.util.time import get_friendly_elapsed, get_friendly_datetime, HOUR


class SessionItem(QFrame):
    """Individual session display with delete button"""

    def __init__(self, log, on_delete=None, parent=None):
        """
        Args:
            log: Log object representing the session
            on_delete: Callback for delete action, receives the log as parameter
            parent: Parent widget
        """
        super().__init__(parent)
        self.log = log
        self.on_delete = on_delete

        self._setup_ui()

    def _setup_ui(self):
        """Set up the session item UI"""
        # Subtle nested card styling
        self.setStyleSheet("""
            SessionItem {
                background-color: rgba(245, 240, 230, 150);
                border: 1px solid rgb(210, 200, 185);
                border-radius: 2px;
                padding: 4px;
                margin: 2px 0px;
            }
        """)

        # Horizontal layout
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 3, 4, 3)
        layout.setSpacing(6)
        self.setLayout(layout)

        # Session time
        start_time = get_friendly_datetime(self.log.start, HOUR)
        time_label = QLabel(start_time)
        time_label.setStyleSheet("color: rgb(70, 50, 35); font-size: 10px; background: transparent;")
        layout.addWidget(time_label)

        # Duration
        if self.log.end:
            duration_label = QLabel(get_friendly_elapsed((self.log.end - self.log.start).total_seconds() - self.log.idle_time))
            duration_label.setStyleSheet("color: rgb(100, 80, 65); font-size: 10px; background: transparent;")
            layout.addWidget(duration_label)

        if self.log.started_by:
            source = self.log.started_by
            source_label = QLabel(f"(started by {source})")
            source_label.setStyleSheet("color: rgb(140, 120, 100); font-size: 9px; font-style: italic; background: transparent;")
            layout.addWidget(source_label)

        layout.addStretch()

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(18, 18)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(160, 50, 50, 100);
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(180, 60, 60, 150);
            }
            QPushButton:pressed {
                background-color: rgba(140, 40, 40, 120);
            }
            QPushButton:disabled {
                background-color: rgba(160, 160, 160, 80);
                color: rgba(255, 255, 255, 100);
            }
        """)
        delete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        if self.on_delete:
            delete_btn.clicked.connect(lambda: self.on_delete(self.log))
        else:
            delete_btn.setEnabled(False)
        
        layout.addWidget(delete_btn)
