"""
Thoughts Page - Reverse-chronological list of quick thoughts.
"""

from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget, QSizePolicy
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from gui.themes import current_theme as _t
from gui.constants import font_pt

from core.notes.service import NoteService


class ThoughtsPage(SheetPage):

    def get_page_title(self) -> str:
        return "Thoughts"

    def get_page_type(self) -> str:
        return "thoughts"

    def build_content(self):
        layout = self.layout()
        layout.addWidget(self._create_section_header("Thoughts"))

        thoughts = NoteService.list_thoughts()

        if not thoughts:
            empty = self._create_text_label("No thoughts yet.", secondary=True)
            layout.addWidget(empty)
        else:
            for thought in thoughts:
                layout.addWidget(self._build_thought_card(thought))
                layout.addSpacing(4)

        layout.addStretch()

    def _build_thought_card(self, thought) -> QWidget:
        t = _t()

        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 4px;
            }}
        """)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(8, 6, 8, 6)
        card_layout.setSpacing(4)
        card.setLayout(card_layout)

        content_label = QLabel(thought.content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        content_label.setStyleSheet(f"""
            QLabel {{
                color: {t.ink_primary};
                font-size: {font_pt(10)}pt;
                background: transparent;
                border: none;
            }}
        """)
        content_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        card_layout.addWidget(content_label)

        ts_label = QLabel(thought.created_at.strftime("%Y-%m-%d %H:%M"))
        ts_label.setStyleSheet(f"""
            QLabel {{
                color: {t.ink_secondary};
                font-size: {font_pt(8)}pt;
                background: transparent;
                border: none;
            }}
        """)
        card_layout.addWidget(ts_label)

        return card
