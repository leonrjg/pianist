"""
Reminder Detail Page - Create/edit reminder with full configuration.
"""

from datetime import datetime
from PyQt6.QtWidgets import QVBoxLayout, QMessageBox, QWidget, QTextEdit
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .vintage_dropdown import VintageDropdown
from .vintage_form_widgets import (
    VintageLineEdit, VintageSpinBox, VintageButton,
    FormSection, VintageCheckBox
)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.db import db
from core.reminder.reminder import Reminder
from core.schedule.sm2 import SM2Scheduler
from core.schedule.stochastic import StochasticScheduler
from core.habit.habit import Habit


class ReminderDetailPage(SheetPage):
    """Detail page for creating/editing a reminder"""

    def __init__(self, reminder_id=None, parent=None):
        self.reminder_id = reminder_id
        self.reminder = None

        # Form fields
        self._name_edit = None
        self._type_dropdown = None
        self._action_dropdown = None
        self._payload_edit = None
        self._notification_dropdown = None

        # SR fields
        self._ease_spin = None
        self._interval_spin = None

        # Stochastic fields
        self._rate_spin = None
        self._weight_spin = None

        # Habit link
        self._habit_dropdown = None

        # Dynamic sections
        self._sr_section = None
        self._stochastic_section = None

        super().__init__(parent)

    def get_page_title(self) -> str:
        if self.reminder:
            return f"Edit: {self.reminder.name}"
        return "New Reminder"

    def get_page_type(self) -> str:
        return "reminder_detail"

    def build_content(self):
        """Build the reminder detail form"""
        layout = self.layout()

        # Load reminder if editing
        if self.reminder_id:
            try:
                self.reminder = Reminder.get_by_id(self.reminder_id)
            except:
                error_label = self._create_text_label("Reminder not found", secondary=True)
                layout.addWidget(error_label)
                return

        # Page title
        title = self._create_section_header("New Reminder" if not self.reminder else self.reminder.name)
        layout.addWidget(title)

        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_widget.setLayout(form_layout)

        # Basic Information Section
        basic_section = FormSection("Basic Information")

        self._name_edit = VintageLineEdit("e.g., Review vocabulary")
        if self.reminder:
            self._name_edit.setText(self.reminder.name)
        basic_section.add_field("Name:", self._name_edit)

        types = ['sr', 'stochastic']
        default_type = self.reminder.reminder_type if self.reminder else 'sr'
        self._type_dropdown = VintageDropdown(types, default_type)
        self._type_dropdown.selection_changed.connect(self._on_type_changed)
        basic_section.add_field("Type:", self._type_dropdown)

        form_layout.addWidget(basic_section)

        # Action Section
        action_section = FormSection("Action")

        actions = ['open_link', 'random_line', 'show_text']
        default_action = self.reminder.action_type if self.reminder else 'show_text'
        self._action_dropdown = VintageDropdown(actions, default_action)
        action_section.add_field("Action:", self._action_dropdown)

        self._payload_edit = QTextEdit()
        self._payload_edit.setMaximumHeight(80)
        self._payload_edit.setPlaceholderText("URL, file path, or text content")
        self._payload_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 252, 245, 180);
                border: 1px dotted rgb(150, 130, 100);
                padding: 6px;
                color: rgb(70, 50, 35);
                font-size: 12px;
            }
        """)
        if self.reminder:
            self._payload_edit.setPlainText(self.reminder.action_payload)
        action_section.add_field("Payload:", self._payload_edit)

        notifications = ['desktop', 'none']
        default_notif = self.reminder.notification_method if self.reminder else 'desktop'
        self._notification_dropdown = VintageDropdown(notifications, default_notif)
        action_section.add_field("Notification:", self._notification_dropdown)

        form_layout.addWidget(action_section)

        # SR Schedule Section
        self._sr_section = FormSection("Spaced Repetition Schedule")

        self._ease_spin = VintageSpinBox()
        self._ease_spin.setMinimum(130)
        self._ease_spin.setMaximum(500)
        self._ease_spin.setSingleStep(10)
        self._ease_spin.setValue(int((self.reminder.ease_factor if self.reminder else 2.5) * 100))
        self._sr_section.add_field("Ease Factor (×100):", self._ease_spin)

        self._interval_spin = VintageSpinBox()
        self._interval_spin.setMinimum(1)
        self._interval_spin.setMaximum(365)
        self._interval_spin.setValue(self.reminder.interval_days if self.reminder else 1)
        self._sr_section.add_field("Interval (days):", self._interval_spin)

        form_layout.addWidget(self._sr_section)

        # Stochastic Schedule Section
        self._stochastic_section = FormSection("Stochastic Schedule")

        self._rate_spin = VintageSpinBox()
        self._rate_spin.setMinimum(1)
        self._rate_spin.setMaximum(10000)
        self._rate_spin.setSingleStep(1)
        rate_val = self.reminder.target_rate_per_week if self.reminder and self.reminder.target_rate_per_week else 1
        self._rate_spin.setValue(int(rate_val))
        self._stochastic_section.add_field("Rate per week:", self._rate_spin)

        self._weight_spin = VintageSpinBox()
        self._weight_spin.setMinimum(1)
        self._weight_spin.setMaximum(100)
        self._weight_spin.setSingleStep(1)
        weight_val = self.reminder.weight if self.reminder and self.reminder.weight else 1
        self._weight_spin.setValue(int(weight_val))
        self._stochastic_section.add_field("Weight:", self._weight_spin)

        form_layout.addWidget(self._stochastic_section)

        # Habit Link Section
        habit_section = FormSection("Habit Link (Optional)")

        # Get all habits
        habits = list(Habit.select())
        habit_names = ['None'] + [h.name for h in habits]
        default_habit = None
        if self.reminder and self.reminder.habit_id:
            try:
                habit = Habit.get_by_id(self.reminder.habit_id)
                default_habit = habit.name
            except:
                pass

        self._habit_dropdown = VintageDropdown(habit_names, default_habit)
        habit_section.add_field("Linked Habit:", self._habit_dropdown)

        form_layout.addWidget(habit_section)

        layout.addWidget(form_widget)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        save_btn = VintageButton("Save Reminder", parent=self)
        save_btn.clicked.connect(self._save_reminder)
        button_layout.addWidget(save_btn)

        if self.reminder:
            trigger_btn = VintageButton("Trigger Now", button_type="primary", parent=self)
            trigger_btn.clicked.connect(self._trigger_reminder)
            button_layout.addWidget(trigger_btn)

            delete_btn = VintageButton("Delete", button_type="danger", parent=self)
            delete_btn.clicked.connect(self._delete_reminder)
            button_layout.addWidget(delete_btn)

        cancel_btn = VintageButton("Cancel", button_type="secondary", parent=self)
        cancel_btn.clicked.connect(lambda: self.navigate_to.emit('reminders', None))
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        # Update visibility based on type
        self._on_type_changed(self._type_dropdown.get_selected())

    def _on_type_changed(self, reminder_type: str):
        """Show/hide sections based on reminder type."""
        if self._sr_section and self._stochastic_section:
            self._sr_section.setVisible(reminder_type == 'sr')
            self._stochastic_section.setVisible(reminder_type == 'stochastic')

    def _save_reminder(self):
        """Save the reminder to database."""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return

        payload = self._payload_edit.toPlainText().strip()
        if not payload:
            QMessageBox.warning(self, "Validation Error", "Action payload is required")
            return

        reminder_type = self._type_dropdown.get_selected()
        action_type = self._action_dropdown.get_selected()
        notification_method = self._notification_dropdown.get_selected()

        ease_factor = self._ease_spin.value() / 100.0
        interval_days = self._interval_spin.value()
        target_rate = self._rate_spin.value()
        weight = self._weight_spin.value()

        # Get habit ID
        habit_id = None
        habit_name = self._habit_dropdown.get_selected()
        if habit_name != 'None':
            try:
                habit = Habit.get(Habit.name == habit_name)
                habit_id = habit.id
            except:
                pass

        now = datetime.now()

        if self.reminder:
            # Update existing
            self.reminder.name = name
            self.reminder.reminder_type = reminder_type
            self.reminder.habit_id = habit_id
            self.reminder.action_type = action_type
            self.reminder.action_payload = payload
            self.reminder.notification_method = notification_method
            self.reminder.ease_factor = ease_factor
            self.reminder.interval_days = interval_days
            self.reminder.target_rate_per_week = target_rate
            self.reminder.weight = weight
            self.reminder.updated_at = now

            # Recalculate next_fire_at
            last_fire = self.reminder.last_fired_at or self.reminder.created_at
            if reminder_type == 'sr':
                self.reminder.next_fire_at = SM2Scheduler.get_next_fire_time(last_fire, interval_days)
            elif reminder_type == 'stochastic':
                self.reminder.next_fire_at = StochasticScheduler.get_next_fire_time(last_fire, target_rate)

            self.reminder.save()
        else:
            # Create new
            reminder = Reminder.create(
                name=name,
                reminder_type=reminder_type,
                habit_id=habit_id,
                action_type=action_type,
                action_payload=payload,
                notification_method=notification_method,
                ease_factor=ease_factor,
                interval_days=interval_days,
                target_rate_per_week=target_rate,
                weight=weight,
                created_at=now,
                updated_at=now
            )

            # Set initial next_fire_at
            if reminder_type == 'sr':
                reminder.next_fire_at = SM2Scheduler.get_next_fire_time(now, interval_days)
            elif reminder_type == 'stochastic':
                reminder.next_fire_at = StochasticScheduler.get_next_fire_time(now, target_rate)

            reminder.save()

        self.content_updated.emit()
        self.navigate_to.emit('reminders', None)

    def _trigger_reminder(self):
        """Manually trigger the reminder now."""
        from core.reminder.service import ReminderService
        
        # Reload from database to get latest data
        reminder = Reminder.get_by_id(self.reminder.id)
        result = ReminderService.fire_reminder(reminder, record_fire=False)
        if not result.success:
            QMessageBox.warning(self, "Action Failed", f"Failed to execute action:\n{result.error}")

    def _delete_reminder(self):
        """Delete the reminder."""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{self.reminder.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.reminder.delete_instance()
            self.content_updated.emit()
            self.navigate_to.emit('reminders', None)
