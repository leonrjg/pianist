"""
Activity Card - Expandable card showing bucket with individual sessions.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable

from .session_item import SessionItem
from .productivity_progress_bar import ProductivityProgressBar

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.service import HabitService
from core.util.time import get_friendly_elapsed, get_friendly_datetime, HOUR


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


class ActivityCard(QFrame):
    """Expandable card displaying a bucket with individual sessions"""

    def __init__(self, habit, bucket, on_navigate: Optional[Callable] = None, compact: bool = False, parent=None):
        """
        Args:
            habit: Habit object
            bucket: Bucket object
            on_navigate: Optional callback to navigate to habit detail
            compact: If True, hide habit name for single-habit views
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.bucket = bucket
        self.on_navigate = on_navigate
        self.compact = compact
        self.expanded = False
        self.sessions_widget = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the card UI"""
        t = _t()
        self.setStyleSheet(f"""
            ActivityCard {{
                background-color: {t.card_bg};
                border-left: 4px solid {t.accent_dark};
                border-top: 1px solid {t.card_border};
                border-right: 1px solid {t.card_border};
                border-bottom: 1px solid {t.card_border};
                border-radius: 3px;
                padding: 4px;
                margin: 2px 0px;
            }}
            ActivityCard:hover {{
                background-color: {t.card_bg};
            }}
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
        t = _t()
        date_layout = QHBoxLayout()
        date_layout.setSpacing(4)

        date_str = get_friendly_datetime(self.bucket.start, HOUR)
        date_badge = QLabel(f"📅 {date_str}")
        date_badge.setStyleSheet(f"""
                    background-color: {t.paper_dark};
                    color: {t.ink_primary};
                    font-size: 10px;
                    padding: 2px;
                    border-radius: 3px;
                """)
        date_layout.addWidget(date_badge)

        # Duration badge with emoji
        duration_str = get_friendly_elapsed(self.bucket.net_duration)
        duration_badge = QLabel(f"⏱ {duration_str}")
        duration_badge.setStyleSheet(f"""
                            background-color: {t.button_primary_bg};
                            color: {t.button_primary_text};
                            font-size: 9px;
                            padding: 2px 0px;
                            border-radius: 3px;
                        """)
        duration_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_layout.addWidget(duration_badge)

        self.main_layout.addLayout(date_layout)

        if not self.compact:
            # Habit name badge on its own row (skip in compact mode)
            self.name_badge = QLabel(self.habit.name)
            self.name_badge.setStyleSheet(f"""
                background-color: {t.paper_dark};
                color: {t.ink_primary};
                font-size: 10px;
                font-weight: bold;
                padding: 2px;
                border-radius: 3px;
            """)
            self.name_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.name_badge.setToolTip(self.habit.name)  # Show full name on hover
            self.name_badge.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.main_layout.addWidget(self.name_badge)
        else:
            self.name_badge = None

        # Productivity rate progress bar (only show if duration >= 1 minute)
        total_time = (self.bucket.end - self.bucket.start).total_seconds()
        if total_time >= 60:
            productivity_rate = self.bucket.net_duration / total_time
            progress_bar = ProductivityProgressBar(productivity_rate, parent=self)
            self.main_layout.addWidget(progress_bar)

        self.expand_stripe = QLabel(f"📶 {self.bucket.sessions} sessions")
        self.expand_stripe.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.expand_stripe.setStyleSheet(f"""
            background-color: {t.paper_dark};
            color: {t.ink_secondary};
            font-size: 9px;
            padding: 1px;
            border-radius: 2px;
            margin-top: 1px;
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
        sessions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sessions_layout.setContentsMargins(0, 0, 0, 0)
        sessions_layout.setSpacing(2)
        sessions_layout.addStretch()
        self.sessions_widget.setLayout(sessions_layout)

        # Query individual sessions (Logs) for this bucket
        logs = HabitService.get_logs_for_bucket(self.habit, self.bucket)

        if logs:
            for log in logs:
                session_item = SessionItem(log, on_delete=self._delete_log, parent=self)
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
        """Handle click on stripe to toggle expansion, or name badge to navigate"""
        # Navigate if clicking on name badge
        if self.name_badge and self.name_badge.geometry().contains(event.pos()):
            if self.on_navigate:
                self.on_navigate(self.habit)
            return
        # Toggle expansion if clicking on the stripe
        if self.expand_stripe and self.expand_stripe.geometry().contains(event.pos()):
            self.toggle_expand()

    def _delete_log(self, log):
        """Delete a log entry and refresh the card"""
        HabitService.delete_log(log)
        self._refresh_sessions()

    def _refresh_sessions(self):
        """Refresh the sessions widget after a deletion"""
        if not self.sessions_widget:
            return

        # Clear existing sessions
        sessions_layout = self.sessions_widget.layout()
        while sessions_layout.count():
            item = sessions_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Re-query logs for this bucket
        logs = HabitService.get_logs_for_bucket(self.habit, self.bucket)

        if logs:
            for log in logs:
                session_item = SessionItem(log, on_delete=self._delete_log, parent=self)
                sessions_layout.addWidget(session_item)
        else:
            no_sessions_label = QLabel("No session details available")
            no_sessions_label.setStyleSheet("color: rgb(140, 120, 100); font-size: 9px; font-style: italic; background: transparent;")
            sessions_layout.addWidget(no_sessions_label)
