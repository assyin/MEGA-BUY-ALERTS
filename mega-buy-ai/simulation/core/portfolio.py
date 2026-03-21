"""
Portfolio class representing a trading portfolio with its own balance and positions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any

from .position import Position, PositionStatus
from ..config.settings import PortfolioConfig
from ..utils.helpers import generate_id, now_utc, safe_div


@dataclass
class PortfolioStats:
    """Portfolio statistics."""
    total_trades: int = 0
    winners: int = 0
    losers: int = 0
    total_profit: float = 0.0
    total_loss: float = 0.0
    peak_balance: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0

    @property
    def win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self.total_trades == 0:
            return 0.0
        return (self.winners / self.total_trades) * 100

    @property
    def profit_factor(self) -> float:
        """Calculate profit factor."""
        return safe_div(self.total_profit, abs(self.total_loss), default=0.0)

    @property
    def avg_win(self) -> float:
        """Calculate average winning trade."""
        return safe_div(self.total_profit, self.winners, default=0.0)

    @property
    def avg_loss(self) -> float:
        """Calculate average losing trade."""
        return safe_div(abs(self.total_loss), self.losers, default=0.0)

    @property
    def expectancy(self) -> float:
        """Calculate expectancy per trade."""
        if self.total_trades == 0:
            return 0.0
        wr = self.win_rate / 100
        return (wr * self.avg_win) - ((1 - wr) * self.avg_loss)


@dataclass
class Portfolio:
    """
    Represents a trading portfolio.

    A portfolio has its own balance, positions, and configuration.
    It tracks performance statistics independently.
    """
    # Configuration
    id: str = ""
    name: str = ""
    type: str = ""  # "empirical_filter" | "p_success_threshold" | "v5_surveillance"
    enabled: bool = True

    # Balance
    initial_balance: float = 2000.0
    current_balance: float = 0.0
    cash_available: float = 0.0

    # Position sizing
    position_size_pct: float = 12.0
    max_concurrent_trades: int = 8

    # Statistics
    stats: PortfolioStats = field(default_factory=PortfolioStats)

    # Positions
    open_positions: List[Position] = field(default_factory=list)
    closed_positions: List[Position] = field(default_factory=list)

    # Configuration details (for filtering)
    config: Optional[PortfolioConfig] = None

    # Timestamps
    created_at: datetime = field(default_factory=now_utc)
    updated_at: datetime = field(default_factory=now_utc)

    def __post_init__(self):
        """Initialize derived values."""
        if self.current_balance == 0.0:
            self.current_balance = self.initial_balance
        if self.cash_available == 0.0:
            self.cash_available = self.initial_balance
        if self.stats.peak_balance == 0.0:
            self.stats.peak_balance = self.initial_balance

    @classmethod
    def from_config(cls, config: PortfolioConfig) -> "Portfolio":
        """Create a portfolio from configuration."""
        return cls(
            id=config.id,
            name=config.name,
            type=config.type,
            enabled=config.enabled,
            initial_balance=config.initial_balance,
            current_balance=config.initial_balance,
            cash_available=config.initial_balance,
            position_size_pct=config.position_size_pct,
            max_concurrent_trades=config.max_concurrent_trades,
            config=config,
        )

    @property
    def total_balance(self) -> float:
        """Calculate total balance (cash + open positions)."""
        positions_value = sum(
            p.allocated_capital + p.current_pnl_usd
            for p in self.open_positions
        )
        return self.cash_available + positions_value

    @property
    def return_pct(self) -> float:
        """Calculate return percentage."""
        if self.initial_balance == 0:
            return 0.0
        return ((self.total_balance - self.initial_balance) / self.initial_balance) * 100

    @property
    def pnl_usd(self) -> float:
        """Calculate P&L in USD."""
        return self.total_balance - self.initial_balance

    @property
    def open_positions_count(self) -> int:
        """Get number of open positions."""
        return len(self.open_positions)

    @property
    def can_open_position(self) -> bool:
        """Check if we can open a new position."""
        return (
            self.enabled and
            self.open_positions_count < self.max_concurrent_trades
        )

    def calculate_allocation(self) -> float:
        """
        Calculate the allocation for a new position.

        Returns:
            Allocation amount in USD
        """
        # Calculate target allocation
        target_allocation = self.total_balance * (self.position_size_pct / 100)

        # Check available cash
        if target_allocation > self.cash_available:
            # Use 95% of remaining cash if not enough
            if self.cash_available >= 100:  # Minimum $100
                return self.cash_available * 0.95
            return 0.0

        return target_allocation

    def open_position(self, position: Position) -> bool:
        """
        Open a new position.

        Args:
            position: Position to open

        Returns:
            True if position was opened, False otherwise
        """
        if not self.can_open_position:
            return False

        allocation = self.calculate_allocation()
        if allocation < 100:  # Minimum $100
            return False

        # Update position
        position.portfolio_id = self.id
        position.allocated_capital = allocation

        # Deduct from cash
        self.cash_available -= allocation

        # Add to open positions
        self.open_positions.append(position)

        self.updated_at = now_utc()
        return True

    def close_position(self, position_id: str, exit_price: float, exit_reason: str) -> Optional[Position]:
        """
        Close a position.

        Args:
            position_id: ID of position to close
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            Closed position or None if not found
        """
        # Find position
        position = None
        for i, p in enumerate(self.open_positions):
            if p.id == position_id:
                position = self.open_positions.pop(i)
                break

        if position is None:
            return None

        # Close position
        position.close(exit_price, exit_reason)

        # Calculate P&L
        pnl = position.final_pnl_usd or 0.0

        # Return capital + P&L to cash
        self.cash_available += position.allocated_capital + pnl

        # Update statistics
        self.stats.total_trades += 1
        if pnl > 0:
            self.stats.winners += 1
            self.stats.total_profit += pnl
        else:
            self.stats.losers += 1
            self.stats.total_loss += pnl

        # Add to closed positions
        self.closed_positions.append(position)

        # Update balance tracking
        self._update_balance_tracking()

        self.updated_at = now_utc()
        return position

    def _update_balance_tracking(self) -> None:
        """Update peak balance and drawdown tracking."""
        current = self.total_balance

        # Update peak
        if current > self.stats.peak_balance:
            self.stats.peak_balance = current

        # Calculate drawdown
        if self.stats.peak_balance > 0:
            drawdown = self.stats.peak_balance - current
            drawdown_pct = (drawdown / self.stats.peak_balance) * 100

            if drawdown > self.stats.max_drawdown:
                self.stats.max_drawdown = drawdown
                self.stats.max_drawdown_pct = drawdown_pct

    def update_prices(self, prices: Dict[str, float]) -> None:
        """
        Update prices for all open positions.

        Args:
            prices: Dictionary of pair -> price
        """
        for position in self.open_positions:
            if position.pair in prices:
                position.update_price(prices[position.pair])

        self._update_balance_tracking()
        self.updated_at = now_utc()

    def get_position(self, position_id: str) -> Optional[Position]:
        """Get a position by ID."""
        for p in self.open_positions:
            if p.id == position_id:
                return p
        for p in self.closed_positions:
            if p.id == position_id:
                return p
        return None

    def get_open_position_by_alert(self, alert_id: str) -> Optional[Position]:
        """Get an open position by alert ID."""
        for p in self.open_positions:
            if p.alert_id == alert_id:
                return p
        return None

    def has_position_for_pair(self, pair: str) -> bool:
        """Check if we already have an open position for a pair."""
        return any(p.pair == pair for p in self.open_positions)

    def reset(self) -> None:
        """Reset portfolio to initial state."""
        self.current_balance = self.initial_balance
        self.cash_available = self.initial_balance
        self.open_positions = []
        self.closed_positions = []
        self.stats = PortfolioStats(peak_balance=self.initial_balance)
        self.updated_at = now_utc()

    def to_dict(self) -> Dict[str, Any]:
        """Convert portfolio to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            "total_balance": self.total_balance,
            "cash_available": self.cash_available,
            "return_pct": self.return_pct,
            "pnl_usd": self.pnl_usd,
            "position_size_pct": self.position_size_pct,
            "max_concurrent_trades": self.max_concurrent_trades,
            "open_positions_count": self.open_positions_count,
            "stats": {
                "total_trades": self.stats.total_trades,
                "winners": self.stats.winners,
                "losers": self.stats.losers,
                "win_rate": self.stats.win_rate,
                "profit_factor": self.stats.profit_factor,
                "total_profit": self.stats.total_profit,
                "total_loss": self.stats.total_loss,
                "avg_win": self.stats.avg_win,
                "avg_loss": self.stats.avg_loss,
                "expectancy": self.stats.expectancy,
                "peak_balance": self.stats.peak_balance,
                "max_drawdown": self.stats.max_drawdown,
                "max_drawdown_pct": self.stats.max_drawdown_pct,
            },
            "open_positions": [p.to_dict() for p in self.open_positions],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_summary(self) -> Dict[str, Any]:
        """Get a summary of the portfolio (without positions)."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "enabled": self.enabled,
            "balance": self.total_balance,
            "return_pct": self.return_pct,
            "pnl_usd": self.pnl_usd,
            "win_rate": self.stats.win_rate,
            "profit_factor": self.stats.profit_factor,
            "total_trades": self.stats.total_trades,
            "open_positions": self.open_positions_count,
            "max_drawdown_pct": self.stats.max_drawdown_pct,
        }
