"""
Form Widgets - Styled form components matching the active theme.
"""

from PyQt6.QtWidgets import QLineEdit, QSpinBox, QCheckBox, QFrame, QVBoxLayout, QLabel, QPushButton, QDateEdit
from PyQt6.QtGui import QFont, QCursor, QIcon
from PyQt6.QtCore import Qt, QDate, QTimer
from pathlib import Path
from .sheet_pages.theme_styles import get_menu_stylesheet as _get_menu_stylesheet


from gui.themes import current_theme as _t
from gui.constants import font_pt


class ThemedLineEdit(QLineEdit):
    """Line edit styled with the active theme."""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)
        self._setup_style()

    def _setup_style(self):
        t = _t()
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {t.input_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
                color: {t.ink_primary};
                font-size: 11px;
                selection-background-color: {t.input_selection};
            }}
            QLineEdit:focus {{
                border: 1px solid {t.input_focus_border};
                background-color: {t.paper};
            }}
            QLineEdit::placeholder {{
                color: {t.ink_secondary};
                font-style: italic;
            }}
        """)


class ThemedSpinBox(QSpinBox):
    """Spin box styled with the active theme."""

    def __init__(self, suffix="", parent=None):
        super().__init__(parent)
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._setup_style()

    def _setup_style(self):
        t = _t()
        self.setStyleSheet(f"""
            QSpinBox {{
                background-color: {t.input_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 4px 6px;
                color: {t.ink_primary};
                font-size: 11px;
                selection-background-color: {t.input_selection};
            }}
            QSpinBox:focus {{
                border: 1px solid {t.input_focus_border};
                background-color: {t.paper};
            }}
        """)

    def stepBy(self, steps):
        pass


class ThemedCheckBox(QCheckBox):
    """Checkbox styled with the active theme."""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._setup_style()

    def _setup_style(self):
        t = _t()
        self.setStyleSheet(f"""
            QCheckBox {{
                color: {t.ink_primary};
                font-size: 11px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                background-color: {t.input_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
            }}
            QCheckBox::indicator:hover {{
                border: 1px solid {t.input_focus_border};
                background-color: {t.paper};
            }}
            QCheckBox::indicator:checked {{
                background-color: {t.button_primary_bg};
                border: 1px solid {t.accent_dark};
            }}
        """)


class ThemedDateEdit(QDateEdit):
    """Date edit styled with the active theme."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")
        self.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)
        self._setup_style()

    def _setup_style(self):
        t = _t()
        menu_style = _get_menu_stylesheet().replace("QMenu", "QCalendarWidget QMenu")
        self.setStyleSheet(f"""
            QDateEdit {{
                background-color: {t.input_bg};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 4px 6px;
                color: {t.ink_primary};
                font-size: 11px;
                selection-background-color: {t.input_selection};
            }}
            QDateEdit:focus {{
                border: 1px solid {t.input_focus_border};
                background-color: {t.paper};
            }}
            QDateEdit::drop-down {{
                background-color: {t.paper_dark};
                border: 1px solid {t.border};
                border-radius: 2px;
                width: 24px;
                subcontrol-position: right;
                padding: 2px;
            }}
            QDateEdit::drop-down:hover {{
                background-color: {t.input_selection};
            }}
            QCalendarWidget {{
                background-color: {t.paper};
                border: 2px solid {t.accent};
                border-radius: 4px;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {t.accent};
                border-bottom: 1px solid {t.accent_dark};
            }}
            QCalendarWidget QToolButton {{
                color: {t.button_primary_text};
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-radius: 3px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {t.accent_light};
            }}
            QCalendarWidget QToolButton:pressed {{
                background-color: {t.accent_dark};
            }}
            QCalendarWidget QToolButton::menu-indicator {{
                image: none;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {t.paper_alt};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: {t.paper};
                color: {t.ink_primary};
                font-size: 10px;
                selection-background-color: {t.input_selection};
                selection-color: {t.ink_primary};
            }}
            QCalendarWidget QAbstractItemView {{
                gridline-color: {t.separator};
            }}
            QCalendarWidget QHeaderView::section {{
                background-color: {t.paper_dark};
                color: {t.ink_primary};
                font-size: 9px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 1px solid {t.border};
            }}
            {menu_style}
        """)

    def stepBy(self, steps):
        pass


class ThemedButton(QPushButton):
    """Button styled with the active theme."""

    def __init__(self, text="", button_type="primary", parent=None):
        super().__init__(text, parent)
        self.button_type = button_type
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._setup_style()

    def _setup_style(self):
        t = _t()
        if self.button_type == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.button_primary_bg};
                    border: 1px solid {t.accent_dark};
                    border-radius: 4px;
                    padding: 6px 13px;
                    color: {t.button_primary_text};
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {t.button_primary_hover};
                    border: 1px solid {t.accent};
                }}
                QPushButton:pressed {{
                    background-color: {t.accent_dark};
                }}
            """)
        elif self.button_type == "danger":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.danger_bg};
                    border: 1px solid {t.accent_dark};
                    border-radius: 4px;
                    padding: 6px 13px;
                    color: {t.button_primary_text};
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {t.danger_hover};
                    border: 1px solid {t.accent_dark};
                }}
                QPushButton:pressed {{
                    background-color: {t.danger_bg};
                }}
            """)
        else:  # secondary
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {t.button_secondary_bg};
                    border: 1px solid {t.border};
                    border-radius: 4px;
                    padding: 6px 13px;
                    color: {t.button_secondary_text};
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    background-color: {t.button_secondary_hover};
                    border: 1px solid {t.accent};
                }}
                QPushButton:pressed {{
                    background-color: {t.paper_dark};
                }}
            """)


class ThemedFormSection(QFrame):
    """Card-style section container for grouping form fields."""

    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)
        self._title_text = title
        self._setup_style()

        if title:
            title_label = QLabel(title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(font_pt(10))
            title_label.setFont(title_font)
            title_label.setStyleSheet(f"color: {_t().ink_primary}; background: transparent;")
            self.main_layout.addWidget(title_label)

    def _setup_style(self):
        t = _t()
        self.setStyleSheet(f"""
            ThemedFormSection {{
                background-color: {t.card_bg};
                border: 1px solid {t.card_border};
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0px;
            }}
        """)

    def add_field(self, label_text, widget):
        t = _t()
        label = QLabel(label_text)
        label.setStyleSheet(f"color: {t.ink_secondary}; font-size: 10px; background: transparent;")
        self.main_layout.addWidget(label)
        self.main_layout.addWidget(widget)

    def add_widget(self, widget):
        self.main_layout.addWidget(widget)
