"""
Calendar Graph - GitHub-style contribution calendar for habit activity.
"""

from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QScrollArea, QWidget, QVBoxLayout
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt
from datetime import datetime, timedelta, date
from typing import List

from .calendar_cell import CalendarCell

# Import database models
import sys


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.bucket import Bucket


class CalendarGraph(QFrame):
    """GitHub-style calendar contribution graph"""

    # Day abbreviations for left labels
    DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    # Month abbreviations
    MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def __init__(self, habit, buckets: List[Bucket], days_back: int = 365, parent=None):
        """
        Args:
            habit: Habit object (or None for aggregated view of all habits)
            buckets: List of activity buckets (from single habit or all habits)
            days_back: Number of days to display (30, 180, or 365)
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.buckets = buckets
        self.days_back = days_back

        # Calculate threshold (50% of max duration)
        self.threshold = self._calculate_threshold()

        # Build grid data
        self.grid_data = self._build_grid_data()

        self._setup_ui()

    def _calculate_threshold(self) -> int:
        """Calculate threshold as 50% of max practice duration"""
        if not self.buckets:
            return 0

        max_duration = max(bucket.net_duration for bucket in self.buckets)
        return max_duration // 2 if max_duration > 0 else 0

    def _build_grid_data(self) -> List[tuple]:
        """
        Build grid data mapping dates to durations.
        Returns: List of (date, duration, sessions) tuples
        """
        # Generate date range (today backwards)
        today = datetime.now().date()
        start_date = today - timedelta(days=self.days_back - 1)

        # Find the first Sunday before or on start_date
        days_to_sunday = (start_date.weekday() + 1) % 7  # Convert Monday=0 to Sunday=0
        grid_start = start_date - timedelta(days=days_to_sunday)

        # Create date -> bucket mapping for fast lookup
        # Aggregate data when multiple buckets exist for same date
        date_to_data = {}
        for bucket in self.buckets:
            # Map all dates within bucket period
            bucket_start = bucket.start.date()
            bucket_end = bucket.end.date()

            current = bucket_start
            while current <= bucket_end:
                # Distribute duration evenly across bucket days (for weekly/monthly habits)
                days_in_bucket = (bucket_end - bucket_start).days + 1
                duration_per_day = bucket.net_duration // days_in_bucket if days_in_bucket > 0 else bucket.net_duration

                # Aggregate: sum durations and sessions for same date
                if current in date_to_data:
                    existing_duration, existing_sessions = date_to_data[current]
                    date_to_data[current] = (existing_duration + duration_per_day, existing_sessions + bucket.sessions)
                else:
                    date_to_data[current] = (duration_per_day, bucket.sessions)
                
                current += timedelta(days=1)

        # Build grid (complete weeks from grid_start)
        grid = []
        current_date = grid_start
        num_weeks = (self.days_back + days_to_sunday + 6) // 7  # Round up to complete weeks

        for week in range(num_weeks):
            for day in range(7):
                data = date_to_data.get(current_date, (0, 0))
                duration, sessions = data
                grid.append((current_date, duration, sessions))
                current_date += timedelta(days=1)

        return grid

    def _setup_ui(self):
        """Setup the calendar graph UI"""
        # Main container with horizontal scroll if needed
        self.setStyleSheet("""
            CalendarGraph {
                background-color: transparent;
                border: none;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)

        # Grid container
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(0, 5, 0, 0)
        grid_layout.setSpacing(1)
        grid_widget.setLayout(grid_layout)

        # Add month labels at top
        self._add_month_labels(grid_layout)

        # Add day labels on left
        self._add_day_labels(grid_layout)

        # Add calendar cells
        self._add_cells(grid_layout)

        main_layout.addWidget(grid_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        # Add legend
        self._add_legend(main_layout)

    def _add_month_labels(self, layout: QGridLayout):
        """Add month labels at top of calendar"""
        num_cells = len(self.grid_data)
        num_weeks = num_cells // 7

        week = 0
        while week < num_weeks:
            week_start_date = self.grid_data[week * 7][0]
            month = week_start_date.month

            # Count consecutive weeks in this month
            span = 1
            while week + span < num_weeks:
                next_week_date = self.grid_data[(week + span) * 7][0]
                if next_week_date.month != month:
                    break
                span += 1

            # Add label spanning all weeks of this month
            month_label = QLabel(self.MONTH_LABELS[month - 1])
            _tc = _t()
            month_label.setStyleSheet(f"""
                color: {_tc.ink_secondary};
                font-size: 9px;
                background: transparent;
            """)
            layout.addWidget(month_label, 0, week + 1, 1, span, Qt.AlignmentFlag.AlignCenter)

            week += span

    def _add_day_labels(self, layout: QGridLayout):
        """Add day abbreviations on left side"""
        for day in range(7):
            day_label = QLabel(self.DAY_LABELS[day])
            day_label.setStyleSheet(f"""
                color: {_t().ink_secondary};
                font-size: 9px;
                background: transparent;
            """)
            day_label.setFixedWidth(20)
            layout.addWidget(day_label, day + 1, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

    def _add_cells(self, layout: QGridLayout):
        """Add calendar cells to grid"""
        for idx, (cell_date, duration, sessions) in enumerate(self.grid_data):
            week = idx // 7
            day = idx % 7

            cell = CalendarCell(cell_date, duration, sessions, self.threshold, self)
            layout.addWidget(cell, day + 1, week + 1)  # +1 to account for labels

    def _add_legend(self, layout: QVBoxLayout):
        """Add color legend below calendar"""
        legend_widget = QWidget()
        legend_widget.setStyleSheet("background: transparent;")
        legend_layout = QGridLayout()
        legend_layout.setContentsMargins(0, 4, 0, 0)
        legend_layout.setSpacing(4)
        legend_widget.setLayout(legend_layout)

        t = _t()
        label_style = f"color: {t.ink_secondary}; font-size: 9px; background: transparent;"

        # Legend label
        less_label = QLabel("Less")
        less_label.setStyleSheet(label_style)
        legend_layout.addWidget(less_label, 0, 0)

        # Color boxes — derive colors the same way CalendarCell does
        parts = t.paper_dark[4:-1].split(',')
        none_color = QColor(int(parts[0]), int(parts[1]), int(parts[2]))
        aparts = t.accent[4:-1].split(',')
        accent_c = QColor(int(aparts[0]), int(aparts[1]), int(aparts[2]))
        some_color = QColor(accent_c.red(), accent_c.green(), accent_c.blue(), 100)
        legend_colors = [none_color, some_color, accent_c]

        for i, color in enumerate(legend_colors):
            box = QFrame()
            box.setFixedSize(8, 8)
            box.setStyleSheet(f"""
                background-color: {color.name(QColor.NameFormat.HexArgb)};
                border: 1px solid {t.border};
                border-radius: 1px;
            """)
            legend_layout.addWidget(box, 0, i + 1)

        # More label
        more_label = QLabel("More")
        more_label.setStyleSheet(label_style)
        legend_layout.addWidget(more_label, 0, len(legend_colors) + 1)

        layout.addWidget(legend_widget, alignment=Qt.AlignmentFlag.AlignCenter)
