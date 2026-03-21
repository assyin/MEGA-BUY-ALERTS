"""
V5 Watchlist Management.

Manages alerts that are being monitored for V5 entry conditions.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum

from ..utils.helpers import generate_id, now_utc, parse_datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WatchlistStatus(Enum):
    """Status of a watchlist entry."""
    WATCHING = "WATCHING"
    ENTRY = "ENTRY"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


@dataclass
class WatchlistEntry:
    """
    Represents an alert being monitored for V5 entry conditions.

    V5 Logic requires monitoring 6 conditions over up to 72 hours:
    1. TL Break (close > trendline)
    2. EMA100 1H (close > EMA100)
    3. EMA20 4H (close > EMA20)
    4. Cloud 1H (close > cloud top)
    5. Cloud 30M (close > cloud top)
    6. CHoCH/BOS (swing high broken)
    """
    # Identifiers
    id: str = field(default_factory=generate_id)
    alert_id: str = ""
    pair: str = ""

    # Timing
    alert_timestamp: datetime = field(default_factory=now_utc)
    deadline: datetime = field(default_factory=lambda: now_utc() + timedelta(hours=72))

    # Trendline
    trendline_price: Optional[float] = None

    # Conditions state
    conditions: Dict[str, bool] = field(default_factory=lambda: {
        "tl_break": False,
        "ema100_1h": False,
        "ema20_4h": False,
        "cloud_1h": False,
        "cloud_30m": False,
        "choch_bos": False,
    })

    # Condition values (for display)
    conditions_values: Dict[str, Any] = field(default_factory=dict)

    # Monitoring
    last_check: Optional[datetime] = None
    check_count: int = 0
    status: WatchlistStatus = WatchlistStatus.WATCHING

    # Result
    entry_timestamp: Optional[datetime] = None
    entry_price: Optional[float] = None
    position_id: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Timestamps
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    @property
    def conditions_met_count(self) -> int:
        """Count of conditions met."""
        return sum(1 for v in self.conditions.values() if v)

    @property
    def all_conditions_met(self) -> bool:
        """Check if all 6 conditions are met."""
        return all(self.conditions.values())

    @property
    def is_expired(self) -> bool:
        """Check if deadline has passed."""
        return now_utc() > self.deadline

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining until deadline."""
        return max(self.deadline - now_utc(), timedelta(0))

    @property
    def hours_remaining(self) -> float:
        """Get hours remaining until deadline."""
        return self.time_remaining.total_seconds() / 3600

    @property
    def hours_elapsed(self) -> float:
        """Get hours since alert."""
        delta = now_utc() - self.alert_timestamp
        return delta.total_seconds() / 3600

    def update_condition(self, condition: str, value: bool, actual_value: Any = None) -> None:
        """
        Update a condition.

        Args:
            condition: Condition name
            value: Whether condition is met
            actual_value: Actual value for display
        """
        if condition in self.conditions:
            self.conditions[condition] = value
            if actual_value is not None:
                self.conditions_values[condition] = actual_value
            self.updated_at = now_utc()

    def mark_entry(self, entry_price: float, position_id: str) -> None:
        """Mark as entry successful."""
        self.status = WatchlistStatus.ENTRY
        self.entry_timestamp = now_utc()
        self.entry_price = entry_price
        self.position_id = position_id
        self.updated_at = now_utc()

    def mark_expired(self) -> None:
        """Mark as expired."""
        self.status = WatchlistStatus.EXPIRED
        self.updated_at = now_utc()

    def mark_rejected(self, reason: str) -> None:
        """Mark as rejected."""
        self.status = WatchlistStatus.REJECTED
        self.rejection_reason = reason
        self.updated_at = now_utc()

    def record_check(self) -> None:
        """Record a condition check."""
        self.last_check = now_utc()
        self.check_count += 1
        self.updated_at = now_utc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "alert_id": self.alert_id,
            "pair": self.pair,
            "alert_timestamp": self.alert_timestamp.isoformat() if self.alert_timestamp else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "trendline_price": self.trendline_price,
            "conditions": self.conditions,
            "conditions_values": self.conditions_values,
            "conditions_met": self.conditions_met_count,
            "all_conditions_met": self.all_conditions_met,
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "check_count": self.check_count,
            "status": self.status.value,
            "hours_elapsed": self.hours_elapsed,
            "hours_remaining": self.hours_remaining,
            "entry_timestamp": self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            "entry_price": self.entry_price,
            "position_id": self.position_id,
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatchlistEntry":
        """Create from dictionary."""
        return cls(
            id=data.get("id", generate_id()),
            alert_id=data.get("alert_id", ""),
            pair=data.get("pair", ""),
            alert_timestamp=parse_datetime(data.get("alert_timestamp")) or now_utc(),
            deadline=parse_datetime(data.get("deadline")) or now_utc() + timedelta(hours=72),
            trendline_price=data.get("trendline_price"),
            conditions=data.get("conditions", {}),
            conditions_values=data.get("conditions_values", {}),
            last_check=parse_datetime(data.get("last_check")),
            check_count=data.get("check_count", 0),
            status=WatchlistStatus(data.get("status", "WATCHING")),
            entry_timestamp=parse_datetime(data.get("entry_timestamp")),
            entry_price=data.get("entry_price"),
            position_id=data.get("position_id"),
            rejection_reason=data.get("rejection_reason"),
        )

    @classmethod
    def from_alert(cls, alert: Dict[str, Any], trendline_price: Optional[float] = None) -> "WatchlistEntry":
        """Create from alert data."""
        alert_time = parse_datetime(alert.get("alert_timestamp")) or now_utc()
        return cls(
            alert_id=alert.get("id", ""),
            pair=alert.get("pair", ""),
            alert_timestamp=alert_time,
            deadline=alert_time + timedelta(hours=72),
            trendline_price=trendline_price,
        )


