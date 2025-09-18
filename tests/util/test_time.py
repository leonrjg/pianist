"""Tests for src.util.time module."""
import pytest
from datetime import datetime
from src.util.time import get_friendly_elapsed, get_friendly_datetime, get_timespan, DAY

def test_get_friendly_elapsed():
    assert get_friendly_elapsed(3661) == "01:01:01"
    assert get_friendly_elapsed(0) == "00:00:00"
    assert get_friendly_elapsed(3599) == "00:59:59"

def test_get_friendly_datetime():
    dt = datetime(2023, 12, 25, 14, 30)
    assert "Mon, Dec 25" in get_friendly_datetime(dt)
    assert "(14:30)" in get_friendly_datetime(dt, scale=3600)
    assert "(14:30)" not in get_friendly_datetime(dt, scale=DAY)

def test_get_timespan():
    start = datetime(2023, 1, 1, 12, 0, 0)
    end = datetime(2023, 1, 1, 12, 1, 0)
    assert get_timespan(start, end) == 60
    
    # Test with default end (now) - just verify it returns an int
    result = get_timespan(start)
    assert isinstance(result, int)