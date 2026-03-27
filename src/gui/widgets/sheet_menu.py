"""
Sheet Menu Widget - Top navigation menu for all sheet pages.

A horizontal scrollable menu bar with icon-based navigation buttons.
"""

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QPushButton, QScrollArea, QWidget


from gui.themes import current_theme as _t, ThemedWidget


# Dimension constants (not theme-sensitive)
class _Dim:
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
    FONT_SIZE = 14
    TOOLTIP_FONT_SIZE = 12


@dataclass
class MenuItem:
    """Data class representing a menu item configuration."""

    page_type: str
    tooltip: str
    icon_path: Optional[str] = None
    data: Optional[object] = None


def _tinted_icon(icon_path: str, tint: str, size: int) -> QIcon:
    """Return a QIcon rendered sharp at the correct device pixel ratio.
    If tint is non-empty, all opaque pixels are recolored to that rgb(r,g,b) color."""
    dpr = QApplication.primaryScreen().devicePixelRatio()
    target = int(size * dpr)
    src = QIcon(icon_path).pixmap(QSize(target, target))
    if not tint:
        src.setDevicePixelRatio(dpr)
        return QIcon(src)
    src.setDevicePixelRatio(1.0)  # work in physical pixel space so drawPixmap fills the canvas
    result = QPixmap(src.size())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, src)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    r, g, b = [int(v.strip()) for v in tint[4:-1].split(',')]
    painter.fillRect(result.rect(), QColor(r, g, b))
    painter.end()
    result.setDevicePixelRatio(dpr)
    return QIcon(result)


class MenuButton(QPushButton, ThemedWidget):
    """Individual menu button with icon and tooltip."""

    def __init__(self, icon_path: Optional[str], tooltip: str, parent=None):
        super().__init__(parent)
        self._icon_path = icon_path
        self.setToolTip(tooltip)
        self.setFixedSize(_Dim.BUTTON_SIZE, _Dim.BUTTON_SIZE)
        self._setup_style()

    def _setup_style(self):
        t = _t()
        if self._icon_path:
            self.setIcon(_tinted_icon(self._icon_path, t.icon_tint, _Dim.ICON_SIZE))
            self.setIconSize(QSize(_Dim.ICON_SIZE, _Dim.ICON_SIZE))
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {t.paper_alt};
                border: 1px solid {t.border};
                border-radius: {_Dim.BORDER_RADIUS}px;
                color: {t.ink_primary};
                font-size: {_Dim.FONT_SIZE}px;
            }}
            QPushButton:hover {{
                background-color: {t.paper};
                border-color: {t.accent};
            }}
            QPushButton:pressed {{
                background-color: {t.paper_dark};
            }}
            QPushButton[active="true"] {{
                background-color: {t.accent};
                border-color: {t.accent_dark};
                color: {t.ink_primary};
            }}
            QPushButton[active="true"]:hover {{
                background-color: {t.accent_dark};
                border-color: {t.accent_dark};
            }}
            QToolTip {{
                background-color: {t.paper};
                color: {t.ink_primary};
                border: 1px solid {t.accent};
                padding: 4px;
                border-radius: 3px;
                font-size: {_Dim.TOOLTIP_FONT_SIZE}px;
            }}
        """)


class SheetMenu(QWidget, ThemedWidget):
    """Top navigation menu for sheet pages."""

    navigate_to = pyqtSignal(str, object)

    MENU_ITEMS = [
        MenuItem("index", "Next Tasks", "gui/icons/next.svg"),
        MenuItem("repertoire", "Repertoire", "gui/icons/list.svg"),
        MenuItem("reminders", "Reminders", "gui/icons/bell.svg"),
        MenuItem("calendar", "Calendar", "gui/icons/calendar.svg"),
        MenuItem("habit_detail", "New Habit", "gui/icons/new.svg"),
        MenuItem("stats", "Stats", "gui/icons/stats.svg"),
        MenuItem("settings", "Settings", "gui/icons/settings.svg"),
    ]

    def __init__(self, parent=None, current_page_type: Optional[str] = None):
        super().__init__(parent)
        self._current_page_type = current_page_type
        self._scroll_area = None
        self._setup_ui()

    def _setup_style(self):
        """Called by ThemeManager.apply() to re-theme all children."""
        if self._scroll_area:
            self._apply_scroll_style(self._scroll_area)
        for btn in self.findChildren(MenuButton):
            btn._setup_style()
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, _Dim.TOP_MARGIN, 0, _Dim.BOTTOM_MARGIN)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)
        self.setStyleSheet("background: transparent;")

        self._scroll_area = self._create_scroll_area()
        button_container = self._create_button_container()
        self._scroll_area.setWidget(button_container)
        main_layout.addWidget(self._scroll_area)

        self.setMaximumHeight(
            button_container.sizeHint().height()
            + _Dim.TOP_MARGIN
            + _Dim.BOTTOM_MARGIN
            + _Dim.SCROLLBAR_HEIGHT
            + _Dim.SCROLLBAR_TOP_MARGIN
        )

    def _apply_scroll_style(self, scroll_area):
        t = _t()
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {t.border};
                height: {_Dim.SCROLLBAR_HEIGHT}px;
                border: none;
                border-radius: 3px;
                margin-left: 10%;
                margin-right: 10%;
            }}
            QScrollBar::handle:horizontal {{
                background: {t.accent};
                min-width: {_Dim.SCROLLBAR_MIN_WIDTH}px;
                border-radius: 3px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {t.accent_light};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                background: transparent;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
            }}
        """)

    def _create_scroll_area(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        self._apply_scroll_style(scroll_area)
        return scroll_area

    def _create_button_container(self) -> QWidget:
        button_container = QWidget()
        button_container.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(
            _Dim.SIDE_MARGIN, 0, _Dim.SIDE_MARGIN, _Dim.BUTTON_BOTTOM_MARGIN
        )
        button_layout.setSpacing(_Dim.BUTTON_SPACING)
        button_container.setLayout(button_layout)
        button_layout.addStretch()
        self._create_menu_buttons(button_layout)
        button_layout.addStretch()
        return button_container

    def _create_menu_buttons(self, layout: QHBoxLayout):
        for menu_item in self.MENU_ITEMS:
            btn = self._create_button(menu_item)
            layout.addWidget(btn)

    def _create_button(self, menu_item: MenuItem) -> MenuButton:
        btn = MenuButton(menu_item.icon_path, menu_item.tooltip, self)
        btn.setProperty("page_type", menu_item.page_type)
        btn.clicked.connect(
            lambda checked=False, item=menu_item: self._on_button_clicked(
                item.page_type, item.data
            )
        )
        if menu_item.page_type == self._current_page_type:
            btn.setProperty("active", True)
        return btn

    def _on_button_clicked(self, page_type: str, data: Optional[object]):
        self.set_current_page(page_type)
        self.navigate_to.emit(page_type, data)

    def set_current_page(self, page_type: str):
        if self._current_page_type == page_type:
            return
        self._current_page_type = page_type
        for child in self.findChildren(MenuButton):
            is_active = child.property("page_type") == page_type
            child.setProperty("active", is_active)
            child.style().unpolish(child)
            child.style().polish(child)
