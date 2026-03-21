"""
Database layer for the simulation system.
Uses SQLite for persistence.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..utils.helpers import now_utc, parse_datetime
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Database:
    """
    SQLite database manager for the simulation system.
    """

    def __init__(self, db_path: str = "data/simulation.db"):
        """
        Initialize database.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        schema = """
        -- Table des alertes capturées
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            pair TEXT NOT NULL,
            price REAL NOT NULL,
            alert_timestamp DATETIME NOT NULL,
            timeframes TEXT,
            scanner_score INTEGER,
            p_success REAL,
            confidence REAL,
            pp INTEGER,
            ec INTEGER,
            di_plus_4h REAL,
            di_minus_4h REAL,
            adx_4h REAL,
            vol_pct_max REAL,
            filter_max_wr INTEGER,
            filter_balanced INTEGER,
            filter_big_winners INTEGER,
            raw_data TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des portefeuilles
        CREATE TABLE IF NOT EXISTS portfolios (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            initial_balance REAL NOT NULL,
            current_balance REAL NOT NULL,
            cash_available REAL NOT NULL,
            position_size_pct REAL NOT NULL,
            max_concurrent_trades INTEGER NOT NULL,
            total_trades INTEGER DEFAULT 0,
            winners INTEGER DEFAULT 0,
            losers INTEGER DEFAULT 0,
            total_profit REAL DEFAULT 0,
            total_loss REAL DEFAULT 0,
            peak_balance REAL,
            max_drawdown REAL DEFAULT 0,
            max_drawdown_pct REAL DEFAULT 0,
            config_json TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Table des positions
        CREATE TABLE IF NOT EXISTS positions (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            alert_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            entry_price REAL NOT NULL,
            entry_timestamp DATETIME NOT NULL,
            allocated_capital REAL NOT NULL,
            current_price REAL,
            highest_price REAL,
            lowest_price REAL,
            initial_sl REAL NOT NULL,
            current_sl REAL NOT NULL,
            be_activated INTEGER DEFAULT 0,
            trailing_activated INTEGER DEFAULT 0,
            trailing_sl REAL,
            exit_price REAL,
            exit_timestamp DATETIME,
            exit_reason TEXT,
            final_pnl_pct REAL,
            final_pnl_usd REAL,
            status TEXT DEFAULT 'OPEN',
            mode TEXT DEFAULT 'LIVE',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
            FOREIGN KEY (alert_id) REFERENCES alerts(id)
        );

        -- Table watchlist V5
        CREATE TABLE IF NOT EXISTS v5_watchlist (
            id TEXT PRIMARY KEY,
            alert_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            alert_timestamp DATETIME NOT NULL,
            deadline DATETIME NOT NULL,
            trendline_price REAL,
            conditions_json TEXT,
            conditions_values_json TEXT,
            last_check DATETIME,
            check_count INTEGER DEFAULT 0,
            status TEXT DEFAULT 'WATCHING',
            entry_timestamp DATETIME,
            entry_price REAL,
            position_id TEXT,
            rejection_reason TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (alert_id) REFERENCES alerts(id),
            FOREIGN KEY (position_id) REFERENCES positions(id)
        );

        -- Table historique des balances
        CREATE TABLE IF NOT EXISTS balance_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            portfolio_id TEXT NOT NULL,
            balance REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
        );

        -- Table configuration
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        -- Table simulation state
        CREATE TABLE IF NOT EXISTS simulation_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT DEFAULT 'STOPPED',
            started_at DATETIME,
            stopped_at DATETIME,
            last_alert_id TEXT,
            last_price_update DATETIME,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );


        -- Table des positions ignorées (solde insuffisant, max trades, etc.)
        CREATE TABLE IF NOT EXISTS ignored_positions (
            id TEXT PRIMARY KEY,
            portfolio_id TEXT NOT NULL,
            alert_id TEXT NOT NULL,
            pair TEXT NOT NULL,
            ignore_reason TEXT NOT NULL,
            alert_price REAL NOT NULL,
            alert_timestamp DATETIME NOT NULL,
            required_capital REAL,
            available_capital REAL,
            current_price REAL,
            highest_price REAL,
            lowest_price REAL,
            theoretical_pnl_pct REAL,
            theoretical_pnl_usd REAL,
            theoretical_sl REAL,
            theoretical_status TEXT DEFAULT "TRACKING",
            theoretical_exit_price REAL,
            theoretical_exit_timestamp DATETIME,
            theoretical_exit_reason TEXT,
            mode TEXT DEFAULT "LIVE",
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
            FOREIGN KEY (alert_id) REFERENCES alerts(id)
        );

        -- Index pour performance
        CREATE INDEX IF NOT EXISTS idx_positions_portfolio ON positions(portfolio_id);
        CREATE INDEX IF NOT EXISTS idx_positions_status ON positions(status);
        CREATE INDEX IF NOT EXISTS idx_positions_pair ON positions(pair);
        CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(alert_timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_pair ON alerts(pair);
        CREATE INDEX IF NOT EXISTS idx_v5_watchlist_status ON v5_watchlist(status);
        CREATE INDEX IF NOT EXISTS idx_balance_history_portfolio ON balance_history(portfolio_id);
        CREATE INDEX IF NOT EXISTS idx_balance_history_timestamp ON balance_history(timestamp);
        CREATE INDEX IF NOT EXISTS idx_ignored_portfolio ON ignored_positions(portfolio_id);
        CREATE INDEX IF NOT EXISTS idx_ignored_status ON ignored_positions(theoretical_status);
        CREATE INDEX IF NOT EXISTS idx_ignored_pair ON ignored_positions(pair);
        """

        with self.get_connection() as conn:
            conn.executescript(schema)

        logger.info(f"Database initialized at {self.db_path}")

    # ===== ALERTS =====

    def save_alert(self, alert: Dict[str, Any]) -> None:
        """Save an alert to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO alerts (
                    id, pair, price, alert_timestamp, timeframes, scanner_score,
                    p_success, confidence, pp, ec, di_plus_4h, di_minus_4h,
                    adx_4h, vol_pct_max, filter_max_wr, filter_balanced,
                    filter_big_winners, raw_data, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.get("id"),
                alert.get("pair"),
                alert.get("price"),
                alert.get("alert_timestamp"),
                json.dumps(alert.get("timeframes", [])),
                alert.get("scanner_score"),
                alert.get("p_success"),
                alert.get("confidence"),
                1 if alert.get("pp") else 0,
                1 if alert.get("ec") else 0,
                alert.get("di_plus_4h"),
                alert.get("di_minus_4h"),
                alert.get("adx_4h"),
                alert.get("vol_pct_max"),
                1 if alert.get("filter_max_wr") else 0,
                1 if alert.get("filter_balanced") else 0,
                1 if alert.get("filter_big_winners") else 0,
                json.dumps(alert),
                now_utc().isoformat()
            ))

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Get an alert by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM alerts WHERE id = ?",
                (alert_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY alert_timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]

    def alert_exists(self, alert_id: str) -> bool:
        """Check if an alert exists."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM alerts WHERE id = ?",
                (alert_id,)
            ).fetchone()
            return row is not None

    # ===== PORTFOLIOS =====

    def save_portfolio(self, portfolio: Dict[str, Any]) -> None:
        """Save a portfolio to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO portfolios (
                    id, name, type, enabled, initial_balance, current_balance,
                    cash_available, position_size_pct, max_concurrent_trades,
                    total_trades, winners, losers, total_profit, total_loss,
                    peak_balance, max_drawdown, max_drawdown_pct, config_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio.get("id"),
                portfolio.get("name"),
                portfolio.get("type"),
                1 if portfolio.get("enabled") else 0,
                portfolio.get("initial_balance"),
                portfolio.get("current_balance", portfolio.get("initial_balance")),
                portfolio.get("cash_available", portfolio.get("initial_balance")),
                portfolio.get("position_size_pct"),
                portfolio.get("max_concurrent_trades"),
                portfolio.get("stats", {}).get("total_trades", 0),
                portfolio.get("stats", {}).get("winners", 0),
                portfolio.get("stats", {}).get("losers", 0),
                portfolio.get("stats", {}).get("total_profit", 0),
                portfolio.get("stats", {}).get("total_loss", 0),
                portfolio.get("stats", {}).get("peak_balance", portfolio.get("initial_balance")),
                portfolio.get("stats", {}).get("max_drawdown", 0),
                portfolio.get("stats", {}).get("max_drawdown_pct", 0),
                json.dumps(portfolio.get("config")),
                now_utc().isoformat()
            ))

    def get_portfolio(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        """Get a portfolio by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM portfolios WHERE id = ?",
                (portfolio_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    def get_all_portfolios(self) -> List[Dict[str, Any]]:
        """Get all portfolios."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM portfolios ORDER BY id"
            ).fetchall()
            return [dict(row) for row in rows]

    # ===== POSITIONS =====

    def save_position(self, position: Dict[str, Any]) -> None:
        """Save a position to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO positions (
                    id, portfolio_id, alert_id, pair, entry_price, entry_timestamp,
                    allocated_capital, current_price, highest_price, lowest_price,
                    initial_sl, current_sl, be_activated, trailing_activated,
                    trailing_sl, exit_price, exit_timestamp, exit_reason,
                    final_pnl_pct, final_pnl_usd, status, mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position.get("id"),
                position.get("portfolio_id"),
                position.get("alert_id"),
                position.get("pair"),
                position.get("entry_price"),
                position.get("entry_timestamp"),
                position.get("allocated_capital"),
                position.get("current_price"),
                position.get("highest_price"),
                position.get("lowest_price"),
                position.get("initial_sl"),
                position.get("current_sl"),
                1 if position.get("be_activated") else 0,
                1 if position.get("trailing_activated") else 0,
                position.get("trailing_sl"),
                position.get("exit_price"),
                position.get("exit_timestamp"),
                position.get("exit_reason"),
                position.get("final_pnl_pct"),
                position.get("final_pnl_usd"),
                position.get("status", "OPEN"),
                position.get("mode", "LIVE"),
                now_utc().isoformat()
            ))

    def get_open_positions(self, portfolio_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get open positions, optionally filtered by portfolio."""
        with self.get_connection() as conn:
            if portfolio_id:
                rows = conn.execute(
                    "SELECT * FROM positions WHERE status = 'OPEN' AND portfolio_id = ?",
                    (portfolio_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM positions WHERE status = 'OPEN'"
                ).fetchall()
            return [dict(row) for row in rows]

    def get_closed_positions(
        self,
        portfolio_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get closed positions."""
        with self.get_connection() as conn:
            if portfolio_id:
                rows = conn.execute(
                    """SELECT * FROM positions
                    WHERE status = 'CLOSED' AND portfolio_id = ?
                    ORDER BY exit_timestamp DESC LIMIT ?""",
                    (portfolio_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT * FROM positions
                    WHERE status = 'CLOSED'
                    ORDER BY exit_timestamp DESC LIMIT ?""",
                    (limit,)
                ).fetchall()
            return [dict(row) for row in rows]

    # ===== V5 WATCHLIST =====

    def save_watchlist_entry(self, entry: Dict[str, Any]) -> None:
        """Save a V5 watchlist entry."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO v5_watchlist (
                    id, alert_id, pair, alert_timestamp, deadline, trendline_price,
                    conditions_json, conditions_values_json, last_check, check_count,
                    status, entry_timestamp, entry_price, position_id, rejection_reason,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.get("id"),
                entry.get("alert_id"),
                entry.get("pair"),
                entry.get("alert_timestamp"),
                entry.get("deadline"),
                entry.get("trendline_price"),
                json.dumps(entry.get("conditions", {})),
                json.dumps(entry.get("conditions_values", {})),
                entry.get("last_check"),
                entry.get("check_count", 0),
                entry.get("status", "WATCHING"),
                entry.get("entry_timestamp"),
                entry.get("entry_price"),
                entry.get("position_id"),
                entry.get("rejection_reason"),
                now_utc().isoformat()
            ))

    def get_active_watchlist(self) -> List[Dict[str, Any]]:
        """Get active V5 watchlist entries."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM v5_watchlist WHERE status = 'WATCHING' ORDER BY deadline"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_watchlist_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get a watchlist entry by ID."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM v5_watchlist WHERE id = ?",
                (entry_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None

    # ===== BALANCE HISTORY =====

    def save_balance_snapshot(self, portfolio_id: str, balance: float) -> None:
        """Save a balance snapshot."""
        with self.get_connection() as conn:
            conn.execute(
                "INSERT INTO balance_history (portfolio_id, balance) VALUES (?, ?)",
                (portfolio_id, balance)
            )

    def get_balance_history(
        self,
        portfolio_id: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get balance history for a portfolio."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM balance_history
                WHERE portfolio_id = ?
                ORDER BY timestamp DESC LIMIT ?""",
                (portfolio_id, limit)
            ).fetchall()
            return [dict(row) for row in rows]

    # ===== SIMULATION STATE =====

    def get_simulation_state(self) -> Dict[str, Any]:
        """Get simulation state."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM simulation_state WHERE id = 1"
            ).fetchone()
            if row:
                return dict(row)
            # Create initial state
            conn.execute(
                "INSERT INTO simulation_state (id, status) VALUES (1, 'STOPPED')"
            )
            return {"id": 1, "status": "STOPPED"}

    def update_simulation_state(self, state: Dict[str, Any]) -> None:
        """Update simulation state."""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE simulation_state SET
                    status = ?,
                    started_at = ?,
                    stopped_at = ?,
                    last_alert_id = ?,
                    last_price_update = ?,
                    updated_at = ?
                WHERE id = 1
            """, (
                state.get("status"),
                state.get("started_at"),
                state.get("stopped_at"),
                state.get("last_alert_id"),
                state.get("last_price_update"),
                now_utc().isoformat()
            ))

    # ===== IGNORED POSITIONS =====

    def save_ignored_position(self, ignored: Dict[str, Any]) -> None:
        """Save an ignored position to database."""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO ignored_positions (
                    id, portfolio_id, alert_id, pair, ignore_reason, alert_price,
                    alert_timestamp, required_capital, available_capital,
                    current_price, highest_price, lowest_price,
                    theoretical_pnl_pct, theoretical_pnl_usd, theoretical_sl,
                    theoretical_status, theoretical_exit_price, theoretical_exit_timestamp,
                    theoretical_exit_reason, mode, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ignored.get("id"),
                ignored.get("portfolio_id"),
                ignored.get("alert_id"),
                ignored.get("pair"),
                ignored.get("ignore_reason"),
                ignored.get("alert_price"),
                ignored.get("alert_timestamp"),
                ignored.get("required_capital"),
                ignored.get("available_capital"),
                ignored.get("current_price"),
                ignored.get("highest_price"),
                ignored.get("lowest_price"),
                ignored.get("theoretical_pnl_pct"),
                ignored.get("theoretical_pnl_usd"),
                ignored.get("theoretical_sl"),
                ignored.get("theoretical_status", "TRACKING"),
                ignored.get("theoretical_exit_price"),
                ignored.get("theoretical_exit_timestamp"),
                ignored.get("theoretical_exit_reason"),
                ignored.get("mode", "LIVE"),
                now_utc().isoformat()
            ))

    def get_ignored_positions(
        self,
        portfolio_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get ignored positions."""
        with self.get_connection() as conn:
            query = "SELECT * FROM ignored_positions WHERE 1=1"
            params = []

            if portfolio_id:
                query += " AND portfolio_id = ?"
                params.append(portfolio_id)

            if status:
                query += " AND theoretical_status = ?"
                params.append(status)

            query += " ORDER BY alert_timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_tracking_ignored_positions(self) -> List[Dict[str, Any]]:
        """Get all ignored positions that are still being tracked."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ignored_positions WHERE theoretical_status = 'TRACKING'"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_ignored_stats(self) -> Dict[str, Any]:
        """Get statistics for ignored positions."""
        with self.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM ignored_positions").fetchone()[0]
            tracking = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'TRACKING'"
            ).fetchone()[0]
            winners = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'WIN'"
            ).fetchone()[0]
            losers = conn.execute(
                "SELECT COUNT(*) FROM ignored_positions WHERE theoretical_status = 'LOSS'"
            ).fetchone()[0]

            # Calculate total theoretical P&L
            pnl_result = conn.execute(
                "SELECT SUM(theoretical_pnl_usd) FROM ignored_positions WHERE theoretical_status IN ('WIN', 'LOSS')"
            ).fetchone()[0] or 0

            return {
                "total": total,
                "tracking": tracking,
                "winners": winners,
                "losers": losers,
                "total_theoretical_pnl": pnl_result
            }


    # ===== UTILITIES =====

    def clear_all_data(self) -> None:
        """Clear all data (for reset)."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM balance_history")
            conn.execute("DELETE FROM v5_watchlist")
            conn.execute("DELETE FROM positions")
            conn.execute("DELETE FROM portfolios")
            conn.execute("DELETE FROM alerts")
            conn.execute("DELETE FROM simulation_state")
        logger.info("All data cleared from database")

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        with self.get_connection() as conn:
            return {
                "alerts": conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0],
                "portfolios": conn.execute("SELECT COUNT(*) FROM portfolios").fetchone()[0],
                "positions_open": conn.execute(
                    "SELECT COUNT(*) FROM positions WHERE status = 'OPEN'"
                ).fetchone()[0],
                "positions_closed": conn.execute(
                    "SELECT COUNT(*) FROM positions WHERE status = 'CLOSED'"
                ).fetchone()[0],
                "watchlist": conn.execute(
                    "SELECT COUNT(*) FROM v5_watchlist WHERE status = 'WATCHING'"
                ).fetchone()[0],
            }
