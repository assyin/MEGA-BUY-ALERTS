"""
Main Simulation Orchestrator.

Ties together all components of the live simulation system:
- Alert capture (LIVE mode - runs continuously)
- Portfolio management
- Position management
- Price monitoring
- V5 surveillance
- Exit strategy execution
- Backtest runner (can be triggered independently)

Architecture:
- LIVE mode (🟢): Always running, captures real-time alerts from Supabase
- BACKTEST mode (🟠): Triggered on-demand, replays historical alerts
- Both can run simultaneously
"""

import asyncio
import signal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from .config.settings import Settings, load_config, save_config, get_settings
from .core.portfolio import Portfolio
from .core.position import Position, SimulationMode
from .core.position_manager import PositionManager
from .core.exit_strategy import ExitStrategy
from .core.alert_capture import AlertCapture
from .core.price_monitor import PriceMonitor
from .core.backtest_runner import BacktestRunner
from .data.database import Database
from .data.alerts_client import AlertsClient
from .data.binance_client import BinanceClient
from .filters.empirical_filters import EmpiricalFilter, create_filter_from_config
from .filters.ml_filters import MLFilter, create_ml_filter_from_config
from .v5.watchlist import WatchlistManager, WatchlistEntry, WatchlistStatus
from .v5.condition_checker import V5ConditionChecker
from .utils.logger import init_logging, get_logger
from .utils.helpers import now_utc

logger = get_logger(__name__)


