"""
Reminder Page - List view of all reminders with creation button.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget, QLabel, QScrollArea, QHBoxLayout, QCheckBox, QMessageBox
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .reminder_card import ReminderCard
from ..themed_form_widgets import ThemedButton, ThemedLineEdit

from core.reminder.service import ReminderService as _ReminderService
from core.settings.service import SettingsService


from gui.themes import current_theme as _t


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
        header = self._create_section_header("Reminders")
        layout.addWidget(header)

        # New reminder button
        new_btn = ThemedButton("+ New Reminder", parent=self)
        new_btn.clicked.connect(lambda: self.navigate_to.emit('reminder_detail', None))
        layout.addWidget(new_btn)

        # Mute section
        layout.addSpacing(8)
        layout.addWidget(self._create_separator())
        layout.addSpacing(4)
        self._build_mute_section(layout)
        layout.addSpacing(8)
        self._build_global_window_section(layout)
        layout.addSpacing(8)
        layout.addWidget(self._create_separator())
        layout.addSpacing(4)
        self._build_visibility_section(layout)
        layout.addSpacing(8)

        # Reminders list
        show_habit_linked = bool(SettingsService.get('reminders.show_habit_linked_on_page', False))
        reminders = _ReminderService.get_for_reminders_page(show_habit_linked)

        if not reminders:
            message = "No reminders yet. Create one to get started!"
            if not show_habit_linked and _ReminderService.get_for_reminders_page(True):
                message = "No standalone reminders."
            no_reminders_label = QLabel(message)
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

            unmute_btn = ThemedButton("Unmute", button_type="secondary", parent=self)
            unmute_btn.clicked.connect(self._unmute)
            layout.addWidget(unmute_btn)
        else:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)

            for label, hours in [("1 h", 1), ("4 h", 4), ("24 h", 24), ("Indefinitely", None)]:
                btn = ThemedButton(label, button_type="secondary", parent=self)
                btn.clicked.connect(lambda _, h=hours: self._mute(h))
                row_layout.addWidget(btn)

            row_layout.addStretch()
            layout.addWidget(row)

    def _build_global_window_section(self, layout):
        """Build global reminder window controls."""
        title = QLabel("Global reminder window")
        title.setStyleSheet(f"color: {_t().ink_primary}; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        enabled = QCheckBox()
        enabled.setChecked(bool(SettingsService.get('reminders.global_window_enabled', False)))
        row_layout.addWidget(enabled)

        start_edit = ThemedLineEdit("HH:MM")
        start_edit.setText(self._format_minutes(SettingsService.get('reminders.global_window_start_minute', 0)))
        start_edit.setFixedWidth(58)
        row_layout.addWidget(start_edit)

        sep = QLabel("to")
        sep.setStyleSheet(f"color: {_t().ink_secondary}; background: transparent; font-size: 11px;")
        row_layout.addWidget(sep)

        end_edit = ThemedLineEdit("HH:MM")
        end_edit.setText(self._format_minutes(SettingsService.get('reminders.global_window_end_minute', 1440)))
        end_edit.setFixedWidth(58)
        row_layout.addWidget(end_edit)

        def save_window(refresh_page=True):
            try:
                start = self._parse_time(start_edit.text(), allow_24=False)
                end = self._parse_time(end_edit.text(), allow_24=True)
            except ValueError as e:
                QMessageBox.warning(self, "Validation Error", str(e))
                return
            SettingsService.set('reminders.global_window_start_minute', start)
            SettingsService.set('reminders.global_window_end_minute', end)
            self.content_updated.emit()
            if refresh_page:
                self.refresh()

        def on_enabled_changed(state):
            SettingsService.set('reminders.global_window_enabled', bool(state))
            save_window()

        enabled.stateChanged.connect(on_enabled_changed)
        start_edit.editingFinished.connect(lambda: save_window())
        end_edit.editingFinished.connect(lambda: save_window())
        row_layout.addStretch()
        layout.addWidget(row)

    def _build_visibility_section(self, layout):
        """Build list visibility controls."""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        show_linked = QCheckBox()
        show_linked.setChecked(bool(SettingsService.get('reminders.show_habit_linked_on_page', False)))
        row_layout.addWidget(show_linked)

        label = QLabel("Show habit-linked reminders")
        label.setStyleSheet(f"color: {_t().ink_primary}; background: transparent; font-size: 12px;")
        row_layout.addWidget(label)

        def on_show_linked_changed(state):
            SettingsService.set('reminders.show_habit_linked_on_page', bool(state))
            self.refresh()

        show_linked.stateChanged.connect(on_show_linked_changed)
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

    @staticmethod
    def _format_minutes(total_minutes: int) -> str:
        total_minutes = int(total_minutes)
        if total_minutes == 1440:
            return "24:00"
        hours = max(0, total_minutes) // 60
        minutes = max(0, total_minutes) % 60
        return f"{hours:02d}:{minutes:02d}"

    @staticmethod
    def _parse_time(value: str, allow_24: bool) -> int:
        text = value.strip()
        parts = text.split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            hours = int(parts[0])
            minutes = int(parts[1])
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        if hours == 24 and minutes == 0 and allow_24:
            return 1440
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError("Time must be between 00:00 and 23:59")
        if hours == 24:
            raise ValueError("Start time cannot be 24:00")
        return hours * 60 + minutes

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
