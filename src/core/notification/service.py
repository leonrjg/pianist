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

    def set_parent(self, widget):
        """
        Set parent widget for notifications.

        Args:
            widget: Parent QWidget (unused, kept for API compatibility)
        """
        self._sound_manager = getattr(widget, "sound_manager", None)

    def show_toast(self, title: str, message: str, duration: int = 5000, urgency: str = 'normal'):
        """
        Show a generic toast notification.

        Args:
            title: Notification title
            message: Notification message
            duration: Display duration in milliseconds
            urgency: Urgency level ('low', 'normal', 'high')
        """
        try:
            toast = NotificationToast()
            toast.show_notification(title, message, duration, urgency)
            if self._sound_manager:
                self._sound_manager.play_sound("notification")
        except Exception as e:
            print(f"Failed to show notification: {e}")

    def show_reminder_notification(self, reminder_name: str, message: str, urgency: str = 'normal'):
        """
        Show a reminder-specific notification.

        Args:
            reminder_name: Name of the reminder
            message: Message to display
            urgency: Urgency level ('low', 'normal', 'high')
        """
        if urgency == 'high':
            duration = 8000
        elif urgency == 'low':
            duration = 4000
        else:
            duration = 5000

        self.show_toast(reminder_name, message, duration, urgency)