class WatchlistManager:
    """
    Manages the V5 watchlist.
    """

    def __init__(self):
        """Initialize watchlist manager."""
        self._entries: Dict[str, WatchlistEntry] = {}

    def add_entry(self, entry: WatchlistEntry) -> None:
        """Add an entry to the watchlist."""
        self._entries[entry.id] = entry
        logger.info(f"Added to V5 watchlist: {entry.pair} (deadline: {entry.deadline})")

    def remove_entry(self, entry_id: str) -> Optional[WatchlistEntry]:
        """Remove an entry from the watchlist."""
        return self._entries.pop(entry_id, None)

    def get_entry(self, entry_id: str) -> Optional[WatchlistEntry]:
        """Get an entry by ID."""
        return self._entries.get(entry_id)

    def get_entry_by_alert(self, alert_id: str) -> Optional[WatchlistEntry]:
        """Get an entry by alert ID."""
        for entry in self._entries.values():
            if entry.alert_id == alert_id:
                return entry
        return None

    def get_active_entries(self) -> List[WatchlistEntry]:
        """Get all active (WATCHING) entries."""
        return [
            e for e in self._entries.values()
            if e.status == WatchlistStatus.WATCHING
        ]

    def get_all_entries(self) -> List[WatchlistEntry]:
        """Get all entries."""
        return list(self._entries.values())

    def get_expired_entries(self) -> List[WatchlistEntry]:
        """Get expired entries that need to be processed."""
        return [
            e for e in self._entries.values()
            if e.status == WatchlistStatus.WATCHING and e.is_expired
        ]

    def cleanup_completed(self) -> int:
        """Remove completed (ENTRY/EXPIRED/REJECTED) entries."""
        to_remove = [
            eid for eid, e in self._entries.items()
            if e.status in (WatchlistStatus.ENTRY, WatchlistStatus.EXPIRED, WatchlistStatus.REJECTED)
        ]
        for eid in to_remove:
            del self._entries[eid]
        return len(to_remove)

    def get_stats(self) -> Dict[str, int]:
        """Get watchlist statistics."""
        stats = {
            "watching": 0,
            "entry": 0,
            "expired": 0,
            "rejected": 0,
        }
        for entry in self._entries.values():
            stats[entry.status.value.lower()] += 1
        stats["total"] = len(self._entries)
        return stats

    def has_alert(self, alert_id: str) -> bool:
        """Check if alert is already in watchlist."""
        return any(e.alert_id == alert_id for e in self._entries.values())

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
