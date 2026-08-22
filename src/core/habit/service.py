"""
Habit Service - Application data service for the GUI.

Owns the authoritative in-memory habit list and schedule cache.
Initialized before any UI is created; the window receives it as a dependency.

The CLI does not use this service — it queries the ORM directly.
"""

import json
import logging
from typing import List, Optional, Callable, Dict, Tuple
from datetime import datetime, date

logger = logging.getLogger(__name__)

from core.db import db
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from core.habit.habit_tracker import HabitTracker
from core.habit.log import Log
from core.task import get_upcoming_tasks
from core.task.task import Task


class HabitService:
    """
    Application data service for the GUI.

    Owns the in-memory habit list. Provides change
    notifications to subscribers via a simple observer list so the service
    does not depend on Qt.
    """

    def __init__(self):
        self._habits: List[Habit] = []
        self._observers: List[Callable] = []

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load habits from DB. Call once at startup."""
        self._habits = list(Habit.select()
            .where(Habit.deleted_at.is_null() & (Habit.archived == False))
            .order_by(Habit.display_order, Habit.id))

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_all_habits(self) -> List[Habit]:
        """All non-archived habits, ordered (includes non-visible)."""
        return list(self._habits)

    def get_visible_habits(self) -> List[Habit]:
        """Non-archived visible habits (shown as piano keys)."""
        return [h for h in self._habits if h.visible]

    def get_today_task_rows(self, include_suppressed: bool = False) -> List[Task]:
        """Tasks (habit-scheduled or standalone) due on the current local date.

        Habits with suppress_piano_key=True are excluded unless include_suppressed=True.
        """
        today = date.today()
        tasks = get_upcoming_tasks(
            self._habits, timespan=24 * 60 * 60,
            include_manual=True, include_completed=True,
        )
        return [
            t for t in tasks
            if t.scheduled_at.date() == today
            and (include_suppressed or not (t.habit is not None and t.habit.suppress_piano_key))
        ]

    def get_staff_task_rows(self) -> List[Task]:
        """Today's task rows for the staff-strip completion summary.

        Excludes hourly habits: they recur many times per day, so each would add a
        note to the strip and drown out the once-a-day items the summary is meant to
        track. Standalone tasks (no habit) are always kept.
        """
        return [
            t for t in self.get_today_task_rows(include_suppressed=True)
            if t.habit is None or t.habit.schedule != 'hourly'
        ]

    def get_habit_by_id(self, habit_id: int) -> Optional[Habit]:
        for h in self._habits:
            if h.id == habit_id:
                return h
        return None

    def get_logged_seconds(self, habit_id) -> int:
        """Net tracked seconds already logged this period for a habit (0 if unknown).

        Used to seed a session's countdown so earlier sessions in the same period
        count toward the habit's allocated minimum time.
        """
        habit = self.get_habit_by_id(habit_id)
        return habit.get_logged_seconds() if habit else 0

    def get_all_non_deleted(self, archived: bool | None = None) -> List[Habit]:
        """All non-deleted habits, optionally filtered by archived state, ordered by display_order."""
        q = Habit.select().where(Habit.deleted_at.is_null()).order_by(Habit.display_order, Habit.name)
        if archived is not None:
            q = q.where(Habit.archived == archived)
        return list(q)

    def get_non_deleted_by_id(self, habit_id) -> Optional[Habit]:
        """Get a non-deleted habit by id, or None if not found."""
        try:
            return Habit.get(Habit.id == habit_id, Habit.deleted_at.is_null())
        except Habit.DoesNotExist:
            return None

    def get_next_task_info(self, habit_id: int) -> Dict:
        """Return {'task_dt': datetime|None, 'is_completed': bool} for the next upcoming task."""
        habit = self.get_habit_by_id(habit_id)
        if not habit:
            return {'task_dt': None, 'is_completed': False}
        try:
            schedule = habit.get_schedule()
            next_tasks = sorted(schedule.get_next_tasks(30 * 24 * 60 * 60))
            task_dt = next_tasks[0] if next_tasks else None
            is_completed = habit.is_task_completed(task_dt) if task_dt else False
            return {'task_dt': task_dt, 'is_completed': is_completed}
        except Exception:
            return {'task_dt': None, 'is_completed': False}

    # ------------------------------------------------------------------
    # Mutation API
    # ------------------------------------------------------------------

    def reorder_piano_keys(self, ordered_backers: List[Tuple[str, object]]) -> None:
        """
        Assign a single, unified display_order across every piano-key backer.

        A piano key is backed by either a Habit (habit-scheduled occurrence or a
        plain visible habit) or a standalone ManualTask. Both carry their own
        ``display_order`` column; assigning positions from one global counter makes
        the two columns comparable so that any key can sort above or below any other,
        regardless of type. This is the single ordering authority — there is no
        pinned today-block.

        Args:
            ordered_backers: Backers in their new visual order. Each item is a
                ``(kind, id)`` tuple where kind is ``'habit'`` or ``'manual'``.
                Duplicates (e.g. an hourly habit due several times today) are
                collapsed to their first occurrence.

        All saves are wrapped in a single transaction so a partial reorder cannot occur.
        """
        seen: set = set()
        with db.atomic():
            position = 0
            for kind, backer_id in ordered_backers:
                if (kind, backer_id) in seen:
                    continue
                seen.add((kind, backer_id))

                if kind == 'habit':
                    habit = self.get_habit_by_id(backer_id)
                    if habit is None:
                        logger.warning("reorder_piano_keys: unknown habit id %r, skipping", backer_id)
                        continue
                    habit.display_order = position
                    habit.save()
                elif kind == 'manual':
                    manual_task = ManualTask.get_or_none(ManualTask.id == backer_id)
                    if manual_task is None:
                        logger.warning("reorder_piano_keys: unknown manual task id %r, skipping", backer_id)
                        continue
                    manual_task.display_order = position
                    manual_task.save()
                else:
                    logger.warning("reorder_piano_keys: unknown backer kind %r, skipping", kind)
                    continue

                position += 1

        self._habits = list(Habit.select()
            .where(Habit.deleted_at.is_null() & (Habit.archived == False))
            .order_by(Habit.display_order, Habit.id))
        self._notify('reordered')

    def toggle_task_completion(self, habit: Habit, task_datetime: datetime) -> None:
        """
        Create or delete a ManualTask, rebuild cache for the affected habit, notify subscribers.
        """
        normalized_dt = task_datetime.replace(microsecond=0)
        with db.atomic():
            existing = ManualTask.select().where(
                (ManualTask.habit == habit) &
                (ManualTask.scheduled_at == normalized_dt) &
                ManualTask.deleted_at.is_null()
            ).first()

            if existing:
                existing.deleted_at = datetime.now()
                existing.updated_at = datetime.now()
                existing.save()
            else:
                ManualTask.create(
                    habit=habit,
                    title=None,
                    scheduled_at=normalized_dt,
                    completed_at=normalized_dt,
                )

        self._notify('task_toggled', habit_id=habit.id)

    def refresh(self) -> None:
        """Reload habits. Call after external mutations."""
        self.load()
        self._notify('refreshed')

    # ------------------------------------------------------------------
    # Tracker API
    # ------------------------------------------------------------------

    def get_enabled_trackers(self, habit: Habit) -> List[HabitTracker]:
        """Get all enabled (non-deleted) trackers for a habit."""
        return list(HabitTracker.select().where(
            (HabitTracker.habit == habit) &
            (HabitTracker.is_enabled == True) &
            HabitTracker.deleted_at.is_null()
        ))

    def get_window_trackers(self, habit: Habit) -> List[HabitTracker]:
        """Get enabled WindowTracker records for a habit."""
        return list(HabitTracker.select().where(
            (HabitTracker.habit == habit) &
            (HabitTracker.tracker == 'WindowTracker') &
            (HabitTracker.is_enabled == True) &
            HabitTracker.deleted_at.is_null()
        ))

    def save_trackers(self, habit: Habit, tracker_configs: List[dict]) -> None:
        """
        Replace all trackers for a habit with the given configs.

        tracker_configs: [{'tracker': str, 'config_json': str}, ...]
        """
        with db.atomic():
            HabitTracker.update(
                deleted_at=datetime.now(),
                updated_at=datetime.now()
            ).where(HabitTracker.habit == habit).execute()

            for entry in tracker_configs:
                HabitTracker.insert(
                    habit=habit,
                    tracker=entry['tracker'],
                    config=entry['config_json'],
                    is_enabled=True
                ).on_conflict_replace().execute()

    # ------------------------------------------------------------------
    # Log API
    # ------------------------------------------------------------------

    def get_logs_for_bucket(self, habit: Habit, bucket) -> List[Log]:
        """Get logs for a habit within a bucket's time range, ordered by start."""
        return list(Log.select().where(
            (Log.habit == habit) &
            (Log.start >= bucket.start) &
            (Log.start < bucket.end) &
            Log.deleted_at.is_null()
        ).order_by(Log.start))

    def delete_log(self, log: Log) -> None:
        """Soft-delete a log entry."""
        log.deleted_at = datetime.now()
        log.updated_at = datetime.now()
        log.save()

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable) -> None:
        """Register a callback(change_type: str, **kwargs) for change notifications."""
        self._observers.append(callback)

    def unsubscribe(self, callback: Callable) -> None:
        self._observers = [cb for cb in self._observers if cb != callback]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify(self, change_type: str, **kwargs) -> None:
        for callback in list(self._observers):
            try:
                callback(change_type, **kwargs)
            except Exception:
                pass

