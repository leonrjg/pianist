import sys
from datetime import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                           QLabel, QLineEdit, QComboBox, QSpinBox, QTextEdit,
                           QListWidget, QListWidgetItem, QTabWidget, QFormLayout,
                           QCheckBox, QMessageBox, QScrollArea, QFrame, QSplitter)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from core.db import db
from core.habit.habit import Habit
from core.habit.habit_tracker import HabitTracker
from core.session import Session
from core.util.time import get_friendly_elapsed, get_friendly_datetime, get_timespan
from core import analytics


class HabitManagementWindow(QWidget):
    """Piano-themed management window for creating, editing, deleting habits and viewing statistics"""

    habit_updated = pyqtSignal()  # Signal to notify piano window of changes

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pianist - Habit Management")
        self.setGeometry(200, 200, 950, 700)

        # Modern, refined color palette
        self.colors = {
            'background': '#fafafa',
            'surface': '#ffffff',
            'surface_variant': '#f5f5f5',
            'primary': '#2d3436',
            'primary_variant': '#636e72',
            'accent': '#6c5ce7',
            'accent_light': '#a29bfe',
            'text_primary': '#2d3436',
            'text_secondary': '#636e72',
            'text_hint': '#b2bec3',
            'border': '#ddd',
            'border_focus': '#6c5ce7'
        }

        # Apply modern stylesheet
        self.setStyleSheet(self._get_modern_stylesheet())

        # Create main layout with tabs
        self.setup_ui()

        # Refresh timer for stats
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_stats)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds

        # Load initial data
        self.refresh_habits_list()
        self.refresh_stats()

    def setup_ui(self):
        """Setup the main UI with tabs"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # Create tabs
        self.create_habits_tab()
        self.create_stats_tab()
        self.create_quick_actions_tab()

        # Close button
        close_button = QPushButton("Close")
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

    def create_habits_tab(self):
        """Create the habits management tab"""
        habits_widget = QWidget()
        layout = QHBoxLayout()
        habits_widget.setLayout(layout)

        # Left side - habits list
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)
        left_widget.setMaximumWidth(300)

        repertoire_label = QLabel("Habits")
        repertoire_label.setObjectName("sectionHeader")
        left_layout.addWidget(repertoire_label)
        self.habits_list = QListWidget()
        self.habits_list.itemClicked.connect(self.load_habit_for_editing)
        left_layout.addWidget(self.habits_list)

        delete_button = QPushButton("Delete Selected")
        delete_button.setObjectName("deleteButton")
        delete_button.clicked.connect(self.delete_habit)
        left_layout.addWidget(delete_button)

        # Right side - habit editor
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        # Habit form
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        name_label = QLabel("Name")
        name_label.setObjectName("fieldLabel")
        form_layout.addRow(name_label, self.name_edit)

        self.schedule_combo = QComboBox()
        self.schedule_combo.addItems(['hourly', 'daily', 'weekly', 'monthly', 'exponential_3'])
        schedule_label = QLabel("Schedule")
        schedule_label.setObjectName("fieldLabel")
        form_layout.addRow(schedule_label, self.schedule_combo)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(0, 1440)  # 0 to 24 hours in minutes
        self.duration_spin.setSuffix(" minutes")
        duration_label = QLabel("Duration")
        duration_label.setObjectName("fieldLabel")
        form_layout.addRow(duration_label, self.duration_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(0, 3600)  # 0 to 1 hour in seconds
        self.timeout_spin.setSuffix(" seconds")
        timeout_label = QLabel("Timeout")
        timeout_label.setObjectName("fieldLabel")
        form_layout.addRow(timeout_label, self.timeout_spin)

        # Trackers
        trackers_label = QLabel("Tracking")
        trackers_label.setObjectName("fieldLabel")
        form_layout.addRow(trackers_label)

        self.io_tracker_cb = QCheckBox("Activity Tracker")
        self.window_tracker_cb = QCheckBox("Window Tracker")
        form_layout.addRow("", self.io_tracker_cb)
        form_layout.addRow("", self.window_tracker_cb)

        self.tracker_args_edit = QLineEdit()
        self.tracker_args_edit.setPlaceholderText("key=value&key2=value2")
        args_label = QLabel("Configuration")
        args_label.setObjectName("fieldLabel")
        form_layout.addRow(args_label, self.tracker_args_edit)

        right_layout.addLayout(form_layout)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.setObjectName("saveButton")
        save_button.clicked.connect(self.save_habit)
        new_button = QPushButton("New")
        new_button.setObjectName("newButton")
        new_button.clicked.connect(self.clear_form)

        button_layout.addWidget(save_button)
        button_layout.addWidget(new_button)
        right_layout.addLayout(button_layout)

        # Add to splitter
        splitter = QSplitter()
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 600])

        layout.addWidget(splitter)
        self.tab_widget.addTab(habits_widget, "Habits")

    def create_stats_tab(self):
        """Create the statistics tab"""
        stats_widget = QWidget()
        layout = QVBoxLayout()
        stats_widget.setLayout(layout)

        # Stats display
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setFont(QFont("Courier", 10))
        layout.addWidget(self.stats_text)

        # Refresh button
        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("refreshButton")
        refresh_button.clicked.connect(self.refresh_stats)
        layout.addWidget(refresh_button)

        self.tab_widget.addTab(stats_widget, "Statistics")

    def create_quick_actions_tab(self):
        """Create the quick actions tab"""
        actions_widget = QWidget()
        layout = QVBoxLayout()
        actions_widget.setLayout(layout)

        # Note about piano window
        note_label = QLabel("Use the piano window to start and stop practice sessions")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #888888; font-style: italic; margin: 10px;")
        layout.addWidget(note_label)

        # Activity log
        activity_header = QLabel("Recent Activity")
        activity_header.setObjectName("sectionHeader")
        layout.addWidget(activity_header)
        self.activity_text = QTextEdit()
        self.activity_text.setReadOnly(True)
        self.activity_text.setMaximumHeight(300)
        layout.addWidget(self.activity_text)

        layout.addStretch()
        self.tab_widget.addTab(actions_widget, "Activity")

    def refresh_habits_list(self):
        """Refresh the habits list"""
        self.habits_list.clear()

        habits = list(Habit.select())
        for habit in habits:
            self.habits_list.addItem(habit.name)

    def load_habit_for_editing(self, item):
        """Load selected habit into the form for editing"""
        habit_name = item.text()
        try:
            habit = Habit.get(Habit.name == habit_name)

            self.name_edit.setText(habit.name)
            self.schedule_combo.setCurrentText(habit.schedule)

            if habit.allocated_time:
                self.duration_spin.setValue(habit.allocated_time // 60)  # Convert to minutes
            else:
                self.duration_spin.setValue(0)

            if habit.inactivity_threshold:
                self.timeout_spin.setValue(habit.inactivity_threshold)
            else:
                self.timeout_spin.setValue(0)

            # Load trackers
            trackers = list(habit.trackers.where(HabitTracker.is_enabled == True))
            self.io_tracker_cb.setChecked(any(t.tracker == 'io' for t in trackers))
            self.window_tracker_cb.setChecked(any(t.tracker == 'window' for t in trackers))

            # Load tracker args (simplified - just get first tracker's config)
            if trackers:
                config = trackers[0].get_config()
                if config and config != ' ()':
                    self.tracker_args_edit.setText(config.strip(' ()'))
                else:
                    self.tracker_args_edit.clear()
            else:
                self.tracker_args_edit.clear()

        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load habit: {e}")

    def save_habit(self):
        """Save the current habit"""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name is required")
            return

        schedule = self.schedule_combo.currentText()
        duration = self.duration_spin.value()
        timeout = self.timeout_spin.value()
        track_args = self.tracker_args_edit.text().strip()

        try:
            with db.atomic():
                habit = Habit.get_or_none(Habit.name == name)
                if not habit:
                    habit = Habit.create(name=name, schedule=schedule)

                habit.schedule = schedule

                if duration > 0:
                    habit.allocated_time = duration * 60  # Convert to seconds
                else:
                    habit.allocated_time = None

                if timeout > 0:
                    habit.inactivity_threshold = timeout
                else:
                    habit.inactivity_threshold = None

                habit.save()

                # Update trackers
                # Delete existing trackers
                HabitTracker.delete().where(HabitTracker.habit == habit).execute()

                # Add selected trackers
                trackers = []
                if self.io_tracker_cb.isChecked():
                    trackers.append('io')
                if self.window_tracker_cb.isChecked():
                    trackers.append('window')

                for tracker in trackers:
                    HabitTracker.insert(
                        habit=habit,
                        tracker=tracker,
                        config=HabitTracker.create_json_config(track_args),
                        is_enabled=True
                    ).on_conflict_replace().execute()

            QMessageBox.information(self, "Success", f"Saved habit '{name}'")
            self.refresh_habits_list()
            self.habit_updated.emit()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save habit: {e}")

    def delete_habit(self):
        """Delete the selected habit"""
        current_item = self.habits_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Error", "Please select a habit to delete")
            return

        habit_name = current_item.text()
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete habit '{habit_name}' and all its data?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                habit = Habit.get(Habit.name == habit_name)
                habit.delete_instance()
                QMessageBox.information(self, "Success", f"Deleted habit '{habit_name}'")
                self.refresh_habits_list()
                self.clear_form()
                self.habit_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete habit: {e}")

    def clear_form(self):
        """Clear the habit form"""
        self.name_edit.clear()
        self.schedule_combo.setCurrentIndex(0)
        self.duration_spin.setValue(0)
        self.timeout_spin.setValue(0)
        self.io_tracker_cb.setChecked(False)
        self.window_tracker_cb.setChecked(False)
        self.tracker_args_edit.clear()


    def refresh_stats(self):
        """Refresh the statistics display"""
        try:
            habits = list(Habit.select())
            if not habits:
                self.stats_text.setText("No habits found")
                self.activity_text.setText("No activity recorded")
                return

            # Generate comprehensive stats
            stats_text = self._generate_stats_text(habits)
            self.stats_text.setText(stats_text)

            # Generate recent activity
            activity_text = self._generate_activity_text(habits)
            self.activity_text.setText(activity_text)

        except Exception as e:
            self.stats_text.setText(f"Error loading stats: {e}")

    def _generate_stats_text(self, habits):
        """Generate formatted statistics text"""
        lines = []

        # Overall summary
        lines.append(f"=== HABITS SUMMARY ({len(habits)} total) ===\n")

        for habit in habits:
            schedule = habit.get_schedule()
            scale = schedule.get_scale()

            lines.append(f"• {habit.name.upper()}")
            lines.append(f"  Schedule: {habit.schedule}")
            lines.append(f"  Created: {get_friendly_datetime(habit.created_at)}")
            lines.append(f"  Started: {get_friendly_datetime(habit.started_at)}")
            lines.append(f"  Next: {get_friendly_datetime(schedule.get_next_task(datetime.now()), scale)}")

            if habit.allocated_time:
                lines.append(f"  Duration: {get_friendly_elapsed(habit.allocated_time)}")
            if habit.inactivity_threshold:
                lines.append(f"  Timeout: {get_friendly_elapsed(habit.inactivity_threshold)}")

            # Trackers
            trackers = list(habit.trackers.where(HabitTracker.is_enabled == True))
            if trackers:
                tracker_names = [t.tracker for t in trackers]
                lines.append(f"  Trackers: {', '.join(tracker_names)}")

            # Activity stats
            buckets = habit.get_activity_buckets()
            lines.append(f"  Current streak: {habit.get_streak()}")
            lines.append(f"  Longest streak: {habit.get_longest_streak()}")
            if buckets:
                total_time = analytics.get_time_spent(buckets)
                lines.append(f"  Total time: {get_friendly_elapsed(total_time)}")
                lines.append(f"  Sessions completed: {len(buckets)}")
            lines.append("")

        # Global analytics
        lines.append("=== GLOBAL ANALYTICS ===\n")

        # Habits by schedule
        lines.append("Habits by schedule:")
        for schedule, group in analytics.group_habits_by_schedule(habits):
            habit_names = [h.name for h in group]
            lines.append(f"  {schedule.capitalize()}: {', '.join(habit_names)}")

        lines.append("")

        # Completion rates
        lines.append("Completion rates (best to worst):")
        sorted_habits = analytics.sort_habits_by_completion_rate(habits)
        for habit, rate in sorted_habits:
            lines.append(f"  {habit.name}: {rate * 100:.1f}%")

        lines.append("")

        # Champion habit
        champion = analytics.get_habit_with_longest_streak(habits)
        lines.append(f"Longest streak champion: {champion.name} ({champion.get_longest_streak()} periods)")

        return "\n".join(lines)

    def _generate_activity_text(self, habits):
        """Generate recent activity text"""
        lines = []
        lines.append("=== RECENT ACTIVITY ===\n")

        # Get recent buckets from all habits
        all_buckets = []
        for habit in habits:
            buckets = habit.get_activity_buckets()
            for bucket in buckets[-5:]:  # Last 5 buckets per habit
                all_buckets.append((habit, bucket))

        # Sort by end time
        all_buckets.sort(key=lambda x: x[1].end, reverse=True)

        if not all_buckets:
            lines.append("No recent activity")
        else:
            for habit, bucket in all_buckets[:10]:  # Show last 10 activities
                scale = habit.get_schedule().get_scale()
                start = get_friendly_datetime(bucket.start, scale)
                duration = get_friendly_elapsed(bucket.net_duration)
                lines.append(f"• {habit.name}: {start} ({duration}, {bucket.sessions} sessions)")

        return "\n".join(lines)

    def _get_modern_stylesheet(self):
        """Return clean, modern stylesheet"""
        return f"""
            QWidget {{
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                font-size: 13px;
            }}

            QTabWidget {{
                background-color: {self.colors['background']};
                border: none;
            }}

            QTabWidget::pane {{
                border: 1px solid {self.colors['border']};
                background-color: {self.colors['surface']};
                border-radius: 8px;
                margin-top: 4px;
            }}

            QTabBar::tab {{
                background-color: {self.colors['surface_variant']};
                color: {self.colors['text_secondary']};
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                border: 1px solid {self.colors['border']};
                border-bottom: none;
                font-weight: 500;
            }}

            QTabBar::tab:selected {{
                background-color: {self.colors['surface']};
                color: {self.colors['accent']};
                border-color: {self.colors['border']};
                font-weight: 600;
            }}

            QTabBar::tab:hover:!selected {{
                background-color: {self.colors['surface']};
                color: {self.colors['text_primary']};
            }}

            QPushButton {{
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }}

            QPushButton:hover {{
                background-color: {self.colors['accent_light']};
            }}

            QPushButton:pressed {{
                background-color: #5a54d6;
            }}

            QPushButton#closeButton {{
                background-color: {self.colors['primary_variant']};
                color: white;
                padding: 12px 24px;
                font-size: 14px;
            }}

            QPushButton#deleteButton {{
                background-color: #e74c3c;
                color: white;
            }}

            QPushButton#deleteButton:hover {{
                background-color: #c0392b;
            }}

            QPushButton#newButton {{
                background-color: {self.colors['surface']};
                color: {self.colors['accent']};
                border: 1px solid {self.colors['accent']};
            }}

            QPushButton#newButton:hover {{
                background-color: {self.colors['accent']};
                color: white;
            }}

            QLineEdit, QComboBox, QSpinBox {{
                background-color: {self.colors['surface']};
                border: 1px solid {self.colors['border']};
                padding: 10px 12px;
                border-radius: 6px;
                color: {self.colors['text_primary']};
                font-size: 13px;
            }}

            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
                border-color: {self.colors['border_focus']};
                outline: none;
            }}

            QListWidget {{
                background-color: {self.colors['surface']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                color: {self.colors['text_primary']};
                font-size: 13px;
            }}

            QListWidget::item {{
                padding: 12px;
                border-bottom: 1px solid {self.colors['surface_variant']};
                background-color: transparent;
            }}

            QListWidget::item:last {{
                border-bottom: none;
            }}

            QListWidget::item:selected {{
                background-color: {self.colors['accent_light']};
                color: white;
                border-radius: 4px;
            }}

            QListWidget::item:hover:!selected {{
                background-color: {self.colors['surface_variant']};
            }}

            QTextEdit {{
                background-color: {self.colors['surface']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                color: {self.colors['text_primary']};
                font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
                font-size: 12px;
                line-height: 1.4;
                padding: 12px;
            }}

            QLabel {{
                color: {self.colors['text_primary']};
                font-weight: normal;
            }}

            QLabel#sectionHeader {{
                color: {self.colors['text_primary']};
                font-size: 16px;
                font-weight: 600;
                padding: 8px 0px 16px 0px;
            }}

            QLabel#fieldLabel {{
                color: {self.colors['text_secondary']};
                font-weight: 500;
                font-size: 13px;
                margin-bottom: 4px;
            }}

            QCheckBox {{
                color: {self.colors['text_primary']};
                font-size: 13px;
                spacing: 8px;
            }}

            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
            }}

            QCheckBox::indicator:unchecked {{
                background-color: {self.colors['surface']};
                border: 2px solid {self.colors['border']};
            }}

            QCheckBox::indicator:checked {{
                background-color: {self.colors['accent']};
                border: 2px solid {self.colors['accent']};
                image: none;
            }}

            QCheckBox::indicator:checked:after {{
                content: "✓";
                color: white;
                font-weight: bold;
                font-size: 12px;
            }}

            QSplitter::handle {{
                background-color: {self.colors['border']};
                width: 1px;
            }}

            QScrollBar:vertical {{
                background: {self.colors['surface_variant']};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}

            QScrollBar::handle:vertical {{
                background: {self.colors['border']};
                border-radius: 4px;
                min-height: 20px;
            }}

            QScrollBar::handle:vertical:hover {{
                background: {self.colors['primary_variant']};
            }}

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                border: none;
                background: none;
                height: 0px;
            }}

            QFormLayout {{
                spacing: 12px;
            }}
        """

    def closeEvent(self, event):
        """Handle window close event"""
        self.refresh_timer.stop()
        event.accept()