"""
Notes Widget - Markdown notes with view/edit modes.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


from gui.themes import current_theme as _t, ThemedWidget


class NotesWidget(QWidget, ThemedWidget):
    """Widget for displaying and editing Markdown notes"""
    
    note_changed = pyqtSignal(str)  # Emitted when note is saved
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._note_text = ""
        self._setup_ui()
        self._setup_style()
        self._update_view()
    
    def _setup_ui(self):
        """Set up the widget UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # View mode - Markdown rendered label
        self._view_label = QLabel()
        self._view_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self._view_label.setWordWrap(True)
        self._view_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self._view_label.setCursor(Qt.CursorShape.IBeamCursor)
        self._view_label.mousePressEvent = lambda e: self._enter_edit_mode()
        layout.addWidget(self._view_label)

        # Edit mode - Plain text editor
        self._edit_text = QTextEdit()
        self._edit_text.setAcceptRichText(False)
        self._edit_text.setPlaceholderText("Click to write a note (Markdown)")
        self._edit_text.hide()
        layout.addWidget(self._edit_text)
        
        # Connect focus out to save and switch to view mode
        self._edit_text.focusOutEvent = self._on_focus_out

    def _setup_style(self):
        t = _t()
        self._view_label.setStyleSheet(f"""
            QLabel {{
                background-color: {t.paper};
                border: 1px solid {t.border};
                border-radius: 3px;
                padding: 8px;
                color: {t.ink_primary};
                font-size: 11px;
            }}
        """)
        self._edit_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {t.paper_alt};
                border: 2px solid {t.accent};
                border-radius: 3px;
                padding: 8px;
                color: {t.ink_primary};
                font-size: 11px;
                selection-background-color: {t.input_selection};
            }}
        """)

    def _enter_edit_mode(self):
        """Switch to edit mode"""
        # Store scroll position before switching
        scroll_area = self._find_scroll_area()
        scroll_pos = scroll_area.verticalScrollBar().value() if scroll_area else 0

        self._edit_text.setPlainText(self._note_text)
        self._view_label.hide()
        self._edit_text.show()
        
        # Move cursor to start before focusing
        cursor = self._edit_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        self._edit_text.setTextCursor(cursor)
        
        self._edit_text.setFocus()

        # Restore scroll position after focus
        if scroll_area:
            scroll_area.verticalScrollBar().setValue(scroll_pos)
    
    def _find_scroll_area(self):
        """Find the parent QScrollArea"""
        from PyQt6.QtWidgets import QScrollArea
        parent = self.parent()
        while parent:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None
    
    def _on_focus_out(self, event):
        """Handle focus out - save and switch to view mode"""
        self._note_text = self._edit_text.toPlainText()
        self._update_view()
        self._edit_text.hide()
        self._view_label.show()
        self.note_changed.emit(self._note_text)
        
        # Call original focusOutEvent
        QTextEdit.focusOutEvent(self._edit_text, event)
    
    def _update_view(self):
        """Update the view label with rendered Markdown"""
        if self._note_text.strip():
            self._view_label.setText(self._note_text)
        else:
            self._view_label.setText("_No notes yet. Click to add notes._")
    
    def set_note(self, note: str):
        """Set the note content"""
        self._note_text = note or ""
        self._update_view()
    
    def get_note(self) -> str:
        """Get the current note content"""
        return self._note_text
