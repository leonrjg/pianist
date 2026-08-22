"""
Reminder service - core logic for firing reminders.

Shared between ReminderManager (automatic) and manual triggers.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import random
from typing import Optional, List

from core.habit.manual_task import ManualTask
from .reminder import Reminder
from .reminder_log import ReminderLog
from .actions import ActionHandler
from ..schedule.stochastic import StochasticScheduler
from ..schedule.active_window import ActiveWindow
from ..settings.service import SettingsService

logger = logging.getLogger(__name__)


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
            # ActionHandler orchestrates the appropriate notification flow
            ActionHandler.show_notification_for_action(reminder, message, urgency)

        # Execute action
        error = None
        try:
            ActionHandler.execute(reminder)
        except Exception as e:
            logger.exception("Error executing reminder action for %s", reminder.id)
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

            # Update last_fired_at; a fire consumes any pending snooze
            reminder.last_fired_at = now
            reminder.snooze_until = None

            if reminder.reminder_type == 'fixed':
                cls.complete_fixed_fire(reminder)
            else:
                cls.reschedule(reminder, now)

            reminder.updated_at = now
            reminder.save()

        return FireResult(
            success=error is None,
            message=message,
            error=error
        )

    @classmethod
    def get_habit_message(cls, reminder: Reminder) -> str:
        """Return the standard message for habit-linked reminders."""
        habit = getattr(reminder, 'habit', None)
        habit_name = habit.name if habit is not None else "this habit"
        return f"It's time for {habit_name}"

    @classmethod
    def get_habit_task_datetime(cls, reminder: Reminder, fired_at: datetime = None) -> Optional[datetime]:
        """Return the scheduled habit task represented by a reminder firing."""
        habit = getattr(reminder, 'habit', None)
        if habit is None:
            return None

        reference = fired_at or reminder.next_fire_at or datetime.now()
        task_dt = reference.replace(
            hour=habit.started_at.hour,
            minute=habit.started_at.minute,
            second=habit.started_at.second,
            microsecond=0
        )
        return task_dt

    @classmethod
    def should_fire_habit_reminder(cls, reminder: Reminder) -> bool:
        """Return whether a habit-linked reminder should fire for its scheduled task."""
        habit = getattr(reminder, 'habit', None)
        if habit is None:
            return True

        task_dt = cls.get_habit_task_datetime(reminder)
        if task_dt is not None and habit.is_task_completed(task_dt):
            cls.reschedule(reminder, reminder.next_fire_at + timedelta(seconds=1))
            return False
        return True

    @classmethod
    def mark_habit_task_done(cls, reminder: Reminder, task_dt: datetime) -> None:
        """Mark a habit-linked reminder's task complete without toggling it off."""
        from core.habit.manual_task import ManualTask

        habit = getattr(reminder, 'habit', None)
        if habit is None or task_dt is None:
            return

        normalized_dt = task_dt.replace(microsecond=0)
        now = datetime.now()
        with ManualTask._meta.database.atomic():
            existing = ManualTask.select().where(
                (ManualTask.habit == habit) &
                (ManualTask.scheduled_at == normalized_dt) &
                ManualTask.deleted_at.is_null()
            ).first()

            if existing:
                existing.completed_at = existing.completed_at or now
                existing.updated_at = now
                existing.save()
            else:
                ManualTask.create(
                    habit=habit,
                    title=None,
                    scheduled_at=normalized_dt,
                    completed_at=now,
                )

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    @classmethod
    def get_all(cls) -> List[Reminder]:
        """All non-deleted reminders, newest first."""
        return list(Reminder.select().where(Reminder.deleted_at.is_null()).order_by(Reminder.created_at.desc()))

    @classmethod
    def get_for_reminders_page(
        cls,
        include_habit_linked: bool = False,
        include_one_off: bool = True,
    ) -> List[Reminder]:
        """Reminders shown on the standalone reminders page."""
        query = Reminder.select().where(Reminder.deleted_at.is_null())
        if not include_habit_linked:
            query = query.where(Reminder.habit.is_null())
        if not include_one_off:
            query = query.where(Reminder.manual_task.is_null())
        return list(query.order_by(Reminder.created_at.desc()))

    @classmethod
    def get_all_enabled(cls) -> List[Reminder]:
        """All enabled, non-deleted reminders."""
        return list(Reminder.select().where(
            (Reminder.is_enabled == True) & Reminder.deleted_at.is_null()
        ))

    @classmethod
    def get_by_id(cls, reminder_id) -> Reminder:
        """Get a non-deleted reminder by id, raising DoesNotExist if not found."""
        return Reminder.get(Reminder.id == reminder_id, Reminder.deleted_at.is_null())

    @classmethod
    def get_for_habit(cls, habit_id) -> List[Reminder]:
        """Get non-deleted reminders linked to a habit, newest first."""
        return list(Reminder.select().where(
            (Reminder.habit == habit_id) &
            Reminder.deleted_at.is_null()
        ).order_by(Reminder.created_at.desc()))

    @classmethod
    def get_overdue_stochastic(cls, now: datetime) -> List[Reminder]:
        """Enabled, un-snoozed stochastic reminders with next_fire_at in the past."""
        return list(Reminder.select().where(
            (Reminder.is_enabled == True) &
            (Reminder.reminder_type == 'stochastic') &
            (Reminder.next_fire_at.is_null(False)) &
            (Reminder.next_fire_at < now) &
            (Reminder.snooze_until.is_null() | (Reminder.snooze_until <= now)) &
            Reminder.deleted_at.is_null()
        ))

    @classmethod
    def get_overdue_fixed(cls, now: datetime) -> List[Reminder]:
        """Enabled, un-snoozed fixed reminders with next_fire_at in the past."""
        return list(Reminder.select().where(
            (Reminder.is_enabled == True) &
            (Reminder.reminder_type == 'fixed') &
            (Reminder.next_fire_at.is_null(False)) &
            (Reminder.next_fire_at < now) &
            (Reminder.snooze_until.is_null() | (Reminder.snooze_until <= now)) &
            Reminder.deleted_at.is_null()
        ))

    @classmethod
    def is_global_window_enabled(cls) -> bool:
        """Return whether reminders are constrained by the global window."""
        return bool(SettingsService.get('reminders.global_window_enabled', False))

    @classmethod
    def get_global_window(cls) -> ActiveWindow:
        """Return the configured global reminder window."""
        return ActiveWindow(
            SettingsService.get('reminders.global_window_start_minute', 0),
            SettingsService.get('reminders.global_window_end_minute', 1440)
        )

    @classmethod
    def get_configured_window(cls, reminder: Reminder) -> ActiveWindow:
        """Return the reminder-specific window."""
        return ActiveWindow(
            getattr(reminder, "active_start_minute", 0),
            getattr(reminder, "active_end_minute", 1440)
        )

    @classmethod
    def get_effective_window(cls, reminder: Reminder) -> ActiveWindow:
        """Return the window used for scheduling after global constraints."""
        reminder_window = cls.get_configured_window(reminder)
        if not cls.is_global_window_enabled():
            return reminder_window
        if cls.is_window_inside_global(reminder_window):
            return reminder_window
        return cls.get_global_window()

    @classmethod
    def is_reminder_outside_global_window(cls, reminder: Reminder) -> bool:
        """Return whether a reminder's time/window falls outside the global window."""
        if not cls.is_global_window_enabled():
            return False

        if reminder.reminder_type == 'fixed':
            fixed_minute = getattr(reminder, 'fixed_time_minute', None)
            if fixed_minute is None and reminder.next_fire_at is not None:
                fixed_minute = reminder.next_fire_at.hour * 60 + reminder.next_fire_at.minute
            if fixed_minute is None:
                return False
            return not cls._window_contains_minute(cls.get_global_window(), fixed_minute)

        return not cls.is_window_inside_global(cls.get_configured_window(reminder))

    @classmethod
    def is_window_inside_global(cls, window: ActiveWindow) -> bool:
        """Return whether all sample points of window fit inside the global window."""
        global_window = cls.get_global_window()
        for minute in cls._window_sample_minutes(window):
            if not cls._window_contains_minute(global_window, minute):
                return False
        return True

    @classmethod
    def defer_until_global_window(cls, reminder: Reminder, now: datetime) -> bool:
        """Move a due reminder to the next global window if it is currently blocked."""
        if not cls.is_global_window_enabled():
            return False
        global_window = cls.get_global_window()
        if global_window.is_within(now):
            return False
        reminder.next_fire_at = global_window.next_window_start(now)
        reminder.updated_at = datetime.now()
        reminder.save()
        return True

    # ------------------------------------------------------------------
    # Mutation API
    # ------------------------------------------------------------------

    @classmethod
    def save(cls, reminder: Reminder) -> None:
        """Persist changes to a reminder, updating updated_at."""
        reminder.updated_at = datetime.now()
        reminder.save()

    @classmethod
    def create(cls, **kwargs) -> Reminder:
        """Create and persist a new reminder."""
        return Reminder.create(**kwargs)

    @classmethod
    def create_fixed_for_manual_task(
        cls,
        manual_task: ManualTask,
        fire_at: datetime,
        notification_method: str = 'desktop'
    ) -> Reminder:
        """Create a one-off fixed reminder for a standalone manual task."""
        now = datetime.now()
        fire_at = fire_at.replace(microsecond=0)
        return cls.create(
            name=manual_task.title or "Task reminder",
            reminder_type='fixed',
            manual_task=manual_task,
            action_type='show_text',
            action_payload=manual_task.title or "Task reminder",
            notification_method=notification_method,
            fixed_time_minute=fire_at.hour * 60 + fire_at.minute,
            next_fire_at=fire_at,
            active_start_minute=0,
            active_end_minute=1440,
            created_at=now,
            updated_at=now
        )

    @classmethod
    def toggle_enabled(cls, reminder: Reminder) -> None:
        """Toggle is_enabled and save."""
        reminder.is_enabled = not reminder.is_enabled
        reminder.updated_at = datetime.now()
        reminder.save()

    @classmethod
    def delete(cls, reminder: Reminder) -> None:
        """Soft-delete a reminder."""
        reminder.deleted_at = datetime.now()
        reminder.updated_at = datetime.now()
        reminder.save()

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

        window = cls.get_effective_window(reminder)

        if reminder.reminder_type == 'stochastic':
            if cls.is_habit_stochastic(reminder):
                reminder.next_fire_at = cls.get_next_habit_stochastic_fire_time(reminder, last_fire)
            elif reminder.target_rate_per_week:
                reminder.next_fire_at = StochasticScheduler.get_next_fire_time(
                    last_fire,
                    reminder.target_rate_per_week,
                    window.start_minute,
                    window.end_minute
                )
        elif reminder.reminder_type == 'fixed':
            reminder.next_fire_at = cls.get_next_fixed_fire_time(reminder, last_fire)
            if reminder.next_fire_at is None and (
                getattr(reminder, 'manual_task', None) is not None or getattr(reminder, 'habit', None) is None
            ):
                reminder.is_enabled = False

        # Advancing the schedule retires any pending snooze for the old occurrence.
        reminder.snooze_until = None
        reminder.updated_at = now
        reminder.save()

    @classmethod
    def is_habit_stochastic(cls, reminder: Reminder) -> bool:
        """Return whether this is a guaranteed random-in-due-day habit reminder."""
        return reminder.reminder_type == 'stochastic' and getattr(reminder, 'habit', None) is not None

    @classmethod
    def get_next_habit_stochastic_fire_time(cls, reminder: Reminder, from_dt: datetime = None) -> Optional[datetime]:
        """Schedule a habit-linked stochastic reminder at a random time within the next due occurrence.

        For the current occurrence's task date, the candidate is drawn only from window
        minutes still in the future (after `from_dt`), guaranteeing a re-fire within the
        same occurrence as long as any window time remains.  Once the window for the
        current occurrence is exhausted, the search advances to the next task occurrence.
        """
        habit = getattr(reminder, 'habit', None)
        if habit is None:
            return None

        base = (from_dt or datetime.now()).replace(microsecond=0)
        window = cls.get_effective_window(reminder)
        schedule = habit.get_schedule()
        scale_seconds = max(1, schedule.get_scale())
        search_from = base - timedelta(seconds=scale_seconds)

        for _ in range(10000):
            task_dt = schedule.get_next_task(search_from)
            if task_dt is None:
                return None

            if task_dt.date() == base.date():
                candidate = cls._random_time_on_date_after(task_dt.date(), base, window)
            else:
                candidate = cls._random_time_on_date(task_dt.date(), window)

            if candidate is not None and candidate > base:
                return candidate

            search_from += timedelta(seconds=scale_seconds)

        logger.error("Could not find next habit stochastic fire time for reminder %s", reminder.id)
        return None

    @classmethod
    def should_fire_fixed(cls, reminder: Reminder) -> bool:
        """Return whether a fixed reminder should notify now."""
        if reminder.reminder_type != 'fixed':
            return True

        manual_task = getattr(reminder, 'manual_task', None)
        if manual_task is not None:
            if manual_task.completed_at is not None or manual_task.deleted_at is not None:
                cls._retire_one_off(reminder)
                return False

        if getattr(reminder, 'habit', None) is not None and not cls.should_fire_habit_reminder(reminder):
            return False

        return True

    @classmethod
    def get_next_fixed_fire_time(cls, reminder: Reminder, from_dt: datetime = None) -> Optional[datetime]:
        """Calculate the next fixed reminder occurrence."""
        base = (from_dt or datetime.now()).replace(microsecond=0)
        fixed_minute = getattr(reminder, 'fixed_time_minute', None)

        manual_task = getattr(reminder, 'manual_task', None)
        if manual_task is not None:
            if manual_task.completed_at is not None or manual_task.deleted_at is not None:
                return None
            if fixed_minute is None:
                fixed_minute = manual_task.scheduled_at.hour * 60 + manual_task.scheduled_at.minute
            candidate = cls._with_minute(manual_task.scheduled_at, fixed_minute)
            return candidate if candidate > base else None

        habit = getattr(reminder, 'habit', None)
        if habit is not None:
            if fixed_minute is None:
                fixed_minute = habit.started_at.hour * 60 + habit.started_at.minute

            schedule = habit.get_schedule()
            scale_seconds = max(1, schedule.get_scale())
            search_from = base - timedelta(seconds=scale_seconds)
            for _ in range(10000):
                task_dt = schedule.get_next_task(search_from)
                if task_dt is None:
                    return None
                candidate = cls._with_minute(task_dt, fixed_minute)
                if candidate > base:
                    return candidate
                search_from += timedelta(seconds=scale_seconds)
            logger.error("Could not find next fixed fire time for reminder %s", reminder.id)
            return None

        return reminder.next_fire_at if reminder.next_fire_at and reminder.next_fire_at > base else None

    @classmethod
    def complete_fixed_fire(cls, reminder: Reminder) -> None:
        """Advance or retire a fixed reminder after it fires."""
        if getattr(reminder, 'manual_task', None) is not None or getattr(reminder, 'habit', None) is None:
            cls._retire_one_off(reminder)
            return

        cls.reschedule(reminder, datetime.now())

    @classmethod
    def snooze(cls, reminder: Reminder, minutes: int) -> None:
        """Defer a reminder's firing by the given number of minutes.

        Sets the user-owned ``snooze_until`` floor without touching the
        schedule-owned ``next_fire_at``. The reminder will not fire until
        ``snooze_until`` has passed (see :meth:`is_snoozed`).
        """
        now = datetime.now()
        reminder.snooze_until = now + timedelta(minutes=minutes)
        reminder.updated_at = now
        reminder.save()

    @classmethod
    def is_snoozed(cls, reminder: Reminder, now: datetime = None) -> bool:
        """Return whether a user-initiated snooze is still suppressing this reminder."""
        snooze_until = getattr(reminder, 'snooze_until', None)
        if snooze_until is None:
            return False
        return snooze_until > (now or datetime.now())

    @classmethod
    def skip_occurrence(cls, reminder: Reminder) -> None:
        """Advance a habit stochastic reminder past the current occurrence to the next one."""
        habit = getattr(reminder, 'habit', None)
        if habit is None:
            logger.warning("skip_occurrence called on reminder %s with no habit — ignoring", reminder.id)
            return

        now = datetime.now()
        schedule = habit.get_schedule()
        scale_seconds = max(1, schedule.get_scale())
        current_task = schedule.get_next_task(now - timedelta(seconds=scale_seconds))
        if current_task is None:
            logger.warning("skip_occurrence: no current task found for reminder %s — habit may have ended", reminder.id)
            reminder.is_enabled = False
            reminder.next_fire_at = None
            reminder.snooze_until = None
            reminder.updated_at = now
            reminder.save()
            return

        past_current = current_task + timedelta(seconds=scale_seconds)
        reminder.next_fire_at = cls.get_next_habit_stochastic_fire_time(reminder, from_dt=past_current)
        reminder.snooze_until = None
        reminder.updated_at = now
        reminder.save()

    @classmethod
    def _retire_one_off(cls, reminder: Reminder) -> None:
        reminder.is_enabled = False
        reminder.next_fire_at = None
        reminder.updated_at = datetime.now()
        reminder.save()

    @staticmethod
    def _with_minute(dt: datetime, minute_of_day: int) -> datetime:
        minute_of_day = int(minute_of_day)
        return dt.replace(
            hour=minute_of_day // 60,
            minute=minute_of_day % 60,
            second=0,
            microsecond=0
        )

    @staticmethod
    def _random_time_on_date(day, window: ActiveWindow) -> datetime:
        minutes = [
            minute
            for minute in range(24 * 60)
            if ReminderService._window_contains_minute(window, minute)
        ]
        if not minutes:
            raise ValueError("Active window must contain at least one minute")

        minute = random.choice(minutes)
        return datetime(day.year, day.month, day.day, minute // 60, minute % 60)

    @staticmethod
    def _random_time_on_date_after(day, after_dt: datetime, window: ActiveWindow) -> Optional[datetime]:
        """Pick a random window minute on `day` strictly after `after_dt`.

        Returns None if no window time remains on that day.
        """
        minutes = [
            minute
            for minute in range(24 * 60)
            if ReminderService._window_contains_minute(window, minute)
            and datetime(day.year, day.month, day.day, minute // 60, minute % 60) > after_dt
        ]
        if not minutes:
            return None

        minute = random.choice(minutes)
        return datetime(day.year, day.month, day.day, minute // 60, minute % 60)

    @staticmethod
    def _window_contains_minute(window: ActiveWindow, minute: int) -> bool:
        minute = int(minute) % 1440
        dt = datetime(2000, 1, 1, minute // 60, minute % 60)
        return window.is_within(dt)

    @staticmethod
    def _window_sample_minutes(window: ActiveWindow) -> list[int]:
        if window.start_minute == window.end_minute:
            return [0, 360, 720, 1080]

        start = int(window.start_minute) % 1440
        end = int(window.end_minute) % 1440
        if start < end:
            minutes = [start]
            if end - start > 1:
                minutes.append(start + (end - start) // 2)
            minutes.append((end - 1) % 1440)
            return minutes

        length = (1440 - start) + end
        minutes = [start]
        if length > 1:
            minutes.append((start + length // 2) % 1440)
        minutes.append((end - 1) % 1440)
        return minutes
