"""
Stat Card - Wood-styled summary statistic card component.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt


from gui.themes import current_theme as _t


class StatCard(QFrame):
    """Wood-styled card for displaying a single summary statistic"""

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
        t = _t()
        self.setStyleSheet(f"""
            StatCard {{
                background-color: {t.card_bg};
                border: 1px solid {t.accent};
                border-radius: 3px;
                padding: 2px;
                margin: 2px;
            }}
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
        title_label.setStyleSheet(f"color: {t.ink_secondary}; background: transparent;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Value (large and prominent)
        value_label = QLabel(self.value)
        value_label.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Set minimum width for better grid layout
        self.setMinimumWidth(100)
