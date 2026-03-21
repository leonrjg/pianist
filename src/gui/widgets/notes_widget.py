"""
Notes Widget - Notepad that appears below piano window.

Displays a text editor for taking notes with auto-save functionality.
"""

from PyQt6.QtWidgets import QWidget, QTextEdit, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QComboBox
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QIcon, QKeyEvent, QTextBlockFormat, QTextCursor

from core.notes.service import NoteService


def _t():
    from gui.themes.manager import ThemeManager
    return ThemeManager.get_instance().current


def _c():
    from gui.constants import piano_colors
    return piano_colors()



class AutoIndentTextEdit(QTextEdit):
    """QTextEdit with auto-indent support for tab characters"""

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events with auto-indent for tabs"""
        # Check if Enter/Return was pressed
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()

            # Get the current line text
            cursor.select(cursor.SelectionType.LineUnderCursor)
            line_text = cursor.selectedText()

            # Count leading tabs
            tab_count = 0
            for char in line_text:
                if char == '\t':
                    tab_count += 1
                else:
                    break

            # Check if line has tabs
            if tab_count > 0:
                # Check if line contains only tabs (no other content)
                if line_text.strip() == '':
                    # Empty indented line - remove tabs and insert plain newline
                    cursor.movePosition(cursor.MoveOperation.StartOfLine)
                    cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
                    cursor.removeSelectedText()
                    cursor.insertText('\n')
                    self.setTextCursor(cursor)
                    return
                else:
                    # Line has content - insert newline with same indentation
                    cursor.clearSelection()
                    cursor.movePosition(cursor.MoveOperation.EndOfLine)
                    cursor.insertText('\n' + '\t' * tab_count)
                    self.setTextCursor(cursor)
                    return

        # Default behavior for all other keys
        super().keyPressEvent(event)


class NotesWidget(QWidget):
    """Notepad widget that appears below the piano window"""

    closed = pyqtSignal()
    
    # Height bounds
    MIN_HEIGHT = 100   # ~3 lines of text
    MAX_HEIGHT = 300  # Maximum height

    def __init__(self, parent=None):
        super().__init__(parent)
        # Use Window flag but maintain parent relationship for proper lifecycle management
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Track if notes were visible before parent state change
        self._was_visible_before_hide = False
        
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

        # Header with habit selector, save indicator, and close button
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 4)
        header.setSpacing(8)

        # Habit selector dropdown
        self.habit_selector = QComboBox()
        self.habit_selector.setCursor(Qt.CursorShape.PointingHandCursor)
        self.habit_selector.setMaximumWidth(150)
        self.habit_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.habit_selector.currentIndexChanged.connect(self._on_habit_changed)
        t = _t()
        c = _c()
        self.habit_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {c.ACCENT.name()};
                border-radius: 3px;
                color: {c.ACCENT_LIGHT.name()};
                font-size: 11px;
                padding: 1px 4px;
                padding-right: 4px;
            }}
            QComboBox:hover {{
                border-color: {c.ACCENT_LIGHT.name()};
                background-color: {c.FRAME_MEDIUM.name()};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {c.ACCENT.name()};
                color: {c.ACCENT_LIGHT.name()};
                selection-background-color: {c.FRAME_MEDIUM.name()};
                selection-color: {c.ACCENT_LIGHT.name()};
                padding: 2px;
            }}
        """)
        header.addWidget(self.habit_selector)

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
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {c.ACCENT.name()};
                border-radius: 10px;
                color: {c.ACCENT_LIGHT.name()};
                font-size: 16px;
                font-weight: bold;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                border-color: {c.ACCENT_LIGHT.name()};
                background-color: {c.FRAME_MEDIUM.name()};
            }}
        """)
        header.addWidget(close_button)

        main_layout.addLayout(header)

        # Text editor with auto-indent
        self.text_edit = AutoIndentTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setPlaceholderText("What are you doing now?")
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.setTabStopDistance(10)  # Reduce tab width from default ~80px to 30px

        # Set line height for better readability
        block_format = QTextBlockFormat()
        block_format.setLineHeight(140, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setBlockFormat(block_format)

        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {c.FRAME_MEDIUM.name()};
                color: {c.WHITE_KEY.name()};
                border: none;
                padding: 8px;
                font-size: 12px;
                selection-background-color: {c.ACCENT.name()};
                selection-color: {c.BACKGROUND.name()};
            }}
            QScrollBar:vertical {{
                background-color: {c.FRAME_DARK.name()};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {c.ACCENT.name()};
                border-radius: 3px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {c.ACCENT_LIGHT.name()};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        main_layout.addWidget(self.text_edit)

    def _populate_habit_selector(self):
        """Populate the habit selector dropdown with available habits"""
        # Block signals to prevent triggering _on_habit_changed during population
        self.habit_selector.blockSignals(True)

        # Clear existing items
        self.habit_selector.clear()

        # Add "Default note" option (global note with habit = None)
        self.habit_selector.addItem("Default note", userData=None)

        # Add all non-archived habits via service
        _service = getattr(self.parent(), 'service', None)
        habits = sorted(_service.get_all_habits(), key=lambda h: h.name) if _service else []
        for habit in habits:
            self.habit_selector.addItem(habit.name, userData=habit.id)

        # Re-enable signals
        self.habit_selector.blockSignals(False)

    def _load_selected_note(self):
        """Load the note for the currently selected habit"""
        # Get the selected habit ID from the dropdown
        habit_id = self.habit_selector.currentData()

        # Load the appropriate note
        if habit_id is None:
            self._note = NoteService.get_global_note()
        else:
            _service = getattr(self.parent(), 'service', None)
            habit = _service.get_habit_by_id(habit_id) if _service else None
            self._note = NoteService.get_habit_note(habit) if habit else NoteService.get_global_note()

        # Update text editor without triggering save
        self.text_edit.blockSignals(True)
        self.text_edit.setPlainText(self._note.content)
        self.text_edit.blockSignals(False)
        self._update_save_status('saved')

    def _on_habit_changed(self, index: int):
        """Handle habit selection change in dropdown"""
        # Save current note before switching
        if self._note is not None:
            self._save_timer.stop()
            self._save_content()

        # Load the new note
        self._load_selected_note()

        # Adjust height for new content
        self._adjust_height()

    def paintEvent(self, event):
        """Draw simple background without border"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw simple rectangle background (no border, no rounded corners)
        c = _c()
        bg = QColor(c.FRAME_DARK)
        bg.setAlpha(240)
        painter.fillRect(self.rect(), bg)

    def show_at_position(self, pos: QPoint, width: int):
        """
        Show the notes widget at the specified position with given width.

        Args:
            pos: Position to show the widget at
            width: Width of the widget (should match piano window)
        """
        self.setFixedWidth(width)
        self.move(pos)

        # Populate habit selector
        self._populate_habit_selector()

        # Auto-select habit if exactly one session is running
        if self.parent() and hasattr(self.parent(), 'session_manager'):
            active_habit_ids = list(self.parent().session_manager._processes.keys())
            if len(active_habit_ids) == 1:
                active_habit_id = active_habit_ids[0]
                # Find and select this habit in the dropdown
                for i in range(self.habit_selector.count()):
                    if self.habit_selector.itemData(i) == active_habit_id:
                        self.habit_selector.setCurrentIndex(i)
                        break

        # Load note content for the selected habit (defaults to global note)
        self._load_selected_note()

        # Adjust height based on loaded content
        self._adjust_height()

        self.show()

        # Re-apply position after show() to fix first-show positioning issue
        # Qt may adjust position on first show, so we force it back
        self.move(pos)

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
            if content and content.strip():
                self._note.update_content(content)
                self._update_save_status('saved')
        except Exception as e:
            self._update_save_status('error', str(e))

    def _adjust_height(self):
        """Adjust widget height based on text content"""
        # Get content height from document
        doc = self.text_edit.document()
        
        # Force document to calculate layout based on text edit width
        # This ensures proper height calculation even on first show
        doc.setTextWidth(self.text_edit.viewport().width())
        
        content_height = doc.size().height()
        
        # Add padding for header and margins (header ~30px + margins ~12px)
        total_height = int(content_height + 42)
        
        # Clamp between min and max
        new_height = max(self.MIN_HEIGHT, min(total_height, self.MAX_HEIGHT))

        # Update height
        old_height = self.height()
        self.setFixedHeight(new_height)

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
            self.save_status_label.setStyleSheet(f"""
                QLabel {{
                    color: {_c().ACCENT_LIGHT.name()};
                    font-size: 14px;
                }}
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

    def changeEvent(self, event):
        """Handle window state changes - synchronize with parent window"""
        if event.type() == event.Type.WindowStateChange:
            # If parent window minimizes/hides, hide notes
            if self.parent() and hasattr(self.parent(), 'isMinimized'):
                if self.parent().isMinimized() and self.isVisible():
                    self._was_visible_before_hide = True
                    self.hide()
                elif not self.parent().isMinimized() and self._was_visible_before_hide:
                    self._was_visible_before_hide = False
                    self.show()
        
        super().changeEvent(event)

    def closeEvent(self, event):
        """Handle close event - save before closing"""
        # Cancel debounce timer
        self._save_timer.stop()
        
        # Save immediately
        self._save_content()
        
        self.closed.emit()
        super().closeEvent(event)
