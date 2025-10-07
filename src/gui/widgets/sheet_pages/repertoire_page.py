"""
Repertoire Page - List of all habits.
"""

from PyQt6.QtWidgets import QVBoxLayout, QWidget
from PyQt6.QtGui import QFont

from .base_page import SheetPage

# Import database models
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from core.habit.habit import Habit


class RepertoirePage(SheetPage):
    """Repertoire page showing list of all habits"""

    def get_page_title(self) -> str:
        return "Repertoire"

    def get_page_type(self) -> str:
        return "repertoire"

    def build_content(self):
        """Build the repertoire page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header(self.get_page_title())
        title.setFont(QFont("Palatino", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        # Load habits from database
        try:
            habits = list(Habit.select().order_by(Habit.display_order, Habit.name))

            if habits:
                habits_widget = QWidget()
                habits_layout = QVBoxLayout()
                habits_layout.setContentsMargins(0, 0, 0, 0)
                habits_widget.setLayout(habits_layout)

                for habit in habits:
                    # Create clickable habit link
                    habit_link = self._create_link_label(
                        f"→ {habit.name}",
                        lambda h=habit: self.navigate_to.emit('habit_detail', h.id)
                    )
                    habits_layout.addWidget(habit_link)

                habits_layout.addStretch()
                layout.addWidget(habits_widget)
            else:
                no_habits_label = self._create_text_label("No habits yet.", secondary=True)
                layout.addWidget(no_habits_label)

        except Exception as e:
            error_label = self._create_text_label(f"Error loading habits: {e}", secondary=True)
            layout.addWidget(error_label)
