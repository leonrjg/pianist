"""
Reminder service - core logic for firing reminders.

Shared between ReminderManager (automatic) and manual triggers.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .reminder import Reminder
from .reminder_log import ReminderLog
from .actions import ActionHandler
from ..schedule.sm2 import SM2Scheduler
from ..schedule.stochastic import StochasticScheduler
from ..notification.service import NotificationService


@dataclass
class FireResult:
    """Result of firing a reminder."""
    success: bool
    message: str
    error: Optional[str] = None


class ReminderService:
    """Service for reminder operations."""

    @classmethod
    def fire_reminder(
        cls,
        reminder: Reminder,
        context_modifier: float = 1.0,
        is_overdue: bool = False,
        skip_notification: bool = False,
        message_override: Optional[str] = None,
        record_fire: bool = True
    ) -> FireResult:
        """
        Fire a reminder: get message, notify, execute action, log, reschedule.

        Args:
            reminder: Reminder to fire
            context_modifier: Context modifier for logging
            is_overdue: Whether reminder is overdue
            skip_notification: Skip desktop notification

        Returns:
            FireResult with success status and message
        """
        now = datetime.now()

        # Get message for notification
        message = message_override if message_override is not None else ActionHandler.get_message(reminder)

        # Send notification first (before action potentially steals focus)
        if not skip_notification and reminder.notification_method == 'desktop':
            urgency = 'high' if is_overdue else 'normal'
            notification_service = NotificationService.get_instance()
            notification_service.show_reminder_notification(reminder.name, message, urgency)

        # Execute action
        error = None
        try:
            ActionHandler.execute(reminder)
        except Exception as e:
            error = str(e)
            message = f"Action failed: {error}"

        if record_fire:
            # Log firing
            ReminderLog.create(
                reminder=reminder,
                fired_at=now,
                action_executed=reminder.action_type,
                notification_sent=reminder.notification_method == 'desktop' and not skip_notification,
                context_modifier=context_modifier,
                was_overdue=is_overdue
            )

            # Update last_fired_at
            reminder.last_fired_at = now

            # Reschedule
            cls.reschedule(reminder, now)

            reminder.updated_at = now
            reminder.save()

        return FireResult(
            success=error is None,
            message=message,
            error=error
        )

    @classmethod
    def reschedule(cls, reminder: Reminder, base_time: datetime = None):
        """
        Calculate and set next fire time for reminder.
        
        Args:
            reminder: Reminder to reschedule
            base_time: Base time for calculation (defaults to last_fired_at or created_at)
        """
        now = datetime.now()
        last_fire = base_time or reminder.last_fired_at or reminder.created_at
        
        if reminder.reminder_type == 'sr':
            reminder.next_fire_at = SM2Scheduler.get_next_fire_time(last_fire, reminder.interval_days)
        elif reminder.reminder_type == 'stochastic':
            if reminder.target_rate_per_week:
                reminder.next_fire_at = StochasticScheduler.get_next_fire_time(last_fire, reminder.target_rate_per_week)
        
        reminder.updated_at = now
        reminder.save()
