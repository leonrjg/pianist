"""Utility functions for time formatting."""
from datetime import datetime
import gettext

t = gettext.gettext

# Time constants in seconds
MINUTE = 60
HOUR = 3600
DAY = 86400
WEEK = 604800
MONTH = 2592000

def get_friendly_elapsed(total_seconds: int) -> str:
    """Convert total seconds to an HH:MM:SS format."""
    if type(total_seconds) == float:
        total_seconds = int(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    result = f"{minutes:02d}:{seconds:02d}"
    if hours > 0:
        result = f"{hours:02d}:" + result
    return result

def get_friendly_datetime(dt: datetime, scale: int = DAY) -> str:
    """Format a datetime object into a human-readable string."""
    day = '%a'
    if datetime.now().day == dt.day - 1:
        day = t('Tomorrow')
    elif datetime.now().day == dt.day:
        day = t('Today')
    elif datetime.now().day == dt.day + 1:
        day = t('Yesterday')
    return dt.strftime(f"{day}, %b %d{' at %H:%M' if scale < DAY else ''}")

def get_timespan(start: datetime, end: datetime = None) -> int:
    """Get the timespan in seconds between two datetime objects."""
    if not end:
        end = datetime.now()
    return int((end - start).total_seconds())

def get_naive_timestamp(dt: datetime) -> int:
    """Get timestamp for a naive datetime without timezone conversion.
    
    Calculates seconds since Unix epoch (1970-01-01 00:00:00) treating
    the datetime as-is without any UTC conversion. This is useful for
    aligning time-based calculations when all datetimes are naive and
    represent the same (unspecified) timezone.
    
    Args:
        dt: A naive datetime object.
        
    Returns:
        Integer seconds since naive epoch (1970-01-01 00:00:00).
    """
    naive_epoch = datetime(1970, 1, 1)
    return int((dt - naive_epoch).total_seconds())