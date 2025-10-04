"""
Index Page - Main directory showing list of habits and navigation options.
"""

from PyQt6.QtWidgets import QVBoxLayout, QScrollArea, QWidget
from PyQt6.QtGui import QFont

from .base_page import SheetPage

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit


class IndexPage(SheetPage):
    """Index page showing list of all habits"""

    def get_page_title(self) -> str:
        return "Repertoire"

    def build_content(self):
        """Build the index page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header(self.get_page_title())
        title.setFont(QFont("Palatino", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        layout.addWidget(self._create_separator())

        # Load habits from database
        try:
            habits = list(Habit.select().order_by(Habit.name))

            if habits:
                # Create scrollable area for habits list
                scroll = QScrollArea()
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QScrollArea.Shape.NoFrame)
                scroll.setStyleSheet("background: transparent; border: none;")

                habits_widget = QWidget()
                habits_layout = QVBoxLayout()
                habits_layout.setContentsMargins(0, 0, 0, 0)
                habits_layout.setSpacing(6)
                habits_widget.setLayout(habits_layout)

                for habit in habits:
                    # Create clickable habit link
                    habit_link = self._create_link_label(
                        f"→ {habit.name}",
                        lambda h=habit: self.navigate_to.emit('habit_detail', h.id)
                    )
                    habits_layout.addWidget(habit_link)

                habits_layout.addStretch()
                scroll.setWidget(habits_widget)
                layout.addWidget(scroll)  # Give scroll area stretch priority
            else:
                no_habits_label = self._create_text_label("No habits yet. Create one below.", secondary=True)
                layout.addWidget(no_habits_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading habits: {e}", secondary=True)
            layout.addWidget(error_label)

        # Separator before actions
        layout.addWidget(self._create_separator())

        # Navigation links
        create_link = self._create_link_label(
            "+ New Habit",
            lambda: self.navigate_to.emit('habit_detail', None)
        )
        layout.addWidget(create_link)

        stats_link = self._create_link_label(
            "📊 Statistics",
            lambda: self.navigate_to.emit('stats', None)
        )
        layout.addWidget(stats_link)

        activity_link = self._create_link_label(
            "📅 Activity",
            lambda: self.navigate_to.emit('activity', None)
        )
        layout.addWidget(activity_link)
