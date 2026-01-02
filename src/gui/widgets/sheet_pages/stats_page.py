"""
Stats Page - View habit statistics and analytics.
"""

from PyQt6.QtWidgets import QHBoxLayout, QLabel
from PyQt6.QtGui import QFont

from .base_page import SheetPage
from .stat_card import StatCard
from .habit_stat_card import HabitStatCard
from .champion_banner import ChampionBanner

# Import database models and analytics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed, get_friendly_datetime
from core import analytics
from datetime import datetime


class StatsPage(SheetPage):
    """Statistics page showing habit analytics"""

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
            habits = list(Habit.select())
            if not habits:
                no_habits_label = self._create_text_label("No habits yet.", secondary=True)
                layout.addWidget(no_habits_label)
                return

            # At-a-glance summary cards
            self._build_summary_section(layout, habits)

            layout.addSpacing(8)

            # Champion habit spotlight
            self._build_champion_section(layout, habits)

            layout.addSpacing(8)

            # Section header for habit performance
            perf_header = self._create_section_header("Performance")
            layout.addWidget(perf_header)

            # Individual habit stat cards
            self._build_habit_stats_section(layout, habits)

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

    def _navigate_to_habit(self, habit):
        """Navigate to habit statistics page"""
        self.navigate_to.emit('habit_stats', habit.id)
