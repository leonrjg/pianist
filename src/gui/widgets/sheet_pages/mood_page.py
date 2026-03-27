"""
Mood Page - Manage moods and view mood logs.
"""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget, QPushButton, QMessageBox, QVBoxLayout, QSizePolicy
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from core.mood.service import MoodService
from core.mood.mood import Mood
from core.mood.mood_log import MoodLog
from core.util.time import get_friendly_datetime
from .base_page import SheetPage
from gui.constants import font_pt
from ..themed_form_widgets import ThemedLineEdit, ThemedButton, ThemedFormSection


from gui.themes import current_theme as _t


class MoodPage(SheetPage):
    """Page for managing moods and viewing logs"""

    def get_page_title(self) -> str:
        return "Mood"

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
        """Build last mood display section"""
        header = self._create_subsection_header("Last Mood")
        layout.addWidget(header)

        current_log = MoodService.get_current_log()
        if current_log:
            t = _t()
            container = QWidget()
            container.setStyleSheet(f"""
                QWidget {{
                    background-color: {t.card_bg};
                    border: 1px solid {t.accent};
                    border-radius: 4px;
                    padding: 8px;
                }}
            """)
            container_layout = QVBoxLayout()
            container_layout.setContentsMargins(8, 8, 8, 8)
            container_layout.setSpacing(4)
            container.setLayout(container_layout)

            mood_label = QLabel(f"{current_log.mood.symbol}  {current_log.mood.description}")
            mood_font = QFont()
            mood_font.setBold(True)
            mood_label.setFont(mood_font)
            container_layout.addWidget(mood_label)

            logged_time = get_friendly_datetime(current_log.start)
            time_label = self._create_text_label(f"Logged: {logged_time}", secondary=True)
            container_layout.addWidget(time_label)

            layout.addWidget(container)
        else:
            no_mood_label = self._create_text_label("No mood logged yet", secondary=True)
            layout.addWidget(no_mood_label)

    def _build_mood_list_section(self, layout):
        """Build mood list section"""
        header = self._create_subsection_header("Available Moods")
        layout.addWidget(header)

        moods = MoodService.get_all()
        for mood in moods:
            mood_row = self._create_mood_row(mood)
            layout.addWidget(mood_row)

    def _create_mood_row(self, mood: Mood) -> QWidget:
        """Create a row for a mood"""
        t = _t()
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(4, 4, 4, 4)
        row_layout.setSpacing(2)
        row.setLayout(row_layout)

        # Emoji (editable)
        emoji_edit = ThemedLineEdit("")
        emoji_edit.setText(mood.symbol)
        emoji_edit.setFixedWidth(50)
        emoji_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        emoji_edit.editingFinished.connect(lambda m=mood, e=emoji_edit: self._update_mood_symbol(m, e.text()))
        row_layout.addWidget(emoji_edit)

        # Description (editable)
        desc_edit = ThemedLineEdit("")
        desc_edit.setText(mood.description)
        desc_edit.editingFinished.connect(lambda m=mood, d=desc_edit: self._update_mood_description(m, d.text()))
        row_layout.addWidget(desc_edit)

        # Up button
        up_btn = QPushButton("↑")
        up_btn.setFixedSize(30, 26)
        up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        up_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.button_secondary_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 2px;
                color: {t.button_secondary_text};
            }}
            QPushButton:hover {{
                background-color: {t.button_secondary_hover};
            }}
        """)
        up_btn.clicked.connect(lambda: self._move_mood_up(mood))
        row_layout.addWidget(up_btn)

        # Down button
        down_btn = QPushButton("↓")
        down_btn.setFixedSize(30, 26)
        down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        down_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.button_secondary_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 2px;
                color: {t.button_secondary_text};
            }}
            QPushButton:hover {{
                background-color: {t.button_secondary_hover};
            }}
        """)
        down_btn.clicked.connect(lambda: self._move_mood_down(mood))
        row_layout.addWidget(down_btn)

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(30, 26)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(160, 50, 50, 100);
                border: 1px solid rgb(120, 40, 40);
                border-radius: 3px;
                padding: 2px;
                color: {t.ink_primary};
            }}
            QPushButton:hover {{
                background-color: rgba(180, 60, 60, 150);
            }}
        """)
        delete_btn.clicked.connect(lambda: self._delete_mood(mood))
        row_layout.addWidget(delete_btn)

        return row

    def _build_add_mood_section(self, layout):
        """Build add new mood section"""
        add_section = ThemedFormSection("Add New Mood")

        # Form container
        form = QWidget()
        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)
        form.setLayout(form_layout)

        # Emoji input
        self.emoji_input = ThemedLineEdit("Emoji")
        self.emoji_input.setFixedWidth(70)
        form_layout.addWidget(self.emoji_input)

        # Description input
        self.description_input = ThemedLineEdit("Description")
        form_layout.addWidget(self.description_input)

        # Add button
        add_btn = ThemedButton("Add")
        add_btn.clicked.connect(self._add_mood)
        form_layout.addWidget(add_btn)

        add_section.layout().addWidget(form)
        layout.addWidget(add_section)

    def _build_recent_logs_section(self, layout):
        """Build recent logs section"""
        header = self._create_subsection_header("Recent Logs")
        layout.addWidget(header)

        logs = MoodService.get_recent_logs(limit=15)
        if logs:
            for log in logs:
                log_row = self._create_log_row(log)
                layout.addWidget(log_row)
        else:
            no_logs_label = self._create_text_label("No mood logs yet", secondary=True)
            layout.addWidget(no_logs_label)

    def _create_log_row(self, log: MoodLog) -> QWidget:
        """Create a row for a mood log"""
        t = _t()
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
        desc_label.setStyleSheet(f"color: {t.ink_primary};")
        desc_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        row_layout.addWidget(desc_label)

        # Time
        start_time = get_friendly_datetime(log.start)
        time_label = self._create_text_label(start_time, secondary=True)
        row_layout.addWidget(time_label)

        row_layout.addStretch()

        # Delete button
        delete_btn = QPushButton("×")
        delete_btn.setFixedWidth(25)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(160, 50, 50, 80);
                border: 1px solid rgb(120, 40, 40);
                border-radius: 3px;
                padding: 0px;
                color: {t.ink_primary};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: rgba(180, 60, 60, 120);
            }}
        """)
        delete_btn.clicked.connect(lambda: self._delete_log(log))
        row_layout.addWidget(delete_btn)

        return row

    def _create_subsection_header(self, text: str) -> QLabel:
        """Create a subsection header"""
        label = QLabel(text)
        font = QFont()
        font.setPointSize(font_pt(11))
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {_t().ink_primary}; padding: 4px 0px 2px 0px;")
        return label

    def _delete_mood(self, mood):
        """Delete a mood"""
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
            MoodService.delete_mood(mood)
            self.refresh()
            self.content_updated.emit()

    def _add_mood(self):
        """Add a new mood"""
        symbol = self.emoji_input.text().strip()
        description = self.description_input.text().strip()

        if not symbol or not description:
            QMessageBox.warning(self, "Invalid Input", "Both emoji and description are required.")
            return

        MoodService.create_mood(symbol, description)
        self.emoji_input.clear()
        self.description_input.clear()
        self.refresh()
        self.content_updated.emit()

    def _update_mood_symbol(self, mood, new_symbol: str):
        """Update mood symbol"""
        new_symbol = new_symbol.strip()
        if new_symbol and new_symbol != mood.symbol:
            MoodService.update_mood_symbol(mood, new_symbol)
            self.content_updated.emit()

    def _update_mood_description(self, mood, new_description: str):
        """Update mood description"""
        new_description = new_description.strip()
        if new_description and new_description != mood.description:
            MoodService.update_mood_description(mood, new_description)
            self.content_updated.emit()

    def _move_mood_up(self, mood):
        """Move mood up in display order"""
        MoodService.move_mood_up(mood)
        self.refresh()
        self.content_updated.emit()

    def _move_mood_down(self, mood):
        """Move mood down in display order"""
        MoodService.move_mood_down(mood)
        self.refresh()
        self.content_updated.emit()

    def _delete_log(self, log):
        """Delete a mood log"""
        MoodService.delete_log(log)
        self.refresh()
        self.content_updated.emit()
