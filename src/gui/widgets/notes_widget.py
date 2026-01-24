"""
Notes Widget - Notepad that appears below piano window.

Displays a text editor for taking notes with auto-save functionality.
"""

from PyQt6.QtWidgets import QWidget, QTextEdit, QPushButton, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QIcon

from core.notes.note import Note
from ..constants import PianoColors


class NotesWidget(QWidget):
    """Notepad widget that appears below the piano window"""

    closed = pyqtSignal()
    
    # Height bounds
    MIN_HEIGHT = 90   # ~3 lines of text
    MAX_HEIGHT = 300  # Maximum height

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dynamic height between min and max
        self.setMinimumHeight(self.MIN_HEIGHT)
        self.setMaximumHeight(self.MAX_HEIGHT)
        
        # Auto-save state
        self._note = None
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_content)
        
        self._setup_ui()

    def _setup_ui(self):
        """Setup the UI layout"""
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(6, 6, 6, 6)
        main_layout.setSpacing(0)
        self.setLayout(main_layout)

        # Minimal header with close button and save indicator only
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 4)
        header.setSpacing(8)

        header.addStretch()

        # Save status indicator
        self.save_status_label = QLabel("✓")
        self.save_status_label.setFixedSize(16, 16)
        self.save_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.save_status_label.setStyleSheet("""
            QLabel {
                color: rgb(34, 139, 34);
                font-size: 14px;
            }
        """)
        self.save_status_label.setToolTip("Saved")
        header.addWidget(self.save_status_label)

        # Close button
        close_button = QPushButton("×")
        close_button.setFixedSize(20, 20)
        close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
                color: rgb(218, 165, 32);
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
                background-color: rgb(92, 61, 46);
            }}
        """)
        header.addWidget(close_button)

        main_layout.addLayout(header)

        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Write your notes here...")
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: rgb(92, 61, 46);
                color: rgb(253, 252, 248);
                border: none;
                padding: 8px;
                font-size: 12px;
                selection-background-color: rgb(184, 134, 11);
                selection-color: rgb(26, 26, 26);
            }}
            QScrollBar:vertical {{
                background-color: rgb(61, 40, 23);
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: rgb(184, 134, 11);
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: rgb(218, 165, 32);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        main_layout.addWidget(self.text_edit)

    def paintEvent(self, event):
        """Draw simple background without border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw simple rectangle background (no border, no rounded corners)
        painter.fillRect(self.rect(), QColor(61, 40, 23, 240))

    def show_at_position(self, pos: QPoint, width: int):
        """
        Show the notes widget at the specified position with given width.
        
        Args:
            pos: Position to show the widget at
            width: Width of the widget (should match piano window)
        """
        print(f"[NotesWidget] show_at_position called: pos=({pos.x()}, {pos.y()}), width={width}")
        print(f"[NotesWidget] Before setFixedWidth: geometry={self.geometry()}")
        
        self.setFixedWidth(width)
        print(f"[NotesWidget] After setFixedWidth: geometry={self.geometry()}")
        
        self.move(pos)
        print(f"[NotesWidget] After move: geometry={self.geometry()}, pos={self.pos()}")
        
        # Load note content
        self._note = Note.get_global_note()
        self.text_edit.blockSignals(True)  # Prevent triggering save on load
        self.text_edit.setPlainText(self._note.content)
        self.text_edit.blockSignals(False)
        self._update_save_status('saved')
        
        # Adjust height based on loaded content
        self._adjust_height()
        print(f"[NotesWidget] After _adjust_height: geometry={self.geometry()}, height={self.height()}")
        
        self.show()
        print(f"[NotesWidget] After show (before re-position): geometry={self.geometry()}, pos={self.pos()}")
        
        # Re-apply position after show() to fix first-show positioning issue
        # Qt may adjust position on first show, so we force it back
        self.move(pos)
        print(f"[NotesWidget] After re-position: geometry={self.geometry()}, pos={self.pos()}")
        
        self.raise_()
        self.activateWindow()
        self.text_edit.setFocus()

    def _on_text_changed(self):
        """Handle text changes - start debounce timer and adjust height"""
        # Cancel existing timer
        self._save_timer.stop()
        
        # Update status to indicate unsaved changes
        self._update_save_status('saving')
        
        # Start new timer (500ms debounce)
        self._save_timer.start(500)
        
        # Adjust height based on content
        self._adjust_height()

    def _save_content(self):
        """Save the note content to database"""
        if self._note is None:
            return
        
        try:
            content = self.text_edit.toPlainText()
            self._note.update_content(content)
            self._update_save_status('saved')
        except Exception as e:
            self._update_save_status('error', str(e))

    def _adjust_height(self):
        """Adjust widget height based on text content"""
        # Get content height from document
        doc = self.text_edit.document()
        content_height = doc.size().height()
        
        # Add padding for header and margins (header ~30px + margins ~12px)
        total_height = int(content_height + 42)
        
        # Clamp between min and max
        new_height = max(self.MIN_HEIGHT, min(total_height, self.MAX_HEIGHT))
        
        print(f"[NotesWidget] _adjust_height: content_height={content_height}, total_height={total_height}, new_height={new_height}")
        
        # Update height
        old_height = self.height()
        self.setFixedHeight(new_height)
        print(f"[NotesWidget] Height changed: {old_height} -> {self.height()}, pos={self.pos()}")

    def _update_save_status(self, status: str, error_msg: str = ''):
        """
        Update the save status indicator.
        
        Args:
            status: One of 'saved', 'saving', 'error'
            error_msg: Error message if status is 'error'
        """
        if status == 'saved':
            self.save_status_label.setText("✓")
            self.save_status_label.setStyleSheet("""
                QLabel {
                    color: rgb(34, 139, 34);
                    font-size: 14px;
                }
            """)
            self.save_status_label.setToolTip("Saved")
        elif status == 'saving':
            self.save_status_label.setText("⏳")
            self.save_status_label.setStyleSheet("""
                QLabel {
                    color: rgb(218, 165, 32);
                    font-size: 14px;
                }
            """)
            self.save_status_label.setToolTip("Saving...")
        elif status == 'error':
            self.save_status_label.setText("✗")
            self.save_status_label.setStyleSheet("""
                QLabel {
                    color: rgb(220, 20, 60);
                    font-size: 14px;
                }
            """)
            self.save_status_label.setToolTip(f"Error: {error_msg}")

    def focusOutEvent(self, event):
        """Handle focus loss - immediately save"""
        # Cancel debounce timer
        self._save_timer.stop()
        
        # Save immediately
        self._save_content()
        
        super().focusOutEvent(event)

    def closeEvent(self, event):
        """Handle close event - save before closing"""
        # Cancel debounce timer
        self._save_timer.stop()
        
        # Save immediately
        self._save_content()
        
        self.closed.emit()
        super().closeEvent(event)
