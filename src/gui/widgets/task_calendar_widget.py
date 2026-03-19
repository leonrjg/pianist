"""
Task Calendar Widget - Custom calendar with task indicators.

Reusable calendar widget that shows dots for days with tasks.
"""

from PyQt6.QtWidgets import QCalendarWidget, QWidget
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QTextCharFormat
from typing import Dict, List


class TaskCalendarWidget(QCalendarWidget):
    """Custom calendar widget with task indicators"""

    day_clicked = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks_by_date: Dict[QDate, List[dict]] = {}
        self._max_tasks_per_day = 1
        self._setup_style()

        # Remove weekend highlighting
        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor(70, 50, 35))  # Same as regular days
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_format)

        # Connect to selectionChanged for date changes, clicked for re-raising popup
        self.selectionChanged.connect(self._on_selection_changed)
        self.clicked.connect(self._on_date_clicked)

    def _setup_style(self):
        """Apply vintage styling to the calendar"""
        from .sheet_pages.vintage_styles import VINTAGE_MENU_STYLE

        # Build the complete stylesheet
        complete_style = """
            QCalendarWidget {
                background-color: rgb(255, 252, 245);
                border: 2px solid rgb(184, 134, 11);
                border-radius: 4px;
            }

            /* Navigation bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: rgb(201, 147, 78);
                border-radius: 3px;
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
        """Override to paint day number and task indicator dot, vertically stacked"""
        painter.save()

        # Determine if this is the selected date
        is_selected = (date == self.selectedDate())

        # Determine if this is current month
        is_current_month = (date.month() == self.monthShown() and date.year() == self.yearShown())

        # Background for selected date
        if is_selected:
            painter.fillRect(rect, QColor(184, 134, 11, 180))

        # Text color
        if is_selected:
            text_color = QColor(255, 252, 245)
        elif is_current_month:
            text_color = QColor(70, 50, 35)
        else:
            text_color = QColor(150, 140, 120)

        # Check if this date has tasks
        qdate = QDate(date.year(), date.month(), date.day())
        has_tasks = qdate in self._tasks_by_date

        # Calculate layout - number on top, dot below, both centered
        dot_size = 5
        spacing = 2
        number_height = 14  # Approximate height for the number

        if has_tasks:
            # Total height of number + spacing + dot
            total_height = number_height + spacing + dot_size
            top_y = rect.center().y() - total_height // 2
        else:
            top_y = rect.center().y() - number_height // 2

        # Draw the day number
        painter.setPen(text_color)
        number_rect = rect.adjusted(0, 0, 0, 0)
        number_rect.setTop(top_y)
        number_rect.setHeight(number_height)
        painter.drawText(number_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, str(date.day()))

        # Draw dot if has tasks
        if has_tasks:
            tasks = self._tasks_by_date[qdate]
            task_count = len(tasks)

            # Calculate dot opacity based on task count
            if self._max_tasks_per_day > 0:
                intensity = task_count / self._max_tasks_per_day
            else:
                intensity = 0

            # Dot position - centered below the number
            dot_x = rect.center().x()
            dot_y = top_y + number_height + spacing + dot_size // 2

            # Color: brass with varying opacity (stark difference)
            base_color = QColor(184, 134, 11)
            alpha = int(20 + (235 * intensity * intensity))  # Quadratic for starker contrast
            dot_color = QColor(base_color.red(), base_color.green(), base_color.blue(), min(alpha, 255))

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(dot_color)
            painter.drawEllipse(int(dot_x - dot_size // 2), int(dot_y - dot_size // 2), dot_size, dot_size)

        painter.restore()

    def _on_selection_changed(self):
        """Handle selection change - update popup content"""
        pass

    def _on_date_clicked(self, date: QDate):
        """Handle any click - ensure popup stays visible"""
        self.day_clicked.emit(date)
