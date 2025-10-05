"""
Stats Page - View habit statistics and analytics.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .base_page import SheetPage

# Import database models and analytics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.habit.habit_tracker import HabitTracker
from core.util.time import get_friendly_elapsed, get_friendly_datetime
from core import analytics


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

        # Text edit for monospaced stats display
        stats_text = QTextEdit()
        stats_text.setReadOnly(True)

        # Generate stats text
        stats_text.setText(self._generate_stats_text())

        layout.addWidget(stats_text)

        # Bottom navigation
        layout.addWidget(self._create_separator())

        back_link = self._create_link_label("← Back", lambda: self.go_back.emit())
        layout.addWidget(back_link)
        layout.addSpacing(4)

    def _generate_stats_text(self) -> str:
        """Generate formatted statistics text"""
        try:
            habits = list(Habit.select())
            if not habits:
                return "No habits found."

            lines = []
            for habit in habits:
                schedule = habit.get_schedule()
                scale = schedule.get_scale()

                lines.append(f"• {habit.name.upper()} ({habit.schedule})")

                from datetime import datetime
                lines.append(f"  Next: {get_friendly_datetime(schedule.get_next_task(datetime.now()), scale)}")

                # Activity stats
                buckets = habit.get_activity_buckets()
                if buckets:
                    total_time = analytics.get_time_spent(buckets)
                    lines.append(f"  Total time: {get_friendly_elapsed(total_time)}")
                    lines.append(f"  Total sessions: {len(buckets)}")
                lines.append("")

            # Global analytics
            lines.append("=== GLOBAL ANALYTICS ===\n")

            # Completion rates
            lines.append("Completion rates:")
            sorted_habits = analytics.sort_habits_by_completion_rate(habits)
            for habit, rate in sorted_habits:
                lines.append(f"  {habit.name}: {rate * 100:.1f}%")

            lines.append("")

            # Champion habit
            champion = analytics.get_habit_with_longest_streak(habits)
            lines.append(f"Longest streak: {champion.name} ({champion.get_longest_streak()} periods)")

            return "\n".join(lines)

        except Exception as e:
            return f"Error generating stats: {e}"
