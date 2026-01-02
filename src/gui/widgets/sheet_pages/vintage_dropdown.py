"""
VintageDropdown - A dropdown widget styled for the vintage paper aesthetic.
"""

from PyQt6.QtWidgets import QPushButton, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from .vintage_styles import VINTAGE_MENU_STYLE


class VintageDropdown(QPushButton):
    """A dropdown button with vintage paper styling"""

    selection_changed = pyqtSignal(str)  # Emits selected value

    def __init__(self, items, default_item=None, parent=None):
        super().__init__(parent)
        self.items = items
        self.selected_item = default_item or (items[0] if items else "")

        self.setText(self.selected_item)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Vintage button styling
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: rgb(120, 80, 50);
                text-decoration: underline;
                border: none;
                text-align: left;
                padding: 2px 4px;
            }
            QPushButton:hover {
                color: rgb(160, 110, 70);
            }
        """)

        # Create vintage menu
        self.menu = QMenu(self)
        self.menu.setStyleSheet(VINTAGE_MENU_STYLE)

        # Add menu items
        for item in items:
            action = self.menu.addAction(item)
            action.triggered.connect(lambda checked, i=item: self._on_item_selected(i))

        self.setMenu(self.menu)

    def _on_item_selected(self, item):
        """Handle item selection"""
        self.selected_item = item
        self.setText(item)
        self.selection_changed.emit(item)

    def get_selected(self):
        """Get the currently selected item"""
        return self.selected_item

    def set_selected(self, item):
        """Set the selected item"""
        if item in self.items:
            self.selected_item = item
            self.setText(item)
