"""
Habit Card - Reusable vintage-styled card component for displaying tasks.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from core.task import Task


class HabitCard(QFrame):
    """Vintage-styled card for displaying a task (habit or manual)"""

    def __init__(self, task: 'Task' = None, subtitle: Optional[str] = None,
                 accent_color: Optional[str] = None, on_click: Optional[Callable] = None,
                 on_complete: Optional[Callable] = None,
                 # Legacy parameters for backwards compatibility
                 habit=None, completed: bool = None, is_start_date: bool = None,
                 is_end_date: bool = None, task_datetime: Optional[datetime] = None,
                 parent=None):
        """
        Args:
            task: Task object to display (new unified API)
            subtitle: Optional subtitle text (e.g., time info, schedule)
            accent_color: Optional left border color (defaults to sepia)
            on_click: Optional callback when card is clicked (receives habit or None for manual tasks)
            on_complete: Optional callback when completion is toggled (receives habit, task_datetime, new_state)

            Legacy parameters (for backwards compatibility):
            habit: Habit object to display
            completed: Whether the task is completed
            is_start_date: Whether this task is on the habit's start date
            is_end_date: Whether this task is on the habit's end date
            task_datetime: Datetime for the scheduled task
            parent: Parent widget
        """
        super().__init__(parent)

        # Support both new Task API and legacy habit API
        if task is not None:
            self.task = task
            self.habit = task.habit
            self.title = task.title
            self.completed = task.completed
            self.task_datetime = task.scheduled_at
            # Only set start/end flags for habit tasks
            if task.habit:
                self.is_start_date = task.scheduled_at.date() == task.habit.started_at.date()
                self.is_end_date = task.habit.ended_at and task.scheduled_at.date() == task.habit.ended_at.date()
            else:
                self.is_start_date = False
                self.is_end_date = False
        else:
            # Legacy API
            self.task = None
            self.habit = habit
            self.title = habit.name if habit else "Untitled"
            self.completed = completed if completed is not None else False
            self.is_start_date = is_start_date if is_start_date is not None else False
            self.is_end_date = is_end_date if is_end_date is not None else False
            self.task_datetime = task_datetime

        self.subtitle = subtitle
        self.accent_color = accent_color or "rgb(200, 185, 160)"
        self.on_click = on_click
        self.on_complete = on_complete

        self._setup_ui()

    def _setup_ui(self):
        """Setup the card UI"""
        # Adjust opacity for completed tasks
        if self.completed:
            bg_opacity = 100
            hover_opacity = 120
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: rgba(255, 252, 245, {bg_opacity});
                    border-left: 4px solid {self.accent_color};
                    border-top: 1px solid rgb(200, 185, 160);
                    border-right: 1px solid rgb(200, 185, 160);
                    border-bottom: 1px solid rgb(200, 185, 160);
                    border-radius: 3px;
                    padding: 8px;
                    margin: 2px 0px;
                    opacity: 0.1;
                }}
                HabitCard:hover {{
                    background-color: rgba(255, 255, 250, {hover_opacity});
                    border-top: 1px solid rgb(184, 134, 11);
                    border-right: 1px solid rgb(184, 134, 11);
                    border-bottom: 1px solid rgb(184, 134, 11);
                    opacity: 1;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                HabitCard {{
                    background-color: rgba(255, 252, 245, 180);
                    border-left: 4px solid {self.accent_color};
                    border-top: 1px solid rgb(200, 185, 160);
                    border-right: 1px solid rgb(200, 185, 160);
                    border-bottom: 1px solid rgb(200, 185, 160);
                    border-radius: 3px;
                    padding: 8px;
                    margin: 2px 0px;
                }}
                HabitCard:hover {{
                    background-color: rgba(255, 255, 250, 200);
                    border-top: 1px solid rgb(184, 134, 11);
                    border-right: 1px solid rgb(184, 134, 11);
                    border-bottom: 1px solid rgb(184, 134, 11);
                }}
            """)

        if self.on_click:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)

        # Create horizontal layout to hold text section and completion button
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(6)

        # Text section (vertical layout for name and subtitle)
        text_section = QVBoxLayout()
        text_section.setContentsMargins(0, 0, 0, 0)
        text_section.setSpacing(2)

        # Name row with optional schedule badge
        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)

        # Task title (bold) with optional checkmark
        name_text = f"✓ {self.title}" if self.completed else self.title
        name_label = QLabel(name_text)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        name_label.setFont(font)
        # Dimmed color if completed
        text_color = "rgb(120, 100, 80)" if self.completed else "rgb(70, 50, 35)"
        name_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        name_layout.addWidget(name_label)

        # Schedule badge (only for habit tasks)
        if self.habit:
            schedule_badge = QLabel(self.habit.schedule)
            schedule_badge.setStyleSheet("""
                background-color: rgba(200, 185, 160, 120);
                color: rgb(70, 50, 35);
                font-size: 9px;
                padding: 2px 4px;
                border-radius: 3px;
            """)
            name_layout.addWidget(schedule_badge)
        else:
            # Manual task badge
            manual_badge = QLabel("manual")
            manual_badge.setStyleSheet("""
                background-color: rgba(140, 110, 180, 120);
                color: rgb(70, 50, 35);
                font-size: 9px;
                padding: 2px 4px;
                border-radius: 3px;
            """)
            name_layout.addWidget(manual_badge)

        name_layout.addStretch()

        text_section.addLayout(name_layout)

        # Optional subtitle with start badge
        if self.subtitle:
            subtitle_layout = QHBoxLayout()
            subtitle_layout.setContentsMargins(0, 0, 0, 0)
            subtitle_layout.setSpacing(4)

            # Add start badge if this is the start date
            if self.is_start_date:
                start_badge = QLabel("🏁 Start")
                start_badge.setStyleSheet("""
                    background-color: rgba(200, 185, 160, 120);
                    color: rgb(70, 50, 35);
                    font-size: 9px;
                    padding: 2px 4px;
                    border-radius: 3px;
                """)
                subtitle_layout.addWidget(start_badge)

            # Add end badge if this is the end date
            if self.is_end_date:
                end_badge = QLabel("🎻 End")
                end_badge.setStyleSheet("""
                    background-color: rgba(200, 185, 160, 120);
                    color: rgb(70, 50, 35);
                    font-size: 9px;
                    padding: 2px 4px;
                    border-radius: 3px;
                """)
                subtitle_layout.addWidget(end_badge)

            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet("color: rgb(110, 90, 70); font-size: 10px; background: transparent;")
            subtitle_layout.addWidget(subtitle_label)
            subtitle_layout.addStretch()

            text_section.addLayout(subtitle_layout)

        # Add text section to main content layout
        main_content_layout.addLayout(text_section)

        # Completion button (if task_datetime and on_complete provided)
        if self.task_datetime and self.on_complete:
            complete_btn = QPushButton()
            complete_btn.setFixedSize(24, 24)
            complete_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

            if self.completed:
                # Checked state - filled checkmark
                complete_btn.setText("✓")
                complete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(184, 134, 11, 180);
                        border: 2px solid rgb(184, 134, 11);
                        border-radius: 12px;
                        color: rgb(255, 252, 245);
                        font-size: 14px;
                        font-weight: bold;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(218, 165, 32, 200);
                        border-color: rgb(218, 165, 32);
                    }
                """)
            else:
                # Unchecked state - empty circle
                complete_btn.setText("")
                complete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(255, 252, 245, 150);
                        border: 2px solid rgb(150, 130, 100);
                        border-radius: 12px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: rgba(255, 252, 245, 200);
                        border-color: rgb(184, 134, 11);
                    }
                """)

            complete_btn.clicked.connect(lambda: self._toggle_completion())
            main_content_layout.addWidget(complete_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Add main content layout to card
        layout.addLayout(main_content_layout)

    def mousePressEvent(self, event):
        """Handle click to trigger callback"""
        if self.on_click:
            self.on_click(self.habit)

    def _toggle_completion(self):
        """Toggle completion state and notify callback"""
        if self.on_complete:
            new_state = not self.completed
            self.on_complete(self.habit, self.task_datetime, new_state)
