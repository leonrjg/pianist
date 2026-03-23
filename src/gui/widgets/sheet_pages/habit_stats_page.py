"""
Habit Statistics Page - Detailed statistics with calendar contribution graph for a single habit.
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QScrollArea
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .calendar_graph import CalendarGraph
from .stat_card import StatCard
from ..themed_dropdown import ThemedDropdown
from .activity_card import ActivityCard

# Import database models and analytics
from core.habit.service import HabitService
from core.util.time import get_friendly_elapsed
from core import analytics


from gui.themes import current_theme as _t


class HabitStatsPage(SheetPage):
    """Statistics page with calendar graph for individual habit"""

    def __init__(self, habit_id=None, service=None, parent=None):
        self.habit_id = habit_id
        self.service = service
        self.habit = None
        self._calendar_graph = None
        self._calendar_container = None
        self._time_range_dropdown = None
        self._time_card = None
        self._productivity_card = None
        self._consistency_card = None
        self._summary_container = None
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
                self.habit = self.service.get_non_deleted_by_id(self.habit_id)
                if self.habit is None:
                    raise ValueError("not found")
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

        t = _t()
        schedule_badge = QLabel(self.habit.schedule)
        schedule_badge.setStyleSheet(f"""
            background-color: {t.paper_dark};
            color: {t.ink_primary};
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
        range_label.setStyleSheet(f"color: {t.ink_secondary}; font-size: 10px; background: transparent;")
        time_range_layout.addWidget(range_label)

        self._time_range_dropdown = ThemedDropdown(["1 month", "6 months", "1 year"], "1 month")
        self._time_range_dropdown.selection_changed.connect(self._on_range_changed)
        time_range_layout.addWidget(self._time_range_dropdown)

        time_range_layout.addStretch()
        layout.addLayout(time_range_layout)

        layout.addSpacing(8)

        # Summary stats cards container
        self._summary_container = QWidget()
        self._summary_container.setStyleSheet("background: transparent;")
        summary_container_layout = QVBoxLayout()
        summary_container_layout.setContentsMargins(0, 0, 0, 0)
        summary_container_layout.setSpacing(4)
        self._summary_container.setLayout(summary_container_layout)
        layout.addWidget(self._summary_container, 0)  # 0 stretch factor - don't expand

        # Build summary section
        self._build_summary_section(days_back=30)

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

        # Recent activity section
        activity_header = self._create_section_header("Recent Activity")
        layout.addWidget(activity_header)

        self._build_activity_section(layout)

        layout.addSpacing(8)

        # Footer links
        layout.addWidget(self._create_separator())

        footer_layout = QHBoxLayout()

        edit_link = self._create_link_label("✏️ Edit Habit", lambda: self.navigate_to.emit('habit_detail', self.habit.id))
        footer_layout.addWidget(edit_link)

        footer_layout.addStretch()

        layout.addLayout(footer_layout)

        layout.addStretch()

    def _build_summary_section(self, days_back=365):
        """Build summary statistics cards for the given time range"""
        # Clear container
        container_layout = self._summary_container.layout()
        
        # Remove existing cards if any
        if self._time_card:
            container_layout.removeWidget(self._time_card)
            self._time_card.deleteLater()
            self._time_card = None
        if self._productivity_card:
            container_layout.removeWidget(self._productivity_card)
            self._productivity_card.deleteLater()
            self._productivity_card = None
        if self._consistency_card:
            container_layout.removeWidget(self._consistency_card)
            self._consistency_card.deleteLater()
            self._consistency_card = None

        # Filter buckets by time range
        from datetime import datetime, timedelta
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        buckets = self.habit.get_activity_buckets()
        filtered_buckets = [b for b in buckets if b.start >= cutoff_date]
        
        # Calculate total time
        if filtered_buckets:
            total_time = analytics.get_time_spent(filtered_buckets)
            total_time_str = get_friendly_elapsed(total_time)
        else:
            total_time_str = "00:00"

        # Calculate productivity rate (net duration / total time)
        total_net_duration = sum(b.net_duration for b in filtered_buckets)
        total_elapsed_time = sum((b.end - b.start).total_seconds() for b in filtered_buckets)
        if total_elapsed_time > 0:
            productivity_rate = total_net_duration / total_elapsed_time
            productivity_str = f"{int(productivity_rate * 100)}%"
        else:
            productivity_str = "0%"

        # Total practice time card
        self._time_card = StatCard("Practice Time", total_time_str, "⏱", parent=self)
        container_layout.addWidget(self._time_card, 0)

        # Productivity card
        self._productivity_card = StatCard("Productivity", productivity_str, "⚡", parent=self)
        container_layout.addWidget(self._productivity_card, 0)

        # Consistency card
        self._consistency_card = StatCard("Consistency", "0%", "📊", parent=self)
        container_layout.addWidget(self._consistency_card, 0)

        container_layout.addStretch()

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

        # Rebuild summary section with new time range
        self._build_summary_section(days_back)
        
        # Rebuild calendar in the container
        self._build_calendar(days_back)

    def _build_activity_section(self, layout):
        """Build recent activity list with compact cards"""
        buckets = self.habit.get_activity_buckets()

        if not buckets:
            no_activity_label = self._create_text_label("No activity yet.", secondary=True)
            layout.addWidget(no_activity_label)
            return

        # Show up to 10 most recent buckets
        for bucket in buckets[:10]:
            card = ActivityCard(self.habit, bucket, service=self.service, compact=True, parent=self)
            layout.addWidget(card)

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
