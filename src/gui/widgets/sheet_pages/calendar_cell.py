"""
Calendar Cell - Single day cell for contribution calendar graph.
"""

from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
from datetime import date

# Import time utilities
from core.util.time import get_friendly_elapsed


from gui.themes import current_theme as _t


class CalendarCell(QFrame):
    """Single day cell in calendar contribution graph"""

    def __init__(self, cell_date: date, duration: int, sessions: int, threshold: int, parent=None):
        """
        Args:
            cell_date: Date for this cell
            duration: Practice duration in seconds
            sessions: Number of sessions
            threshold: Threshold for "good" activity (50% of max)
            parent: Parent widget
        """
        super().__init__(parent)
        self.cell_date = cell_date
        self.duration = duration
        self.sessions = sessions
        self.threshold = threshold

        self._setup_ui()

    def _setup_ui(self):
        """Setup cell UI with color and tooltip"""
        t = _t()
        self.setFixedSize(10, 10)

        color = self._get_color(t)

        self.setStyleSheet(f"""
            CalendarCell {{
                background-color: {color.name(QColor.NameFormat.HexArgb)};
                border: none;
                border-radius: 1px;
            }}
            CalendarCell:hover {{
                border: 1px solid {t.accent};
            }}
        """)

        if self.cell_date.day == 1:
            day_label = QLabel("1", self)
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_label.setStyleSheet(f"""
                background: transparent;
                color: {t.ink_primary};
                font-size: 7px;
                font-weight: bold;
            """)
            day_label.setGeometry(0, 0, 10, 10)

        self._set_tooltip()

    def _get_color(self, t=None) -> QColor:
        """Get cell color based on duration"""
        if t is None:
            t = _t()
        from PyQt6.QtGui import QColor as _QColor
        parts = t.paper_dark[4:-1].split(',')
        none_color = _QColor(int(parts[0]), int(parts[1]), int(parts[2]))
        aparts = t.accent[4:-1].split(',')
        accent = _QColor(int(aparts[0]), int(aparts[1]), int(aparts[2]))
        some_color = _QColor(accent.red(), accent.green(), accent.blue(), 100)
        if self.duration == 0:
            return none_color
        elif self.duration < self.threshold:
            return some_color
        else:
            return accent

    def _set_tooltip(self):
        """Set tooltip with date, duration, and session info"""
        date_str = self.cell_date.strftime("%b %d, %Y")

        if self.duration > 0:
            duration_str = get_friendly_elapsed(self.duration)
            session_str = f"{self.sessions} session{'s' if self.sessions != 1 else ''}"
            
            # Check if parent CalendarGraph has a habit (single habit view) or None (aggregated view)
            parent_graph = self.parent()
            if parent_graph and hasattr(parent_graph, 'habit') and parent_graph.habit is None:
                # Aggregated view - show "All habits"
                tooltip = f"{date_str}\nAll habits\n{duration_str}\n{session_str}"
            else:
                # Single habit view
                tooltip = f"{date_str}\n{duration_str}\n{session_str}"
        else:
            tooltip = f"{date_str}\nNo activity"

        self.setToolTip(tooltip)
