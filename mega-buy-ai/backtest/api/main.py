#!/usr/bin/env python3
"""
MEGA BUY Backtest API
FastAPI backend for backtest dashboard
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import (
    BacktestRun, Alert, Trade,
    SessionLocal, init_db
)
from engine import BacktestEngine, DEFAULT_CONFIG

# Initialize database
init_db()

app = FastAPI(
    title="MEGA BUY Backtest API",
    description="API for running and viewing backtests",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    config: Optional[Dict[str, Any]] = None
    strategy_version: Optional[str] = 'v1'  # v1, v2, v3, or v4 (optimized)


class BacktestRunResponse(BaseModel):
    id: int
    symbol: str
    start_date: datetime
    end_date: datetime
    created_at: datetime
    strategy_version: Optional[str] = 'v1'
    total_alerts: int
    stc_validated: int
    rejected_15m_alone: int
    rejected_pp_buy: int
    valid_combos: int
    with_tl_break: int
    delay_respected: int
    delay_exceeded: int
    expired: int
    waiting: int
    valid_entries: int
    no_entry: int
    total_trades: int
    pnl_strategy_c: float
    pnl_strategy_d: float
    avg_pnl_c: float
    avg_pnl_d: float

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: int
    alert_datetime: datetime
    timeframe: str
    price_close: float
    score: int
    stc_validated: bool
    stc_valid_tfs: Optional[str]
    is_15m_alone: bool
    combo_tfs: Optional[str]
    has_trendline: bool
    tl_type: Optional[str]
    has_tl_break: bool
    tl_break_datetime: Optional[datetime]
    tl_break_delay_hours: Optional[float]
    tl_retest_count: Optional[int] = 0
    tl_prior_false_breaks: Optional[int] = 0
    delay_exceeded: bool
    has_entry: bool
    entry_datetime: Optional[datetime]
    entry_price: Optional[float]
    entry_diff_vs_alert: Optional[float]
    status: str
    # Fibonacci bonus
    fib_bonus: Optional[bool] = False
    fib_level: Optional[float] = None
    fib_price: Optional[float] = None
    # V3 Golden Box Retest fields
    v3_entry_found: Optional[bool] = None
    v3_entry_datetime: Optional[datetime] = None
    v3_entry_price: Optional[float] = None
    v3_sl_price: Optional[float] = None
    v3_box_high: Optional[float] = None
    v3_box_low: Optional[float] = None
    v3_box_range_pct: Optional[float] = None
    v3_hours_to_entry: Optional[float] = None
    v3_sl_distance_pct: Optional[float] = None
    v3_quality_score: Optional[int] = None
    v3_rejected: Optional[bool] = None
    v3_rejection_reason: Optional[str] = None
    # Foreign Candle Order Block
    fc_ob_1h_found: Optional[bool] = False
    fc_ob_1h_count: Optional[int] = None
    fc_ob_1h_type: Optional[str] = None
    fc_ob_1h_zone_high: Optional[float] = None
    fc_ob_1h_zone_low: Optional[float] = None
    fc_ob_1h_strength: Optional[int] = None
    fc_ob_1h_retest: Optional[bool] = False
    fc_ob_1h_distance_pct: Optional[float] = None
    fc_ob_1h_datetime: Optional[datetime] = None
    fc_ob_1h_in_zone: Optional[int] = 0
    fc_ob_1h_retested: Optional[int] = 0
    fc_ob_4h_found: Optional[bool] = False
    fc_ob_4h_count: Optional[int] = None
    fc_ob_4h_type: Optional[str] = None
    fc_ob_4h_zone_high: Optional[float] = None
    fc_ob_4h_zone_low: Optional[float] = None
    fc_ob_4h_strength: Optional[int] = None
    fc_ob_4h_retest: Optional[bool] = False
    fc_ob_4h_distance_pct: Optional[float] = None
    fc_ob_4h_datetime: Optional[datetime] = None
    fc_ob_4h_in_zone: Optional[int] = 0
    fc_ob_4h_retested: Optional[int] = 0
    fc_ob_bonus: Optional[bool] = False
    fc_ob_score: Optional[int] = None
    fc_ob_label: Optional[str] = None
    # Volume Profile Analysis
    vp_bonus: Optional[bool] = False
    vp_score: Optional[int] = None
    vp_grade: Optional[str] = None
    vp_poc_1h: Optional[float] = None
    vp_vah_1h: Optional[float] = None
    vp_val_1h: Optional[float] = None
    vp_hvn_levels_1h: Optional[List[float]] = None
    vp_lvn_levels_1h: Optional[List[float]] = None
    vp_total_volume_1h: Optional[float] = None
    vp_poc_4h: Optional[float] = None
    vp_vah_4h: Optional[float] = None
    vp_val_4h: Optional[float] = None
    vp_hvn_levels_4h: Optional[List[float]] = None
    vp_lvn_levels_4h: Optional[List[float]] = None
    vp_total_volume_4h: Optional[float] = None
    vp_entry_position_1h: Optional[str] = None
    vp_entry_position_4h: Optional[str] = None
    vp_entry_vs_poc_pct_1h: Optional[float] = None
    vp_entry_vs_poc_pct_4h: Optional[float] = None
    vp_sl_near_hvn: Optional[bool] = False
    vp_sl_hvn_level: Optional[float] = None
    vp_sl_hvn_distance_pct: Optional[float] = None
    vp_sl_optimized: Optional[float] = None
    vp_naked_poc_1h: Optional[bool] = False
    vp_naked_poc_level_1h: Optional[float] = None
    vp_naked_poc_4h: Optional[bool] = False
    vp_naked_poc_level_4h: Optional[float] = None
    vp_label: Optional[str] = None
    vp_recommendation: Optional[str] = None
    vp_details: Optional[Dict[str, Any]] = None

    # VP Retest Detection
    vp_val_retested: Optional[bool] = False
    vp_val_retest_rejected: Optional[bool] = False
    vp_val_retest_dt: Optional[str] = None
    vp_poc_retested: Optional[bool] = False
    vp_poc_retest_rejected: Optional[bool] = False
    vp_poc_retest_dt: Optional[str] = None
    vp_vah_retested: Optional[bool] = False
    vp_hvn_retested: Optional[bool] = False
    vp_hvn_retest_level: Optional[float] = None
    vp_ob_confluence: Optional[bool] = False
    vp_ob_confluence_tf: Optional[str] = None
    vp_pullback_completed: Optional[bool] = False
    vp_pullback_level: Optional[str] = None
    vp_pullback_quality: Optional[str] = None

    # V6 Advanced Scoring Strategy
    v6_rejected: Optional[bool] = False
    v6_rejection_reason: Optional[str] = None
    v6_score: Optional[int] = None
    v6_grade: Optional[str] = None
    v6_retest_hours: Optional[float] = None
    v6_entry_hours: Optional[float] = None
    v6_distance_pct: Optional[float] = None
    v6_rsi_at_entry: Optional[float] = None
    v6_adx_at_entry: Optional[float] = None
    v6_potential_pct: Optional[float] = None
    v6_has_cvd_divergence: Optional[bool] = False
    v6_timing_adj: Optional[int] = None
    v6_momentum_adj: Optional[int] = None

    # MEGA BUY Full Details (DMI Moves, RSI Moves, Volume %, LazyBar, EC RSI per TF)
    mega_buy_details: Optional[Dict[str, Any]] = None

    # Convert datetime to string for retest datetime fields
    @field_validator('vp_val_retest_dt', 'vp_poc_retest_dt', mode='before')
    @classmethod
    def convert_datetime_to_str(cls, v):
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return v

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: int
    alert_datetime: datetime
    timeframe: str
    alert_price: float
    entry_datetime: datetime
    entry_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    highest_price: float
    trailing_active: bool
    exit_datetime_c: Optional[datetime]
    exit_price_c: float
    exit_reason_c: str
    pnl_c: float
    tp1_hit: bool
    tp2_hit: bool
    exit_datetime_d: Optional[datetime]
    exit_price_d: float
    exit_reason_d: str
    pnl_d: float

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_backtests: int
    total_symbols: int
    total_trades: int
    total_pnl_c: float
    total_pnl_d: float
    avg_pnl_c: float
    avg_pnl_d: float
    win_rate_c: float
    win_rate_d: float


# Background task status
backtest_status = {}


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/")
async def root():
    """Serve dashboard"""
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "MEGA BUY Backtest API", "docs": "/docs"}


@app.get("/api/config")
async def get_default_config():
    """Get default configuration"""
    return DEFAULT_CONFIG


@app.get("/api/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get overall dashboard statistics"""
    db = SessionLocal()
    try:
        runs = db.query(BacktestRun).all()

        if not runs:
            return DashboardStats(
                total_backtests=0,
                total_symbols=0,
                total_trades=0,
                total_pnl_c=0,
                total_pnl_d=0,
                avg_pnl_c=0,
                avg_pnl_d=0,
                win_rate_c=0,
                win_rate_d=0
            )

        symbols = set(r.symbol for r in runs)
        total_trades = sum(r.total_trades for r in runs)
        total_pnl_c = sum(r.pnl_strategy_c for r in runs)
        total_pnl_d = sum(r.pnl_strategy_d for r in runs)

        # Calculate win rates
        trades = db.query(Trade).all()
        wins_c = sum(1 for t in trades if t.pnl_c > 0)
        wins_d = sum(1 for t in trades if t.pnl_d > 0)
        win_rate_c = (wins_c / len(trades) * 100) if trades else 0
        win_rate_d = (wins_d / len(trades) * 100) if trades else 0

        return DashboardStats(
            total_backtests=len(runs),
            total_symbols=len(symbols),
            total_trades=total_trades,
            total_pnl_c=total_pnl_c,
            total_pnl_d=total_pnl_d,
            avg_pnl_c=total_pnl_c / total_trades if total_trades > 0 else 0,
            avg_pnl_d=total_pnl_d / total_trades if total_trades > 0 else 0,
            win_rate_c=win_rate_c,
            win_rate_d=win_rate_d
        )
    finally:
        db.close()


