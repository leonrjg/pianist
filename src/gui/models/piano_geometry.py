"""
Piano Geometry Model - Calculates all coordinates and dimensions based on current state.

This model separates layout calculations from rendering logic, making it easy to:
- Adjust layouts without touching rendering code
- Test coordinate calculations independently
- Support different window sizes and states
"""

from PyQt6.QtCore import QRect, QPoint
from ..constants import PianoLayout


class PianoGeometry:
    """Calculates all geometric properties for the piano interface"""

    def __init__(self, window_width: int, window_height: int, fallboard_visible: bool = False):
        self.window_width = window_width
        self.window_height = window_height
        self.fallboard_visible = fallboard_visible

    def update(self, window_width: int = None, window_height: int = None, fallboard_visible: bool = None):
        """Update geometry parameters"""
        if window_width is not None:
            self.window_width = window_width
        if window_height is not None:
            self.window_height = window_height
        if fallboard_visible is not None:
            self.fallboard_visible = fallboard_visible

    # ===== Frame Geometry =====

    @property
    def drawer_width(self) -> int:
        """Width of the drawer (left wooden panel)"""
        return PianoLayout.HINGE_OFFSET

    @property
    def drawer_rect(self) -> QRect:
        """
        Rectangle for the drawer (left wooden panel).

        The drawer is always painted at the same position. Visibility is controlled
        by the window mask animation in the main window, not by conditional rendering.
        """
        return QRect(0, 0, self.drawer_width, self.window_height)

    @property
    def hinge_x(self) -> int:
        """X position of drawer opener (brass hinges) - always at drawer edge"""
        return self.drawer_width

    @property
    def keybed_rect(self) -> QRect:
        """Rectangle for the keybed (black strip after drawer)"""
        # Keybed always after drawer
        return QRect(self.drawer_width, 0, PianoLayout.KEYBED_WIDTH, self.window_height)

    # ===== Keys Geometry =====

    @property
    def keys_start_x(self) -> int:
        """X position where piano keys start - always after drawer + keybed"""
        return self.drawer_width + PianoLayout.KEYBED_WIDTH

    @property
    def keys_end_x(self) -> int:
        """X position where piano keys end"""
        return self.window_width - PianoLayout.RIGHT_FRAME_WIDTH

    @property
    def keys_width(self) -> int:
        """Total width of the key area"""
        return self.keys_end_x - self.keys_start_x

    @property
    def black_key_width(self) -> int:
        """Width of black keys (time display area)"""
        return int(self.keys_width * PianoLayout.BLACK_KEY_WIDTH_RATIO)

    @property
    def black_key_height(self) -> int:
        """Height of black keys"""
        return int(PianoLayout.KEY_HEIGHT * PianoLayout.BLACK_KEY_HEIGHT_RATIO)

    def get_key_rect(self, key_index: int) -> QRect:
        """Get rectangle for a white key at given index"""
        y = 5 + (key_index * PianoLayout.KEY_HEIGHT)
        return QRect(
            self.keys_start_x,
            int(y + 1),
            self.keys_width,
            int(PianoLayout.KEY_HEIGHT - 1)
        )

    def get_black_key_rect(self, key_index: int) -> QRect:
        """Get rectangle for a black key (between white keys)"""
        y = 5 + ((key_index + 1) * PianoLayout.KEY_HEIGHT) - (self.black_key_height / 2)
        x = self.keys_end_x - self.black_key_width
        return QRect(
            int(x),
            int(y),
            self.black_key_width,
            int(self.black_key_height)
        )

    @property
    def time_display_area(self) -> QRect:
        """Cached area for time displays (black keys region)"""
        return QRect(
            self.keys_end_x - self.black_key_width,
            10,
            self.black_key_width,
            self.window_height - 20
        )

    # ===== Brass Elements Geometry =====

    def get_hinge_positions(self) -> list[tuple[int, int, int, int]]:
        """Get positions for brass hinges as (x, y, width, height) tuples"""
        return [
            (self.hinge_x + 5, PianoLayout.BRASS_HINGE_TOP_Y - 4,
             PianoLayout.BRASS_HINGE_SIZE, PianoLayout.BRASS_HINGE_SIZE),
            (self.hinge_x + 5, self.window_height - PianoLayout.BRASS_HINGE_BOTTOM_OFFSET - 4,
             PianoLayout.BRASS_HINGE_SIZE, PianoLayout.BRASS_HINGE_SIZE)
        ]

    def get_hinge_click_areas(self) -> list[QRect]:
        """Get clickable areas for brass hinges"""
        from ..constants import Interactions
        tolerance = Interactions.HINGE_CLICK_TOLERANCE
        return [
            QRect(self.hinge_x, PianoLayout.BRASS_HINGE_TOP_Y - tolerance, 18, 16),
            QRect(self.hinge_x, self.window_height - PianoLayout.BRASS_HINGE_BOTTOM_OFFSET - tolerance, 18, 16)
        ]

    def get_pedal_positions(self) -> list[tuple[int, int, int, int]]:
        """Get positions for decorative pedals as (x, y, width, height) tuples"""
        pedal_x = self.window_width - PianoLayout.PEDAL_X_OFFSET
        pedal_origin_y = self.window_height // 2 + 10
        positions = [
            pedal_origin_y - PianoLayout.PEDAL_SPACING,
            pedal_origin_y,
            pedal_origin_y + PianoLayout.PEDAL_SPACING
        ]
        return [
            (pedal_x - 5, y - 5, PianoLayout.PEDAL_SIZE, PianoLayout.PEDAL_SIZE)
            for y in positions
        ]

    def get_pedal_rod_positions(self) -> list[tuple[QPoint, QPoint]]:
        """Get line positions for pedal rods as (start, end) point tuples"""
        pedal_x = self.window_width - PianoLayout.PEDAL_X_OFFSET
        pedal_origin_y = self.window_height // 2 + 10
        positions = [
            pedal_origin_y - PianoLayout.PEDAL_SPACING,
            pedal_origin_y,
            pedal_origin_y + PianoLayout.PEDAL_SPACING
        ]
        return [
            (QPoint(pedal_x - 5, y), QPoint(pedal_x - 13, y))
            for y in positions
        ]

    # ===== Window Controls Geometry =====

    @property
    def close_button_center(self) -> QPoint:
        """Center point of close button"""
        x = self.window_width - PianoLayout.CONTROL_X_OFFSET + 20
        return QPoint(x, PianoLayout.CONTROL_BUTTON_CLOSE_Y)

    @property
    def minimize_button_center(self) -> QPoint:
        """Center point of minimize button"""
        x = self.window_width - PianoLayout.CONTROL_X_OFFSET + 20
        return QPoint(x, PianoLayout.CONTROL_BUTTON_MINIMIZE_Y)

    def get_close_button_rect(self) -> QRect:
        """Rectangle for close button"""
        center = self.close_button_center
        half_size = PianoLayout.CONTROL_BUTTON_SIZE // 2
        return QRect(center.x() - half_size, center.y() - half_size,
                    PianoLayout.CONTROL_BUTTON_SIZE, PianoLayout.CONTROL_BUTTON_SIZE)

    def get_minimize_button_rect(self) -> QRect:
        """Rectangle for minimize button"""
        center = self.minimize_button_center
        half_size = PianoLayout.CONTROL_BUTTON_SIZE // 2
        return QRect(center.x() - half_size, center.y() - half_size,
                    PianoLayout.CONTROL_BUTTON_SIZE, PianoLayout.CONTROL_BUTTON_SIZE)

    # ===== Right Frame Geometry =====

    @property
    def right_frame_x(self) -> int:
        """X position of right frame"""
        return self.window_width - PianoLayout.RIGHT_FRAME_WIDTH

    @property
    def right_frame_rect(self) -> QRect:
        """Rectangle for right frame"""
        return QRect(self.right_frame_x, 0, PianoLayout.RIGHT_FRAME_WIDTH, self.window_height)

    # ===== Scroll Indicators Geometry =====

    @property
    def scroll_indicator_x(self) -> int:
        """X position of scroll indicator - centered in scroll strip"""
        strip_rect = self.scroll_strip_rect
        return strip_rect.x() + (strip_rect.width() // 2) - 2

    @property
    def scroll_track_rect(self) -> QRect:
        """Rectangle for scroll track"""
        y = PianoLayout.SCROLL_TRACK_PADDING
        height = self.window_height - (PianoLayout.SCROLL_TRACK_PADDING * 2) - 20
        return QRect(
            self.scroll_indicator_x,
            y,
            PianoLayout.SCROLL_TRACK_WIDTH,
            height
        )

    def get_scroll_thumb_rect(self, scroll_offset: int, max_scroll_offset: int) -> QRect:
        """Get rectangle for scroll thumb based on current scroll position"""
        track = self.scroll_track_rect
        if max_scroll_offset > 0:
            thumb_height = max(PianoLayout.SCROLL_THUMB_MIN_HEIGHT, track.height() // 4)
            scroll_ratio = scroll_offset / max_scroll_offset
            thumb_y = track.y() + scroll_ratio * (track.height() - thumb_height)
            return QRect(
                track.x() - 1,
                int(thumb_y),
                track.width() + 2,
                int(thumb_height)
            )
        return QRect()

    def get_scroll_arrow_positions(self, scroll_offset: int, max_scroll_offset: int) -> dict:
        """Get positions for scroll arrows"""
        track = self.scroll_track_rect

        up_arrow_y = track.y() - 10
        down_arrow_y = track.y() + track.height() + 6

        return {
            'up': {
                'y': up_arrow_y,
                'x': self.scroll_indicator_x,
                'can_scroll': scroll_offset > 0
            },
            'down': {
                'y': down_arrow_y,
                'x': self.scroll_indicator_x,
                'can_scroll': scroll_offset < max_scroll_offset
            }
        }

    # ===== Hit Testing =====

    def is_point_in_keys(self, pos: QPoint) -> bool:
        """Check if point is within the keys area"""
        return self.keys_start_x <= pos.x() <= self.keys_end_x

    def get_key_index_at_point(self, pos: QPoint) -> int:
        """Get key index at given point, or -1 if no key"""
        if not self.is_point_in_keys(pos):
            return -1

        y_relative = pos.y() - 10
        if y_relative < 0:
            return -1

        return int(y_relative // PianoLayout.KEY_HEIGHT)

    def is_point_in_control_button(self, pos: QPoint) -> bool:
        """Check if point is in a control button"""
        from ..constants import Interactions
        close_center = self.close_button_center
        min_center = self.minimize_button_center
        radius = Interactions.CONTROL_BUTTON_CLICK_RADIUS

        return ((pos - close_center).manhattanLength() < radius or
                (pos - min_center).manhattanLength() < radius)

    def is_point_in_hinge(self, pos: QPoint) -> bool:
        """Check if point is in a brass hinge clickable area"""
        for area in self.get_hinge_click_areas():
            if area.contains(pos):
                return True
        return False

    def is_point_in_brass_section(self, pos: QPoint) -> bool:
        """Check if point is in the brass pedals section"""
        pedal_x = self.window_width - PianoLayout.PEDAL_X_OFFSET
        brass_area = QRect(pedal_x - 20, self.window_height // 2 - 60, 40, 120)
        return brass_area.contains(pos)

    def is_point_in_piano_frame(self, pos: QPoint) -> bool:
        """Check if point is on piano frame (not keybed area)"""
        # Point is on frame if it's NOT in the keys area
        if pos.x() < self.keys_start_x or pos.x() > self.keys_end_x:
            return True
        # Also consider brass section as part of frame
        if self.is_point_in_brass_section(pos):
            return True
        return False
