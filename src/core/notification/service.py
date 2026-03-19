"""
Generic notification service for desktop notifications.

Uses a custom piano-themed toast widget.
"""

from gui.widgets.notification_toast import NotificationToast


class NotificationService:
    """
    Singleton notification service for displaying toast notifications.

    Provides consistent notification styling across the application.
    """

    _instance = None

    @classmethod
    def get_instance(cls) -> 'NotificationService':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._sound_manager = None
        self._active_toasts = []  # Keep references to prevent GC

    def set_parent(self, widget):
        """
        Set parent widget for notifications.

        Args:
            widget: Parent QWidget (unused, kept for API compatibility)
        """
        self._sound_manager = getattr(widget, "sound_manager", None)

    def show_toast(self, title: str, message: str, duration: int = 5000, urgency: str = 'normal', buttons: list = None, key_bindings: dict = None):
        """
        Show a generic toast notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
            urgency: Urgency level ('low', 'normal', 'high')
            buttons: Optional list of button configs (see NotificationToast.show_notification)

        Returns:
            NotificationToast instance (for chaining updates)
        """
        try:
            toast = NotificationToast()

            # Keep reference to prevent garbage collection
            self._active_toasts.append(toast)

            # Auto-cleanup when toast is destroyed
            toast.destroyed.connect(lambda: self._cleanup_toast(toast))

            toast.show_notification(title, message, duration, urgency, buttons, key_bindings)
            if self._sound_manager:
                self._sound_manager.play_sound("notification")
            return toast
        except Exception as e:
            print(f"Failed to show notification: {e}")
            return None

    def _cleanup_toast(self, toast):
        """Remove toast from active list when destroyed."""
        try:
            self._active_toasts.remove(toast)
        except (ValueError, AttributeError):
            pass  # Already removed or list doesn't exist

    def show_reminder_notification(self, reminder_name: str, message: str, urgency: str = 'normal'):
        """
        Show a reminder-specific notification.

        Args:
            reminder_name: Name of the reminder
            message: Message to display
            urgency: Urgency level ('low', 'normal', 'high')
        """
        if urgency == 'high':
            duration = 15000
        elif urgency == 'low':
            duration = 5000
        else:
            duration = 12000

        self.show_toast(reminder_name, message, duration, urgency)
