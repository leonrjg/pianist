"""
Active time window helpers for scheduling reminders.
"""

from datetime import datetime, timedelta


class ActiveWindow:
    """Daily active window defined by start and end minutes."""

    def __init__(self, start_minute: int, end_minute: int):
        self.start_minute = int(start_minute)
        self.end_minute = int(end_minute)

    def length_minutes(self) -> int:
        if self.start_minute == self.end_minute:
            return 24 * 60
        # Normalize end_minute if >= 1440
        normalized_end = self.end_minute % 1440 if self.end_minute >= 1440 else self.end_minute
        if self.start_minute < normalized_end:
            return normalized_end - self.start_minute
        return (24 * 60 - self.start_minute) + normalized_end

    def is_within(self, dt: datetime) -> bool:
        minute = dt.hour * 60 + dt.minute
        if self.start_minute == self.end_minute:
            return True
        # Normalize end_minute if >= 1440
        normalized_end = self.end_minute % 1440 if self.end_minute >= 1440 else self.end_minute
        if self.start_minute < normalized_end:
            return self.start_minute <= minute < normalized_end
        return minute >= self.start_minute or minute < normalized_end

    def clamp(self, dt: datetime) -> datetime:
        """Return dt if within window, else next window start."""
        return dt if self.is_within(dt) else self.next_window_start(dt)

    def next_window_start(self, dt: datetime) -> datetime:
        minute = dt.hour * 60 + dt.minute
        start = self.start_minute
        end = self.end_minute

        if start == end:
            return dt

        # Normalize end_minute if >= 1440 for comparison
        normalized_end = end % 1440 if end >= 1440 else end

        if start < normalized_end:
            if minute < start:
                return dt.replace(hour=start // 60, minute=start % 60, second=0, microsecond=0)
            return (dt + timedelta(days=1)).replace(
                hour=start // 60, minute=start % 60, second=0, microsecond=0
            )

        # Overnight window (e.g., 22:00-02:00)
        if minute >= start or minute < normalized_end:
            return dt
        return dt.replace(hour=start // 60, minute=start % 60, second=0, microsecond=0)

    def window_end(self, dt: datetime) -> datetime:
        """Return the end datetime for the window that contains dt."""
        start = self.start_minute
        end = self.end_minute

        if start == end:
            return (dt + timedelta(days=1)).replace(
                hour=dt.hour, minute=dt.minute, second=dt.second, microsecond=dt.microsecond
            )

        start_dt = dt.replace(hour=start // 60, minute=start % 60, second=0, microsecond=0)

        # Handle end_minute >= 1440 (end of day = midnight next day)
        if end >= 1440:
            end_dt = (dt + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            end_dt = dt.replace(hour=end // 60, minute=end % 60, second=0, microsecond=0)

        if start < end:
            return end_dt

        # Overnight window
        if dt >= start_dt:
            return end_dt + timedelta(days=1)
        return end_dt

    def advance_by_active_seconds(self, dt: datetime, active_seconds: float) -> datetime:
        """Advance dt by active seconds counted only within the window."""
        if active_seconds <= 0:
            return self.clamp(dt)

        current = self.clamp(dt)
        remaining = float(active_seconds)

        while True:
            end_dt = self.window_end(current)
            available = (end_dt - current).total_seconds()
            if remaining <= available:
                return current + timedelta(seconds=remaining)
            remaining -= available
            # Move to next window start after end_dt
            current = self.next_window_start(end_dt + timedelta(seconds=1))
