"""
Reminder Detail Page - Create/edit reminder with full configuration.
"""

from datetime import datetime
from types import SimpleNamespace
from PyQt6.QtWidgets import QVBoxLayout, QMessageBox, QWidget, QTextEdit, QLabel
from PyQt6.QtCore import Qt, QDate

from .base_page import SheetPage
from ..themed_dropdown import ThemedDropdown
from ..themed_form_widgets import (
    ThemedLineEdit, ThemedSpinBox, ThemedButton,
    ThemedFormSection, ThemedCheckBox, ThemedDateEdit
)

from core.reminder.service import ReminderService
from gui.themes import current_theme as _t
from core.schedule.stochastic import StochasticScheduler


class ReminderDetailPage(SheetPage):
    """Detail page for creating/editing a reminder"""

    def __init__(self, reminder_id=None, default_habit_id=None, return_page='reminders', return_data=None, parent=None):
        self.reminder_id = reminder_id
        self.default_habit_id = default_habit_id
        self.return_page = return_page
        self.return_data = return_data
        self.reminder = None

        # Form fields
        self._name_edit = None
        self._type_dropdown = None
        self._action_dropdown = None
        self._payload_edit = None
        self._notification_dropdown = None
        self._action_section = None

        # Stochastic fields
        self._rate_spin = None
        self._weight_spin = None

        # Fixed fields
        self._fixed_date_edit = None
        self._fixed_time_edit = None

        # Active window fields
        self._active_section = None
        self._active_start_edit = None
        self._active_end_edit = None
        self._global_window_warning = None

        # Options
        self._bypass_anti_spam_checkbox = None

        # Habit link
        self._habit_dropdown = None

        # Dynamic sections
        self._stochastic_section = None
        self._fixed_section = None

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
                self.reminder = ReminderService.get_by_id(self.reminder_id)
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
        basic_section = ThemedFormSection("Basic Information")

        self._name_edit = ThemedLineEdit("e.g., Review vocabulary")
        if self.reminder:
            self._name_edit.setText(self.reminder.name)
        basic_section.add_field("Name:", self._name_edit)

        types = ['stochastic', 'fixed']
        default_type = self.reminder.reminder_type if self.reminder and self.reminder.reminder_type in types else 'stochastic'
        self._type_dropdown = ThemedDropdown(types, default_type)
        self._type_dropdown.selection_changed.connect(self._on_type_changed)
        basic_section.add_field("Type:", self._type_dropdown)

        form_layout.addWidget(basic_section)

        # Action Section
        self._action_section = ThemedFormSection("Action")

        actions = ['open_link', 'random_line', 'show_text', 'anki_card']
        default_action = self.reminder.action_type if self.reminder else 'show_text'
        self._action_dropdown = ThemedDropdown(actions, default_action)
        self._action_section.add_field("Action:", self._action_dropdown)

        self._payload_edit = QTextEdit()
        self._payload_edit.setMaximumHeight(80)
        self._payload_edit.setPlaceholderText("URL, file path, deck name, or text content")
        _pt = _t()
        self._payload_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {_pt.input_bg};
                border: 1px dotted {_pt.border};
                padding: 6px;
                color: {_pt.ink_primary};
                font-size: 12px;
            }}
        """)
        if self.reminder:
            self._payload_edit.setPlainText(self.reminder.action_payload)
        self._action_section.add_field("Payload:", self._payload_edit)

        notifications = ['desktop', 'none']
        default_notif = self.reminder.notification_method if self.reminder else 'desktop'
        self._notification_dropdown = ThemedDropdown(notifications, default_notif)
        self._action_section.add_field("Notification:", self._notification_dropdown)

        self._bypass_anti_spam_checkbox = ThemedCheckBox("Bypass anti-spam filter")
        if self.reminder:
            self._bypass_anti_spam_checkbox.setChecked(bool(self.reminder.bypass_anti_spam))
        self._action_section.add_field("Options:", self._bypass_anti_spam_checkbox)

        form_layout.addWidget(self._action_section)

        # Stochastic Schedule Section
        self._stochastic_section = ThemedFormSection("Stochastic Schedule")

        self._rate_spin = ThemedSpinBox()
        self._rate_spin.setMinimum(1)
        self._rate_spin.setMaximum(10000)
        self._rate_spin.setSingleStep(1)
        rate_val = self.reminder.target_rate_per_week if self.reminder and self.reminder.target_rate_per_week else 1
        self._rate_spin.setValue(int(rate_val))
        self._stochastic_section.add_field("Rate per week:", self._rate_spin)

        self._weight_spin = ThemedSpinBox()
        self._weight_spin.setMinimum(1)
        self._weight_spin.setMaximum(100)
        self._weight_spin.setSingleStep(1)
        weight_val = self.reminder.weight if self.reminder and self.reminder.weight else 1
        self._weight_spin.setValue(int(weight_val))
        self._stochastic_section.add_field("Weight:", self._weight_spin)

        form_layout.addWidget(self._stochastic_section)

        # Fixed Schedule Section
        self._fixed_section = ThemedFormSection("Fixed Schedule")

        self._fixed_date_edit = ThemedDateEdit()
        fixed_dt = self.reminder.next_fire_at if self.reminder and self.reminder.next_fire_at else datetime.now()
        self._fixed_date_edit.setDate(QDate(fixed_dt.year, fixed_dt.month, fixed_dt.day))
        self._fixed_section.add_field("Date (one-off):", self._fixed_date_edit)

        self._fixed_time_edit = ThemedLineEdit("HH:MM")
        if self.reminder and self.reminder.fixed_time_minute is not None:
            fixed_minutes = self.reminder.fixed_time_minute
        elif self.reminder and self.reminder.next_fire_at:
            fixed_minutes = self.reminder.next_fire_at.hour * 60 + self.reminder.next_fire_at.minute
        else:
            fixed_minutes = 9 * 60
        self._fixed_time_edit.setText(self._format_minutes(fixed_minutes))
        self._fixed_section.add_field("Time:", self._fixed_time_edit)
        self._fixed_time_edit.editingFinished.connect(self._refresh_global_window_warning)

        form_layout.addWidget(self._fixed_section)

        # Active Window Section
        self._active_section = ThemedFormSection("Active Window")

        self._active_start_edit = ThemedLineEdit("HH:MM")
        self._active_end_edit = ThemedLineEdit("HH:MM")
        start_minutes = self.reminder.active_start_minute if self.reminder else 0
        end_minutes = self.reminder.active_end_minute if self.reminder else 1440
        self._active_start_edit.setText(self._format_minutes(start_minutes))
        self._active_end_edit.setText(self._format_minutes(end_minutes))
        self._active_start_edit.editingFinished.connect(self._refresh_global_window_warning)
        self._active_end_edit.editingFinished.connect(self._refresh_global_window_warning)

        self._active_section.add_field("Start:", self._active_start_edit)
        self._active_section.add_field("End:", self._active_end_edit)

        form_layout.addWidget(self._active_section)

        self._global_window_warning = QLabel("Warning: this reminder is outside the global reminder window.")
        self._global_window_warning.setWordWrap(True)
        self._global_window_warning.setStyleSheet(f"""
            color: {_t().danger_bg};
            background: transparent;
            font-size: 11px;
            font-weight: bold;
        """)
        self._global_window_warning.setVisible(False)
        form_layout.addWidget(self._global_window_warning)

        # Habit Link Section
        habit_section = ThemedFormSection("Habit Link (Optional)")

        # Get all habits via service
        _habit_service = getattr(self.window(), 'service', None)
        habits = _habit_service.get_all_habits() if _habit_service else []
        habit_names = ['None'] + [h.name for h in habits]
        default_habit = None
        selected_habit_id = self.reminder.habit_id if self.reminder and self.reminder.habit_id else self.default_habit_id
        if selected_habit_id:
            linked = next((h for h in habits if h.id == selected_habit_id), None)
            if linked:
                default_habit = linked.name

        self._habit_dropdown = ThemedDropdown(habit_names, default_habit)
        self._habit_dropdown.selection_changed.connect(lambda _: self._refresh_action_visibility())
        habit_section.add_field("Linked Habit:", self._habit_dropdown)

        form_layout.addWidget(habit_section)

        layout.addWidget(form_widget)

        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(8)

        save_btn = ThemedButton("Save Reminder", parent=self)
        save_btn.clicked.connect(self._save_reminder)
        button_layout.addWidget(save_btn)

        if self.reminder:
            trigger_btn = ThemedButton("Trigger Now", button_type="primary", parent=self)
            trigger_btn.clicked.connect(self._trigger_reminder)
            button_layout.addWidget(trigger_btn)

            delete_btn = ThemedButton("Delete", button_type="danger", parent=self)
            delete_btn.clicked.connect(self._delete_reminder)
            button_layout.addWidget(delete_btn)

        cancel_btn = ThemedButton("Cancel", button_type="secondary", parent=self)
        cancel_btn.clicked.connect(self._navigate_back)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        # Update visibility based on type
        self._on_type_changed(self._type_dropdown.get_selected())
        self._refresh_action_visibility()

    def _on_type_changed(self, reminder_type: str):
        """Show/hide sections based on reminder type."""
        if self._stochastic_section and self._fixed_section:
            self._stochastic_section.setVisible(reminder_type == 'stochastic' and not self._is_habit_linked())
            self._fixed_section.setVisible(reminder_type == 'fixed')
        if self._active_section:
            self._active_section.setVisible(reminder_type != 'fixed')
        self._refresh_global_window_warning()

    def _refresh_action_visibility(self):
        if self._action_section:
            self._action_section.setVisible(not self._is_habit_linked())
        if self._stochastic_section and self._type_dropdown:
            self._stochastic_section.setVisible(
                self._type_dropdown.get_selected() == 'stochastic' and not self._is_habit_linked()
            )

    def _is_habit_linked(self) -> bool:
        return self._habit_dropdown is not None and self._habit_dropdown.get_selected() != 'None'

    def _refresh_global_window_warning(self):
        if not self._global_window_warning:
            return

        try:
            reminder_type = self._type_dropdown.get_selected()
            if reminder_type == 'fixed':
                fixed_minute = self._parse_time(self._fixed_time_edit.text(), allow_24=False)
                active_start = 0
                active_end = 1440
            else:
                fixed_minute = None
                active_start = self._parse_time(self._active_start_edit.text(), allow_24=False)
                active_end = self._parse_time(self._active_end_edit.text(), allow_24=True)
        except ValueError:
            self._global_window_warning.setVisible(False)
            return

        reminder = SimpleNamespace(
            reminder_type=reminder_type,
            fixed_time_minute=fixed_minute,
            next_fire_at=None,
            active_start_minute=active_start,
            active_end_minute=active_end,
        )
        self._global_window_warning.setVisible(ReminderService.is_reminder_outside_global_window(reminder))

    def _save_reminder(self):
        """Save the reminder to database."""
        name = self._name_edit.text().strip()
        is_habit_linked = self._is_habit_linked()
        if not name and not is_habit_linked:
            QMessageBox.warning(self, "Validation Error", "Name is required")
            return

        payload = self._payload_edit.toPlainText().strip()
        if not is_habit_linked and not payload:
            QMessageBox.warning(self, "Validation Error", "Action payload is required")
            return

        reminder_type = self._type_dropdown.get_selected()
        action_type = 'show_text' if is_habit_linked else self._action_dropdown.get_selected()
        notification_method = self._notification_dropdown.get_selected()

        target_rate = self._rate_spin.value()
        weight = self._weight_spin.value()

        try:
            active_start = self._parse_time(self._active_start_edit.text(), allow_24=False)
            active_end = self._parse_time(self._active_end_edit.text(), allow_24=True)
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))
            return

        fixed_time_minute = None
        fixed_fire_at = None
        if reminder_type == 'fixed':
            try:
                fixed_time_minute = self._parse_time(self._fixed_time_edit.text(), allow_24=False)
            except ValueError as e:
                QMessageBox.warning(self, "Validation Error", str(e))
                return

            qdate = self._fixed_date_edit.date()
            fixed_fire_at = datetime(
                qdate.year(),
                qdate.month(),
                qdate.day(),
                fixed_time_minute // 60,
                fixed_time_minute % 60,
                0
            )
            active_start = 0
            active_end = 1440

        # Get habit ID
        habit_id = None
        habit_name = self._habit_dropdown.get_selected()
        if habit_name != 'None':
            _habit_service = getattr(self.window(), 'service', None)
            if _habit_service:
                matched = next((h for h in _habit_service.get_all_habits() if h.name == habit_name), None)
                if matched:
                    habit_id = matched.id
                    if is_habit_linked:
                        name = name or f"{matched.name} reminder"
                        payload = f"It's time for {matched.name}"

        if is_habit_linked and habit_id is None:
            QMessageBox.warning(self, "Validation Error", "Linked habit is required")
            return

        now = datetime.now()

        bypass_anti_spam = self._bypass_anti_spam_checkbox.isChecked()

        if self.reminder:
            # Update existing
            self.reminder.name = name
            self.reminder.reminder_type = reminder_type
            self.reminder.habit_id = habit_id
            self.reminder.action_type = action_type
            self.reminder.action_payload = payload
            self.reminder.notification_method = notification_method
            self.reminder.target_rate_per_week = target_rate
            self.reminder.weight = weight
            self.reminder.fixed_time_minute = fixed_time_minute
            self.reminder.active_start_minute = active_start
            self.reminder.active_end_minute = active_end
            self.reminder.bypass_anti_spam = bypass_anti_spam

            # Recalculate next_fire_at
            last_fire = self.reminder.last_fired_at or self.reminder.created_at
            if reminder_type == 'stochastic':
                if habit_id is not None:
                    self.reminder.next_fire_at = ReminderService.get_next_habit_stochastic_fire_time(self.reminder, now)
                else:
                    self.reminder.next_fire_at = StochasticScheduler.get_next_fire_time(
                        last_fire,
                        target_rate,
                        active_start,
                        active_end
                    )
            elif reminder_type == 'fixed':
                self.reminder.next_fire_at = fixed_fire_at
                if habit_id is not None:
                    self.reminder.next_fire_at = ReminderService.get_next_fixed_fire_time(self.reminder, now)

            ReminderService.save(self.reminder)
        else:
            # Create new
            reminder = ReminderService.create(
                name=name,
                reminder_type=reminder_type,
                habit_id=habit_id,
                action_type=action_type,
                action_payload=payload,
                notification_method=notification_method,
                target_rate_per_week=target_rate,
                weight=weight,
                fixed_time_minute=fixed_time_minute,
                next_fire_at=fixed_fire_at if reminder_type == 'fixed' else None,
                active_start_minute=active_start,
                active_end_minute=active_end,
                bypass_anti_spam=bypass_anti_spam,
                created_at=now,
                updated_at=now
            )

            # Set initial next_fire_at
            if reminder_type == 'stochastic':
                if habit_id is not None:
                    reminder.next_fire_at = ReminderService.get_next_habit_stochastic_fire_time(reminder, now)
                else:
                    reminder.next_fire_at = StochasticScheduler.get_next_fire_time(
                        now,
                        target_rate,
                        active_start,
                        active_end
                    )
            elif reminder_type == 'fixed' and habit_id is not None:
                reminder.next_fire_at = ReminderService.get_next_fixed_fire_time(reminder, now)

            ReminderService.save(reminder)

        self.content_updated.emit()
        self._navigate_back()

    def _trigger_reminder(self):
        """Manually trigger the reminder now."""
        reminder = ReminderService.get_by_id(self.reminder.id)
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
            ReminderService.delete(self.reminder)
            self.content_updated.emit()
            self._navigate_back()

    def _navigate_back(self):
        self.navigate_to.emit(self.return_page, self.return_data)

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
