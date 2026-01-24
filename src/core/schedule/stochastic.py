"""
Stochastic scheduling using Poisson process.

Generates random fire times with target rate per week.
"""

import random
from datetime import datetime, timedelta

from .active_window import ActiveWindow


class StochasticScheduler:
    """
    Stochastic scheduler using exponential distribution.

    Generates random wait times following Poisson process with given rate.
    Enforces minimum gap between firings.
    """

    WEEK_SECONDS = 7 * 24 * 60 * 60
    MIN_GAP_MINUTES = 15  # Minimum 15 minutes between stochastic reminders

    @staticmethod
    def get_next_fire_time(
        last_fired_at: datetime,
        target_rate_per_week: float,
        active_start_minute: int = 0,
        active_end_minute: int = 1440
    ) -> datetime:
        """
        Calculate next fire time using exponential distribution.

        Args:
            last_fired_at: Last time reminder fired (or created_at if never fired)
            target_rate_per_week: Target number of firings per week

        Returns:
            Next scheduled fire time
        """
        if target_rate_per_week <= 0:
            raise ValueError("Target rate must be positive")

        window = ActiveWindow(active_start_minute, active_end_minute)
        active_minutes = window.length_minutes()
        active_seconds_per_week = active_minutes * 60 * 7

        if active_seconds_per_week <= 0:
            raise ValueError("Active window must have positive duration")

        # Convert rate to lambda (events per active second)
        lambda_rate = target_rate_per_week / active_seconds_per_week

        # Sample from exponential distribution (active seconds)
        wait_active_seconds = random.expovariate(lambda_rate)

        # Compute next time within the active window
        base_time = window.clamp(last_fired_at)
        next_time = window.advance_by_active_seconds(base_time, wait_active_seconds)

        # Enforce minimum gap in wall-clock time
        min_gap_seconds = StochasticScheduler.MIN_GAP_MINUTES * 60
        min_time = last_fired_at + timedelta(seconds=min_gap_seconds)
        if next_time < min_time:
            next_time = window.clamp(min_time)

        return next_time

    @staticmethod
    def should_fire(reminders: list, now: datetime = None) -> tuple:
        """
        Select one stochastic reminder to fire using weight-based competition.

        Args:
            reminders: List of due stochastic reminders with weights
            now: Current time (defaults to datetime.now())

        Returns:
            Tuple of (selected_reminder, None) or (None, None) if no valid reminder
        """
        if not reminders:
            return None, None

        if now is None:
            now = datetime.now()

        # Filter to only due reminders
        due_reminders = [r for r in reminders if r.next_fire_at and r.next_fire_at <= now]

        if not due_reminders:
            return None, None

        # Weight-based selection
        total_weight = sum(r.weight for r in due_reminders)
        if total_weight <= 0:
            return None, None

        rand_val = random.uniform(0, total_weight)
        cumulative = 0

        for reminder in due_reminders:
            cumulative += reminder.weight
            if rand_val <= cumulative:
                return reminder, None

        # Fallback to last reminder
        return due_reminders[-1], None
