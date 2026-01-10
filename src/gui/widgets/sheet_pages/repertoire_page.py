"""
Repertoire Page - List of all habits.
"""

from datetime import datetime

from PyQt6.QtGui import QFont

from .base_page import SheetPage
from .habit_card import HabitCard

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit
from core.util.time import get_friendly_datetime


class RepertoirePage(SheetPage):
    """Repertoire page showing list of all habits"""

    def get_page_title(self) -> str:
        return "Repertoire"

    def get_page_type(self) -> str:
        return "repertoire"

    def build_content(self):
        """Build the repertoire page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header(self.get_page_title())
        layout.addWidget(title)

        # Load habits from database
        try:
            habits = list(Habit.select().order_by(Habit.display_order, Habit.name))

            if habits:
                for habit in habits:
                    # Get next scheduled task
                    schedule = habit.get_schedule()
                    next_task = schedule.get_next_task(datetime.now())
                    if next_task:
                        scale = schedule.get_scale()
                        subtitle = f"Next: {get_friendly_datetime(next_task, scale)}"
                    else:
                        subtitle = habit.schedule
                    
                    # Create habit card with next task info
                    card = HabitCard(
                        habit,
                        subtitle=subtitle,
                        on_click=self._navigate_to_habit,
                        parent=self
                    )
                    layout.addWidget(card)
            else:
                no_habits_label = self._create_text_label("No habits yet.", secondary=True)
                layout.addWidget(no_habits_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading habits: {e}", secondary=True)
            layout.addWidget(error_label)

        layout.addStretch()

    def _navigate_to_habit(self, habit):
        """Navigate to habit detail page"""
        self.navigate_to.emit('habit_detail', habit.id)
