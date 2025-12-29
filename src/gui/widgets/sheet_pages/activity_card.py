"""
Activity Card - Expandable card showing bucket with individual sessions.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable

from .session_item import SessionItem

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.log import Log
from core.util.time import get_friendly_elapsed, get_friendly_datetime


class ActivityCard(QFrame):
    """Expandable card displaying a bucket with individual sessions"""

    def __init__(self, habit, bucket, on_navigate: Optional[Callable] = None, parent=None):
        """
        Args:
            habit: Habit object
            bucket: Bucket object
            on_navigate: Optional callback to navigate to habit detail
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.bucket = bucket
        self.on_navigate = on_navigate
        self.expanded = False
        self.sessions_widget = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the card UI"""
        # Card styling
        self.setStyleSheet("""
            ActivityCard {
                background-color: rgba(255, 252, 245, 180);
                border-left: 4px solid rgb(140, 110, 80);
                border-top: 1px solid rgb(200, 185, 160);
                border-right: 1px solid rgb(200, 185, 160);
                border-bottom: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                padding: 6px;
                margin: 2px 0px;
            }
            ActivityCard:hover {
                background-color: rgba(255, 255, 250, 200);
            }
        """)


        # Main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(4)
        self.setLayout(self.main_layout)

        # Summary section (always visible)
        self._build_summary_section()

    def _build_summary_section(self):
        """Build the collapsed summary view"""
        # Habit name
        name_label = QLabel(self.habit.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
        self.main_layout.addWidget(name_label)

        # Badges row below name
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(4)

        # Date badge with emoji
        scale = self.habit.get_schedule().get_scale()
        date_str = get_friendly_datetime(self.bucket.start, scale)

        date_badge = QLabel(f"📅 {date_str}")
        date_badge.setStyleSheet("""
            background-color: rgba(200, 185, 160, 120);
            color: rgb(70, 50, 35);
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        badges_layout.addWidget(date_badge)

        # Duration badge with emoji
        duration_str = get_friendly_elapsed(self.bucket.net_duration)
        duration_badge = QLabel(f"⏱ {duration_str}")
        duration_badge.setStyleSheet("""
            background-color: rgba(184, 134, 11, 120);
            color: rgb(40, 20, 10);
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        badges_layout.addWidget(duration_badge)

        # Session count badge
        session_count_badge = QLabel(f"{self.bucket.sessions} session{'s' if self.bucket.sessions != 1 else ''}")
        session_count_badge.setStyleSheet("""
            background-color: rgba(220, 210, 195, 100);
            color: rgb(90, 70, 55);
            font-size: 9px;
            font-style: italic;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        badges_layout.addWidget(session_count_badge)

        badges_layout.addStretch()
        self.main_layout.addLayout(badges_layout)

        # Expansion stripe with three dots
        self.expand_stripe = QLabel("···")
        self.expand_stripe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.expand_stripe.setStyleSheet("""
            background-color: rgba(200, 185, 160, 80);
            color: rgb(100, 80, 65);
            font-size: 12px;
            padding: 2px;
            border-radius: 2px;
            margin-top: 2px;
        """)
        self.expand_stripe.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.main_layout.addWidget(self.expand_stripe)

    def _build_sessions_section(self):
        """Build the expanded sessions view"""
        if self.sessions_widget:
            return  # Already built

        # Container for sessions
        self.sessions_widget = QWidget()
        self.sessions_widget.setStyleSheet("background: transparent;")
        sessions_layout = QVBoxLayout()
        sessions_layout.setContentsMargins(20, 4, 0, 0)  # Indent from left
        sessions_layout.setSpacing(2)
        self.sessions_widget.setLayout(sessions_layout)

        # Query individual sessions (Logs) for this bucket
        logs = Log.select().where(
            (Log.habit == self.habit) &
            (Log.start >= self.bucket.start) &
            (Log.start < self.bucket.end)
        ).order_by(Log.start)

        if logs:
            for log in logs:
                session_item = SessionItem(log, parent=self)
                sessions_layout.addWidget(session_item)
        else:
            no_sessions_label = QLabel("No session details available")
            no_sessions_label.setStyleSheet("color: rgb(140, 120, 100); font-size: 9px; font-style: italic; background: transparent;")
            sessions_layout.addWidget(no_sessions_label)

        self.main_layout.addWidget(self.sessions_widget)
        self.sessions_widget.hide()

    def toggle_expand(self):
        """Toggle expanded/collapsed state"""
        if not self.sessions_widget:
            self._build_sessions_section()

        self.expanded = not self.expanded

        if self.expanded:
            self.sessions_widget.show()
        else:
            self.sessions_widget.hide()

    def mousePressEvent(self, event):
        """Handle click on stripe to toggle expansion"""
        # Only toggle if clicking on the stripe
        if self.expand_stripe.geometry().contains(event.pos()):
            self.toggle_expand()
