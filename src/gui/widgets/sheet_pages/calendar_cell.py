"""
Calendar Cell - Single day cell for contribution calendar graph.
"""

from PyQt6.QtWidgets import QFrame, QLabel
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
from datetime import date

# Import time utilities
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.util.time import get_friendly_elapsed


class CalendarCell(QFrame):
    """Single day cell in calendar contribution graph"""

    # Color constants
    COLOR_NONE = QColor(230, 225, 210)  # Light aged paper - no activity
    COLOR_SOME = QColor(184, 134, 11, 100)  # Semi-transparent brass - some activity
    COLOR_GOOD = QColor(184, 134, 11)  # Solid brass - good activity

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
        # Fixed size
        self.setFixedSize(10, 10)

        # Determine color based on duration and threshold
        color = self._get_color()

        # Apply styling
        self.setStyleSheet(f"""
            CalendarCell {{
                background-color: {color.name(QColor.NameFormat.HexArgb)};
                border: none;
                border-radius: 1px;
            }}
            CalendarCell:hover {{
                border: 1px solid rgb(184, 134, 11);
            }}
        """)

        # Add day number label if this is the first day of the month
        if self.cell_date.day == 1:
            day_label = QLabel("1", self)
            day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_label.setStyleSheet("""
                background: transparent;
                color: rgb(70, 50, 35);
                font-size: 7px;
                font-weight: bold;
            """)
            day_label.setGeometry(0, 0, 10, 10)

        # Set tooltip
        self._set_tooltip()

    def _get_color(self) -> QColor:
        """Get cell color based on duration"""
        if self.duration == 0:
            return self.COLOR_NONE
        elif self.duration < self.threshold:
            return self.COLOR_SOME
        else:
            return self.COLOR_GOOD

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
