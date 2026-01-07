"""
Vintage Form Widgets - Styled form components matching the vintage aesthetic.
"""

from PyQt6.QtWidgets import QLineEdit, QSpinBox, QCheckBox, QFrame, QVBoxLayout, QLabel, QPushButton, QDateEdit
from PyQt6.QtGui import QFont, QCursor, QIcon
from PyQt6.QtCore import Qt, QDate, QTimer
from pathlib import Path
from .vintage_styles import VINTAGE_MENU_STYLE


class VintageLineEdit(QLineEdit):
    """Line edit with vintage paper styling"""

    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        if placeholder:
            self.setPlaceholderText(placeholder)

        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                color: rgb(70, 50, 35);
                font-size: 11px;
                selection-background-color: rgba(184, 134, 11, 120);
            }
            QLineEdit:focus {
                border: 1px solid rgb(184, 134, 11);
                background-color: rgba(255, 255, 250, 220);
            }
            QLineEdit::placeholder {
                color: rgba(120, 100, 80, 150);
                font-style: italic;
            }
        """)


class VintageSpinBox(QSpinBox):
    """Spin box with vintage paper styling"""

    def __init__(self, suffix="", parent=None):
        super().__init__(parent)

        # Disable up/down buttons
        self.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)

        self.setStyleSheet("""
            QSpinBox {
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                padding: 4px 6px;
                color: rgb(70, 50, 35);
                font-size: 11px;
                selection-background-color: rgba(184, 134, 11, 120);
            }
            QSpinBox:focus {
                border: 1px solid rgb(184, 134, 11);
                background-color: rgba(255, 255, 250, 220);
            }
        """)

    def stepBy(self, steps):
        """Override to disable keyboard up/down arrow stepping"""
        pass


class VintageCheckBox(QCheckBox):
    """Checkbox with vintage paper styling"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)

        self.setStyleSheet("""
            QCheckBox {
                color: rgb(70, 50, 35);
                font-size: 11px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
            }
            QCheckBox::indicator:hover {
                border: 1px solid rgb(184, 134, 11);
                background-color: rgba(255, 255, 250, 220);
            }
            QCheckBox::indicator:checked {
                background-color: rgba(184, 134, 11, 180);
                border: 1px solid rgb(160, 115, 10);
            }
        """)


