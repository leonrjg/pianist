"""
Stats Page - The practice ledger.

Statistics are engraved like a printed score report rather than a dashboard of
icon cards: a typographic figures masthead at the top, an understated "Leading"
callout for the standout habit, a per-habit ledger with hairline consistency
bars, the activity graph, and a ruled "recent practice" list. No emoji, no
gradient hero, no chunky cards — the same engraved language as the reminders
programme.
"""

from datetime import datetime

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QLabel, QWidget, QFrame, QProgressBar, QSizePolicy
)
from PyQt6.QtGui import QCursor
from PyQt6.QtCore import Qt

from .base_page import SheetPage
from .calendar_graph import CalendarGraph
from ..themed_dropdown import ThemedDropdown

from core.habit.habit import Habit
from core.habit.bucket import Bucket
from core.util.time import get_timespan

from gui.constants import make_font
from gui.themes import current_theme as _t


class StatsPage(SheetPage):
    """Statistics page showing habit analytics as an engraved practice ledger."""

    _RANGES = ["1 month", "3 months", "6 months", "1 year"]
    _RANGE_DAYS = {"1 month": 30, "3 months": 90, "6 months": 180, "1 year": 365}

    def __init__(self, service=None, parent=None):
        self.service = service
        self._calendar_graph = None
        self._calendar_container = None
        self._all_habits = []
        self._current_range = "1 month"
        super().__init__(parent)

    def get_page_title(self) -> str:
        return "Statistics"

    def get_page_type(self) -> str:
        return "stats"

    # ------------------------------------------------------------------
    # Page assembly
    # ------------------------------------------------------------------

    def build_content(self):
        layout = self.layout()
        layout.addWidget(self._create_section_header("Statistics"))

        try:
            habits = self.service.get_all_non_deleted(archived=False)
            self._all_habits = habits

            if not habits:
                layout.addWidget(self._create_text_label("No habits yet.", secondary=True))
                layout.addStretch()
                return

            stats = self._gather_stats(habits)

            layout.addSpacing(4)
            layout.addWidget(self._build_figures(stats))

            leading = self._build_leading(stats)
            if leading is not None:
                layout.addSpacing(8)
                layout.addWidget(leading)

            layout.addSpacing(10)
            layout.addWidget(self._group_header("By habit"))
            for entry in stats['per_habit']:
                layout.addWidget(self._build_habit_row(entry))
                layout.addSpacing(2)

            layout.addSpacing(14)
            layout.addLayout(self._build_activity_header())
            self._calendar_container = QWidget()
            self._calendar_container.setStyleSheet("background: transparent;")
            container_layout = QVBoxLayout()
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(0)
            self._calendar_container.setLayout(container_layout)
            layout.addWidget(self._calendar_container)
            self._build_calendar(self._RANGE_DAYS.get(self._current_range, 30))

            layout.addSpacing(14)
            layout.addWidget(self._group_header("Recent practice"))
            self._build_recent(layout, habits)

        except Exception as e:
            layout.addWidget(self._create_text_label(f"Error loading statistics: {e}", secondary=True))

        layout.addStretch()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _gather_stats(self, habits) -> dict:
        """Compute global and per-habit figures in a single pass."""
        per_habit = []
        total_time = 0
        total_sessions = 0
        champion = None

        for habit in habits:
            schedule = habit.get_schedule()
            scheduled = len(schedule.get_previous_tasks(get_timespan(schedule.start)))
            buckets = habit.get_activity_buckets()
            completed = len(buckets)
            rate = Habit.completion_rate(completed, scheduled)
            time_seconds = Bucket.total_net_duration(buckets) if buckets else 0
            streak = habit.get_longest_streak()

            entry = {
                'habit': habit,
                'rate': rate,
                'time': time_seconds,
                'sessions': completed,
                'streak': streak,
            }
            per_habit.append(entry)

            total_time += time_seconds
            total_sessions += completed
            if champion is None or streak > champion['streak']:
                champion = entry

        per_habit.sort(key=lambda e: (e['rate'], e['streak']), reverse=True)

        return {
            'per_habit': per_habit,
            'total_time': total_time,
            'total_sessions': total_sessions,
            'habit_count': len(habits),
            'best_streak': champion['streak'] if champion else 0,
            'champion': champion,
        }

    # ------------------------------------------------------------------
    # Figures masthead
    # ------------------------------------------------------------------

    def _build_figures(self, stats) -> QFrame:
        """A ruled, typographic box of the four headline numbers."""
        t = _t()
        box = QFrame()
        box.setObjectName("FiguresBox")
        box.setStyleSheet(f"""
            QFrame#FiguresBox {{
                background: transparent;
                border-top: 1px solid {t.separator};
                border-bottom: 1px solid {t.separator};
            }}
        """)
        row = QHBoxLayout(box)
        row.setContentsMargins(2, 8, 2, 8)
        row.setSpacing(0)

        figures = [
            (self._format_hours(stats['total_time']), "practice"),
            (str(stats['total_sessions']), "sessions"),
            (str(stats['habit_count']), "habits"),
            (str(stats['best_streak']), "best streak"),
        ]
        for i, (value, caption) in enumerate(figures):
            if i > 0:
                row.addWidget(self._vrule())
            row.addWidget(self._figure_column(value, caption), 1)
        return box

    def _figure_column(self, value: str, caption: str) -> QWidget:
        t = _t()
        col = QWidget()
        col.setStyleSheet("background: transparent;")
        box = QVBoxLayout(col)
        box.setContentsMargins(2, 0, 2, 0)
        box.setSpacing(1)

        value_lbl = QLabel(value)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = make_font(t.header_font, 15)
        value_font.setBold(True)
        value_lbl.setFont(value_font)
        value_lbl.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        box.addWidget(value_lbl)

        caption_lbl = QLabel(caption)
        caption_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        caption_lbl.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 9px;")
        box.addWidget(caption_lbl)
        return col

    def _vrule(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"background-color: {_t().separator}; max-width: 1px; border: none;")
        return line

    # ------------------------------------------------------------------
    # Leading callout (replaces the champion hero banner)
    # ------------------------------------------------------------------

    def _build_leading(self, stats):
        champion = stats['champion']
        if champion is None or champion['streak'] <= 0:
            return None

        t = _t()
        habit = champion['habit']
        frame = QFrame()
        frame.setObjectName("statsLeading")
        frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        frame.setStyleSheet(f"""
            QFrame#statsLeading {{
                background-color: {t.card_bg};
                border: 1px solid {t.card_border};
                border-left: 3px solid {t.accent};
                border-radius: 5px;
            }}
            QFrame#statsLeading:hover {{ border-color: {t.card_hover_border}; border-left-color: {t.accent}; }}
        """)
        frame.mousePressEvent = lambda e, h=habit: self._navigate_to_habit(h)

        outer = QHBoxLayout(frame)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        body_box = QVBoxLayout()
        body_box.setContentsMargins(0, 0, 0, 0)
        body_box.setSpacing(2)

        name = QLabel(habit.name)
        name_font = make_font(t.header_font, 12)
        name_font.setBold(True)
        name.setFont(name_font)
        name.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        body_box.addWidget(name)

        detail = QLabel(
            f"{champion['streak']}-period streak · {int(champion['rate'] * 100)}% consistency"
        )
        detail.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 10px;")
        body_box.addWidget(detail)
        outer.addLayout(body_box, 1)

        tag = QLabel("LEADING")
        tag.setStyleSheet(
            f"color: {t.accent_dark}; background: transparent; font-size: 8px; font-weight: bold;"
        )
        tag.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addWidget(tag)

        return frame

    # ------------------------------------------------------------------
    # Per-habit ledger
    # ------------------------------------------------------------------

    def _build_habit_row(self, entry) -> QFrame:
        t = _t()
        habit = entry['habit']
        accent = t.accent if entry['rate'] >= 0.6 else t.accent_dark if entry['rate'] >= 0.3 else t.border
        row = QFrame()
        row.setObjectName("statsHabitRow")
        row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        row.setStyleSheet(f"""
            QFrame#statsHabitRow {{
                background-color: {t.card_bg};
                border: 1px solid {t.card_border};
                border-left: 3px solid {accent};
                border-radius: 5px;
            }}
            QFrame#statsHabitRow:hover {{ border-color: {t.card_hover_border}; border-left-color: {accent}; }}
        """)
        row.mousePressEvent = lambda e, h=habit: self._navigate_to_habit(h)

        outer = QHBoxLayout(row)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        # Left: name + condensed meta (schedule, sessions, streak, time)
        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(3)

        name = QLabel(habit.name)
        name.setWordWrap(True)
        name_font = make_font(t.header_font, 11)
        name_font.setBold(True)
        name.setFont(name_font)
        name.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        left_box.addWidget(name)

        sub = QLabel(
            f"{habit.schedule} · {entry['sessions']} sessions"
            + (f" · {entry['streak']}× streak" if entry['streak'] > 0 else "")
            + (f" · {self._format_hours(entry['time'])}" if entry['time'] > 0 else "")
        )
        sub.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 9px;")
        left_box.addWidget(sub)
        outer.addLayout(left_box, 1)

        # Right: consistency percentage + hairline bar
        right_box = QVBoxLayout()
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(4)

        pct = QLabel(f"{int(entry['rate'] * 100)}%")
        pct.setAlignment(Qt.AlignmentFlag.AlignRight)
        pct_font = make_font(t.header_font, 13)
        pct_font.setBold(True)
        pct.setFont(pct_font)
        pct.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        right_box.addWidget(pct)

        bar = self._consistency_bar(entry['rate'])
        bar.setFixedWidth(68)
        right_box.addWidget(bar)
        outer.addLayout(right_box)

        return row

    def _consistency_bar(self, rate: float) -> QProgressBar:
        t = _t()
        rate = max(0.0, min(1.0, rate))
        bar = QProgressBar()
        bar.setMinimum(0)
        bar.setMaximum(100)
        bar.setValue(int(rate * 100))
        bar.setTextVisible(False)
        bar.setFixedHeight(4)
        chunk = t.accent if rate >= 0.6 else t.accent_dark if rate >= 0.3 else t.border
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t.paper_dark};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {chunk};
                border-radius: 2px;
            }}
        """)
        return bar

    # ------------------------------------------------------------------
    # Activity graph (preserved) with adjacent range control
    # ------------------------------------------------------------------

    def _build_activity_header(self) -> QHBoxLayout:
        t = _t()
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        row.addWidget(self._group_header("Activity"))
        row.addStretch()

        show = QLabel("show")
        show.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 10px;")
        row.addWidget(show)

        dropdown = ThemedDropdown(self._RANGES, self._current_range)
        dropdown.selection_changed.connect(self._on_range_changed)
        row.addWidget(dropdown)
        return row

    def _build_calendar(self, days_back: int = 30):
        """Rebuild the activity graph from all habits within the selected range."""
        from datetime import timedelta

        container_layout = self._calendar_container.layout()
        if self._calendar_graph:
            container_layout.removeWidget(self._calendar_graph)
            self._calendar_graph.deleteLater()
            self._calendar_graph = None

        cutoff_date = datetime.now() - timedelta(days=days_back)
        all_buckets = []
        for habit in self._all_habits:
            buckets = habit.get_activity_buckets(since=cutoff_date)
            if buckets:
                all_buckets.extend(buckets)

        if not all_buckets:
            no_data = self._create_text_label("Start practicing to fill the calendar.", secondary=True)
            container_layout.addWidget(no_data)
            return

        self._calendar_graph = CalendarGraph(None, all_buckets, days_back, parent=self)
        container_layout.addWidget(self._calendar_graph)

    def _on_range_changed(self, range_str: str):
        self._current_range = range_str
        self._build_calendar(self._RANGE_DAYS.get(range_str, 365))

    # ------------------------------------------------------------------
    # Recent practice
    # ------------------------------------------------------------------

    def _build_recent(self, layout, habits):
        entries = []
        for habit in habits:
            for bucket in habit.get_activity_buckets(limit=10):
                entries.append((habit, bucket))

        if not entries:
            layout.addWidget(self._create_text_label("No recent activity.", secondary=True))
            return

        entries.sort(key=lambda pair: pair[1].end, reverse=True)
        for habit, bucket in entries[:20]:
            layout.addWidget(self._build_recent_row(habit, bucket))
            layout.addSpacing(2)

    def _build_recent_row(self, habit, bucket) -> QFrame:
        from core.util.time import get_friendly_elapsed

        t = _t()
        row = QFrame()
        row.setObjectName("statsRecentRow")
        row.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        row.setStyleSheet(f"""
            QFrame#statsRecentRow {{
                background-color: {t.card_bg};
                border: 1px solid {t.card_border};
                border-left: 3px solid {t.accent};
                border-radius: 5px;
            }}
            QFrame#statsRecentRow:hover {{ border-color: {t.card_hover_border}; border-left-color: {t.accent}; }}
        """)
        row.mousePressEvent = lambda e, h=habit: self._navigate_to_habit(h)

        outer = QHBoxLayout(row)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(10)

        # Date gutter
        gutter_box = QVBoxLayout()
        gutter_box.setContentsMargins(0, 0, 0, 0)
        gutter_box.setSpacing(1)

        day = QLabel(bucket.start.strftime("%b %d"))
        day_font = make_font(t.header_font, 12)
        day_font.setBold(True)
        day.setFont(day_font)
        day.setStyleSheet(f"color: {t.ink_primary}; background: transparent;")
        gutter_box.addWidget(day)

        weekday = QLabel(bucket.start.strftime("%a").lower())
        weekday.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 9px;")
        gutter_box.addWidget(weekday)
        outer.addLayout(gutter_box)

        # Body: name + inline meta
        body_box = QVBoxLayout()
        body_box.setContentsMargins(0, 0, 0, 0)
        body_box.setSpacing(2)

        name = QLabel(habit.name)
        name.setWordWrap(True)
        name.setStyleSheet(f"color: {t.ink_primary}; background: transparent; font-size: 11px;")
        body_box.addWidget(name)

        sessions = bucket.sessions
        session_text = "1 session" if sessions == 1 else f"{sessions} sessions"
        meta = QLabel(f"{get_friendly_elapsed(bucket.net_duration)} · {session_text}")
        meta.setStyleSheet(f"color: {t.ink_secondary}; background: transparent; font-size: 9px;")
        body_box.addWidget(meta)
        outer.addLayout(body_box, 1)

        return row

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _group_header(self, text: str) -> QLabel:
        t = _t()
        label = QLabel(f"♪ {text}")
        font = make_font(t.header_font, 12)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {t.ink_primary}; background: transparent; padding: 2px 0px;")
        return label

    @staticmethod
    def _format_hours(total_seconds: int) -> str:
        """Compact human duration: '0m', '47m', '6h', '14h 32m'."""
        total_seconds = int(total_seconds)
        if total_seconds <= 0:
            return "0m"
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        if hours <= 0:
            return f"{minutes}m"
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h {minutes}m"

    def _navigate_to_habit(self, habit):
        self.navigate_to.emit('habit_detail', habit.id)
