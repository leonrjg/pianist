"""
Sheet Menu Widget - Top navigation menu for all sheet pages.

A horizontal scrollable menu bar with icon-based navigation buttons.
"""

from dataclasses import dataclass
from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QScrollArea, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon


# Theme constants - centralized for consistency and easy modification
class MenuTheme:
    """Visual theme constants for the menu."""

    # Colors (sepia/vintage theme matching the rest of the UI)
    PAPER_BG = "rgba(252, 248, 235, 200)"
    PAPER_BORDER = "rgb(200, 185, 160)"
    INK_COLOR = "rgb(70, 50, 35)"
    BRASS_PRIMARY = "rgb(184, 134, 11)"
    BRASS_DARK = "rgb(160, 115, 10)"
    BRASS_LIGHT = "rgb(218, 165, 32)"
    BRASS_LIGHTER = "rgb(232, 195, 92)"
    PAPER_LIGHT = "rgba(255, 252, 245, 255)"
    PAPER_PRESSED = "rgba(240, 235, 220, 255)"
    PAPER_CREAM = "rgb(252, 248, 235)"

    # Dimensions
    BUTTON_SIZE = 30
    ICON_SIZE = 18
    BORDER_RADIUS = 6
    BUTTON_SPACING = 4
    TOP_MARGIN = 4
    BOTTOM_MARGIN = 2
    BUTTON_BOTTOM_MARGIN = 0
    SIDE_MARGIN = 6
    SCROLLBAR_HEIGHT = 3
    SCROLLBAR_MIN_WIDTH = 20
    SCROLLBAR_TOP_MARGIN = 2

    # Typography
    FONT_SIZE = 14
    TOOLTIP_FONT_SIZE = 12


@dataclass
class MenuItem:
    """Data class representing a menu item configuration."""
    page_type: str
    tooltip: str
    icon_path: Optional[str] = None
    data: Optional[object] = None


