"""
Base SheetPage - Abstract base class for all music sheet pages.
"""

from abc import ABCMeta, abstractmethod
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QPalette


# Resolve metaclass conflict between QWidget and ABC
class CombinedMeta(type(QWidget), ABCMeta):
    pass


class SheetPage(QWidget, metaclass=CombinedMeta):
    """Abstract base class for all sheet pages"""

    # Signals
    navigate_to = pyqtSignal(str, object)  # (page_type, data) - request navigation
    go_back = pyqtSignal()  # Request back navigation
    content_updated = pyqtSignal()  # Content changed, need refresh

    # Shared vintage paper aesthetic colors (sepia tones)
    PAPER_COLOR = QColor(252, 248, 235)  # Aged cream paper
    INK_PRIMARY = QColor(70, 50, 35)  # Dark sepia ink
    INK_SECONDARY = QColor(110, 90, 70)  # Lighter brown ink
    LINK_COLOR = QColor(120, 80, 50)  # Warm brown link
    LINK_HOVER_COLOR = QColor(160, 110, 70)  # Lighter brown on hover
    SEPARATOR_COLOR = QColor(200, 185, 160)  # Aged separator
    ACCENT_BRASS = QColor(184, 134, 11)  # Brass/gold accent

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_style()
        self._setup_ui()

    def _setup_style(self):
        """Apply paper-like styling to the page"""
        # Don't set background via palette - let parent widget handle it
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        # Apply vintage book aesthetic with sepia tones
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: rgb(70, 50, 35);
            }}
            QLabel {{
                background: transparent;
                color: rgb(70, 50, 35);
            }}
            QLineEdit {{
                background-color: rgba(255, 252, 245, 180);
                border: none;
                border-bottom: 1px dotted rgb(150, 130, 100);
                border-radius: 0px;
                padding: 4px 6px;
                color: rgb(70, 50, 35);
            }}
            QComboBox, QSpinBox {{
                background-color: rgba(255, 252, 245, 180);
                border: 1px solid rgb(200, 185, 160);
                border-radius: 2px;
                padding: 3px 6px;
                color: rgb(70, 50, 35);
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QCheckBox {{
                background: transparent;
                color: rgb(70, 50, 35);
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                border: 1px solid rgb(120, 100, 75);
                border-radius: 2px;
                background: rgb(252, 248, 240);
            }}
            QCheckBox::indicator:checked {{
                background: rgb(184, 134, 11);
                border-color: rgb(160, 115, 10);
            }}
        """)

    def _setup_ui(self):
        """Setup the basic page layout with scrollable content"""
        # Main layout for the page (this is what QWidget.layout() returns)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        super().setLayout(main_layout)

        # Import and add menu widget at the top
        from ..sheet_menu import SheetMenu
        # Get page type from get_page_type() if it exists, otherwise derive from class name
        current_page_type = self.get_page_type() if hasattr(self, 'get_page_type') else None
        self._menu = SheetMenu(self, current_page_type=current_page_type)
        self._menu.navigate_to.connect(self.navigate_to.emit)
        main_layout.addWidget(self._menu)

        # Create scroll area with wood-styled scrollbar
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Wood piano-themed scrollbar styling (matching painted scroll indicators)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgb(61, 40, 23);  /* wood_dark */
                width: 8px;
                margin: 30px 2px 20px 2px;  /* top right bottom left */
                border: none;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: rgb(184, 134, 11);  /* brass */
                min-height: 20px;
                border-radius: 2px;
                border: 1px solid rgb(184, 134, 11);
            }
            QScrollBar::handle:vertical:hover {
                background: rgb(218, 165, 32);  /* brass_light */
                border: 1px solid rgb(218, 165, 32);
            }
            QScrollBar::add-line:vertical {
                background: transparent;
                subcontrol-position: bottom;
                subcontrol-origin: margin;
            }
            QScrollBar::sub-line:vertical {
                background: transparent;
                subcontrol-position: top;
                subcontrol-origin: margin;
            }
            QScrollBar::add-line:vertical:hover,
            QScrollBar::sub-line:vertical:hover {
                background: rgba(184, 134, 11, 30);
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: rgb(92, 61, 46);  /* wood_medium */
            }
        """)

        # Container widget for scroll content
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
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

        self.build_content()

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
        # Clear and rebuild content layout
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.build_content()

    def _create_link_label(self, text: str, callback=None) -> 'QLabel':
        """Create a clickable link-styled label with vintage ink aesthetic"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QCursor

        label = QLabel(text)
        label.setStyleSheet(f"""
            QLabel {{
                color: rgb(120, 80, 50);
                text-decoration: underline;
                background: transparent;
            }}
            QLabel:hover {{
                color: rgb(160, 110, 70);
            }}
        """)

        # Set cursor programmatically (not via stylesheet)
        label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        if callback:
            label.mousePressEvent = lambda e: callback()

        return label

    def _create_section_header(self, text: str) -> 'QLabel':
        """Create a vintage section header with handwritten style"""
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtGui import QFont

        label = QLabel(f'♫ {text}')

        font = QFont("Palatino", 14)
        font.setBold(True)
        label.setFont(font)
        label.setStyleSheet("color: rgb(70, 50, 35); padding: 2px 0px;")
        return label

    def _create_text_label(self, text: str, secondary=False) -> 'QLabel':
        """Create a regular text label with sepia ink"""
        from PyQt6.QtWidgets import QLabel

        label = QLabel(text)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        if secondary:
            label.setStyleSheet("color: rgb(110, 90, 70); font-style: italic;")
        else:
            label.setStyleSheet("color: rgb(70, 50, 35);")
        return label

    def _create_separator(self) -> 'QFrame':
        """Create a vintage separator line (aged paper color)"""
        from PyQt6.QtWidgets import QFrame

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setStyleSheet("background-color: rgb(200, 185, 160); max-height: 1px;")
        return line
