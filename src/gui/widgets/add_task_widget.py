"""
Add Task Widget - Floating task creation form.

Allows users to quickly create manual tasks with a title and scheduled date.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QDate
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QCursor
from datetime import datetime

from core.task.service import TaskService
from .themed_date_picker import ThemedDatePicker


def _c():
    from gui.constants import piano_colors
    return piano_colors()


from gui.themes import current_theme as _t, ThemedWidget


class AddTaskWidget(QWidget, ThemedWidget):
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

        self._title_label = QLabel("Add Task")
        layout.addWidget(self._title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Task title...")
        self.title_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.title_input)

        date_row = QHBoxLayout()
        date_row.setSpacing(6)

        self._date_label = QLabel("Date:")
        date_row.addWidget(self._date_label)

        self.date_input = ThemedDatePicker()
        self.date_input.setDate(QDate.currentDate())
        date_row.addWidget(self.date_input)
        date_row.addStretch()

        layout.addLayout(date_row)

        self.submit_button = QPushButton("Add Task")
        self.submit_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.submit_button.clicked.connect(self._on_submit)
        layout.addWidget(self.submit_button)

        self.setFixedWidth(200)
        self._setup_style()

    def _setup_style(self):
        c = _c()
        t = _t()
        self._title_label.setStyleSheet(f"""
            QLabel {{
                color: {c.WHITE_KEY.name()};
                font-size: 11px;
                font-weight: bold;
                background: transparent;
            }}
        """)
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 3px;
                color: {t.ink_primary};
                font-size: 10px;
                padding: 5px 6px;
            }}
            QLineEdit:focus {{
                border: 1px solid {t.accent};
            }}
        """)
        self._date_label.setStyleSheet(f"""
            QLabel {{
                color: {c.FRAME_LIGHT.name()};
                font-size: 9px;
                background: transparent;
            }}
        """)
        self.submit_button.setStyleSheet(f"""
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
        """)

    def _on_submit(self):
        """Handle task submission"""
        title = self.title_input.text().strip()

        if not title:
            return

        try:
            # Get selected date
            qdate = self.date_input.date()
            scheduled_dt = datetime(qdate.year(), qdate.month(), qdate.day(), 0, 0, 0)

            TaskService.create_standalone_task(title, scheduled_dt)

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

        c = _c()
        bg = QColor(c.FRAME_DARK)
        bg.setAlpha(230)
        painter.fillPath(path, bg)
        painter.setPen(c.ACCENT)
        painter.drawPath(path)

    def show_at_position(self, pos: QPoint):
        """Show the widget at the specified position, clamped to screen bounds"""
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
        # Focus on title input
        self.title_input.setFocus()

    def closeEvent(self, event):
        """Handle close event"""
        self.closed.emit()
        super().closeEvent(event)
