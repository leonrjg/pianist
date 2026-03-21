"""
Index Page - Main directory showing list of habits and navigation options.
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtGui import QFont
from datetime import datetime, timedelta

from core.util.time import get_friendly_datetime
from .base_page import SheetPage
from .habit_card import HabitCard

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.task import get_upcoming_tasks, get_past_tasks, Task
from core.task.service import TaskService


class IndexPage(SheetPage):
    """Index page showing upcoming tasks"""

    def get_page_title(self) -> str:
        return "Next Tasks"

    def get_page_type(self) -> str:
        return "index"

    def build_content(self):
        """Build the index page content"""
        layout = self.layout()

        _service = getattr(self.window(), 'service', None)
        habits = sorted(_service.get_all_habits(), key=lambda h: h.name) if _service else []

        title = self._create_section_header("Tasks")
        layout.addWidget(title)

        # Past tasks section (only if configured)
        try:
            from core.settings.service import SettingsService
            past_days = int(SettingsService.get('index.past_days', 0))
        except Exception:
            past_days = 0

        if past_days > 0:
            self._build_past_tasks_section(layout, habits, past_days)

        self._build_upcoming_tasks_section(layout, habits)
        layout.addStretch()


    def _build_past_tasks_section(self, layout, habits, past_days: int):
        """Build and display past tasks from the last N days."""
        try:
            lookback = past_days * 24 * 60 * 60
            past_tasks = get_past_tasks(habits=habits, lookback_seconds=lookback,
                                        include_manual=True, include_completed=True)
            if not past_tasks:
                return

            separator = self._create_separator()
            layout.addWidget(separator)
            past_header = self._create_text_label("Past", secondary=True)
            layout.addWidget(past_header)

            grouped = self._group_tasks_by_day(past_tasks)
            for day_label, tasks in grouped:
                header = self._create_day_header(day_label)
                layout.addWidget(header)
                for task in tasks:
                    accent_color = self._get_urgency_color(task.scheduled_at)
                    card = HabitCard(
                        task=task,
                        subtitle=get_friendly_datetime(task.scheduled_at),
                        accent_color=accent_color,
                        on_click=self._navigate_to_habit if task.habit else None,
                        on_complete=self._on_task_completion_toggled,
                        parent=self
                    )
                    layout.addWidget(card)
                layout.addSpacing(8)

            separator2 = self._create_separator()
            layout.addWidget(separator2)
        except Exception as e:
            error_label = self._create_text_label(f"Error loading past tasks: {e}", secondary=True)
            layout.addWidget(error_label)

    def _build_upcoming_tasks_section(self, layout, habits):
        """Build and display the upcoming tasks section"""
        try:
            timespan = 30 * 24 * 60 * 60
            upcoming_tasks = get_upcoming_tasks(
                habits=habits,
                timespan=timespan,
                include_manual=True,
                include_completed=True
            )

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
                        # Get urgency color
                        accent_color = self._get_urgency_color(task.scheduled_at)

                        # Use Task-based API
                        card = HabitCard(
                            task=task,
                            subtitle=get_friendly_datetime(task.scheduled_at),
                            accent_color=accent_color,
                            on_click=self._navigate_to_habit if task.habit else None,
                            on_complete=self._on_task_completion_toggled,
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
            task_date = task.scheduled_at.date()

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
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        label = QLabel(f"♪ {text}")
        font = QFont(label.font().family(), 12)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"""
            color: {t.ink_primary};
            padding: 6px 0px 4px 0px;
            background: transparent;
        """)
        return label

    def _get_urgency_color(self, task_dt):
        """Get accent color based on task urgency"""
        from gui.themes.manager import ThemeManager
        colors = ThemeManager.get_instance().current.urgency_colors
        now = datetime.now()
        hours_until = (task_dt - now).total_seconds() / 3600

        if hours_until < 0:
            return colors[0]   # Overdue
        elif hours_until < 2:
            return colors[1]   # Soon
        elif hours_until < 24:
            return colors[2]   # Today
        else:
            return colors[3]   # Future

    def _navigate_to_habit(self, habit):
        """Navigate to habit detail page"""
        self.navigate_to.emit('habit_detail', habit.id)

    def _on_task_completion_toggled(self, habit, task_datetime, new_state):
        """Handle task completion toggle - create/update/delete ManualTask"""
        try:
            normalized_dt = task_datetime.replace(microsecond=0)

            if habit is not None:
                _service = getattr(self.window(), 'service', None)
                if _service:
                    _service.toggle_task_completion(habit, normalized_dt)
            else:
                TaskService.toggle_standalone_task_completion(normalized_dt, new_state)

            self.refresh()
            self.content_updated.emit()

        except Exception as e:
            print(f"Error toggling task completion: {e}")

