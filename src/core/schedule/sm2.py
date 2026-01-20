"""
SM-2 (SuperMemo 2) spaced repetition algorithm.

Calculates intervals based on ease factor and previous interval.
"""

from datetime import datetime, timedelta


class SM2Scheduler:
    """
    SM-2 spaced repetition scheduler for reminders.

    Intervals grow exponentially: interval = previous_interval × ease_factor
    Minimum interval is 1 day.
    """

    @staticmethod
    def calculate_next_interval(ease_factor: float, current_interval_days: int, quality: int = 3) -> tuple[float, int]:
        """
        Calculate next interval based on SM-2 algorithm.

        Args:
            ease_factor: Current ease factor (default 2.5)
            current_interval_days: Current interval in days
            quality: Quality rating 0-3 (0=again, 1=hard, 2=good, 3=easy)

        Returns:
            Tuple of (new_ease_factor, new_interval_days)
        """
        # Adjust ease factor based on quality
        # Map quality (0-3) to traditional SM-2 quality (0-5)
        sm2_quality = quality * 1.5 + 1  # Maps 0->1, 1->2.5, 2->4, 3->5.5 (capped at 5)
        sm2_quality = min(5, sm2_quality)

        new_ease = ease_factor + (0.1 - (5 - sm2_quality) * (0.08 + (5 - sm2_quality) * 0.02))
        new_ease = max(1.3, new_ease)  # Minimum ease factor

        # Calculate new interval
        if quality < 2:  # Again or Hard
            new_interval = max(1, current_interval_days * 0.5)  # Reset to half
        else:
            if current_interval_days == 0:
                new_interval = 1
            elif current_interval_days == 1:
                new_interval = 6
            else:
                new_interval = current_interval_days * new_ease

        return new_ease, int(new_interval)

    @staticmethod
    def get_next_fire_time(last_fired_at: datetime, interval_days: int) -> datetime:
        """
        Calculate next fire time based on last fire time and interval.

        Args:
            last_fired_at: Last time reminder fired
            interval_days: Interval in days

        Returns:
            Next scheduled fire time
        """
        return last_fired_at + timedelta(days=interval_days)

    @staticmethod
    def is_due(next_fire_at: datetime, now: datetime = None) -> bool:
        """
        Check if reminder is due.

        Args:
            next_fire_at: Scheduled fire time
            now: Current time (defaults to datetime.now())

        Returns:
            True if reminder is due
        """
        if now is None:
            now = datetime.now()
        return next_fire_at <= now
