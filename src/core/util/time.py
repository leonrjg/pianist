"""Utility functions for time formatting."""
from calendar import day_abbr
from datetime import datetime, timedelta
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
    return dt.strftime(f"{day}, %b %d, %Y{' (%H:%M)' if scale < DAY else ''}")

def get_timespan(start: datetime, end: datetime = None) -> int:
    """Get the timespan in seconds between two datetime objects."""
    if not end:
        end = datetime.now()
    return int((end - start).total_seconds())