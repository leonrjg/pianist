"""Reusable productivity/progress bar component."""

from PyQt6.QtWidgets import QProgressBar


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


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

        t = _t()
        if self.rate >= 0.8:
            bar_color = t.accent
            text_color = t.button_primary_text
        elif self.rate >= 0.6:
            bar_color = t.accent_dark
            text_color = t.button_primary_text
        else:
            bar_color = t.border
            text_color = t.ink_primary

        self.setStyleSheet(f"""
            ProductivityProgressBar {{
                background-color: {t.paper_dark};
                border: 1px solid {t.border};
                border-radius: 4px;
                color: {text_color};
                font-size: 9px;
                text-align: center;
            }}
            ProductivityProgressBar::chunk {{
                background-color: {bar_color};
                border-radius: 3px;
            }}
        """)