class MenuButton(QPushButton):
    """Individual menu button with icon and tooltip."""

    def __init__(self, icon_path: Optional[str], tooltip: str, parent=None):
        super().__init__(parent)

        self.setToolTip(tooltip)
        self.setFixedSize(MenuTheme.BUTTON_SIZE, MenuTheme.BUTTON_SIZE)

        # Set icon if SVG path provided
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(MenuTheme.ICON_SIZE, MenuTheme.ICON_SIZE))

        # Apply vintage button styling
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {MenuTheme.PAPER_BG};
                border: 1px solid {MenuTheme.PAPER_BORDER};
                border-radius: {MenuTheme.BORDER_RADIUS}px;
                color: {MenuTheme.INK_COLOR};
                font-size: {MenuTheme.FONT_SIZE}px;
            }}
            QPushButton:hover {{
                background-color: {MenuTheme.PAPER_LIGHT};
                border-color: {MenuTheme.BRASS_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {MenuTheme.PAPER_PRESSED};
            }}
            QPushButton[active="true"] {{
                background-color: {MenuTheme.BRASS_LIGHT};
                border-color: {MenuTheme.BRASS_PRIMARY};
                color: {MenuTheme.INK_COLOR};
            }}
            QPushButton[active="true"]:hover {{
                background-color: {MenuTheme.BRASS_LIGHTER};
                border-color: {MenuTheme.BRASS_PRIMARY};
            }}
            QToolTip {{
                background-color: {MenuTheme.PAPER_CREAM};
                color: {MenuTheme.INK_COLOR};
                border: 1px solid {MenuTheme.BRASS_PRIMARY};
                padding: 4px;
                border-radius: 3px;
                font-size: {MenuTheme.TOOLTIP_FONT_SIZE}px;
            }}
        """)


class SheetMenu(QWidget):
    """Top navigation menu for sheet pages."""

    # Single signal for all navigation with page type and optional data
    navigate_to = pyqtSignal(str, object)  # (page_type, data)

    # Menu items configuration - centralized for easy modification
    MENU_ITEMS = [
        MenuItem('index', 'Next Tasks', 'gui/icons/next.svg'),
        MenuItem('repertoire', 'Repertoire', 'gui/icons/list.svg'),
        MenuItem('reminders', 'Reminders', 'gui/icons/bell.svg'),
        MenuItem('calendar', 'Calendar', 'gui/icons/calendar.svg'),
        MenuItem('habit_detail', 'New Habit', 'gui/icons/new.svg'),
        MenuItem('stats', 'Stats', 'gui/icons/stats.svg'),
        MenuItem('settings', 'Settings', 'gui/icons/settings.svg'),
    ]

    def __init__(self, parent=None, current_page_type: Optional[str] = None):
        super().__init__(parent)
        self._current_page_type = current_page_type
        self._setup_ui()

    def _setup_ui(self):
        """Setup the menu UI with scrollable button layout."""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, MenuTheme.TOP_MARGIN, 0, MenuTheme.BOTTOM_MARGIN)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        self.setStyleSheet("background: transparent;")

        scroll_area = self._create_scroll_area()
        button_container = self._create_button_container()

        scroll_area.setWidget(button_container)
        main_layout.addWidget(scroll_area)

        # Set maximum height dynamically based on actual content size
        self.setMaximumHeight(button_container.sizeHint().height() + MenuTheme.TOP_MARGIN + MenuTheme.BOTTOM_MARGIN + MenuTheme.SCROLLBAR_HEIGHT + MenuTheme.SCROLLBAR_TOP_MARGIN)

    def _create_scroll_area(self) -> QScrollArea:
        """Create and configure the horizontal scroll area."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {MenuTheme.PAPER_BORDER};
                height: {MenuTheme.SCROLLBAR_HEIGHT}px;
                border: none;
                border-radius: 3px;
                margin-left: 10%;
                margin-right: 10%;
            }}
            QScrollBar::handle:horizontal {{
                background: {MenuTheme.BRASS_PRIMARY};
                min-width: {MenuTheme.SCROLLBAR_MIN_WIDTH}px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {MenuTheme.BRASS_LIGHT};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                background: transparent;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)

        return scroll_area

    def _create_button_container(self) -> QWidget:
        """Create the container widget for menu buttons."""
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent;")

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(MenuTheme.SIDE_MARGIN, 0, MenuTheme.SIDE_MARGIN, MenuTheme.BUTTON_BOTTOM_MARGIN)
        button_layout.setSpacing(MenuTheme.BUTTON_SPACING)
        button_container.setLayout(button_layout)

        # Center the buttons
        button_layout.addStretch()
        self._create_menu_buttons(button_layout)
        button_layout.addStretch()

        return button_container

    def _create_menu_buttons(self, layout: QHBoxLayout):
        """Create all menu buttons from configuration."""
        for menu_item in self.MENU_ITEMS:
            btn = self._create_button(menu_item)
            layout.addWidget(btn)

    def _create_button(self, menu_item: MenuItem) -> MenuButton:
        """Create a single menu button from a MenuItem configuration."""
        btn = MenuButton(menu_item.icon_path, menu_item.tooltip, self)

        # Store page type on the button for later identification
        btn.setProperty('page_type', menu_item.page_type)

        # Connect click signal with proper closure
        btn.clicked.connect(
            lambda checked=False, item=menu_item:
                self._on_button_clicked(item.page_type, item.data)
        )

        # Set active state if this is the current page
        if menu_item.page_type == self._current_page_type:
            btn.setProperty('active', True)

        return btn

    def _on_button_clicked(self, page_type: str, data: Optional[object]):
        """Handle button click and update active state."""
        self.set_current_page(page_type)
        self.navigate_to.emit(page_type, data)

    def set_current_page(self, page_type: str):
        """Update the current page type and refresh all button states."""
        if self._current_page_type == page_type:
            return  # No change needed

        self._current_page_type = page_type

        # Update all menu buttons by iterating through children
        for child in self.findChildren(MenuButton):
            is_active = (child.property('page_type') == page_type)
            child.setProperty('active', is_active)
            child.style().unpolish(child)
            child.style().polish(child)
