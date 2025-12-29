"""
Activity Page - View recent habit activity log.
"""

from .base_page import SheetPage
from .activity_card import ActivityCard

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit


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
        title = self._create_section_header(self.get_page_title())
        layout.addWidget(title)

        try:
            # Get all habits
            habits = list(Habit.select())
            if not habits:
                no_habits_label = self._create_text_label("No habits yet.", secondary=True)
                layout.addWidget(no_habits_label)
                layout.addStretch()
                return

            # Collect all buckets from all habits
            all_buckets = []
            for habit in habits:
                buckets = habit.get_activity_buckets()
                for bucket in buckets[:10]:  # Take up to 10 most recent per habit
                    all_buckets.append((habit, bucket))

            if not all_buckets:
                no_activity_label = self._create_text_label("No recent activity.", secondary=True)
                layout.addWidget(no_activity_label)
            else:
                # Sort by bucket end time (most recent first)
                all_buckets.sort(key=lambda x: x[1].end, reverse=True)

                # Display up to 20 most recent activities
                for habit, bucket in all_buckets[:20]:
                    card = ActivityCard(
                        habit,
                        bucket,
                        on_navigate=self._navigate_to_habit,
                        parent=self
                    )
                    layout.addWidget(card)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading activity: {e}", secondary=True)
            layout.addWidget(error_label)

    def _navigate_to_habit(self, habit):
        """Navigate to habit detail page"""
        self.navigate_to.emit('habit_detail', habit.id)

