"""Utility functions for time handling and conversions"""

from datetime import datetime, timezone


def iso_to_dt(iso_str):
    """Convert ISO string to UTC datetime object"""
    # Handle both string and numeric timestamps
    if isinstance(iso_str, (int, float)):
        ts = int(iso_str)
        # If timestamp is in milliseconds, convert to seconds
        if ts > 10**10:  # Timestamps in milliseconds are larger than 10^10
            ts = ts // 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    else:
        return datetime.fromisoformat(iso_str.replace("Z","")).astimezone(timezone.utc)


def now_utc():
    """Get current UTC datetime"""
    return datetime.now(timezone.utc)