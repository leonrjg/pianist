"""
Base Painter - Shared painting utilities.

Provides common painting operations used by all specific painters.
"""

from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt


class BasePainter:
    """Base class with shared painting utilities"""

    @staticmethod
    def draw_gradient_rect(painter: QPainter, x1: int, y1: int, x2: int, y2: int,
                          color1: QColor, color2: QColor, vertical: bool = False):
        """Draw a rectangle with gradient fill"""
        gradient = QLinearGradient()
        if vertical:
            gradient.setStart(0, y1)
            gradient.setFinalStop(0, y2)
        else:
            gradient.setStart(x1, 0)
            gradient.setFinalStop(x2, 0)

        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    @staticmethod
    def interpolate_color(color1: QColor, color2: QColor, ratio: float) -> QColor:
        """Interpolate between two QColors"""
        ratio = max(0.0, min(1.0, ratio))  # Clamp ratio to [0, 1]
        r = int(color1.red() + (color2.red() - color1.red()) * ratio)
        g = int(color1.green() + (color2.green() - color1.green()) * ratio)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * ratio)
        return QColor(r, g, b)

    @staticmethod
    def draw_frame_texture(painter: QPainter, start_x: int, end_x: int, height: int,
                           dark_color: QColor, medium_color: QColor, shade_intensity: float = 0.3):
        """Draw frame texture by drawing vertical lines with varying shades"""
        for i in range(end_x - start_x):
            shade = i / (end_x - start_x)
            color = BasePainter.interpolate_color(dark_color, medium_color, shade * shade_intensity)
            painter.setPen(color)
            painter.drawLine(start_x + i, 0, start_x + i, height)