@app.get("/api/backtests", response_model=List[BacktestRunResponse])
async def list_backtests():
    """List all backtest runs"""
    db = SessionLocal()
    try:
        runs = db.query(BacktestRun).order_by(BacktestRun.created_at.desc()).all()
        return runs
    finally:
        db.close()


@app.get("/api/backtests/{backtest_id}", response_model=BacktestRunResponse)
async def get_backtest(backtest_id: int):
    """Get a specific backtest run"""
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        return run
    finally:
        db.close()


@app.get("/api/backtests/{backtest_id}/alerts", response_model=List[AlertResponse])
async def get_backtest_alerts(backtest_id: int):
    """Get all alerts for a backtest"""
    db = SessionLocal()
    try:
        alerts = db.query(Alert).filter(Alert.backtest_run_id == backtest_id).order_by(Alert.alert_datetime).all()
        return alerts
    finally:
        db.close()


@app.get("/api/backtests/{backtest_id}/trades", response_model=List[TradeResponse])
async def get_backtest_trades(backtest_id: int):
    """Get all trades for a backtest"""
    db = SessionLocal()
    try:
        trades = db.query(Trade).filter(Trade.backtest_run_id == backtest_id).order_by(Trade.alert_datetime).all()
        return trades
    finally:
        db.close()


