"""
Habit Service - Application data service for the GUI.

Owns the authoritative in-memory habit list and schedule cache.
Initialized before any UI is created; the window receives it as a dependency.

The CLI does not use this service — it queries the ORM directly.
"""

import json
from typing import List, Optional, Callable, Dict
from datetime import datetime

from core.db import db
from core.habit.habit import Habit
from core.habit.manual_task import ManualTask
from core.habit.habit_tracker import HabitTracker
from core.habit.log import Log


class HabitService:
    """
    Application data service for the GUI.

    Owns the in-memory habit list and schedule result cache. Provides change
    notifications to subscribers via a simple observer list so the service
    does not depend on Qt.
    """

    def __init__(self):
        self._habits: List[Habit] = []
        self._schedule_cache: Dict[int, Dict] = {}  # habit_id -> {task_dt, is_completed}
        self._observers: List[Callable] = []

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load habits from DB and build the schedule cache. Call once at startup."""
        self._habits = [
            h for h in Habit.select().where(Habit.deleted_at.is_null()).order_by(Habit.display_order, Habit.id)
            if not h.archived
        ]
        self._rebuild_schedule_cache()

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_all_habits(self) -> List[Habit]:
        """All non-archived habits, ordered (includes non-visible)."""
        return list(self._habits)

    def get_visible_habits(self) -> List[Habit]:
        """Non-archived visible habits (shown as piano keys)."""
        return [h for h in self._habits if h.visible]

    def get_habit_by_id(self, habit_id: int) -> Optional[Habit]:
        for h in self._habits:
            if h.id == habit_id:
                return h
        return None

    def get_all_non_deleted(self) -> List[Habit]:
        """All non-deleted habits including archived, ordered by display_order."""
        return list(Habit.select().where(Habit.deleted_at.is_null()).order_by(Habit.display_order, Habit.name))

    def get_non_deleted_by_id(self, habit_id) -> Optional[Habit]:
        """Get a non-deleted habit by id, or None if not found."""
        try:
            return Habit.get(Habit.id == habit_id, Habit.deleted_at.is_null())
        except Habit.DoesNotExist:
            return None

    def get_next_task_info(self, habit_id: int) -> Dict:
        """Return cached {'task_dt': datetime|None, 'is_completed': bool} for a habit."""
        return self._schedule_cache.get(habit_id, {'task_dt': None, 'is_completed': False})

    # ------------------------------------------------------------------
    # Mutation API
    # ------------------------------------------------------------------

    def reorder_visible_habits(self, reordered_visible: List[Habit]) -> None:
        """
        Update display_order for visible habits, reload in-memory list, notify subscribers.

        All saves are wrapped in a single transaction so a partial reorder cannot occur.
        """
        with db.atomic():
            for i, habit in enumerate(reordered_visible):
                habit.display_order = i
                habit.save()
        self._habits = [
            h for h in Habit.select().where(Habit.deleted_at.is_null()).order_by(Habit.display_order, Habit.id)
            if not h.archived
        ]
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

        self._rebuild_schedule_cache_for_habit(habit)
        self._notify('task_toggled', habit_id=habit.id)

    def refresh(self) -> None:
        """Reload habits and rebuild schedule cache. Call after external mutations."""
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

    def _rebuild_schedule_cache(self) -> None:
        self._schedule_cache.clear()
        for habit in self._habits:
            self._rebuild_schedule_cache_for_habit(habit)

    def _rebuild_schedule_cache_for_habit(self, habit: Habit) -> None:
        try:
            schedule = habit.get_schedule()
            next_tasks = sorted(schedule.get_next_tasks(30 * 24 * 60 * 60))
            task_dt = next_tasks[0] if next_tasks else None
            is_completed = habit.is_task_completed(task_dt) if task_dt else False
            self._schedule_cache[habit.id] = {'task_dt': task_dt, 'is_completed': is_completed}
        except Exception:
            self._schedule_cache[habit.id] = {'task_dt': None, 'is_completed': False}
