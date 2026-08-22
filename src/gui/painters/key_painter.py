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
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QFontMetrics, QPainterPath, QPolygonF
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF

from .base_painter import BasePainter
from ..constants import piano_colors, PianoLayout, Animations, font_pt, make_font
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

        # Keys region overlay (theme-defined image over all keys)
        try:
            from gui.themes.manager import ThemeManager
            t = ThemeManager.get_instance().current
            if t.keys_overlay:
                BasePainter.draw_image_overlay(
                    painter,
                    geometry.keys_start_x, 0,
                    geometry.keys_width, geometry.window_height,
                    t.keys_overlay, t.keys_overlay_opacity,
                )
        except Exception:
            pass

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
            key_color = piano_colors().WHITE_KEY_PRESSED
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
            painter.setBrush(QBrush(piano_colors().WHITE_KEY))
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
        painter.setPen(QPen(piano_colors().WHITE_KEY_SHADOW))
        painter.setBrush(QBrush(piano_colors().WHITE_KEY_SHADOW))
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
        painter.setPen(QPen(piano_colors().TEXT_PRIMARY))
        font = QFont()
        font.setWeight(QFont.Weight.Light)
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

        # Clip path: rounded left corners (exposed end), square right corners (embedded end)
        corner_r = 3
        key_clip = QPainterPath()
        key_clip.moveTo(x + corner_r, y)
        key_clip.lineTo(x + width, y)
        key_clip.lineTo(x + width, y + height)
        key_clip.lineTo(x + corner_r, y + height)
        key_clip.arcTo(x, y + height - corner_r * 2, corner_r * 2, corner_r * 2, 270, -90)
        key_clip.lineTo(x, y + corner_r)
        key_clip.arcTo(x, y, corner_r * 2, corner_r * 2, 180, -90)
        key_clip.closeSubpath()

        painter.save()
        painter.setClipPath(key_clip)

        # Main black key body with vertical gradient (darker at bottom)
        KeyPainter.draw_gradient_rect(
            painter,
            x,
            y,
            x + width,
            y + height,
            piano_colors().BLACK_KEY_SHINE,
            piano_colors().BLACK_KEY,
            vertical=True
        )

        # Derive edge highlight/shadow tones from the black key base color
        bk = piano_colors().BLACK_KEY
        edge_highlight = bk.lighter(200)
        edge_highlight.setAlpha(120)
        edge_shadow = bk.darker(200)
        edge_shadow.setAlpha(180)
        gloss_top = bk.lighter(180)
        gloss_top.setAlpha(130)
        gloss_fade = QColor(gloss_top.red(), gloss_top.green(), gloss_top.blue(), 0)
        # Left edge highlight (simulates light catching the edge)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(edge_highlight))
        painter.drawRect(int(x), int(y), 1, int(height))

        # Right edge shadow
        painter.setBrush(QBrush(edge_shadow))
        painter.drawRect(int(x + width - 1), int(y), 1, int(height))

        # Top glossy highlight (vertical fade)
        highlight_height = int(height * 0.25)
        KeyPainter.draw_gradient_rect(
            painter,
            x,
            y,
            x + width,
            y + highlight_height,
            gloss_top,
            gloss_fade,
            vertical=True
        )

        # Specular gloss band: bright horizontal strip in the upper-left area
        gloss_specular = bk.lighter(220)
        gloss_specular.setAlpha(60)
        gloss_specular_fade = QColor(gloss_specular.red(), gloss_specular.green(), gloss_specular.blue(), 0)
        KeyPainter.draw_gradient_rect(
            painter,
            x,
            y + 2,
            x + int(width * 0.55),
            y + int(height * 0.18),
            gloss_specular,
            gloss_specular_fade,
            vertical=False
        )

        painter.restore()


        # Time text on black key
        KeyPainter.draw_time_display(painter, geometry, black_key_rect, state, index, keys_data)

        # Time adjustment buttons on black key (only when session active)
        KeyPainter.draw_time_adjustment_buttons(painter, geometry, black_key_rect, state, index, keys_data)

        # Task completion checkmark on black key
        KeyPainter.draw_task_checkmark(painter, black_key_rect, state, index, keys_data)

        # Restore painter state if we scaled
        if reorder_manager and reorder_manager.is_reorder_mode:
            painter.restore()

    @staticmethod
    def draw_time_display(painter: QPainter, geometry: 'PianoGeometry', black_key_rect: QRect,
                          state: PianoState, index: int, keys_data: list):
        """Draw time display text on a black key"""
        # Find if there's a time display for the corresponding habit
        time_text = ""
        is_overtime = False
        if index < len(keys_data):
            habit = keys_data[index].get('habit')
            if habit:
                time_text = state.get_time_display(habit.id) or ""
                is_overtime = state.is_time_display_overtime(habit.id)

        # Use full width - buttons will overlay on hover
        text_rect = QRect(
            black_key_rect.x(),
            black_key_rect.y(),
            black_key_rect.width(),
            black_key_rect.height()
        )

        font_size = 12 if len(time_text) <= 5 else 11
        # A countdown that has passed its target (overtime) is shown in the accent
        # colour to signal the minimum time was reached.
        text_color = piano_colors().ACCENT if is_overtime else piano_colors().BLACK_KEY_TEXT
        painter.setPen(QPen(text_color))
        painter.setFont(make_font('Helvetica', font_size))
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter,
            time_text
        )

    @staticmethod
    def draw_time_adjustment_buttons(painter: QPainter, geometry: 'PianoGeometry',
                                     black_key_rect: QRect, state: PianoState,
                                     index: int, keys_data: list):
        """Draw time adjustment buttons on a black key (both visible when hovering either, overlays time)"""
        if index >= len(keys_data):
            return

        key_data = keys_data[index]
        habit = key_data.get('habit')

        # Only show buttons if there's an active session for this habit
        if not habit or not state.has_active_session(habit.id):
            return

        # Show the whole button block when hovering over any one of them.
        if state.hovered_time_button and state.hovered_time_button[0] == index:
            hovered_button_type = state.hovered_time_button[1]
            # The countdown/stopwatch toggle only exists for habits with an
            # allocated minimum time (countdown is meaningless without one).
            include_mode = habit.allocated_time is not None
            buttons = geometry.get_time_adjustment_buttons_rects(index, include_mode=include_mode)

            if include_mode:
                mode = state.get_session_time_mode(habit.id) or 'countdown'
                KeyPainter._draw_mode_button(
                    painter,
                    buttons['mode'],
                    mode,
                    is_hovered=(hovered_button_type == 'mode')
                )
            KeyPainter._draw_time_button(
                painter,
                buttons['minus'],
                '-',
                is_hovered=(hovered_button_type == 'minus')
            )
            KeyPainter._draw_time_button(
                painter,
                buttons['plus'],
                '+',
                is_hovered=(hovered_button_type == 'plus')
            )

    @staticmethod
    def _draw_time_button(painter: QPainter, rect: QRect, text: str, is_hovered: bool = False):
        """Draw a single time adjustment button with opaque background"""
        bg_color = piano_colors().ACCENT_LIGHT if is_hovered else piano_colors().ACCENT
        border_color = piano_colors().ACCENT.darker(130)

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(rect)

        painter.setPen(QPen(piano_colors().WHITE_KEY))
        painter.setFont(make_font('Helvetica', 10, QFont.Weight.Bold))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    @staticmethod
    def _draw_mode_button(painter: QPainter, rect: QRect, mode: str, is_hovered: bool = False):
        """Draw the countdown/stopwatch toggle button.

        The glyph shows the *current* mode: an hourglass for countdown, a clock
        face for stopwatch. Drawn as vector primitives (not a font glyph) so it
        renders reliably at this small size.
        """
        bg_color = piano_colors().ACCENT_LIGHT if is_hovered else piano_colors().ACCENT
        border_color = piano_colors().ACCENT.darker(130)
        ink = piano_colors().WHITE_KEY

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(QBrush(bg_color))
        painter.drawRect(rect)

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        # Inset the glyph within the 12px button.
        m = 3
        gl = rect.left() + m
        gr = rect.right() - m + 1
        gt = rect.top() + m
        gb = rect.bottom() - m + 1
        cx = (gl + gr) / 2

        if mode == 'countdown':
            # Hourglass: two triangles meeting at the centre.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(ink))
            cy = (gt + gb) / 2
            painter.drawPolygon(QPolygonF([QPointF(gl, gt), QPointF(gr, gt), QPointF(cx, cy)]))
            painter.drawPolygon(QPolygonF([QPointF(gl, gb), QPointF(gr, gb), QPointF(cx, cy)]))
        else:
            # Clock face: a circle with a short hand.
            painter.setPen(QPen(ink, 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            face = QRectF(gl, gt + 1, gr - gl, gb - gt - 1)
            painter.drawEllipse(face)
            fcx, fcy = face.center().x(), face.center().y()
            painter.drawLine(QPointF(fcx, fcy), QPointF(fcx, face.top() + 1.5))
            painter.drawLine(QPointF(fcx, fcy), QPointF(fcx + 2, fcy))
        painter.restore()

    @staticmethod
    def draw_task_checkmark(painter: QPainter, black_key_rect: QRect, state: PianoState,
                           index: int, keys_data: list):
        """Draw task completion checkmark on a black key"""
        if index >= len(keys_data):
            return

        key_data = keys_data[index]
        habit = key_data.get('habit')
        task_datetime = key_data.get('task_datetime')
        is_completed = key_data.get('is_completed', False)

        if not task_datetime:
            return

        if habit and state.has_active_session(habit.id):
            return

        # Calculate checkmark position (center of black key)
        checkmark_size = 16
        center_x = black_key_rect.x() + black_key_rect.width() / 2
        center_y = black_key_rect.y() + black_key_rect.height() / 2
        checkmark_x = center_x - checkmark_size / 2
        checkmark_y = center_y - checkmark_size / 2

        is_hovered = (state.hovered_checkmark_index == index)

        if is_hovered or is_completed:
            # Filled accent circle with checkmark
            accent = piano_colors().ACCENT
            circle_color = QColor(accent.red(), accent.green(), accent.blue(), 200 if is_hovered else 160)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(circle_color))
            painter.drawEllipse(int(checkmark_x), int(checkmark_y), checkmark_size, checkmark_size)

            painter.setPen(QPen(piano_colors().WHITE_KEY, 2))
            painter.setFont(make_font('Arial', 12, QFont.Weight.Bold))
            painter.drawText(
                QRect(int(checkmark_x), int(checkmark_y), checkmark_size, checkmark_size),
                Qt.AlignmentFlag.AlignCenter,
                "✓"
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
        painter.setPen(QPen(piano_colors().ACCENT_LIGHT, 3))
        painter.drawLine(
            geometry.keys_start_x,
            int(y_position),
            geometry.keys_start_x + geometry.keys_width,
            int(y_position)
        )

        # Draw small triangles on the sides
        painter.setBrush(QBrush(piano_colors().ACCENT_LIGHT))
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
        painter.setBrush(QBrush(piano_colors().WHITE_KEY))
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
                piano_colors().BLACK_KEY_SHINE,
                piano_colors().BLACK_KEY,
                vertical=True
            )

        # Restore opacity
        painter.setOpacity(old_opacity)