class SimulationOrchestrator:
    """
    Main orchestrator for the live simulation system.

    Always runs in LIVE mode (🟢) capturing real-time alerts.
    Backtest (🟠) can be triggered independently and runs in parallel.
    """

    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize the simulation orchestrator.

        Args:
            settings: Configuration settings (uses default if not provided)
        """
        self.settings = settings or get_settings()

        # Initialize logging
        init_logging(
            level=self.settings.global_config.log_level,
            log_dir="logs"
        )

        logger.info("🚀 Initializing SimulationOrchestrator (LIVE mode)")

        # Database
        self.database = Database(self.settings.global_config.database_path)

        # Exit strategy
        self.exit_strategy = ExitStrategy(self.settings.exit_strategy)

        # Clients - LIVE mode always uses Supabase
        self.binance_client = BinanceClient()
        self.alerts_client = AlertsClient(self.settings.global_config.alerts_api_url)

        # Initialize portfolios
        self.portfolios: Dict[str, Portfolio] = {}
        self._init_portfolios()

        # Position manager (LIVE mode)
        self.position_manager = PositionManager(
            self.portfolios,
            self.exit_strategy,
            self.database,
            mode="LIVE"
        )

        # Filters
        self.filters: Dict[str, Any] = {}
        self._init_filters()

        # V5 components
        self.watchlist_manager = WatchlistManager()
        self.v5_condition_checker = V5ConditionChecker(
            self.binance_client,
            choch_margin_pct=0.5,
            swing_left=5,
            swing_right=3
        )

        # Alert capture (LIVE)
        self.alert_capture = AlertCapture(
            self.alerts_client,
            self.database,
            on_alert_callback=self._on_new_alert
        )

        # Price monitor
        self.price_monitor = PriceMonitor(
            self.binance_client,
            on_price_update=self._on_price_update
        )

        # Backtest runner (independent)
        self.backtest_runner = BacktestRunner(
            settings=self.settings,
            database=self.database
        )
        self._backtest_task: Optional[asyncio.Task] = None

        # State
        self._running = False
        self._tasks: List[asyncio.Task] = []

    def _init_portfolios(self) -> None:
        """Initialize portfolios from configuration."""
        for portfolio_id, config in self.settings.portfolios.items():
            portfolio = Portfolio.from_config(config)
            self.portfolios[portfolio_id] = portfolio

            # Save to database
            self.database.save_portfolio(portfolio.to_dict())

        logger.info(f"Initialized {len(self.portfolios)} portfolios")

    def _init_filters(self) -> None:
        """Initialize filters for each portfolio."""
        for portfolio_id, config in self.settings.portfolios.items():
            if config.type == "empirical_filter":
                self.filters[portfolio_id] = create_filter_from_config(config)
            elif config.type == "p_success_threshold":
                self.filters[portfolio_id] = create_ml_filter_from_config(config)
            # V5 doesn't use filters

        logger.info(f"Initialized {len(self.filters)} filters")

    def apply_config_changes(self, new_settings: Settings) -> None:
        """
        Apply configuration changes at runtime without restart.

        Updates:
        - Exit strategy parameters (SL, BE, trailing)
        - Portfolio settings (enabled, position size, etc.)

        Args:
            new_settings: New settings to apply
        """
        old_exit = self.settings.exit_strategy
        new_exit = new_settings.exit_strategy

        # Update exit strategy config
        self.exit_strategy.config = new_exit

        # Log changes
        if old_exit.sl_pct != new_exit.sl_pct:
            logger.info(f"Config updated: SL {old_exit.sl_pct}% → {new_exit.sl_pct}%")
        if old_exit.be_activation_pct != new_exit.be_activation_pct:
            logger.info(f"Config updated: BE activation {old_exit.be_activation_pct}% → {new_exit.be_activation_pct}%")
        if old_exit.trailing_activation_pct != new_exit.trailing_activation_pct:
            logger.info(f"Config updated: Trailing activation {old_exit.trailing_activation_pct}% → {new_exit.trailing_activation_pct}%")

        # Update portfolio settings
        for pid, new_config in new_settings.portfolios.items():
            if pid in self.portfolios:
                portfolio = self.portfolios[pid]
                old_enabled = portfolio.enabled

                portfolio.enabled = new_config.enabled
                portfolio.position_size_pct = new_config.position_size_pct
                portfolio.max_concurrent_trades = new_config.max_concurrent_trades

                if old_enabled != new_config.enabled:
                    status = "enabled" if new_config.enabled else "disabled"
                    logger.info(f"Config updated: Portfolio {pid} {status}")

        # Update settings reference
        self.settings = new_settings
        logger.info("Configuration changes applied successfully")

    def _on_new_alert(self, alert: Dict[str, Any]) -> None:
        """
        Handle a new alert.

        Args:
            alert: Alert data
        """
        asyncio.create_task(self._process_alert(alert))

    async def _process_alert(self, alert: Dict[str, Any]) -> None:
        """
        Process a new alert through all portfolios.

        Args:
            alert: Alert data
        """
        pair = alert.get("pair", "")
        price = alert.get("price", 0)
        alert_id = alert.get("id", "")

        logger.info(f"Processing alert: {pair} @ {price}")

        # Process for each portfolio
        for portfolio_id, portfolio in self.portfolios.items():
            if not portfolio.enabled:
                continue

            # V5 portfolio - add to watchlist
            if portfolio.type == "v5_surveillance":
                await self._add_to_v5_watchlist(alert, portfolio_id)
                continue

            # Live portfolios - check filter and open position
            filter_obj = self.filters.get(portfolio_id)
            if filter_obj and filter_obj.evaluate(alert):
                # Check if already has position for this pair
                if portfolio.has_position_for_pair(pair):
                    logger.debug(f"{portfolio.name}: Already has position for {pair}")
                    continue

                # Open position
                position = self.position_manager.open_position(
                    portfolio_id, alert, price
                )

                if position:
                    # Add symbol to price monitor
                    self.price_monitor.add_symbol(pair)
                    logger.info(
                        f"{portfolio.name}: Opened position {pair} @ {price}"
                    )
            else:
                reason = filter_obj.get_rejection_reason(alert) if filter_obj else "No filter"
                logger.debug(f"{portfolio.name}: Rejected - {reason}")

    async def _add_to_v5_watchlist(
        self,
        alert: Dict[str, Any],
        portfolio_id: str
    ) -> None:
        """
        Add an alert to V5 watchlist after checking prerequisites.

        Args:
            alert: Alert data
            portfolio_id: V5 portfolio ID
        """
        alert_id = alert.get("id", "")

        # Check if already in watchlist
        if self.watchlist_manager.has_alert(alert_id):
            logger.debug(f"V5: Alert {alert_id} already in watchlist")
            return

        # Check prerequisites
        passes, rejection_reason, trendline_price = await self.v5_condition_checker.check_prerequisites(alert)

        if not passes:
            logger.info(f"V5: Alert {alert['pair']} rejected - {rejection_reason}")
            return

        # Create watchlist entry
        entry = WatchlistEntry.from_alert(alert, trendline_price)
        self.watchlist_manager.add_entry(entry)

        # Save to database
        self.database.save_watchlist_entry(entry.to_dict())

        logger.info(f"V5: Added {alert['pair']} to watchlist (TL @ {trendline_price:.4f})")

    def _on_price_update(self, prices: Dict[str, float]) -> None:
        """
        Handle price updates.

        Args:
            prices: Dictionary of symbol -> price
        """
        # Check exits for LIVE positions
        closed = self.position_manager.check_exits(prices)

        # Update ignored positions (shadow tracking)
        self.position_manager.update_ignored_positions(prices)

        for portfolio_id, position, exit_result in closed:
            portfolio = self.portfolios.get(portfolio_id)
            logger.info(
                f"Exit: {portfolio.name if portfolio else portfolio_id} - "
                f"{position.pair} @ {exit_result.exit_price:.4f} "
                f"({exit_result.exit_type.value}, P&L: {position.final_pnl_pct:.2f}%)"
            )

            # Remove symbol from monitor if no more positions
            if not any(p.pair == position.pair for p in self.position_manager.get_all_open_positions()):
                self.price_monitor.remove_symbol(position.pair)

        # Also update prices and check exits for BACKTEST positions
        if self.backtest_runner and self.backtest_runner.portfolios:
            for portfolio in self.backtest_runner.portfolios.values():
                portfolio.update_prices(prices)

                # Check exits for each open position
                for position in list(portfolio.open_positions):
                    if position.pair not in prices:
                        continue

                    current_price = prices[position.pair]
                    exit_result, be_activated, trailing_activated = self.exit_strategy.check_exit(
                        position, current_price
                    )

                    if exit_result.should_exit:
                        closed_position = portfolio.close_position(
                            position.id,
                            exit_result.exit_price,
                            exit_result.exit_type.value
                        )
                        if closed_position:
                            self.database.save_position(closed_position.to_dict())
                            self.database.save_portfolio(portfolio.to_dict())
                            logger.info(
                                f"🟠 BT Exit: {portfolio.name} - {closed_position.pair} "
                                f"@ {exit_result.exit_price:.4f} ({exit_result.exit_type.value}, "
                                f"P&L: {closed_position.final_pnl_pct:.2f}%)"
                            )

    async def _v5_monitoring_loop(self) -> None:
        """V5 condition monitoring loop."""
        v5_config = self.settings.portfolios.get("backtest_v5")
        interval = 900  # 15 minutes default

        if v5_config and v5_config.v5_config:
            interval = v5_config.v5_config.monitoring_interval_sec

        while self._running:
            try:
                await self._check_v5_conditions()
            except Exception as e:
                logger.error(f"Error in V5 monitoring loop: {e}")

            await asyncio.sleep(interval)

    async def _check_v5_conditions(self) -> None:
        """Check conditions for all V5 watchlist entries."""
        # Check for expired entries first
        for entry in self.watchlist_manager.get_expired_entries():
            entry.mark_expired()
            self.database.save_watchlist_entry(entry.to_dict())
            logger.info(f"V5: {entry.pair} expired without entry")

        # Check conditions for active entries
        for entry in self.watchlist_manager.get_active_entries():
            result = await self.v5_condition_checker.check_conditions(entry)

            # Update database
            self.database.save_watchlist_entry(entry.to_dict())

            if result.all_met:
                # All conditions met - execute entry
                await self._execute_v5_entry(entry)
            else:
                logger.debug(
                    f"V5: {entry.pair} - {entry.conditions_met_count}/6 conditions met"
                )

        # Cleanup completed entries
        cleaned = self.watchlist_manager.cleanup_completed()
        if cleaned > 0:
            logger.debug(f"V5: Cleaned up {cleaned} completed watchlist entries")

    async def _execute_v5_entry(self, entry: WatchlistEntry) -> None:
        """
        Execute entry for a V5 watchlist entry.

        Args:
            entry: Watchlist entry with all conditions met
        """
        portfolio_id = "backtest_v5"
        portfolio = self.portfolios.get(portfolio_id)

        if not portfolio or not portfolio.can_open_position:
            logger.warning(f"V5: Cannot open position - portfolio unavailable or max trades reached")
            return

        # Get current price
        price = await self.binance_client.get_price(entry.pair)
        if not price:
            logger.error(f"V5: Could not get price for {entry.pair}")
            return

        # Create alert-like data
        alert = {
            "id": entry.alert_id,
            "pair": entry.pair,
            "price": price,
        }

        # Open position
        position = self.position_manager.open_position(portfolio_id, alert, price)

        if position:
            # Update watchlist entry
            entry.mark_entry(price, position.id)
            self.database.save_watchlist_entry(entry.to_dict())

            # Add to price monitor
            self.price_monitor.add_symbol(entry.pair)

            logger.info(
                f"V5: Entry executed - {entry.pair} @ {price:.4f} "
                f"(after {entry.hours_elapsed:.1f}h, {entry.check_count} checks)"
            )

    async def _balance_snapshot_loop(self) -> None:
        """Periodic balance snapshot loop."""
        while self._running:
            self.position_manager.save_balance_snapshots()
            await asyncio.sleep(300)  # Every 5 minutes

    async def start(self) -> None:
        """Start the LIVE simulation (runs continuously)."""
        if self._running:
            logger.warning("Simulation already running")
            return

        self._running = True

        # Update simulation state
        self.database.update_simulation_state({
            "status": "RUNNING_LIVE",
            "started_at": now_utc().isoformat(),
            "stopped_at": None,
        })

        # Load existing positions
        self.position_manager.load_from_database()

        # Add existing position symbols to price monitor
        for position in self.position_manager.get_all_open_positions():
            self.price_monitor.add_symbol(position.pair)

        # Start LIVE mode components
        await self.alert_capture.start(self.settings.global_config.alert_polling_interval_sec)
        await self.price_monitor.start(self.settings.global_config.price_polling_interval_sec)

        # Start V5 monitoring
        self._tasks.append(asyncio.create_task(self._v5_monitoring_loop()))

        # Start balance snapshots
        self._tasks.append(asyncio.create_task(self._balance_snapshot_loop()))

        logger.info("🟢 LIVE Simulation started - monitoring real-time alerts 24/7")

    async def start_backtest(self, days: int = 7, speed: float = 0.0) -> Dict[str, Any]:
        """
        Start backtest replay (runs in parallel with LIVE).

        Args:
            days: Number of days to replay
            speed: Replay speed (0 = instant)

        Returns:
            Status dict
        """
        if self.backtest_runner.is_running:
            return {"success": False, "error": "Backtest already running"}

        # Run backtest in background task
        self._backtest_task = asyncio.create_task(
            self._run_backtest_and_sync(days=days, speed=speed)
        )

        logger.info(f"🟠 BACKTEST started: {days} days, speed={speed}")
        return {
            "success": True,
            "message": f"Backtest started for {days} days",
            "mode": "BACKTEST"
        }

    async def _run_backtest_and_sync(self, days: int, speed: float) -> None:
        """Run backtest and add symbols to price monitor when done."""
        await self.backtest_runner.start(days=days, speed=speed)

        # After backtest completes, add all backtest position symbols to price monitor
        for portfolio in self.backtest_runner.portfolios.values():
            for position in portfolio.open_positions:
                self.price_monitor.add_symbol(position.pair)

        logger.info(f"🟠 BACKTEST: Added {sum(len(p.open_positions) for p in self.backtest_runner.portfolios.values())} symbols to price monitor")

    async def stop_backtest(self) -> Dict[str, Any]:
        """Stop the backtest replay."""
        if not self.backtest_runner.is_running:
            return {"success": False, "error": "No backtest running"}

        await self.backtest_runner.stop()

        if self._backtest_task:
            self._backtest_task.cancel()
            try:
                await self._backtest_task
            except asyncio.CancelledError:
                pass
            self._backtest_task = None

        logger.info("🟠 BACKTEST stopped")
        return {"success": True, "message": "Backtest stopped"}

    def get_backtest_status(self) -> Dict[str, Any]:
        """Get backtest progress and status."""
        return self.backtest_runner.progress

    def get_backtest_results(self) -> Dict[str, Any]:
        """Get backtest results."""
        return self.backtest_runner.get_results()

    async def stop(self) -> None:
        """Stop the LIVE simulation."""
        if not self._running:
            return

        self._running = False

        # Stop LIVE components
        await self.alert_capture.stop()
        await self.price_monitor.stop()

        # Stop backtest if running
        if self.backtest_runner.is_running:
            await self.backtest_runner.stop()
        if self._backtest_task:
            self._backtest_task.cancel()
            try:
                await self._backtest_task
            except asyncio.CancelledError:
                pass

        # Cancel tasks
        for task in self._tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        self._tasks.clear()

        # Close clients
        await self.alerts_client.close()
        await self.binance_client.close()

        # Update simulation state
        self.database.update_simulation_state({
            "status": "STOPPED",
            "stopped_at": now_utc().isoformat(),
        })

        logger.info("🟢 LIVE Simulation stopped")

    def get_status(self) -> Dict[str, Any]:
        """Get simulation status."""
        status = {
            "running": self._running,
            "live_mode": {
                "active": self._running,
                "emoji": "🟢",
                "alerts_captured": self.alert_capture.get_seen_count() if self.alert_capture else 0,
            },
            "backtest_mode": {
                "active": self.backtest_runner.is_running,
                "emoji": "🟠",
                **self.backtest_runner.progress,
            },
            "portfolios": self.position_manager.get_portfolio_summary(),
            "stats": self.position_manager.get_stats(),
            "watchlist": self.watchlist_manager.get_stats(),
            "price_monitor": {
                "symbols": len(self.price_monitor.get_watched_symbols()),
                "last_update": self.price_monitor.last_update.isoformat() if self.price_monitor.last_update else None,
            },
        }

        return status

    def reset(self) -> None:
        """Reset the simulation."""
        if self._running:
            raise RuntimeError("Cannot reset while simulation is running")

        self.position_manager.reset_all()
        self.watchlist_manager.clear()
        self.alert_capture.clear_seen()
        self.database.clear_all_data()
        self._init_portfolios()

        logger.info("Simulation reset")


async def run_simulation():
    """
    Main entry point for running the simulation.

    LIVE mode runs continuously. Backtest can be triggered via API.
    """
    orchestrator = SimulationOrchestrator()

    # Handle shutdown signals
    def handle_shutdown(sig):
        logger.info(f"Received signal {sig}, shutting down...")
        asyncio.create_task(orchestrator.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_event_loop().add_signal_handler(sig, lambda s=sig: handle_shutdown(s))

    try:
        await orchestrator.start()

        # Keep running
        while orchestrator._running:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        await orchestrator.stop()


if __name__ == "__main__":
    asyncio.run(run_simulation())
