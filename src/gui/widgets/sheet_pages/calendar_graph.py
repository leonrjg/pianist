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
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.bucket import Bucket


class CalendarGraph(QFrame):
    """GitHub-style calendar contribution graph"""

    # Day abbreviations for left labels
    DAY_LABELS = ["S", "M", "T", "W", "T", "F", "S"]  # Sunday to Saturday

    # Month abbreviations
    MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    def __init__(self, habit, buckets: List[Bucket], days_back: int = 365, parent=None):
        """
        Args:
            habit: Habit object
            buckets: List of activity buckets
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

        main_layout.addWidget(grid_widget, alignment=Qt.AlignmentFlag.AlignLeft)

        # Add legend
        self._add_legend(main_layout)

    def _add_month_labels(self, layout: QGridLayout):
        """Add month labels at top of calendar"""
        current_month = None
        col = 0

        # Calculate weeks
        num_cells = len(self.grid_data)
        num_weeks = num_cells // 7

        for week in range(num_weeks):
            # Get first day of this week (index 0 = Sunday)
            week_start_date = self.grid_data[week * 7][0]
            month = week_start_date.month

            # Check if this week has any activity
            week_has_activity = any(
                self.grid_data[week * 7 + day][1] > 0  # duration > 0
                for day in range(7)
                if week * 7 + day < len(self.grid_data)
            )

            # Add label at start of each new month only if there's activity in this week
            if month != current_month and week_has_activity:
                month_label = QLabel(self.MONTH_LABELS[month - 1])
                month_label.setStyleSheet("""
                    color: rgb(110, 90, 70);
                    font-size: 9px;
                    background: transparent;
                """)
                layout.addWidget(month_label, 0, col, Qt.AlignmentFlag.AlignLeft)
                current_month = month

            col += 1

    def _add_day_labels(self, layout: QGridLayout):
        """Add day abbreviations on left side"""
        for day in range(7):
            day_label = QLabel(self.DAY_LABELS[day])
            day_label.setStyleSheet("""
                color: rgb(110, 90, 70);
                font-size: 9px;
                background: transparent;
            """)
            day_label.setFixedWidth(12)
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

        # Legend label
        less_label = QLabel("Less")
        less_label.setStyleSheet("color: rgb(110, 90, 70); font-size: 9px; background: transparent;")
        legend_layout.addWidget(less_label, 0, 0)

        # Color boxes
        colors = [
            CalendarCell.COLOR_NONE,
            CalendarCell.COLOR_SOME,
            CalendarCell.COLOR_GOOD,
        ]

        for i, color in enumerate(colors):
            box = QFrame()
            box.setFixedSize(8, 8)
            box.setStyleSheet(f"""
                background-color: {color.name(QColor.NameFormat.HexArgb)};
                border: 1px solid rgb(200, 185, 160);
                border-radius: 1px;
            """)
            legend_layout.addWidget(box, 0, i + 1)

        # More label
        more_label = QLabel("More")
        more_label.setStyleSheet("color: rgb(110, 90, 70); font-size: 9px; background: transparent;")
        legend_layout.addWidget(more_label, 0, len(colors) + 1)

        layout.addWidget(legend_widget, alignment=Qt.AlignmentFlag.AlignLeft)
