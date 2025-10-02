import logging
import time

from .tracker import Tracker
from pynput import mouse, keyboard

logger = logging.getLogger(__name__)

EPSILON = 2

class IOTracker(Tracker):
    def __init__(self):
        """Initialize IO tracker with mouse and keyboard listeners."""
        super().__init__()

        def pulse(*args):
            self.last_active = int(time.time())

        # Set up listeners
        self._mouse_listener = mouse.Listener(on_move=pulse)
        self._keyboard_listener = keyboard.Listener(on_press=pulse)

        # Start listening
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def is_active(self) -> bool:
        """Check if recent input activity was detected."""
        return self.last_active and (time.time() - self.last_active) < EPSILON

