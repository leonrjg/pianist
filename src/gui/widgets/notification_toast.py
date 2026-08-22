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
    QPushButton,
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
    QIcon,
)

from ..constants import piano_colors
from core.settings.service import SettingsService
from gui.themes import current_theme as _t


class NotificationToast(QWidget):
    """
    Desktop notification toast with clean, modern styling.
    
    Appears as a popup in the bottom-right corner of the screen.
    """
    
    # Dimensions
    WIDTH = 350
    HEIGHT = 160
    MESSAGE_MAX_HEIGHT = 44
    MARGIN = 30
    SHADOW_SIZE = 6
    BORDER_RADIUS = 12
    ICON_SIZE = 28

    # Timer limits (QTimer uses signed 32-bit int milliseconds)
    MAX_TIMER_MS = 2147483647  # ~24.8 days
    
    # Colors (resolved dynamically from active theme in paintEvent)
    BORDER_COLOR = QColor(60, 60, 65)
    BORDER_COLOR = QColor(60, 60, 65)
    TITLE_COLOR = QColor(255, 255, 255)
    MESSAGE_COLOR = QColor(220, 220, 225)

    URGENT_COLOR = QColor(220, 80, 80)
    
    # Animation
    SLIDE_DURATION = 250
    PROGRESS_INTERVAL = 50
    
    def __init__(self, parent=None):
        # Qt.Tool (not Qt.Window): on macOS only panel-type windows can be
        # non-activating, so a plain Window would steal focus on show()
        # despite WindowDoesNotAcceptFocus / WA_ShowWithoutActivating.
        super().__init__(
            parent,
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Tool windows hide when the app deactivates on macOS; a toast must
        # stay visible while the user works in another app.
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self._urgency = 'normal'
        self._duration = 12000
        self._icon_pixmap = None
        self._buttons = None
        self._configured_opacity = float(SettingsService.get('window.opacity', 1.0))

        # Drag support: the coordinator (NotificationService) moves the whole
        # group of visible toasts together via a shared offset.
        self._coordinator = None
        self._dragging = False
        self._drag_start_global = QPoint()
        self._home_pos = QPoint()  # default (un-dragged) position
        
        self._load_icon()
        self._setup_ui()
        self._setup_animations()
        SettingsService.signals.changed.connect(self._on_setting_changed)
        
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
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        
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
        text_layout.setSpacing(1)
        # Header pinned to the top, footer (buttons/progress) to the bottom,
        # message centered between them via paired stretches below, so every
        # toast keeps the same layout regardless of content.
        text_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
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
        self._title_label.setStyleSheet("font-size: 14px; font-weight: 400;")
        self._title_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_layout.addWidget(self._title_label, 1, Qt.AlignmentFlag.AlignVCenter)
        
        # Close button
        self._close_button = QPushButton()
        self._close_button.setFixedSize(20, 20)
        self._close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_icon_path = os.path.join(os.path.dirname(__file__), '..', 'icons', 'x.svg')
        if os.path.exists(close_icon_path):
            self._close_button.setIcon(QIcon(close_icon_path))
            self._close_button.setIconSize(self._close_button.size() * 0.6)
        else:
            self._close_button.setText('×')
        self._close_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: rgba(255, 255, 255, 180);
                font-size: 18px;
                font-weight: bold;
                padding: 0;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 20);
                border-radius: 4px;
                color: rgba(255, 255, 255, 255);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 30);
            }
        """)
        self._close_button.clicked.connect(self._on_close_clicked)
        self._close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        top_layout.addWidget(self._close_button, 0, Qt.AlignmentFlag.AlignVCenter)
        
        text_layout.addLayout(top_layout)

        # Stretch above the message; paired with the one below it, this keeps
        # the message vertically centered between the pinned header and footer.
        text_layout.addStretch(1)

        # Message label (scrollable for long text)
        self._message_label = QLabel()
        self._message_label.setWordWrap(True)
        self._message_label.setAutoFillBackground(False)
        self._message_label.setTextFormat(Qt.TextFormat.RichText)  # Support HTML from Anki cards
        self._message_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self._message_label.setOpenExternalLinks(True)
        # Stay mouse-interactive (links/selection) without grabbing keyboard
        # focus, so showing a toast never activates its window.
        self._message_label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._message_label.setMinimumWidth(0)
        self._message_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        msg_palette = self._message_label.palette()
        msg_palette.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 205))
        self._message_label.setPalette(msg_palette)
        self._message_label.setStyleSheet("font-size: 13px;")

        message_container = QWidget()
        message_container.setStyleSheet("background: transparent;")
        message_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        message_layout = QVBoxLayout(message_container)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.addWidget(self._message_label)

        self._message_scroll = QScrollArea()
        self._message_scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._message_scroll.setWidgetResizable(True)
        self._message_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._message_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._message_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._message_scroll.setFixedHeight(self.MESSAGE_MAX_HEIGHT)
        c = piano_colors()
        self._message_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
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
        self._message_scroll.setWidget(message_container)

        text_layout.addWidget(self._message_scroll)

        # Matching stretch below the message keeps it centered and pushes the
        # footer to the bottom, so the footer's height (buttons vs. progress
        # bar) never shifts the header or message position.
        text_layout.addStretch(1)

        # Feedback buttons container (hidden by default)
        self._feedback_container = QWidget()
        self._feedback_container.setStyleSheet("background: transparent;")
        self._feedback_container.setContentsMargins(0, 0, 0, 0)
        self._feedback_layout = QHBoxLayout(self._feedback_container)
        self._feedback_layout.setContentsMargins(0, 2, 0, 2)
        self._feedback_layout.setSpacing(6)
        self._feedback_container.hide()
        text_layout.addWidget(self._feedback_container)
        text_layout.setStretchFactor(self._feedback_container, 0)  # Don't stretch

        # Countdown progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(100)
        _accent_rgb = _t().accent[4:-1]
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255, 255, 255, 25);
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: rgba({_accent_rgb}, 170);
                border-radius: 2px;
            }}
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

        # Snap-back animation: the "pull" toward the default location.
        # OutBack gives a slight magnetic overshoot.
        self._snap_anim = QPropertyAnimation(self, b"pos")
        self._snap_anim.setDuration(220)
        self._snap_anim.setEasingCurve(QEasingCurve.Type.OutBack)

    def set_drag_coordinator(self, coordinator):
        """Register the coordinator that moves all toasts as a group."""
        self._coordinator = coordinator

    def apply_offset(self, offset: QPoint, animate: bool):
        """
        Move to home position plus a coordinator-supplied offset.

        Args:
            offset: Total offset from home (pile indent + group + individual).
            animate: When True, glide to the target (used for the snap-back
                     "pull" and pile reflow); otherwise follow the cursor instantly.
        """
        target = self._home_pos + offset
        if animate:
            self._snap_anim.stop()
            self._snap_anim.setStartValue(self.pos())
            self._snap_anim.setEndValue(target)
            self._snap_anim.start()
        else:
            if self._snap_anim.state() == QPropertyAnimation.State.Running:
                self._snap_anim.stop()
            self.move(target)

    def show_notification(self, title: str, message: str, duration: int = 7000, urgency: str = 'normal',
                         buttons: list = None):
        """
        Display the notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
            urgency: 'low', 'normal', or 'high'
            buttons: Optional list of button configs:
                     [{"label": str, "callback": callable, "color": str}, ...]
        """
        self._duration = duration
        self._urgency = urgency
        self._buttons = buttons

        # Setup buttons if provided
        if self._buttons:
            self._setup_buttons(self._buttons)
        else:
            self._feedback_container.hide()
        
        self._title_label.setText(title)
        self._set_message_text(message)

        # Position at bottom-right of screen (clamped to visible area)
        screen = self.screen().availableGeometry()
        end_x = screen.right() - self.WIDTH - self.MARGIN
        end_y = screen.bottom() - self.height() - self.MARGIN
        end_x = max(screen.left(), min(end_x, screen.right() - self.WIDTH))
        end_y = max(screen.top(), min(end_y, screen.bottom() - self.height()))
        start_x = screen.right() + 10

        # Default (un-dragged) location; the pile/group may already be offset.
        self._home_pos = QPoint(end_x, end_y)
        offset = self._coordinator.offset_for(self) if self._coordinator else QPoint(0, 0)
        target = self._home_pos + offset

        self.move(target)
        self.setWindowOpacity(0.0)

        self.show()

        # Animate in
        self._slide_anim.setStartValue(QPoint(start_x, target.y()))
        self._slide_anim.setEndValue(target)
        self._slide_anim.start()

        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(self._configured_opacity)
        self._fade_anim.start()

        # Only auto-close if no buttons (buttons require user interaction)
        if self._buttons is None or len(self._buttons) == 0:
            self._start_timers(duration)
        else:
            self._progress_bar.hide()

    def _message_width(self) -> int:
        """Available width for wrapped message text inside the fixed-width toast."""
        contents_width = self.WIDTH - (self.SHADOW_SIZE + 8) * 2
        return max(0, contents_width - 8)

    def _set_message_text(self, message: str):
        self._message_label.setMaximumWidth(self._message_width())
        self._message_label.setText(message)
        self._message_label.adjustSize()
    
    def _start_hide_animation(self):
        """Start the hide animation."""
        self._hide_timer.stop()
        self._progress_timer.stop()
        screen = self.screen().availableGeometry()
        end_x = screen.right() + 10
        
        self._slide_anim.setStartValue(self.pos())
        self._slide_anim.setEndValue(QPoint(end_x, self.pos().y()))
        self._slide_anim.start()
        
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.start()
    
    def _setup_buttons(self, buttons: list):
        """
        Setup custom buttons from config.

        Args:
            buttons: List of {"label": str, "callback": callable, "color": str (optional)}
        """
        # Clear existing buttons
        while self._feedback_layout.count():
            item = self._feedback_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Ensure margins are maintained
        self._feedback_layout.setContentsMargins(0, 2, 0, 2)

        for button_config in buttons:
            label = button_config.get("label", "")
            callback = button_config.get("callback")
            color = button_config.get("color", "rgba(140, 170, 90, 200)")  # Default green
            primary = button_config.get("primary", False)
            icon_path = button_config.get("icon")

            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # don't let a button activate the toast on show

            if icon_path and os.path.exists(icon_path):
                btn.setIcon(QIcon(icon_path))
                btn.setIconSize(btn.size() * 0.55)
                btn.setText("")
                btn.setFixedSize(28, 28)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: rgba(255, 255, 255, 25);
                        border: none;
                        border-radius: 4px;
                        padding: 0;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 50);
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(255, 255, 255, 20);
                    }}
                """)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.clicked.connect(lambda checked, cb=callback, lbl=label: self._on_button_clicked(cb, lbl))
                self._feedback_layout.addWidget(btn)
                continue
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if primary:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: {_t().button_primary_text};
                        border: none;
                        padding: 6px 16px;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 13px;
                    }}
                    QPushButton:hover {{
                        background-color: {color.replace('200)', '230)')};
                    }}
                    QPushButton:pressed {{
                        background-color: {color.replace('200)', '180)')};
                    }}
                """)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {color};
                        color: {_t().button_primary_text};
                        border: none;
                        padding: 6px 8px;
                        border-radius: 4px;
                        font-weight: bold;
                        font-size: 10px;
                    }}
                    QPushButton:hover {{
                        background-color: {color.replace('200)', '200)').replace('160)', '180)')};
                    }}
                    QPushButton:pressed {{
                        background-color: {color.replace('200)', '180)').replace('160)', '140)')};
                    }}
                """)
            btn.clicked.connect(lambda checked, cb=callback, lbl=label: self._on_button_clicked(cb, lbl))
            self._feedback_layout.addWidget(btn)

        self._feedback_container.show()
        self._feedback_container.updateGeometry()  # Force layout recalculation

    def _on_button_clicked(self, callback, label: str):
        """Handle button click - just call callback, let it handle updates."""
        if callback:
            callback()

    def update_content(self, title: str = None, message: str = None, buttons: list = None,
                      auto_close_after: int = None):
        """
        Update notification content in place (smooth transition without hide/show).

        Args:
            title: New title (None = keep current)
            message: New message (None = keep current)
            buttons: New buttons (None = keep current, [] = remove buttons)
            auto_close_after: Auto-close after N milliseconds (None = don't auto-close)
        """
        # Update title
        if title is not None:
            self._title_label.setText(title)

        # Update message
        if message is not None:
            self._set_message_text(message)

        # Update buttons and manage timers
        if buttons is not None:
            had_buttons = self._buttons and len(self._buttons) > 0
            has_buttons = buttons and len(buttons) > 0

            self._buttons = buttons

            if has_buttons:
                self._setup_buttons(buttons)
                # Stop timers when adding buttons (auto_close_after below will restart if needed)
                self._hide_timer.stop()
                self._progress_timer.stop()
                self._progress_bar.hide()
            else:
                self._feedback_container.hide()
                self._progress_bar.show()  # Show progress bar when no buttons
                # Start timers when removing buttons (if not already closing)
                if had_buttons and self.windowOpacity() > 0:
                    if auto_close_after is None:
                        auto_close_after = 2000  # Default 2 sec for updates without buttons

        # Handle auto-close
        if auto_close_after is not None:
            self._hide_timer.stop()
            self._progress_timer.stop()
            self._progress_bar.show()
            self._start_timers(max(0, int(auto_close_after)))

    def _on_close_clicked(self):
        """Handle close button click."""
        self._start_hide_animation()

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

    def _on_setting_changed(self, key: str, value):
        """Apply window opacity changes to this toast while it is visible."""
        if key != 'window.opacity':
            return

        self._configured_opacity = float(value)
        is_fading_out = (
            self._fade_anim.state() == QPropertyAnimation.State.Running
            and self._fade_anim.endValue() == 0.0
        )
        if self.isVisible() and not is_fading_out:
            self._fade_anim.stop()
            self.setWindowOpacity(self._configured_opacity)
    
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
        c = piano_colors()
        gradient.setColorAt(0.0, c.FRAME_MEDIUM)
        gradient.setColorAt(1.0, c.FRAME_DARK)
        painter.fillPath(path, QBrush(gradient))
        
        # Subtle border
        painter.setPen(QPen(self.BORDER_COLOR, 1))
        painter.drawRoundedRect(content_rect, self.BORDER_RADIUS, self.BORDER_RADIUS)
        
    
    def enterEvent(self, event):
        """Pause hide timer when mouse enters."""
        # Don't pause timer for notifications with buttons (they don't auto-close)
        has_buttons = self._buttons and len(self._buttons) > 0
        if not has_buttons:
            self._hide_timer.stop()
            self._progress_timer.stop()
            # Calculate remaining time, with safety bounds
            elapsed = int(self._elapsed_timer.elapsed())
            self._remaining_ms = max(0, min(self._remaining_ms - elapsed, self.MAX_TIMER_MS))
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Resume hide timer when mouse leaves."""
        # Don't resume timer for notifications with buttons (they don't auto-close)
        has_buttons = self._buttons and len(self._buttons) > 0
        if not has_buttons:
            # Only restart if not already hiding
            if self.windowOpacity() > 0 and not self._fade_anim.state() == QPropertyAnimation.State.Running:
                # Clamp to valid QTimer range to prevent overflow
                safe_remaining = max(300, min(self._remaining_ms, self.MAX_TIMER_MS))
                self._elapsed_timer.restart()
                self._hide_timer.start(safe_remaining)
                self._progress_timer.start()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """Begin dragging the toast (and the whole visible group)."""
        if event.button() == Qt.MouseButton.LeftButton and self._coordinator:
            self._dragging = True
            self._drag_start_global = event.globalPosition().toPoint()
            self._coordinator.begin_drag(self)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Forward drag deltas to the coordinator (moves pile or this toast)."""
        if self._dragging and self._coordinator:
            current = event.globalPosition().toPoint()
            delta = current - self._drag_start_global
            self._coordinator.update_drag(self, delta.x(), delta.y())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """End the drag gesture."""
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            if self._coordinator:
                self._coordinator.end_drag(self)
            event.accept()
            return
        super().mouseReleaseEvent(event)
