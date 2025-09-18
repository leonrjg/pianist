"""Utility functions for time formatting."""
from datetime import datetime

# Time constants in seconds
MINUTE = 60
HOUR = 3600
DAY = 86400
WEEK = 604800
MONTH = 2592000

def get_friendly_elapsed(total_seconds: int) -> str:
    """Convert total seconds to an HH:MM:SS format."""
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def get_friendly_datetime(dt: datetime, scale: int = DAY) -> str:
    """Format a datetime object into a human-readable string."""
    return dt.strftime(f"%a, %b %d{' (%H:%M)' if scale < DAY else ''}")

def get_timespan(start: datetime, end: datetime = None) -> int:
    """Get the timespan in seconds between two datetime objects."""
    if not end:
        end = datetime.now()
    return int((end - start).total_seconds())