"""
Stochastic scheduling using Poisson process.

Generates random fire times with target rate per week.
"""

import random
from datetime import datetime, timedelta


class StochasticScheduler:
    """
    Stochastic scheduler using exponential distribution.

    Generates random wait times following Poisson process with given rate.
    Enforces minimum gap between firings.
    """

    WEEK_SECONDS = 7 * 24 * 60 * 60
    MIN_GAP_MINUTES = 15  # Minimum 15 minutes between stochastic reminders

    @staticmethod
    def get_next_fire_time(last_fired_at: datetime, target_rate_per_week: float) -> datetime:
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

        # Convert rate to lambda (events per second)
        lambda_rate = target_rate_per_week / StochasticScheduler.WEEK_SECONDS

        # Sample from exponential distribution
        wait_seconds = random.expovariate(lambda_rate)

        # Enforce minimum gap
        min_gap_seconds = StochasticScheduler.MIN_GAP_MINUTES * 60
        wait_seconds = max(wait_seconds, min_gap_seconds)

        return last_fired_at + timedelta(seconds=wait_seconds)

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
