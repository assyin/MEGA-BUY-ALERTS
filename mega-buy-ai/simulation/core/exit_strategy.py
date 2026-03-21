"""
Exit Strategy Engine.

Implements the unified exit strategy for all portfolios:
- Stop Loss: -5%
- Break-Even: Activates at +4%, moves SL to +0.5%
- Trailing Stop: Activates at +15%, trails at -10% from highest
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum

from .position import Position
from ..config.settings import ExitStrategyConfig


class ExitType(Enum):
    """Types of exit."""
    NONE = "NONE"
    STOP_LOSS = "STOP_LOSS"
    BREAK_EVEN = "BREAK_EVEN"
    TRAILING_STOP = "TRAILING_STOP"


@dataclass
class ExitResult:
    """Result of exit check."""
    should_exit: bool
    exit_type: ExitType
    exit_price: float
    reason: str

    @classmethod
    def no_exit(cls) -> "ExitResult":
        """Create a no-exit result."""
        return cls(
            should_exit=False,
            exit_type=ExitType.NONE,
            exit_price=0.0,
            reason=""
        )

    @classmethod
    def exit(cls, exit_type: ExitType, exit_price: float, reason: str) -> "ExitResult":
        """Create an exit result."""
        return cls(
            should_exit=True,
            exit_type=exit_type,
            exit_price=exit_price,
            reason=reason
        )


class ExitStrategy:
    """
    Exit strategy engine.

    Manages stop loss, break-even, and trailing stop for positions.
    """

    def __init__(self, config: Optional[ExitStrategyConfig] = None):
        """
        Initialize exit strategy.

        Args:
            config: Exit strategy configuration
        """
        self.config = config or ExitStrategyConfig()

    @property
    def sl_pct(self) -> float:
        """Stop loss percentage."""
        return self.config.sl_pct

    @property
    def be_activation_pct(self) -> float:
        """Break-even activation percentage."""
        return self.config.be_activation_pct

    @property
    def be_sl_pct(self) -> float:
        """Break-even stop loss percentage."""
        return self.config.be_sl_pct

    @property
    def trailing_activation_pct(self) -> float:
        """Trailing stop activation percentage."""
        return self.config.trailing_activation_pct

    @property
    def trailing_distance_pct(self) -> float:
        """Trailing stop distance percentage."""
        return self.config.trailing_distance_pct

    def calculate_initial_levels(self, entry_price: float) -> dict:
        """
        Calculate initial stop loss and trigger levels.

        Args:
            entry_price: Entry price

        Returns:
            Dictionary with SL, BE trigger, and trailing trigger prices
        """
        return {
            "initial_sl": entry_price * (1 - self.sl_pct / 100),
            "be_trigger": entry_price * (1 + self.be_activation_pct / 100),
            "be_sl": entry_price * (1 + self.be_sl_pct / 100),
            "trailing_trigger": entry_price * (1 + self.trailing_activation_pct / 100),
        }

    def check_exit(
        self,
        position: Position,
        current_price: float,
        current_low: Optional[float] = None
    ) -> Tuple[ExitResult, bool, bool]:
        """
        Check if a position should be exited.

        Args:
            position: The position to check
            current_price: Current price
            current_low: Current candle low (optional, defaults to current_price)

        Returns:
            Tuple of (ExitResult, be_activated, trailing_activated)
        """
        if current_low is None:
            current_low = current_price

        entry_price = position.entry_price
        be_activated = position.be_activated
        trailing_activated = position.trailing_activated

        # Calculate levels
        levels = self.calculate_initial_levels(entry_price)

        # Update highest price
        highest = max(position.highest_price, current_price)

        # PHASE 1: Check initial Stop Loss (if BE not activated)
        if not be_activated:
            if current_low <= levels["initial_sl"]:
                return (
                    ExitResult.exit(
                        ExitType.STOP_LOSS,
                        levels["initial_sl"],
                        f"Stop Loss hit at -{self.sl_pct}%"
                    ),
                    be_activated,
                    trailing_activated
                )

        # PHASE 2: Check Break-Even activation
        if not be_activated and current_price >= levels["be_trigger"]:
            be_activated = True
            position.activate_break_even(levels["be_sl"])

        # PHASE 3: Check Break-Even Stop Loss (if BE activated but trailing not)
        if be_activated and not trailing_activated:
            if current_low <= position.current_sl:
                return (
                    ExitResult.exit(
                        ExitType.BREAK_EVEN,
                        position.current_sl,
                        f"Break-Even SL hit at +{self.be_sl_pct}%"
                    ),
                    be_activated,
                    trailing_activated
                )

        # PHASE 4: Check Trailing activation
        if not trailing_activated and current_price >= levels["trailing_trigger"]:
            trailing_activated = True
            trailing_sl = highest * (1 - self.trailing_distance_pct / 100)
            position.activate_trailing(trailing_sl)

        # PHASE 5: Update and check Trailing Stop
        if trailing_activated:
            # Calculate new trailing SL based on highest
            new_trailing_sl = highest * (1 - self.trailing_distance_pct / 100)

            # Only update if higher
            if position.trailing_sl is None or new_trailing_sl > position.trailing_sl:
                position.update_trailing_sl(new_trailing_sl)

            # Check if trailing SL hit
            if current_low <= position.trailing_sl:
                return (
                    ExitResult.exit(
                        ExitType.TRAILING_STOP,
                        position.trailing_sl,
                        f"Trailing Stop hit at {position.trailing_sl:.2f}"
                    ),
                    be_activated,
                    trailing_activated
                )

        # Update position highest price
        position.update_price(current_price)

        return (ExitResult.no_exit(), be_activated, trailing_activated)

    def get_current_sl_level(self, position: Position) -> float:
        """
        Get the current stop loss level for a position.

        Args:
            position: The position

        Returns:
            Current stop loss price
        """
        if position.trailing_activated and position.trailing_sl:
            return position.trailing_sl
        elif position.be_activated:
            return position.current_sl
        else:
            return position.initial_sl

    def get_position_status(self, position: Position) -> str:
        """
        Get a human-readable status of the position.

        Args:
            position: The position

        Returns:
            Status string
        """
        if position.trailing_activated:
            return "TRAILING"
        elif position.be_activated:
            return "BE_ACTIVE"
        else:
            return "OPEN"

    def calculate_pnl_at_exit(
        self,
        position: Position,
        exit_type: ExitType
    ) -> Tuple[float, float]:
        """
        Calculate P&L at different exit scenarios.

        Args:
            position: The position
            exit_type: Type of exit

        Returns:
            Tuple of (pnl_pct, pnl_usd)
        """
        entry_price = position.entry_price
        allocated = position.allocated_capital

        if exit_type == ExitType.STOP_LOSS:
            pnl_pct = -self.sl_pct
        elif exit_type == ExitType.BREAK_EVEN:
            pnl_pct = self.be_sl_pct
        elif exit_type == ExitType.TRAILING_STOP:
            if position.trailing_sl:
                pnl_pct = ((position.trailing_sl - entry_price) / entry_price) * 100
            else:
                pnl_pct = self.trailing_activation_pct - self.trailing_distance_pct
        else:
            pnl_pct = position.current_pnl_pct

        pnl_usd = allocated * (pnl_pct / 100)
        return (pnl_pct, pnl_usd)
