"""
Piano Floating Window - Main window (Refactored)

This is the orchestrator that composes all components together.
Responsibilities:
- Layout composition
- Signal routing between components
- Window-level event handling

Heavy lifting is delegated to:
- Models: PianoGeometry, PianoState
- Managers: SessionManager, AnimationManager, SoundManager
- Painters: FramePainter, KeyPainter, AccentPainter
"""

import time
import logging
from typing import Optional
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QIcon, QPainterPath

from core.util.time import get_friendly_elapsed
from datetime import datetime

from ..services import HabitService
from ..constants import PianoLayout, piano_colors, _parse_rgb, Animations, Interactions
from ..models import PianoGeometry, PianoState
from ..managers import SessionManager, AnimationManager, SoundManager, DrawerAnimationManager, WindowSizeManager, ReorderModeManager, AutoSessionManager, ReminderManager
from ..painters import FramePainter, KeyPainter
from .music_sheet_widget import MusicSheetWidget
from .marquee import Marquee
from core.reminder.context import ContextEvaluator
from core.notification.service import NotificationService


class PianoFloatingWindow(QWidget):
    """Main piano interface window - orchestrates all components"""

    # Session management signals
    session_start_requested = pyqtSignal(object)  # Emits Habit object
    session_stop_requested = pyqtSignal(object)   # Emits Habit object

    def __init__(self, service: HabitService):
        super().__init__()

        # ===== Data Service =====
        self.service = service
        service.subscribe(self._on_habits_changed)

        # ===== Window Setup =====
        self.setWindowTitle("Pianist")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon('etc.png'))

        # ===== Initialize Window Size Manager =====
        self.size_manager = WindowSizeManager(self)

        # ===== Initialize Models =====
        # Window is always sized to accommodate full content (drawer + keys)
        # Drawer visibility is controlled by mask, not window size
        initial_size = self.size_manager.get_initial_size(drawer_visible=False)
        initial_width = initial_size.width()
        initial_height = initial_size.height()

        self.state = PianoState()
        self.state.toggleable_drawer_visible = False

        self.geometry_model = PianoGeometry(
            window=self,
            toggleable_drawer_visible=False
        )

        # ===== Initialize Keys Placeholder =====
        self.state.num_habits = len(service.get_visible_habits())
        self.keys = []  # Will be populated by update_keys_for_window_size()

        # ===== Initialize Managers =====
        self.session_manager = SessionManager()
        self.session_manager.elapsed_updated.connect(self.on_elapsed_updated)
        self.session_manager.session_ended.connect(self.on_session_ended)
        self.session_manager.error_occurred.connect(self.on_session_error)
        self.session_manager.start()

        # Auto-session manager for window-based session triggering
        self.auto_session_manager = AutoSessionManager(service=service)
        self.auto_session_manager.session_start_requested.connect(self.on_session_start_requested)

        # Connect session management signals
        self.session_start_requested.connect(self.on_session_start_requested)
        self.session_stop_requested.connect(self.on_session_stop_requested)

        # ===== Window Sizing =====
        # Resize window BEFORE creating drawer animation manager so geometry queries work correctly
        self.resize(initial_width, initial_height)
        min_width = self.size_manager.get_minimum_width()
        min_height = self.size_manager.get_minimum_height()
        self.setMinimumSize(min_width, min_height)

        # Cap maximum window size to screen size
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.setMaximumSize(screen_geometry.width(), screen_geometry.height())

        self.animation_manager = AnimationManager(self)
        self.animation_manager.fade_finished.connect(self.on_fade_finished)

        self.drawer_animation_manager = DrawerAnimationManager(self)
        self.drawer_animation_manager.initialize_state(self.state.toggleable_drawer_visible)
        self.drawer_animation_manager.animation_finished.connect(self.on_drawer_animation_finished)

        self.sound_manager = SoundManager()

        self.reorder_mode_manager = ReorderModeManager(self)
        self.reorder_mode_manager.pulse_updated.connect(self.update)
        self.reorder_mode_manager.reorder_mode_toggled.connect(self.on_reorder_mode_toggled)
        self.reorder_mode_manager.set_num_keys(len(self.keys))

        # Reminder system
        self.context_evaluator = ContextEvaluator()
        self.reminder_manager = ReminderManager(self.context_evaluator)
        self.reminder_manager.notification_requested.connect(self._on_reminder_notification)
        self.reminder_manager.start()

        # Notification service
        self.notification_service = NotificationService.get_instance()
        self.notification_service.set_parent(self)

        # ===== Key Press Visual Effect =====
        self.press_timer = QTimer()
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.clear_key_press)

        # ===== Hide Timer (for double-click hide feature) =====
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.show_window_after_hide)

        # ===== Management Window =====
        self.management_window = None

        # ===== Notes Widget (init placeholder) =====
        self.notes_widget = None

        # ===== Music Sheet Widget (Interactive Drawer Content) =====
        self.music_sheet_widget = MusicSheetWidget(self, sound_manager=self.sound_manager)
        self.music_sheet_widget.habit_updated.connect(self.on_habit_updated_from_sheet)
        self.music_sheet_widget.hide()  # Initially hidden
        self._position_music_sheet_widget()

        # ===== Tips Marquee (Below music stand holder) =====
        tips = [
            "Tip: rearrange keys by clicking the Reorder button and dragging keys",
            "Tip: When in compact mode, double-click anywhere to hide the window for a few seconds",
            "Tip: Right-click the mood button to manage moods",
            "Tip: Right-click a key for more options",
        ]
        self.tips_marquee = Marquee(tips, self)
        self._position_tips_marquee()

        # ===== Initialize Keys =====
        self.update_keys_for_window_size()

        # ===== Center Window =====
        self.center_window()

        # ===== Set Window Opacity =====
        self.setWindowOpacity(Animations.WINDOW_OPACITY_NORMAL)

        # ===== Enable Mouse Tracking =====
        self.setMouseTracking(True)

        # ===== Connect State Signals =====
        self.state.toggleable_drawer_toggled.connect(self.on_toggleable_drawer_toggled)
        self.size_manager.size_changed.connect(self.on_window_resized)

        # ===== Create Control Buttons Container =====
        self.control_buttons_container = QWidget(self)
        control_layout = QVBoxLayout(self.control_buttons_container)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)

        # Close button
        self.close_button = QPushButton()
        self.close_button.setIcon(QIcon('gui/icons/min.svg'))
        self.close_button.setIconSize(QSize(14, 14))
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.showMinimized)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Maximize button
        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(QIcon('gui/icons/maximize.svg'))
        self.maximize_button.setIconSize(QSize(14, 14))
        self.maximize_button.setFixedSize(20, 20)
        self.maximize_button.setToolTip('Maximize window')
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.maximize_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Reorder button
        self.reorder_button = QPushButton()
        self.reorder_button.setIcon(QIcon('gui/icons/reorder.svg'))
        self.reorder_button.setIconSize(QSize(14, 14))
        self.reorder_button.setFixedSize(20, 20)
        self.reorder_button.setToolTip('Reorder keys')
        self.reorder_button.clicked.connect(self.reorder_mode_manager.toggle_reorder_mode)
        self.reorder_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Mood button
        self.mood_button = QPushButton()
        self.mood_button.setIcon(QIcon('gui/icons/mood.svg'))
        self.mood_button.setIconSize(QSize(14, 14))
        self.mood_button.setFixedSize(20, 20)
        self.mood_button.setToolTip('Log mood')
        self.mood_button.clicked.connect(self.on_mood_button_clicked)
        self.mood_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mood_button.installEventFilter(self)

        # Add Task button
        self.add_task_button = QPushButton("+")
        self.add_task_button.setFixedSize(20, 20)
        self.add_task_button.setToolTip('Add task')
        self.add_task_button.clicked.connect(self.on_add_task_button_clicked)
        self.add_task_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Notes button
        self.notes_button = QPushButton()
        self.notes_button.setIcon(QIcon('gui/icons/notes.svg'))
        self.notes_button.setIconSize(QSize(14, 14))
        self.notes_button.setFixedSize(20, 20)
        self.notes_button.setToolTip('Notes')
        self.notes_button.clicked.connect(self.on_notes_button_clicked)
        self.notes_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.notes_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Sync button
        self.sync_button = QPushButton()
        self.sync_button.setIcon(QIcon('gui/icons/sync.svg'))
        self.sync_button.setIconSize(QSize(14, 14))
        self.sync_button.setFixedSize(20, 20)
        self.sync_button.setToolTip('Sync')
        self.sync_button.clicked.connect(self.on_sync_button_clicked)
        self.sync_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sync_button.hide()  # Hidden until a peer device is known
        self._sync_rotation = 0
        # Cached pixmap is rebuilt in _setup_style with the correct theme color
        self._sync_icon_pixmap = None

        self._apply_sync_button_style(active=False)
        self._setup_style()

        control_layout.addWidget(self.close_button)
        control_layout.addWidget(self.maximize_button)
        control_layout.addWidget(self.reorder_button)
        control_layout.addWidget(self.mood_button)
        control_layout.addWidget(self.add_task_button)
        control_layout.addWidget(self.notes_button)
        control_layout.addWidget(self.sync_button)
        control_layout.addStretch()

        # Spin timer: rotate icon while a sync is in-flight
        self._sync_spin_timer = QTimer()
        self._sync_spin_timer.setInterval(50)
        self._sync_spin_timer.timeout.connect(self._on_sync_spin_tick)

        # Poll timer: update sync button visibility/color every 5 s
        self._sync_poll_timer = QTimer()
        self._sync_poll_timer.timeout.connect(self._update_sync_button_state)
        self._sync_poll_timer.start(5000)
        self._update_sync_button_state()  # Apply immediately

        self._position_control_buttons_container()

        # ===== Mood Bar Widget =====
        from .mood_bar_widget import MoodBarWidget
        self.mood_bar = MoodBarWidget(self)
        self.mood_bar.mood_selected.connect(self.on_mood_selected)
        self.mood_bar.closed.connect(self.on_mood_bar_closed)
        self.mood_bar.hide()

        # ===== Mood Update Timer =====
        self.mood_update_timer = QTimer()
        self.mood_update_timer.timeout.connect(self.update_mood_button_icon)
        self.mood_update_timer.start(60000)  # Check every minute
        self.update_mood_button_icon()  # Initial update

        # ===== Add Task Widget =====
        from .add_task_widget import AddTaskWidget
        self.add_task_widget = AddTaskWidget(self)
        self.add_task_widget.task_created.connect(self.on_task_created)
        self.add_task_widget.closed.connect(self.on_add_task_closed)
        self.add_task_widget.hide()

        # ===== Notes Widget =====
        from .notes_widget import NotesWidget
        self.notes_widget = NotesWidget(self)
        self.notes_widget.closed.connect(self.on_notes_closed)
        self.notes_widget.hide()

        # Install event filter to forward notes drag events to piano
        self.notes_widget.installEventFilter(self)

    # ===== Window Management =====

    def center_window(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.size().width()) // 2
        y = (screen_geometry.height() - self.size().height()) // 2
        self.move(x, y)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self.show()
            if self.state.toggleable_drawer_visible:
                self.toggle_toggleable_drawer()
        else:
            self.showMaximized()
            if not self.state.toggleable_drawer_visible:
                self.toggle_toggleable_drawer()

    def resizeEvent(self, event):
        """
        Handle window resize events.

        Delegates to WindowSizeManager which validates size and coordinates
        with drawer mask animation.
        """
        super().resizeEvent(event)

        new_width = self.size().width()
        new_height = self.size().height()

        # Let size manager handle the resize and coordinate with drawer mask
        if self.size_manager.handle_user_resize(new_width, new_height, self.drawer_animation_manager):
            # Size manager approved the resize - no need to update state, geometry_model queries window directly
            pass

    def on_window_resized(self, width, height):
        """Handle window resize state change"""
        # No need to update geometry_model - it queries window dimensions directly
        self.update_keys_for_window_size()
        self._position_music_sheet_widget()  # Reposition music sheet widget
        self._position_tips_marquee()  # Reposition tips marquee
        self._position_control_buttons_container()  # Reposition control buttons
        self._update_notes_widget_position()  # Update notes widget position
        self.update()

    def _position_control_buttons_container(self):
        """Position the control buttons container centered horizontally in the control panel"""
        # Center horizontally in the control panel
        control_panel_start_x = self.width() - PianoLayout.CONTROL_PANEL_WIDTH
        container_width = 20  # Button width
        x = control_panel_start_x + (PianoLayout.CONTROL_PANEL_WIDTH - container_width) // 2
        y = 10

        self.control_buttons_container.move(x, y)

    # ===== Keys Management =====

    def update_keys_for_window_size(self):
        """Update the keys array based on current window size and scroll position.

        Reads only from the in-memory service cache — no database access.
        Safe to call on every resize and scroll event.
        """
        all_habits = self.service.get_visible_habits()
        self.state.num_habits = len(all_habits)
        num_actual_habits = len(all_habits)

        available_height = self.height() - PianoLayout.FRAME_PADDING_VERTICAL
        num_keys_that_fit = max(1, int(available_height // PianoLayout.KEY_HEIGHT)) + 2

        self.state.scrolling_enabled = num_actual_habits > num_keys_that_fit

        if self.state.scrolling_enabled:
            self.state.max_scroll_offset = max(0, num_actual_habits - num_keys_that_fit)

            new_keys = []
            for i in range(num_keys_that_fit):
                habit_index = i + self.state.scroll_offset
                if habit_index < num_actual_habits:
                    habit = all_habits[habit_index]
                    info = self.service.get_next_task_info(habit.id)
                    new_keys.append({
                        'label': habit.name,
                        'habit': habit,
                        'time': None,
                        'task_datetime': info['task_dt'],
                        'is_completed': info['is_completed'],
                    })
                else:
                    new_keys.append({'label': '', 'habit': None, 'time': None, 'task_datetime': None, 'is_completed': False})
        else:
            self.state.scroll_offset = 0
            self.state.max_scroll_offset = 0

            new_keys = []
            for habit in all_habits[:num_keys_that_fit]:
                info = self.service.get_next_task_info(habit.id)
                new_keys.append({
                    'label': habit.name,
                    'habit': habit,
                    'time': None,
                    'task_datetime': info['task_dt'],
                    'is_completed': info['is_completed'],
                })

            while len(new_keys) < num_keys_that_fit:
                new_keys.append({'label': '', 'habit': None, 'time': None, 'task_datetime': None, 'is_completed': False})

        self.keys = new_keys
        self.reorder_mode_manager.set_num_keys(len(new_keys))

    # ===== Painting =====

    def paintEvent(self, event):
        """Main paint event - delegates to painters"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Create rounded rectangle clip path
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), PianoLayout.WINDOW_BORDER_RADIUS, PianoLayout.WINDOW_BORDER_RADIUS)
        painter.setClipPath(path)

        # Draw background
        painter.fillRect(self.rect(), piano_colors().BACKGROUND)

        # Delegate to painters (window mask controls visibility)
        FramePainter.draw_frame(painter, self.geometry_model)
        KeyPainter.draw_keys(painter, self.geometry_model, self.state, self.keys, self.reorder_mode_manager)

        # Draw window controls
        self.draw_window_controls(painter)

    def draw_window_controls(self, painter):
        """Draw window controls (now handled by QPushButton widgets)"""
        pass

    # ===== Mouse Events =====

    def _get_resize_edge_at_position(self, pos: QPoint):
        """Detect resize edge at position (returns edge name or None)"""
        if self.state.toggleable_drawer_visible:
            return None

        fallboard_x = self.geometry_model.toggleable_drawer_width
        # Check corners first (larger zone)
        if pos.y() <= Interactions.RESIZE_CORNER_THRESHOLD or pos.y() >= self.height() - Interactions.RESIZE_CORNER_THRESHOLD:
            if fallboard_x <= pos.x() <= fallboard_x + Interactions.RESIZE_CORNER_THRESHOLD:
                return 'top-left' if pos.y() <= Interactions.RESIZE_CORNER_THRESHOLD else 'bottom-left'
        # Then check straight edge (narrower zone)
        elif fallboard_x <= pos.x() <= fallboard_x + Interactions.RESIZE_EDGE_THRESHOLD:
            return 'left'
        return None

    def _get_checkmark_index_at_point(self, pos: QPoint) -> Optional[int]:
        """Get the key index if point is in checkmark region, None otherwise"""
        # Checkmark is in center of black key area
        for i in range(len(self.keys) - 1):
            key_data = self.keys[i]
            # Only check for keys with tasks
            if not key_data.get('habit') or not key_data.get('task_datetime'):
                continue

            black_key_rect = self.geometry_model.get_black_key_rect(i)
            # Checkmark is center 30px of black key
            checkmark_width = 30
            checkmark_x = black_key_rect.x() + (black_key_rect.width() - checkmark_width) / 2

            if (checkmark_x <= pos.x() <= checkmark_x + checkmark_width and
                black_key_rect.y() <= pos.y() <= black_key_rect.y() + black_key_rect.height()):
                return i

        return None

    def _get_time_button_at_point(self, pos: QPoint) -> Optional[tuple[int, str]]:
        """
        Get the (key_index, button_type) if point is on a time button, None otherwise.

        Returns:
            Tuple of (key_index, button_type) where button_type is 'plus' or 'minus', or None
        """
        for i in range(len(self.keys) - 1):
            key_data = self.keys[i]
            habit = key_data.get('habit')

            # Only check if there's an active session
            if not habit or not self.session_manager.has_active_session(habit.id):
                continue

            button_type = self.geometry_model.get_time_button_at_point(pos, i)
            if button_type:
                return (i, button_type)

        return None

    def _toggle_task_completion(self, habit, task_datetime):
        """Toggle task completion state"""
        try:
            self.service.toggle_task_completion(habit, task_datetime)
            # Notify music sheet to refresh its pages
            if hasattr(self, 'music_sheet_widget'):
                self.music_sheet_widget.habit_updated.emit()
        except Exception as e:
            print(f"Error toggling task completion: {e}")

    def handle_time_adjustment_click(self, habit_id: int, button_type: str):
        """
        Handle time adjustment button click.

        Args:
            habit_id: ID of the habit whose session to adjust
            button_type: 'plus' or 'minus'
        """
        delta_seconds = 60 if button_type == 'plus' else -60
        self.session_manager.adjust_session_time(habit_id, delta_seconds)

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            local_pos = event.position().toPoint()

            # Check for time adjustment button click FIRST (highest priority during sessions)
            time_button = self._get_time_button_at_point(local_pos)
            if time_button is not None:
                key_index, button_type = time_button
                key_data = self.keys[key_index]
                habit = key_data.get('habit')
                if habit:
                    self.handle_time_adjustment_click(habit.id, button_type)
                    return

            # Check for checkmark click (only if that habit has no active session)
            checkmark_index = self._get_checkmark_index_at_point(local_pos)
            if checkmark_index is not None and checkmark_index >= 0 and checkmark_index < len(self.keys):
                key_data = self.keys[checkmark_index]
                habit = key_data.get('habit')
                # Only allow checkmark click if this specific habit has no active session
                if habit and key_data.get('task_datetime') and not self.session_manager.has_active_session(habit.id):
                    self._toggle_task_completion(habit, key_data['task_datetime'])
                    return

            # Check for resize on fallboard left edge (when drawer closed)
            edge = self._get_resize_edge_at_position(local_pos)
            if edge:
                self.state.start_resize(edge, self.geometry(), global_pos.x(), global_pos.y())
                return

            self.state.start_drag(global_pos.x(), global_pos.y(), local_pos.x(), local_pos.y())

            # Check for double-click on piano frame
            current_time = time.time() * 1000
            if current_time - self.state.last_click_time < Interactions.DOUBLE_CLICK_THRESHOLD:
                if self.geometry_model.is_point_in_piano_frame(local_pos):
                    if self.geometry_model.toggleable_drawer_visible:
                        self.toggle_maximize()
                    else:
                        self.hide_window_for_seconds(Interactions.DOUBLE_CLICK_HIDE_DURATION)
                    return

            self.state.last_click_time = current_time

        elif event.button() == Qt.MouseButton.RightButton:
            local_pos = event.position().toPoint()
            self.handle_right_click(local_pos)

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            local_pos = event.position().toPoint()

            # Handle window resizing
            if self.state._is_resizing:
                global_pos = event.globalPosition().toPoint()
                dx = global_pos.x() - self.state._drag_start_x
                dy = global_pos.y() - self.state._drag_start_y
                rect = self.state._resize_start_rect
                edge = self.state._resize_edge

                x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
                if 'left' in edge:
                    x, w = x + dx, w - dx
                if 'top' in edge:
                    y, h = y + dy, h - dy
                if 'bottom' in edge:
                    h = h + dy

                # Enforce minimum size
                min_w = self.size_manager.get_minimum_width()
                min_h = self.size_manager.get_minimum_height()
                if w >= min_w and h >= min_h:
                    self.setGeometry(x, y, w, h)
                return

            # Handle key reordering in reorder mode
            if self.reorder_mode_manager.is_reorder_mode and self.state.is_dragging_key():
                # Update drag position
                self.state.update_key_drag(local_pos.y(), self.calculate_drop_target(local_pos.y()))
                self.update()
                return

            # Handle normal window dragging
            drag_start_x, drag_start_y = self.state.get_drag_start()
            if drag_start_x != 0 or drag_start_y != 0:
                current_pos = event.globalPosition().toPoint()
                diff_x = current_pos.x() - drag_start_x
                diff_y = current_pos.y() - drag_start_y

                # Calculate total distance for drag detection
                distance = (diff_x ** 2 + diff_y ** 2) ** 0.5

                # In reorder mode, check if press was on a key FIRST (before allowing window drag)
                if self.reorder_mode_manager.is_reorder_mode and not self.state.is_dragging and not self.state.is_dragging_key():
                    press_local_x, press_local_y = self.state.get_press_local()
                    press_pos = QPoint(press_local_x, press_local_y)

                    # Check if press was on a key
                    key_index = self.geometry_model.get_key_index_at_point(press_pos)
                    if key_index >= 0 and key_index < len(self.keys):
                        # If on a key and moved beyond threshold, start key drag
                        if distance > Interactions.KEY_REORDER_THRESHOLD:
                            self.state.start_key_drag(key_index, local_pos.y())
                            self.update()
                            return
                        # If on a key but haven't moved enough yet, DON'T start window drag
                        else:
                            return

                # Check if we've moved enough to consider this a window drag
                if not self.state.is_dragging and not self.state.is_dragging_key():
                    if distance > Interactions.DRAG_THRESHOLD:
                        self.state.is_dragging = True

                # Move window if dragging (and not dragging a key)
                if self.state.is_dragging and not self.state.is_dragging_key():
                    self.move(self.pos() + QPoint(diff_x, diff_y))
                    self.state.mark_window_moved()  # Mark that window was actually moved
                    # Update drag position without resetting the moved flag
                    self.state.start_drag(current_pos.x(), current_pos.y(), reset_moved_flag=False)
                    # Update notes widget position when dragging
                    self._update_notes_widget_position()
        else:
            # Track hover state for time buttons and checkmarks
            local_pos = event.position().toPoint()

            # Check for time button hover (only when sessions are active)
            time_button = self._get_time_button_at_point(local_pos)
            if time_button != self.state.hovered_time_button:
                self.state.hovered_time_button = time_button
                self.update()

            # Check for checkmark hover (only for habits with no active session)
            checkmark_index = self._get_checkmark_index_at_point(local_pos)

            # Only allow hover if the specific habit has no active session
            if checkmark_index is not None and checkmark_index >= 0 and checkmark_index < len(self.keys):
                habit = self.keys[checkmark_index].get('habit')
                # Clear hover if this habit has an active session
                if habit and self.session_manager.has_active_session(habit.id):
                    checkmark_index = None

            if checkmark_index != self.state.hovered_checkmark_index:
                self.state.hovered_checkmark_index = checkmark_index
                self.update()

            # Update cursor based on hover position
            self.update_cursor_for_position(local_pos)

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Handle resize end
            if self.state._is_resizing:
                self.state.end_resize()
                return

            # Handle key reorder drop
            if self.state.is_dragging_key():
                self.perform_key_reorder()
                self.state.end_key_drag()
                self.update()
                self.state.end_drag()
                return

            # Determine if this was a click (not a window drag)
            press_local_x, press_local_y = self.state.get_press_local()
            release_pos = event.position().toPoint()

            # Calculate distance between press and release in local coordinates
            is_valid_click = False
            if press_local_x != 0 or press_local_y != 0:
                diff_x = release_pos.x() - press_local_x
                diff_y = release_pos.y() - press_local_y
                distance = (diff_x ** 2 + diff_y ** 2) ** 0.5
                is_valid_click = distance <= Interactions.CLICK_TOLERANCE

            # Process click if:
            # - Window was not moved (not a window drag), AND
            # - Release is close to press (not a large mouse movement)
            if not self.state.window_was_moved and is_valid_click:
                self.handle_click(release_pos)

            # Reset drag state
            self.state.end_drag()

    def handle_click(self, pos: QPoint):
        """
        Handle a click at the given position.

        Checks clickable regions in priority order. First match handles the click.
        No mode restrictions needed - key dragging already prevents key clicks in reorder mode.
        """
        # Drawer toggle
        if self.geometry_model.is_point_in_hinge(pos):
            self.toggle_toggleable_drawer()
            return

        # Keys (start habit session)
        if self.geometry_model.is_point_in_keys(pos):
            self.handle_key_click(pos)

    def handle_right_click(self, pos: QPoint):
        """
        Handle a right-click at the given position.

        Opens the drawer and navigates to the habit's detail page if clicked on a key.
        """
        if self.geometry_model.is_point_in_keys(pos):
            key_index = self.geometry_model.get_key_index_at_point(pos)

            if key_index >= 0 and key_index < len(self.keys):
                key_data = self.keys[key_index]
                habit = key_data.get('habit')

                if habit:
                    # Open drawer if not already open
                    if not self.state.toggleable_drawer_visible:
                        self.toggle_toggleable_drawer()

                    # Navigate to habit detail page
                    self.music_sheet_widget.navigate_to_habit_detail(habit)

    def update_cursor_for_position(self, pos: QPoint):
        """Update cursor based on mouse position"""
        cursor = Qt.CursorShape.ArrowCursor

        # Show resize cursor on fallboard left edge (when drawer closed)
        edge = self._get_resize_edge_at_position(pos)
        if edge:
            cursor = Qt.CursorShape.SizeFDiagCursor if 'top' in edge or 'bottom' in edge else Qt.CursorShape.SizeHorCursor
            self.setCursor(cursor)
            return

        if (self.geometry_model.is_point_in_control_button(pos) or
            self.geometry_model.is_point_in_keys(pos) or
            self.geometry_model.is_point_in_hinge(pos)):
            cursor = Qt.CursorShape.PointingHandCursor

        self.setCursor(cursor)

    def wheelEvent(self, event):
        """Handle mouse wheel for scrolling"""
        if self.state.scrolling_enabled:
            delta = event.angleDelta().y()

            if hasattr(event, 'pixelDelta') and not event.pixelDelta().isNull():
                pixel_delta = event.pixelDelta().y()
                scroll_amount = pixel_delta / 30.0
            else:
                scroll_amount = delta / 40.0

            self.state.scroll_accumulator += scroll_amount
            scroll_steps = int(self.state.scroll_accumulator)
            self.state.scroll_accumulator -= scroll_steps

            if scroll_steps != 0:
                old_offset = self.state.scroll_offset
                self.state.scroll_offset = self.state.scroll_offset - scroll_steps

                if self.state.scroll_offset != old_offset:
                    self.update_keys_for_window_size()
                    self.update()

            event.accept()
        else:
            super().wheelEvent(event)

    # ===== Key Interaction =====

    def handle_key_click(self, click_pos: QPoint):
        """Handle piano key clicks"""
        key_index = self.geometry_model.get_key_index_at_point(click_pos)

        if key_index >= 0 and key_index < len(self.keys):
            key_data = self.keys[key_index]
            habit = key_data.get('habit')

            # Trigger visual press effect
            self.state.press_key(key_index)
            self.update()
            self.press_timer.start(Animations.KEY_PRESS_DURATION)

            if habit:
                self.toggle_session(habit)

    def clear_key_press(self):
        """Clear the pressed key visual effect"""
        self.state.release_key()
        self.update()

    # ===== Session Management =====

    def toggle_session(self, habit):
        """Request to start or stop a session for the given habit"""
        if self.session_manager.has_active_session(habit.id):
            self.session_stop_requested.emit(habit)
        else:
            self.session_start_requested.emit(habit)

    def start_session(self, habit):
        """Start a session thread"""
        try:
            self.session_manager.start_session(habit)
            print(f"Starting session for {habit.name}")
        except Exception as e:
            print(f"Error starting session: {e}")

    def end_session(self, habit):
        """End a session"""
        try:
            self.session_manager.stop_session(habit.id)
            print(f"Stopping session for {habit.name}")

            # Clean up display immediately
            self.state.clear_time_display(habit.id)
            self.update()

        except Exception as e:
            print(f"Error stopping session: {e}")

    def on_elapsed_updated(self, habit_id: int, elapsed_seconds: int):
        """Handle elapsed time updates from session process"""
        time_text = get_friendly_elapsed(elapsed_seconds)
        self.state.set_time_display(habit_id, time_text)
        # Only update the time display area
        self.update(self.geometry_model.time_display_area)

    def on_session_ended(self, habit_id: int):
        """Handle session ended signal from process"""
        self.state.clear_time_display(habit_id)
        self.update(self.geometry_model.time_display_area)

    def on_session_error(self, error_message: str):
        """Handle session error from process"""
        print(f"Session error: {error_message}")

    def on_session_start_requested(self, habit):
        """Handle session start request (manual or auto) - play sound and start session"""
        # Check if session is already running
        if self.session_manager.has_active_session(habit.id):
            return

        # Play start sound
        self.sound_manager.play_sound('start')

        # Start the session
        self.start_session(habit)

    def on_session_stop_requested(self, habit):
        """Handle session stop request - play sound and stop session"""
        # Play end sound
        self.sound_manager.play_sound('end')

        # Mark as manually ended to prevent autostart for an hour
        self.auto_session_manager.mark_session_manually_ended(habit)

        # Stop the session
        self.end_session(habit)

    # ===== Reorder Mode =====

    def calculate_drop_target(self, y_position: int) -> int:
        """
        Calculate the target index for dropping a key based on Y position.

        Args:
            y_position: Current Y position of the dragged key

        Returns:
            Index where the key should be dropped
        """
        # Find which key position this Y coordinate corresponds to
        for i in range(len(self.keys)):
            key_rect = self.geometry_model.get_key_rect(i)
            key_center_y = key_rect.y() + key_rect.height() // 2

            if y_position < key_center_y:
                return i

        # If beyond all keys, drop at the end
        return len(self.keys) - 1

    def perform_key_reorder(self):
        """
        Perform the actual reordering of habits in the database.

        Updates display_order values based on the new arrangement.
        """
        if self.state.dragged_key_index is None or self.state.drop_target_index is None:
            return

        from_index = self.state.dragged_key_index
        to_index = self.state.drop_target_index

        # Don't reorder if dropping in the same position
        if from_index == to_index:
            return

        # Get the habit that was dragged
        dragged_key = self.keys[from_index]
        dragged_habit = dragged_key.get('habit')

        if not dragged_habit:
            return

        # Reorder the visible habits list
        reordered_habits = list(self.service.get_visible_habits())
        dragged = reordered_habits.pop(from_index)
        # Adjust target index if dragging downward (after pop, indices shift)
        adjusted_to_index = to_index if to_index <= from_index else to_index - 1
        reordered_habits.insert(adjusted_to_index, dragged)

        # Persist via service (atomic transaction, updates in-memory list, notifies)
        self.service.reorder_visible_habits(reordered_habits)

        # Play sound
        self.sound_manager.play_sound('thunk')

    def on_reorder_mode_toggled(self, is_active: bool):
        """Handle reorder mode toggle"""
        # Exit any active key drag
        if self.state.is_dragging_key():
            self.state.end_key_drag()

        self.update()

    # ===== Toggleable Drawer Toggle =====

    def toggle_toggleable_drawer(self):
        """Toggle the toggleable drawer visibility"""
        self.state.toggle_toggleable_drawer()

    def on_toggleable_drawer_toggled(self, visible: bool):
        """
        Handle toggleable drawer toggle state change.

        Shows/hides the music sheet widget and delegates mask animation
        to DrawerAnimationManager which handles the window mask
        reveal/hide effect.
        """
        self.geometry_model.update(toggleable_drawer_visible=visible)

        # Play drawer open sound
        self.sound_manager.play_sound('drawer')

        # Show widget immediately when opening
        if visible:
            self.music_sheet_widget.show()
            self.music_sheet_widget.raise_()  # Bring to front

        # Update notes widget to match new visible width
        self._update_notes_widget_position()

        self.drawer_animation_manager.start_animation(visible, self.geometry_model.toggleable_drawer_width)

    def on_drawer_animation_finished(self):
        """Handle drawer animation completion - hide widget after closing animation"""
        if not self.state.toggleable_drawer_visible:
            self.music_sheet_widget.hide()
        
        # Update notes widget position/width when drawer finishes animating
        self._update_notes_widget_position()

    # ===== Music Sheet Widget Management =====

    def _position_music_sheet_widget(self):
        """Position the music sheet widget in the toggleable drawer area"""
        drawer_rect = self.geometry_model.toggleable_drawer_rect

        # Add margins for the dark wood container
        margin = 6
        x = drawer_rect.x() + margin
        y = drawer_rect.y() + margin + 5
        width = drawer_rect.width() - (margin * 2)
        height = drawer_rect.height() - (margin * 2) - 20

        self.music_sheet_widget.setGeometry(x, y, width, height)

    def _position_tips_marquee(self):
        """Position the tips marquee below the music sheet widget"""
        drawer_rect = self.geometry_model.toggleable_drawer_rect

        margin = 6
        marquee_height = 20
        x = drawer_rect.x() + margin
        y = drawer_rect.y() + drawer_rect.height() - marquee_height
        width = drawer_rect.width() - (margin * 2)

        self.tips_marquee.setGeometry(x, y, width, marquee_height)
        self.tips_marquee.raise_()

    def on_habit_updated_from_sheet(self):
        """Handle habit updates from the music sheet widget"""
        self.service.refresh()

    # ===== Window Hiding =====

    def hide_window_for_seconds(self, seconds: int):
        """Hide the window for the specified number of seconds with fade animation"""
        self.state.is_fading_out = True
        self.animation_manager.fade_out()
        self.hide_timer.start(seconds * 1000)

    def on_fade_finished(self):
        """Called when fade animation finishes"""
        if self.state.is_fading_out:
            self.hide()

    def show_window_after_hide(self):
        """Show the window again after the hide timer expires"""
        self.show()
        self.state.is_fading_out = False
        self.animation_manager.fade_in()

    def refresh_habits(self):
        """Refresh habits list when management window updates them"""
        self.service.refresh()

    # ===== Sync Button =====

    def _control_button_stylesheet(self, border_override: str = None, color_override: str = None) -> str:
        """Return a themed stylesheet for a control panel button."""
        c = piano_colors()
        bg = c.FRAME_DARK.name()
        border = border_override or c.ACCENT.name()
        hover_border = c.ACCENT_LIGHT.name()
        txt = color_override or c.ACCENT.name()
        hover_txt = c.ACCENT_LIGHT.name()
        return f"""
            QPushButton {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 10px;
                color: {txt};
                font-size: 14px;
                font-weight: bold;
                padding-bottom: 2px;
            }}
            QPushButton:hover {{
                border-color: {hover_border};
                color: {hover_txt};
            }}
        """

    @staticmethod
    def _themed_icon(svg_path: str, color) -> QIcon:
        """Return svg_path icon tinted to the given QColor via composition."""
        base = QIcon(svg_path)
        pixmap = base.pixmap(QSize(14, 14))
        if pixmap.isNull():
            return base
        p = QPainter(pixmap)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        p.fillRect(pixmap.rect(), color)
        p.end()
        return QIcon(pixmap)

    def _setup_style(self):
        """Re-apply theme to all control panel buttons and repaint."""
        plain = self._control_button_stylesheet()
        c = piano_colors()
        icon_color = c.ACCENT
        icon_map = {
            self.close_button: 'gui/icons/min.svg',
            self.maximize_button: 'gui/icons/maximize.svg',
            self.reorder_button: 'gui/icons/reorder.svg',
            self.mood_button: 'gui/icons/mood.svg',
            self.notes_button: 'gui/icons/notes.svg',
        }
        for btn, svg_path in icon_map.items():
            btn.setStyleSheet(plain)
            btn.setIcon(self._themed_icon(svg_path, icon_color))
        self.add_task_button.setStyleSheet(plain)
        # Rebuild cached sync spin pixmap with current theme color
        sync_icon = self._themed_icon('gui/icons/sync.svg', icon_color)
        self._sync_icon_pixmap = sync_icon.pixmap(QSize(14, 14))
        self.sync_button.setIcon(sync_icon)
        # Re-apply sync button only if fully initialized
        if hasattr(self, '_sync_spin_timer'):
            self._update_sync_button_state()
        # Re-apply mood button (it has its own icon logic)
        self.update_mood_button_icon()
        self.update()

    def _apply_sync_button_style(self, active: bool):
        """Apply active (peers in range) or muted (no peers) style to the sync button."""
        from gui.themes.manager import ThemeManager
        t = ThemeManager.get_instance().current
        c = piano_colors()
        border = t.status_active if active else c.FRAME_LIGHT.name()
        hover_border = _parse_rgb(t.status_active).lighter(130).name() if active else c.ACCENT.name()
        self.sync_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {c.FRAME_DARK.name()};
                border: 1px solid {border};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: {hover_border};
            }}
        """)

    def _update_sync_button_state(self):
        """Poll sync state and update button visibility, color, and spin animation."""
        try:
            from core.sync.models import Device
            from core.sync.service import SyncService
            client = SyncService.get_instance().client
            known = Device.select().where(Device.is_self == False).count()
            peers_in_range = client.peer_count > 0
            is_syncing = client.is_syncing
        except Exception:
            known = 0
            peers_in_range = False
            is_syncing = False

        self.sync_button.setVisible(known > 0)
        self._apply_sync_button_style(active=peers_in_range)

        if is_syncing and not self._sync_spin_timer.isActive():
            self._sync_spin_timer.start()
        elif not is_syncing and self._sync_spin_timer.isActive():
            self._sync_spin_timer.stop()
            self._sync_rotation = 0
            self.sync_button.setIcon(self._themed_icon('gui/icons/sync.svg', piano_colors().ACCENT))
            self.sync_button.setIconSize(QSize(14, 14))

    def _on_sync_spin_tick(self):
        """Advance sync icon rotation by one frame."""
        from PyQt6.QtGui import QTransform
        self._sync_rotation = (self._sync_rotation + 12) % 360
        transform = QTransform().rotate(self._sync_rotation)
        rotated = self._sync_icon_pixmap.transformed(transform, Qt.TransformationMode.SmoothTransformation)
        self.sync_button.setIcon(QIcon(rotated))

    def on_sync_button_clicked(self):
        """Open the drawer and navigate to the sync page."""
        if not self.state.toggleable_drawer_visible:
            self.toggle_toggleable_drawer()
        self.music_sheet_widget.navigate_to_sync_page()

    # ===== Mood Management =====

    def on_mood_button_clicked(self):
        """Handle mood button left click - toggle mood bar"""
        if self.state.mood_bar_visible:
            self.mood_bar.close()
        else:
            # Position mood bar to the left of control panel
            button_pos = self.mood_button.mapToGlobal(self.mood_button.rect().topLeft())
            bar_x = button_pos.x() - self.mood_bar.sizeHint().width() - 10
            bar_y = button_pos.y()
            self.mood_bar.show_at_position(QPoint(bar_x, bar_y))
            self.state.mood_bar_visible = True

    def on_mood_selected(self, mood_id: int):
        """Handle mood selection from mood bar"""
        self.state.mood_bar_visible = False
        self.update_mood_button_icon()

    def on_mood_bar_closed(self):
        """Handle mood bar closed"""
        self.state.mood_bar_visible = False

    # ===== Add Task Management =====

    def on_add_task_button_clicked(self):
        """Handle add task button click - show add task widget"""
        # Position widget to the left of the button
        button_pos = self.add_task_button.mapToGlobal(self.add_task_button.rect().topLeft())
        widget_x = button_pos.x() - self.add_task_widget.sizeHint().width() - 10
        widget_y = button_pos.y()
        self.add_task_widget.show_at_position(QPoint(widget_x, widget_y))

    def on_task_created(self):
        """Handle task creation - refresh piano keys and music sheet"""
        # Refresh keys to update next tasks
        self.update_keys_for_window_size()
        # Notify music sheet to refresh pages
        if hasattr(self, 'music_sheet_widget') and self.music_sheet_widget:
            self.music_sheet_widget.refresh_current_page()

    def on_add_task_closed(self):
        """Handle add task widget closed"""
        pass

    def update_mood_button_icon(self):
        """Update mood button icon to show current mood or default"""
        from core.mood.service import MoodService

        c = piano_colors()
        current_log = MoodService.get_current_log()
        if current_log:
            self.mood_button.setText(current_log.mood.symbol)
            self.mood_button.setIcon(QIcon())
        else:
            self.mood_button.setText('')
            self.mood_button.setIcon(self._themed_icon('gui/icons/mood.svg', c.ACCENT))
        self.mood_button.setStyleSheet(self._control_button_stylesheet())

    def eventFilter(self, obj, event):
        """Filter events for mood button right-click and notes widget drag forwarding"""
        # Handle mood button right-click
        if obj == self.mood_button and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.RightButton:
                # Open drawer and navigate to mood page
                if not self.state.toggleable_drawer_visible:
                    self.toggle_toggleable_drawer()
                self.music_sheet_widget.navigate_to_mood_page()
                return True
        
        # Handle notes widget drag events - forward to piano window
        if self.notes_widget is not None and obj == self.notes_widget:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Calculate relative position in piano window coordinates
                    from PyQt6.QtCore import QPointF
                    notes_global_pos = self.notes_widget.mapToGlobal(event.position().toPoint())
                    piano_local_pos = self.mapFromGlobal(notes_global_pos)
                    
                    # Create new event with piano coordinates and forward to piano
                    # PyQt6 requires QPointF
                    from PyQt6.QtGui import QMouseEvent
                    piano_event = QMouseEvent(
                        event.Type.MouseButtonPress,
                        QPointF(piano_local_pos),
                        QPointF(notes_global_pos),
                        event.button(),
                        event.buttons(),
                        event.modifiers()
                    )
                    self.mousePressEvent(piano_event)
                    return True
            
            elif event.type() == event.Type.MouseMove:
                if event.buttons() == Qt.MouseButton.LeftButton:
                    # Forward drag events to piano
                    from PyQt6.QtCore import QPointF
                    notes_global_pos = self.notes_widget.mapToGlobal(event.position().toPoint())
                    piano_local_pos = self.mapFromGlobal(notes_global_pos)
                    
                    from PyQt6.QtGui import QMouseEvent
                    piano_event = QMouseEvent(
                        event.Type.MouseMove,
                        QPointF(piano_local_pos),
                        QPointF(notes_global_pos),
                        event.button(),
                        event.buttons(),
                        event.modifiers()
                    )
                    self.mouseMoveEvent(piano_event)
                    return True
            
            elif event.type() == event.Type.MouseButtonRelease:
                if event.button() == Qt.MouseButton.LeftButton:
                    # Forward release to piano
                    from PyQt6.QtCore import QPointF
                    notes_global_pos = self.notes_widget.mapToGlobal(event.position().toPoint())
                    piano_local_pos = self.mapFromGlobal(notes_global_pos)
                    
                    from PyQt6.QtGui import QMouseEvent
                    piano_event = QMouseEvent(
                        event.Type.MouseButtonRelease,
                        QPointF(piano_local_pos),
                        QPointF(notes_global_pos),
                        event.button(),
                        event.buttons(),
                        event.modifiers()
                    )
                    self.mouseReleaseEvent(piano_event)
                    return True
        
        return super().eventFilter(obj, event)

    # ===== Notes Management =====

    def on_notes_button_clicked(self):
        """Toggle notes widget visibility"""
        if self.notes_widget is None:
            return
            
        if self.state.notes_visible:
            self.notes_widget.close()
        else:
            # Calculate visible portion of window (accounting for hidden drawer mask)
            drawer_width = self.geometry_model.toggleable_drawer_width
            visible_start_x = drawer_width if not self.state.toggleable_drawer_visible else 0
            visible_width = self.width() - visible_start_x
            
            # Position below window, aligned with visible portion
            window_pos = self.pos()
            window_height = self.height()
            notes_x = window_pos.x() + visible_start_x
            notes_y = window_pos.y() + window_height
            
            self.notes_widget.show_at_position(QPoint(notes_x, notes_y), visible_width)
            self.state.notes_visible = True

    def on_notes_closed(self):
        """Handle notes widget closed"""
        self.state.notes_visible = False

    def _update_notes_widget_position(self):
        """Update notes widget position and size when window moves/resizes"""
        if self.state.notes_visible:
            # Calculate visible portion of window (accounting for hidden drawer mask)
            drawer_width = self.geometry_model.toggleable_drawer_width
            visible_start_x = drawer_width if not self.state.toggleable_drawer_visible else 0
            visible_width = self.width() - visible_start_x
            
            # Update position and width to match visible portion
            window_pos = self.pos()
            window_height = self.height()
            new_x = window_pos.x() + visible_start_x
            new_y = window_pos.y() + window_height
            
            self.notes_widget.move(new_x, new_y)
            self.notes_widget.setFixedWidth(visible_width)

    def changeEvent(self, event):
        """Handle window state changes - synchronize notes widget"""
        if event.type() == event.Type.WindowStateChange:
            # Only handle notes widget if it exists (initialized)
            if hasattr(self, 'notes_widget'):
                if self.isMinimized():
                    # Hide notes when piano minimizes
                    if self.state.notes_visible and self.notes_widget.isVisible():
                        self.notes_widget._was_visible_before_hide = True
                        self.notes_widget.hide()
                else:
                    # Restore notes when piano restores
                    if self.notes_widget._was_visible_before_hide:
                        self.notes_widget._was_visible_before_hide = False
                        self.notes_widget.show()
        
        super().changeEvent(event)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        # Check for Ctrl+F (or Cmd+F on macOS) to open search
        if event.key() == Qt.Key.Key_F and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Only open search if drawer is visible
            if self.state.toggleable_drawer_visible:
                self.music_sheet_widget.show_search_bar()
                event.accept()
                return
        
        super().keyPressEvent(event)

    # ===== Cleanup =====

    def _on_habits_changed(self, change_type: str, **kwargs):
        """Handle service change notifications — rebuild keys and repaint."""
        self.update_keys_for_window_size()
        self.update()

    def _on_reminder_notification(self, reminder_id, message: str, urgency: str):
        """Handle reminder notification using ActionHandler (supports all action types)."""
        from core.reminder.service import ReminderService
        from core.reminder.actions import ActionHandler

        reminder = ReminderService.get_by_id(reminder_id)
        ActionHandler.show_notification_for_action(reminder, message, urgency)

    def closeEvent(self, event):
        """Clean up when window closes"""
        # Stop all sessions first (don't wait yet)
        if hasattr(self, 'session_manager'):
            self.session_manager.cleanup()

        if hasattr(self, 'reminder_manager'):
            self.reminder_manager.stop()

        # Wait for monitor threads
        if hasattr(self, 'session_manager'):
            self.session_manager.wait(500)

        if hasattr(self, 'reminder_manager'):
            self.reminder_manager.wait(500)

        # Clean up other managers
        if hasattr(self, 'drawer_animation_manager'):
            self.drawer_animation_manager.cleanup()

        if hasattr(self, 'reorder_mode_manager'):
            self.reorder_mode_manager.cleanup()

        if hasattr(self, 'mood_update_timer'):
            self.mood_update_timer.stop()

        if self.management_window is not None:
            self.management_window.close()

        event.accept()
