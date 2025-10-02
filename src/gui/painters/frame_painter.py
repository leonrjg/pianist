"""
Frame Painter - Draws the piano wooden frame and fallboard.

Responsible for painting:
- Left wooden panel with wood grain effect
- Music sheet on drawer
- Keybed (black strip)
- Right wooden frame
"""

from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt

from .base_painter import BasePainter
from .music_sheet_painter import MusicSheetPainter
from ..constants import PianoColors, PianoLayout
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
        # Always draw drawer at fixed position (visibility controlled by window mask)
        drawer_rect = geometry.drawer_rect
        if not drawer_rect.isEmpty():
            # Draw wooden drawer background
            FramePainter.draw_wood_grain_effect(
                painter,
                start_x=0,
                end_x=geometry.drawer_width,
                height=geometry.window_height,
                dark_color=PianoColors.WOOD_DARK,
                medium_color=PianoColors.WOOD_MEDIUM,
                shade_intensity=0.3
            )

            # Draw music sheet on the drawer
            MusicSheetPainter.draw_music_sheet(painter, drawer_rect)

        # Draw keybed (black strip between frame and keys)
        FramePainter.draw_keybed(painter, geometry)

        # Draw right frame
        FramePainter.draw_right_frame(painter, geometry)

    @staticmethod
    def draw_fallboard(painter: QPainter, geometry: PianoGeometry):
        """Draw the fallboard panel"""
        fallboard_rect = geometry.fallboard_rect
        if not fallboard_rect.isEmpty():
            # Temporarily using bright red for testing visibility
            painter.setBrush(QBrush(QColor(255, 0, 0)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(fallboard_rect)

    @staticmethod
    def draw_keybed(painter: QPainter, geometry: PianoGeometry):
        """Draw the keybed (black strip between frame and keys)"""
        keybed_rect = geometry.keybed_rect
        painter.setPen(QPen(PianoColors.KEYBED))
        painter.setBrush(QBrush(PianoColors.KEYBED))
        painter.drawRect(keybed_rect)

    @staticmethod
    def draw_right_frame(painter: QPainter, geometry: PianoGeometry):
        """Draw the right wooden frame with gradient"""
        FramePainter.draw_gradient_rect(
            painter,
            geometry.right_frame_x,
            0,
            geometry.window_width,
            geometry.window_height,
            PianoColors.WOOD_MEDIUM,
            PianoColors.WOOD_DARK,
            vertical=True
        )
