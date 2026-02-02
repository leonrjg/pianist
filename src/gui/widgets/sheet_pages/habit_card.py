"""
Habit Card - Reusable vintage-styled card component for displaying habits.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable
from datetime import datetime


class HabitCard(QFrame):
    """Vintage-styled card for displaying a habit with optional details"""

    def __init__(self, habit, subtitle: Optional[str] = None,
                 accent_color: Optional[str] = None, on_click: Optional[Callable] = None,
                 completed: bool = False, is_start_date: bool = False, is_end_date: bool = False,
                 task_datetime: Optional[datetime] = None, on_complete: Optional[Callable] = None,
                 parent=None):
        """
        Args:
            habit: Habit object to display
            subtitle: Optional subtitle text (e.g., time info, schedule)
            accent_color: Optional left border color (defaults to sepia)
            on_click: Optional callback when card is clicked (receives habit)
            completed: Whether the task is completed (shows checkmark)
            is_start_date: Whether this task is on the habit's start date
            is_end_date: Whether this task is on the habit's end date
            task_datetime: Optional datetime for the scheduled task (enables completion button)
            on_complete: Optional callback when completion is toggled (receives habit, task_datetime, new_state)
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.subtitle = subtitle
        self.accent_color = accent_color or "rgb(200, 185, 160)"
        self.on_click = on_click
        self.completed = completed
        self.is_start_date = is_start_date
        self.is_end_date = is_end_date
        self.task_datetime = task_datetime
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

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        self.setLayout(layout)

        # Name row with schedule badge
        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(0, 0, 0, 0)
        name_layout.setSpacing(6)

        # Habit name (bold) with optional checkmark
        name_text = f"✓ {self.habit.name}" if self.completed else self.habit.name
        name_label = QLabel(name_text)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        name_label.setFont(font)
        # Dimmed color if completed
        text_color = "rgb(120, 100, 80)" if self.completed else "rgb(70, 50, 35)"
        name_label.setStyleSheet(f"color: {text_color}; background: transparent;")
        name_layout.addWidget(name_label)

        # Schedule badge
        schedule_badge = QLabel(self.habit.schedule)
        schedule_badge.setStyleSheet("""
            background-color: rgba(200, 185, 160, 120);
            color: rgb(70, 50, 35);
            font-size: 9px;
            padding: 2px 4px;
            border-radius: 3px;
        """)
        name_layout.addWidget(schedule_badge)
        name_layout.addStretch()

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
            name_layout.addWidget(complete_btn)

        layout.addLayout(name_layout)

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
            
            layout.addLayout(subtitle_layout)

    def mousePressEvent(self, event):
        """Handle click to trigger callback"""
        if self.on_click:
            self.on_click(self.habit)

    def _toggle_completion(self):
        """Toggle completion state and notify callback"""
        if self.on_complete:
            new_state = not self.completed
            self.on_complete(self.habit, self.task_datetime, new_state)
