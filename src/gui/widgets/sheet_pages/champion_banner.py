"""
Champion Banner - Special highlight for the top-performing habit.
"""

from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtGui import QFont, QCursor
from PyQt6.QtCore import Qt
from typing import Optional, Callable


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


class ChampionBanner(QFrame):
    """Vintage award-style banner highlighting the champion habit"""

    def __init__(self, habit, streak: int, completion_rate: float,
                 on_click: Optional[Callable] = None, parent=None):
        """
        Args:
            habit: Champion habit object
            streak: Longest streak count
            completion_rate: Completion rate (0-1)
            on_click: Optional callback when clicked
            parent: Parent widget
        """
        super().__init__(parent)
        self.habit = habit
        self.streak = streak
        self.completion_rate = completion_rate
        self.on_click = on_click

        self._setup_ui()

    def _setup_ui(self):
        """Setup the banner UI"""
        t = _t()
        accent_rgb = t.accent[4:-1]
        accent_light_rgb = t.accent_light[4:-1]
        self.setStyleSheet(f"""
            ChampionBanner {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba({accent_light_rgb}, 180),
                    stop:1 rgba({accent_rgb}, 180)
                );
                border: 1px solid {t.accent_dark};
                border-radius: 4px;
                padding: 6px;
                margin: 3px 0px;
            }}
            ChampionBanner:hover {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba({accent_light_rgb}, 200),
                    stop:1 rgba({accent_rgb}, 200)
                );
            }}
        """)

        if self.on_click:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        # Main layout - horizontal to save space
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(6, 4, 6, 4)
        main_layout.setSpacing(8)
        self.setLayout(main_layout)

        # Trophy icon
        trophy_label = QLabel("🏆")
        trophy_label.setStyleSheet("background: transparent; font-size: 16px;")
        main_layout.addWidget(trophy_label)

        # Vertical layout for name and stats
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Habit name
        name_label = QLabel(self.habit.name)
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(11)
        name_label.setFont(name_font)
        name_label.setStyleSheet(f"color: {t.button_primary_text}; background: transparent;")
        info_layout.addWidget(name_label)

        # Stats in one line
        stats_text = f"🔥 {self.streak} streak  •  {int(self.completion_rate * 100)}% completion"
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet(f"color: {t.button_primary_text}; font-size: 10px; background: transparent;")
        info_layout.addWidget(stats_label)

        main_layout.addLayout(info_layout)
        main_layout.addStretch()

    def mousePressEvent(self, event):
        """Handle click to trigger callback"""
        if self.on_click:
            self.on_click(self.habit)
