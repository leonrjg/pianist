"""
Reminder Page - List view of all reminders with creation button.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QScrollArea, QHBoxLayout
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .reminder_card import ReminderCard
from .vintage_form_widgets import VintageButton

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.reminder.service import ReminderService as _ReminderService


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


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
        desc.setStyleSheet(f"color: {_t().ink_secondary}; font-size: 12px; margin-bottom: 16px;")
        layout.addWidget(desc)

        # New reminder button
        new_btn = VintageButton("+ New Reminder", parent=self)
        new_btn.clicked.connect(lambda: self.navigate_to.emit('reminder_detail', None))
        layout.addWidget(new_btn)

        # Mute section
        layout.addSpacing(8)
        layout.addWidget(self._create_separator())
        layout.addSpacing(4)
        self._build_mute_section(layout)

        # Reminders list
        reminders = _ReminderService.get_all()

        if not reminders:
            no_reminders_label = QLabel("No reminders yet. Create one to get started!")
            no_reminders_label.setStyleSheet(f"color: {_t().ink_secondary}; font-style: italic; margin-top: 24px;")
            layout.addWidget(no_reminders_label)
        else:
            for reminder in reminders:
                card = ReminderCard(reminder, self)
                card.toggle_enabled.connect(self._toggle_reminder)
                card.edit_clicked.connect(self._edit_reminder)
                card.trigger_now.connect(self._trigger_reminder)
                layout.addWidget(card)

        layout.addStretch()

    def _get_reminder_manager(self):
        """Get the reminder manager from the top-level window."""
        return getattr(self.window(), 'reminder_manager', None)

    def _build_mute_section(self, layout):
        """Build the mute reminders controls."""
        rm = self._get_reminder_manager()

        mute_label = QLabel("Mute all reminders")
        mute_label.setStyleSheet(f"color: {_t().ink_primary}; font-weight: bold; font-size: 12px;")
        layout.addWidget(mute_label)

        if rm and rm.is_muted:
            status = QLabel("Reminders are currently muted.")
            status.setStyleSheet(f"color: {_t().ink_secondary}; font-style: italic; font-size: 11px;")
            layout.addWidget(status)

            unmute_btn = VintageButton("Unmute", button_type="secondary", parent=self)
            unmute_btn.clicked.connect(self._unmute)
            layout.addWidget(unmute_btn)
        else:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            for label, hours in [("1 h", 1), ("4 h", 4), ("24 h", 24), ("Indefinitely", None)]:
                btn = VintageButton(label, button_type="secondary", parent=self)
                btn.clicked.connect(lambda _, h=hours: self._mute(h))
                row_layout.addWidget(btn)

            row_layout.addStretch()
            layout.addWidget(row)

    def _mute(self, hours):
        rm = self._get_reminder_manager()
        if rm:
            rm.mute(hours)
        self.refresh()

    def _unmute(self):
        rm = self._get_reminder_manager()
        if rm:
            rm.unmute()
        self.refresh()

    def _toggle_reminder(self, reminder):
        """Toggle reminder enabled state."""
        from core.reminder.service import ReminderService
        ReminderService.toggle_enabled(reminder)
        self.navigate_to.emit('reminders', None)

    def _edit_reminder(self, reminder):
        """Navigate to edit page."""
        self.navigate_to.emit('reminder_detail', reminder.id)

    def _trigger_reminder(self, reminder):
        """Manually trigger a reminder now."""
        from core.reminder.service import ReminderService

        fresh_reminder = ReminderService.get_by_id(reminder.id)
        ReminderService.fire_reminder(fresh_reminder, record_fire=False)

        # Refresh the page
        self.content_updated.emit()
