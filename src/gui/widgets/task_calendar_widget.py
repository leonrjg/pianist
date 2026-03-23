"""
Task Calendar Widget - Custom calendar with task indicators.

Reusable calendar widget that shows dots for days with tasks.
"""

from PyQt6.QtWidgets import QCalendarWidget, QWidget
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QTextCharFormat
from typing import Dict, List


from gui.themes.color import parse_color as _parse_rgb


class TaskCalendarWidget(QCalendarWidget):
    """Custom calendar widget with task indicators"""

    day_clicked = pyqtSignal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tasks_by_date: Dict[QDate, List[dict]] = {}
        self._ical_by_date: Dict[QDate, List] = {}
        self._max_tasks_per_day = 1
        self._setup_style()

        # Remove weekend highlighting
        weekend_format = QTextCharFormat()
        from gui.themes.manager import ThemeManager
        weekend_format.setForeground(_parse_rgb(ThemeManager.get_instance().current.ink_primary))
        self.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_format)
        self.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_format)

        # Connect to selectionChanged for date changes, clicked for re-raising popup
        self.selectionChanged.connect(self._on_selection_changed)
        self.clicked.connect(self._on_date_clicked)

    def _setup_style(self):
        """Apply theme-aware styling to the calendar."""
        from gui.themes.manager import ThemeManager
        from .sheet_pages.theme_styles import get_menu_stylesheet
        t = ThemeManager.get_instance().current

        complete_style = f"""
            QCalendarWidget {{
                background-color: {t.paper};
                border: 2px solid {t.accent};
                border-radius: 4px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {t.accent};
                border-radius: 3px;
                border-bottom: 1px solid {t.accent_dark};
            }}
            QCalendarWidget QToolButton {{
                color: {t.paper};
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-radius: 3px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {t.accent_light};
            }}
            QCalendarWidget QToolButton:pressed {{
                background-color: {t.accent_dark};
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {t.paper_dark};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: {t.paper};
                color: {t.ink_primary};
                font-size: 11px;
                selection-background-color: {t.accent};
                selection-color: {t.paper};
            }}
            QCalendarWidget QAbstractItemView {{
                gridline-color: {t.border};
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: {t.paper_dark};
                color: {t.ink_primary};
                font-size: 9px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 1px solid {t.border};
            }}
        """
        complete_style += "\n" + get_menu_stylesheet().replace("QMenu", "QCalendarWidget QMenu")
        self.setStyleSheet(complete_style)

    def set_tasks(self, tasks_by_date: Dict[QDate, List[dict]]):
        """Set tasks to display on the calendar."""
        self._tasks_by_date = tasks_by_date
        if tasks_by_date:
            self._max_tasks_per_day = max(len(tasks) for tasks in tasks_by_date.values())
        else:
            self._max_tasks_per_day = 1
        self.updateCells()

    def set_ical_events(self, ical_by_date: Dict[QDate, List]):
        """Set ICAL events to display on the calendar (rendered as small diamonds)."""
        self._ical_by_date = ical_by_date
        self.updateCells()

    def paintCell(self, painter, rect, date):
        """Override to paint day number, task dot, and ICAL diamond."""
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current

        painter.save()
        is_selected = (date == self.selectedDate())
        is_current_month = (date.month() == self.monthShown() and date.year() == self.yearShown())

        if is_selected:
            painter.fillRect(rect, _parse_rgb(t.accent, 180))

        if is_selected:
            text_color = _parse_rgb(t.paper)
        elif is_current_month:
            text_color = _parse_rgb(t.ink_primary)
        else:
            text_color = _parse_rgb(t.ink_secondary)

        qdate = QDate(date.year(), date.month(), date.day())
        has_tasks = qdate in self._tasks_by_date
        has_ical = qdate in self._ical_by_date

        dot_size = 5
        ical_size = 4
        spacing = 2
        number_height = 14
        indicator_size = max(dot_size, ical_size)

        total_height = number_height + (spacing + indicator_size if (has_tasks or has_ical) else 0)
        top_y = rect.center().y() - total_height // 2

        # Day number
        painter.setPen(text_color)
        number_rect = rect.adjusted(0, 0, 0, 0)
        number_rect.setTop(top_y)
        number_rect.setHeight(number_height)
        painter.drawText(number_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, str(date.day()))

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)

        # Horizontal indicator row below number
        if has_tasks or has_ical:
            indicator_y = top_y + number_height + spacing

            total_width = 0
            if has_tasks:
                total_width += dot_size
            if has_ical:
                if has_tasks:
                    total_width += spacing
                total_width += ical_size

            current_x = rect.center().x() - total_width // 2

            # Task dot (circle)
            if has_tasks:
                task_count = len(self._tasks_by_date[qdate])
                intensity = task_count / max(self._max_tasks_per_day, 1)
                alpha = int(20 + 235 * intensity * intensity)
                painter.setBrush(_parse_rgb(t.accent, min(alpha, 255)))
                dot_cx = current_x + dot_size // 2
                dot_cy = indicator_y + dot_size // 2
                painter.drawEllipse(int(dot_cx - dot_size // 2), int(dot_cy - dot_size // 2), dot_size, dot_size)
                current_x += dot_size + spacing

            # ICAL diamond (small rotated square)
            if has_ical:
                events = self._ical_by_date[qdate]
                # Use color of first event's source
                event_color = events[0].color if events else t.link
                from PyQt6.QtGui import QPolygon
                from PyQt6.QtCore import QPoint as QP
                cx = current_x + ical_size // 2
                cy = int(indicator_y + ical_size // 2)
                half = ical_size // 2 + 1
                diamond = QPolygon([QP(cx, cy - half), QP(cx + half, cy), QP(cx, cy + half), QP(cx - half, cy)])
                painter.setBrush(_parse_rgb(event_color, 200))
                painter.drawPolygon(diamond)

        painter.restore()

    def _on_selection_changed(self):
        """Handle selection change - update popup content"""
        pass

    def _on_date_clicked(self, date: QDate):
        """Handle any click - ensure popup stays visible"""
        self.day_clicked.emit(date)
