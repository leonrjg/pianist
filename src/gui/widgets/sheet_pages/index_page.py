"""
Index Page - Main directory showing list of habits and navigation options.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QFont
from datetime import datetime, timedelta

from core.util.time import get_friendly_datetime
from .base_page import SheetPage
from .habit_card import HabitCard

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
        try:
            timespan = 30 * 24 * 60 * 60
            upcoming_tasks = get_upcoming_tasks(habits, timespan)

            if upcoming_tasks:
                # Group tasks by day
                grouped_tasks = self._group_tasks_by_day(upcoming_tasks)

                # Build cards for each day group
                for day_label, tasks in grouped_tasks:
                    # Day header
                    header = self._create_day_header(day_label)
                    layout.addWidget(header)

                    # Task cards for this day
                    for task in tasks:
                        habit = task['habit']
                        task_dt = task['datetime']
                        completed = task.get('completed', False)

                        # Create subtitle with time and schedule
                        time_str = get_friendly_datetime(task_dt)
                        subtitle = f"{time_str} • {habit.schedule}"

                        # Get urgency color
                        accent_color = self._get_urgency_color(task_dt)

                        card = HabitCard(
                            habit,
                            subtitle=subtitle,
                            accent_color=accent_color,
                            on_click=self._navigate_to_habit,
                            completed=completed,
                            parent=self
                        )
                        layout.addWidget(card)

                    # Add spacing between day groups
                    layout.addSpacing(8)
            else:
                tasks_label = self._create_text_label("No upcoming tasks in the next 7 days.", secondary=True)
                layout.addWidget(tasks_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading tasks: {e}", secondary=True)
            layout.addWidget(error_label)

    def _group_tasks_by_day(self, tasks):
        """Group tasks by day with friendly labels"""
        now = datetime.now()
        today = now.date()
        tomorrow = (now + timedelta(days=1)).date()

        grouped = {}
        for task in tasks[:100]:
            task_date = task['datetime'].date()

            # Create friendly label
            if task_date == today:
                label = get_friendly_datetime(datetime.now())
            elif task_date == tomorrow:
                label = get_friendly_datetime(datetime.now() + timedelta(days=1))
            else:
                label = get_friendly_datetime(task_date)

            if label not in grouped:
                grouped[label] = []
            grouped[label].append(task)

        return list(grouped.items())

    def _create_day_header(self, text):
        """Create a styled day header"""
        label = QLabel(f"♪ {text}")
        # Use the application's default font family with larger size
        font = QFont(label.font().family(), 12)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("""
            color: rgb(70, 50, 35);
            padding: 6px 0px 4px 0px;
            background: transparent;
        """)
        return label

    def _get_urgency_color(self, task_dt):
        """Get accent color based on task urgency"""
        now = datetime.now()
        hours_until = (task_dt - now).total_seconds() / 3600

        if hours_until < 0:
            return "rgb(160, 50, 50)"  # Overdue - reddish
        elif hours_until < 2:
            return "rgb(184, 134, 11)"  # Soon - brass
        elif hours_until < 24:
            return "rgb(140, 110, 80)"  # Today - brown
        else:
            return "rgb(200, 185, 160)"  # Future - light sepia

    def _navigate_to_habit(self, habit):
        """Navigate to habit detail page"""
        self.navigate_to.emit('habit_detail', habit.id)

