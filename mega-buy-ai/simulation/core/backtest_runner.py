"""
Backtest Runner - Runs independently from LIVE simulation.

Replays historical alerts from Supabase while LIVE simulation continues.
All trades are labeled as BACKTEST mode.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta

from ..data.alerts_client import AlertsClient
from ..data.binance_client import BinanceClient
from ..data.database import Database
from ..core.portfolio import Portfolio
from ..core.position import Position, SimulationMode
from ..core.exit_strategy import ExitStrategy
from ..filters.empirical_filters import create_filter_from_config
from ..filters.ml_filters import create_ml_filter_from_config
from ..config.settings import Settings, get_settings
from ..utils.logger import get_logger
from ..utils.helpers import now_utc, generate_id, parse_datetime

logger = get_logger(__name__)


class BacktestRunner:
    """
    Runs backtest simulation independently from LIVE mode.

    Uses Supabase alerts (same source as LIVE mode) for backtesting.
    Can be started/stopped without affecting the main LIVE simulation.
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        database: Optional[Database] = None,
        on_progress: Optional[Callable[[int, int], None]] = None
    ):
        """
        Initialize backtest runner.

        Args:
            settings: Configuration settings
            database: Shared database instance
            on_progress: Callback for progress updates (processed, total)
        """
        self.settings = settings or get_settings()
        self.database = database or Database(self.settings.global_config.database_path)
        self.on_progress = on_progress

        # Alerts client (uses Supabase via dashboard API)
        self.alerts_client = AlertsClient(
            base_url=self.settings.global_config.alerts_api_url
        )

        # Binance client for price updates
        self.binance_client = BinanceClient()

        # Exit strategy
        self.exit_strategy = ExitStrategy(self.settings.exit_strategy)

        # Portfolios (separate instances for backtest)
        self.portfolios: Dict[str, Portfolio] = {}
        self._init_portfolios()

        # Filters
        self.filters: Dict[str, Any] = {}
        self._init_filters()

        # State
        self._running = False
        self._alerts: List[Dict[str, Any]] = []
        self._processed = 0
        self._total = 0
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def _init_portfolios(self) -> None:
        """Initialize separate portfolio instances for backtest."""
        for portfolio_id, config in self.settings.portfolios.items():
            # Create new portfolio with BACKTEST prefix
            portfolio = Portfolio.from_config(config)
            portfolio.id = f"bt_{portfolio_id}"
            portfolio.name = f"[BT] {portfolio.name}"
            self.portfolios[portfolio_id] = portfolio

        logger.info(f"BacktestRunner: Initialized {len(self.portfolios)} portfolios")

    def _init_filters(self) -> None:
        """Initialize filters for each portfolio."""
        for portfolio_id, config in self.settings.portfolios.items():
            if config.type == "empirical_filter":
                self.filters[portfolio_id] = create_filter_from_config(config)
            elif config.type == "p_success_threshold":
                self.filters[portfolio_id] = create_ml_filter_from_config(config)

    @property
    def is_running(self) -> bool:
        """Check if backtest is running."""
        return self._running

    @property
    def progress(self) -> Dict[str, Any]:
        """Get current progress."""
        return {
            "running": self._running,
            "processed": self._processed,
            "total": self._total,
            "remaining": self._total - self._processed,
            "progress_pct": (self._processed / self._total * 100) if self._total > 0 else 0,
            "start_time": self._start_time.isoformat() if self._start_time else None,
        }

    async def start(
        self,
        days: int = 7,
        speed: float = 0.0,
        reset_portfolios: bool = True
    ) -> None:
        """
        Start backtest replay.

        Args:
            days: Number of days to replay
            speed: Replay speed (0 = instant, 1.0 = real-time)
            reset_portfolios: Reset portfolio balances before starting
        """
        if self._running:
            logger.warning("Backtest already running")
            return

        logger.info(f"🟠 Starting BACKTEST: {days} days, speed={speed}")

        self._running = True
        self._start_time = now_utc()
        self._processed = 0

        # Reset portfolios if requested
        if reset_portfolios:
            for portfolio in self.portfolios.values():
                portfolio.reset()

        # Load alerts from Supabase
        self._alerts = await self.alerts_client.fetch_alerts_for_period(days=days)
        self._total = len(self._alerts)

        logger.info(f"🟠 Loaded {self._total} alerts for backtest")

        # Process alerts
        try:
            for alert in self._alerts:
                if not self._running:
                    break

                await self._process_alert(alert)
                self._processed += 1

                # Progress callback
                if self.on_progress:
                    self.on_progress(self._processed, self._total)

                # Progress logging
                if self._processed % 100 == 0:
                    logger.info(
                        f"🟠 BACKTEST: {self._processed}/{self._total} "
                        f"({self.progress['progress_pct']:.1f}%)"
                    )

                # Speed control
                if speed > 0:
                    await asyncio.sleep(1.0 / speed)
                else:
                    await asyncio.sleep(0)  # Yield to event loop

            self._end_time = now_utc()
            logger.info(
                f"🟠 BACKTEST completed: {self._processed}/{self._total} alerts processed"
            )

        except Exception as e:
            logger.error(f"Backtest error: {e}")
        finally:
            self._running = False
            await self.binance_client.close()

    async def stop(self) -> None:
        """Stop backtest replay."""
        if not self._running:
            return

        logger.info("🟠 Stopping BACKTEST...")
        self._running = False

    async def _process_alert(self, alert: Dict[str, Any]) -> None:
        """Process a single alert through all portfolios."""
        pair = alert.get("pair", "")
        price = alert.get("price", 0)
        alert_id = alert.get("id", "")

        # Save alert to local database for later lookups (timeframes, etc.)
        if not self.database.alert_exists(str(alert_id)):
            self.database.save_alert(alert)

        for portfolio_id, portfolio in self.portfolios.items():
            if not portfolio.enabled:
                continue

            # Skip V5 for backtest (too complex for replay)
            if portfolio.type == "v5_surveillance":
                continue

            # Check filter
            filter_obj = self.filters.get(portfolio_id)
            if filter_obj and filter_obj.evaluate(alert):
                # Check if already has position for this pair
                if portfolio.has_position_for_pair(pair):
                    continue

                # Open position
                position = self._open_position(portfolio, alert, price)
                if position:
                    logger.debug(
                        f"🟠 BT {portfolio.name}: Opened {pair} @ {price:.4f}"
                    )

    def _open_position(
        self,
        portfolio: Portfolio,
        alert: Dict[str, Any],
        price: float
    ) -> Optional[Position]:
        """Open a position in backtest mode."""
        if not portfolio.can_open_position:
            # Track ignored position - max trades reached
            self._save_ignored_position(
                portfolio=portfolio,
                alert=alert,
                entry_price=price,
                reason="MAX_TRADES_REACHED",
                required_capital=portfolio.calculate_allocation(),
                available_capital=portfolio.cash_available
            )
            logger.debug(
                f"[IGNORED] {alert.get('pair')} in {portfolio.name}: "
                f"max trades ({portfolio.open_positions_count}/{portfolio.max_concurrent_trades})"
            )
            return None

        allocation = portfolio.calculate_allocation()
        if allocation < 100:
            # Track ignored position - insufficient balance
            self._save_ignored_position(
                portfolio=portfolio,
                alert=alert,
                entry_price=price,
                reason="INSUFFICIENT_BALANCE",
                required_capital=allocation if allocation > 0 else portfolio.position_size_pct / 100 * portfolio.current_balance,
                available_capital=portfolio.cash_available
            )
            logger.debug(
                f"[IGNORED] {alert.get('pair')} in {portfolio.name}: "
                f"insufficient balance (need ${allocation:.2f}, have ${portfolio.cash_available:.2f})"
            )
            return None

        # Calculate stop loss
        levels = self.exit_strategy.calculate_initial_levels(price)

        # Get alert timestamp (use alert's original time)
        alert_ts = alert.get("alert_timestamp")
        entry_time = parse_datetime(alert_ts) if alert_ts else now_utc()

        # Create position with BACKTEST mode
        position = Position(
            id=generate_id(),
            portfolio_id=portfolio.id,
            alert_id=str(alert.get("id", "")),
            pair=alert.get("pair", ""),
            entry_price=price,
            entry_timestamp=entry_time,
            allocated_capital=allocation,
            current_price=price,
            highest_price=price,
            initial_sl=levels["initial_sl"],
            current_sl=levels["initial_sl"],
            mode=SimulationMode.BACKTEST,  # Mark as BACKTEST
        )

        if portfolio.open_position(position):
            self.database.save_position(position.to_dict())
            return position

        return None


    def _save_ignored_position(
        self,
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
            "portfolio_id": portfolio.id,
            "alert_id": str(alert.get("id", "")),
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
            "mode": "BACKTEST"
        }

        self.database.save_ignored_position(ignored_data)

    def get_results(self) -> Dict[str, Any]:
        """Get backtest results."""
        results = {
            "status": "completed" if not self._running else "running",
            "alerts_processed": self._processed,
            "alerts_total": self._total,
            "duration_sec": None,
            "portfolios": [],
        }

        if self._start_time and self._end_time:
            results["duration_sec"] = (self._end_time - self._start_time).total_seconds()

        for portfolio in self.portfolios.values():
            # Include both closed trades and open positions
            open_positions = len(portfolio.open_positions) if hasattr(portfolio, 'open_positions') else 0
            closed_trades = portfolio.stats.total_trades
            total_activity = closed_trades + open_positions

            results["portfolios"].append({
                "id": portfolio.id,
                "name": portfolio.name,
                "balance": portfolio.total_balance,
                "return_pct": portfolio.return_pct,
                "total_trades": total_activity,  # Include open positions
                "closed_trades": closed_trades,
                "open_positions": open_positions,
                "win_rate": portfolio.stats.win_rate,
                "profit_factor": portfolio.stats.profit_factor,
            })

        return results
