"""
Position Manager.

Manages positions across all portfolios, handles entries and exits.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from .portfolio import Portfolio
from .position import Position, PositionStatus, SimulationMode
from .exit_strategy import ExitStrategy, ExitResult, ExitType
from ..config.settings import Settings, ExitStrategyConfig
from ..data.database import Database
from ..utils.logger import get_logger
from ..utils.helpers import now_utc, generate_id, parse_datetime

logger = get_logger(__name__)


class PositionManager:
    """
    Manages positions across all portfolios.

    Responsibilities:
    - Open positions when alerts pass filters
    - Monitor open positions
    - Execute exits based on exit strategy
    - Update portfolio statistics
    """

    def __init__(
        self,
        portfolios: Dict[str, Portfolio],
        exit_strategy: ExitStrategy,
        database: Database,
        mode: str = "LIVE"
    ):
        """
        Initialize position manager.

        Args:
            portfolios: Dictionary of portfolio_id -> Portfolio
            exit_strategy: Exit strategy engine
            database: Database for persistence
            mode: Simulation mode ("LIVE" or "BACKTEST")
        """
        self.portfolios = portfolios
        self.exit_strategy = exit_strategy
        self.database = database
        self.mode = SimulationMode(mode)

    def open_position(
        self,
        portfolio_id: str,
        alert: Dict[str, Any],
        entry_price: float
    ) -> Optional[Position]:
        """
        Open a position in a portfolio.

        Args:
            portfolio_id: Target portfolio ID
            alert: Alert data
            entry_price: Entry price

        Returns:
            Created position or None if failed
        """
        portfolio = self.portfolios.get(portfolio_id)
        if not portfolio:
            logger.warning(f"Portfolio not found: {portfolio_id}")
            return None

        if not portfolio.can_open_position:
            # Track ignored position - max trades reached
            self._save_ignored_position(
                portfolio_id=portfolio_id,
                portfolio=portfolio,
                alert=alert,
                entry_price=entry_price,
                reason="MAX_TRADES_REACHED",
                required_capital=portfolio.calculate_allocation(),
                available_capital=portfolio.cash_available
            )
            logger.info(
                f"[IGNORED] {alert.get('pair')} in {portfolio_id}: "
                f"max trades reached ({portfolio.open_positions_count}/{portfolio.max_concurrent_trades})"
            )
            return None

        # Calculate allocation
        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            # Track ignored position - insufficient balance
            self._save_ignored_position(
                portfolio_id=portfolio_id,
                portfolio=portfolio,
                alert=alert,
                entry_price=entry_price,
                reason="INSUFFICIENT_BALANCE",
                required_capital=allocation if allocation > 0 else portfolio.position_size_pct / 100 * portfolio.current_balance,
                available_capital=portfolio.cash_available
            )
            logger.info(
                f"[IGNORED] {alert.get('pair')} in {portfolio_id}: "
                f"insufficient balance (need ${allocation:.2f}, have ${portfolio.cash_available:.2f})"
            )
            return None

        # Calculate stop loss levels
        levels = self.exit_strategy.calculate_initial_levels(entry_price)

        # Get alert timestamp (use alert's original time, not current time)
        alert_ts = alert.get("alert_timestamp")
        entry_time = parse_datetime(alert_ts) if alert_ts else now_utc()

        # Create position with mode label
        position = Position(
            id=generate_id(),
            portfolio_id=portfolio_id,
            alert_id=alert.get("id", ""),
            pair=alert.get("pair", ""),
            entry_price=entry_price,
            entry_timestamp=entry_time,
            allocated_capital=allocation,
            current_price=entry_price,
            highest_price=entry_price,
            initial_sl=levels["initial_sl"],
            current_sl=levels["initial_sl"],
            mode=self.mode,  # LIVE or BACKTEST
        )

        # Open in portfolio
        if portfolio.open_position(position):
            # Save to database
            self.database.save_position(position.to_dict())
            self.database.save_portfolio(portfolio.to_dict())

            logger.info(
                f"Opened position in {portfolio.name}: {position.pair} @ {entry_price:.4f} "
                f"(allocation: ${allocation:.2f})"
            )
            return position

        return None

    def check_exits(self, prices: Dict[str, float]) -> List[Tuple[str, Position, ExitResult]]:
        """
        Check all open positions for exit conditions.

        Args:
            prices: Dictionary of symbol -> current price

        Returns:
            List of (portfolio_id, position, exit_result) tuples for closed positions
        """
        closed_positions = []

        for portfolio_id, portfolio in self.portfolios.items():
            # Update prices first
            portfolio.update_prices(prices)

            # Check each open position
            for position in list(portfolio.open_positions):
                if position.pair not in prices:
                    continue

                current_price = prices[position.pair]

                # Check exit
                exit_result, be_activated, trailing_activated = self.exit_strategy.check_exit(
                    position, current_price
                )

                if exit_result.should_exit:
                    # Close position
                    closed_position = portfolio.close_position(
                        position.id,
                        exit_result.exit_price,
                        exit_result.exit_type.value
                    )

                    if closed_position:
                        # Save to database
                        self.database.save_position(closed_position.to_dict())
                        self.database.save_portfolio(portfolio.to_dict())

                        closed_positions.append(
                            (portfolio_id, closed_position, exit_result)
                        )

                        logger.info(
                            f"Closed position in {portfolio.name}: {closed_position.pair} "
                            f"@ {exit_result.exit_price:.4f} "
                            f"({exit_result.exit_type.value}, P&L: {closed_position.final_pnl_pct:.2f}%)"
                        )
                else:
                    # Update position in database
                    self.database.save_position(position.to_dict())

        return closed_positions

    def get_all_open_positions(self) -> List[Position]:
        """Get all open positions across all portfolios."""
        positions = []
        for portfolio in self.portfolios.values():
            positions.extend(portfolio.open_positions)
        return positions

    def get_open_symbols(self) -> set:
        """Get all symbols with open positions."""
        symbols = set()
        for portfolio in self.portfolios.values():
            for position in portfolio.open_positions:
                symbols.add(position.pair)
        return symbols

    def get_portfolio_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all portfolios."""
        return [portfolio.to_summary() for portfolio in self.portfolios.values()]

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """Get a portfolio by ID."""
        return self.portfolios.get(portfolio_id)

    def reset_all(self) -> None:
        """Reset all portfolios to initial state."""
        for portfolio in self.portfolios.values():
            portfolio.reset()
            self.database.save_portfolio(portfolio.to_dict())

        logger.info("All portfolios reset")

    def save_balance_snapshots(self) -> None:
        """Save balance snapshots for all portfolios."""
        for portfolio in self.portfolios.values():
            self.database.save_balance_snapshot(
                portfolio.id,
                portfolio.total_balance
            )

    def load_from_database(self) -> None:
        """Load portfolios and positions from database."""
        # Load open positions
        for portfolio in self.portfolios.values():
            positions_data = self.database.get_open_positions(portfolio.id)
            portfolio.open_positions = [
                Position.from_dict(p) for p in positions_data
            ]

            # Recalculate cash available
            total_allocated = sum(p.allocated_capital for p in portfolio.open_positions)
            portfolio.cash_available = portfolio.current_balance - total_allocated

        logger.info("Loaded positions from database")


    def _save_ignored_position(
        self,
        portfolio_id: str,
        portfolio: Portfolio,
        alert: Dict[str, Any],
        entry_price: float,
        reason: str,
        required_capital: float,
        available_capital: float
    ) -> None:
        """Save an ignored position for tracking."""
        alert_ts = alert.get("alert_timestamp")
        alert_time = parse_datetime(alert_ts) if alert_ts else now_utc()

        # Calculate theoretical SL
        levels = self.exit_strategy.calculate_initial_levels(entry_price)

        ignored_data = {
            "id": generate_id(),
            "portfolio_id": portfolio_id,
            "alert_id": alert.get("id", ""),
            "pair": alert.get("pair", ""),
            "ignore_reason": reason,
            "alert_price": entry_price,
            "alert_timestamp": alert_time.isoformat() if hasattr(alert_time, 'isoformat') else str(alert_time),
            "required_capital": required_capital,
            "available_capital": available_capital,
            "current_price": entry_price,
            "highest_price": entry_price,
            "lowest_price": entry_price,
            "theoretical_pnl_pct": 0.0,
            "theoretical_pnl_usd": 0.0,
            "theoretical_sl": levels["initial_sl"],
            "theoretical_status": "TRACKING",
            "mode": self.mode.value
        }

        self.database.save_ignored_position(ignored_data)

    def update_ignored_positions(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Update all tracking ignored positions with current prices.

        Returns list of ignored positions that hit theoretical SL or TP.
        """
        closed_ignored = []
        tracking_positions = self.database.get_tracking_ignored_positions()

        for ignored in tracking_positions:
            pair = ignored.get("pair")
            if pair not in prices:
                continue

            current_price = prices[pair]
            entry_price = ignored.get("alert_price", 0)
            highest = ignored.get("highest_price", entry_price)
            lowest = ignored.get("lowest_price", entry_price)
            sl_price = ignored.get("theoretical_sl", entry_price * 0.95)

            # Update highest/lowest
            if current_price > highest:
                highest = current_price
            if current_price < lowest:
                lowest = current_price

            # Calculate P&L
            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            # Assume same allocation as portfolio default (12% = $240)
            theoretical_capital = 240.0
            pnl_usd = theoretical_capital * pnl_pct / 100

            # Check if SL hit
            if current_price <= sl_price:
                ignored["theoretical_status"] = "LOSS"
                ignored["theoretical_exit_price"] = sl_price
                ignored["theoretical_exit_timestamp"] = now_utc().isoformat()
                ignored["theoretical_exit_reason"] = "STOP_LOSS"
                ignored["theoretical_pnl_pct"] = -5.0  # Fixed SL at -5%
                ignored["theoretical_pnl_usd"] = -12.0  # $240 * -5%
                closed_ignored.append(ignored)
                logger.info(
                    f"[IGNORED CLOSED] {pair} in {ignored.get('portfolio_id')}: "
                    f"SL hit @ {sl_price:.4f} (Theoretical P&L: -$12.00)"
                )
            # Check if BE activation (4%)
            elif pnl_pct >= 4.0 and ignored.get("theoretical_status") == "TRACKING":
                # Move SL to BE
                sl_price = entry_price * 1.005  # BE + 0.5%
                ignored["theoretical_sl"] = sl_price
            # Check if trailing activation (15%)
            elif pnl_pct >= 15.0:
                # Trailing at 10% from highest
                trailing_sl = highest * 0.90
                if trailing_sl > sl_price:
                    sl_price = trailing_sl
                    ignored["theoretical_sl"] = sl_price
            # Check TP (50%)
            elif pnl_pct >= 50.0:
                ignored["theoretical_status"] = "WIN"
                ignored["theoretical_exit_price"] = current_price
                ignored["theoretical_exit_timestamp"] = now_utc().isoformat()
                ignored["theoretical_exit_reason"] = "TAKE_PROFIT"
                ignored["theoretical_pnl_pct"] = pnl_pct
                ignored["theoretical_pnl_usd"] = pnl_usd
                closed_ignored.append(ignored)
                logger.info(
                    f"[IGNORED CLOSED] {pair} in {ignored.get('portfolio_id')}: "
                    f"TP hit @ {current_price:.4f} (Theoretical P&L: +${pnl_usd:.2f})"
                )

            # Update in database
            ignored["current_price"] = current_price
            ignored["highest_price"] = highest
            ignored["lowest_price"] = lowest
            ignored["theoretical_pnl_pct"] = pnl_pct
            ignored["theoretical_pnl_usd"] = pnl_usd
            self.database.save_ignored_position(ignored)

        return closed_ignored

    def get_ignored_symbols(self) -> set:
        """Get all symbols with tracking ignored positions."""
        tracking = self.database.get_tracking_ignored_positions()
        return {p.get("pair") for p in tracking if p.get("pair")}

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics."""
        total_balance = sum(p.total_balance for p in self.portfolios.values())
        total_initial = sum(p.initial_balance for p in self.portfolios.values())
        total_open = sum(p.open_positions_count for p in self.portfolios.values())
        total_trades = sum(p.stats.total_trades for p in self.portfolios.values())

        return {
            "total_balance": total_balance,
            "total_initial": total_initial,
            "total_pnl": total_balance - total_initial,
            "total_return_pct": ((total_balance - total_initial) / total_initial * 100) if total_initial > 0 else 0,
            "total_open_positions": total_open,
            "total_trades": total_trades,
            "portfolios": len(self.portfolios),
        }
