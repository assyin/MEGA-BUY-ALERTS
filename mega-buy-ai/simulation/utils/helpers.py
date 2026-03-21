"""
Utility functions and helpers.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, Union


def generate_id() -> str:
    """Generate a unique ID."""
    return str(uuid.uuid4())


def parse_datetime(dt_str: Union[str, datetime, None]) -> Optional[datetime]:
    """
    Parse a datetime string to datetime object.
    Handles various formats including ISO with timezone.
    """
    if dt_str is None:
        return None

    if isinstance(dt_str, datetime):
        return dt_str

    # Handle timezone formats like +00:00
    if isinstance(dt_str, str):
        # Try Python's fromisoformat first (handles +00:00)
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            # Return naive datetime (strip timezone for consistency)
            return dt.replace(tzinfo=None)
        except ValueError:
            pass

    # Try various formats as fallback
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    raise ValueError(f"Could not parse datetime: {dt_str}")


def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def format_currency(amount: float, decimals: int = 2) -> str:
    """Format a number as currency."""
    if amount >= 0:
        return f"${amount:,.{decimals}f}"
    else:
        return f"-${abs(amount):,.{decimals}f}"


def format_percent(value: float, decimals: int = 1) -> str:
    """Format a number as percentage."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def calculate_pct_change(entry: float, current: float) -> float:
    """Calculate percentage change."""
    if entry == 0:
        return 0.0
    return ((current - entry) / entry) * 100


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hours_between(start: datetime, end: datetime) -> float:
    """Calculate hours between two datetimes."""
    delta = end - start
    return delta.total_seconds() / 3600


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that returns default if denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator
