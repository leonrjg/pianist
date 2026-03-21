"""
Accent Painter - Draws accent-colored decorative elements (hinges, pedals).

Responsible for painting all decorative accent elements on the piano.
"""

from PyQt6.QtGui import QPainter, QPen, QBrush
from PyQt6.QtCore import QPoint

from .base_painter import BasePainter
from ..constants import piano_colors


class AccentPainter(BasePainter):
    """Handles painting of decorative accent elements"""

    @staticmethod
    def draw_accent_elements(painter: QPainter, elements: list[tuple[int, int, int, int]]):
        """
        Draw accent elements (hinges, pedals) with consistent styling

        Args:
            painter: QPainter instance
            elements: List of (x, y, width, height) tuples for ellipses
        """
        color = piano_colors().ACCENT
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(color))
        for x, y, w, h in elements:
            painter.drawEllipse(x, y, w, h)

    @staticmethod
    def draw_pedal_rods(painter: QPainter, rod_positions: list[tuple[QPoint, QPoint]]):
        """
        Draw pedal connecting rods

        Args:
            painter: QPainter instance
            rod_positions: List of (start_point, end_point) tuples for lines
        """
        color = piano_colors().ACCENT
        painter.setPen(QPen(color, 2))
        for start, end in rod_positions:
            painter.drawLine(start, end)
