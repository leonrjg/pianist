"""
Piano Floating Window - Main window (Refactored)

This is the orchestrator that composes all components together.
Responsibilities:
- Layout composition
- Signal routing between components
- Window-level event handling

Heavy lifting is delegated to:
- Models: PianoGeometry, PianoState
- Managers: SessionProcessManager, AnimationManager, SoundManager
- Painters: FramePainter, KeyPainter, BrassPainter
"""

import time
from typing import Optional
from PyQt6.QtWidgets import QWidget, QApplication, QPushButton, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QSize, pyqtSignal
from PyQt6.QtGui import QPainter, QIcon, QPainterPath

from core.db import initialize_database, db
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from core.util.time import get_friendly_elapsed
from datetime import datetime

from ..constants import PianoLayout, PianoColors, Animations, Interactions
from ..models import PianoGeometry, PianoState
from ..managers import SessionProcessManager, AnimationManager, SoundManager, DrawerAnimationManager, WindowSizeManager, ReorderModeManager, AutoSessionManager, ReminderManager
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

    def __init__(self):
        super().__init__()

        # ===== Initialize Database =====
        initialize_database()

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

        # ===== Load Habits =====
        # Load all habits for AutoSessionManager (includes non-visible, excludes archived)
        all_habits = [h for h in Habit.select().order_by(Habit.display_order, Habit.id) if not h.archived]
        # Load only visible habits for piano keys
        self.habits = [h for h in all_habits if h.visible]
        self.state.num_habits = len(self.habits)
        self.keys = []  # Will be populated by update_keys_for_window_size()

        # ===== Initialize Managers =====
        self.session_manager = SessionProcessManager()
        self.session_manager.elapsed_updated.connect(self.on_elapsed_updated)
        self.session_manager.session_ended.connect(self.on_session_ended)
        self.session_manager.error_occurred.connect(self.on_session_error)
        self.session_manager.start()

        # Auto-session manager for window-based session triggering
        self.auto_session_manager = AutoSessionManager(habits=all_habits)
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
        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
            }}
        """)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Maximize button
        self.maximize_button = QPushButton()
        self.maximize_button.setIcon(QIcon('gui/icons/maximize.svg'))
        self.maximize_button.setIconSize(QSize(14, 14))
        self.maximize_button.setFixedSize(20, 20)
        self.maximize_button.setToolTip('Maximize window')
        self.maximize_button.clicked.connect(self.toggle_maximize)
        self.maximize_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
            }}
        """)
        self.maximize_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Reorder button
        self.reorder_button = QPushButton()
        self.reorder_button.setIcon(QIcon('gui/icons/reorder.svg'))
        self.reorder_button.setIconSize(QSize(14, 14))
        self.reorder_button.setFixedSize(20, 20)
        self.reorder_button.setToolTip('Reorder keys')
        self.reorder_button.clicked.connect(self.reorder_mode_manager.toggle_reorder_mode)
        self.reorder_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
            }}
        """)
        self.reorder_button.setCursor(Qt.CursorShape.PointingHandCursor)

        # Mood button
        self.mood_button = QPushButton()
        self.mood_button.setIcon(QIcon('gui/icons/mood.svg'))
        self.mood_button.setIconSize(QSize(14, 14))
        self.mood_button.setFixedSize(20, 20)
        self.mood_button.setToolTip('Log mood')
        self.mood_button.clicked.connect(self.on_mood_button_clicked)
        self.mood_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
            }}
        """)
        self.mood_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mood_button.installEventFilter(self)

        # Notes button
        self.notes_button = QPushButton()
        self.notes_button.setIcon(QIcon('gui/icons/notes.svg'))
        self.notes_button.setIconSize(QSize(14, 14))
        self.notes_button.setFixedSize(20, 20)
        self.notes_button.setToolTip('Notes')
        self.notes_button.clicked.connect(self.on_notes_button_clicked)
        self.notes_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb(61, 40, 23);
                border: 1px solid rgb(184, 134, 11);
                border-radius: 10px;
            }}
            QPushButton:hover {{
                border-color: rgb(218, 165, 32);
            }}
        """)
        self.notes_button.setCursor(Qt.CursorShape.PointingHandCursor)

        control_layout.addWidget(self.close_button)
        control_layout.addWidget(self.maximize_button)
        control_layout.addWidget(self.reorder_button)
        control_layout.addWidget(self.mood_button)
        control_layout.addWidget(self.notes_button)
        control_layout.addStretch()

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
        """Update the keys array based on current window size and scroll position"""
        available_height = self.height() - PianoLayout.FRAME_PADDING_VERTICAL
        num_keys_that_fit = max(1, int(available_height // PianoLayout.KEY_HEIGHT)) + 2

        all_habits = list(self.habits)
        num_actual_habits = len(all_habits)

        # Determine if scrolling is needed
        self.state.scrolling_enabled = num_actual_habits > num_keys_that_fit

        if self.state.scrolling_enabled:
            # Calculate maximum scroll offset
            self.state.max_scroll_offset = max(0, num_actual_habits - num_keys_that_fit)

            # Create keys array with scroll offset applied
            new_keys = []
            for i in range(num_keys_that_fit):
                habit_index = i + self.state.scroll_offset
                if habit_index < num_actual_habits:
                    habit = all_habits[habit_index]
                    # Use get_next_tasks() to match Index page behavior (shows all upcoming including overdue)
                    schedule = habit.get_schedule()
                    next_tasks = sorted(schedule.get_next_tasks(30 * 24 * 60 * 60))  # 30 days like Index
                    task_dt = next_tasks[0] if next_tasks else None
                    new_keys.append({
                        'label': habit.name,
                        'habit': habit,
                        'time': None,
                        'task_datetime': task_dt,
                        'is_completed': habit.is_task_completed(task_dt) if task_dt else False
                    })
                else:
                    new_keys.append({'label': '', 'habit': None, 'time': None, 'task_datetime': None, 'is_completed': False})
        else:
            # No scrolling needed
            self.state.scroll_offset = 0
            self.state.max_scroll_offset = 0

            new_keys = []
            for habit in all_habits[:num_keys_that_fit]:
                # Use get_next_tasks() to match Index page behavior (shows all upcoming including overdue)
                schedule = habit.get_schedule()
                next_tasks = sorted(schedule.get_next_tasks(30 * 24 * 60 * 60))  # 30 days like Index
                task_dt = next_tasks[0] if next_tasks else None
                new_keys.append({
                    'label': habit.name,
                    'habit': habit,
                    'time': None,
                    'task_datetime': task_dt,
                    'is_completed': habit.is_task_completed(task_dt) if task_dt else False
                })

            # Fill remaining slots with empty keys
            while len(new_keys) < num_keys_that_fit:
                new_keys.append({'label': '', 'habit': None, 'time': None, 'task_datetime': None, 'is_completed': False})

        self.keys = new_keys

        # Update reorder manager with new key count
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
        painter.fillRect(self.rect(), PianoColors.BACKGROUND)

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

    def _toggle_task_completion(self, habit, task_datetime):
        """Toggle task completion state"""
        try:
            normalized_dt = task_datetime.replace(microsecond=0)

            with db.atomic():
                # Check if already completed
                existing = ManualTask.select().where(
                    (ManualTask.habit == habit) &
                    (ManualTask.completed_at == normalized_dt)
                ).first()

                if existing:
                    # Unmark
                    existing.delete_instance()
                else:
                    # Mark complete
                    ManualTask.create(
                        habit=habit,
                        title=None,
                        completed_at=normalized_dt
                    )

            # CRITICAL: Refresh keys immediately to recalculate next tasks
            self.update_keys_for_window_size()

            self.update()

            # Emit signal to update music sheet pages
            if hasattr(self, 'music_sheet_widget'):
                self.music_sheet_widget.habit_updated.emit()

        except Exception as e:
            print(f"Error toggling task completion: {e}")

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            local_pos = event.position().toPoint()

            # Check for checkmark click (only if no active session)
            if not self.session_manager.is_session_active():
                checkmark_index = self._get_checkmark_index_at_point(local_pos)
                if checkmark_index is not None and checkmark_index >= 0 and checkmark_index < len(self.keys):
                    key_data = self.keys[checkmark_index]
                    if key_data.get('habit') and key_data.get('task_datetime'):
                        self._toggle_task_completion(key_data['habit'], key_data['task_datetime'])
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
            # Check for checkmark hover (only if no active session)
            local_pos = event.position().toPoint()
            if not self.session_manager.is_session_active():
                checkmark_index = self._get_checkmark_index_at_point(local_pos)
                if checkmark_index != self.state.hovered_checkmark_index:
                    self.state.hovered_checkmark_index = checkmark_index
                    self.update()
            else:
                # Clear hover if session is active
                if self.state.hovered_checkmark_index is not None:
                    self.state.hovered_checkmark_index = None
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
        """Start a session in separate process"""
        try:
            self.session_manager.start_session(habit)
            print(f"Starting session process for {habit.name}")
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

        # Reorder the habits list
        reordered_habits = list(self.habits)
        dragged = reordered_habits.pop(from_index)
        # Adjust target index if dragging downward (after pop, indices shift)
        adjusted_to_index = to_index if to_index <= from_index else to_index - 1
        reordered_habits.insert(adjusted_to_index, dragged)

        # Update display_order in database
        for i, habit in enumerate(reordered_habits):
            habit.display_order = i
            habit.save()

        # Update local state
        self.habits = reordered_habits
        self.update_keys_for_window_size()

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
        # Reload all habits and filter visible ones for piano keys (exclude archived)
        all_habits = [h for h in Habit.select().order_by(Habit.display_order, Habit.id) if not h.archived]
        self.habits = [h for h in all_habits if h.visible]
        self.state.num_habits = len(self.habits)

        # Refresh keys
        self.update_keys_for_window_size()
        self.update()

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
        # Reload all habits and filter visible ones for piano keys (exclude archived)
        all_habits = [h for h in Habit.select().order_by(Habit.display_order, Habit.id) if not h.archived]
        self.habits = [h for h in all_habits if h.visible]
        self.state.num_habits = len(self.habits)

        self.update_keys_for_window_size()
        self.update()

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

    def update_mood_button_icon(self):
        """Update mood button icon to show current mood or default"""
        from core.mood.mood import Mood
        
        current_log = Mood.get_current_mood_log()
        if current_log:
            # Show current mood emoji
            self.mood_button.setText(current_log.mood.symbol)
            self.mood_button.setIcon(QIcon())
            self.mood_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb(61, 40, 23);
                    border: 1px solid rgb(184, 134, 11);
                    border-radius: 10px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    border-color: rgb(218, 165, 32);
                }}
            """)
        else:
            # Show default smiley icon
            self.mood_button.setText('')
            self.mood_button.setIcon(QIcon('gui/icons/mood.svg'))
            self.mood_button.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb(61, 40, 23);
                    border: 1px solid rgb(184, 134, 11);
                    border-radius: 10px;
                }}
                QPushButton:hover {{
                    border-color: rgb(218, 165, 32);
                }}
            """)

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

    def _on_reminder_notification(self, title: str, message: str, urgency: str):
        """Handle reminder notification request."""
        self.notification_service.show_reminder_notification(title, message, urgency)

    def closeEvent(self, event):
        """Clean up when window closes"""
        # Stop all threads first (don't wait yet)
        if hasattr(self, 'session_manager'):
            self.session_manager.cleanup()

        if hasattr(self, 'reminder_manager'):
            self.reminder_manager.stop()

        # Now wait for threads with short timeouts (parallel)
        if hasattr(self, 'session_manager'):
            self.session_manager.wait(500)  # Reduced from 3000ms

        if hasattr(self, 'reminder_manager'):
            self.reminder_manager.wait(500)  # Reduced from 2000ms

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
