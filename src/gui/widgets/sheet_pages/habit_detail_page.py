"""
Habit Detail Page - View and edit individual habit details.
"""


from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QMessageBox, QWidget)
from PyQt6.QtCore import Qt, QDate

from core.tracker.registry import TrackerRegistry
from . import HabitStatCard
from .base_page import SheetPage
from .vintage_dropdown import VintageDropdown
from .vintage_form_widgets import VintageLineEdit, VintageSpinBox, VintageCheckBox, VintageButton, VintageDateEdit, FormSection
from .notes_widget import NotesWidget
from ..tracker_help_widget import TrackerHelpWidget

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.db import db
from core.habit.habit import Habit
from core.habit.habit_tracker import HabitTracker


class HabitDetailPage(SheetPage):
    """Detail page for viewing/editing a habit"""

    def __init__(self, habit_id=None, parent=None):
        self.habit_id = habit_id
        self.habit = None
        self._name_edit = None
        self._schedule_dropdown = None
        self._start_date_edit = None
        self._end_date_edit = None
        self._duration_spin = None
        self._timeout_spin = None
        self._visible_checkbox = None
        self._notes_widget = None

        # Dynamic tracker widgets - populated during build_content
        self._tracker_checkboxes = {}  # {tracker_name: QCheckBox}
        self._tracker_config_edits = {}  # {tracker_name: QLineEdit}
        self._tracker_help_widgets = {}  # {tracker_name: TrackerHelpWidget}
        self._tracker_help_containers = {}  # {tracker_name: QWidget}
        self._initially_enabled_trackers = set()  # Track which trackers were enabled from DB

        super().__init__(parent)

    def get_page_title(self) -> str:
        if self.habit:
            return f"Edit: {self.habit.name}"
        return "New Habit"

    def get_page_type(self) -> str:
        return "habit_detail"

    def build_content(self):
        """Build the habit detail form"""
        layout = self.layout()

        # Load habit if editing
        if self.habit_id:
            try:
                self.habit = Habit.get_by_id(self.habit_id)
            except:
                error_label = self._create_text_label("Habit not found", secondary=True)
                layout.addWidget(error_label)
                return

        # Page title
        title = self._create_section_header("New Habit" if not self.habit else self.habit.name)
        layout.addWidget(title)

        # Statistics button (if editing)
        if self.habit:
            stats_button = VintageButton("View Statistics", button_type="secondary", parent=self)
            stats_button.clicked.connect(lambda: self.navigate_to.emit('habit_stats', self.habit.id))
            layout.addWidget(stats_button)

        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_widget.setLayout(form_layout)

        # Basic Information Section
        basic_section = FormSection("Information")

        # Name field
        self._name_edit = VintageLineEdit("e.g., Reading")
        if self.habit:
            self._name_edit.setText(self.habit.name)
        basic_section.add_field("Name:", self._name_edit)

        # Schedule field
        schedules = ['hourly', 'daily', 'weekly', 'monthly', 'exponential_3']
        default_schedule = self.habit.schedule if self.habit else None
        self._schedule_dropdown = VintageDropdown(schedules, default_schedule)
        basic_section.add_field("Schedule:", self._schedule_dropdown)

        # Start date field
        self._start_date_edit = VintageDateEdit()
        self._start_date_edit.setMaximumWidth(140)
        if self.habit and self.habit.started_at:
            # Convert datetime to QDate
            qdate = QDate(self.habit.started_at.year, self.habit.started_at.month, self.habit.started_at.day)
            self._start_date_edit.setDate(qdate)
        else:
            # Default to today
            self._start_date_edit.setDate(QDate.currentDate())
        basic_section.add_field("Start date:", self._start_date_edit)

        # End date field
        self._end_date_edit = VintageDateEdit()
        self._end_date_edit.setMaximumWidth(140)
        self._end_date_edit.setSpecialValueText("No end date")
        self._end_date_edit.setMinimumDate(QDate(1900, 1, 1))
        if self.habit and self.habit.ended_at:
            # Convert datetime to QDate
            qdate = QDate(self.habit.ended_at.year, self.habit.ended_at.month, self.habit.ended_at.day)
            self._end_date_edit.setDate(qdate)
        else:
            # Set to minimum date to show "No end date"
            self._end_date_edit.setDate(QDate(1900, 1, 1))
        basic_section.add_field("End date:", self._end_date_edit)
        
        # Show span if both start and end dates are set
        if self.habit and self.habit.started_at and self.habit.ended_at:
            span_days = (self.habit.ended_at.date() - self.habit.started_at.date()).days + 1
            span_label = self._create_text_label(f"Duration: {span_days} days", secondary=True)
            basic_section.add_widget(span_label)

        form_layout.addWidget(basic_section)

        # Time Settings Section
        time_section = FormSection("Progress")

        # Duration field
        self._duration_spin = VintageSpinBox()
        self._duration_spin.setMinimum(0)
        self._duration_spin.setMaximumWidth(140)
        if self.habit and self.habit.allocated_time:
            self._duration_spin.setValue(self.habit.allocated_time // 60)
        time_section.add_field("Minimum time to count towards streak (min):", self._duration_spin)

        # Timeout field
        self._timeout_spin = VintageSpinBox()
        self._timeout_spin.setMinimum(0)
        self._timeout_spin.setMaximumWidth(140)
        self._timeout_spin.setValue(30)
        if self.habit and self.habit.inactivity_threshold:
            self._timeout_spin.setValue(self.habit.inactivity_threshold)
        time_section.add_field("Maximum inactivity until progress stops (sec):", self._timeout_spin)

        form_layout.addWidget(time_section)

        # Display Options Section
        display_section = FormSection("Display Options")

        # Show as key checkbox
        self._visible_checkbox = VintageCheckBox("Show as piano key")
        self._visible_checkbox.setChecked(self.habit.visible if self.habit else True)
        display_section.add_widget(self._visible_checkbox)

        form_layout.addWidget(display_section)

        # Trackers section - dynamically generated from registry
        trackers_section = FormSection("Tracking")

        # Get enabled trackers for this habit
        enabled_trackers = {}
        if self.habit:
            for ht in self.habit.trackers.where(HabitTracker.is_enabled == True):
                enabled_trackers[ht.tracker] = ht.get_config()
                self._initially_enabled_trackers.add(ht.tracker)

        # Create UI for each available tracker
        tracker_names = TrackerRegistry.get_tracker_names()
        for tracker_name in sorted(tracker_names):
            config = TrackerRegistry.get_config_schema(tracker_name)

            # Create checkbox for this tracker
            checkbox = VintageCheckBox(f"{tracker_name}")
            checkbox.setChecked(tracker_name in enabled_trackers)
            checkbox.stateChanged.connect(lambda state, tn=tracker_name: self._on_tracker_toggled(tn, state))
            self._tracker_checkboxes[tracker_name] = checkbox
            trackers_section.add_widget(checkbox)

            if config:
                # Create container for config and help (shown when checked)
                help_container = QWidget()
                help_layout = QVBoxLayout()
                help_layout.setContentsMargins(0, 5, 0, 10)
                help_container.setLayout(help_layout)

                # Slightly darker background to differentiate from other form elements
                help_container.setStyleSheet("""
                    QWidget {
                        background-color: rgb(245, 240, 225);
                        padding: 5px;
                    }
                """)

                # Config input field
                config_label = self._create_text_label(f"Config:", secondary=True)
                help_layout.addWidget(config_label)

                config_edit = VintageLineEdit(self._get_config_placeholder(tracker_name))
                if tracker_name in enabled_trackers:
                    config_dict = enabled_trackers[tracker_name]
                    config_edit.setText(self._config_dict_to_string(config_dict))
                config_edit.textChanged.connect(lambda: self._on_config_changed())
                self._tracker_config_edits[tracker_name] = config_edit
                help_layout.addWidget(config_edit)

                # Help widget
                help_widget = TrackerHelpWidget()
                self._tracker_help_widgets[tracker_name] = help_widget
                help_layout.addWidget(help_widget)

                # Show config container if tracker is checked
                help_container.setVisible(checkbox.isChecked())
                self._tracker_help_containers[tracker_name] = help_container
                trackers_section.add_widget(help_container)

                # Only show/start help widget if tracker is newly checked (not from DB)
                is_newly_checked = checkbox.isChecked() and tracker_name not in self._initially_enabled_trackers
                if is_newly_checked:
                    config_dict = self._parse_config_string(config_edit.text())
                    help_widget.set_tracker(tracker_name, config_dict)
                    help_widget.start_updates()
                else:
                    # Hide help widget for initially enabled trackers
                    help_widget.hide()

        form_layout.addWidget(trackers_section)

        form_layout.addStretch()
        layout.addWidget(form_widget)

        # Notes section
        notes_section = FormSection("Notes")
        self._notes_widget = NotesWidget(parent=self)
        if self.habit and self.habit.note:
            self._notes_widget.set_note(self.habit.note)
        notes_section.add_widget(self._notes_widget)
        form_layout.addWidget(notes_section)

        # Action buttons at bottom
        layout.addWidget(self._create_separator())

        button_layout = QHBoxLayout()
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setSpacing(4)

        # Delete button (if editing)
        if self.habit:
            delete_button = VintageButton("Delete", button_type="danger", parent=self)
            delete_button.clicked.connect(self._delete_habit)
            button_layout.addWidget(delete_button)

        # Save button
        save_button = VintageButton("Save", button_type="primary", parent=self)
        save_button.clicked.connect(self._save_habit)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)

    def _get_config_placeholder(self, tracker_name: str) -> str:
        """Get placeholder text for tracker config field."""
        if tracker_name == 'window':
            return 'keywords = ["piano", "synthesia"]'
        elif tracker_name == 'io':
            return "No config required"
        else:
            return 'key = "value"'

    def _config_dict_to_string(self, config_dict: dict) -> str:
        """Convert config dictionary to TOML format string."""
        return TrackerRegistry.config_to_string(config_dict)

    def _parse_config_string(self, config_str: str) -> dict:
        """Parse TOML config string to dictionary."""
        try:
            return TrackerRegistry.parse_config(config_str)
        except ValueError as e:
            # Return empty dict on parse error - the UI will show it in real-time
            return {}

    def _on_tracker_toggled(self, tracker_name: str, state: int):
        """Handle tracker checkbox toggle."""
        is_checked = state == Qt.CheckState.Checked.value
        container = self._tracker_help_containers.get(tracker_name)
        help_widget = self._tracker_help_widgets.get(tracker_name)

        # Show/hide the config container
        if container:
            container.setVisible(is_checked)

        # Only show help widget for trackers that weren't initially enabled
        was_initially_enabled = tracker_name in self._initially_enabled_trackers
        should_show_help = is_checked and not was_initially_enabled

        if help_widget:
            if should_show_help:
                config_edit = self._tracker_config_edits.get(tracker_name)
                config_dict = self._parse_config_string(config_edit.text() if config_edit else "")
                help_widget.set_tracker(tracker_name, config_dict)
                help_widget.start_updates()
                help_widget.show()
            else:
                help_widget.stop_updates()
                help_widget.hide()

        # If user is re-checking a tracker that was initially enabled, remove it from the set
        # so help will show next time they check it
        if not is_checked and was_initially_enabled:
            self._initially_enabled_trackers.discard(tracker_name)

    def _on_config_changed(self):
        """Handle config text change - update help widgets with new config."""
        for tracker_name, checkbox in self._tracker_checkboxes.items():
            # Only update help widgets that are visible (newly checked trackers)
            if checkbox.isChecked() and tracker_name not in self._initially_enabled_trackers:
                config_edit = self._tracker_config_edits.get(tracker_name)
                help_widget = self._tracker_help_widgets.get(tracker_name)
                if config_edit and help_widget and help_widget.isVisible():
                    config_dict = self._parse_config_string(config_edit.text())
                    help_widget.set_tracker(tracker_name, config_dict)

    def _save_habit(self):
        """Save the habit"""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name is required")
            return

        schedule = self._schedule_dropdown.get_selected()
        duration = self._duration_spin.value()
        timeout = self._timeout_spin.value()
        visible = self._visible_checkbox.isChecked()
        note = self._notes_widget.get_note()
        
        # Get start date from date picker
        qdate = self._start_date_edit.date()
        from datetime import datetime
        start_date = datetime(qdate.year(), qdate.month(), qdate.day())
        
        # Get end date from date picker (None if set to minimum date)
        end_qdate = self._end_date_edit.date()
        end_date = None
        if end_qdate.year() > 1900:
            end_date = datetime(end_qdate.year(), end_qdate.month(), end_qdate.day())

        try:
            with db.atomic():
                if self.habit:
                    # Update existing
                    self.habit.name = name
                    self.habit.schedule = schedule
                    self.habit.started_at = start_date
                    self.habit.ended_at = end_date
                else:
                    # Create new
                    self.habit = Habit.create(name=name, schedule=schedule, started_at=start_date, ended_at=end_date)

                if duration > 0:
                    self.habit.allocated_time = duration * 60
                else:
                    self.habit.allocated_time = None

                if timeout > 0:
                    self.habit.inactivity_threshold = timeout

                self.habit.visible = visible
                self.habit.note = note if note.strip() else None

                self.habit.save()

                # Update trackers - delete all and recreate from checkboxes
                HabitTracker.delete().where(HabitTracker.habit == self.habit).execute()

                # Create HabitTracker records for each checked tracker
                for tracker_name, checkbox in self._tracker_checkboxes.items():
                    if checkbox.isChecked():
                        config_edit = self._tracker_config_edits.get(tracker_name)
                        config_str = config_edit.text().strip() if config_edit else ""
                        config_dict = self._parse_config_string(config_str)

                        # Convert dict to JSON
                        import json
                        config_json = json.dumps(config_dict)

                        HabitTracker.insert(
                            habit=self.habit,
                            tracker=tracker_name,
                            config=config_json,
                            is_enabled=True
                        ).on_conflict_replace().execute()

            # Stop all help widget updates before leaving
            for help_widget in self._tracker_help_widgets.values():
                help_widget.stop_updates()

            # Emit signal to refresh piano window
            self.content_updated.emit()

            self.navigate_to.emit("index", None)

        except Exception as e:
            # Clear the habit reference on failure so retry will create new
            if self.habit and not self.habit.id:
                self.habit = None
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to save: {e}")

    def _delete_habit(self):
        """Delete the current habit"""
        if not self.habit:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete '{self.habit.name}' and all its data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Stop all help widget updates before deleting
                for help_widget in self._tracker_help_widgets.values():
                    help_widget.stop_updates()

                self.habit.delete_instance()
                self.content_updated.emit()
                self.navigate_to.emit("index", None)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    def hideEvent(self, event):
        """Stop updates when page is hidden."""
        # Stop all help widget updates when navigating away
        for help_widget in self._tracker_help_widgets.values():
            if help_widget:
                help_widget.stop_updates()
        super().hideEvent(event)

    def showEvent(self, event):
        """Restart updates when page is shown."""
        # Restart updates only for visible help widgets (newly checked trackers)
        for tracker_name, checkbox in self._tracker_checkboxes.items():
            if checkbox.isChecked() and tracker_name not in self._initially_enabled_trackers:
                help_widget = self._tracker_help_widgets.get(tracker_name)
                config_edit = self._tracker_config_edits.get(tracker_name)
                if help_widget and help_widget.isVisible() and config_edit:
                    config_dict = self._parse_config_string(config_edit.text())
                    help_widget.set_tracker(tracker_name, config_dict)
                    help_widget.start_updates()
        super().showEvent(event)

    def closeEvent(self, event):
        """Clean up resources when page is closed."""
        # Stop all help widget updates
        for help_widget in self._tracker_help_widgets.values():
            if help_widget:
                help_widget.stop_updates()
        super().closeEvent(event)
