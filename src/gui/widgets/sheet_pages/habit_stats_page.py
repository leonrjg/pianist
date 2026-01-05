"""
Habit Statistics Page - Detailed statistics with calendar contribution graph for a single habit.
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .calendar_graph import CalendarGraph
from .stat_card import StatCard
from .vintage_dropdown import VintageDropdown

# Import database models and analytics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed
from core import analytics


class HabitStatsPage(SheetPage):
    """Statistics page with calendar graph for individual habit"""

    def __init__(self, habit_id=None, parent=None):
        self.habit_id = habit_id
        self.habit = None
        self._calendar_graph = None
        self._calendar_container = None
        self._time_range_dropdown = None
        super().__init__(parent)

    def get_page_title(self) -> str:
        if self.habit:
            return f"Stats: {self.habit.name}"
        return "Habit Statistics"

    def get_page_type(self) -> str:
        return "habit_stats"

    def build_content(self):
        """Build the statistics page content"""
        layout = self.layout()

        # Load habit
        if self.habit_id:
            try:
                self.habit = Habit.get_by_id(self.habit_id)
            except:
                error_label = self._create_text_label("Habit not found", secondary=True)
                layout.addWidget(error_label)
                return
        else:
            error_label = self._create_text_label("No habit specified", secondary=True)
            layout.addWidget(error_label)
            return

        # Header with habit name and schedule badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        title = self._create_section_header(self.habit.name)
        header_layout.addWidget(title)

        schedule_badge = QLabel(self.habit.schedule)
        schedule_badge.setStyleSheet("""
            background-color: rgba(200, 185, 160, 120);
            color: rgb(70, 50, 35);
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        header_layout.addWidget(schedule_badge)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # Time range selector
        time_range_layout = QHBoxLayout()
        time_range_layout.setSpacing(6)

        range_label = QLabel("Show:")
        range_label.setStyleSheet("color: rgb(110, 90, 70); font-size: 10px; background: transparent;")
        time_range_layout.addWidget(range_label)

        self._time_range_dropdown = VintageDropdown(["1 month", "6 months", "1 year"], "1 month")
        self._time_range_dropdown.selection_changed.connect(self._on_range_changed)
        time_range_layout.addWidget(self._time_range_dropdown)

        time_range_layout.addStretch()
        layout.addLayout(time_range_layout)

        layout.addSpacing(8)

        # Summary stats cards
        self._build_summary_section(layout)

        layout.addSpacing(8)

        # Calendar section
        calendar_header = self._create_section_header("Activity Graph")
        layout.addWidget(calendar_header)

        # Create calendar container to maintain position
        self._calendar_container = QWidget()
        self._calendar_container.setStyleSheet("background: transparent;")
        calendar_container_layout = QVBoxLayout()
        calendar_container_layout.setContentsMargins(0, 0, 0, 0)
        calendar_container_layout.setSpacing(0)
        self._calendar_container.setLayout(calendar_container_layout)
        layout.addWidget(self._calendar_container)

        # Build calendar graph
        self._build_calendar(days_back=60)

        layout.addSpacing(8)

        # Footer links
        layout.addWidget(self._create_separator())

        footer_layout = QHBoxLayout()

        edit_link = self._create_link_label("✏️ Edit Habit", lambda: self.navigate_to.emit('habit_detail', self.habit.id))
        footer_layout.addWidget(edit_link)

        footer_layout.addStretch()

        layout.addLayout(footer_layout)

        layout.addStretch()

    def _build_summary_section(self, layout):
        """Build summary statistics cards"""
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(4)

        # Total time
        buckets = self.habit.get_activity_buckets()
        if buckets:
            total_time = analytics.get_time_spent(buckets)
            total_time_str = get_friendly_elapsed(total_time)
        else:
            total_time_str = "00:00"

        # Total practice time card
        time_card = StatCard("Practice Time", total_time_str, "⏱", parent=self)
        summary_layout.addWidget(time_card)
        summary_layout.addStretch()

        layout.addLayout(summary_layout)

    def _build_calendar(self, days_back=365):
        """Build calendar graph with specified time range"""
        # Clear container
        container_layout = self._calendar_container.layout()

        # Remove existing calendar if any
        if self._calendar_graph:
            container_layout.removeWidget(self._calendar_graph)
            self._calendar_graph.deleteLater()
            self._calendar_graph = None

        # Get buckets
        buckets = self.habit.get_activity_buckets()

        if not buckets:
            no_data_label = self._create_text_label("Start practicing to see your calendar!", secondary=True)
            container_layout.addWidget(no_data_label)
            return

        # Create calendar graph
        self._calendar_graph = CalendarGraph(self.habit, buckets, days_back, parent=self)
        container_layout.addWidget(self._calendar_graph)

    def _build_detailed_stats(self, layout):
        """Build detailed statistics section"""
        detail_header = self._create_section_header("Detailed Statistics")
        layout.addWidget(detail_header)

        buckets = self.habit.get_activity_buckets()

        if not buckets:
            no_data_label = self._create_text_label("No data available yet.", secondary=True)
            layout.addWidget(no_data_label)
            return

        # Total sessions
        total_sessions = len(buckets)
        sessions_label = self._create_text_label(f"Total sessions: {total_sessions}", secondary=False)
        layout.addWidget(sessions_label)

        # Average session duration
        total_time = analytics.get_time_spent(buckets)
        if total_sessions > 0:
            avg_duration = total_time // total_sessions
            avg_str = get_friendly_elapsed(avg_duration)
        else:
            avg_str = "00:00"

        avg_label = self._create_text_label(f"Average session: {avg_str}", secondary=False)
        layout.addWidget(avg_label)

        # Best streak period (if there was a streak)
        longest_streak = self.habit.get_longest_streak()
        if longest_streak > 0:
            # Note: We could track actual dates of best streak, but that would require more complex logic
            # For now, just show the number
            streak_label = self._create_text_label(f"Best streak: {longest_streak} periods", secondary=False)
            layout.addWidget(streak_label)

    def _on_range_changed(self, range_str: str):
        """Handle time range selection change"""
        days_back = self._get_days_back(range_str)

        # Rebuild calendar in the container
        self._build_calendar(days_back)

    def _get_days_back(self, range_str: str) -> int:
        """Convert range string to days"""
        if range_str == "1 month":
            return 30
        elif range_str == "6 months":
            return 180
        elif range_str == "1 year":
            return 365
        else:
            return 365  # Default to 1 year
