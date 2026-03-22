"""
Base Painter - Shared painting utilities.

Provides common painting operations used by all specific painters.
"""

import os

from PyQt6.QtGui import QPainter, QColor, QLinearGradient, QBrush
from PyQt6.QtCore import Qt, QRectF

_SRC_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_image_cache: dict = {}


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
    def draw_image_overlay(painter: QPainter, x: int, y: int, w: int, h: int,
                           theme_path: str, opacity: float, center_horizontal: bool = True):
        """Draw a raster or SVG image clipped to the given rect.

        The image is scaled to fill the full height (preserving aspect ratio) and
        optionally centered horizontally. Excess width is clipped.
        Images are cached by path across all painters.
        """
        if not theme_path or opacity <= 0:
            return
        try:
            from PyQt6.QtCore import QRect
            full_path = os.path.join(_SRC_DIR, theme_path)
            if not os.path.isfile(full_path):
                return
            if full_path not in _image_cache:
                if full_path.lower().endswith('.svg'):
                    from PyQt6.QtSvg import QSvgRenderer
                    _image_cache[full_path] = ('svg', QSvgRenderer(full_path))
                else:
                    from PyQt6.QtGui import QPixmap
                    _image_cache[full_path] = ('raster', QPixmap(full_path))
            kind, resource = _image_cache[full_path]
            painter.save()
            painter.setClipRect(QRect(x, y, w, h))
            painter.setOpacity(opacity)
            if kind == 'svg':
                resource.render(painter, QRectF(x, y, h, h))
            else:
                from PyQt6.QtCore import Qt
                scaled = resource.scaledToHeight(h, Qt.TransformationMode.SmoothTransformation)
                draw_x = x - (scaled.width() - w) // 2 if center_horizontal else x
                painter.drawPixmap(draw_x, y, scaled)
            painter.restore()
        except Exception:
            pass

    @staticmethod
    def draw_gradient_rect_stops(painter: QPainter, x1: int, y1: int, x2: int, y2: int,
                                 stops: list, vertical: bool = False):
        """Draw a rectangle with a multi-stop gradient fill.

        stops: list of (position, QColor) where position is 0.0–1.0
        """
        gradient = QLinearGradient()
        if vertical:
            gradient.setStart(0, y1)
            gradient.setFinalStop(0, y2)
        else:
            gradient.setStart(x1, 0)
            gradient.setFinalStop(x2, 0)
        for pos, color in stops:
            gradient.setColorAt(pos, color)
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
