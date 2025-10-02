"""
Key Painter - Draws piano keys (white and black).

Responsible for painting:
- White piano keys with 3D effects and labels
- Black keys (time display areas)
- Key press visual effects
- Time displays on black keys
"""

from typing import Optional
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt, QRect

from .base_painter import BasePainter
from ..constants import PianoColors, PianoLayout
from ..models.piano_geometry import PianoGeometry
from ..models.piano_state import PianoState


class KeyPainter(BasePainter):
    """Handles painting of piano keys"""

    @staticmethod
    def draw_keys(painter: QPainter, geometry: PianoGeometry, state: PianoState, keys_data: list):
        """
        Draw all piano keys

        Args:
            painter: QPainter instance
            geometry: PianoGeometry model
            state: PianoState model
            keys_data: List of key data dictionaries with 'label', 'habit', 'time'
        """
        # Draw white keys first
        for i, key_data in enumerate(keys_data):
            KeyPainter.draw_white_key(painter, geometry, state, i, key_data)

        # Draw black keys on top (time display areas)
        for i in range(len(keys_data) - 1):
            KeyPainter.draw_black_key(painter, geometry, state, i, keys_data)

    @staticmethod
    def draw_white_key(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                       index: int, key_data: dict):
        """Draw a single white piano key"""
        key_rect = geometry.get_key_rect(index)

        # Key gap (black line between keys)
        if index > 0:
            painter.setPen(QPen(PianoColors.KEY_GAP, 1))
            painter.drawLine(
                geometry.keys_start_x,
                int(key_rect.y()),
                geometry.keys_end_x,
                int(key_rect.y())
            )

        # Check if this key is currently pressed
        is_pressed = state.is_key_pressed(index)

        # Draw key with appropriate color based on press state
        if is_pressed:
            # Pressed state: darker color and subtle shadow
            key_color = PianoColors.WHITE_KEY_PRESSED
            painter.setPen(QPen(key_color))
            painter.setBrush(QBrush(key_color))
            # Offset key slightly when pressed
            pressed_rect = QRect(
                key_rect.x(),
                key_rect.y() + 2,
                key_rect.width(),
                key_rect.height() - 2
            )
            painter.drawRect(pressed_rect)

            # Draw subtle shadow
            shadow_color = QColor(PianoColors.WHITE_KEY_SHADOW)
            shadow_color.setAlpha(120)
            painter.setPen(QPen(shadow_color, 2))
        else:
            # Normal state
            painter.setPen(QPen(PianoColors.WHITE_KEY))
            painter.setBrush(QBrush(PianoColors.WHITE_KEY))
            painter.drawRect(key_rect)

        # Key front edge (curved edge like real piano keys)
        KeyPainter.draw_key_front_edge(painter, geometry, key_rect)

        # Label on key
        KeyPainter.draw_key_label(painter, geometry, key_rect, key_data.get('label', ''))

    @staticmethod
    def draw_key_front_edge(painter: QPainter, geometry: PianoGeometry, key_rect: QRect):
        """Draw the curved front edge of a piano key"""
        painter.setPen(QPen(PianoColors.WHITE_KEY_SHADOW))
        painter.setBrush(QBrush(PianoColors.WHITE_KEY_SHADOW))
        painter.drawChord(
            geometry.keys_start_x - 10,
            int(key_rect.y() + 2),
            18,
            int(key_rect.height() - 4),
            270 * 16,
            180 * 16
        )

    @staticmethod
    def draw_key_label(painter: QPainter, geometry: PianoGeometry, key_rect: QRect, label: str):
        """Draw the label text on a piano key"""
        painter.setPen(QPen(PianoColors.TEXT_PRIMARY))
        painter.setFont(QFont('Microsoft Sans Serif', 12))
        label_rect = QRect(
            geometry.keys_start_x + 15,
            int(key_rect.y()),
            geometry.keys_width - 25,
            int(key_rect.height())
        )
        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            label
        )

    @staticmethod
    def draw_black_key(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                       index: int, keys_data: list):
        """Draw a single black key (time display area)"""
        black_key_rect = geometry.get_black_key_rect(index)

        # Draw black key with gradient
        KeyPainter.draw_gradient_rect(
            painter,
            black_key_rect.x(),
            black_key_rect.y(),
            black_key_rect.x() + black_key_rect.width(),
            black_key_rect.y() + black_key_rect.height(),
            PianoColors.BLACK_KEY_SHINE,
            PianoColors.BLACK_KEY,
            vertical=False
        )

        # Black key front edge
        painter.setPen(QPen(QColor(105, 105, 105)))
        painter.setBrush(QBrush(QColor(105, 105, 105)))
        painter.drawRect(
            int(black_key_rect.x() - 2),
            int(black_key_rect.y()),
            2,
            int(black_key_rect.height())
        )

        # Time text on black key
        KeyPainter.draw_time_display(painter, black_key_rect, state, index, keys_data)

    @staticmethod
    def draw_time_display(painter: QPainter, black_key_rect: QRect, state: PianoState,
                          index: int, keys_data: list):
        """Draw time display text on a black key"""
        painter.setPen(QPen(PianoColors.BLACK_KEY_TEXT))
        painter.setFont(QFont('Helvetica', 12))

        # Find if there's a time display for the corresponding habit
        time_text = ""
        if index < len(keys_data):
            habit = keys_data[index].get('habit')
            if habit:
                time_text = state.get_time_display(habit.id) or ""

        painter.drawText(
            black_key_rect,
            Qt.AlignmentFlag.AlignCenter,
            time_text
        )
