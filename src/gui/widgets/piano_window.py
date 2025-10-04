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

import sys
import time
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QRectF
from PyQt6.QtGui import QPainter, QIcon, QPen, QBrush, QPainterPath

from core.db import initialize_database
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed

from ..constants import PianoLayout, PianoColors, Animations, Interactions
from ..models import PianoGeometry, PianoState
from ..managers import SessionProcessManager, AnimationManager, SoundManager, DrawerAnimationManager, WindowSizeManager, ReorderModeManager
from ..painters import FramePainter, KeyPainter, BrassPainter
from .music_sheet_widget import MusicSheetWidget


class PianoFloatingWindow(QWidget):
    """Main piano interface window - orchestrates all components"""

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
        self.state.set_window_size(initial_width, initial_height)
        self.state.toggleable_drawer_visible = False

        self.geometry_model = PianoGeometry(
            window_width=initial_width,
            window_height=initial_height,
            toggleable_drawer_visible=False
        )

        # ===== Load Habits =====
        self.habits = list(Habit.select().order_by(Habit.display_order, Habit.id))
        self.state.num_habits = len(self.habits)
        self.keys = []  # Will be populated by update_keys_for_window_size()

        # ===== Initialize Managers =====
        self.session_manager = SessionProcessManager()
        self.session_manager.elapsed_updated.connect(self.on_elapsed_updated)
        self.session_manager.session_ended.connect(self.on_session_ended)
        self.session_manager.error_occurred.connect(self.on_session_error)
        self.session_manager.start()

        self.animation_manager = AnimationManager(self)
        self.animation_manager.fade_finished.connect(self.on_fade_finished)

        self.drawer_animation_manager = DrawerAnimationManager(self)

        self.sound_manager = SoundManager()

        self.reorder_mode_manager = ReorderModeManager(self)
        self.reorder_mode_manager.pulse_updated.connect(self.update)
        self.reorder_mode_manager.reorder_mode_toggled.connect(self.on_reorder_mode_toggled)
        self.reorder_mode_manager.set_num_keys(len(self.keys))

        # ===== Window Sizing =====
        self.resize(initial_width, initial_height)
        min_width = self.size_manager.get_minimum_width()
        min_height = self.size_manager.get_minimum_height()
        self.setMinimumSize(min_width, min_height)

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

        # ===== Music Sheet Widget (Interactive Drawer Content) =====
        self.music_sheet_widget = MusicSheetWidget(self, sound_manager=self.sound_manager)
        self.music_sheet_widget.habit_updated.connect(self.on_habit_updated_from_sheet)
        self.music_sheet_widget.hide()  # Initially hidden
        self._position_music_sheet_widget()

        # ===== Initialize Keys =====
        self.update_keys_for_window_size()

        # ===== Center Window =====
        self.center_window()

        # ===== Set Window Opacity =====
        self.setWindowOpacity(Animations.WINDOW_OPACITY_NORMAL)

        # ===== Enable Mouse Tracking =====
        self.setMouseTracking(True)

        # ===== Connect State Signals =====
        self.state.window_resized.connect(self.on_window_resized)
        self.state.toggleable_drawer_toggled.connect(self.on_toggleable_drawer_toggled)
        self.size_manager.size_changed.connect(self.on_window_resized)

        # ===== Initialize Toggleable Drawer State =====
        self.drawer_animation_manager.initialize_state(self.state.toggleable_drawer_visible)

    # ===== Window Management =====

    def center_window(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.size().width()) // 2
        y = (screen_geometry.height() - self.size().height()) // 2
        self.move(x, y)

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
            # Size manager approved the resize, update our state
            self.state.set_window_size(new_width, new_height)

    def on_window_resized(self, width, height):
        """Handle window resize state change"""
        self.geometry_model.update(window_width=width, window_height=height)
        self.update_keys_for_window_size()
        self._position_music_sheet_widget()  # Reposition music sheet widget
        self.update()

    # ===== Keys Management =====

    def update_keys_for_window_size(self):
        """Update the keys array based on current window size and scroll position"""
        available_height = self.state.window_height - PianoLayout.FRAME_PADDING_VERTICAL
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
                    new_keys.append({
                        'label': habit.name,
                        'habit': habit,
                        'time': None
                    })
                else:
                    new_keys.append({'label': '', 'habit': None, 'time': None})
        else:
            # No scrolling needed
            self.state.scroll_offset = 0
            self.state.max_scroll_offset = 0

            new_keys = []
            for habit in all_habits[:num_keys_that_fit]:
                new_keys.append({'label': habit.name, 'habit': habit, 'time': None})

            # Fill remaining slots with empty keys
            while len(new_keys) < num_keys_that_fit:
                new_keys.append({'label': '', 'habit': None, 'time': None})

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

        # Draw brass elements (pedals only, hinges replaced by « on fallboard)
        BrassPainter.draw_brass_elements(painter, self.geometry_model.get_pedal_positions())
        BrassPainter.draw_pedal_rods(painter, self.geometry_model.get_pedal_rod_positions())

        # Draw window controls
        self.draw_window_controls(painter)

    def draw_window_controls(self, painter):
        """Draw close and minimize buttons"""
        x_position = self.state.window_width - PianoLayout.CONTROL_X_OFFSET

        # Close button
        close_center = self.geometry_model.close_button_center
        painter.setPen(QPen(PianoColors.BRASS, 1))
        painter.setBrush(QBrush(PianoColors.WOOD_DARK))
        painter.drawEllipse(close_center.x() - 8, close_center.y() - 8, 16, 16)
        painter.setPen(QPen(PianoColors.BRASS_LIGHT))
        painter.drawText(close_center.x() - 4, close_center.y() + 4, '✕')

        # Minimize button
        min_center = self.geometry_model.minimize_button_center
        painter.setPen(QPen(PianoColors.BRASS, 1))
        painter.setBrush(QBrush(PianoColors.WOOD_DARK))
        painter.drawEllipse(min_center.x() - 8, min_center.y() - 8, 16, 16)
        painter.setPen(QPen(PianoColors.BRASS_LIGHT))
        painter.drawText(min_center.x() - 4, min_center.y() + 4, '−')

    # ===== Mouse Events =====

    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            global_pos = event.globalPosition().toPoint()
            local_pos = event.position().toPoint()
            self.state.start_drag(global_pos.x(), global_pos.y(), local_pos.x(), local_pos.y())

            # Check for double-click on piano frame
            current_time = time.time() * 1000
            if current_time - self.state.last_click_time < Interactions.DOUBLE_CLICK_THRESHOLD:
                if self.geometry_model.is_point_in_piano_frame(local_pos):
                    self.hide_window_for_seconds(Interactions.DOUBLE_CLICK_HIDE_DURATION)
                    return

            self.state.last_click_time = current_time

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            local_pos = event.position().toPoint()

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
        else:
            # Update cursor based on hover position
            self.update_cursor_for_position(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
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
        Handle a click at the given position using a declarative click handler registry.

        Click handlers are checked in priority order (highest first).
        Each handler can specify which modes it's active in.
        """
        # Define click handlers with their conditions and actions
        # Format: (condition_fn, action_fn, active_in_reorder_mode)
        click_handlers = [
            # Always-active controls (work in all modes)
            (
                lambda p: (self.geometry_model.close_button_center - p).manhattanLength() < Interactions.CONTROL_BUTTON_CLICK_RADIUS,
                lambda p: self.close(),
                True  # Active in reorder mode
            ),
            (
                lambda p: (self.geometry_model.minimize_button_center - p).manhattanLength() < Interactions.CONTROL_BUTTON_CLICK_RADIUS,
                lambda p: self.showMinimized(),
                True  # Active in reorder mode
            ),
            (
                lambda p: self.geometry_model.is_point_on_pedal(p),
                lambda p: self.reorder_mode_manager.toggle_reorder_mode(),
                True  # Active in reorder mode
            ),

            # Normal-mode-only controls
            (
                lambda p: self.geometry_model.is_point_in_hinge(p),
                lambda p: self.toggle_toggleable_drawer(),
                False  # Only active in normal mode
            ),
            (
                lambda p: self.geometry_model.is_point_in_brass_section(p),
                lambda p: None,  # Consume click, no action
                False  # Only active in normal mode
            ),
            (
                lambda p: self.geometry_model.is_point_in_keys(p),
                lambda p: self.handle_key_click(p),
                False  # Only active in normal mode
            ),
        ]

        # Process click handlers in order
        for condition, action, active_in_reorder in click_handlers:
            # Skip handlers that aren't active in current mode
            if self.reorder_mode_manager.is_reorder_mode and not active_in_reorder:
                continue

            # Check if this handler matches the click position
            if condition(pos):
                action(pos)
                return  # Handler processed the click, stop checking

    def update_cursor_for_position(self, pos: QPoint):
        """Update cursor based on mouse position"""
        cursor = Qt.CursorShape.ArrowCursor

        if (self.geometry_model.is_point_in_control_button(pos) or
            self.geometry_model.is_point_in_keys(pos) or
            self.geometry_model.is_point_in_brass_section(pos) or
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
        """Start or stop a session for the given habit"""
        if self.session_manager.has_active_session(habit.id):
            self.sound_manager.play_sound('end')
            self.end_session(habit)
        else:
            self.sound_manager.play_sound('start')
            self.start_session(habit)

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
        reordered_habits.insert(to_index, dragged)

        # Update display_order in database
        for i, habit in enumerate(reordered_habits):
            habit.display_order = i
            habit.save()

        # Update local state
        self.habits = reordered_habits
        self.update_keys_for_window_size()

        # Play sound
        self.sound_manager.play_sound('page')

    def on_reorder_mode_toggled(self, is_active: bool):
        """Handle reorder mode toggle"""
        # Exit any active key drag
        if self.state.is_dragging_key():
            self.state.end_key_drag()

        # Play sound effect
        if is_active:
            self.sound_manager.play_sound('drawer')
        else:
            self.sound_manager.play_sound('page')

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

        # Show/hide the music sheet widget
        if visible:
            self.music_sheet_widget.show()
            self.music_sheet_widget.raise_()  # Bring to front
        else:
            self.music_sheet_widget.hide()

        self.drawer_animation_manager.start_animation(visible, self.geometry_model.toggleable_drawer_width)

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

    def on_habit_updated_from_sheet(self):
        """Handle habit updates from the music sheet widget"""
        # Reload habits
        self.habits = list(Habit.select().order_by(Habit.display_order, Habit.id))
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
        self.habits = list(Habit.select().order_by(Habit.display_order, Habit.id))
        self.state.num_habits = len(self.habits)
        self.update_keys_for_window_size()
        self.update()

    # ===== Cleanup =====

    def closeEvent(self, event):
        """Clean up when window closes"""
        if hasattr(self, 'session_manager'):
            self.session_manager.cleanup()
            self.session_manager.wait(3000)

        if hasattr(self, 'drawer_animation_manager'):
            self.drawer_animation_manager.cleanup()

        if hasattr(self, 'reorder_mode_manager'):
            self.reorder_mode_manager.cleanup()

        if self.management_window is not None:
            self.management_window.close()

        event.accept()
