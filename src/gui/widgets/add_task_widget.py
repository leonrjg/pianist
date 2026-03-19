"""
Add Task Widget - Floating task creation form.

Allows users to quickly create manual tasks with a title and scheduled date.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QDate
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QCursor
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.habit.manual_task import ManualTask
from core.db import db
from .vintage_date_picker import VintageDatePicker


class AddTaskWidget(QWidget):
    """Floating form for adding manual tasks"""

    task_created = pyqtSignal()  # Emits when task is created
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        self.setLayout(layout)

        # Title label
        title_label = QLabel("Add Task")
        title_label.setStyleSheet("""
            QLabel {
                color: rgb(255, 252, 245);
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }
        """)
        layout.addWidget(title_label)

        # Task title input
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title...")
        self.title_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 252, 245, 220);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                color: rgb(70, 50, 35);
                font-size: 10px;
                padding: 5px 6px;
            }
            QLineEdit:focus {
                border: 1px solid rgb(184, 134, 11);
                background-color: rgba(255, 255, 250, 240);
            }
            QLineEdit::placeholder {
                color: rgba(120, 100, 80, 150);
                font-style: italic;
            }
        """)
        # Connect Enter key to submit
        self.title_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.title_input)

        # Date input
        date_row = QHBoxLayout()
        date_row.setSpacing(6)

        date_label = QLabel("Date:")
        date_label.setStyleSheet("""
            QLabel {
                color: rgb(200, 185, 160);
                font-size: 9px;
                background: transparent;
            }
        """)
        date_row.addWidget(date_label)

        # Use custom vintage date picker with TaskCalendarWidget
        self.date_input = VintageDatePicker()
        self.date_input.setDate(QDate.currentDate())
        date_row.addWidget(self.date_input)
        date_row.addStretch()

        layout.addLayout(date_row)

        # Submit button
        self.submit_button = QPushButton("Add Task")
        self.submit_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.submit_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(184, 134, 11, 180);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 3px;
                color: rgb(255, 252, 245);
                font-size: 10px;
                font-weight: bold;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: rgba(218, 165, 32, 200);
                border-color: rgb(218, 165, 32);
            }
            QPushButton:pressed {
                background-color: rgba(160, 115, 10, 200);
            }
        """)
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)

        # Set fixed width
        self.setFixedWidth(200)

    def _on_submit(self):
        """Handle task submission"""
        title = self.title_input.text().strip()

        if not title:
            return

        try:
            # Get selected date
            qdate = self.date_input.date()
            scheduled_dt = datetime(qdate.year(), qdate.month(), qdate.day(), 0, 0, 0)

            # Create manual task
            with db.atomic():
                ManualTask.create(
                    habit=None,
                    title=title,
                    scheduled_at=scheduled_dt,
                    completed_at=None
                )

            # Clear input and emit signal
            self.title_input.clear()
            self.date_input.setDate(QDate.currentDate())
            self.task_created.emit()
            self.close()

        except Exception as e:
            print(f"Error creating task: {e}")
            import traceback
            traceback.print_exc()

    def paintEvent(self, event):
        """Draw rounded background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded rectangle background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)

        painter.fillPath(path, QColor(61, 40, 23, 230))
        painter.setPen(QColor(184, 134, 11))
        painter.drawPath(path)

    def show_at_position(self, pos: QPoint):
        """Show the widget at the specified position"""
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()
        # Focus on title input
        self.title_input.setFocus()

    def closeEvent(self, event):
        """Handle close event"""
        self.closed.emit()
        super().closeEvent(event)
