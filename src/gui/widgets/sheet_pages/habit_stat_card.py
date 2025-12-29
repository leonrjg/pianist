"""
Habit Stat Card - Expanded card showing detailed habit statistics.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable


class HabitStatCard(QFrame):
    """Card displaying detailed statistics for a single habit"""

    def __init__(self, habit, stats: dict, on_click: Optional[Callable] = None, parent=None):
        """
        Args:
            habit: Habit object
            stats: Dictionary with keys: completion_rate, streak, total_time,
                   session_count, next_task, activity_pattern
            on_click: Optional callback when card is clicked
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.stats = stats
        self.on_click = on_click

        self._setup_ui()

    def _setup_ui(self):
        """Setup the card UI"""
        # Card styling - more compact
        self.setStyleSheet("""
            HabitStatCard {
                background-color: rgba(255, 252, 245, 180);
                border-left: 4px solid rgb(184, 134, 11);
                border-top: 1px solid rgb(200, 185, 160);
                border-right: 1px solid rgb(200, 185, 160);
                border-bottom: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                padding: 6px;
                margin: 2px 0px;
            }
            HabitStatCard:hover {
                background-color: rgba(255, 255, 250, 200);
                border-top: 1px solid rgb(184, 134, 11);
                border-right: 1px solid rgb(184, 134, 11);
                border-bottom: 1px solid rgb(184, 134, 11);
            }
        """)

        if self.on_click:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)

        # Habit name with schedule badge
        name_layout = QHBoxLayout()
        name_layout.setSpacing(6)

        name_label = QLabel(self.habit.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
        name_layout.addWidget(name_label)

        # Schedule badge
        schedule_badge = QLabel(self.habit.schedule)
        schedule_badge.setStyleSheet("""
            background-color: rgba(200, 185, 160, 120);
            color: rgb(70, 50, 35);
            font-size: 9px;
            padding: 2px 6px;
            border-radius: 3px;
        """)
        name_layout.addWidget(schedule_badge)
        name_layout.addStretch()

        main_layout.addLayout(name_layout)

        # Completion rate with progress bar
        completion_rate = self.stats.get('completion_rate', 0)
        self._add_progress_section(main_layout, completion_rate)

        # Stats row (streak, time, sessions) with labels
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)

        # Streak
        if self.stats.get('streak', 0) > 0:
            streak_label = QLabel(f"🔥 Streak: {self.stats['streak']}")
            streak_label.setStyleSheet("color: rgb(70, 50, 35); font-size: 10px; background: transparent;")
            stats_layout.addWidget(streak_label)

        # Total time
        if self.stats.get('total_time'):
            time_label = QLabel(f"Total time: {self.stats['total_time']}")
            time_label.setStyleSheet("color: rgb(70, 50, 35); font-size: 10px; background: transparent;")
            stats_layout.addWidget(time_label)

        # Session count
        if self.stats.get('session_count'):
            session_label = QLabel(f"Sessions: {self.stats['session_count']}")
            session_label.setStyleSheet("color: rgb(70, 50, 35); font-size: 10px; background: transparent;")
            stats_layout.addWidget(session_label)

        stats_layout.addStretch()
        main_layout.addLayout(stats_layout)

    def _add_progress_section(self, layout, completion_rate):
        """Add completion rate progress bar"""
        # Completion rate label
        rate_text = f"{int(completion_rate * 100)}% consistency"
        rate_label = QLabel(rate_text)
        rate_label.setStyleSheet("color: rgb(70, 50, 35); font-size: 10px; background: transparent;")
        layout.addWidget(rate_label)

        # Progress bar styled as vintage gauge
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(int(completion_rate * 100))
        progress_bar.setTextVisible(False)
        progress_bar.setFixedHeight(8)

        # Style based on performance
        if completion_rate >= 0.8:
            bar_color = "rgb(184, 134, 11)"  # Brass - excellent
        elif completion_rate >= 0.5:
            bar_color = "rgb(140, 110, 80)"  # Brown - good
        else:
            bar_color = "rgb(180, 160, 140)"  # Light sepia - needs attention

        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(230, 225, 210, 180);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)

        layout.addWidget(progress_bar)

    def mousePressEvent(self, event):
        """Handle click to trigger callback"""
        if self.on_click:
            self.on_click(self.habit)