@app.delete("/api/backtests/{backtest_id}")
async def delete_backtest(backtest_id: int):
    """Delete a backtest run"""
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == backtest_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Backtest not found")
        db.delete(run)
        db.commit()
        return {"message": "Backtest deleted successfully"}
    finally:
        db.close()


def run_backtest_task(task_id: str, symbol: str, start_date: str, end_date: str, config: dict, strategy_version: str = 'v1'):
    """Background task for running backtest"""
    try:
        backtest_status[task_id] = {"status": "running", "progress": "Starting..."}
        engine = BacktestEngine(config)

        def progress_callback(msg):
            backtest_status[task_id]["progress"] = msg

        run_id = engine.run_backtest(symbol, start_date, end_date, progress_callback, strategy_version=strategy_version)
        backtest_status[task_id] = {
            "status": "completed",
            "progress": "Completed",
            "backtest_id": run_id
        }
    except Exception as e:
        backtest_status[task_id] = {
            "status": "error",
            "progress": str(e)
        }


@app.post("/api/backtests")
async def create_backtest(request: BacktestRequest, background_tasks: BackgroundTasks):
    """Start a new backtest"""
    task_id = f"{request.symbol}_{datetime.now().timestamp()}"
    config = request.config or DEFAULT_CONFIG.copy()
    strategy_version = request.strategy_version or 'v1'

    background_tasks.add_task(
        run_backtest_task,
        task_id,
        request.symbol,
        request.start_date,
        request.end_date,
        config,
        strategy_version
    )

    backtest_status[task_id] = {"status": "queued", "progress": "Queued"}

    return {"task_id": task_id, "message": "Backtest started"}


@app.get("/api/backtests/status/{task_id}")
async def get_backtest_status(task_id: str):
    """Get status of a running backtest"""
    if task_id not in backtest_status:
        raise HTTPException(status_code=404, detail="Task not found")
    return backtest_status[task_id]


@app.get("/api/symbols")
async def list_symbols():
    """List all symbols with backtests"""
    db = SessionLocal()
    try:
        runs = db.query(BacktestRun).all()
        symbols = {}
        for run in runs:
            if run.symbol not in symbols:
                symbols[run.symbol] = {
                    "symbol": run.symbol,
                    "backtest_count": 0,
                    "total_trades": 0,
                    "total_pnl_c": 0,
                    "total_pnl_d": 0,
                    "last_backtest": None
                }
            symbols[run.symbol]["backtest_count"] += 1
            symbols[run.symbol]["total_trades"] += run.total_trades
            symbols[run.symbol]["total_pnl_c"] += run.pnl_strategy_c
            symbols[run.symbol]["total_pnl_d"] += run.pnl_strategy_d
            if symbols[run.symbol]["last_backtest"] is None or run.created_at > symbols[run.symbol]["last_backtest"]:
                symbols[run.symbol]["last_backtest"] = run.created_at

        return list(symbols.values())
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9001)
