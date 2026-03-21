"""
API Routes for the Simulation Dashboard.

Provides REST endpoints for:
- Simulation status and control
- Portfolio data
- Position data
- V5 watchlist
- Configuration
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json

from ..main import SimulationOrchestrator
from ..config.settings import get_settings, save_config, Settings
from ..data.database import Database
from ..utils.helpers import now_utc


class SimulationAPI:
    """
    API handler for the simulation dashboard.

    This class provides methods that can be used with any web framework
    (FastAPI, Flask, etc.) to expose the simulation data.
    """

    def __init__(self, orchestrator: SimulationOrchestrator):
        """
        Initialize API.

        Args:
            orchestrator: Simulation orchestrator instance
        """
        self.orchestrator = orchestrator
        self.database = orchestrator.database

    # ===== OVERVIEW =====

    def get_overview(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """Get overview of the simulation.

        Args:
            mode: Filter by mode - "LIVE", "BACKTEST", or None for combined view
        """
        status = self.orchestrator.get_status()

        # LIVE portfolios stats
        live_portfolios = status["portfolios"]
        live_total_balance = sum(p["balance"] for p in live_portfolios)
        live_total_initial = sum(self.orchestrator.portfolios[p["id"]].initial_balance for p in live_portfolios)
        live_total_pnl = live_total_balance - live_total_initial
        live_total_return_pct = (live_total_pnl / live_total_initial * 100) if live_total_initial > 0 else 0
        live_open_positions = sum(p["open_positions"] for p in live_portfolios)
        live_total_trades = sum(p["total_trades"] for p in live_portfolios)

        # BACKTEST portfolios stats
        backtest_portfolios = []
        bt_total_balance = 0
        bt_total_initial = 0
        bt_total_pnl = 0
        bt_total_return_pct = 0
        bt_open_positions = 0
        bt_total_trades = 0

        if self.orchestrator.backtest_runner:
            for portfolio in self.orchestrator.backtest_runner.portfolios.values():
                bt_total_balance += portfolio.total_balance
                bt_total_initial += portfolio.initial_balance
                bt_open_positions += portfolio.open_positions_count
                bt_total_trades += portfolio.stats.total_trades

                # V5 is skipped in backtest - mark as live_only
                is_v5 = portfolio.type == "v5_surveillance"

                backtest_portfolios.append({
                    "id": portfolio.id,
                    "name": portfolio.name,
                    "type": portfolio.type,
                    "enabled": portfolio.enabled,
                    "balance": portfolio.total_balance,
                    "return_pct": portfolio.return_pct,
                    "pnl_usd": portfolio.total_balance - portfolio.initial_balance,
                    "win_rate": portfolio.stats.win_rate,
                    "profit_factor": portfolio.stats.profit_factor,
                    "total_trades": portfolio.stats.total_trades,
                    "open_positions": portfolio.open_positions_count,
                    "max_drawdown_pct": portfolio.stats.max_drawdown_pct,
                    "live_only": is_v5,  # Flag for V5 portfolios
                })
            bt_total_pnl = bt_total_balance - bt_total_initial
            bt_total_return_pct = (bt_total_pnl / bt_total_initial * 100) if bt_total_initial > 0 else 0

        # Build response based on mode filter
        if mode == "LIVE":
            return {
                "mode": "LIVE",
                "emoji": "🟢",
                "running": status["running"],
                "timestamp": now_utc().isoformat(),
                "alerts_captured": status.get("live_mode", {}).get("alerts_captured", 0),
                "global": {
                    "total_initial": live_total_initial,
                    "total_balance": live_total_balance,
                    "total_pnl": live_total_pnl,
                    "total_return_pct": live_total_return_pct,
                    "total_open_positions": live_open_positions,
                    "total_trades": live_total_trades,
                },
                "portfolios": live_portfolios,
                "watchlist_stats": status["watchlist"],
            }

        elif mode == "BACKTEST":
            bt_status = status.get("backtest_mode", {})
            return {
                "mode": "BACKTEST",
                "emoji": "🟠",
                "running": bt_status.get("running", False),
                "timestamp": now_utc().isoformat(),
                "progress": {
                    "processed": bt_status.get("processed", 0),
                    "total": bt_status.get("total", 0),
                    "progress_pct": bt_status.get("progress_pct", 0),
                },
                "global": {
                    "total_initial": bt_total_initial,
                    "total_balance": bt_total_balance,
                    "total_pnl": bt_total_pnl,
                    "total_return_pct": bt_total_return_pct,
                    "total_open_positions": bt_open_positions,
                    "total_trades": bt_total_trades,
                },
                "portfolios": backtest_portfolios,
            }

        # Default: combined view with both modes
        return {
            "running": status["running"],
            "timestamp": now_utc().isoformat(),
            "live": {
                "emoji": "🟢",
                "active": status.get("live_mode", {}).get("active", False),
                "alerts_captured": status.get("live_mode", {}).get("alerts_captured", 0),
                "global": {
                    "total_initial": live_total_initial,
                    "total_balance": live_total_balance,
                    "total_pnl": live_total_pnl,
                    "total_return_pct": live_total_return_pct,
                    "total_open_positions": live_open_positions,
                    "total_trades": live_total_trades,
                },
                "portfolios": live_portfolios,
            },
            "backtest": {
                "emoji": "🟠",
                "active": status.get("backtest_mode", {}).get("running", False),
                "progress": {
                    "processed": status.get("backtest_mode", {}).get("processed", 0),
                    "total": status.get("backtest_mode", {}).get("total", 0),
                    "progress_pct": status.get("backtest_mode", {}).get("progress_pct", 0),
                },
                "global": {
                    "total_initial": bt_total_initial,
                    "total_balance": bt_total_balance,
                    "total_pnl": bt_total_pnl,
                    "total_return_pct": bt_total_return_pct,
                    "total_open_positions": bt_open_positions,
                    "total_trades": bt_total_trades,
                },
                "portfolios": backtest_portfolios,
            },
            "watchlist_stats": status["watchlist"],
        }

    # ===== PORTFOLIOS =====

    def get_portfolios(self) -> list:
        """Get all portfolios."""
        return [p.to_dict() for p in self.orchestrator.portfolios.values()]

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific portfolio."""
        portfolio = self.orchestrator.portfolios.get(portfolio_id)
        if portfolio:
            return portfolio.to_dict()
        return None

    def get_portfolio_history(self, portfolio_id: str, limit: int = 1000) -> list:
        """Get balance history for a portfolio."""
        return self.database.get_balance_history(portfolio_id, limit)

    # ===== POSITIONS =====

    def get_open_positions(
        self,
        portfolio_id: Optional[str] = None,
        detailed: bool = False,
        mode: Optional[str] = None  # "LIVE", "BACKTEST", or None for all
    ) -> list:
        """Get open positions filtered by mode.

        Args:
            portfolio_id: Optional filter by portfolio
            detailed: If True, include full details for each position
            mode: Filter by mode - "LIVE", "BACKTEST", or None for all
        """
        positions = []

        # LIVE positions (if mode is None or "LIVE")
        if mode is None or mode == "LIVE":
            if portfolio_id:
                portfolio = self.orchestrator.portfolios.get(portfolio_id)
                if portfolio:
                    for p in portfolio.open_positions:
                        if detailed:
                            positions.append(self.get_position(p.id))
                        else:
                            pos_dict = p.to_dict()
                            pos_dict["portfolio_name"] = portfolio.name
                            # Add alert timeframes
                            if p.alert_id:
                                alert = self.database.get_alert(p.alert_id)
                                if alert:
                                    pos_dict["timeframes"] = alert.get("timeframes", "")
                            positions.append(pos_dict)
            else:
                for portfolio in self.orchestrator.portfolios.values():
                    for p in portfolio.open_positions:
                        if detailed:
                            positions.append(self.get_position(p.id))
                        else:
                            pos_dict = p.to_dict()
                            pos_dict["portfolio_name"] = portfolio.name
                            # Add alert timeframes
                            if p.alert_id:
                                alert = self.database.get_alert(p.alert_id)
                                if alert:
                                    pos_dict["timeframes"] = alert.get("timeframes", "")
                            positions.append(pos_dict)

        # BACKTEST positions (if mode is None or "BACKTEST")
        if (mode is None or mode == "BACKTEST") and self.orchestrator.backtest_runner:
            for portfolio in self.orchestrator.backtest_runner.portfolios.values():
                for p in portfolio.open_positions:
                    pos_dict = p.to_dict()
                    pos_dict["portfolio_name"] = portfolio.name
                    pos_dict["portfolio_type"] = portfolio.type
                    # Add alert timeframes for backtest positions
                    if p.alert_id:
                        alert = self.database.get_alert(p.alert_id)
                        if alert:
                            pos_dict["timeframes"] = alert.get("timeframes", "")
                    positions.append(pos_dict)

        return positions

    def get_closed_positions(
        self,
        portfolio_id: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """Get closed positions with portfolio names."""
        positions = self.database.get_closed_positions(portfolio_id, limit)

        # Build portfolio name mapping
        portfolio_names = {}
        for p in self.orchestrator.portfolios.values():
            portfolio_names[p.id] = p.name
        if self.orchestrator.backtest_runner:
            for p in self.orchestrator.backtest_runner.portfolios.values():
                portfolio_names[p.id] = p.name

        # Add portfolio names to positions
        for pos in positions:
            pid = pos.get("portfolio_id", "")
            pos["portfolio_name"] = portfolio_names.get(pid, pid)

        return positions

    def get_position(self, position_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific position with full details including alert data."""
        # Search in LIVE portfolios first
        for portfolio in self.orchestrator.portfolios.values():
            position = portfolio.get_position(position_id)
            if position:
                return self._build_position_details(position, portfolio)

        # Search in BACKTEST portfolios
        if self.orchestrator.backtest_runner:
            for portfolio in self.orchestrator.backtest_runner.portfolios.values():
                position = portfolio.get_position(position_id)
                if position:
                    return self._build_position_details(position, portfolio)

        return None

    def _build_position_details(self, position, portfolio) -> Dict[str, Any]:
        """Build full position details with calculated fields."""
        result = position.to_dict()

        # Add portfolio info
        result["portfolio_name"] = portfolio.name
        result["portfolio_type"] = portfolio.type

        # Add alert details if available
        if position.alert_id:
            alert = self.database.get_alert(position.alert_id)
            if alert:
                result["alert"] = alert

        # Add calculated fields
        result["duration_hours"] = None
        if position.entry_timestamp:
            from ..utils.helpers import now_utc
            delta = now_utc() - position.entry_timestamp
            result["duration_hours"] = round(delta.total_seconds() / 3600, 2)

        # Distance to SL
        if position.current_sl and position.current_price:
            result["distance_to_sl_pct"] = round(
                ((position.current_price - position.current_sl) / position.current_price) * 100, 2
            )

        # Max drawdown from highest
        if position.highest_price and position.current_price:
            result["drawdown_from_high_pct"] = round(
                ((position.highest_price - position.current_price) / position.highest_price) * 100, 2
            )

        # Max run-up from entry
        if position.entry_price and position.highest_price:
            result["max_runup_pct"] = round(
                ((position.highest_price - position.entry_price) / position.entry_price) * 100, 2
            )

        return result

    # ===== V5 WATCHLIST =====

    def get_watchlist(self) -> list:
        """Get V5 watchlist entries."""
        return [e.to_dict() for e in self.orchestrator.watchlist_manager.get_all_entries()]

    def get_active_watchlist(self) -> list:
        """Get active V5 watchlist entries."""
        return [e.to_dict() for e in self.orchestrator.watchlist_manager.get_active_entries()]

    def get_watchlist_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific watchlist entry."""
        entry = self.orchestrator.watchlist_manager.get_entry(entry_id)
        if entry:
            return entry.to_dict()
        return None

    def get_watchlist_stats(self) -> Dict[str, int]:
        """Get watchlist statistics."""
        return self.orchestrator.watchlist_manager.get_stats()


    # ===== IGNORED POSITIONS =====

    def get_ignored_positions(
        self,
        portfolio_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """
        Get ignored positions (positions skipped due to insufficient balance, etc.).

        Args:
            portfolio_id: Optional filter by portfolio
            status: Optional filter by status (TRACKING, WIN, LOSS)
            limit: Maximum number of results
        """
        return self.database.get_ignored_positions(portfolio_id, status, limit)

    def get_ignored_stats(self) -> Dict[str, Any]:
        """Get statistics for ignored positions."""
        return self.database.get_ignored_stats()

    def get_tracking_ignored(self) -> list:
        """Get all ignored positions that are still being tracked."""
        return self.database.get_tracking_ignored_positions()

    # ===== ALERTS =====

    def get_recent_alerts(self, limit: int = 100) -> list:
        """Get recent alerts."""
        return self.database.get_recent_alerts(limit)

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific alert."""
        return self.database.get_alert(alert_id)

    # ===== CONFIGURATION =====

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return self.orchestrator.settings.to_dict()

    def update_config(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update configuration.

        Args:
            config_data: New configuration data

        Returns:
            Updated configuration
        """
        # Parse and validate
        new_settings = Settings.from_dict(config_data)

        # Save to file
        save_config(new_settings)

        # Apply changes to running orchestrator (no restart required)
        self.orchestrator.apply_config_changes(new_settings)

        return new_settings.to_dict()

    def update_portfolio_config(
        self,
        portfolio_id: str,
        config_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a specific portfolio configuration.

        Args:
            portfolio_id: Portfolio ID
            config_data: New configuration data

        Returns:
            Updated portfolio configuration
        """
        portfolio = self.orchestrator.portfolios.get(portfolio_id)
        if not portfolio:
            return None

        # Update fields
        if "enabled" in config_data:
            portfolio.enabled = config_data["enabled"]
        if "initial_balance" in config_data:
            portfolio.initial_balance = config_data["initial_balance"]
        if "position_size_pct" in config_data:
            portfolio.position_size_pct = config_data["position_size_pct"]
        if "max_concurrent_trades" in config_data:
            portfolio.max_concurrent_trades = config_data["max_concurrent_trades"]

        # Save to database
        self.database.save_portfolio(portfolio.to_dict())

        return portfolio.to_dict()

    # ===== SIMULATION CONTROL =====

    async def start_simulation(self) -> Dict[str, Any]:
        """Start the simulation."""
        await self.orchestrator.start()
        return {"status": "started", "running": True}

    async def stop_simulation(self) -> Dict[str, Any]:
        """Stop the simulation."""
        await self.orchestrator.stop()
        return {"status": "stopped", "running": False}

    def get_simulation_status(self) -> Dict[str, Any]:
        """Get simulation status."""
        state = self.database.get_simulation_state()
        status = self.orchestrator.get_status()

        result = {
            "running": self.orchestrator._running,
            "live_mode": status.get("live_mode", {}),
            "backtest_mode": status.get("backtest_mode", {}),
            "status": state.get("status", "UNKNOWN"),
            "started_at": state.get("started_at"),
            "stopped_at": state.get("stopped_at"),
        }

        return result

    # ===== BACKTEST CONTROL =====

    async def start_backtest(self, days: int = 7, speed: float = 0.0) -> Dict[str, Any]:
        """
        Start backtest replay (runs in parallel with LIVE).

        Args:
            days: Number of days to replay
            speed: Replay speed (0 = instant)
        """
        return await self.orchestrator.start_backtest(days=days, speed=speed)

    async def stop_backtest(self) -> Dict[str, Any]:
        """Stop backtest replay."""
        return await self.orchestrator.stop_backtest()

    def get_backtest_status(self) -> Dict[str, Any]:
        """Get backtest progress and status."""
        return self.orchestrator.get_backtest_status()

    def get_backtest_results(self) -> Dict[str, Any]:
        """Get backtest results."""
        return self.orchestrator.get_backtest_results()

    def get_backtest_positions(self) -> list:
        """Get open positions from the backtest runner."""
        positions = []
        if self.orchestrator.backtest_runner:
            for portfolio in self.orchestrator.backtest_runner.portfolios.values():
                for pos in portfolio.open_positions:
                    pos_dict = pos.to_dict()
                    pos_dict["portfolio_name"] = portfolio.name
                    pos_dict["portfolio_type"] = portfolio.type
                    positions.append(pos_dict)
        return positions

    def reset_simulation(self) -> Dict[str, Any]:
        """Reset the simulation."""
        if self.orchestrator._running:
            return {"error": "Cannot reset while running", "success": False}

        self.orchestrator.reset()
        return {"status": "reset", "success": True}

    # ===== STATISTICS =====

    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        return self.database.get_stats()

    def get_comparison(self) -> Dict[str, Any]:
        """Get portfolio comparison data."""
        portfolios = []
        for portfolio in self.orchestrator.portfolios.values():
            portfolios.append({
                "id": portfolio.id,
                "name": portfolio.name,
                "type": portfolio.type,
                "balance": portfolio.total_balance,
                "return_pct": portfolio.return_pct,
                "win_rate": portfolio.stats.win_rate,
                "profit_factor": portfolio.stats.profit_factor,
                "total_trades": portfolio.stats.total_trades,
                "open_positions": portfolio.open_positions_count,
                "max_drawdown_pct": portfolio.stats.max_drawdown_pct,
            })

        # Sort by return
        portfolios.sort(key=lambda x: x["return_pct"], reverse=True)

        return {
            "portfolios": portfolios,
            "best_return": portfolios[0] if portfolios else None,
            "best_win_rate": max(portfolios, key=lambda x: x["win_rate"]) if portfolios else None,
            "most_trades": max(portfolios, key=lambda x: x["total_trades"]) if portfolios else None,
        }


def create_api_routes(orchestrator: SimulationOrchestrator) -> SimulationAPI:
    """
    Create API routes handler.

    Args:
        orchestrator: Simulation orchestrator

    Returns:
        SimulationAPI instance
    """
    return SimulationAPI(orchestrator)
