"""
Brass Painter - Draws brass elements (hinges, pedals).

Responsible for painting all brass decorative elements on the piano.
"""

from PyQt6.QtGui import QPainter, QPen, QBrush
from PyQt6.QtCore import QPoint

from .base_painter import BasePainter
from ..constants import PianoColors


class BrassPainter(BasePainter):
    """Handles painting of brass elements"""

    @staticmethod
    def draw_brass_elements(painter: QPainter, elements: list[tuple[int, int, int, int]]):
        """
        Draw brass elements (hinges, pedals) with consistent styling

        Args:
            painter: QPainter instance
            elements: List of (x, y, width, height) tuples for ellipses
        """
        brass_color = PianoColors.BRASS
        painter.setPen(QPen(brass_color, 1))
        painter.setBrush(QBrush(brass_color))
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
        brass_color = PianoColors.BRASS
        painter.setPen(QPen(brass_color, 2))
        for start, end in rod_positions:
            painter.drawLine(start, end)
