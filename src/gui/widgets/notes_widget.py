"""
Notes Widget - Notepad that appears below piano window.

Displays a text editor for taking notes with auto-save functionality.
"""

import logging

from PyQt6.QtWidgets import (
    QWidget,
    QTextEdit,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QEvent, QPropertyAnimation, QEasingCurve, QMimeData
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QKeyEvent,
    QFont,
    QTextCharFormat,
    QTextCursor,
)

from core.notes.service import NoteService
from core.settings.service import SettingsService

from gui.widgets.notes_markdown import (
    BOLD_WEIGHT,
    CODE_PROPERTY,
    apply_markdown,
    document_to_markdown,
    fragment_to_markdown,
)

from gui.themes import current_theme as _t, ThemedWidget
from gui.painters.frame_painter import FramePainter
from gui.painters.base_painter import BasePainter


def _c():
    from gui.constants import piano_colors
    return piano_colors()


logger = logging.getLogger(__name__)



class AutoIndentTextEdit(QTextEdit):
    """QTextEdit with auto-indent, inline Markdown formatting, and Markdown copy.

    Styling is limited to inline character formats (bold/italic/code/strike/underline).
    The note's canonical form is Markdown; see ``notes_markdown`` for the
    document<->Markdown mapping that this editor's load/save/copy go through.
    """

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events with formatting shortcuts and tab auto-indent"""
        # Formatting shortcuts. Ctrl+B / Ctrl+I are required; they route through
        # the same toggles as the toolbar so button state stays in sync.
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_B:
                self.toggle_bold()
                return
            if event.key() == Qt.Key.Key_I:
                self.toggle_italic()
                return
            if event.key() == Qt.Key.Key_U:
                self.toggle_underline()
                return

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

    # ----- Inline formatting -------------------------------------------------

    def _merge_format(self, fmt: QTextCharFormat):
        """Apply a char format to the selection and to subsequent typing."""
        cursor = self.textCursor()
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        self.mergeCurrentCharFormat(fmt)

    def toggle_bold(self):
        c = _c()
        is_bold = self.currentCharFormat().fontWeight() > QFont.Weight.Normal
        fmt = QTextCharFormat()
        if is_bold:
            fmt.setFontWeight(QFont.Weight.Normal)
            # Restore the body text color so un-bolded runs match plain text.
            fmt.setForeground(c.WHITE_KEY)
        else:
            fmt.setFontWeight(BOLD_WEIGHT)
            # Color carries the emphasis: the body font has no heavier face.
            fmt.setForeground(c.ACCENT_LIGHT)
        self._merge_format(fmt)

    def toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(not self.currentCharFormat().fontItalic())
        self._merge_format(fmt)

    def toggle_strike(self):
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut())
        self._merge_format(fmt)

    def toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(not self.currentCharFormat().fontUnderline())
        self._merge_format(fmt)

    def toggle_code(self):
        is_code = self.currentCharFormat().boolProperty(CODE_PROPERTY)
        fmt = QTextCharFormat()
        if is_code:
            fmt.setProperty(CODE_PROPERTY, False)
            fmt.setFontFixedPitch(False)
            fmt.setFontFamilies([self.font().family()])
        else:
            fmt.setProperty(CODE_PROPERTY, True)
            fmt.setFontFixedPitch(True)
            fmt.setFontFamilies(["monospace"])
        self._merge_format(fmt)

    # ----- Clipboard ---------------------------------------------------------

    def insertFromMimeData(self, source: QMimeData):
        """Paste as plain, unformatted text at the document's default style."""
        if source.hasText():
            cursor = self.textCursor()
            cursor.insertText(source.text(), QTextCharFormat())

    def createMimeDataFromSelection(self) -> QMimeData:
        """Copy the selection as Markdown so inline styling is preserved."""
        data = QMimeData()
        cursor = self.textCursor()
        if cursor.hasSelection():
            data.setText(fragment_to_markdown(cursor.selection()))
        return data


