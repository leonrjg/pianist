"""
Base SheetPage - Abstract base class for all music sheet pages.
"""

from abc import abstractmethod
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QColor


from gui.themes import current_theme as _t, ThemedWidget
from gui.constants import font_pt, make_font


class SheetPage(QWidget, ThemedWidget):
    """Abstract base class for all sheet pages"""

    # Signals
    navigate_to = pyqtSignal(str, object)  # (page_type, data) - request navigation
    content_updated = pyqtSignal()  # Content changed, need refresh

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        """Apply paper-like styling to the page using the active theme."""
        t = _t()
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {t.ink_primary};
            }}
            QLabel {{
                background: transparent;
                color: {t.ink_primary};
                margin: 0;
                padding: 0;
            }}
            QLineEdit {{
                background-color: {t.paper};
                border: 1px dotted {t.border};
                margin: 0 4px 0 4px;
                padding: 4px 6px;
                color: {t.ink_primary};
            }}
            QComboBox, QSpinBox {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 2px;
                padding: 3px 6px;
                color: {t.ink_primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QCheckBox {{
                background: transparent;
                color: {t.ink_primary};
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                border: 1px solid {t.border};
                border-radius: 2px;
                background: {t.paper_alt};
            }}
            QCheckBox::indicator:checked {{
                background: {t.accent};
                border-color: {t.accent_dark};
            }}
        """)

    def _setup_ui(self):
        """Setup the basic page layout with scrollable content"""
        # Main layout for the page (this is what QWidget.layout() returns)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        super().setLayout(main_layout)

        # Create scroll area with wood-styled scrollbar
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        t = _t()
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {t.scrollbar_stylesheet}
        """)

        # Container widget for scroll content
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(6)
        scroll_content.setLayout(content_layout)

        # Set scroll content
        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Override layout() to return content layout for subclasses
        self._main_layout = main_layout
        self._content_layout = content_layout
        self._scroll_area = scroll_area
        self._scroll_content = scroll_content

        self._scroll_area.viewport().installEventFilter(self)
        self.build_content()
        self._update_content_width()

    def _update_content_width(self):
        """Clamp content width to current viewport."""
        if self._scroll_area and self._scroll_content:
            viewport_width = self._scroll_area.viewport().width()
            if viewport_width > 0:
                self._scroll_content.setMaximumWidth(viewport_width)

    def resizeEvent(self, event):
        """Keep content width in sync on page resize."""
        super().resizeEvent(event)
        self._update_content_width()

    def layout(self):
        """Override to return the content layout for subclasses to use"""
        return self._content_layout

    @abstractmethod
    def build_content(self):
        """Build the page content (must be implemented by subclasses)"""
        pass

    @abstractmethod
    def get_page_title(self) -> str:
        """Return the page title"""
        pass

    @abstractmethod
    def get_page_type(self) -> str:
        """Return the page type for navigation"""
        pass

    def refresh(self):
        """Refresh page content (can be overridden)"""
        t = _t()
        self._scroll_area.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            {t.scrollbar_stylesheet}
        """)
        # Clear and rebuild content layout
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.build_content()
        self._update_content_width()

    def eventFilter(self, obj, event):
        if obj is self._scroll_area.viewport() and event.type() == QEvent.Type.Resize:
            self._update_content_width()
        return super().eventFilter(obj, event)

    def _create_link_label(self, text: str, callback=None) -> 'QLabel':
        """Create a clickable link-styled label."""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QCursor
        t = _t()
        label = QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: {t.link};
                text-decoration: underline;
                background: transparent;
            }}
            QLabel:hover {{
                color: {t.link_hover};
            }}
        """)
        label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        if callback:
            label.mousePressEvent = lambda e: callback()
        return label

    def _create_section_header(self, text: str) -> 'QLabel':
        """Create a section header styled for the active theme."""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QFont
        t = _t()
        label = QLabel(f'♫ {text}')
        font = make_font(t.header_font, 18)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet(f"color: {t.ink_primary};")
        return label

    def _create_text_label(self, text: str, secondary=False) -> 'QLabel':
        """Create a regular text label."""
        from PyQt6.QtWidgets import QLabel
        t = _t()
        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if secondary:
            label.setStyleSheet(f"color: {t.ink_secondary}; font-style: italic;")
        else:
            label.setStyleSheet(f"color: {t.ink_primary};")
        return label

    def _create_separator(self) -> 'QFrame':
        """Create a separator line."""
        from PyQt6.QtWidgets import QFrame
        t = _t()
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet(f"background-color: {t.separator}; max-height: 1px;")
        return line
