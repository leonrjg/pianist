"""
Habit Detail Page - View and edit individual habit details.
"""

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QSpinBox, QCheckBox, QPushButton, QMessageBox, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from .base_page import SheetPage
from .vintage_dropdown import VintageDropdown

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.db import db
from core.habit.habit import Habit
from core.habit.habit_tracker import HabitTracker
from core.util.time import get_friendly_elapsed, get_friendly_datetime


class HabitDetailPage(SheetPage):
    """Detail page for viewing/editing a habit"""

    def __init__(self, habit_id=None, parent=None):
        self.habit_id = habit_id
        self.habit = None
        self._name_edit = None
        self._schedule_dropdown = None
        self._duration_spin = None
        self._timeout_spin = None
        self._io_tracker_cb = None
        self._window_tracker_cb = None
        self._tracker_args_edit = None

        super().__init__(parent)

    def get_page_title(self) -> str:
        if self.habit:
            return f"Edit: {self.habit.name}"
        return "New Habit"

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
                back_link = self._create_link_label("← Back", lambda: self.go_back.emit())
                layout.addWidget(back_link)
                return

        # Page title
        title_text = f"{self.habit.name}" if self.habit else "♪ New Habit"
        title = self._create_section_header(title_text)
        layout.addWidget(title)

        layout.addWidget(self._create_separator())

        form_widget = QWidget()
        form_layout = QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_widget.setLayout(form_layout)

        # Show statistics first if editing existing habit
        if self.habit:
            form_layout.addWidget(self._create_text_label("Statistics:", secondary=True))

            schedule = self.habit.get_schedule()
            scale = schedule.get_scale()

            from datetime import datetime
            next_task = get_friendly_datetime(schedule.get_next_task(datetime.now()), scale)

            stats_lines = [f"Next: {next_task}"]
            stats_lines.append(f"Current streak: {self.habit.get_streak()}")
            stats_lines.append(f"Longest streak: {self.habit.get_longest_streak()}")

            buckets = self.habit.get_activity_buckets()
            if buckets:
                from core import analytics
                total_time = analytics.get_time_spent(buckets)
                stats_lines.append(f"Total time: {get_friendly_elapsed(total_time)}")
                stats_lines.append(f"Sessions: {len(buckets)}")

            stats_text = "\n".join(stats_lines)
            stats_label = self._create_text_label(stats_text, secondary=False)
            form_layout.addWidget(stats_label)

            form_layout.addWidget(self._create_separator())

        # Name field
        name_label = self._create_text_label("Name:", secondary=True)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g., Reading")
        if self.habit:
            self._name_edit.setText(self.habit.name)
        form_layout.addWidget(name_label)
        form_layout.addWidget(self._name_edit)

        # Schedule field
        schedule_label = self._create_text_label("Schedule:", secondary=True)
        form_layout.addWidget(schedule_label)

        schedules = ['hourly', 'daily', 'weekly', 'monthly', 'exponential_3']
        default_schedule = self.habit.schedule if self.habit else None
        self._schedule_dropdown = VintageDropdown(schedules, default_schedule)
        form_layout.addWidget(self._schedule_dropdown)

        # Duration field
        form_layout.addWidget(self._create_text_label("Duration (min):", secondary=True))
        self._duration_spin = QSpinBox()
        self._duration_spin.setRange(0, 1440)
        self._duration_spin.setSuffix(" min")
        self._duration_spin.setMaximumWidth(120)
        if self.habit and self.habit.allocated_time:
            self._duration_spin.setValue(self.habit.allocated_time // 60)
        form_layout.addWidget(self._duration_spin)

        # Timeout field
        form_layout.addWidget(self._create_text_label("Timeout (sec):", secondary=True))
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(0, 3600)
        self._timeout_spin.setSuffix(" sec")
        self._timeout_spin.setMaximumWidth(120)
        if self.habit and self.habit.inactivity_threshold:
            self._timeout_spin.setValue(self.habit.inactivity_threshold)
        form_layout.addWidget(self._timeout_spin)

        # Trackers section
        form_layout.addWidget(self._create_text_label("Tracking:", secondary=True))

        self._io_tracker_cb = QCheckBox("IO Tracker")
        self._window_tracker_cb = QCheckBox("Window Tracker")

        if self.habit:
            trackers = list(self.habit.trackers.where(HabitTracker.is_enabled == True))
            self._io_tracker_cb.setChecked(any(t.tracker == 'io' for t in trackers))
            self._window_tracker_cb.setChecked(any(t.tracker == 'window' for t in trackers))

        form_layout.addWidget(self._io_tracker_cb)
        form_layout.addWidget(self._window_tracker_cb)

        config_label = self._create_text_label("Tracker Config:", secondary=True)
        form_layout.addWidget(config_label)
        self._tracker_args_edit = QLineEdit()
        self._tracker_args_edit.setPlaceholderText("key=value&key2=value2")
        if self.habit:
            trackers = list(self.habit.trackers.where(HabitTracker.is_enabled == True))
            if trackers:
                config = trackers[0].get_config()
                if config and config != ' ()':
                    self._tracker_args_edit.setText(str(config))
        form_layout.addWidget(self._tracker_args_edit)

        form_layout.addStretch()
        layout.addWidget(form_widget)

        # Action buttons at bottom
        layout.addWidget(self._create_separator())

        button_layout = QHBoxLayout()

        # Save button (styled as link)
        save_link = self._create_link_label("💾 Save", self._save_habit)
        button_layout.addWidget(save_link)

        button_layout.addStretch()

        # Delete button (if editing)
        if self.habit:
            delete_link = self._create_link_label("🗑 Delete", self._delete_habit)
            delete_link.setStyleSheet("""
                QLabel { color: rgb(180, 50, 50); text-decoration: underline; }
                QLabel:hover { color: rgb(220, 80, 80); }
            """)
            button_layout.addWidget(delete_link)

        layout.addLayout(button_layout)

        # Back link
        back_link = self._create_link_label("← Back to Index", lambda: self.go_back.emit())
        layout.addWidget(back_link)

    def _save_habit(self):
        """Save the habit"""
        name = self._name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name is required")
            return

        schedule = self._schedule_dropdown.get_selected()
        duration = self._duration_spin.value()
        timeout = self._timeout_spin.value()
        track_args = self._tracker_args_edit.text().strip()

        try:
            with db.atomic():
                if self.habit:
                    # Update existing
                    self.habit.name = name
                    self.habit.schedule = schedule
                else:
                    # Create new
                    self.habit = Habit.create(name=name, schedule=schedule)

                if duration > 0:
                    self.habit.allocated_time = duration * 60
                else:
                    self.habit.allocated_time = None

                if timeout > 0:
                    self.habit.inactivity_threshold = timeout
                else:
                    self.habit.inactivity_threshold = None

                self.habit.save()

                # Update trackers
                HabitTracker.delete().where(HabitTracker.habit == self.habit).execute()

                trackers = []
                if self._io_tracker_cb.isChecked():
                    trackers.append('io')
                if self._window_tracker_cb.isChecked():
                    trackers.append('window')

                for tracker in trackers:
                    HabitTracker.insert(
                        habit=self.habit,
                        tracker=tracker,
                        config=HabitTracker.create_json_config(track_args),
                        is_enabled=True
                    ).on_conflict_replace().execute()

            # Emit signal to refresh piano window
            self.content_updated.emit()

            # Go back to index
            self.go_back.emit()

        except Exception as e:
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
                self.habit.delete_instance()
                self.content_updated.emit()
                self.go_back.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
