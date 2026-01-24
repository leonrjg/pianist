"""
Background thread manager for reminder system.

Checks for due reminders every 30 seconds and fires them with context awareness.
"""

import logging
from datetime import datetime

from PyQt6.QtCore import QThread, pyqtSignal

from core.reminder.reminder import Reminder
from core.reminder.context import ContextEvaluator
from core.reminder.actions import ActionHandler
from core.reminder.service import ReminderService
from core.schedule.stochastic import StochasticScheduler

logger = logging.getLogger(__name__)


class ReminderManager(QThread):
    """
    Background thread for reminder scheduling and firing.

    Checks reminders every 30 seconds, applies context modifiers,
    and fires appropriate reminders based on type.
    """

    reminder_fired = pyqtSignal(int, str)  # reminder_id, message
    notification_requested = pyqtSignal(str, str, str)  # title, message, urgency

    CHECK_INTERVAL_MS = 30_000  # 30 seconds
    ANTI_SPAM_GAP_MINUTES = 15  # Minimum gap between any notifications

    def __init__(self, context_evaluator: ContextEvaluator):
        """
        Initialize reminder manager.

        Args:
            context_evaluator: Context evaluator for adaptive scheduling
        """
        super().__init__()
        self.context_evaluator = context_evaluator
        self.running = False
        self.last_notification_time = None

    def run(self):
        """Main thread loop."""
        self.running = True
        logger.info("ReminderManager started")

        # Check for overdue reminders on startup
        self._check_overdue_on_startup()

        # Main loop
        while self.running:
            try:
                self._check_and_fire_reminders()
            except Exception as e:
                logger.error(f"Error checking reminders: {e}", exc_info=True)

            # Sleep in small chunks so we can exit quickly
            sleep_chunks = self.CHECK_INTERVAL_MS // 1000  # Number of 1-second chunks
            for _ in range(sleep_chunks):
                if not self.running:
                    break
                self.msleep(1000)

        logger.info("ReminderManager stopped")

    def stop(self):
        """Stop the manager thread."""
        self.running = False

    def _check_overdue_on_startup(self):
        """Check for overdue reminders when app starts."""
        now = datetime.now()

        # SR reminders: Fire with urgency
        sr_reminders = Reminder.select().where(
            (Reminder.is_enabled == True) &
            (Reminder.reminder_type == 'sr') &
            (Reminder.next_fire_at.is_null(False)) &
            (Reminder.next_fire_at < now)
        )

        for reminder in sr_reminders:
            logger.info(f"Overdue SR reminder on startup: {reminder.name}")
            self._fire_reminder(reminder, is_overdue=True)

        # Stochastic reminders: Just reschedule, don't fire
        stochastic_reminders = Reminder.select().where(
            (Reminder.is_enabled == True) &
            (Reminder.reminder_type == 'stochastic') &
            (Reminder.next_fire_at.is_null(False)) &
            (Reminder.next_fire_at < now)
        )

        for reminder in stochastic_reminders:
            logger.info(f"Rescheduling overdue stochastic reminder: {reminder.name}")
            ReminderService.reschedule(reminder)

    def _check_and_fire_reminders(self):
        """Check all enabled reminders and fire if due."""
        now = datetime.now()

        # Update context evaluator idle status
        self.context_evaluator.update_idle_status()

        # Get all enabled reminders
        reminders = Reminder.select().where(Reminder.is_enabled == True)

        sr_due = []
        stochastic_due = []

        for reminder in reminders:
            if not reminder.next_fire_at:
                # Initialize next_fire_at if missing
                ReminderService.reschedule(reminder)
                continue

            if reminder.next_fire_at <= now:
                if reminder.reminder_type == 'sr':
                    sr_due.append(reminder)
                elif reminder.reminder_type == 'stochastic':
                    stochastic_due.append(reminder)

        # Fire all due SR reminders (guaranteed)
        for reminder in sr_due:
            self._fire_reminder(reminder)

        # Fire one stochastic reminder (weight-based competition)
        if stochastic_due:
            selected, _ = StochasticScheduler.should_fire(stochastic_due, now)
            if selected:
                self._fire_reminder(selected)

    def _fire_reminder(self, reminder, is_overdue: bool = False):
        """
        Fire a reminder with anti-spam protection.

        Args:
            reminder: Reminder to fire
            is_overdue: Whether reminder is overdue
        """
        now = datetime.now()

        # Check anti-spam gap
        if self.last_notification_time:
            time_since_last = (now - self.last_notification_time).total_seconds()
            if time_since_last < self.ANTI_SPAM_GAP_MINUTES * 60:
                logger.info(f"{datetime.now()} - Anti-spam: Skipping {reminder.name} (too soon)")
                return

        # Get context modifier
        context_modifier = self.context_evaluator.get_modifier(reminder)

        # Prepare notification on main thread before action steals focus
        message = ActionHandler.get_message(reminder)
        if reminder.notification_method == 'desktop':
            urgency = 'high' if is_overdue else 'normal'
            self.notification_requested.emit(reminder.name, message, urgency)
            self.last_notification_time = now

        # Small delay to let notification appear before action
        self.msleep(300)

        # Fire using service without background-thread notifications
        result = ReminderService.fire_reminder(
            reminder,
            context_modifier=context_modifier,
            is_overdue=is_overdue,
            skip_notification=True,
            message_override=message
        )

        # Emit signal
        self.reminder_fired.emit(reminder.id, result.message)

        logger.info(f"{datetime.now()} - Fired reminder: {reminder.name} (context: {context_modifier:.2f})")
