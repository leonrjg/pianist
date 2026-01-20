"""
Context evaluator for adaptive reminder scheduling.

Applies probability modifiers based on user activity patterns.
"""

from datetime import datetime, timedelta
import json


class ContextEvaluator:
    """
    Evaluates context modifiers for reminder firing probability.

    Tracks user activity and applies modifiers:
    - idle_boost: ×1.5 after returning from idle (>5 min)
    - sustained_boost: ×1.3 after sustained activity (>30 min)
    - startup_reduce: ×0.3 during first 2 minutes after app start
    - overdue_urgency: +20% per overdue day for SR reminders, max ×2
    """

    IDLE_THRESHOLD_SECONDS = 5 * 60  # 5 minutes
    SUSTAINED_THRESHOLD_SECONDS = 30 * 60  # 30 minutes
    STARTUP_WINDOW_SECONDS = 2 * 60  # 2 minutes

    def __init__(self):
        self.app_start_time = datetime.now()
        self.last_activity_time = datetime.now()
        self.activity_start_time = datetime.now()
        self.was_idle = False

    def record_activity(self):
        """Record user activity (called by main window on user interaction)."""
        now = datetime.now()

        # Check if returning from idle
        if self.was_idle:
            self.was_idle = False
            self.activity_start_time = now

        self.last_activity_time = now

    def update_idle_status(self):
        """Update idle status based on time since last activity."""
        now = datetime.now()
        time_since_activity = (now - self.last_activity_time).total_seconds()

        if time_since_activity > self.IDLE_THRESHOLD_SECONDS:
            self.was_idle = True

    def get_modifier(self, reminder) -> float:
        """
        Calculate context modifier for reminder firing.

        Args:
            reminder: Reminder object with scheduling info

        Returns:
            Probability modifier between 0.0 and 2.0
        """
        now = datetime.now()
        modifier = 1.0

        # Parse context config
        context_config = {}
        try:
            if reminder.context_config:
                context_config = json.loads(reminder.context_config)
        except:
            pass

        # Startup reduction (first 2 minutes)
        time_since_startup = (now - self.app_start_time).total_seconds()
        if time_since_startup < self.STARTUP_WINDOW_SECONDS:
            if context_config.get('startup_reduce', True):
                modifier *= 0.3

        # Idle boost (returning from idle)
        time_since_activity = (now - self.last_activity_time).total_seconds()
        if time_since_activity < 60 and self.was_idle:  # Just returned from idle
            if context_config.get('idle_boost', True):
                modifier *= 1.5

        # Sustained activity boost (active for >30 min)
        time_in_session = (now - self.activity_start_time).total_seconds()
        if time_in_session > self.SUSTAINED_THRESHOLD_SECONDS:
            if context_config.get('sustained_boost', True):
                modifier *= 1.3

        # Overdue urgency (SR only)
        if reminder.reminder_type == 'sr' and reminder.next_fire_at:
            if now > reminder.next_fire_at:
                days_overdue = (now - reminder.next_fire_at).days
                if context_config.get('overdue_urgency', True):
                    urgency_boost = min(1.0, days_overdue * 0.2)  # +20% per day, max +100%
                    modifier *= (1.0 + urgency_boost)

        # Cap modifier at 2.0
        return min(2.0, max(0.0, modifier))

    def reset_session(self):
        """Reset session tracking (called on app startup)."""
        self.app_start_time = datetime.now()
        self.last_activity_time = datetime.now()
        self.activity_start_time = datetime.now()
        self.was_idle = False
