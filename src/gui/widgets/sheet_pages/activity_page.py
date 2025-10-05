"""
Activity Page - View recent habit activity log.
"""

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .base_page import SheetPage

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed, get_friendly_datetime


class ActivityPage(SheetPage):
    """Activity page showing recent habit activity"""

    def get_page_title(self) -> str:
        return "Recent Activity"

    def get_page_type(self) -> str:
        return "activity"

    def build_content(self):
        """Build the activity page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header("Recent Activity")
        layout.addWidget(title)

        # Text edit for activity display
        activity_text = QTextEdit()
        activity_text.setReadOnly(True)
        activity_text.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Generate activity text
        activity_content = self._generate_activity_text()
        activity_text.setText(activity_content)
        layout.addWidget(activity_text)

        # Bottom navigation
        layout.addWidget(self._create_separator())

        back_link = self._create_link_label("← Back to Index", lambda: self.go_back.emit())
        layout.addWidget(back_link)

    def _generate_activity_text(self) -> str:
        """Generate recent activity text"""
        habits = list(Habit.select())
        if not habits:
            return "No habits found."

        lines = []

        # Get recent buckets from all habits
        all_buckets = []
        for habit in habits:
            buckets = habit.get_activity_buckets()
            for bucket in buckets[-5:]:  # Last 5 per habit
                all_buckets.append((habit, bucket))

        # Sort by end time
        all_buckets.sort(key=lambda x: x[1].end, reverse=True)

        if not all_buckets:
            lines.append("No recent activity")
        else:
            for habit, bucket in all_buckets[:15]:  # Show last 15
                scale = habit.get_schedule().get_scale()
                start = get_friendly_datetime(bucket.start, scale)
                duration = get_friendly_elapsed(bucket.net_duration)
                lines.append(f"• {habit.name}")
                lines.append(f"  {start} ({duration}, {bucket.sessions} sessions)")
                lines.append("")

        return "\n".join(lines)

