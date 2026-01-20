"""
Custom desktop notification toast widget.

A frameless popup that slides in from the corner of the screen.
"""

import os

from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QProgressBar,
    QSizePolicy,
)
from PyQt6.QtCore import (
    Qt,
    QTimer,
    QPropertyAnimation,
    QEasingCurve,
    QPoint,
    QRectF,
    QElapsedTimer,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QPainterPath,
    QPixmap,
    QPalette,
    QLinearGradient,
)

from ..constants import PianoColors


class NotificationToast(QWidget):
    """
    Desktop notification toast with clean, modern styling.
    
    Appears as a popup in the bottom-right corner of the screen.
    """
    
    # Dimensions
    WIDTH = 320
    MIN_HEIGHT = 44
    MAX_HEIGHT = 300
    MARGIN = 30
    SHADOW_SIZE = 6
    BORDER_RADIUS = 12
    ICON_SIZE = 28
    
    # Colors
    BG_COLOR_TOP = PianoColors.WOOD_MEDIUM
    BG_COLOR_BOTTOM = PianoColors.WOOD_DARK
    BORDER_COLOR = QColor(60, 60, 65)
    TITLE_COLOR = QColor(255, 255, 255)
    MESSAGE_COLOR = QColor(220, 220, 225)
    ACCENT_COLOR = QColor(184, 134, 11)  # Subtle brass accent
    URGENT_COLOR = QColor(220, 80, 80)
    
    # Animation
    SLIDE_DURATION = 250
    PROGRESS_INTERVAL = 50
    
    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self._urgency = 'normal'
        self._duration = 12000
        self._icon_pixmap = None
        
        self._load_icon()
        self._setup_ui()
        self._setup_animations()
        
        # Auto-hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._start_hide_animation)

        # Progress tracking
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(self.PROGRESS_INTERVAL)
        self._progress_timer.timeout.connect(self._update_progress)
        self._elapsed_timer = QElapsedTimer()
        self._remaining_ms = 0
    
    def _load_icon(self):
        """Load the app icon."""
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'piano.png')
        if os.path.exists(icon_path):
            dpr = self.devicePixelRatioF()
            target_size = int(self.ICON_SIZE * dpr)
            pixmap = QPixmap(icon_path).scaled(
                target_size, target_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            pixmap.setDevicePixelRatio(dpr)
            self._icon_pixmap = pixmap
    
    def _setup_ui(self):
        """Set up the notification layout."""
        self.setFixedWidth(self.WIDTH)
        
        # Main layout with shadow padding
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(
            self.SHADOW_SIZE + 8,
            self.SHADOW_SIZE + 6,
            self.SHADOW_SIZE + 8,
            self.SHADOW_SIZE + 6
        )
        main_layout.setSpacing(6)
        
        # Text container
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(2, 2, 2, 2)
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Icon + title row (paired and vertically centered)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(2, 2, 2, 2)
        top_layout.setSpacing(6)

        self._icon_label = QLabel()
        self._icon_label.setFixedSize(self.ICON_SIZE, self.ICON_SIZE)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if self._icon_pixmap:
            self._icon_label.setPixmap(self._icon_pixmap)
        top_layout.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # Title label
        self._title_label = QLabel()
        self._title_label.setWordWrap(True)
        self._title_label.setAutoFillBackground(False)
        title_palette = self._title_label.palette()
        title_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self._title_label.setPalette(title_palette)
        self._title_label.setStyleSheet("font-size: 16px; font-weight: 400;")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_layout.addWidget(self._title_label, 1, Qt.AlignmentFlag.AlignVCenter)
        text_layout.addLayout(top_layout)
        
        # Message label (scrollable for long text)
        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setAutoFillBackground(False)
        self._message_label.setTextFormat(Qt.TextFormat.MarkdownText)
        self._message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self._message_label.setOpenExternalLinks(True)
        msg_palette = self._message_label.palette()
        msg_palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 205))
        self._message_label.setPalette(msg_palette)
        self._message_label.setStyleSheet("font-size: 12px;")

        message_container = QWidget()
        message_container.setStyleSheet("background: transparent;")
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.addWidget(self._message_label)

        self._message_scroll = QScrollArea()
        self._message_scroll.setWidgetResizable(True)
        self._message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._message_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._message_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._message_scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self._message_scroll.setWidget(message_container)

        text_layout.addWidget(self._message_scroll)

        # Countdown progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255, 255, 255, 25);
                border: none;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background: rgba(184, 134, 11, 170);
                border-radius: 2px;
            }
        """)
        text_layout.addWidget(self._progress_bar)
        main_layout.addLayout(text_layout, 1)
    
    def _setup_animations(self):
        """Set up slide and fade animations."""
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(self.SLIDE_DURATION)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(self.SLIDE_DURATION)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.finished.connect(self._on_fade_finished)
    
    def show_notification(self, title: str, message: str, duration: int = 7000, urgency: str = 'normal'):
        """
        Display the notification.
        
        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
            urgency: 'low', 'normal', or 'high'
        """
        self._duration = duration
        self._urgency = urgency
        
        # Adjust size to content
        self._message_label.adjustSize()
        message_height = self._message_label.sizeHint().height()
        self._message_scroll.setMaximumHeight(message_height * 3)

        self.setMinimumHeight(self.MIN_HEIGHT)
        self.setMaximumHeight(self.MAX_HEIGHT)
        self.adjustSize()
        
        # Position at bottom-right of screen (clamped to visible area)
        screen = self.screen().availableGeometry()
        end_x = screen.right() - self.WIDTH - self.MARGIN
        end_y = screen.bottom() - self.height() - self.MARGIN
        end_x = max(screen.left(), min(end_x, screen.right() - self.WIDTH))
        end_y = max(screen.top(), min(end_y, screen.bottom() - self.height()))
        start_x = screen.right() + 10
        
        self.move(end_x, end_y)
        self.setWindowOpacity(0.0)
        
        self._title_label.setText(title)
        self._message_label.setText(message)
        
        self.show()
        
        # Animate in
        self._slide_anim.setStartValue(QPoint(start_x, end_y))
        self._slide_anim.setEndValue(QPoint(end_x, end_y))
        self._slide_anim.start()
        
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()
        
        self._start_timers(duration)
    
    def _start_hide_animation(self):
        """Start the hide animation."""
        self._progress_timer.stop()
        screen = self.screen().availableGeometry()
        end_x = screen.right() + 10
        
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(end_x, self.pos().y()))
        self._slide_anim.start()
        
        self._fade_anim.setStartValue(1.0)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()

    def _start_timers(self, duration):
        self._remaining_ms = max(0, int(duration))
        self._progress_bar.setRange(0, self._remaining_ms or 1)
        self._progress_bar.setValue(self._remaining_ms)
        self._elapsed_timer.restart()
        self._hide_timer.start(self._remaining_ms)
        self._progress_timer.start()

    def _update_progress(self):
        elapsed = int(self._elapsed_timer.elapsed())
        remaining = max(0, self._remaining_ms - elapsed)
        self._progress_bar.setValue(remaining)
        if remaining == 0:
            self._progress_timer.stop()
    
    def _on_fade_finished(self):
        """Handle fade animation completion."""
        if self.windowOpacity() == 0.0:
            self.hide()
            self.deleteLater()
    
    def paintEvent(self, event):
        """Paint the notification background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Content rect
        content_rect = QRectF(
            self.SHADOW_SIZE,
            self.SHADOW_SIZE,
            self.width() - self.SHADOW_SIZE * 2,
            self.height() - self.SHADOW_SIZE * 2
        )
        
        # Draw shadow
        for i in range(self.SHADOW_SIZE):
            alpha = int(25 * (1 - i / self.SHADOW_SIZE))
            shadow_rect = content_rect.adjusted(-i, -i + 1, i, i + 1)
            path = QPainterPath()
            path.addRoundedRect(shadow_rect, self.BORDER_RADIUS + i, self.BORDER_RADIUS + i)
            painter.fillPath(path, QColor(0, 0, 0, alpha))
        
        # Background
        path = QPainterPath()
        path.addRoundedRect(content_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        gradient = QLinearGradient(content_rect.topLeft(), content_rect.bottomLeft())
        gradient.setColorAt(0.0, self.BG_COLOR_TOP)
        gradient.setColorAt(1.0, self.BG_COLOR_BOTTOM)
        painter.fillPath(path, QBrush(gradient))
        
        # Subtle border
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawRoundedRect(content_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        
    
    def enterEvent(self, event):
        """Pause hide timer when mouse enters."""
        self._hide_timer.stop()
        self._progress_timer.stop()
        elapsed = int(self._elapsed_timer.elapsed())
        self._remaining_ms = max(0, self._remaining_ms - elapsed)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """Resume hide timer when mouse leaves."""
        # Only restart if not already hiding
        if self.windowOpacity() > 0 and not self._fade_anim.state() == QPropertyAnimation.State.Running:
            self._elapsed_timer.restart()
            self._hide_timer.start(self._remaining_ms)
            self._progress_timer.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Dismiss on click."""
        self._hide_timer.stop()
        self._progress_timer.stop()
        self._start_hide_animation()
        super().mousePressEvent(event)
