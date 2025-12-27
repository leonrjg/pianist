"""
Key Painter - Draws piano keys (white and black).

Responsible for painting:
- White piano keys with 3D effects and labels
- Black keys (time display areas)
- Key press visual effects
- Time displays on black keys
- Vibration offsets during reorder mode
- Drag preview during key reordering
"""

from typing import Optional, TYPE_CHECKING
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRect

from .base_painter import BasePainter
from ..constants import PianoColors, PianoLayout, Animations
from ..models.piano_geometry import PianoGeometry
from ..models.piano_state import PianoState

if TYPE_CHECKING:
    from ..managers.reorder_mode_manager import ReorderModeManager


class KeyPainter(BasePainter):
    """Handles painting of piano keys"""

    @staticmethod
    def draw_keys(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                  keys_data: list, reorder_manager: Optional['ReorderModeManager'] = None):
        """
        Draw all piano keys

        Args:
            painter: QPainter instance
            geometry: PianoGeometry model
            state: PianoState model
            keys_data: List of key data dictionaries with 'label', 'habit', 'time'
            reorder_manager: Optional reorder mode manager for vibration effects
        """
        # Draw white keys first (except the one being dragged)
        for i, key_data in enumerate(keys_data):
            # Skip dragged key in first pass
            if state.is_dragging_key() and i == state.dragged_key_index:
                continue
            KeyPainter.draw_white_key(painter, geometry, state, i, key_data, reorder_manager)

        # Draw black keys on top (time display areas, except dragged key)
        for i in range(len(keys_data) - 1):
            if state.is_dragging_key() and i == state.dragged_key_index:
                continue
            KeyPainter.draw_black_key(painter, geometry, state, i, keys_data, reorder_manager)

        # Draw drop target indicator if dragging
        if state.is_dragging_key() and state.drop_target_index is not None:
            KeyPainter.draw_drop_indicator(painter, geometry, state)

        # Draw dragged key last (on top) with transparency
        if state.is_dragging_key() and state.dragged_key_index is not None:
            KeyPainter.draw_dragged_key(painter, geometry, state, keys_data, reorder_manager)

    @staticmethod
    def draw_white_key(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                       index: int, key_data: dict, reorder_manager: Optional['ReorderModeManager'] = None):
        """Draw a single white piano key"""
        key_rect = geometry.get_key_rect(index)

        # Apply scale transformation if in reorder mode
        if reorder_manager and reorder_manager.is_reorder_mode:
            scale = reorder_manager.get_scale(index)

            # Save painter state
            painter.save()

            # Calculate center point of key for scaling
            center_x = key_rect.x() + key_rect.width() / 2
            center_y = key_rect.y() + key_rect.height() / 2

            # Translate to center, scale, translate back
            painter.translate(center_x, center_y)
            painter.scale(scale, scale)
            painter.translate(-center_x, -center_y)

        # Check if this key is currently pressed
        is_pressed = state.is_key_pressed(index)

        # Fill the key first (no border)
        painter.setPen(Qt.PenStyle.NoPen)
        if is_pressed:
            # Pressed state: darker color
            key_color = PianoColors.WHITE_KEY_PRESSED
            painter.setBrush(QBrush(key_color))
            # Offset key slightly when pressed
            pressed_rect = QRect(
                key_rect.x(),
                key_rect.y() + 2,
                key_rect.width(),
                key_rect.height() - 2
            )
            painter.drawRect(pressed_rect)
        else:
            # Normal state - fill with white
            painter.setBrush(QBrush(PianoColors.WHITE_KEY))
            painter.drawRect(key_rect)

        # Key front edge (curved edge like real piano keys)
        KeyPainter.draw_key_front_edge(painter, geometry, key_rect)

        # Label on key
        KeyPainter.draw_key_label(painter, geometry, key_rect, key_data.get('label', ''))

        # Restore painter state if we scaled
        if reorder_manager and reorder_manager.is_reorder_mode:
            painter.restore()

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
        font = QFont('Avenir', 13)
        painter.setFont(font)

        label_rect = QRect(
            geometry.keys_start_x + 15,
            int(key_rect.y()),
            geometry.keys_width - 25,
            int(key_rect.height())
        )

        # Elide text if it doesn't fit
        metrics = QFontMetrics(font)
        elided_text = metrics.elidedText(label, Qt.TextElideMode.ElideRight, label_rect.width())

        painter.drawText(
            label_rect,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            elided_text
        )

    @staticmethod
    def draw_black_key(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                       index: int, keys_data: list, reorder_manager: Optional['ReorderModeManager'] = None):
        """Draw a single black key (time display area) with realistic 3D appearance"""
        black_key_rect = geometry.get_black_key_rect(index)

        # Apply scale transformation if in reorder mode
        if reorder_manager and reorder_manager.is_reorder_mode:
            scale = reorder_manager.get_scale(index)

            # Save painter state
            painter.save()

            # Calculate center point of black key for scaling
            center_x = black_key_rect.x() + black_key_rect.width() / 2
            center_y = black_key_rect.y() + black_key_rect.height() / 2

            # Translate to center, scale, translate back
            painter.translate(center_x, center_y)
            painter.scale(scale, scale)
            painter.translate(-center_x, -center_y)

        x = black_key_rect.x()
        y = black_key_rect.y()
        width = black_key_rect.width()
        height = black_key_rect.height()

        # Main black key body with vertical gradient (darker at bottom)
        KeyPainter.draw_gradient_rect(
            painter,
            x,
            y,
            x + width,
            y + height,
            PianoColors.BLACK_KEY_SHINE,
            PianoColors.BLACK_KEY,
            vertical=True
        )

        # Left edge highlight (simulates light catching the edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(60, 60, 60, 120)))
        painter.drawRect(int(x), int(y), 1, int(height))

        # Right edge shadow
        painter.setBrush(QBrush(QColor(10, 10, 10, 150)))
        painter.drawRect(int(x + width - 1), int(y), 1, int(height))

        # Top glossy highlight (realistic piano black keys have a shine at the top)
        highlight_height = int(height * 0.25)
        KeyPainter.draw_gradient_rect(
            painter,
            x,
            y,
            x + width,
            y + highlight_height,
            QColor(80, 80, 80, 80),
            QColor(40, 40, 40, 0),
            vertical=True
        )

        # Front edge (left side) - more prominent 3D effect
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(80, 80, 80)))
        painter.drawRect(int(x - 2), int(y), 2, int(height))

        # Front edge shadow at bottom
        painter.setBrush(QBrush(QColor(15, 15, 15)))
        painter.drawRect(int(x - 2), int(y + height - 3), 2, 3)

        # Rounded bottom edge effect
        painter.setPen(QPen(QColor(15, 15, 15), 1))
        painter.drawLine(int(x), int(y + height - 1), int(x + width), int(y + height - 1))

        # Time text on black key
        KeyPainter.draw_time_display(painter, black_key_rect, state, index, keys_data)

        # Restore painter state if we scaled
        if reorder_manager and reorder_manager.is_reorder_mode:
            painter.restore()

    @staticmethod
    def draw_time_display(painter: QPainter, black_key_rect: QRect, state: PianoState,
                          index: int, keys_data: list):
        """Draw time display text on a black key"""
        # Find if there's a time display for the corresponding habit
        time_text = ""
        if index < len(keys_data):
            habit = keys_data[index].get('habit')
            if habit:
                time_text = state.get_time_display(habit.id) or ""

        font_size = 12 if len(time_text) <= 5 else 11
        painter.setPen(QPen(PianoColors.BLACK_KEY_TEXT))
        painter.setFont(QFont('Avenir', font_size))
        painter.drawText(
            black_key_rect,
            Qt.AlignmentFlag.AlignCenter,
            time_text
        )

    @staticmethod
    def draw_drop_indicator(painter: QPainter, geometry: PianoGeometry, state: PianoState):
        """Draw an indicator line showing where the dragged key will be dropped"""
        if state.drop_target_index is None:
            return

        # Calculate Y position for drop indicator (between keys)
        key_height = PianoLayout.KEY_HEIGHT
        y_position = geometry.get_key_rect(state.drop_target_index).y()

        # Draw horizontal line indicator
        painter.setPen(QPen(PianoColors.BRASS_LIGHT, 3))
        painter.drawLine(
            geometry.keys_start_x,
            int(y_position),
            geometry.keys_start_x + geometry.keys_width,
            int(y_position)
        )

        # Draw small triangles on the sides
        painter.setBrush(QBrush(PianoColors.BRASS_LIGHT))
        painter.setPen(Qt.PenStyle.NoPen)

        # Left triangle
        from PyQt6.QtGui import QPolygon
        from PyQt6.QtCore import QPoint
        left_triangle = QPolygon([
            QPoint(geometry.keys_start_x - 6, int(y_position)),
            QPoint(geometry.keys_start_x, int(y_position - 4)),
            QPoint(geometry.keys_start_x, int(y_position + 4))
        ])
        painter.drawPolygon(left_triangle)

        # Right triangle
        right_x = geometry.keys_start_x + geometry.keys_width
        right_triangle = QPolygon([
            QPoint(right_x + 6, int(y_position)),
            QPoint(right_x, int(y_position - 4)),
            QPoint(right_x, int(y_position + 4))
        ])
        painter.drawPolygon(right_triangle)

    @staticmethod
    def draw_dragged_key(painter: QPainter, geometry: PianoGeometry, state: PianoState,
                        keys_data: list, reorder_manager: Optional['ReorderModeManager'] = None):
        """Draw the key that is currently being dragged with transparency"""
        if state.dragged_key_index is None:
            return

        # Save current opacity
        old_opacity = painter.opacity()
        painter.setOpacity(Animations.KEY_DRAG_OPACITY)

        index = state.dragged_key_index
        key_data = keys_data[index] if index < len(keys_data) else {}

        # Get original key position
        key_rect = geometry.get_key_rect(index)

        # Calculate offset based on drag position
        drag_offset_y = state.drag_current_y - key_rect.y()

        # Create dragged position
        dragged_rect = QRect(
            key_rect.x(),
            int(state.drag_current_y),
            key_rect.width(),
            key_rect.height()
        )

        # Draw white key at dragged position
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(PianoColors.WHITE_KEY))
        painter.drawRect(dragged_rect)

        # Draw key front edge
        KeyPainter.draw_key_front_edge(painter, geometry, dragged_rect)

        # Draw label
        KeyPainter.draw_key_label(painter, geometry, dragged_rect, key_data.get('label', ''))

        # Draw corresponding black key if applicable
        if index < len(keys_data) - 1:
            black_key_rect = geometry.get_black_key_rect(index)
            dragged_black_rect = QRect(
                black_key_rect.x(),
                int(state.drag_current_y + (black_key_rect.y() - key_rect.y())),
                black_key_rect.width(),
                black_key_rect.height()
            )

            # Draw black key at dragged position (simplified version)
            x = dragged_black_rect.x()
            y = dragged_black_rect.y()
            width = dragged_black_rect.width()
            height = dragged_black_rect.height()

            KeyPainter.draw_gradient_rect(
                painter,
                x, y, x + width, y + height,
                PianoColors.BLACK_KEY_SHINE,
                PianoColors.BLACK_KEY,
                vertical=True
            )

        # Restore opacity
        painter.setOpacity(old_opacity)
