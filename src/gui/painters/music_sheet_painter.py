"""
Music Sheet Painter - Draws an elegant music sheet on the drawer.

Responsible for painting:
- Paper sheet with realistic appearance
- Staff lines (5 horizontal lines for musical notation)
- Placeholder musical elements (clef, notes, etc.)
- Subtle shadows and texture
"""

from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont
from PyQt6.QtCore import Qt, QRect

from .base_painter import BasePainter
from gui.constants import font_pt, make_font


class MusicSheetPainter(BasePainter):
    """Handles painting of the music sheet on the drawer"""

    # Music sheet colors
    PAPER_COLOR = QColor(252, 250, 242)  # Slightly off-white paper
    PAPER_SHADOW = QColor(200, 195, 180, 80)  # Subtle shadow
    STAFF_LINE_COLOR = QColor(40, 40, 40)  # Dark gray for staff lines
    TEXT_COLOR = QColor(60, 60, 60)  # Dark gray for text

    @staticmethod
    def draw_music_sheet(painter: QPainter, drawer_rect: QRect):
        """
        Draw an elegant music sheet on the drawer.

        Args:
            painter: QPainter instance
            drawer_rect: Rectangle defining the drawer area
        """
        if drawer_rect.isEmpty():
            return

        # Calculate container dimensions (dark wooden holder)
        container_margin = 6
        container_x = drawer_rect.x() + container_margin
        container_y = drawer_rect.y() + container_margin + 15
        container_width = drawer_rect.width() - (container_margin * 2)
        container_height = drawer_rect.height() - (container_margin * 2) - 30

        container_rect = QRect(container_x, container_y, container_width, container_height)

        # Draw darker wooden container
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(44, 24, 16)))  # Very dark wood
        painter.drawRect(container_rect)

        # Draw inner shadow for depth
        shadow_color = QColor(20, 10, 5, 100)
        painter.setPen(QPen(shadow_color, 2))
        painter.drawRect(container_rect.adjusted(1, 1, -1, -1))

        # Calculate sheet dimensions (slightly smaller than container)
        sheet_margin = 4
        sheet_x = container_x + sheet_margin
        sheet_y = container_y + sheet_margin
        sheet_width = container_width - (sheet_margin * 2)
        sheet_height = container_height - (sheet_margin * 2)

        sheet_rect = QRect(sheet_x, sheet_y, sheet_width, sheet_height)

        # Draw paper shadow (slightly offset)
        shadow_rect = sheet_rect.adjusted(2, 2, 2, 2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(MusicSheetPainter.PAPER_SHADOW))
        painter.drawRect(shadow_rect)

        # Draw paper sheet
        painter.setPen(QPen(QColor(220, 215, 200), 1))
        painter.setBrush(QBrush(MusicSheetPainter.PAPER_COLOR))
        painter.drawRect(sheet_rect)

        # Draw staff lines (5 lines per staff, multiple staffs)
        MusicSheetPainter._draw_staff_lines(painter, sheet_rect)

        # Draw placeholder musical elements
        MusicSheetPainter._draw_musical_elements(painter, sheet_rect)

    @staticmethod
    def _draw_staff_lines(painter: QPainter, sheet_rect: QRect):
        """
        Draw staff lines on the music sheet.

        Args:
            painter: QPainter instance
            sheet_rect: Rectangle defining the sheet area
        """
        painter.setPen(QPen(MusicSheetPainter.STAFF_LINE_COLOR, 1))

        # Staff configuration
        line_spacing = 6  # Space between lines in a staff
        staff_height = line_spacing * 4  # 5 lines = 4 spaces
        staff_spacing = 35  # Space between staffs

        start_x = sheet_rect.x() + 5
        end_x = sheet_rect.x() + sheet_rect.width() - 5
        start_y = sheet_rect.y() + 15

        # Draw multiple staffs to fill the sheet
        num_staffs = min(6, (sheet_rect.height() - 30) // staff_spacing)

        for staff_index in range(num_staffs):
            staff_y = start_y + (staff_index * staff_spacing)

            # Draw 5 horizontal lines for this staff
            for line in range(5):
                y = staff_y + (line * line_spacing)
                if y + line_spacing < sheet_rect.y() + sheet_rect.height() - 10:
                    painter.drawLine(start_x, y, end_x, y)

    @staticmethod
    def _draw_musical_elements(painter: QPainter, sheet_rect: QRect):
        """
        Draw placeholder musical elements (clef, notes, etc.).

        Args:
            painter: QPainter instance
            sheet_rect: Rectangle defining the sheet area
        """
        # Use a music-like font for symbols
        font = make_font("Arial", 10)
        painter.setFont(font)
        painter.setPen(QPen(MusicSheetPainter.TEXT_COLOR))

        # Draw treble clef symbol (using a simple text representation)
        clef_x = sheet_rect.x() + 10
        clef_y = sheet_rect.y() + 30
        painter.drawText(clef_x, clef_y, "𝄞")  # Treble clef symbol

        # Draw some simple note placeholders (circles and stems)
        note_font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(note_font)

        # First staff notes
        notes_y = sheet_rect.y() + 24
        note_positions = [28, 40, 52, 64, 76, 88]

        for i, x_offset in enumerate(note_positions):
            note_x = sheet_rect.x() + x_offset
            # Alternate between different vertical positions
            y_offset = (i % 3) * 3
            painter.drawEllipse(note_x, notes_y + y_offset, 3, 2)
            # Draw stem
            if i % 2 == 0:
                painter.drawLine(note_x + 3, notes_y + y_offset, note_x + 3, notes_y + y_offset - 8)
            else:
                painter.drawLine(note_x, notes_y + y_offset + 2, note_x, notes_y + y_offset + 10)

        # Draw bass clef on second staff if there's room
        if sheet_rect.height() > 80:
            bass_clef_y = sheet_rect.y() + 65
            painter.setFont(make_font("Arial", 10))
            painter.drawText(clef_x, bass_clef_y, "𝄢")  # Bass clef symbol

            # More notes on second staff
            notes_y2 = sheet_rect.y() + 59
            for i, x_offset in enumerate(note_positions):
                note_x = sheet_rect.x() + x_offset
                y_offset = ((i + 1) % 3) * 3
                painter.drawEllipse(note_x, notes_y2 + y_offset, 3, 2)
                if i % 2 == 1:
                    painter.drawLine(note_x + 3, notes_y2 + y_offset, note_x + 3, notes_y2 + y_offset - 8)
                else:
                    painter.drawLine(note_x, notes_y2 + y_offset + 2, note_x, notes_y2 + y_offset + 10)
