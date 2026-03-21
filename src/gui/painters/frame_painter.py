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
            # Draw wooden toggleable drawer background
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
    def draw_fallboard(painter: QPainter, geometry: PianoGeometry):
        """Draw the fallboard (narrow brown panel on left of content with « symbol)"""
        fallboard_rect = geometry.fallboard_rect

        # Draw gradient background
        FramePainter.draw_gradient_rect(
            painter,
            fallboard_rect.x(),
            fallboard_rect.y(),
            fallboard_rect.x() + geometry.fallboard_width,
            geometry.window_height,
            piano_colors().FRAME_MEDIUM,
            piano_colors().FRAME_DARK,
            vertical=True
        )

        # Draw « symbol at center
        from PyQt6.QtGui import QFont
        font = QFont()
        font.setPixelSize(16)
        painter.setFont(font)
        painter.setPen(QPen(piano_colors().ACCENT))

        x_center = fallboard_rect.x() + (geometry.fallboard_width // 2)
        y_center = fallboard_rect.y() + (geometry.window_height // 2)

        painter.drawText(int(x_center - 8), int(y_center + 6), "«")

    @staticmethod
    def draw_control_panel(painter: QPainter, geometry: PianoGeometry):
        """Draw the control panel (right side with window controls and pedals)"""
        FramePainter.draw_gradient_rect(
            painter,
            geometry.control_panel_x,
            0,
            geometry.window_width,
            geometry.window_height,
            piano_colors().FRAME_MEDIUM,
            piano_colors().FRAME_DARK,
            vertical=True
        )
