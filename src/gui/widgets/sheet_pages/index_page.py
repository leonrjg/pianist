"""
Index Page - Main directory showing list of habits and navigation options.
"""

from PyQt6.QtGui import QFont

from core.util.time import get_friendly_datetime
from .base_page import SheetPage

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.analytics import get_upcoming_tasks


class IndexPage(SheetPage):
    """Index page showing upcoming tasks"""

    def get_page_title(self) -> str:
        return "Next Tasks"

    def get_page_type(self) -> str:
        return "index"

    def build_content(self):
        """Build the index page content"""
        layout = self.layout()

        habits = list(Habit.select().order_by(Habit.display_order, Habit.name))

        # Page title
        title = self._create_section_header(self.get_page_title())
        layout.addWidget(title)

        # Load and display upcoming tasks
        self._build_upcoming_tasks_section(layout, habits)

        layout.addStretch()


    def _build_upcoming_tasks_section(self, layout, habits):
        """Build and display the upcoming tasks section"""
        from datetime import datetime

        try:
            # Get upcoming tasks for the next 7 days
            timespan = 7 * 24 * 60 * 60  # 7 days in seconds
            upcoming_tasks = get_upcoming_tasks(habits, timespan)

            if upcoming_tasks:
                # Build text block with all tasks
                task_lines = []
                for task in upcoming_tasks[:10]:
                    habit = task['habit']
                    task_dt = task['datetime']
                    time_str = get_friendly_datetime(task_dt)
                    task_lines.append(f"• {habit.name} ({habit.schedule})")
                    task_lines.append(f"    {time_str}\n")

                # Create single text label with all tasks
                tasks_text = "\n".join(task_lines)
                tasks_label = self._create_text_label(tasks_text)
                layout.addWidget(tasks_label)
            else:
                tasks_label = self._create_text_label("No upcoming tasks in the next 7 days.", secondary=True)
                layout.addWidget(tasks_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading tasks: {e}", secondary=True)
            layout.addWidget(error_label)

