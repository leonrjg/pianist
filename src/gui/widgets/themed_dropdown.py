"""
ThemedDropdown - A dropdown widget styled for the wood paper aesthetic.
"""

from PyQt6.QtWidgets import QPushButton, QMenu
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from .sheet_pages.theme_styles import get_menu_stylesheet
from gui.themes import current_theme as _t, ThemedWidget


class ThemedDropdown(QPushButton, ThemedWidget):
    """A dropdown button styled for the active theme.

    Items may be plain strings or (label, data) tuples.  When plain strings are
    used, `selected_data` equals the label.
    """

    selection_changed = pyqtSignal(str)  # Emits selected label

    def __init__(self, items, default_item=None, parent=None):
        super().__init__(parent)
        # Normalise to (label, data) pairs
        self._pairs: list[tuple[str, object]] = [
            (i, i) if isinstance(i, str) else (i[0], i[1]) for i in items
        ]
        default_label = default_item if isinstance(default_item, str) else (default_item[0] if isinstance(default_item, tuple) else None)
        first_label = self._pairs[0][0] if self._pairs else ""
        self.selected_item = default_label or first_label
        self.selected_data = next((d for l, d in self._pairs if l == self.selected_item), None)

        self.setText(self.selected_item)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setMaximumWidth(100)

        self.menu = QMenu(self)
        self._setup_style()

        for label, data in self._pairs:
            action = self.menu.addAction(label)
            action.triggered.connect(lambda checked, l=label, d=data: self._on_item_selected(l, d))

        self.setMenu(self.menu)

    def _setup_style(self):
        t = _t()
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {t.link};
                text-decoration: underline;
                border: none;
                text-align: left;
                padding: 2px 4px;
            }}
            QPushButton:hover {{
                color: {t.link_hover};
            }}
            QPushButton::menu-indicator {{
                right: 6px;
                bottom: 2px;
            }}
        """)
        self.menu.setStyleSheet(get_menu_stylesheet())

    def _on_item_selected(self, label: str, data):
        self.selected_item = label
        self.selected_data = data
        self.setText(label)
        self.selection_changed.emit(label)

    def get_selected(self):
        return self.selected_item

    def set_selected(self, label: str):
        for l, d in self._pairs:
            if l == label:
                self.selected_item = l
                self.selected_data = d
                self.setText(l)
                return

    def set_selected_by_data(self, data):
        for l, d in self._pairs:
            if d == data:
                self.selected_item = l
                self.selected_data = d
                self.setText(l)
                return

    def set_items(self, items, default_data=None):
        """Replace all items. Items may be strings or (label, data) tuples."""
        self._pairs = [
            (i, i) if isinstance(i, str) else (i[0], i[1]) for i in items
        ]
        self.menu.clear()
        for label, data in self._pairs:
            action = self.menu.addAction(label)
            action.triggered.connect(lambda checked, l=label, d=data: self._on_item_selected(l, d))

        # Restore selection: prefer matching default_data, else first item
        matched = next(((l, d) for l, d in self._pairs if d == default_data), None)
        first = self._pairs[0] if self._pairs else ("", None)
        label, data = matched or first
        self.selected_item = label
        self.selected_data = data
        self.setText(label)
