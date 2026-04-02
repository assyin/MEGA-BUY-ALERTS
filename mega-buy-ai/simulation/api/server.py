"""
FastAPI Server for the Simulation Dashboard.

Provides REST API endpoints and WebSocket support.
"""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .routes import SimulationAPI
from ..main import SimulationOrchestrator
from ..utils.logger import get_logger

logger = get_logger(__name__)


if FASTAPI_AVAILABLE:
    from fastapi import Body

    # Pydantic models for request/response
    class ConfigUpdate(BaseModel):
        """Configuration update model (legacy - kept for compatibility)."""
        global_config: Optional[dict] = None
        exit_strategy: Optional[dict] = None
        portfolios: Optional[dict] = None

    class PortfolioUpdate(BaseModel):
        """Portfolio update model."""
        enabled: Optional[bool] = None
        initial_balance: Optional[float] = None
        position_size_pct: Optional[float] = None
        max_concurrent_trades: Optional[int] = None

    class BacktestStart(BaseModel):
        """Backtest start parameters."""
        days: int = 7
        speed: float = 0.0


def create_app(orchestrator: Optional[SimulationOrchestrator] = None) -> "FastAPI":
    """
    Create FastAPI application.

    Args:
        orchestrator: Simulation orchestrator (creates new if not provided)

    Returns:
        FastAPI application
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")

    # Create orchestrator if not provided
    if orchestrator is None:
        orchestrator = SimulationOrchestrator()

    api = SimulationAPI(orchestrator)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Lifespan context manager for startup/shutdown."""
        # Startup - launch LIVE simulation (alert capture + V5 monitoring)
        logger.info("Starting simulation API server...")
        await orchestrator.start()
        yield
        # Shutdown
        logger.info("Shutting down simulation API server...")
        await orchestrator.stop()

    app = FastAPI(
        title="MEGA BUY Simulation API",
        description="API for the MEGA BUY Live Simulation System",
        version="1.0.0",
        lifespan=lifespan
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== OVERVIEW =====

    @app.get("/api/overview")
    async def get_overview(mode: Optional[str] = Query(None, description="Filter by mode: LIVE, BACKTEST, or None for combined")):
        """Get simulation overview.

        Args:
            mode: LIVE, BACKTEST, or None for combined view
        """
        return api.get_overview(mode=mode)

    # ===== PORTFOLIOS =====

    @app.get("/api/portfolios")
    async def get_portfolios():
        """Get all portfolios."""
        return api.get_portfolios()

    @app.get("/api/portfolios/{portfolio_id}")
    async def get_portfolio(portfolio_id: str):
        """Get a specific portfolio."""
        portfolio = api.get_portfolio(portfolio_id)
        if not portfolio:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return portfolio

    @app.get("/api/portfolios/{portfolio_id}/history")
    async def get_portfolio_history(portfolio_id: str, limit: int = Query(1000)):
        """Get portfolio balance history."""
        return api.get_portfolio_history(portfolio_id, limit)

    @app.put("/api/portfolios/{portfolio_id}")
    async def update_portfolio(portfolio_id: str, update: PortfolioUpdate):
        """Update portfolio configuration."""
        result = api.update_portfolio_config(portfolio_id, update.dict(exclude_none=True))
        if not result:
            raise HTTPException(status_code=404, detail="Portfolio not found")
        return result

    # ===== POSITIONS =====

    @app.get("/api/positions")
    async def get_positions(
        portfolio_id: Optional[str] = Query(None),
        status: str = Query("open"),
        detailed: bool = Query(False),
        mode: Optional[str] = Query(None, description="Filter by mode: LIVE, BACKTEST, or None for all")
    ):
        """Get positions.

        Args:
            portfolio_id: Filter by portfolio
            status: "open" or "closed"
            detailed: If true, include full details for each position
            mode: Filter by mode: LIVE, BACKTEST, or None for all
        """
        if status == "open":
            return api.get_open_positions(portfolio_id, detailed=detailed, mode=mode)
        else:
            return api.get_closed_positions(portfolio_id)

    @app.get("/api/positions/{position_id}")
    async def get_position(position_id: str):
        """Get a specific position."""
        position = api.get_position(position_id)
        if not position:
            raise HTTPException(status_code=404, detail="Position not found")
        return position

    # ===== V5 WATCHLIST =====

    @app.get("/api/watchlist")
    async def get_watchlist(active_only: bool = Query(False)):
        """Get V5 watchlist."""
        if active_only:
            return api.get_active_watchlist()
        return api.get_watchlist()

    @app.get("/api/watchlist/stats")
    async def get_watchlist_stats():
        """Get watchlist statistics."""
        return api.get_watchlist_stats()

    @app.get("/api/watchlist/{entry_id}")
    async def get_watchlist_entry(entry_id: str):
        """Get a specific watchlist entry."""
        entry = api.get_watchlist_entry(entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        return entry


    # ===== IGNORED POSITIONS =====

    @app.get("/api/ignored")
    async def get_ignored_positions(
        portfolio_id: Optional[str] = Query(None),
        status: Optional[str] = Query(None, description="Filter by status: TRACKING, WIN, LOSS"),
        limit: int = Query(100)
    ):
        """
        Get ignored positions (skipped due to insufficient balance, max trades, etc.).

        These are positions that would have been opened but could not due to portfolio constraints.
        The system tracks them to show what was missed.
        """
        return api.get_ignored_positions(portfolio_id, status, limit)

    @app.get("/api/ignored/stats")
    async def get_ignored_stats():
        """
        Get statistics for ignored positions.

        Returns:
            - total: Total ignored positions
            - tracking: Currently tracking
            - winners: Theoretical wins
            - losers: Theoretical losses
            - total_theoretical_pnl: Total theoretical P&L
        """
        return api.get_ignored_stats()

    @app.get("/api/ignored/tracking")
    async def get_tracking_ignored():
        """Get all ignored positions that are still being tracked."""
        return api.get_tracking_ignored()

    # ===== ALERTS =====

    @app.get("/api/alerts")
    async def get_alerts(limit: int = Query(100)):
        """Get recent alerts."""
        return api.get_recent_alerts(limit)

    @app.get("/api/alerts/{alert_id}")
    async def get_alert(alert_id: str):
        """Get a specific alert."""
        alert = api.get_alert(alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        return alert

    # ===== CONFIGURATION =====

    @app.get("/api/config")
    async def get_config():
        """Get current configuration."""
        return api.get_config()

    @app.put("/api/config")
    async def update_config(config: dict = Body(...)):
        """Update configuration."""
        return api.update_config(config)

    # ===== SIMULATION CONTROL =====

    @app.get("/api/simulation/status")
    async def get_simulation_status():
        """Get simulation status."""
        return api.get_simulation_status()

    @app.post("/api/simulation/start")
    async def start_simulation():
        """Start the simulation."""
        return await api.start_simulation()

    @app.post("/api/simulation/stop")
    async def stop_simulation():
        """Stop the simulation."""
        return await api.stop_simulation()

    @app.post("/api/simulation/reset")
    async def reset_simulation():
        """Reset the simulation."""
        result = api.reset_simulation()
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result

    # ===== BACKTEST CONTROL =====

    @app.post("/api/backtest/start")
    async def start_backtest(params: BacktestStart):
        """Start backtest replay (runs in parallel with LIVE)."""
        return await api.start_backtest(days=params.days, speed=params.speed)

    @app.post("/api/backtest/stop")
    async def stop_backtest():
        """Stop backtest replay."""
        return await api.stop_backtest()

    @app.get("/api/backtest/status")
    async def get_backtest_status():
        """Get backtest progress and status."""
        return api.get_backtest_status()

    @app.get("/api/backtest/results")
    async def get_backtest_results():
        """Get backtest results."""
        return api.get_backtest_results()

    @app.get("/api/backtest/positions")
    async def get_backtest_positions():
        """Get open positions from backtest."""
        return api.get_backtest_positions()

    # ===== STATISTICS =====

    @app.get("/api/stats/database")
    async def get_database_stats():
        """Get database statistics."""
        return api.get_database_stats()

    @app.get("/api/stats/comparison")
    async def get_comparison():
        """Get portfolio comparison."""
        return api.get_comparison()

    # ===== WEBSOCKET =====

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket endpoint for real-time updates."""
        await websocket.accept()

        try:
            while True:
                # Send status updates every 5 seconds
                status = api.get_overview()
                await websocket.send_json({"type": "status", "data": status})
                await asyncio.sleep(5)

        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")

    return app


def run_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Run the API server.

    Args:
        host: Host to bind to
        port: Port to listen on
    """
    if not FASTAPI_AVAILABLE:
        print("FastAPI not installed. Run: pip install fastapi uvicorn")
        return

    import uvicorn

    orchestrator = SimulationOrchestrator()
    app = create_app(orchestrator)

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
