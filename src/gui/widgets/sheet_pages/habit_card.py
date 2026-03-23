"""
Habit Card - Reusable card component for displaying tasks.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from core.task import Task


from gui.themes import current_theme as _t
from gui.constants import font_pt


class HabitCard(QFrame):
    """Card for displaying a task (habit or manual)"""

    def __init__(self, task: 'Task' = None, subtitle: Optional[str] = None,
                 accent_color: Optional[str] = None, on_click: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None,
                 # Legacy parameters for backwards compatibility
                 habit=None, completed: bool = None, is_start_date: bool = None,
                 is_end_date: bool = None, task_datetime: Optional[datetime] = None,
                 parent=None):
        super().__init__(parent)

        # Support both new Task API and legacy habit API
        if task is not None:
            self.task = task
            self.habit = task.habit
            self.title = task.title
            self.completed = task.completed
            self.task_datetime = task.scheduled_at
            if task.habit:
                self.is_start_date = task.scheduled_at.date() == task.habit.started_at.date()
                self.is_end_date = task.habit.ended_at and task.scheduled_at.date() == task.habit.ended_at.date()
            else:
                self.is_start_date = False
                self.is_end_date = False
        else:
            self.task = None
            self.habit = habit
            self.title = habit.name if habit else "Untitled"
            self.completed = completed if completed is not None else False
            self.is_start_date = is_start_date if is_start_date is not None else False
            self.is_end_date = is_end_date if is_end_date is not None else False
            self.task_datetime = task_datetime

        self.subtitle = subtitle
        self.accent_color = accent_color or _t().border
        self.on_click = on_click
        self.on_complete = on_complete

        self._setup_ui()

    def _setup_ui(self):
        t = _t()
        if self.completed:
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: {t.card_bg_completed};
                    border-left: 4px solid {self.accent_color};
                    border-top: 1px solid {t.card_border};
                    border-right: 1px solid {t.card_border};
                    border-bottom: 1px solid {t.card_border};
                    border-radius: 3px;
                    padding: 8px;
                    margin: 2px 0px;
                }}
                HabitCard:hover {{
                    background-color: {t.card_bg};
                    border-top: 1px solid {t.card_hover_border};
                    border-right: 1px solid {t.card_hover_border};
                    border-bottom: 1px solid {t.card_hover_border};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: {t.card_bg};
                    border-left: 4px solid {self.accent_color};
                    border-top: 1px solid {t.card_border};
                    border-right: 1px solid {t.card_border};
                    border-bottom: 1px solid {t.card_border};
                    border-radius: 3px;
                    padding: 8px;
                    margin: 2px 0px;
                }}
                HabitCard:hover {{
                    background-color: {t.paper};
                    border-top: 1px solid {t.card_hover_border};
                    border-right: 1px solid {t.card_hover_border};
                    border-bottom: 1px solid {t.card_hover_border};
                }}
            """)

        if self.on_click:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)

        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(6)

        text_section = QVBoxLayout()
        text_section.setContentsMargins(0, 0, 0, 0)
        text_section.setSpacing(2)

        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)

        name_text = f"✓ {self.title}" if self.completed else self.title
        name_label = QLabel(name_text)
        font = QFont()
        font.setBold(True)
        font.setPointSize(font_pt(11))
        name_label.setFont(font)
        text_color = t.ink_secondary if self.completed else t.ink_primary
        name_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        name_layout.addWidget(name_label)

        badge_style = f"""
            background-color: {t.paper_dark};
            color: {t.ink_secondary};
            font-size: 9px;
            padding: 2px 4px;
            border-radius: 3px;
        """

        if self.habit:
            schedule_badge = QLabel(self.habit.schedule)
            schedule_badge.setStyleSheet(badge_style)
            name_layout.addWidget(schedule_badge)
        else:
            manual_badge = QLabel("manual")
            manual_badge.setStyleSheet(f"""
                background-color: {t.paper_dark};
                color: {t.link};
                font-size: 9px;
                padding: 2px 4px;
                border-radius: 3px;
            """)
            name_layout.addWidget(manual_badge)

        name_layout.addStretch()
        text_section.addLayout(name_layout)

        if self.subtitle:
            subtitle_layout = QHBoxLayout()
            subtitle_layout.setContentsMargins(0, 0, 0, 0)
            subtitle_layout.setSpacing(4)

            if self.is_start_date:
                start_badge = QLabel("🏁 Start")
                start_badge.setStyleSheet(badge_style)
                subtitle_layout.addWidget(start_badge)

            if self.is_end_date:
                end_badge = QLabel("🎻 End")
                end_badge.setStyleSheet(badge_style)
                subtitle_layout.addWidget(end_badge)

            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet(f"color: {t.ink_secondary}; font-size: 10px; background: transparent;")
            subtitle_layout.addWidget(subtitle_label)
            subtitle_layout.addStretch()
            text_section.addLayout(subtitle_layout)

        main_content_layout.addLayout(text_section)

        if self.task_datetime and self.on_complete:
            complete_btn = QPushButton()
            complete_btn.setFixedSize(24, 24)
            complete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            if self.completed:
                complete_btn.setText("✓")
                complete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t.button_primary_bg};
                        border: 2px solid {t.accent};
                        border-radius: 12px;
                        color: {t.button_primary_text};
                        font-size: 14px;
                        font-weight: bold;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {t.button_primary_hover};
                        border-color: {t.accent_light};
                    }}
                """)
            else:
                complete_btn.setText("")
                complete_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t.card_bg};
                        border: 2px solid {t.card_border};
                        border-radius: 12px;
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background-color: {t.paper};
                        border-color: {t.card_hover_border};
                    }}
                """)

            complete_btn.clicked.connect(lambda: self._toggle_completion())
            main_content_layout.addWidget(complete_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(main_content_layout)

    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.habit)

    def _toggle_completion(self):
        if self.on_complete:
            new_state = not self.completed
            self.on_complete(self.habit, self.task_datetime, new_state)
