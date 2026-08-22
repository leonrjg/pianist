"""
Staff Strip Painter - Draws today's task completion summary on the fallboard.

One note per task due today, stacked top-to-bottom:
  - Filled circle = completed
  - Hollow circle = pending
Horizontal stem extends left from each circle head.
"""

from PyQt6.QtGui import QPainter, QPen, QBrush
from PyQt6.QtCore import Qt, QRectF

from .base_painter import BasePainter
from ..models.piano_geometry import PianoGeometry
from ..constants import font_pt, piano_colors


_HEAD_D = 7       # note head diameter
_NOTE_GAP = 8     # vertical gap between note centres
_FRAC_GAP = 5     # gap between last note's bottom edge and fraction text
_FRAC_H = 14      # height of fraction text box
_V_MARGIN = 10    # top/bottom breathing room so notes never touch the edges


def _slot_h() -> int:
    """Vertical space occupied by one note (head + following gap)."""
    return _HEAD_D + _NOTE_GAP


def _capacity(rect) -> int:
    """How many notes fit in the strip once top/bottom margins are honoured."""
    avail = rect.height() - 2 * _V_MARGIN
    if avail < _HEAD_D:
        return 0
    # n notes need n*_HEAD_D + (n-1)*_NOTE_GAP <= avail
    return int((avail + _NOTE_GAP) // _slot_h())


def _visible_count(rect, n: int) -> tuple:
    """Return (shown, overflow) — how many note heads to draw and whether an
    ellipsis indicator is needed for the remainder that doesn't fit."""
    cap = _capacity(rect)
    if n <= cap:
        return n, False
    # Reserve the last slot for the overflow indicator.
    return max(0, cap - 1), True


def _note_centres(rect, n: int):
    """Yield (cx, cy) for each of n notes, centred vertically within the
    margined region of the strip."""
    total_h = n * _HEAD_D + max(0, n - 1) * _NOTE_GAP
    top_y = rect.top() + _V_MARGIN + max(0, (rect.height() - 2 * _V_MARGIN - total_h) / 2)
    cx = rect.left() + rect.width() * 0.45
    for i in range(n):
        cy = top_y + i * _slot_h() + _HEAD_D / 2
        yield cx, cy


class StaffStripPainter(BasePainter):
    """Draws the staff strip overlaid on the fallboard."""

    @staticmethod
    def get_note_rects(geometry: PianoGeometry, n: int) -> list:
        """Return full-width fallboard row rects for each of n notes (for hit-testing).
        Returns empty list when n == 0 (chevron mode — no interactive note areas)."""
        if n == 0:
            return []
        rect = geometry.fallboard_rect
        shown, _ = _visible_count(rect, n)
        slot_h = _slot_h()
        return [
            QRectF(rect.left(), cy - slot_h / 2, rect.width(), slot_h)
            for _, cy in _note_centres(rect, shown)
        ]

    @staticmethod
    def _draw_chevron(painter: QPainter, rect) -> None:
        """Draw the « drawer-toggle hint, centred on the fallboard."""
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setPixelSize(16)
        painter.setFont(font)
        painter.setPen(QPen(piano_colors().ACCENT))
        x = rect.left() + (rect.width() // 2) - 8
        y = rect.top() + (rect.height() // 2) + 6
        painter.drawText(x, y, "«")

    @staticmethod
    def draw(painter: QPainter, geometry: PianoGeometry, completions: list) -> None:
        rect = geometry.fallboard_rect
        if rect.isEmpty():
            return

        painter.save()
        painter.setClipRect(rect)

        # No tasks today — show the chevron drawer hint instead
        if not completions:
            StaffStripPainter._draw_chevron(painter, rect)
            painter.restore()
            return

        ink = piano_colors().ACCENT
        n = len(completions)
        shown, overflow = _visible_count(rect, n)
        centres = list(_note_centres(rect, shown))

        for completed, (cx, cy) in zip(completions[:shown], centres):
            # Stem — flush with the left edge of the fallboard
            painter.setPen(QPen(ink, 1.5))
            painter.drawLine(
                rect.left(), int(cy),
                int(cx - _HEAD_D / 2), int(cy),
            )

            # Head
            head_rect = QRectF(cx - _HEAD_D / 2, cy - _HEAD_D / 2, _HEAD_D, _HEAD_D)
            painter.setPen(QPen(ink, 1.5))
            painter.setBrush(QBrush(ink) if completed else Qt.BrushStyle.NoBrush)
            painter.drawEllipse(head_rect)

        if overflow:
            StaffStripPainter._draw_overflow(painter, rect, centres, ink)

        painter.restore()

    @staticmethod
    def _draw_overflow(painter: QPainter, rect, centres: list, ink) -> None:
        """Draw a vertical ellipsis below the last visible note to signal that
        more tasks exist than the strip can show at this height."""
        from PyQt6.QtGui import QFont
        last_cy = centres[-1][1] if centres else rect.top() + _V_MARGIN
        cx = rect.left() + rect.width() * 0.45
        cy = last_cy + _slot_h()
        font = QFont()
        font.setPixelSize(12)
        painter.setFont(font)
        painter.setPen(QPen(ink))
        painter.drawText(
            QRectF(rect.left(), cy - _slot_h() / 2, rect.width(), _slot_h()),
            Qt.AlignmentFlag.AlignCenter,
            "⋮",
        )