class NotesWidget(QWidget, ThemedWidget):
    """Notepad widget that appears below the piano window"""

    closed = pyqtSignal()
    
    # Height bounds
    MIN_HEIGHT = 100   # ~3 lines of text
    AUTO_MAX_HEIGHT = 300  # Maximum automatic content-driven height
    MAX_HEIGHT = 700  # Maximum height
    RESIZE_MARGIN = 8
    NOTE_RESULTS_MAX_HEIGHT = 180
    # Extra vertical gap above each paragraph (actual line break), not between
    # wrapped lines within a paragraph.
    BLOCK_SPACING = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Track if notes were visible before parent state change
        self._was_visible_before_hide = False
        self._is_resizing_height = False
        self._resize_start_y = 0
        self._resize_start_height = 0
        self._user_resized_height = False
        
        # Dynamic height between min and max
        self.setMinimumHeight(self.MIN_HEIGHT)
        self.setMaximumHeight(self.MAX_HEIGHT)
        self.setMouseTracking(True)
        
        if parent is not None:
            parent.installEventFilter(self)

        self._fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._fade_animation.finished.connect(self._on_fade_finished)

        SettingsService.signals.changed.connect(self._on_setting_changed)

        # Auto-save state
        self._note = None
        self._note_items = []
        self._selected_note_data = None
        self._updating_note_search = False
        self._notepad_show_all = False
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

        # Header with searchable note selector and controls
        header = QHBoxLayout()
        header.setContentsMargins(2, 0, 2, 4)
        header.setSpacing(8)

        self.note_search = QLineEdit()
        self.note_search.setMaximumWidth(240)
        self.note_search.setPlaceholderText("Search notes")
        self.note_search.setClearButtonEnabled(True)
        self.note_search.textChanged.connect(self._on_note_search_changed)
        self.note_search.installEventFilter(self)
        header.addWidget(self.note_search)

        self._add_note_button = QPushButton("+")
        self._add_note_button.setFixedSize(26, 24)
        self._add_note_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_note_button.setToolTip("Add note")
        self._add_note_button.clicked.connect(self._on_add_note_clicked)
        header.addWidget(self._add_note_button)

        self._rename_note_button = QPushButton("✎")
        self._rename_note_button.setFixedSize(26, 24)
        self._rename_note_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._rename_note_button.setToolTip("Edit note")
        self._rename_note_button.clicked.connect(self._on_edit_note_clicked)
        header.addWidget(self._rename_note_button)

        header.addStretch()

        main_layout.addLayout(header)

        # Compact inline-formatting toolbar on its own row.
        format_bar = QHBoxLayout()
        format_bar.setContentsMargins(2, 0, 2, 4)
        format_bar.setSpacing(4)

        self._format_buttons = {}
        for key, label, tooltip in (
            ('bold', 'B', 'Bold (Ctrl+B)'),
            ('italic', 'I', 'Italic (Ctrl+I)'),
            ('underline', 'U', 'Underline (Ctrl+U)'),
            ('code', '<>', 'Code'),
            ('strike', 'S', 'Strikethrough'),
        ):
            button = self._make_format_button(key, label, tooltip)
            self._format_buttons[key] = button
            format_bar.addWidget(button)

        format_bar.addStretch()

        main_layout.addLayout(format_bar)

        self._note_results = QListWidget()
        self._note_results.setMaximumHeight(self.NOTE_RESULTS_MAX_HEIGHT)
        self._note_results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._note_results.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self._note_results.itemClicked.connect(self._on_note_result_clicked)
        self._note_results.installEventFilter(self)
        self._note_results.hide()
        main_layout.addWidget(self._note_results)

        # Text editor with auto-indent. Rich text is enabled so inline styling
        # works; paste is still flattened (insertFromMimeData) so external
        # formatting never leaks in.
        self.text_edit = AutoIndentTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("What are you doing now?")
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.currentCharFormatChanged.connect(self._update_format_buttons)
        self.text_edit.setTabStopDistance(10)  # Reduce tab width from default ~80px to 30px
        self.text_edit.setMouseTracking(True)
        self.text_edit.installEventFilter(self)

        main_layout.addWidget(self.text_edit)

        self._resize_handle = QFrame()
        self._resize_handle.setFixedHeight(6)
        self._resize_handle.setCursor(Qt.CursorShape.SizeVerCursor)
        self._resize_handle.installEventFilter(self)
        main_layout.addWidget(self._resize_handle)

        self._setup_style()

    def _make_format_button(self, key: str, label: str, tooltip: str) -> QPushButton:
        """Create a compact, checkable inline-formatting toolbar button."""
        button = QPushButton(label)
        button.setFixedSize(20, 20)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tooltip)
        # Keep focus (and thus the selection) in the editor when toggling.
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda _checked, k=key: self._toggle_format(k))
        return button

    def _toggle_format(self, key: str):
        """Route a toolbar button to the matching editor toggle."""
        getattr(self.text_edit, f"toggle_{key}")()

    def _update_format_buttons(self, fmt: QTextCharFormat):
        """Reflect the caret's current inline styling in the toolbar buttons."""
        state = {
            'bold': fmt.fontWeight() > QFont.Weight.Normal,
            'italic': fmt.fontItalic(),
            'underline': fmt.fontUnderline(),
            'code': fmt.boolProperty(CODE_PROPERTY),
            'strike': fmt.fontStrikeOut(),
        }
        for key, button in self._format_buttons.items():
            button.setChecked(state[key])

    def is_on_resize_handle(self, pos: QPoint) -> bool:
        """Return True when a point is in the bottom resize strip."""
        return pos.y() >= self.height() - self.RESIZE_MARGIN

    def is_resizing_height(self) -> bool:
        """Return True while the user is dragging the vertical resize edge."""
        return self._is_resizing_height

    def _set_resize_cursor_for_position(self, pos: QPoint):
        if self.is_on_resize_handle(pos):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        """Start vertical resizing from the bottom edge."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_on_resize_handle(event.position().toPoint()):
            self._start_height_resize(event.globalPosition().toPoint().y())
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Resize vertically while dragging the bottom edge."""
        if self._is_resizing_height:
            self._resize_height_to(event.globalPosition().toPoint().y())
            event.accept()
            return

        self._set_resize_cursor_for_position(event.position().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Finish vertical resizing."""
        if event.button() == Qt.MouseButton.LeftButton and self._is_resizing_height:
            self._finish_height_resize(event.position().toPoint())
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_height_resize(self, global_y: int):
        self._is_resizing_height = True
        self._resize_start_y = global_y
        self._resize_start_height = self.height()
        self._user_resized_height = True

    def _resize_height_to(self, global_y: int):
        dy = global_y - self._resize_start_y
        new_height = max(self.MIN_HEIGHT, min(self._resize_start_height + dy, self.MAX_HEIGHT))
        self.resize(self.width(), new_height)

    def _finish_height_resize(self, pos: QPoint):
        self._is_resizing_height = False
        self._set_resize_cursor_for_position(pos)

    def _setup_style(self):
        c = _c()
        self.note_search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {c.FRAME_MEDIUM.name()};
                color: {c.ACCENT_LIGHT.name()};
                border: 1px solid {c.ACCENT.name()};
                border-radius: 3px;
                text-align: left;
                padding: 2px 4px;
                font-size: 11px;
                selection-background-color: {c.ACCENT.name()};
                selection-color: {c.BACKGROUND.name()};
            }}
            QLineEdit:focus {{
                color: {c.WHITE_KEY.name()};
                border-color: {c.ACCENT_LIGHT.name()};
            }}
        """)
        self._note_results.setStyleSheet(f"""
            QListWidget {{
                background-color: {c.FRAME_DARK.name()};
                color: {c.ACCENT_LIGHT.name()};
                border: 1px solid {c.ACCENT.name()};
                font-size: 11px;
            }}
            QListWidget::item {{
                padding: 4px 6px;
            }}
            QListWidget::item:selected {{
                background-color: {c.ACCENT.name()};
                color: {c.BACKGROUND.name()};
            }}
        """)
        note_button_style = f"""
            QPushButton {{
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {c.ACCENT.name()};
                border-radius: 3px;
                color: {c.ACCENT_LIGHT.name()};
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                border-color: {c.ACCENT_LIGHT.name()};
                background-color: {c.FRAME_MEDIUM.name()};
            }}
        """
        self._add_note_button.setStyleSheet(note_button_style)
        self._rename_note_button.setStyleSheet(note_button_style)
        format_button_style = f"""
            QPushButton {{
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {c.ACCENT.name()};
                border-radius: 3px;
                color: {c.ACCENT_LIGHT.name()};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border-color: {c.ACCENT_LIGHT.name()};
                background-color: {c.FRAME_MEDIUM.name()};
            }}
            QPushButton:checked {{
                background-color: {c.ACCENT.name()};
                color: {c.BACKGROUND.name()};
                border-color: {c.ACCENT_LIGHT.name()};
            }}
        """
        for key, button in self._format_buttons.items():
            font = button.font()
            font.setItalic(key == 'italic')
            font.setStrikeOut(key == 'strike')
            font.setUnderline(key == 'underline')
            button.setFont(font)
            button.setStyleSheet(format_button_style)
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
        self._resize_handle.setStyleSheet(f"""
            QFrame {{
                background-color: {c.FRAME_MEDIUM.name()};
                border-top: 1px solid {c.ACCENT.name()};
            }}
            QFrame:hover {{
                border-top-color: {c.ACCENT_LIGHT.name()};
            }}
        """)

    def _populate_note_selector(self, default_note_id=None):
        """Populate the searchable note selector with available notes."""
        _service = getattr(self.parent(), 'service', None)
        habits = sorted(_service.get_all_habits(), key=lambda h: h.name) if _service else []
        items = []

        for note in NoteService.list_global_notes() or [NoteService.get_global_note()]:
            items.append((note.title, {'habit_id': None, 'note_id': note.id}))

        for habit in habits:
            notes = NoteService.list_habit_notes(habit)
            if not notes:
                notes = [NoteService.get_habit_note(habit)]

            for note in notes:
                items.append((f"{note.title} / {habit.name}", {'habit_id': habit.id, 'note_id': note.id}))

        if not items:
            note = NoteService.get_global_note()
            items.append((note.title, {'habit_id': None, 'note_id': note.id}))

        self._note_items = items
        selected_data = self._selector_data_for_note(default_note_id) or (items[0][1] if items else None)
        selected_label = self._label_for_note_data(selected_data)
        self._set_selected_note(selected_label, selected_data, load=False)

    def _selector_data_for_note(self, note_id):
        if note_id is None:
            return None
        return next((data for _, data in self._note_items if data['note_id'] == note_id), None)

    def _label_for_note_data(self, data):
        if data is None:
            return ''
        return next((label for label, item_data in self._note_items if item_data == data), '')

    def _filtered_note_items(self):
        query = self.note_search.text().strip().lower()
        if not query or self._updating_note_search:
            if self._notepad_show_all:
                return self._note_items
            return self._current_scope_note_items()
        return [(label, data) for label, data in self._note_items if query in label.lower()]

    def _current_scope_note_items(self):
        """Notes belonging to the currently selected note's habit (or the
        global notes when no habit is selected), plus a trailing "..." entry
        to expand to the full note list when there's more to show."""
        habit_id = (self._selected_note_data or {}).get('habit_id')
        scoped = [(label, data) for label, data in self._note_items if data['habit_id'] == habit_id]
        if len(scoped) < len(self._note_items):
            scoped = scoped + [("...", {'show_all': True})]
        return scoped

    def _show_note_results(self):
        if not self._note_results.isVisible():
            self._notepad_show_all = False
        self._refresh_note_results()
        self._note_results.show()
        self._adjust_height()

    def _hide_note_results(self):
        was_visible = self._note_results.isVisible()
        self._note_results.hide()
        if was_visible:
            self._adjust_height()

    def _refresh_note_results(self):
        self._note_results.clear()
        filtered_items = self._filtered_note_items()

        if filtered_items:
            for label, data in filtered_items:
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, data)
                self._note_results.addItem(item)
            self._note_results.setCurrentRow(0)
        else:
            item = QListWidgetItem("No notes")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._note_results.addItem(item)

        row_height = self._note_results.sizeHintForRow(0)
        if row_height <= 0:
            row_height = 24
        height = min(row_height * self._note_results.count() + 4, self.NOTE_RESULTS_MAX_HEIGHT)
        self._note_results.setFixedHeight(max(row_height + 4, height))

    def _set_selected_note(self, label: str, data, load: bool = True):
        self._selected_note_data = data
        self._updating_note_search = True
        self.note_search.clear()
        self.note_search.setPlaceholderText(label or "Search notes")
        self.note_search.setCursorPosition(0)
        self._updating_note_search = False
        if load:
            self._on_note_changed()

    def _load_selected_note(self):
        """Load the currently selected note."""
        selected_data = self._selected_note_data or {}
        note_id = selected_data.get('note_id')
        self._note = NoteService.get_note_by_id(note_id) if note_id else NoteService.get_global_note()

        # Update text editor without triggering save. Content is Markdown,
        # which rebuilds the document.
        self.text_edit.blockSignals(True)
        apply_markdown(self.text_edit.document(), self._note.content or "", bold_color=_c().ACCENT_LIGHT,
                       block_spacing=self.BLOCK_SPACING)
        self.text_edit.blockSignals(False)

    def _on_note_selected(self, label: str, data):
        """Handle note selection from the search results."""
        self._hide_note_results()
        self._set_selected_note(label, data)

    def _on_note_result_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data is None:
            return
        if data.get('show_all'):
            self._notepad_show_all = True
            self._refresh_note_results()
            return
        self._on_note_selected(item.text(), data)

    def _on_note_search_changed(self, text: str):
        """Filter the note result list as the user types."""
        if self._updating_note_search:
            return
        self._show_note_results()

    def _select_first_filtered_note(self) -> bool:
        filtered_items = self._filtered_note_items()
        if not filtered_items:
            return False
        label, data = filtered_items[0]
        self._on_note_selected(label, data)
        return True

    def _on_note_changed(self):
        """Handle note selection change."""
        # Save current note before switching
        if self._note is not None:
            self._save_timer.stop()
            self._save_content()

        # Load the new note
        self._load_selected_note()

        # Adjust height for new content
        self._adjust_height()

    def _on_add_note_clicked(self):
        """Create a named note in the selected scope."""
        if self._note is not None:
            self._save_timer.stop()
            self._save_content()

        selected_data = self._selected_note_data or {}
        habit_id = selected_data.get('habit_id')

        title, accepted = QInputDialog.getText(self, "New note", "Name")
        if not accepted:
            return

        title = title.strip()
        if not title:
            title = None

        try:
            if habit_id is None:
                note = NoteService.create_global_note(title=title)
            else:
                _service = getattr(self.parent(), 'service', None)
                habit = _service.get_habit_by_id(habit_id) if _service else None
                note = NoteService.create_habit_note(habit, title=title) if habit else NoteService.create_global_note(title=title)

            self._populate_note_selector(default_note_id=note.id)
            self._load_selected_note()
            self._user_resized_height = False
            self._adjust_height()
            self.text_edit.setFocus()
        except Exception:
            logger.exception("Failed to create note")

    def _on_edit_note_clicked(self):
        """Show a menu to rename or delete the currently selected note."""
        if self._note is None:
            return

        menu = QMenu(self)
        menu.addAction("Rename", self._on_rename_note_clicked)
        menu.addAction("Delete", self._on_delete_note_clicked)
        pos = self._rename_note_button.mapToGlobal(self._rename_note_button.rect().bottomLeft())
        menu.exec(pos)

    def _on_rename_note_clicked(self):
        """Rename the currently selected note."""
        if self._note is None:
            return

        title, accepted = QInputDialog.getText(self, "Rename note", "Name", text=self._note.title)
        if not accepted:
            return

        title = title.strip()
        if not title or title == self._note.title:
            return

        try:
            NoteService.rename_note(self._note, title)
            self._populate_note_selector(default_note_id=self._note.id)
        except Exception:
            logger.exception("Failed to rename note")

    def _on_delete_note_clicked(self):
        """Delete the currently selected note, after confirmation."""
        if self._note is None:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete '{self._note.title}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Drop any pending debounced save so it can't land on the note we
        # switch to next (see _load_selected_note).
        self._save_timer.stop()

        habit_id = self._note.habit_id

        try:
            NoteService.delete_note(self._note)
            self._note = None

            # Fall back to this habit's default note (not the overall
            # default note) when the deleted note belonged to a habit.
            fallback_note_id = None
            if habit_id is not None:
                _service = getattr(self.parent(), 'service', None)
                habit = _service.get_habit_by_id(habit_id) if _service else None
                if habit:
                    fallback_note_id = NoteService.get_habit_note(habit).id

            self._populate_note_selector(default_note_id=fallback_note_id)
            self._load_selected_note()
            self._user_resized_height = False
            self._adjust_height()
            self.text_edit.setFocus()
        except Exception:
            logger.exception("Failed to delete note")

    def paintEvent(self, event):
        """Draw background matching the piano frame style (gradient + SVG overlay)"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        t = _t()
        r = self.rect()
        gradient = (t.fallboard_gradient if t else ())
        if gradient:
            stops = [(1.0 - pos, color) for pos, color in FramePainter._parse_gradient_stops(gradient)]
            BasePainter.draw_gradient_rect_stops(
                painter, r.x(), r.y(), r.right(), r.bottom(), stops, vertical=True
            )
        else:
            c = _c()
            bg = QColor(c.FRAME_DARK)
            bg.setAlpha(240)
            painter.fillRect(r, bg)

        if t and t.frame_svg:
            BasePainter.draw_image_overlay(painter, r.x(), r.y(), r.width(), r.height(), t.frame_svg, t.frame_svg_opacity)

    def show_at_position(self, pos: QPoint, width: int, note_id=None):
        """
        Show the notes widget at the specified position with given width.

        Args:
            pos: Position to show the widget at
            width: Width of the widget (should match piano window)
            note_id: If given, selects this note instead of auto-selecting one
        """
        self.setFixedWidth(width)
        self.move(pos)

        default_note_id = note_id
        if default_note_id is None:
            # Auto-select habit if exactly one session is running
            if self.parent() and hasattr(self.parent(), 'session_manager'):
                active_habit_ids = list(self.parent().session_manager._processes.keys())
                if len(active_habit_ids) == 1:
                    _service = getattr(self.parent(), 'service', None)
                    habit = _service.get_habit_by_id(active_habit_ids[0]) if _service else None
                    if habit:
                        default_note_id = NoteService.get_habit_note(habit).id

        # Populate note selector
        self._populate_note_selector(default_note_id=default_note_id)

        # Load note content for the selected habit (defaults to global note)
        self._load_selected_note()

        # Adjust height based on loaded content
        self._user_resized_height = False
        self._adjust_height()

        self.setWindowOpacity(SettingsService.get('window.opacity', 1.0))
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
        
        # Start new timer (500ms debounce)
        self._save_timer.start(500)
        
        # Adjust height based on content
        self._adjust_height()

    def _save_content(self):
        """Save the note content to database"""
        if self._note is None:
            return
        
        try:
            # Persist the canonical Markdown, not the rendered plain text, so
            # inline styling survives a reload.
            content = document_to_markdown(self.text_edit.document())
            if content and content.strip():
                self._note.update_content(content)
        except Exception as e:
            logger.exception("Failed to save note")

    def _adjust_height(self):
        """Adjust widget height based on text content"""
        if self._user_resized_height and not self._note_results.isVisible():
            return

        # Get content height from document
        doc = self.text_edit.document()

        # Force document to calculate layout based on text edit width
        # This ensures proper height calculation even on first show
        doc.setTextWidth(self.text_edit.viewport().width())

        content_height = doc.size().height()

        # Add padding for the header row, the format toolbar row, and margins.
        result_height = self._note_results.height() + 4 if self._note_results.isVisible() else 0
        total_height = int(content_height + 66 + result_height)

        # Clamp automatic sizing so long saved notes open with scrolling.
        new_height = max(self.MIN_HEIGHT, min(total_height, self.AUTO_MAX_HEIGHT))

        if self._user_resized_height:
            new_height = max(self.height(), new_height)

        # Update height without preventing manual vertical resizing
        self.resize(self.width(), new_height)

    def focusOutEvent(self, event):
        """Handle focus loss - immediately save"""
        # Cancel debounce timer
        self._save_timer.stop()
        
        # Save immediately
        self._save_content()
        
        super().focusOutEvent(event)

    def eventFilter(self, obj, event):
        if obj == getattr(self, 'note_search', None):
            if event.type() in (QEvent.Type.FocusIn, QEvent.Type.MouseButtonPress):
                QTimer.singleShot(0, self._show_note_results)
                return False
            if event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self._hide_note_results_if_focus_left_selector)
                return False
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    return self._select_first_filtered_note()
                if event.key() == Qt.Key.Key_Down:
                    self._show_note_results()
                    self._note_results.setFocus()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._hide_note_results()
                    return True

        if obj == getattr(self, '_note_results', None):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    item = self._note_results.currentItem()
                    if item is not None:
                        self._on_note_result_clicked(item)
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self._hide_note_results()
                    self.note_search.setFocus()
                    return True
            if event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(0, self._hide_note_results_if_focus_left_selector)
                return False

        if obj == getattr(self, 'text_edit', None):
            if event.type() == QEvent.Type.FocusIn:
                self._hide_note_results()
                return False

        if obj == getattr(self, '_resize_handle', None):
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._start_height_resize(event.globalPosition().toPoint().y())
                return True
            if event.type() == QEvent.Type.MouseMove and self._is_resizing_height:
                self._resize_height_to(event.globalPosition().toPoint().y())
                return True
            if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._finish_height_resize(self.mapFromGlobal(event.globalPosition().toPoint()))
                return True

        if obj is self.parent():
            if event.type() == QEvent.Type.Hide and self.isVisible():
                self._was_visible_before_hide = True
                self._fade_animation.stop()
                self._fade_animation.setStartValue(self.windowOpacity())
                self._fade_animation.setEndValue(0.0)
                self._fade_animation.start()
            elif event.type() == QEvent.Type.Show and self._was_visible_before_hide:
                self._was_visible_before_hide = False
                self._fade_animation.stop()
                self.setWindowOpacity(0.0)
                self.show()
                self._fade_animation.setStartValue(0.0)
                self._fade_animation.setEndValue(SettingsService.get('window.opacity', 1.0))
                self._fade_animation.start()
            elif event.type() == QEvent.Type.WindowDeactivate:
                self._hide_note_results()
        return False

    def _hide_note_results_if_focus_left_selector(self):
        focused = self.focusWidget()
        if focused not in (self.note_search, self._note_results):
            self._hide_note_results()

    def _on_fade_finished(self):
        if self.windowOpacity() == 0.0:
            self.hide()
            self.setWindowOpacity(SettingsService.get('window.opacity', 1.0))

    def _on_setting_changed(self, key: str, value):
        if key == 'window.opacity':
            self.setWindowOpacity(float(value))

    def closeEvent(self, event):
        """Handle close event - save before closing"""
        # Cancel debounce timer
        self._save_timer.stop()
        
        # Save immediately
        self._save_content()
        
        self.closed.emit()
        super().closeEvent(event)
