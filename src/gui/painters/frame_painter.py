"""
Frame Painter - Draws the piano wooden frame and fallboard.

Responsible for painting:
- Left wooden panel with wood grain effect
- Fallboard (narrow indicator panel)
- Control panel (right side)

Note: The toggleable drawer content is now handled by MusicSheetWidget,
not painted here.
"""

from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt

from .base_painter import BasePainter
from ..constants import piano_colors, PianoLayout
from ..models.piano_geometry import PianoGeometry


def _current_theme():
    try:
        from gui.themes.manager import ThemeManager
        return ThemeManager.get_instance().current
    except Exception:
        return None


class FramePainter(BasePainter):
    """Handles painting of the piano frame"""

    @staticmethod
    def draw_frame(painter: QPainter, geometry: PianoGeometry):
        """
        Draw the complete piano frame

        Args:
            painter: QPainter instance
            geometry: PianoGeometry model with all coordinates
        """
        # Always draw toggleable drawer background at fixed position (visibility controlled by window mask)
        # Note: Content (MusicSheetWidget) is rendered separately as a QWidget
        toggleable_drawer_rect = geometry.toggleable_drawer_rect
        if not toggleable_drawer_rect.isEmpty():
            t = _current_theme()
            gradient = (t.frame_gradient or t.fallboard_gradient) if t else ()
            if gradient:
                FramePainter._draw_panel_gradient_stops(
                    painter, 0, 0, geometry.toggleable_drawer_width, geometry.window_height, gradient
                )
                FramePainter._draw_panel_svg(painter, 0, 0, geometry.toggleable_drawer_width, geometry.window_height)
            else:
                FramePainter.draw_frame_texture(
                    painter,
                    start_x=0,
                    end_x=geometry.toggleable_drawer_width,
                    height=geometry.window_height,
                    dark_color=piano_colors().FRAME_DARK,
                    medium_color=piano_colors().FRAME_MEDIUM,
                    shade_intensity=0.5
                )
            # MusicSheetWidget will be rendered on top by Qt's widget system

        # Draw fallboard (part of main content panel, always visible)
        FramePainter.draw_fallboard(painter, geometry)

        # Draw control panel (right side)
        FramePainter.draw_control_panel(painter, geometry)

    @staticmethod
    def _parse_gradient_stops(gradient: tuple) -> list:
        stops = []
        for pos, rgb in gradient:
            r, g, b = [int(v.strip()) for v in rgb[4:-1].split(',')]
            stops.append((pos, QColor(r, g, b)))
        return stops

    @staticmethod
    def _draw_panel_gradient_stops(painter: QPainter, x1: int, y1: int, x2: int, y2: int, gradient: tuple):
        FramePainter.draw_gradient_rect_stops(
            painter, x1, y1, x2, y2,
            FramePainter._parse_gradient_stops(gradient),
            vertical=True,
        )

    @staticmethod
    def _draw_panel_gradient(painter: QPainter, x1: int, y1: int, x2: int, y2: int):
        """Draw the fallboard/control-panel gradient, using theme stops when available."""
        t = _current_theme()
        if t and t.fallboard_gradient:
            FramePainter._draw_panel_gradient_stops(painter, x1, y1, x2, y2, t.fallboard_gradient)
        else:
            FramePainter.draw_gradient_rect(
                painter, x1, y1, x2, y2,
                piano_colors().FRAME_MEDIUM,
                piano_colors().FRAME_DARK,
                vertical=True,
            )

    @staticmethod
    def _draw_panel_svg(painter: QPainter, x: int, y: int, w: int, h: int):
        """Overlay the frame SVG if the theme specifies one."""
        t = _current_theme()
        if t and t.frame_svg:
            BasePainter.draw_image_overlay(painter, x, y, w, h, t.frame_svg, t.frame_svg_opacity)

    @staticmethod
    def draw_fallboard(painter: QPainter, geometry: PianoGeometry):
        """Draw the fallboard (narrow brown panel on left of content with « symbol)"""
        fallboard_rect = geometry.fallboard_rect
        x1 = fallboard_rect.x()
        x2 = x1 + geometry.fallboard_width

        FramePainter._draw_panel_gradient(painter, x1, fallboard_rect.y(), x2, geometry.window_height)
        FramePainter._draw_panel_svg(painter, x1, 0, geometry.fallboard_width, geometry.window_height)

        # Draw « symbol at center
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setPixelSize(16)
        painter.setFont(font)
        painter.setPen(QPen(piano_colors().ACCENT))

        x_center = x1 + (geometry.fallboard_width // 2)
        y_center = fallboard_rect.y() + (geometry.window_height // 2)

        painter.drawText(int(x_center - 8), int(y_center + 6), "«")

    @staticmethod
    def draw_control_panel(painter: QPainter, geometry: PianoGeometry):
        """Draw the control panel (right side with window controls and pedals)"""
        w = geometry.window_width - geometry.control_panel_x
        FramePainter._draw_panel_gradient(painter, geometry.control_panel_x, 0, geometry.window_width, geometry.window_height)
        FramePainter._draw_panel_svg(painter, geometry.control_panel_x, 0, w, geometry.window_height)
