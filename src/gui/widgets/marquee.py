"""
Tips Marquee Widget - Scrolling tips display below the music stand holder.
"""

from typing import List

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont, QFontMetrics


class Marquee(QWidget):
    """A marquee widget that scrolls through tips to help users learn the UI."""

    @staticmethod
    def _text_color():
        from gui.constants import piano_colors, font_pt
        return piano_colors().FRAME_HIGHLIGHT

    TEXT_COLOR = QColor(180, 160, 140)  # fallback only
    SCROLL_SPEED = 1
    TICK_INTERVAL = 30
    TIP_SEPARATOR = "   •   "

    def __init__(self, tips: List[str], parent=None):
        super().__init__(parent)
        self._tips = tips
        self._expanded = False
        self._scroll_offset = 0
        self._text_width = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

        self._setup_ui()
        self._calculate_text_width()
        self._timer.start(self.TICK_INTERVAL)

    def _setup_ui(self):
        self.setFixedHeight(20)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # Spacer to push toggle to the right
        layout.addStretch()

        # Toggle button with "Tips" label
        self._toggle_btn = QPushButton("Tips ▶")
        self._toggle_btn.setFixedHeight(18)
        self._toggle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        from gui.constants import piano_colors, font_pt
        c = piano_colors()
        self._toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {c.FRAME_HIGHLIGHT.name()};
                font-size: 10px;
                padding: 0 4px;
            }}
            QPushButton:hover {{
                color: {c.ACCENT.name()};
            }}
        """)
        self._toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self._toggle_btn)

    def _get_full_text(self) -> str:
        return self.TIP_SEPARATOR.join(self._tips) + self.TIP_SEPARATOR

    def _calculate_text_width(self):
        font = QFont()
        from gui.constants import font_pt
        font.setPointSize(font_pt(9))
        metrics = QFontMetrics(font)
        self._text_width = metrics.horizontalAdvance(self._get_full_text())

    def _tick(self):
        if not self._expanded or self._text_width == 0:
            return
        self._scroll_offset += self.SCROLL_SPEED
        if self._scroll_offset >= self._text_width:
            self._scroll_offset = 0
        self.update()

    def paintEvent(self, event):
        if not self._expanded:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont()
        from gui.constants import font_pt
        font.setPointSize(font_pt(9))
        painter.setFont(font)
        painter.setPen(self._text_color())

        # Clip to area before the toggle button
        text_area_width = self._toggle_btn.x() - 4
        painter.setClipRect(0, 0, text_area_width, self.height())

        full_text = self._get_full_text()
        text_y = self.height() // 2 + painter.fontMetrics().ascent() // 2 - 1

        x1 = -self._scroll_offset
        x2 = x1 + self._text_width

        painter.drawText(int(x1), text_y, full_text)
        painter.drawText(int(x2), text_y, full_text)

    def _toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._toggle_btn.setText("Tips ▼")
        else:
            self._toggle_btn.setText("Tips ▶")
        self.update()

    def set_tips(self, tips: List[str]):
        self._tips = tips
        self._scroll_offset = 0
        self._calculate_text_width()
        self.update()

    def set_visible_marquee(self, visible: bool):
        self._expanded = visible
        if visible:
            self._toggle_btn.setText("Tips ▼")
        else:
            self._toggle_btn.setText("Tips ▶")
        self.update()
