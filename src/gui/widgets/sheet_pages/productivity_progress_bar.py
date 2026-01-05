"""Reusable productivity/progress bar component with vintage styling."""

from PyQt6.QtWidgets import QProgressBar


class ProductivityProgressBar(QProgressBar):
    """Progress bar with embedded text showing percentage and vintage styling."""

    def __init__(self, rate: float, label_text: str = None, parent=None):
        """
        Args:
            rate: Progress rate from 0.0 to 1.0
            label_text: Optional custom label (defaults to "{rate}% productivity")
            parent: Parent widget
        """
        super().__init__(parent)
        self.rate = max(0.0, min(1.0, rate))
        self.label_text = label_text or f"{int(self.rate * 100)}% productivity"
        self._setup_ui()

    def _setup_ui(self):
        """Setup the progress bar UI."""
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(int(self.rate * 100))
        self.setTextVisible(True)
        self.setFormat(self.label_text)
        self.setFixedHeight(18)

        # Color based on performance
        if self.rate >= 0.8:
            bar_color = "rgb(184, 134, 11)"  # Brass - excellent
        elif self.rate >= 0.6:
            bar_color = "rgb(140, 110, 80)"  # Brown - good
        else:
            bar_color = "rgb(180, 160, 140)"  # Light sepia - needs attention

        self.setStyleSheet(f"""
            ProductivityProgressBar {{
                background-color: rgba(230, 225, 210, 180);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 4px;
                color: black;
                font-size: 9px;
                text-align: center;
            }}
            ProductivityProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)
