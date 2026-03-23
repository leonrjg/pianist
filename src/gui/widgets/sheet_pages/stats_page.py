"""
Stats Page - View habit statistics and analytics.
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from PyQt6.QtGui import QFont

from .base_page import SheetPage
from .stat_card import StatCard
from .habit_stat_card import HabitStatCard
from .champion_banner import ChampionBanner
from .calendar_graph import CalendarGraph
from ..themed_dropdown import ThemedDropdown
from .activity_card import ActivityCard

from core.habit.service import HabitService
from core.util.time import get_friendly_elapsed, get_friendly_datetime
from core import analytics


from gui.themes import current_theme as _t


class StatsPage(SheetPage):
    """Statistics page showing habit analytics"""

    def __init__(self, service=None, parent=None):
        self.service = service
        self._calendar_graph = None
        self._calendar_container = None
        self._time_range_dropdown = None
        self._all_habits = []
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Statistics"

    def get_page_type(self) -> str:
        return "stats"

    def build_content(self):
        """Build the stats page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header("Statistics")
        layout.addWidget(title)

        try:
            habits = self.service.get_all_non_deleted()
            self._all_habits = habits
            
            if not habits:
                no_habits_label = self._create_text_label("No habits yet.", secondary=True)
                layout.addWidget(no_habits_label)
                return

            # Time range selector
            time_range_layout = QHBoxLayout()
            time_range_layout.setSpacing(6)

            range_label = QLabel("Show:")
            range_label.setStyleSheet(f"color: {_t().ink_secondary}; font-size: 10px; background: transparent;")
            time_range_layout.addWidget(range_label)

            self._time_range_dropdown = ThemedDropdown(["1 month", "6 months", "1 year"], "1 month")
            self._time_range_dropdown.selection_changed.connect(self._on_range_changed)
            time_range_layout.addWidget(self._time_range_dropdown)

            time_range_layout.addStretch()
            layout.addLayout(time_range_layout)
            layout.addSpacing(8)

            # At-a-glance summary cards
            self._build_summary_section(layout, habits)

            layout.addSpacing(8)

            # Champion habit spotlight
            self._build_champion_section(layout, habits)

            layout.addSpacing(8)

            # Calendar section
            calendar_header = self._create_section_header("Activity Graph")
            layout.addWidget(calendar_header)

            # Create calendar container
            self._calendar_container = QWidget()
            self._calendar_container.setStyleSheet("background: transparent;")
            calendar_container_layout = QVBoxLayout()
            calendar_container_layout.setContentsMargins(0, 0, 0, 0)
            calendar_container_layout.setSpacing(0)
            self._calendar_container.setLayout(calendar_container_layout)
            layout.addWidget(self._calendar_container)

            # Build calendar graph
            self._build_calendar(days_back=30)

            layout.addSpacing(8)

            # Recent activity section
            activity_header = self._create_section_header("Recent Activity")
            layout.addWidget(activity_header)

            self._build_activity_section(layout, habits)

            layout.addSpacing(8)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading statistics: {e}", secondary=True)
            layout.addWidget(error_label)

        layout.addStretch()

    def _build_summary_section(self, layout, habits):
        """Build the at-a-glance summary cards section"""
        # Calculate global stats
        total_time_seconds = 0
        total_sessions = 0

        for habit in habits:
            buckets = habit.get_activity_buckets()
            if buckets:
                total_time_seconds += analytics.get_time_spent(buckets)
                total_sessions += len(buckets)

        # Create summary cards in a horizontal layout
        summary_layout = QHBoxLayout()
        summary_layout.setSpacing(4)

        # Total practice time card
        total_time_str = get_friendly_elapsed(total_time_seconds) if total_time_seconds > 0 else "0h 0m"
        time_card = StatCard("Practice Time", total_time_str, "⏱", parent=self)
        summary_layout.addWidget(time_card)

        # Total sessions card
        sessions_card = StatCard("Sessions", str(total_sessions), "📊", parent=self)
        summary_layout.addWidget(sessions_card)

        layout.addLayout(summary_layout)

    def _build_champion_section(self, layout, habits):
        """Build the champion habit spotlight banner"""
        try:
            champion = analytics.get_habit_with_longest_streak(habits)
            if champion:
                streak = champion.get_longest_streak()
                completion_rate = analytics.get_completion_rate(champion)

                banner = ChampionBanner(
                    champion,
                    streak=streak,
                    completion_rate=completion_rate,
                    on_click=self._navigate_to_habit,
                    parent=self
                )
                layout.addWidget(banner)
        except:
            pass  # Skip if no champion can be determined

    def _build_habit_stats_section(self, layout, habits):
        """Build the individual habit statistics cards"""
        # Sort by completion rate (best first)
        sorted_habits = analytics.sort_habits_by_completion_rate(habits)

        for habit, completion_rate in sorted_habits:
            # Gather stats for this habit
            buckets = habit.get_activity_buckets()

            stats = {
                'completion_rate': completion_rate,
                'streak': habit.get_longest_streak(),
            }

            if buckets:
                total_time = analytics.get_time_spent(buckets)
                stats['total_time'] = get_friendly_elapsed(total_time)
                stats['session_count'] = len(buckets)

            # Create card
            card = HabitStatCard(
                habit,
                stats=stats,
                on_click=self._navigate_to_habit,
                parent=self
            )
            layout.addWidget(card)

    def _build_calendar(self, days_back=365):
        """Build calendar graph with aggregated data from all habits"""
        # Clear container
        container_layout = self._calendar_container.layout()

        # Remove existing calendar if any
        if self._calendar_graph:
            container_layout.removeWidget(self._calendar_graph)
            self._calendar_graph.deleteLater()
            self._calendar_graph = None

        # Collect all buckets from all habits
        all_buckets = []
        for habit in self._all_habits:
            buckets = habit.get_activity_buckets()
            if buckets:
                all_buckets.extend(buckets)

        if not all_buckets:
            no_data_label = self._create_text_label("Start practicing to see your calendar!", secondary=True)
            container_layout.addWidget(no_data_label)
            return

        # Create calendar graph with aggregated data (habit=None)
        self._calendar_graph = CalendarGraph(None, all_buckets, days_back, parent=self)
        container_layout.addWidget(self._calendar_graph)

    def _on_range_changed(self, range_str: str):
        """Handle time range selection change"""
        days_back = self._get_days_back(range_str)
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

    def _build_activity_section(self, layout, habits):
        """Build recent activity list with activity cards"""
        # Collect all buckets from all habits
        all_buckets = []
        for habit in habits:
            buckets = habit.get_activity_buckets()
            for bucket in buckets[:10]:  # Take up to 10 most recent per habit
                all_buckets.append((habit, bucket))

        if not all_buckets:
            no_activity_label = self._create_text_label("No recent activity.", secondary=True)
            layout.addWidget(no_activity_label)
            return

        # Sort by bucket end time (most recent first)
        all_buckets.sort(key=lambda x: x[1].end, reverse=True)

        # Display up to 20 most recent activities
        for habit, bucket in all_buckets[:20]:
            card = ActivityCard(
                habit,
                bucket,
                service=self.service,
                on_navigate=self._navigate_to_habit,
                parent=self
            )
            layout.addWidget(card)

    def _navigate_to_habit(self, habit):
        """Navigate to habit detail page"""
        self.navigate_to.emit('habit_detail', habit.id)
