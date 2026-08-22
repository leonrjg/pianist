"""
Entry Card - Shared chrome for ruled "programme" list entries.

Gives list rows (reminders, notepads, ...) a consistent card look - accent
tick, border, hover state - and a click-to-activate gesture. Subclasses own
all domain-specific content (what the tick color means, what the body shows).
"""

from PyQt6.QtWidgets import QFrame, QSizePolicy
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt

from gui.themes import current_theme as _t


class ClickableCard(QFrame):
    """A bordered card with an accent tick and a click-to-activate gesture."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _apply_card_style(self, tick_color: str):
        t = _t()
        class_name = type(self).__name__
        self.setStyleSheet(f"""
            {class_name} {{
                background-color: {t.card_bg};
                border: 1px solid {t.card_border};
                border-left: 3px solid {tick_color};
                border-radius: 5px;
            }}
            {class_name}:hover {{
                border-color: {t.card_hover_border};
                border-left-color: {tick_color};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_activate()
        super().mousePressEvent(event)

    def _on_activate(self):
        """Override to emit the subclass's activation signal."""
        pass
