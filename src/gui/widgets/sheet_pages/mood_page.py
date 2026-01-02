"""
Mood Page - Manage moods and view mood logs.
"""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton, QLineEdit, QMessageBox, QVBoxLayout
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from datetime import datetime

from core.mood.mood import Mood
from core.mood.mood_log import MoodLog
from core.util.time import get_friendly_datetime
from .base_page import SheetPage


class MoodPage(SheetPage):
    """Page for managing moods and viewing logs"""

    def get_page_title(self) -> str:
        return "Mood Management"

    def get_page_type(self) -> str:
        return "mood"

    def build_content(self):
        """Build the mood management page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header(self.get_page_title())
        layout.addWidget(title)

        # Current mood section
        self._build_current_mood_section(layout)

        layout.addSpacing(12)

        # Mood list section
        self._build_mood_list_section(layout)

        layout.addSpacing(12)

        # Add new mood section
        self._build_add_mood_section(layout)

        layout.addSpacing(12)

        # Recent logs section
        self._build_recent_logs_section(layout)

        layout.addStretch()

    def _build_current_mood_section(self, layout):
        """Build current mood display section"""
        header = self._create_subsection_header("Current Mood")
        layout.addWidget(header)

        current_log = Mood.get_current_mood_log()
        if current_log:
            # Container for current mood
            container = QWidget()
            container.setStyleSheet("""
                QWidget {
                    background-color: rgba(184, 134, 11, 30);
                    border: 1px solid rgb(184, 134, 11);
                    border-radius: 4px;
                    padding: 8px;
                }
            """)
            container_layout = QVBoxLayout()
            container_layout.setContentsMargins(8, 8, 8, 8)
            container_layout.setSpacing(4)
            container.setLayout(container_layout)

            # Mood display
            mood_label = QLabel(f"{current_log.mood.symbol}  {current_log.mood.description}")
            mood_font = QFont("Palatino", 16)
            mood_font.setBold(True)
            mood_label.setFont(mood_font)
            container_layout.addWidget(mood_label)

            # Time info
            start_time = get_friendly_datetime(current_log.start)
            end_time = get_friendly_datetime(current_log.end)
            time_label = self._create_text_label(f"Started: {start_time} • Ends: {end_time}", secondary=True)
            container_layout.addWidget(time_label)

            # End button
            end_btn = QPushButton("End Current Mood")
            end_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            end_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgb(92, 61, 46);
                    border: 1px solid rgb(120, 100, 75);
                    border-radius: 3px;
                    padding: 4px 8px;
                    color: rgb(252, 248, 235);
                }
                QPushButton:hover {
                    background-color: rgb(122, 80, 64);
                    border-color: rgb(184, 134, 11);
                }
            """)
            end_btn.clicked.connect(lambda: self._end_current_mood(current_log))
            container_layout.addWidget(end_btn)

            layout.addWidget(container)
        else:
            no_mood_label = self._create_text_label("No active mood", secondary=True)
            layout.addWidget(no_mood_label)

    def _build_mood_list_section(self, layout):
        """Build mood list section"""
        header = self._create_subsection_header("Available Moods")
        layout.addWidget(header)

        moods = Mood.get_all_ordered()
        for mood in moods:
            mood_row = self._create_mood_row(mood)
            layout.addWidget(mood_row)

    def _create_mood_row(self, mood: Mood) -> QWidget:
        """Create a row for a mood"""
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(4, 4, 4, 4)
        row_layout.setSpacing(8)
        row.setLayout(row_layout)

        # Emoji
        emoji_label = QLabel(mood.symbol)
        emoji_font = QFont("", 16)
        emoji_label.setFont(emoji_font)
        emoji_label.setFixedWidth(30)
        row_layout.addWidget(emoji_label)

        # Description
        desc_label = QLabel(mood.description)
        desc_label.setStyleSheet("color: rgb(70, 50, 35);")
        row_layout.addWidget(desc_label)

        row_layout.addStretch()

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(160, 50, 50, 100);
                border: 1px solid rgb(120, 40, 40);
                border-radius: 3px;
                padding: 2px 6px;
                color: rgb(70, 50, 35);
            }
            QPushButton:hover {
                background-color: rgba(180, 60, 60, 150);
            }
        """)
        delete_btn.clicked.connect(lambda: self._delete_mood(mood))
        row_layout.addWidget(delete_btn)

        return row

    def _build_add_mood_section(self, layout):
        """Build add new mood section"""
        header = self._create_subsection_header("Add New Mood")
        layout.addWidget(header)

        # Form container
        form = QWidget()
        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)
        form.setLayout(form_layout)

        # Emoji input
        self.emoji_input = QLineEdit()
        self.emoji_input.setPlaceholderText("Emoji")
        self.emoji_input.setFixedWidth(60)
        form_layout.addWidget(self.emoji_input)

        # Description input
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText("Description")
        form_layout.addWidget(self.description_input)

        # Add button
        add_btn = QPushButton("Add")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: rgb(92, 61, 46);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 3px;
                padding: 4px 12px;
                color: rgb(252, 248, 235);
            }
            QPushButton:hover {
                background-color: rgb(122, 80, 64);
                border-color: rgb(218, 165, 32);
            }
        """)
        add_btn.clicked.connect(self._add_mood)
        form_layout.addWidget(add_btn)

        layout.addWidget(form)

    def _build_recent_logs_section(self, layout):
        """Build recent logs section"""
        header = self._create_subsection_header("Recent Logs")
        layout.addWidget(header)

        logs = MoodLog.get_recent_logs(limit=15)
        if logs:
            for log in logs:
                log_row = self._create_log_row(log)
                layout.addWidget(log_row)
        else:
            no_logs_label = self._create_text_label("No mood logs yet", secondary=True)
            layout.addWidget(no_logs_label)

    def _create_log_row(self, log: MoodLog) -> QWidget:
        """Create a row for a mood log"""
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(4, 2, 4, 2)
        row_layout.setSpacing(8)
        row.setLayout(row_layout)

        # Emoji
        emoji_label = QLabel(log.mood.symbol)
        emoji_label.setFixedWidth(25)
        row_layout.addWidget(emoji_label)

        # Description
        desc_label = QLabel(log.mood.description)
        desc_label.setStyleSheet("color: rgb(70, 50, 35);")
        desc_label.setFixedWidth(200)
        row_layout.addWidget(desc_label)

        # Time
        start_time = get_friendly_datetime(log.start)
        duration = log.get_duration_seconds() // 60  # minutes
        time_label = self._create_text_label(f"{start_time} • {duration}m", secondary=True)
        row_layout.addWidget(time_label)

        row_layout.addStretch()

        return row

    def _create_subsection_header(self, text: str) -> QLabel:
        """Create a subsection header"""
        label = QLabel(text)
        font = QFont("Palatino", 11)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("color: rgb(70, 50, 35); padding: 4px 0px 2px 0px;")
        return label

    def _end_current_mood(self, log: MoodLog):
        """End the current mood"""
        log.end_now('manual')
        self.refresh()
        self.content_updated.emit()

    def _delete_mood(self, mood: Mood):
        """Delete a mood"""
        # Check if mood has logs for warning message
        has_logs = not mood.can_delete()
        warning_text = f"Delete mood '{mood.description}'?"
        if has_logs:
            warning_text += "\n\nThis will also delete all associated logs."
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            warning_text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            mood.delete_instance()
            self.refresh()
            self.content_updated.emit()

    def _add_mood(self):
        """Add a new mood"""
        symbol = self.emoji_input.text().strip()
        description = self.description_input.text().strip()

        if not symbol or not description:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Both emoji and description are required."
            )
            return

        # Get max display_order
        max_order = 0
        moods = Mood.select()
        if moods.count() > 0:
            max_order = max(m.display_order for m in moods)

        Mood.create(
            symbol=symbol,
            description=description,
            display_order=max_order + 1
        )

        self.emoji_input.clear()
        self.description_input.clear()
        self.refresh()
        self.content_updated.emit()
