"""
Add Task Widget - Floating task/thought creation form.

Two tabs:
- Task: create manual tasks with a title and scheduled date.
- Thought: capture a quick thought that can be browsed later.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QLabel, QTabWidget, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QDate
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QCursor
from datetime import datetime
import logging

from core.task.service import TaskService
from core.notes.service import NoteService
from .themed_date_picker import ThemedDatePicker


def _c():
    from gui.constants import piano_colors
    return piano_colors()


from gui.themes import current_theme as _t, ThemedWidget

logger = logging.getLogger(__name__)


class AddTaskWidget(QWidget, ThemedWidget):
    """Floating form for adding manual tasks or quick thoughts."""

    task_created = pyqtSignal()
    thought_created = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    # ------------------------------------------------------------------
    # UI setup
    # ------------------------------------------------------------------

    def _setup_ui(self):
        outer = QVBoxLayout()
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(0)
        self.setLayout(outer)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.tabBar().setExpanding(True)
        outer.addWidget(self._tabs)

        self._tabs.addTab(self._build_task_tab(), "Task")
        self._tabs.addTab(self._build_thought_tab(), "Thought")

        self.setFixedWidth(220)
        self._setup_style()

    def _build_task_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        tab.setLayout(layout)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title...")
        self.title_input.returnPressed.connect(self._on_task_submit)
        layout.addWidget(self.title_input)

        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        self._time_label = QLabel("Reminder:")
        time_row.addWidget(self._time_label)
        self.reminder_time_input = QLineEdit()
        self.reminder_time_input.setPlaceholderText("HH:MM")
        self.reminder_time_input.returnPressed.connect(self._on_task_submit)
        time_row.addWidget(self.reminder_time_input)
        layout.addLayout(time_row)

        date_row = QHBoxLayout()
        date_row.setSpacing(6)
        self._date_label = QLabel("Date:")
        date_row.addWidget(self._date_label)
        self.date_input = ThemedDatePicker()
        self.date_input.setDate(QDate.currentDate())
        date_row.addWidget(self.date_input)
        date_row.addStretch()
        layout.addLayout(date_row)

        self.submit_task_button = QPushButton("Add Task")
        self.submit_task_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.submit_task_button.clicked.connect(self._on_task_submit)
        layout.addWidget(self.submit_task_button)

        return tab

    def _build_thought_tab(self) -> QWidget:
        tab = QWidget()
        tab.setStyleSheet("background: transparent;")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(6)
        tab.setLayout(layout)

        self.thought_input = QTextEdit()
        self.thought_input.setPlaceholderText("What's on your mind?")
        self.thought_input.setAcceptRichText(False)
        self.thought_input.setFixedHeight(90)
        layout.addWidget(self.thought_input)

        self.submit_thought_button = QPushButton("Save Thought")
        self.submit_thought_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.submit_thought_button.clicked.connect(self._on_thought_submit)
        layout.addWidget(self.submit_thought_button)

        return tab

    def _setup_style(self):
        c = _c()
        t = _t()

        input_style = f"""
            QLineEdit, QTextEdit {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 3px;
                color: {t.ink_primary};
                font-size: 10px;
                padding: 5px 6px;
            }}
            QLineEdit:focus, QTextEdit:focus {{
                border: 1px solid {t.accent};
            }}
        """
        label_style = f"""
            QLabel {{
                color: {c.FRAME_LIGHT.name()};
                font-size: 9px;
                background: transparent;
            }}
        """
        button_style = f"""
            QPushButton {{
                background-color: {t.button_primary_bg};
                border: 1px solid {t.accent};
                border-radius: 3px;
                color: {t.button_primary_text};
                font-size: 10px;
                font-weight: bold;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                background-color: {t.button_primary_hover};
                border-color: {t.accent_light};
            }}
        """
        tab_style = f"""
            QTabWidget {{
                background: transparent;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar {{
                background: transparent;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {t.ink_secondary};
                font-size: 10px;
                padding: 4px 0px;
                border: none;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {t.ink_primary};
                border-bottom: 2px solid {t.accent};
            }}
            QTabBar::tab:hover:!selected {{
                color: {t.ink_primary};
            }}
        """

        self.title_input.setStyleSheet(input_style)
        self.reminder_time_input.setStyleSheet(input_style)
        self.thought_input.setStyleSheet(input_style)
        self._time_label.setStyleSheet(label_style)
        self._date_label.setStyleSheet(label_style)
        self.submit_task_button.setStyleSheet(button_style)
        self.submit_thought_button.setStyleSheet(button_style)
        self._tabs.setStyleSheet(tab_style)

    # ------------------------------------------------------------------
    # Submission handlers
    # ------------------------------------------------------------------

    def _on_task_submit(self):
        title = self.title_input.text().strip()
        if not title:
            return

        try:
            qdate = self.date_input.date()
            reminder_minutes = self._parse_optional_time(self.reminder_time_input.text())
            hour = reminder_minutes // 60 if reminder_minutes is not None else 0
            minute = reminder_minutes % 60 if reminder_minutes is not None else 0
            scheduled_dt = datetime(qdate.year(), qdate.month(), qdate.day(), hour, minute, 0)
            reminder_at = scheduled_dt if reminder_minutes is not None else None

            TaskService.create_standalone_task(title, scheduled_dt, reminder_at=reminder_at)

            self.title_input.clear()
            self.reminder_time_input.clear()
            self.date_input.setDate(QDate.currentDate())
            self.task_created.emit()
            self.close()

        except Exception:
            logger.exception("Error creating task")

    def _on_thought_submit(self):
        content = self.thought_input.toPlainText().strip()
        if not content:
            return

        try:
            NoteService.create_thought(content)
            self.thought_input.clear()
            self.thought_created.emit()
            self.close()

        except Exception:
            logger.exception("Error saving thought")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_optional_time(value: str):
        text = value.strip()
        if not text:
            return None
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("Reminder time must be in HH:MM format")
        hours = int(parts[0])
        minutes = int(parts[1])
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError("Reminder time must be between 00:00 and 23:59")
        return hours * 60 + minutes

    def paintEvent(self, event):
        """Draw rounded background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)

        c = _c()
        bg = QColor(c.FRAME_DARK)
        bg.setAlpha(230)
        painter.fillPath(path, bg)
        painter.setPen(c.ACCENT)
        painter.drawPath(path)

    def show_at_position(self, pos: QPoint):
        """Show the widget at the specified position, clamped to screen bounds."""
        # Re-evaluate "today" on every open; the popup lives for the whole
        # session, so a date captured at construction goes stale across days.
        self.date_input.setDate(QDate.currentDate())
        self.adjustSize()

        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        x = max(geo.left(), min(pos.x(), geo.right() - self.width()))
        y = max(geo.top(), min(pos.y(), geo.bottom() - self.height()))

        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()
        if self._tabs.currentIndex() == 1:
            self.thought_input.setFocus()
        else:
            self.title_input.setFocus()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)
