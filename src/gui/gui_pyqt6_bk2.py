import sys
import multiprocessing
import os
import time
from PyQt6.QtWidgets import (QApplication, QWidget)
from PyQt6.QtCore import Qt, QTimer, QRect, QPoint, QThread, pyqtSignal, QUrl, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QLinearGradient, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QSoundEffect

from core.db import initialize_database
from core.habit.habit import Habit
from core.util.time import get_friendly_elapsed

# Constants
KEY_PRESS_DURATION = 400  # milliseconds
SOUND_FILES = {
    'start': "gui/sounds/play.wav",
    'end': "gui/sounds/stop.wav"
}
BLACK_KEY_WIDTH_RATIO = 0.45
BLACK_KEY_HEIGHT_RATIO = 0.5


def session_worker_process(habit_id, habit_name, command_queue, result_queue):
    """Worker process function that runs Session completely isolated"""
    try:
        # Import inside process to avoid Qt conflicts
        import time
        from core.session import Session
        from core.habit.habit import Habit

        # Reconstruct habit object in this process
        habit = Habit.get_by_id(habit_id)
        session = Session(habit)
        session.start()

        print(f"Session started for {habit_name} in process {os.getpid()}")

        # Main loop: handle commands and send updates
        while True:
            try:
                # Check for commands (non-blocking)
                if not command_queue.empty():
                    command = command_queue.get_nowait()
                    if command == 'stop':
                        break
                    elif command == 'get_elapsed':
                        elapsed = session.get_elapsed_time()
                        result_queue.put(('elapsed', habit_id, elapsed))

                # Send periodic elapsed time updates
                elapsed = session.get_elapsed_time()
                result_queue.put(('elapsed', habit_id, elapsed))

                time.sleep(1)  # Update every second

            except Exception as e:
                result_queue.put(('error', habit_id, str(e)))
                break

        # Clean shutdown
        session.end(ended_by="process_stop")
        result_queue.put(('ended', habit_id))
        print(f"Session ended for {habit_name}")

    except Exception as e:
        try:
            result_queue.put(('error', habit_id, str(e)))
        except Exception:
            pass  # Queue might be closed


class SessionProcessManager(QThread):
    """Manages communication with session processes"""
    elapsed_updated = pyqtSignal(int, int)  # habit_id, elapsed_seconds
    session_ended = pyqtSignal(int)  # habit_id
    error_occurred = pyqtSignal(str)  # error message

    def __init__(self):
        super().__init__()
        self.processes = {}  # habit_id -> (process, command_queue, result_queue)
        self.running = True

    def start_session(self, habit):
        """Start a session in a separate process"""
        try:
            # Create communication queues
            command_queue = multiprocessing.Queue()
            result_queue = multiprocessing.Queue()

            # Start worker process
            process = multiprocessing.Process(
                target=session_worker_process,
                args=(habit.id, habit.name, command_queue, result_queue)
            )
            process.start()

            # Store process info
            self.processes[habit.id] = (process, command_queue, result_queue)
            print(f"Started session process for {habit.name}")

        except Exception as e:
            self.error_occurred.emit(f"Failed to start session process: {str(e)}")

    def stop_session(self, habit_id):
        """Stop a session process - non-blocking"""
        if habit_id in self.processes:
            process, command_queue, result_queue = self.processes[habit_id]
            try:
                # Send stop command
                command_queue.put('stop')
                print(f"Sent stop command to session process for habit {habit_id}")

                # Don't wait for process - let the monitoring loop handle cleanup
                # The run() method will detect when process ends and clean up

            except Exception as e:
                self.error_occurred.emit(f"Error stopping session: {str(e)}")

    def run(self):
        """Monitor all session processes for updates"""
        while self.running:
            # Check all result queues for updates
            for habit_id, (process, command_queue, result_queue) in list(self.processes.items()):
                try:
                    # Check if process is still alive
                    if not process.is_alive():
                        self.session_ended.emit(habit_id)
                        del self.processes[habit_id]
                        print(f"Session process for habit {habit_id} has ended")
                        continue

                    # Check for results (non-blocking)
                    while not result_queue.empty():
                        try:
                            message = result_queue.get_nowait()
                            msg_type, msg_habit_id, data = message

                            if msg_type == 'elapsed':
                                self.elapsed_updated.emit(msg_habit_id, data)
                            elif msg_type == 'ended':
                                self.session_ended.emit(msg_habit_id)
                                if msg_habit_id in self.processes:
                                    del self.processes[msg_habit_id]
                            elif msg_type == 'error':
                                self.error_occurred.emit(data)

                        except:
                            break  # No more messages

                except Exception as e:
                    self.error_occurred.emit(f"Process monitoring error: {str(e)}")

            # Small delay to prevent busy waiting
            self.msleep(100)

    def cleanup(self):
        """Clean up all processes"""
        self.running = False

        # Send stop commands to all processes
        for habit_id, (process, command_queue, result_queue) in list(self.processes.items()):
            try:
                command_queue.put('stop')
            except:
                pass

        # Give processes a moment to stop gracefully
        self.msleep(500)

        self.processes.clear()


