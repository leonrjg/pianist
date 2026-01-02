"""
Stat Card - Vintage-styled summary statistic card component.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


class StatCard(QFrame):
    """Vintage-styled card for displaying a single summary statistic"""

    def __init__(self, title: str, value: str, icon: str = "", parent=None):
        """
        Args:
            title: Stat title (e.g., "Total Practice Time")
            value: Stat value (e.g., "24h 35m")
            icon: Optional unicode icon/emoji
            parent: Parent widget
        """
        super().__init__(parent)
        self.title = title
        self.value = value
        self.icon = icon

        self._setup_ui()

    def _setup_ui(self):
        """Set up the card UI"""
        # Card styling with vintage paper and brass accents - more compact
        self.setStyleSheet("""
            StatCard {
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 3px;
                padding: 2px;
                margin: 2px;
            }
        """)

        # Layout
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 2, 1, 2)
        layout.setSpacing(1)
        self.setLayout(layout)

        # Icon and title
        if self.icon:
            title_text = f"{self.icon} {self.title}"
        else:
            title_text = self.title

        title_label = QLabel(title_text)
        title_label.setStyleSheet("color: rgb(110, 90, 70); background: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Value (large and prominent)
        value_label = QLabel(self.value)
        value_label.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Set minimum width for better grid layout
        self.setMinimumWidth(100)
