"""
Position class representing an open or closed trading position.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

from ..utils.helpers import generate_id, now_utc, calculate_pct_change


class PositionStatus(Enum):
    """Position status enumeration."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ExitReason(Enum):
    """Exit reason enumeration."""
    STOP_LOSS = "STOP_LOSS"
    BREAK_EVEN = "BREAK_EVEN"
    TRAILING_STOP = "TRAILING_STOP"
    MANUAL = "MANUAL"


class SimulationMode(Enum):
    """Simulation mode enumeration."""
    LIVE = "LIVE"
    BACKTEST = "BACKTEST"


@dataclass
class Position:
    """
    Represents a trading position.

    Attributes:
        id: Unique position identifier
        portfolio_id: ID of the portfolio this position belongs to
        alert_id: ID of the alert that triggered this position
        pair: Trading pair (e.g., "BTCUSDT")
        entry_price: Entry price
        entry_timestamp: When the position was opened
        allocated_capital: Capital allocated to this position in USD
    """
    # Identifiers
    id: str = field(default_factory=generate_id)
    portfolio_id: str = ""
    alert_id: str = ""
    pair: str = ""

    # Entry
    entry_price: float = 0.0
    entry_timestamp: datetime = field(default_factory=now_utc)
    allocated_capital: float = 0.0

    # Current state
    current_price: float = 0.0
    highest_price: float = 0.0
    lowest_price: float = float('inf')

    # Stop Loss Management
    initial_sl: float = 0.0
    current_sl: float = 0.0
    be_activated: bool = False
    be_activation_price: float = 0.0
    trailing_activated: bool = False
    trailing_activation_price: float = 0.0
    trailing_sl: Optional[float] = None

    # Exit
    exit_price: Optional[float] = None
    exit_timestamp: Optional[datetime] = None
    exit_reason: Optional[str] = None

    # Status
    status: PositionStatus = PositionStatus.OPEN

    # Mode (LIVE or BACKTEST)
    mode: SimulationMode = SimulationMode.LIVE

    # Timestamps
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self):
        """Initialize derived values."""
        if self.current_price == 0.0:
            self.current_price = self.entry_price
        if self.highest_price == 0.0:
            self.highest_price = self.entry_price
        if self.lowest_price == float('inf'):
            self.lowest_price = self.entry_price

    @property
    def current_pnl_pct(self) -> float:
        """Calculate current P&L percentage."""
        if self.status == PositionStatus.CLOSED and self.exit_price:
            return calculate_pct_change(self.entry_price, self.exit_price)
        return calculate_pct_change(self.entry_price, self.current_price)

    @property
    def current_pnl_usd(self) -> float:
        """Calculate current P&L in USD."""
        return self.allocated_capital * (self.current_pnl_pct / 100)

    @property
    def final_pnl_pct(self) -> Optional[float]:
        """Get final P&L percentage (only for closed positions)."""
        if self.status == PositionStatus.CLOSED and self.exit_price:
            return calculate_pct_change(self.entry_price, self.exit_price)
        return None

    @property
    def final_pnl_usd(self) -> Optional[float]:
        """Get final P&L in USD (only for closed positions)."""
        pnl_pct = self.final_pnl_pct
        if pnl_pct is not None:
            return self.allocated_capital * (pnl_pct / 100)
        return None

    @property
    def is_open(self) -> bool:
        """Check if position is open."""
        return self.status == PositionStatus.OPEN

    @property
    def is_winner(self) -> bool:
        """Check if position is a winner (only valid for closed positions)."""
        pnl = self.final_pnl_pct
        return pnl is not None and pnl > 0

    def update_price(self, price: float) -> None:
        """
        Update current price and track high/low.

        Args:
            price: New current price
        """
        self.current_price = price
        self.highest_price = max(self.highest_price, price)
        self.lowest_price = min(self.lowest_price, price)
        self.updated_at = now_utc()

    def activate_break_even(self, new_sl: float) -> None:
        """
        Activate break-even stop loss.

        Args:
            new_sl: New stop loss price (typically entry + small margin)
        """
        self.be_activated = True
        self.be_activation_price = self.current_price
        self.current_sl = new_sl
        self.updated_at = now_utc()

    def activate_trailing(self, trailing_sl: float) -> None:
        """
        Activate trailing stop.

        Args:
            trailing_sl: Initial trailing stop loss price
        """
        self.trailing_activated = True
        self.trailing_activation_price = self.current_price
        self.trailing_sl = trailing_sl
        self.updated_at = now_utc()

    def update_trailing_sl(self, new_trailing_sl: float) -> None:
        """
        Update trailing stop loss to a higher level.

        Args:
            new_trailing_sl: New trailing stop loss price
        """
        if self.trailing_sl is None or new_trailing_sl > self.trailing_sl:
            self.trailing_sl = new_trailing_sl
            self.updated_at = now_utc()

    def close(self, exit_price: float, exit_reason: str) -> None:
        """
        Close the position.

        Args:
            exit_price: Price at which position was closed
            exit_reason: Reason for closing (STOP_LOSS, BREAK_EVEN, TRAILING_STOP)
        """
        self.exit_price = exit_price
        self.exit_timestamp = now_utc()
        self.exit_reason = exit_reason
        self.status = PositionStatus.CLOSED
        self.current_price = exit_price
        self.updated_at = now_utc()

    def to_dict(self) -> dict:
        """Convert position to dictionary."""
        return {
            "id": self.id,
            "portfolio_id": self.portfolio_id,
            "alert_id": self.alert_id,
            "pair": self.pair,
            "entry_price": self.entry_price,
            "entry_timestamp": self.entry_timestamp.isoformat() if self.entry_timestamp else None,
            "allocated_capital": self.allocated_capital,
            "current_price": self.current_price,
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "current_pnl_pct": self.current_pnl_pct,
            "current_pnl_usd": self.current_pnl_usd,
            "initial_sl": self.initial_sl,
            "current_sl": self.current_sl,
            "be_activated": self.be_activated,
            "trailing_activated": self.trailing_activated,
            "trailing_sl": self.trailing_sl,
            "exit_price": self.exit_price,
            "exit_timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp else None,
            "exit_reason": self.exit_reason,
            "final_pnl_pct": self.final_pnl_pct,
            "final_pnl_usd": self.final_pnl_usd,
            "status": self.status.value,
            "mode": self.mode.value,
            "last_sync": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Position":
        """Create position from dictionary."""
        from ..utils.helpers import parse_datetime

        return cls(
            id=data.get("id", generate_id()),
            portfolio_id=data.get("portfolio_id", ""),
            alert_id=data.get("alert_id", ""),
            pair=data.get("pair", ""),
            entry_price=data.get("entry_price", 0.0),
            entry_timestamp=parse_datetime(data.get("entry_timestamp")) or now_utc(),
            allocated_capital=data.get("allocated_capital", 0.0),
            current_price=data.get("current_price", 0.0),
            highest_price=data.get("highest_price", 0.0),
            lowest_price=data.get("lowest_price", float('inf')),
            initial_sl=data.get("initial_sl", 0.0),
            current_sl=data.get("current_sl", 0.0),
            be_activated=data.get("be_activated", False),
            trailing_activated=data.get("trailing_activated", False),
            trailing_sl=data.get("trailing_sl"),
            exit_price=data.get("exit_price"),
            exit_timestamp=parse_datetime(data.get("exit_timestamp")),
            exit_reason=data.get("exit_reason"),
            status=PositionStatus(data.get("status", "OPEN")),
            mode=SimulationMode(data.get("mode", "LIVE")),
        )