class PianoFloatingWindow(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize database
        initialize_database()

        # Window setup
        self.setWindowTitle("Pianist")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowIcon(QIcon('etc.png'))

        # Window dimensions - vertical orientation
        self.width = 280
        self.height = 315  # Default window height
        self.key_height = 40  # Fixed key height for consistency
        self.frame_padding = 60  # Top and bottom padding

        # Piano-realistic color scheme
        self.colors = {
            'white_key': QColor(253, 252, 248),
            'white_key_pressed': QColor(245, 243, 237),
            'white_key_shadow': QColor(232, 230, 224),
            'black_key': QColor(26, 25, 22),
            'black_key_shine': QColor(42, 41, 37),
            'black_key_text': QColor(180, 180, 180),
            'wood_dark': QColor(61, 40, 23),
            'wood_medium': QColor(92, 61, 46),
            'wood_light': QColor(122, 80, 64),
            'wood_highlight': QColor(141, 95, 74),
            'brass': QColor(184, 134, 11),
            'brass_light': QColor(218, 165, 32),
            'text': QColor(74, 74, 74),
            'fallboard': QColor(44, 24, 16),
            'key_gap': QColor(26, 26, 26),
            'background': QColor(26, 26, 26)
        }

        # Load habits from database and map to piano keys
        self.habits = list(Habit.select())
        self.time_displays = {}  # habit_id -> current time text

        # Scroll state for key navigation
        self.scroll_offset = 0
        self.max_scroll_offset = 0
        self.scrolling_enabled = False
        self.scroll_accumulator = 0.0

        # Initialize process manager
        self.process_manager = SessionProcessManager()
        self.process_manager.elapsed_updated.connect(self.on_elapsed_updated)
        self.process_manager.session_ended.connect(self.on_session_ended)
        self.process_manager.error_occurred.connect(self.on_session_error)
        self.process_manager.start()

        # Management window (lazily initialized)
        self.management_window = None

        # Create initial key data from habits and calculate dynamic keys
        self.update_keys_for_window_size()

        # Set initial size and minimum size
        self.resize(self.width, self.height)
        self.setMinimumSize(250, 200)


        # Set up dragging
        self.drag_start_position = None
        self.has_moved = False
        self.drag_threshold = 5  # Minimum pixels to consider it a drag

        # Double-click tracking for hiding window
        self.last_click_time = 0
        self.double_click_threshold = 200  # milliseconds
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.show_window_after_hide)

        # Fade animation setup
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)  # 300ms fade duration
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation.finished.connect(self.on_fade_finished)
        self.is_fading_out = False

        # Visual effect state for white key presses
        self.pressed_key = None
        self.press_timer = QTimer()
        self.press_timer.setSingleShot(True)
        self.press_timer.timeout.connect(self.clear_key_press)

        # Center window on screen
        self.center_window()

        # Setup sound effect
        self.setup_sound()

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # Update internal dimensions when window is resized
        self.width = self.size().width()
        self.height = self.size().height()

        # Recalculate keys based on new window size
        self.update_keys_for_window_size()

        self.update()  # Trigger repaint

    def update_keys_for_window_size(self):
        """Update the keys array based on current window size and scroll position"""
        # Calculate how many keys can fit in the current window
        available_height = self.height - self.frame_padding
        num_keys_that_fit = max(1, int(available_height // self.key_height)) + 2

        # Get all actual habits (non-None keys)
        all_habits = list(self.habits)
        num_actual_habits = len(all_habits)

        # Determine if scrolling is needed
        self.scrolling_enabled = num_actual_habits > num_keys_that_fit

        if self.scrolling_enabled:
            # Calculate maximum scroll offset
            self.max_scroll_offset = max(0, num_actual_habits - num_keys_that_fit)

            # Ensure scroll offset is within bounds
            self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll_offset))

            # Create keys array with scroll offset applied
            new_keys = []
            for i in range(num_keys_that_fit):
                habit_index = i + self.scroll_offset
                if habit_index < num_actual_habits:
                    habit = all_habits[habit_index]
                    new_keys.append({
                        'label': habit.name,
                        'habit': habit,
                        'time': None
                    })
                else:
                    # Shouldn't happen in scrolling mode, but safety fallback
                    new_keys.append({
                        'label': '',
                        'habit': None,
                        'time': None
                    })
        else:
            # No scrolling needed - use original padding behavior
            self.scroll_offset = 0
            self.max_scroll_offset = 0

            new_keys = []

            # Add actual habit keys first
            for i, habit in enumerate(all_habits[:num_keys_that_fit]):
                new_keys.append({
                    'label': habit.name,
                    'habit': habit,
                    'time': None
                })

            # Fill remaining slots with empty keys for padding
            while len(new_keys) < num_keys_that_fit:
                new_keys.append({
                    'label': '',
                    'habit': None,
                    'time': None
                })

        # Only update if the keys have actually changed
        keys_changed = (not hasattr(self, 'keys') or
                       len(new_keys) != len(self.keys) or
                       any(new_keys[i]['label'] != self.keys[i]['label']
                           for i in range(min(len(new_keys), len(self.keys)))))

        if keys_changed:
            self.keys = new_keys
            scroll_status = f" (scrolling: {self.scroll_offset}/{self.max_scroll_offset})" if self.scrolling_enabled else " (no scroll)"

    def center_window(self):
        """Center the window on screen"""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        x = (screen_geometry.width() - self.size().width()) // 2
        y = (screen_geometry.height() - self.size().height()) // 2
        self.move(x, y)


    def clear_key_press(self):
        """Clear the pressed key visual effect"""
        self.pressed_key = None
        self.update()

    def _create_sound_player(self, file_key):
        """Create a sound player for the given file key"""
        file_path = SOUND_FILES[file_key]
        if os.path.exists(file_path):
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(file_path))
            return effect
        return None

    def setup_sound(self):
        """Setup sound effects"""
        try:
            self.start_player = self._create_sound_player('start')
            self.end_player = self._create_sound_player('end')

            if not self.start_player and not self.end_player:
                print(f"Warning: No sound files found ({', '.join(SOUND_FILES.values())})")

        except Exception as e:
            print(f"Error setting up sound: {e}")
            self.start_player = None
            self.end_player = None

    def play_start_sound(self):
        """Play the session start sound effect"""
        try:
            if self.start_player:
                self.start_player.play()
        except Exception as e:
            print(f"Error playing start sound: {e}")

    def play_end_sound(self):
        """Play the session end sound effect"""
        try:
            if self.end_player:
                self.end_player.play()
        except Exception as e:
            print(f"Error playing end sound: {e}")


    def mousePressEvent(self, event):
        """Handle mouse press for dragging and double-click detection"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.globalPosition().toPoint()
            self.has_moved = False

            # Check for double-click on piano frame (but not on keybed)
            current_time = time.time() * 1000  # Convert to milliseconds
            if current_time - self.last_click_time < self.double_click_threshold:
                # This is a double-click
                if self.is_piano_frame_click(event.position().toPoint()):
                    self.hide_window_for_seconds(5)
                    return

            self.last_click_time = current_time

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging and cursor updates"""
        if event.buttons() == Qt.MouseButton.LeftButton and self.drag_start_position:
            current_pos = event.globalPosition().toPoint()
            diff = current_pos - self.drag_start_position

            # Check if we've moved enough to consider this a drag
            if not self.has_moved:
                distance = (diff.x() ** 2 + diff.y() ** 2) ** 0.5
                if distance > self.drag_threshold:
                    self.has_moved = True

            # Only move window if we're in drag mode
            if self.has_moved:
                self.move(self.pos() + diff)
                self.drag_start_position = current_pos
        else:
            # Update cursor based on hover position when not dragging
            self.update_cursor_for_position(event.position().toPoint())

    def update_cursor_for_position(self, pos):
        """Update cursor based on mouse position over clickable elements"""
        cursor = Qt.CursorShape.ArrowCursor  # Default cursor

        # Check if hovering over clickable elements
        if self.is_control_button_area(pos) or self.is_key_area(pos) or self.is_brass_section_click(pos):
            cursor = Qt.CursorShape.PointingHandCursor

        self.setCursor(cursor)

    def is_control_button_area(self, pos):
        """Check if position is over control buttons (close/minimize)"""
        x_position = self.width - 40

        # Close button
        close_center = QPoint(x_position + 20, 30)
        if (pos - close_center).manhattanLength() < 10:
            return True

        # Minimize button
        min_center = QPoint(x_position + 20, 60)
        if (pos - min_center).manhattanLength() < 10:
            return True

        return False

    def is_key_area(self, pos):
        """Check if position is over piano keys area"""
        keys_start_x = 95
        keys_end_x = self.width - 40

        # Check if in key area bounds
        if keys_start_x <= pos.x() <= keys_end_x:
            y_relative = pos.y() - 10
            if y_relative >= 0:
                key_index = int(y_relative // self.key_height)
                if 0 <= key_index < len(self.keys):
                    # Only show pointer for keys with actual habits
                    key_data = self.keys[key_index]
                    return key_data.get('habit') is not None
        return False

    def paintEvent(self, event):
        """Custom paint event to draw the piano interface"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw background
        painter.fillRect(self.rect(), self.colors['background'])

        # Draw piano frame and components
        self.draw_piano_frame(painter)
        self.draw_piano_keys(painter)
        self.draw_piano_details(painter)
        self.draw_window_controls(painter)
        self.draw_scroll_indicators(painter)

    def draw_piano_frame(self, painter):
        """Draw realistic piano wooden frame for vertical orientation"""
        frame_width = 90

        # Left wooden panel with wood grain effect
        for i in range(frame_width):
            shade = i / frame_width
            color = self.interpolate_color(self.colors['wood_dark'], self.colors['wood_medium'], shade * 0.3)
            painter.setPen(QPen(color, 1))
            painter.drawLine(i, 0, i, self.height)

        # Piano fallboard area
        fallboard_x = frame_width - 25
        painter.setBrush(QBrush(self.colors['fallboard']))
        painter.drawRect(fallboard_x, 10, 10 - fallboard_x, self.height - 10 - 10)

        # Brass hinges on fallboard
        self._draw_brass_elements(painter, [
            (fallboard_x + 5, 50 - 4, 8, 8),
            (fallboard_x + 5, self.height - 50 - 4, 8, 8)
        ])

        # Key bed
        painter.setPen(QPen(QColor(10, 10, 10)))
        painter.setBrush(QBrush(QColor(10, 10, 10)))
        painter.drawRect(frame_width, 0, 5, self.height)

        # Right frame
        right_frame_x = self.width - 40
        self.draw_gradient_rect(painter, right_frame_x, 0, self.width, self.height,
                               self.colors['wood_medium'], self.colors['wood_dark'], vertical=True)

    def draw_piano_keys(self, painter):
        """Draw realistic piano keys for vertical orientation"""
        keys_start_x = 95
        keys_end_x = self.width - 40
        key_width = keys_end_x - keys_start_x

        key_height = self.key_height

        # Calculate and cache the time display area
        black_key_width = int(key_width * BLACK_KEY_WIDTH_RATIO)
        self.time_display_area = QRect(keys_end_x - black_key_width, 10, black_key_width, self.height - 20)

        # Draw white keys first
        for i, key_data in enumerate(self.keys):
            y = 5 + (i * key_height)

            # Key gap (black line between keys)
            if i > 0:
                painter.setPen(QPen(self.colors['key_gap'], 1))
                painter.drawLine(keys_start_x, int(y), keys_end_x, int(y))

            # Check if this key is currently pressed
            is_pressed = self.pressed_key == i

            # White key with 3D effect and press state
            if is_pressed:
                # Pressed state: darker color and subtle shadow
                key_color = self.colors['white_key_pressed']
                painter.setPen(QPen(key_color))
                painter.setBrush(QBrush(key_color))
                key_rect = QRect(keys_start_x, int(y + 2), key_width, int(key_height - 2))
                painter.drawRect(key_rect)

                shadow_color = QColor(self.colors['white_key_shadow'])
                shadow_color.setAlpha(120)
                painter.setPen(QPen(shadow_color, 2))
            else:
                # Normal state
                painter.setPen(QPen(self.colors['white_key']))
                painter.setBrush(QBrush(self.colors['white_key']))
                key_rect = QRect(keys_start_x, int(y + 1), key_width, int(key_height - 1))
                painter.drawRect(key_rect)

            # Key front edge (curved edge like real piano keys)
            painter.setPen(QPen(self.colors['white_key_shadow']))
            painter.setBrush(QBrush(self.colors['white_key_shadow']))
            painter.drawChord(keys_start_x - 10, int(y + 2), 18, int(key_height - 4), 270 * 16, 180 * 16)

            # Label on key
            painter.setPen(QPen(self.colors['text']))
            painter.setFont(QFont('Microsoft Sans Serif', 12))
            label_rect = QRect(keys_start_x + 15, int(y), key_width - 25, int(key_height))
            painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                           key_data.get('label', ''))

        # Draw black keys (between white keys for time display) - reuse calculated dimensions
        black_key_height = key_height * BLACK_KEY_HEIGHT_RATIO

        for i in range(len(self.keys) - 1):
            # Position between current and next white key
            y = 5 + ((i + 1) * key_height) - (black_key_height / 2)
            x = keys_end_x - black_key_width

            # Black key with gradient
            self.draw_gradient_rect(painter, int(x), int(y), keys_end_x + 1, int(y + black_key_height),
                                   self.colors['black_key_shine'], self.colors['black_key'], vertical=False)

            # Black key front edge
            painter.setPen(QPen(QColor(105, 105, 105)))
            painter.setBrush(QBrush(QColor(105, 105, 105)))
            painter.drawRect(int(x - 2), int(y), 2, int(black_key_height))

            # Time text on black key
            painter.setPen(QPen(self.colors['black_key_text']))
            painter.setFont(QFont('Helvetica', 12))
            text_rect = QRect(int(x), int(y), int(black_key_width), int(black_key_height))

            # Find if there's a time display for the corresponding habit
            time_text = ""
            if i < len(self.keys):
                habit = self.keys[i].get('habit')
                if habit and habit.id in self.time_displays:
                    time_text = self.time_displays[habit.id]

            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, time_text)

    def draw_gradient_rect(self, painter, x1, y1, x2, y2, color1, color2, vertical=False):
        """Draw a rectangle with gradient fill"""
        gradient = QLinearGradient()
        if vertical:
            gradient.setStart(0, y1)
            gradient.setFinalStop(0, y2)
        else:
            gradient.setStart(x1, 0)
            gradient.setFinalStop(x2, 0)

        gradient.setColorAt(0, color1)
        gradient.setColorAt(1, color2)

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def interpolate_color(self, color1, color2, ratio):
        """Interpolate between two QColors"""
        r = int(color1.red() + (color2.red() - color1.red()) * ratio)
        g = int(color1.green() + (color2.green() - color1.green()) * ratio)
        b = int(color1.blue() + (color2.blue() - color1.blue()) * ratio)
        return QColor(r, g, b)

    def _draw_brass_elements(self, painter, elements):
        """Draw brass elements (hinges, pedals) with consistent styling"""
        brass_color = self.colors['brass']
        painter.setPen(QPen(brass_color, 1))
        painter.setBrush(QBrush(brass_color))
        for x, y, w, h in elements:
            painter.drawEllipse(x, y, w, h)

    def draw_piano_details(self, painter):
        """Add realistic piano details"""
        # Pedals at the right side (decorative elements)
        pedal_x = self.width - 25
        pedal_origin_y = self.height // 2 + 10
        pedal_positions = [pedal_origin_y - 25, pedal_origin_y, pedal_origin_y + 25]

        # Draw pedals
        pedal_elements = [(pedal_x - 5, y - 5, 10, 10) for y in pedal_positions]
        self._draw_brass_elements(painter, pedal_elements)

        # Draw pedal rods
        brass_color = self.colors['brass']
        painter.setPen(QPen(brass_color, 2))
        for y in pedal_positions:
            painter.drawLine(pedal_x - 5, y, pedal_x - 13, y)

    def draw_window_controls(self, painter):
        """Add minimize and close buttons styled as piano buttons"""
        x_position = self.width - 40

        # Close button
        close_y = 20
        painter.setPen(QPen(self.colors['brass'], 1))
        painter.setBrush(QBrush(self.colors['wood_dark']))
        painter.drawEllipse(x_position + 20 - 8, close_y - 8, 16, 16)

        painter.setPen(QPen(self.colors['brass_light']))
        painter.drawText(x_position + 20 - 4, close_y + 4, '✕')

        # Minimize button
        min_y = 40
        painter.setPen(QPen(self.colors['brass'], 1))
        painter.setBrush(QBrush(self.colors['wood_dark']))
        painter.drawEllipse(x_position + 20 - 8, min_y - 8, 16, 16)

        painter.setPen(QPen(self.colors['brass_light']))
        painter.setFont(QFont('Microsoft Sans Serif', 12, QFont.Weight.Bold))
        painter.drawText(x_position + 20 - 4, min_y + 4, '−')

    def draw_scroll_indicators(self, painter):
        """Draw scroll indicators when scrolling is enabled"""
        if not self.scrolling_enabled:
            return

        # Position indicators on the left wooden frame
        indicator_x = 15
        keys_area_start = 10
        keys_area_height = self.height - 20

        # Draw scroll track background
        track_width = 4
        track_x = indicator_x
        track_y = keys_area_start + 20
        track_height = keys_area_height - 40

        painter.setPen(QPen(self.colors['wood_dark'], 1))
        painter.setBrush(QBrush(self.colors['wood_dark']))
        painter.drawRect(track_x, track_y, track_width, track_height)

        # Calculate scroll thumb position and size
        if self.max_scroll_offset > 0:
            thumb_height = max(8, track_height // 4)
            scroll_ratio = self.scroll_offset / self.max_scroll_offset
            thumb_y = track_y + scroll_ratio * (track_height - thumb_height)

            # Draw scroll thumb
            painter.setPen(QPen(self.colors['brass'], 1))
            painter.setBrush(QBrush(self.colors['brass']))
            painter.drawRect(track_x - 1, int(thumb_y), track_width + 2, int(thumb_height))

        # Draw scroll arrows at top and bottom
        arrow_size = 6
        arrow_color = self.colors['brass'] if self.scroll_offset > 0 else self.colors['wood_medium']

        # Up arrow (can scroll up if scroll_offset > 0)
        painter.setPen(QPen(arrow_color, 2))
        up_arrow_y = track_y - 10
        painter.drawLine(indicator_x - 2, up_arrow_y + 4, indicator_x + 2, up_arrow_y)
        painter.drawLine(indicator_x + 2, up_arrow_y, indicator_x + 6, up_arrow_y + 4)

        # Down arrow (can scroll down if scroll_offset < max_scroll_offset)
        arrow_color = self.colors['brass'] if self.scroll_offset < self.max_scroll_offset else self.colors['wood_medium']
        painter.setPen(QPen(arrow_color, 2))
        down_arrow_y = track_y + track_height + 6
        painter.drawLine(indicator_x - 2, down_arrow_y, indicator_x + 2, down_arrow_y + 4)
        painter.drawLine(indicator_x + 2, down_arrow_y + 4, indicator_x + 6, down_arrow_y)

    def mouseReleaseEvent(self, event):
        """Handle mouse release for button clicks"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Only handle clicks if we haven't moved (not a drag)
            if not self.has_moved:
                # Check for control button clicks
                x_position = self.width - 40
                click_pos = event.position().toPoint()  # Convert to QPoint

                # Close button
                close_center = QPoint(x_position + 20, 20)
                if (click_pos - close_center).manhattanLength() < 10:
                    self.close()
                    return

                # Minimize button
                min_center = QPoint(x_position + 20, 40)
                if (click_pos - min_center).manhattanLength() < 10:
                    self.showMinimized()
                    return

                # Check for brass section clicks (management area)
                if self.is_brass_section_click(click_pos):
                    self.open_management_window()
                    return

                # Check for key clicks
                self.handle_key_click(click_pos)

            # Reset drag state
            self.drag_start_position = None
            self.has_moved = False

    def wheelEvent(self, event):
        """Handle mouse wheel events for scrolling through keys"""
        if self.scrolling_enabled:
            # Get scroll delta (positive = scroll up, negative = scroll down)
            delta = event.angleDelta().y()

            # Use pixel delta for touchpad precision if available
            if hasattr(event, 'pixelDelta') and not event.pixelDelta().isNull():
                pixel_delta = event.pixelDelta().y()
                # Scale pixel delta to scroll units (more sensitive)
                scroll_amount = pixel_delta / 30.0  # Adjust sensitivity here
            else:
                # Fallback to angle delta for mouse wheels
                # Much more sensitive than before - use smaller divisor
                scroll_amount = delta / 40.0  # Was 120, now 40 for smoother scrolling

            # Accumulate fractional scrolling for smooth movement
            if not hasattr(self, 'scroll_accumulator'):
                self.scroll_accumulator = 0.0

            self.scroll_accumulator += scroll_amount

            # Convert accumulated scroll to integer steps
            scroll_steps = int(self.scroll_accumulator)
            self.scroll_accumulator -= scroll_steps

            # Update scroll offset if we have accumulated enough for at least one step
            if scroll_steps != 0:
                old_offset = self.scroll_offset
                self.scroll_offset = max(0, min(self.scroll_offset - scroll_steps, self.max_scroll_offset))

                # Only update if scroll position actually changed
                if self.scroll_offset != old_offset:
                    self.update_keys_for_window_size()
                    self.update()  # Trigger repaint

            event.accept()
        else:
            # Pass the event to parent if scrolling is not enabled
            super().wheelEvent(event)

    def handle_key_click(self, click_pos):
        """Handle piano key clicks"""
        keys_start_x = 95
        keys_end_x = self.width - 40
        key_height = self.key_height

        # Check if click is in key area
        if keys_start_x <= click_pos.x() <= keys_end_x:
            # Determine which key was clicked
            y_relative = click_pos.y() - 10
            if y_relative >= 0:
                key_index = int(y_relative // key_height)
                if 0 <= key_index < len(self.keys):
                    key_data = self.keys[key_index]
                    habit = key_data.get('habit')

                    # Trigger visual press effect for white keys
                    self.pressed_key = key_index
                    self.update()
                    self.press_timer.start(KEY_PRESS_DURATION)

                    if habit:
                        scroll_info = f" (scroll: {self.scroll_offset}/{self.max_scroll_offset})" if self.scrolling_enabled else ""
                        print(f"DEBUG: Clicked habit: {habit.name} at visual index {key_index}{scroll_info}")
                        self.toggle_session(habit)
                    else:
                        scroll_info = f" (scroll: {self.scroll_offset}/{self.max_scroll_offset})" if self.scrolling_enabled else ""
                        print(f"DEBUG: Clicked placeholder key {key_index}{scroll_info}")

    def toggle_session(self, habit):
        """Start or stop a session for the given habit"""
        if habit.id in self.process_manager.processes:
            # End existing session
            self.play_end_sound()
            self.end_session(habit)
        else:
            # Start new session
            self.play_start_sound()
            self.start_session(habit)

    def start_session(self, habit):
        """Start a session in separate process"""
        try:
            self.process_manager.start_session(habit)
            print(f"Starting session process for {habit.name}")
        except Exception as e:
            print(f"Error starting session: {e}")

    def end_session(self, habit):
        """End a session"""
        try:
            self.process_manager.stop_session(habit.id)
            print(f"Stopping session for {habit.name}")

            # Clean up display immediately
            if habit.id in self.time_displays:
                del self.time_displays[habit.id]
            self.update()  # Trigger repaint

        except Exception as e:
            print(f"Error stopping session: {e}")

    def on_elapsed_updated(self, habit_id, elapsed_seconds):
        """Handle elapsed time updates from session process"""
        time_text = get_friendly_elapsed(elapsed_seconds)
        self.time_displays[habit_id] = time_text
        # Only update the time display area instead of the whole widget
        if self.time_display_area:
            self.update(self.time_display_area)
        else:
            self.update()  # Fallback if area not calculated yet

    def on_session_ended(self, habit_id):
        """Handle session ended signal from process"""
        if habit_id in self.time_displays:
            del self.time_displays[habit_id]
        # Only update the time display area
        if self.time_display_area:
            self.update(self.time_display_area)
        else:
            self.update()  # Fallback if area not calculated yet

    def on_session_error(self, error_message):
        """Handle session error from process"""
        print(f"Session error: {error_message}")

    def is_brass_section_click(self, click_pos):
        """Check if click is in the brass section (pedals area)"""
        pedal_x = self.width - 25
        brass_area = QRect(pedal_x - 20, self.height // 2 - 60, 40, 120)
        return brass_area.contains(click_pos)

    def open_management_window(self):
        """Open the management window"""
        if self.management_window is None:
            from gui.management_window import HabitManagementWindow
            self.management_window = HabitManagementWindow()
            # Connect signal to refresh piano window when habits are updated
            self.management_window.habit_updated.connect(self.refresh_habits)

        self.management_window.show()
        self.management_window.raise_()
        self.management_window.activateWindow()

    def is_piano_frame_click(self, pos):
        """Check if click is on the piano frame (but not on the keybed)"""
        keys_start_x = 95
        keys_end_x = self.width - 40

        # Check if NOT in key area (this means it's on the frame)
        if pos.x() < keys_start_x or pos.x() > keys_end_x:
            return True

        # Also check if in the brass section area (pedals), which is considered frame
        if self.is_brass_section_click(pos):
            return True

        return False

    def hide_window_for_seconds(self, seconds):
        """Hide the window for the specified number of seconds with fade animation"""
        self.is_fading_out = True
        self.fade_animation.setStartValue(self.windowOpacity())
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.start()
        self.hide_timer.start(seconds * 1000)  # Convert seconds to milliseconds

    def on_fade_finished(self):
        """Called when fade animation finishes"""
        if self.is_fading_out:
            # Hide the window after fade out completes
            self.hide()

    def show_window_after_hide(self):
        """Show the window again after the hide timer expires with fade animation"""
        self.show()
        #self.raise_()
        self.is_fading_out = False
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(0.97)  # Return to original opacity
        self.fade_animation.start()

    def refresh_habits(self):
        """Refresh habits list when management window updates them"""
        self.habits = list(Habit.select())
        self.update_keys_for_window_size()
        self.update()

    def closeEvent(self, event):
        """Clean up processes when window closes"""
        if hasattr(self, 'process_manager'):
            self.process_manager.cleanup()
            self.process_manager.wait(3000)  # Wait up to 3 seconds

        # Close management window if open
        if self.management_window is not None:
            self.management_window.close()

        event.accept()


def main():
    # Required for multiprocessing on some platforms
    multiprocessing.set_start_method('spawn', force=True)

    app = QApplication(sys.argv)

    # Set application properties
    app.setApplicationName("Piano Activity Tracker")

    # Create and show the window
    window = PianoFloatingWindow()
    window.show()

    # Set window opacity for floating effect
    window.setWindowOpacity(0.97)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()