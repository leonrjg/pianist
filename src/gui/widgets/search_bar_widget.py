"""
Search Bar Widget - Browser-style text search interface.

Provides a compact floating search bar with keyboard navigation support.
"""

from PyQt6.QtWidgets import QFrame, QLineEdit, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


class SearchBarWidget(QFrame):
    """Browser-style search bar for text search functionality."""
    
    # Signals
    search_changed = pyqtSignal(str)  # Emitted when search query changes
    next_match = pyqtSignal()  # Emitted when user requests next match
    previous_match = pyqtSignal()  # Emitted when user requests previous match
    close_requested = pyqtSignal()  # Emitted when user wants to close search
    
    def __init__(self, parent=None):
        """Initialize the search bar widget."""
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._setup_ui()
        self._setup_shortcuts()
    
    def _setup_ui(self):
        """Setup the search bar UI."""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)
        
        # Search input field
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Find in page...")
        self._search_input.setFixedHeight(22)
        self._search_input.textChanged.connect(self._on_search_changed)
        layout.addWidget(self._search_input, stretch=1)
        
        # Match counter label
        self._counter_label = QLabel("0 of 0")
        self._counter_label.setFixedWidth(45)
        self._counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._counter_label)
        
        # Close button
        self._close_button = QPushButton("×")
        self._close_button.setFixedSize(20, 20)
        self._close_button.clicked.connect(self.close_requested.emit)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self._close_button)
        
        # Style the widget and children
        t = _t()
        self.setStyleSheet(f"""
            SearchBarWidget {{
                background-color: {t.paper_alt};
                border: 2px solid {t.accent};
                border-radius: 4px;
            }}
            QLineEdit {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 4px 8px;
                color: {t.ink_primary};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}
            QLabel {{
                color: {t.ink_primary};
                font-size: 11px;
                font-weight: 600;
                background: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {t.ink_primary};
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {t.input_selection};
                border-radius: 3px;
            }}
            QPushButton:pressed {{
                background-color: {t.input_selection};
            }}
        """)
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts."""
        # Install event filter on search input to catch Enter/Escape
        self._search_input.installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """Handle keyboard events for search input."""
        if obj == self._search_input and event.type() == event.Type.KeyPress:
            key_event = event
            key = key_event.key()
            modifiers = key_event.modifiers()
            
            # Enter or F3: Next match
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_F3):
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    self.previous_match.emit()
                else:
                    self.next_match.emit()
                return True
            
            # Escape: Close search
            elif key == Qt.Key.Key_Escape:
                self.close_requested.emit()
                return True
        
        return super().eventFilter(obj, event)
    
    def _on_search_changed(self, text: str):
        """Handle search text change."""
        self.search_changed.emit(text)
    
    def update_counter(self, current: int, total: int):
        """
        Update the match counter display.
        
        Args:
            current: Current match index (1-based)
            total: Total number of matches
        """
        self._counter_label.setText(f"{current} of {total}")
    
    def focus_input(self):
        """Focus the search input field."""
        self._search_input.setFocus()
        self._search_input.selectAll()
    
    def get_search_text(self) -> str:
        """
        Get the current search text.
        
        Returns:
            Current search query
        """
        return self._search_input.text()
    
    def clear_search(self):
        """Clear the search input."""
        self._search_input.clear()
