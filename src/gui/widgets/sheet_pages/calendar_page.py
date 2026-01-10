"""
Calendar Page - Calendar view with task scheduling.

Shows a styled calendar with dots indicating scheduled tasks.
Clicking a day shows a popup with tasks for that day.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QCalendarWidget, QLabel, 
                              QLineEdit, QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QDate, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QTextCharFormat, QFont
from datetime import datetime, timedelta
from typing import Dict, List

from .base_page import SheetPage
from .vintage_styles import VINTAGE_MENU_STYLE

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.analytics import get_upcoming_tasks


class TaskPopup(QWidget):
    """Vertical popup showing tasks for a selected day."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the popup UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(3)
        self.setLayout(layout)

        # Task input at top
        self._task_input = QLineEdit()
        self._task_input.setPlaceholderText("Add task...")
        self._task_input.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 252, 245, 220);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 2px;
                color: rgb(70, 50, 35);
                font-size: 9px;
                padding: 3px 5px;
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
        layout.addWidget(self._task_input)

        # Scroll area for tasks list
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgb(61, 40, 23);
                width: 6px;
                margin: 2px;
                border: none;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: rgb(184, 134, 11);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgb(218, 165, 32);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: transparent;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        # Container for task items
        self._tasks_container = QWidget()
        self._tasks_container.setStyleSheet("background: transparent;")
        self._tasks_layout = QVBoxLayout()
        self._tasks_layout.setContentsMargins(0, 0, 0, 0)
        self._tasks_layout.setSpacing(2)
        self._tasks_container.setLayout(self._tasks_layout)

        scroll_area.setWidget(self._tasks_container)
        layout.addWidget(scroll_area)

        # Set fixed size for popup - very compact
        self.setFixedSize(180, 240)

    def set_tasks(self, date: QDate, tasks: List[dict]):
        """
        Set the tasks to display for a given date.
        
        Args:
            date: The date these tasks are for
            tasks: List of task dicts with 'habit' and 'datetime' keys
        """
        # Clear existing tasks
        while self._tasks_layout.count():
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add date header with better contrast
        date_str = date.toString("MMM d")
        header = QLabel(date_str)
        header.setStyleSheet("""
            color: rgb(255, 252, 245);
            font-size: 10px;
            font-weight: bold;
            background: transparent;
            padding: 1px 0px;
        """)
        self._tasks_layout.addWidget(header)

        # Add tasks
        if tasks:
            for task in tasks:
                task_widget = self._create_task_widget(task)
                self._tasks_layout.addWidget(task_widget)
        else:
            no_tasks_label = QLabel("No tasks")
            no_tasks_label.setStyleSheet("""
                color: rgb(200, 185, 160);
                font-size: 8px;
                font-style: italic;
                background: transparent;
                padding: 2px 1px;
            """)
            self._tasks_layout.addWidget(no_tasks_label)

        self._tasks_layout.addStretch()

    def _create_task_widget(self, task: dict) -> QWidget:
        """Create a widget for a single task"""
        widget = QFrame()
        widget.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        widget.setLayout(layout)

        # Habit name
        habit = task['habit']
        completed = task.get('completed', False)
        
        # Add checkmark to name if completed
        name_text = f"✓ {habit.name}" if completed else habit.name
        name_label = QLabel(name_text)
        name_label.setStyleSheet("""
            QLabel {
                color: rgb(70, 50, 35);
                font-size: 10px;
                font-weight: bold;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        # Time and schedule on one line
        task_dt = task['datetime']
        time_str = task_dt.strftime("%I:%M %p").lstrip('0')
        detail_label = QLabel(f"{time_str} • {habit.schedule}")
        detail_label.setStyleSheet("""
            QLabel {
                color: rgb(110, 90, 70);
                font-size: 9px;
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }
        """)
        layout.addWidget(detail_label)

        return widget

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
        """Show the popup at the specified position"""
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Handle close event"""
        self.closed.emit()
        super().closeEvent(event)


class CalendarWheelFilter(QWidget):
    """Event filter that blocks wheel events on calendar's internal view"""
    
    def __init__(self, calendar, parent=None):
        super().__init__(parent)
        self._calendar = calendar
        self._scroll_area = None
        
        # Find and install filter on all child widgets that might handle wheel events
        from PyQt6.QtWidgets import QAbstractItemView, QTableView
        for child in calendar.findChildren(QWidget):
            child.installEventFilter(self)
    
    def set_scroll_area(self, scroll_area):
        self._scroll_area = scroll_area
    
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Wheel:
            # Forward to scroll area
            if self._scroll_area:
                scrollbar = self._scroll_area.verticalScrollBar()
                if scrollbar:
                    delta = event.angleDelta().y()
                    scrollbar.setValue(scrollbar.value() - delta)
            return True  # Block the event from reaching the calendar
        return False


class TaskCalendarWidget(QCalendarWidget):
    """Custom calendar widget with task indicators"""

    day_clicked = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks_by_date: Dict[QDate, List[dict]] = {}
        self._max_tasks_per_day = 1
        self._setup_style()
        
        # Connect the built-in clicked signal
        self.clicked.connect(self._on_date_clicked)

    def _setup_style(self):
        """Apply vintage styling to the calendar"""
        # Build the complete stylesheet
        complete_style = """
            QCalendarWidget {
                background-color: rgb(255, 252, 245);
                border: 2px solid rgb(184, 134, 11);
                border-radius: 4px;
            }
            
            /* Navigation bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: rgb(184, 134, 11);
                border-bottom: 1px solid rgb(160, 115, 10);
            }
            
            /* Month/Year buttons */
            QCalendarWidget QToolButton {
                color: rgb(255, 252, 245);
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-radius: 3px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(200, 150, 30, 150);
            }
            QCalendarWidget QToolButton:pressed {
                background-color: rgba(160, 115, 10, 150);
            }
            
            /* Vertical arrow buttons */
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
            }
            
            /* Header (day names) */
            QCalendarWidget QWidget {
                alternate-background-color: rgb(245, 240, 225);
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: rgb(255, 252, 245);
                color: rgb(70, 50, 35);
                font-size: 11px;
                selection-background-color: rgba(184, 134, 11, 180);
                selection-color: rgb(255, 252, 245);
            }
            
            /* Day cells */
            QCalendarWidget QAbstractItemView {
                gridline-color: rgb(230, 220, 200);
            }
            
            /* Header row with day names */
            QCalendarWidget QHeaderView::section {
                background-color: rgba(200, 185, 160, 120);
                color: rgb(70, 50, 35);
                font-size: 9px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 1px solid rgb(200, 185, 160);
            }
            
            /* Today's date */
            QCalendarWidget QAbstractItemView:enabled {
                background-color: rgb(255, 252, 245);
            }
        """
        
        # Append the shared menu style for calendar dropdowns
        complete_style += "\n" + VINTAGE_MENU_STYLE.replace("QMenu", "QCalendarWidget QMenu")
        
        self.setStyleSheet(complete_style)

    def set_tasks(self, tasks_by_date: Dict[QDate, List[dict]]):
        """
        Set tasks to display on the calendar.
        
        Args:
            tasks_by_date: Dictionary mapping QDate to list of task dicts
        """
        self._tasks_by_date = tasks_by_date
        
        # Calculate max tasks per day for dot intensity
        if tasks_by_date:
            self._max_tasks_per_day = max(len(tasks) for tasks in tasks_by_date.values())
        else:
            self._max_tasks_per_day = 1
        
        # Update the display
        self.updateCells()

    def paintCell(self, painter, rect, date):
        """Override to paint task indicators below day numbers"""
        # Call parent to draw the day number
        super().paintCell(painter, rect, date)
        
        # Check if this date has tasks
        qdate = QDate(date.year(), date.month(), date.day())
        if qdate in self._tasks_by_date:
            tasks = self._tasks_by_date[qdate]
            task_count = len(tasks)
            
            # Calculate dot opacity based on task count (darker = more tasks)
            if self._max_tasks_per_day > 0:
                intensity = task_count / self._max_tasks_per_day
            else:
                intensity = 0
            
            # Draw dot below the day number (at the very bottom of the cell)
            dot_size = 4
            dot_x = rect.center().x()
            dot_y = rect.bottom() - 4  # Moved closer to bottom to avoid overlapping number
            
            # Color: brass with varying opacity
            base_color = QColor(184, 134, 11)
            alpha = int(100 + (155 * intensity))  # Range from 100 to 255
            dot_color = QColor(base_color.red(), base_color.green(), base_color.blue(), alpha)
            
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(dot_x - dot_size // 2, dot_y - dot_size // 2, dot_size, dot_size)

    def _on_date_clicked(self, date: QDate):
        """Handle date click from built-in signal"""
        self.day_clicked.emit(date)


class CalendarPage(SheetPage):
    """Calendar page showing scheduled tasks"""

    def __init__(self, parent=None):
        self._calendar = None
        self._popup = None
        self._wheel_filter = None
        self._pending_date = None  # Date to show after popup closes
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Calendar"

    def get_page_type(self) -> str:
        return "calendar"

    def build_content(self):
        """Build the calendar page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header("Calendar")
        layout.addWidget(title)

        # Description
        desc = self._create_text_label("Click a day to view scheduled tasks", secondary=True)
        layout.addWidget(desc)

        layout.addSpacing(8)

        # Create custom calendar widget
        self._calendar = TaskCalendarWidget(self)
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.setNavigationBarVisible(True)
        
        # Install wheel event filter to redirect scrolling to page
        self._wheel_filter = CalendarWheelFilter(self._calendar, self)
        
        # Load tasks and update calendar
        self._load_tasks()
        
        # Connect day click signal
        self._calendar.day_clicked.connect(self._on_day_clicked)
        
        layout.addWidget(self._calendar)
        layout.addStretch()

        # Create popup (hidden initially)
        self._popup = TaskPopup()
        self._popup.closed.connect(self._on_popup_closed)

    def _load_tasks(self):
        """Load upcoming tasks and organize by date"""
        try:
            # Get all habits
            habits = list(Habit.select())
            
            # Get upcoming tasks for next 365 days
            timespan = 365 * 24 * 60 * 60
            upcoming_tasks = get_upcoming_tasks(habits, timespan)
            
            # Group tasks by date
            tasks_by_date: Dict[QDate, List[dict]] = {}
            for task in upcoming_tasks:
                task_dt = task['datetime']
                qdate = QDate(task_dt.year, task_dt.month, task_dt.day)
                
                if qdate not in tasks_by_date:
                    tasks_by_date[qdate] = []
                tasks_by_date[qdate].append(task)
            
            # Update calendar
            self._calendar.set_tasks(tasks_by_date)
            
        except Exception as e:
            print(f"Error loading tasks: {e}")
            import traceback
            traceback.print_exc()

    def _on_day_clicked(self, date: QDate):
        """Handle day click - show popup with tasks"""
        # If popup is visible, store the date and let it close first
        if self._popup.isVisible():
            self._pending_date = date
            self._popup.close()
            return
        
        self._show_popup_for_date(date)

    def _show_popup_for_date(self, date: QDate):
        """Show popup with tasks for the given date"""
        tasks = self._calendar._tasks_by_date.get(date, [])
        self._popup.set_tasks(date, tasks)
        
        # Calculate popup position (to the right of the calendar)
        calendar_global_pos = self._calendar.mapToGlobal(QPoint(0, 0))
        calendar_rect = self._calendar.rect()
        
        popup_x = calendar_global_pos.x() + calendar_rect.width() + 10
        popup_y = calendar_global_pos.y()
        
        self._popup.show_at_position(QPoint(popup_x, popup_y))

    def _on_popup_closed(self):
        """Handle popup close - show pending date if any"""
        if self._pending_date:
            date = self._pending_date
            self._pending_date = None
            # Use timer to show after close completes
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._show_popup_for_date(date))

    def showEvent(self, event):
        """Set up scroll area reference when page is shown"""
        super().showEvent(event)
        if self._calendar and self._wheel_filter:
            from PyQt6.QtWidgets import QScrollArea
            parent = self._calendar.parent()
            while parent:
                if isinstance(parent, QScrollArea):
                    self._wheel_filter.set_scroll_area(parent)
                    break
                parent = parent.parent()

    def hideEvent(self, event):
        """Clean up when page is hidden"""
        if self._popup:
            self._popup.close()
        self._pending_date = None
        super().hideEvent(event)

    def refresh(self):
        """Refresh the calendar with updated tasks"""
        if self._popup:
            self._popup.close()
        self._pending_date = None
        if self._calendar:
            self._load_tasks()
        super().refresh()
