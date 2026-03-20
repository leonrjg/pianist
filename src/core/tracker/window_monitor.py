import logging
import threading
import time
import pywinctl

logger = logging.getLogger(__name__)


class WindowMonitor:
    """Simple singleton that caches focused window title and notifies on changes."""

    _instance = None
    _lock = threading.Lock()

    # Simple cache
    _cached_title = ""
    _last_update = 0
    _poll_interval = 3

    # Callbacks for window changes
    _callbacks = []
    _callbacks_lock = threading.Lock()

    # Background thread
    _thread = None
    _stop_event = threading.Event()

    @classmethod
    def get_instance(cls):
        """Get or create singleton (double-checked locking)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._start_monitoring()
        return cls._instance

    @classmethod
    def register_callback(cls, callback):
        """Register a callback to be called when window title changes."""
        with cls._callbacks_lock:
            cls._callbacks.append(callback)

    @classmethod
    def unregister_callback(cls, callback):
        """Remove a previously registered callback."""
        with cls._callbacks_lock:
            cls._callbacks = [cb for cb in cls._callbacks if cb != callback]

    @classmethod
    def _start_monitoring(cls):
        """Start background polling thread."""
        cls._thread = threading.Thread(target=cls._poll_loop, daemon=True)
        cls._thread.start()
        logger.info("WindowMonitor background thread started")

    @classmethod
    def _poll_loop(cls):
        """Background thread that updates cache and notifies on changes."""
        while not cls._stop_event.is_set():
            try:
                new_title = pywinctl.getActiveWindowTitle() or ""

                # Only notify if title actually changed
                if new_title != cls._cached_title:
                    cls._cached_title = new_title
                    cls._last_update = time.time()

                    # Snapshot callbacks under lock, then iterate without holding it
                    with cls._callbacks_lock:
                        callbacks = list(cls._callbacks)
                    for callback in callbacks:
                        try:
                            callback(new_title)
                        except Exception as e:
                            logger.error(f"Callback error: {e}")
            except Exception as e:
                logger.error(f"WindowMonitor polling error: {e}")

            time.sleep(cls._poll_interval)

    @classmethod
    def get_current_title(cls) -> str:
        """Get cached window title."""
        return cls._cached_title
