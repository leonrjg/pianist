"""
Calendar Page - Calendar view with task scheduling.

Shows a styled calendar with dots indicating scheduled tasks.
Clicking a day shows a popup with tasks for that day.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QCalendarWidget, QLabel,
                              QLineEdit, QPushButton, QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QDate, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QTextCharFormat, QFont, QCursor
from datetime import datetime, timedelta
from typing import Dict, List

from .base_page import SheetPage
from .vintage_styles import VINTAGE_MENU_STYLE
from ..task_calendar_widget import TaskCalendarWidget

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from core.analytics import get_tasks_in_range
from core.db import db


class TaskPopup(QWidget):
    """Popup showing tasks for a selected day."""

    closed = pyqtSignal()
    task_created = pyqtSignal()  # Signal when a new task is created

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._current_date = None  # Track which date we're showing tasks for
        self._setup_ui()

        # Fade animation
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(150)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.InOutQuad)

    def _setup_ui(self):
        """Setup the popup UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        self.setLayout(layout)

        # Task input row at top
        input_row = QWidget()
        input_row.setStyleSheet("background: transparent;")
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(4)
        input_row.setLayout(input_layout)

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
        # Connect Enter key to submit
        self._task_input.returnPressed.connect(self._on_add_task)
        input_layout.addWidget(self._task_input)

        # Add button
        add_btn = QPushButton("+")
        add_btn.setFixedSize(20, 20)
        add_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(184, 134, 11, 180);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 2px;
                color: rgb(255, 252, 245);
                font-size: 12px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: rgba(218, 165, 32, 200);
                border-color: rgb(218, 165, 32);
            }
            QPushButton:pressed {
                background-color: rgba(160, 115, 10, 200);
            }
        """)
        add_btn.clicked.connect(self._on_add_task)
        input_layout.addWidget(add_btn)

        layout.addWidget(input_row)

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
        self._current_date = date  # Store current date for task creation

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

    def _on_add_task(self):
        """Handle adding a new manual task"""
        title = self._task_input.text().strip()

        if not title or not self._current_date:
            return

        try:
            # Convert QDate to datetime at start of day
            scheduled_dt = datetime(
                self._current_date.year(),
                self._current_date.month(),
                self._current_date.day(),
                0, 0, 0
            )

            # Create standalone manual task
            with db.atomic():
                ManualTask.create(
                    habit=None,  # Standalone task
                    title=title,
                    scheduled_at=scheduled_dt,
                    completed_at=None  # Not completed yet
                )

            # Clear input
            self._task_input.clear()

            # Emit signal to refresh calendar
            self.task_created.emit()

        except Exception as e:
            print(f"Error creating manual task: {e}")
            import traceback
            traceback.print_exc()

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
        """Show the popup at the specified position with fade in"""
        from PyQt6.QtCore import QTimer
        self.move(pos)
        self.setWindowOpacity(0)
        self.show()
        self._fade_anim.setStartValue(0)
        self._fade_anim.setEndValue(1)
        self._fade_anim.start()
        # Delay raise to happen after focus settles
        QTimer.singleShot(0, self.raise_)

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
        
        # Install on calendar itself and all children
        calendar.installEventFilter(self)
        for child in calendar.findChildren(QWidget):
            child.installEventFilter(self)
    
    def set_scroll_area(self, scroll_area):
        self._scroll_area = scroll_area
    
    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.Wheel:
            if self._scroll_area:
                scrollbar = self._scroll_area.verticalScrollBar()
                if scrollbar:
                    delta = event.angleDelta().y()
                    scrollbar.setValue(scrollbar.value() - delta)
            return True
        return False


class CalendarPage(SheetPage):
    """Calendar page showing scheduled tasks"""

    def __init__(self, parent=None):
        self._calendar = None
        self._popup = None
        self._wheel_filter = None
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Calendar"

    def get_page_type(self) -> str:
        return "calendar"

    def build_content(self):
        """Build the calendar page content"""
        layout = self.layout()

        # Create custom calendar widget
        self._calendar = TaskCalendarWidget(self)
        self._calendar.setGridVisible(True)
        self._calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._calendar.setNavigationBarVisible(True)

        # Install wheel event filter to redirect scrolling to page
        self._wheel_filter = CalendarWheelFilter(self._calendar, self)

        # Load tasks for current month
        self._load_tasks()

        # Reload tasks when month changes
        self._calendar.currentPageChanged.connect(self._on_month_changed)

        # Connect day click signal
        self._calendar.day_clicked.connect(self._on_day_clicked)

        layout.addWidget(self._calendar)
        layout.addStretch()

        # Create popup (hidden initially) - parent to main window to stay in hierarchy
        self._popup = TaskPopup(self.window())
        self._popup.closed.connect(self._on_popup_closed)
        self._popup.task_created.connect(self._on_task_created)

        # Close popup when focus leaves it
        from PyQt6.QtWidgets import QApplication
        QApplication.instance().focusChanged.connect(self._on_focus_changed)

    def _load_tasks(self):
        """Load tasks for currently visible month with buffer"""
        try:
            habits = list(Habit.select())
            now = datetime.now()

            # Get visible month center date
            year = self._calendar.yearShown()
            month = self._calendar.monthShown()
            center_date = datetime(year, month, 15)

            # Calculate date range ±60 days around visible month
            buffer_days = 60
            start_date = center_date - timedelta(days=buffer_days)
            end_date = center_date + timedelta(days=buffer_days)

            # Calculate timespans relative to now (schedule methods work from now)
            prev_timespan = int((now - start_date).total_seconds())
            next_timespan = int((end_date - now).total_seconds())

            # Collect tasks for each habit in range
            all_tasks = []
            for habit in habits:
                schedule = habit.get_schedule()

                # Get previous tasks (if start_date is in the past)
                if prev_timespan > 0:
                    for task in schedule.get_previous_tasks(prev_timespan):
                        if start_date <= task <= end_date:
                            all_tasks.append({
                                'habit': habit,
                                'datetime': task,
                                'completed': habit.is_task_completed(task)
                            })

                # Get next tasks (if end_date is in the future)
                if next_timespan > 0:
                    for task in schedule.get_next_tasks(next_timespan):
                        if start_date <= task <= end_date:
                            all_tasks.append({
                                'habit': habit,
                                'datetime': task,
                                'completed': habit.is_task_completed(task)
                            })

            # Add manual tasks in the date range
            manual_tasks = ManualTask.select().where(
                (ManualTask.scheduled_at >= start_date) &
                (ManualTask.scheduled_at <= end_date)
            )

            for manual_task in manual_tasks:
                # Create a pseudo-habit object for display
                # If it has a habit, use that; otherwise create a display wrapper
                if manual_task.habit:
                    display_habit = manual_task.habit
                else:
                    # Create a simple object with name and schedule attributes for display
                    class DisplayTask:
                        def __init__(self, title):
                            self.name = title
                            self.schedule = "manual"

                    display_habit = DisplayTask(manual_task.title or "Untitled")

                all_tasks.append({
                    'habit': display_habit,
                    'datetime': manual_task.scheduled_at,
                    'completed': manual_task.is_completed
                })

            # Group tasks by date
            tasks_by_date: Dict[QDate, List[dict]] = {}
            for task in all_tasks:
                task_dt = task['datetime']
                qdate = QDate(task_dt.year, task_dt.month, task_dt.day)

                if qdate not in tasks_by_date:
                    tasks_by_date[qdate] = []
                tasks_by_date[qdate].append(task)

            self._calendar.set_tasks(tasks_by_date)

        except Exception as e:
            print(f"Error loading tasks: {e}")
            import traceback
            traceback.print_exc()

    def _on_month_changed(self, year: int, month: int):
        """Reload tasks when user navigates to different month"""
        self._load_tasks()

    def _on_day_clicked(self, date: QDate):
        """Handle day click - show popup with tasks"""
        tasks = self._calendar._tasks_by_date.get(date, [])
        self._popup.set_tasks(date, tasks)
        
        # Calculate popup position (to the right of the calendar)
        calendar_global_pos = self._calendar.mapToGlobal(QPoint(0, 0))
        calendar_rect = self._calendar.rect()
        
        popup_x = calendar_global_pos.x() + calendar_rect.width() + 10
        popup_y = calendar_global_pos.y()
        
        self._popup.show_at_position(QPoint(popup_x, popup_y))

    def _on_popup_closed(self):
        """Handle popup close"""
        pass

    def _on_task_created(self):
        """Handle new task creation - reload calendar and update popup"""
        self._load_tasks()
        # Refresh popup with updated tasks for current date
        if self._popup.isVisible() and self._popup._current_date:
            tasks = self._calendar._tasks_by_date.get(self._popup._current_date, [])
            self._popup.set_tasks(self._popup._current_date, tasks)

    def _on_focus_changed(self, old, new):
        """Close popup when focus moves outside of it"""
        if self._popup and self._popup.isVisible():
            # Check if new focus is not within the popup
            if new is None or not self._popup.isAncestorOf(new):
                self._popup.close()

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
        """Close popup when page is hidden"""
        if self._popup:
            self._popup.close()
        super().hideEvent(event)

    def refresh(self):
        """Refresh the calendar with updated tasks"""
        if self._popup:
            self._popup.close()
        if self._calendar:
            self._load_tasks()
        super().refresh()
