import logging
import time

from .tracker import Tracker
from pynput import mouse, keyboard

logger = logging.getLogger(__name__)

EPSILON = 5

class IOTracker(Tracker):
    def __init__(self):
        super().__init__()

        def pulse(*args):
            self.last_active = time.time()

        # Set up listeners
        self._mouse_listener = mouse.Listener(on_move=pulse)
        self._keyboard_listener = keyboard.Listener(on_press=pulse)

        # Start listening
        self._mouse_listener.start()
        self._keyboard_listener.start()

    def is_active(self) -> bool:
        return self.last_active and (time.time() - self.last_active) < EPSILON

