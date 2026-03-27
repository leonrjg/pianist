"""
Wood Date Picker - Custom date picker using TaskCalendarWidget.

Shows selected date and opens TaskCalendarWidget popup when clicked.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QDate, QPoint, pyqtSignal
from PyQt6.QtGui import QCursor
from .task_calendar_widget import TaskCalendarWidget


from gui.themes import current_theme as _t, ThemedWidget


class ThemedDatePicker(QWidget, ThemedWidget):
    """Custom date picker widget with TaskCalendarWidget popup"""

    date_changed = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_date = QDate.currentDate()
        self._calendar_popup = None
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)

        # Date display button
        self._date_button = QPushButton()
        self._date_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._date_button.clicked.connect(self._show_calendar)
        layout.addWidget(self._date_button)
        self._setup_style()

        # Update button text
        self._update_button_text()

    def _setup_style(self):
        t = _t()
        self._date_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 3px;
                color: {t.ink_primary};
                font-size: 10px;
                padding: 4px 8px;
                text-align: left;
            }}
            QPushButton:hover {{
                border: 1px solid {t.accent};
                background-color: {t.paper_alt};
            }}
        """)

    def _update_button_text(self):
        """Update the button text with current date"""
        self._date_button.setText(self._current_date.toString("MMM d, yyyy"))

    def _show_calendar(self):
        """Show the calendar popup"""
        if self._calendar_popup is None:
            self._calendar_popup = TaskCalendarWidget()
            self._calendar_popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
            self._calendar_popup.setGridVisible(True)
            self._calendar_popup.setVerticalHeaderFormat(TaskCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
            self._calendar_popup.setNavigationBarVisible(True)
            self._calendar_popup.clicked.connect(self._on_date_selected)

        # Set current date
        self._calendar_popup.setSelectedDate(self._current_date)

        # Position below the button, clamped to screen bounds
        button_pos = self._date_button.mapToGlobal(self._date_button.rect().bottomLeft())
        popup_x = button_pos.x()
        popup_y = button_pos.y() + 2

        self._calendar_popup.adjustSize()
        from PyQt6.QtGui import QGuiApplication
        screen = QGuiApplication.screenAt(button_pos) or QGuiApplication.primaryScreen()
        geo = screen.availableGeometry()
        popup_x = max(geo.left(), min(popup_x, geo.right() - self._calendar_popup.width()))
        popup_y = max(geo.top(), min(popup_y, geo.bottom() - self._calendar_popup.height()))

        self._calendar_popup.move(popup_x, popup_y)
        self._calendar_popup.show()
        self._calendar_popup.raise_()
        self._calendar_popup.activateWindow()

    def _on_date_selected(self, date: QDate):
        """Handle date selection from calendar"""
        self._current_date = date
        self._update_button_text()
        self.date_changed.emit(date)
        if self._calendar_popup:
            self._calendar_popup.close()

    def date(self) -> QDate:
        """Get the currently selected date"""
        return self._current_date

    def setDate(self, date: QDate):
        """Set the current date"""
        self._current_date = date
        self._update_button_text()
