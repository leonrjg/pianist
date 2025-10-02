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
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint
from PyQt6.QtGui import QPainter, QIcon, QPen, QBrush

from core.db import initialize_database
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed

from ..constants import PianoLayout, PianoColors, Animations, Interactions
from ..models import PianoGeometry, PianoState
from ..managers import SessionProcessManager, AnimationManager, SoundManager, DrawerAnimationManager, WindowSizeManager
from ..painters import FramePainter, KeyPainter, BrassPainter


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
        self.state.fallboard_visible = False

        self.geometry_model = PianoGeometry(
            window_width=initial_width,
            window_height=initial_height,
            fallboard_visible=False
        )

        # ===== Load Habits =====
        self.habits = list(Habit.select())
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
        self.state.fallboard_toggled.connect(self.on_fallboard_toggled)
        self.size_manager.size_changed.connect(self.on_window_resized)

        # ===== Initialize Drawer State =====
        self.drawer_animation_manager.initialize_state(self.state.fallboard_visible)

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

    # ===== Painting =====

    def paintEvent(self, event):
        """Main paint event - delegates to painters"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), PianoColors.BACKGROUND)

        # Delegate to painters (window mask controls visibility)
        FramePainter.draw_frame(painter, self.geometry_model)
        KeyPainter.draw_keys(painter, self.geometry_model, self.state, self.keys)

        # Draw brass elements (hinges and pedals)
        BrassPainter.draw_brass_elements(painter, self.geometry_model.get_hinge_positions())
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
            pos = event.globalPosition().toPoint()
            self.state.start_drag(pos.x(), pos.y())

            # Check for double-click on piano frame
            current_time = time.time() * 1000
            if current_time - self.state.last_click_time < Interactions.DOUBLE_CLICK_THRESHOLD:
                if self.geometry_model.is_point_in_piano_frame(event.position().toPoint()):
                    self.hide_window_for_seconds(Interactions.DOUBLE_CLICK_HIDE_DURATION)
                    return

            self.state.last_click_time = current_time

    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag_start_x, drag_start_y = self.state.get_drag_start()
            if drag_start_x != 0 or drag_start_y != 0:
                current_pos = event.globalPosition().toPoint()
                diff_x = current_pos.x() - drag_start_x
                diff_y = current_pos.y() - drag_start_y

                # Check if we've moved enough to consider this a drag
                if not self.state.is_dragging:
                    distance = (diff_x ** 2 + diff_y ** 2) ** 0.5
                    if distance > Interactions.DRAG_THRESHOLD:
                        self.state.is_dragging = True

                # Move window if dragging
                if self.state.is_dragging:
                    self.move(self.pos() + QPoint(diff_x, diff_y))
                    self.state.start_drag(current_pos.x(), current_pos.y())
        else:
            # Update cursor based on hover position
            self.update_cursor_for_position(event.position().toPoint())

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only handle clicks if we haven't moved (not a drag)
            if not self.state.is_dragging:
                click_pos = event.position().toPoint()

                # Check for control button clicks
                if (self.geometry_model.close_button_center - click_pos).manhattanLength() < Interactions.CONTROL_BUTTON_CLICK_RADIUS:
                    self.close()
                    return

                if (self.geometry_model.minimize_button_center - click_pos).manhattanLength() < Interactions.CONTROL_BUTTON_CLICK_RADIUS:
                    self.showMinimized()
                    return

                # Check for brass hinge clicks (drawer toggle)
                if self.geometry_model.is_point_in_hinge(click_pos):
                    self.toggle_fallboard()
                    return

                # Check for brass section clicks (management area)
                if self.geometry_model.is_point_in_brass_section(click_pos):
                    self.open_management_window()
                    return

                # Check for key clicks
                self.handle_key_click(click_pos)

            # Reset drag state
            self.state.end_drag()

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
            self.sound_manager.play_end_sound()
            self.end_session(habit)
        else:
            self.sound_manager.play_start_sound()
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

    # ===== Fallboard Toggle =====

    def toggle_fallboard(self):
        """Toggle the fallboard visibility"""
        self.state.toggle_fallboard()

    def on_fallboard_toggled(self, visible: bool):
        """
        Handle drawer toggle state change.

        Delegates animation to DrawerAnimationManager which handles the window mask
        reveal/hide effect.
        """
        self.geometry_model.update(fallboard_visible=visible)
        self.drawer_animation_manager.start_animation(visible, self.geometry_model.drawer_width)

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

    # ===== Management Window =====

    def open_management_window(self):
        """Open the management window"""
        if self.management_window is None:
            from gui.management_window import HabitManagementWindow
            self.management_window = HabitManagementWindow()
            self.management_window.habit_updated.connect(self.refresh_habits)

        self.management_window.show()
        self.management_window.raise_()
        self.management_window.activateWindow()

    def refresh_habits(self):
        """Refresh habits list when management window updates them"""
        self.habits = list(Habit.select())
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

        if self.management_window is not None:
            self.management_window.close()

        event.accept()
