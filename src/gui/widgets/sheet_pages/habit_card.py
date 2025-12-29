"""
Habit Card - Reusable vintage-styled card component for displaying habits.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable


class HabitCard(QFrame):
    """Vintage-styled card for displaying a habit with optional details"""

    def __init__(self, habit, subtitle: Optional[str] = None,
                 accent_color: Optional[str] = None, on_click: Optional[Callable] = None,
                 parent=None):
        """
        Args:
            habit: Habit object to display
            subtitle: Optional subtitle text (e.g., time info, schedule)
            accent_color: Optional left border color (defaults to sepia)
            on_click: Optional callback when card is clicked (receives habit)
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.subtitle = subtitle
        self.accent_color = accent_color or "rgb(200, 185, 160)"
        self.on_click = on_click

        self._setup_ui()

    def _setup_ui(self):
        """Setup the card UI"""
        # Card styling
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

        # Habit name (bold)
        name_label = QLabel(self.habit.name)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        name_label.setFont(font)
        name_label.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
        layout.addWidget(name_label)

        # Optional subtitle
        if self.subtitle:
            subtitle_label = QLabel(self.subtitle)
            subtitle_label.setStyleSheet("color: rgb(110, 90, 70); font-size: 10px; background: transparent;")
            layout.addWidget(subtitle_label)

    def mousePressEvent(self, event):
        """Handle click to trigger callback"""
        if self.on_click:
            self.on_click(self.habit)
