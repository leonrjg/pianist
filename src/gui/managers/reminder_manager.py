"""
Background thread manager for reminder system.

Checks for due reminders every 30 seconds and fires them with context awareness.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

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

    reminder_fired = pyqtSignal(object, str)  # reminder_id, message
    notification_requested = pyqtSignal(object, str, str)  # reminder_id, message, urgency

    CHECK_INTERVAL_MS = 30_000  # 30 seconds
    ANTI_SPAM_GAP_MINUTES = 9  # Minimum gap between any notifications

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
        self._mute_until: Optional[datetime] = None  # None = not muted; datetime.max = indefinite

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

    def mute(self, hours: Optional[float]):
        """Mute all reminders. Pass None for indefinite mute."""
        if hours is None:
            self._mute_until = datetime.max
        else:
            self._mute_until = datetime.now() + timedelta(hours=hours)
        logger.info(f"Reminders muted until {self._mute_until}")

    def unmute(self):
        """Re-enable reminders."""
        self._mute_until = None
        logger.info("Reminders unmuted")

    @property
    def is_muted(self) -> bool:
        if self._mute_until is None:
            return False
        if self._mute_until == datetime.max:
            return True
        return datetime.now() < self._mute_until

    def _check_overdue_on_startup(self):
        """Check for overdue reminders when app starts."""
        now = datetime.now()

        for reminder in ReminderService.get_overdue_stochastic(now):
            if ReminderService.is_habit_stochastic(reminder):
                if ReminderService.defer_until_global_window(reminder, now):
                    logger.info(f"Deferring overdue habit stochastic reminder outside global window: {reminder.name}")
                    continue
                logger.info(f"Overdue habit stochastic reminder on startup: {reminder.name}")
                self._fire_reminder(reminder, is_overdue=True)
                continue
            logger.info(f"Rescheduling overdue stochastic reminder: {reminder.name}")
            ReminderService.reschedule(reminder)

        for reminder in ReminderService.get_overdue_fixed(now):
            if ReminderService.defer_until_global_window(reminder, now):
                logger.info(f"Deferring overdue fixed reminder outside global window: {reminder.name}")
                continue
            if ReminderService.should_fire_fixed(reminder):
                logger.info(f"Overdue fixed reminder on startup: {reminder.name}")
                self._fire_reminder(reminder, is_overdue=True)

    def _check_and_fire_reminders(self):
        """Check all enabled reminders and fire if due."""
        now = datetime.now()

        # Update context evaluator idle status
        self.context_evaluator.update_idle_status()

        reminders = ReminderService.get_all_enabled()

        stochastic_due = []
        habit_stochastic_due = []
        fixed_due = []

        for reminder in reminders:
            if not reminder.next_fire_at:
                # Initialize next_fire_at if missing
                ReminderService.reschedule(reminder)
                continue

            if reminder.next_fire_at <= now:
                if ReminderService.defer_until_global_window(reminder, now):
                    logger.info(f"Deferring reminder outside global window: {reminder.name}")
                    continue
                if reminder.reminder_type == 'stochastic':
                    if ReminderService.is_habit_stochastic(reminder):
                        habit_stochastic_due.append(reminder)
                    else:
                        stochastic_due.append(reminder)
                elif reminder.reminder_type == 'fixed':
                    fixed_due.append(reminder)

        for reminder in fixed_due:
            if ReminderService.should_fire_fixed(reminder):
                self._fire_reminder(reminder)

        for reminder in habit_stochastic_due:
            if ReminderService.should_fire_habit_reminder(reminder):
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

        # Check mute
        if self.is_muted:
            logger.info(f"Reminders muted — skipping {reminder.name}")
            return

        # Check anti-spam gap — fixed reminders and reminders with bypass_anti_spam are always exempt
        anti_spam_exempt = (
            reminder.reminder_type == 'fixed'
            or getattr(reminder, 'bypass_anti_spam', False)
        )
        if not anti_spam_exempt and self.last_notification_time:
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

            # Main thread will use ActionHandler.show_notification_for_action
            self.notification_requested.emit(reminder.id, message, urgency)

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
