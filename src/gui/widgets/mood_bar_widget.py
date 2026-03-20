"""
Mood Bar Widget - Floating mood selector bar.

Displays available moods as clickable emoji buttons with tooltips.
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor, QPainterPath

from core.mood.service import MoodService
from core.mood.mood import Mood
from ..constants import PianoColors


class MoodBarWidget(QWidget):
    """Floating bar for selecting moods"""

    mood_selected = pyqtSignal(int)  # Emits mood_id
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._load_moods()

    def _setup_ui(self):
        """Setup the UI layout"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        self.setLayout(layout)

    def _load_moods(self):
        """Load moods from database and create buttons"""
        layout = self.layout()
        
        # Clear existing buttons
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Create button for each mood
        moods = MoodService.get_all()
        for mood in moods:
            btn = QPushButton(mood.symbol)
            btn.setFixedSize(32, 32)
            btn.setToolTip(mood.description)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(92, 61, 46, 200);
                    border: 1px solid rgb(184, 134, 11);
                    border-radius: 4px;
                    font-size: 16px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: rgba(122, 80, 64, 220);
                    border-color: rgb(218, 165, 32);
                }
                QPushButton:pressed {
                    background-color: rgba(61, 40, 23, 200);
                }
            """)
            btn.clicked.connect(lambda checked, m=mood: self._on_mood_clicked(m))
            layout.addWidget(btn)

    def _on_mood_clicked(self, mood: Mood):
        """Handle mood button click"""
        MoodService.log_mood(mood)
        self.mood_selected.emit(mood.id)
        self.close()

    def paintEvent(self, event):
        """Draw rounded background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded rectangle background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 6, 6)
        
        painter.fillPath(path, QColor(61, 40, 23, 230))
        painter.setPen(QColor(184, 134, 11))
        painter.drawPath(path)

    def show_at_position(self, pos: QPoint):
        """Show the mood bar at the specified position"""
        self.move(pos)
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        """Handle close event"""
        self.closed.emit()
        super().closeEvent(event)
