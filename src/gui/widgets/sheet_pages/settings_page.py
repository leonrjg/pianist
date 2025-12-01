"""
Stats Page - View habit statistics and analytics.
"""

from PyQt6.QtWidgets import QTextEdit

from .base_page import SheetPage

# Import database models and analytics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class SettingsPage(SheetPage):
    """Statistics page showing habit analytics"""

    def get_page_title(self) -> str:
        return "Settings"

    def get_page_type(self) -> str:
        return "settings"

    def build_content(self):
        """Build the stats page content"""
        layout = self.layout()

        # Page title
        title = self._create_section_header(self.get_page_title())
        layout.addWidget(title)

        # Text edit for monospaced stats display
        stats_text = QTextEdit()
        stats_text.setMaximumHeight(50)
        stats_text.setReadOnly(True)

        # Generate text
        stats_text.setText('etc')

        layout.addWidget(stats_text)

        # Export
        header = self._create_section_header('Export')
        layout.addWidget(header)

        csv = self._create_link_label('CSV', lambda: self.navigate_to.emit('export'))
        layout.addWidget(csv)

        layout.addStretch()

