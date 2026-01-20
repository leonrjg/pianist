"""
Reminder Page - List view of all reminders with creation button.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QScrollArea
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .reminder_card import ReminderCard
from .vintage_form_widgets import VintageButton

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.reminder.reminder import Reminder


class ReminderPage(SheetPage):
    """Page displaying list of all reminders"""

    def get_page_title(self) -> str:
        return "Reminders"

    def get_page_type(self) -> str:
        return "reminders"

    def build_content(self):
        """Build the reminders list"""
        layout = self.layout()

        # Header
        header = self._create_section_header("🔔 Reminders")
        layout.addWidget(header)

        # Description
        desc = QLabel("Manage your spaced repetition and stochastic reminders")
        desc.setStyleSheet("color: rgb(110, 90, 70); font-size: 12px; margin-bottom: 16px;")
        layout.addWidget(desc)

        # New reminder button
        new_btn = VintageButton("+ New Reminder", parent=self)
        new_btn.clicked.connect(lambda: self.navigate_to.emit('reminder_detail', None))
        layout.addWidget(new_btn)

        # Reminders list
        reminders = Reminder.select().order_by(Reminder.created_at.desc())

        if not reminders:
            no_reminders_label = QLabel("No reminders yet. Create one to get started!")
            no_reminders_label.setStyleSheet("color: rgb(110, 90, 70); font-style: italic; margin-top: 24px;")
            layout.addWidget(no_reminders_label)
        else:
            for reminder in reminders:
                card = ReminderCard(reminder, self)
                card.toggle_enabled.connect(self._toggle_reminder)
                card.edit_clicked.connect(self._edit_reminder)
                card.trigger_now.connect(self._trigger_reminder)
                layout.addWidget(card)

        layout.addStretch()

    def _toggle_reminder(self, reminder):
        """Toggle reminder enabled state."""
        reminder.is_enabled = not reminder.is_enabled
        reminder.save()
        self.navigate_to.emit('reminders', None)

    def _edit_reminder(self, reminder):
        """Navigate to edit page."""
        self.navigate_to.emit('reminder_detail', reminder.id)

    def _trigger_reminder(self, reminder):
        """Manually trigger a reminder now."""
        from core.reminder.service import ReminderService

        fresh_reminder = Reminder.get_by_id(reminder.id)
        ReminderService.fire_reminder(fresh_reminder, record_fire=False)

        # Refresh the page
        self.content_updated.emit()