class VintageDateEdit(QDateEdit):
    """Date edit with vintage paper styling"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat("yyyy-MM-dd")

        # Disable up/down buttons
        self.setButtonSymbols(QDateEdit.ButtonSymbols.NoButtons)

        # Build the complete stylesheet including shared menu styles
        complete_style = """
            QDateEdit {
                background-color: rgba(255, 252, 245, 200);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 3px;
                padding: 4px 6px;
                color: rgb(70, 50, 35);
                font-size: 11px;
                selection-background-color: rgba(184, 134, 11, 120);
            }
            QDateEdit:focus {
                border: 1px solid rgb(184, 134, 11);
                background-color: rgba(255, 255, 250, 220);
            }
            QDateEdit::drop-down {
                background-color: rgba(200, 185, 160, 120);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 2px;
                width: 24px;
                subcontrol-position: right;
                image: url({calendar_icon_url});
                padding: 2px;
            }
            QDateEdit::drop-down:hover {
                background-color: rgba(184, 134, 11, 120);
            }
            
            /* Calendar popup styling */
            QCalendarWidget {
                background-color: rgb(255, 252, 245);
                border: 2px solid rgb(184, 134, 11);
                border-radius: 4px;
            }
            
            /* Navigation bar */
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: rgb(184, 134, 11);
                border-bottom: 1px solid rgb(160, 115, 10);
            }
            
            /* Month/Year buttons */
            QCalendarWidget QToolButton {
                color: rgb(255, 252, 245);
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-radius: 3px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: rgba(200, 150, 30, 150);
            }
            QCalendarWidget QToolButton:pressed {
                background-color: rgba(160, 115, 10, 150);
            }
            
            /* Vertical arrow buttons */
            QCalendarWidget QToolButton::menu-indicator {
                image: none;
            }
            
            /* Header (day names) */
            QCalendarWidget QWidget {
                alternate-background-color: rgb(245, 240, 225);
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: rgb(255, 252, 245);
                color: rgb(70, 50, 35);
                font-size: 10px;
                selection-background-color: rgba(184, 134, 11, 180);
                selection-color: rgb(255, 252, 245);
            }
            
            /* Day cells */
            QCalendarWidget QAbstractItemView {
                gridline-color: rgb(230, 220, 200);
            }
            
            /* Header row with day names */
            QCalendarWidget QHeaderView::section {
                background-color: rgba(200, 185, 160, 120);
                color: rgb(70, 50, 35);
                font-size: 9px;
                font-weight: bold;
                padding: 4px;
                border: none;
                border-bottom: 1px solid rgb(200, 185, 160);
            }
            
            /* Today's date */
            QCalendarWidget QAbstractItemView:enabled {
                background-color: rgb(255, 252, 245);
            }
        """
        
        # Append the shared menu style for calendar dropdowns
        complete_style += "\n" + VINTAGE_MENU_STYLE.replace("QMenu", "QCalendarWidget QMenu")
        
        self.setStyleSheet(complete_style)
    
    def stepBy(self, steps):
        """Override to disable keyboard up/down arrow stepping"""
        pass


class VintageButton(QPushButton):
    """Button with vintage paper styling"""

    def __init__(self, text="", button_type="primary", parent=None):
        """
        Args:
            text: Button text
            button_type: "primary", "secondary", or "danger"
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.button_type = button_type
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._apply_style()

    def _apply_style(self):
        """Apply styling based on button type"""
        if self.button_type == "primary":
            # Brass/gold primary button
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(184, 134, 11, 180);
                    border: 1px solid rgb(160, 115, 10);
                    border-radius: 4px;
                    padding: 6px 16px;
                    color: rgb(255, 252, 245);
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: rgba(200, 150, 30, 200);
                    border: 1px solid rgb(184, 134, 11);
                }
                QPushButton:pressed {
                    background-color: rgba(160, 115, 10, 200);
                }
            """)
        elif self.button_type == "danger":
            # Red danger button
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(180, 50, 50, 150);
                    border: 1px solid rgb(150, 40, 40);
                    border-radius: 4px;
                    padding: 6px 16px;
                    color: rgb(255, 252, 245);
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(200, 60, 60, 180);
                    border: 1px solid rgb(180, 50, 50);
                }
                QPushButton:pressed {
                    background-color: rgba(150, 40, 40, 180);
                }
            """)
        else:  # secondary
            # Light paper secondary button
            self.setStyleSheet("""
                QPushButton {
                    background-color: rgba(255, 252, 245, 200);
                    border: 1px solid rgb(200, 185, 160);
                    border-radius: 4px;
                    padding: 6px 16px;
                    color: rgb(70, 50, 35);
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: rgba(255, 255, 250, 220);
                    border: 1px solid rgb(184, 134, 11);
                }
                QPushButton:pressed {
                    background-color: rgba(240, 235, 220, 220);
                }
            """)


class FormSection(QFrame):
    """Card-style section container for grouping form fields"""

    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            FormSection {
                background-color: rgba(255, 252, 245, 150);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 4px;
                padding: 4px;
                margin: 4px 0px;
            }
        """)

        # Main layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(8, 8, 8, 8)
        self.main_layout.setSpacing(6)
        self.setLayout(self.main_layout)

        # Add title if provided
        if title:
            title_label = QLabel(title)
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(10)
            title_label.setFont(title_font)
            title_label.setStyleSheet("color: rgb(70, 50, 35); background: transparent;")
            self.main_layout.addWidget(title_label)

    def add_field(self, label_text, widget):
        """Add a labeled field to the section"""
        # Label
        label = QLabel(label_text)
        label.setStyleSheet("color: rgb(100, 80, 65); font-size: 10px; background: transparent;")
        self.main_layout.addWidget(label)

        # Widget
        self.main_layout.addWidget(widget)

    def add_widget(self, widget):
        """Add a widget directly to the section"""
        self.main_layout.addWidget(widget)
