"""
Repertoire Page - List of all habits.
"""

from datetime import datetime

from PyQt6.QtGui import QFont

from .base_page import SheetPage
from .habit_card import HabitCard
from ..themed_form_widgets import ThemedButton

from core.habit.service import HabitService
from core.util.time import get_friendly_datetime


class RepertoirePage(SheetPage):
    """Repertoire page showing list of all habits"""

    def __init__(self, service=None, parent=None):
        self.service = service
        self._show_archived_only = False
        self._archived_button = None
        super().__init__(parent)

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

        # Archived button
        button_text = "Show Active" if self._show_archived_only else "Show Archived"
        self._archived_button = ThemedButton(button_text, button_type="secondary", parent=self)
        self._archived_button.clicked.connect(self._toggle_archived_view)
        layout.addWidget(self._archived_button)

        # Load habits via service
        try:
            habits = self.service.get_all_non_deleted(archived=self._show_archived_only)

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

                    # Add archived indicator if archived
                    if habit.archived:
                        subtitle = f"[ARCHIVED] {subtitle}"

                    # Create habit card with next task info
                    card = HabitCard(
                        habit=habit,
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

    def _toggle_archived_view(self):
        """Toggle between showing active habits and archived habits."""
        self._show_archived_only = not self._show_archived_only
        # Rebuild the page content to switch views
        self.refresh()
