"""
Notepad Card - Programme-style entry for a single habit notepad.

Shares its card chrome and click-to-activate gesture with ReminderCard via
ClickableCard, but its body is notepad-specific: a title and a content
preview, no time gutter. Clicking the card opens the notepad in the
toggleable notepad pane.
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QWidget, QSizePolicy
from PyQt6.QtCore import pyqtSignal

from gui.themes import current_theme as _t
from gui.constants import make_font
from .entry_card import ClickableCard


class NotepadCard(ClickableCard):
    """A single ruled programme entry for a habit notepad."""

    open_clicked = pyqtSignal(object)  # Emits note

    def __init__(self, note, parent=None):
        super().__init__(parent)
        self.note = note
        self._setup_ui()

    def _setup_ui(self):
        t = _t()
        self.setToolTip("Click to open")
        self._apply_card_style(t.accent)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 9, 8, 9)
        row.setSpacing(8)
        row.addWidget(self._build_body(t), 1)

    def _build_body(self, t) -> QWidget:
        """Title plus a one-line content preview."""
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        box = QVBoxLayout(body)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(2)

        title_lbl = QLabel(self.note.title)
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_font = make_font(t.header_font, 12)
        title_lbl.setFont(title_font)
        title_lbl.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        box.addWidget(title_lbl)

        preview = self._preview_text()
        if preview:
            preview_lbl = QLabel(preview)
            preview_lbl.setWordWrap(True)
            preview_lbl.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 10px;")
            box.addWidget(preview_lbl)

        return body

    def _on_activate(self):
        self.open_clicked.emit(self.note)

    def _preview_text(self) -> str:
        preview = (self.note.content or "").strip().replace("\n", " ")
        if len(preview) > 80:
            preview = preview[:80] + "…"
        return preview
