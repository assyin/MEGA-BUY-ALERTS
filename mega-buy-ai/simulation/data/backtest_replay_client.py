"""
Client for replaying alerts from backtest.db for BACKTEST mode.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.logger import get_logger

logger = get_logger(__name__)

# Default path to backtest database
DEFAULT_BACKTEST_DB = Path(__file__).parent.parent.parent / "backtest" / "data" / "backtest.db"


class BacktestReplayClient:
    """
    Client for replaying historical alerts from backtest.db.

    Used in BACKTEST mode to simulate trading on historical data.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize backtest replay client.

        Args:
            db_path: Path to backtest.db file
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_BACKTEST_DB

        if not self.db_path.exists():
            logger.warning(f"Backtest database not found at {self.db_path}")
        else:
            logger.info(f"BacktestReplayClient initialized with {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def fetch_alerts(
        self,
        limit: int = 100,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        pair: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch alerts from backtest.db.

        Args:
            limit: Maximum number of alerts to fetch
            since: Only fetch alerts after this timestamp
            until: Only fetch alerts before this timestamp
            pair: Filter by trading pair

        Returns:
            List of alert dictionaries
        """
        if not self.db_path.exists():
            logger.error(f"Backtest database not found: {self.db_path}")
            return []

        try:
            conn = self._get_connection()

            # Build query - join alerts with backtest_runs to get pair (symbol)
            query = """
                SELECT
                    a.id,
                    r.symbol as pair,
                    a.price_close as price,
                    a.alert_datetime as alert_timestamp,
                    a.combo_tfs as timeframes,
                    a.score as scanner_score,
                    a.adx_plus_di_4h as di_plus_4h,
                    a.adx_minus_di_4h as di_minus_4h,
                    a.adx_value_4h as adx_4h,
                    a.vol_ratio_4h as vol_pct_max,
                    a.v3_entry_found as has_entry,
                    a.v3_entry_price as entry_price,
                    a.v4_score,
                    a.v4_grade,
                    a.conditions
                FROM alerts a
                JOIN backtest_runs r ON a.backtest_run_id = r.id
                WHERE 1=1
            """
            params = []

            if since:
                query += " AND a.alert_datetime > ?"
                params.append(since.isoformat())

            if until:
                query += " AND a.alert_datetime <= ?"
                params.append(until.isoformat())

            if pair:
                query += " AND r.symbol = ?"
                params.append(pair)

            query += " ORDER BY a.alert_datetime ASC LIMIT ?"
            params.append(limit)

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            alerts = [self._process_alert(dict(row)) for row in rows]
            logger.debug(f"Fetched {len(alerts)} alerts from backtest.db")
            return alerts

        except sqlite3.Error as e:
            logger.error(f"Database error fetching alerts: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    def fetch_alerts_for_period(
        self,
        days: int = 7,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch alerts for a specific period.

        Args:
            days: Number of days to fetch
            end_date: End date (defaults to now)

        Returns:
            List of alert dictionaries
        """
        if end_date is None:
            end_date = datetime.utcnow()

        since = end_date - timedelta(days=days)

        return self.fetch_alerts(
            limit=10000,  # Get all alerts in period
            since=since,
            until=end_date
        )

    def get_alert_count(self) -> int:
        """Get total number of alerts in database."""
        if not self.db_path.exists():
            return 0

        try:
            conn = self._get_connection()
            count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def get_date_range(self) -> tuple:
        """Get min and max alert dates in database."""
        if not self.db_path.exists():
            return None, None

        try:
            conn = self._get_connection()
            row = conn.execute("""
                SELECT MIN(alert_datetime), MAX(alert_datetime)
                FROM alerts
            """).fetchone()
            conn.close()
            return row[0], row[1]
        except Exception as e:
            logger.error(f"Error getting date range: {e}")
            return None, None

    def _process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize an alert from backtest.db.

        Args:
            alert: Raw alert data from database

        Returns:
            Processed alert matching the expected format
        """
        import json

        # Parse timeframes from comma-separated string
        timeframes = alert.get("timeframes", "")
        if isinstance(timeframes, str) and timeframes:
            timeframes = [tf.strip() for tf in timeframes.split(",") if tf.strip()]
        elif not timeframes:
            timeframes = []

        # Parse conditions JSON if present
        conditions = alert.get("conditions", {})
        if isinstance(conditions, str):
            try:
                conditions = json.loads(conditions)
            except json.JSONDecodeError:
                conditions = {}

        processed = {
            "id": str(alert.get("id", "")),
            "pair": alert.get("pair", ""),
            "price": float(alert.get("price", 0) or 0),
            "alert_timestamp": alert.get("alert_timestamp"),
            "timeframes": timeframes,
            "scanner_score": alert.get("scanner_score", 0),

            # Indicators from backtest data
            "di_plus_4h": alert.get("di_plus_4h", 0) or 0,
            "di_minus_4h": alert.get("di_minus_4h", 0) or 0,
            "adx_4h": alert.get("adx_4h", 0) or 0,
            # vol_ratio_4h is often NULL in backtest.db, use conditions.Volume as fallback
            "vol_pct_max": (alert.get("vol_pct_max", 0) or 0) * 100 if alert.get("vol_pct_max") else (
                200.0 if (isinstance(conditions, dict) and conditions.get("Volume", False)) else 0
            ),

            # Get pp and ec from conditions - keys are PP_buy and Entry_Confirm
            "pp": conditions.get("PP_buy", False) if isinstance(conditions, dict) else False,
            "ec": conditions.get("Entry_Confirm", False) if isinstance(conditions, dict) else False,

            # V4 scoring (use as p_success proxy)
            "v4_score": alert.get("v4_score", 0),
            "v4_grade": alert.get("v4_grade", ""),
            "p_success": (alert.get("v4_score", 0) or 0) / 100.0,  # Normalize to 0-1

            # Entry info
            "has_entry": alert.get("has_entry", False),
            "entry_price": alert.get("entry_price"),

            # Mark as backtest
            "source": "BACKTEST",
        }

        return processed

    def health_check(self) -> bool:
        """Check if database is accessible."""
        return self.db_path.exists() and self.get_alert_count() > 0


class BacktestReplayIterator:
    """
    Iterator for replaying alerts chronologically with simulated time.
    """

    def __init__(
        self,
        client: BacktestReplayClient,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        speed_multiplier: float = 1.0
    ):
        """
        Initialize replay iterator.

        Args:
            client: BacktestReplayClient instance
            start_date: Start date for replay
            end_date: End date for replay
            speed_multiplier: Speed up factor (1.0 = real-time, 10.0 = 10x faster)
        """
        self.client = client
        self.start_date = start_date
        self.end_date = end_date
        self.speed_multiplier = speed_multiplier

        # Load all alerts for the period
        self.alerts = client.fetch_alerts(
            limit=10000,
            since=start_date,
            until=end_date
        )
        self.current_index = 0

        logger.info(
            f"BacktestReplayIterator: Loaded {len(self.alerts)} alerts "
            f"from {start_date} to {end_date}"
        )

    def __iter__(self):
        """Return iterator."""
        self.current_index = 0
        return self

    def __next__(self) -> Dict[str, Any]:
        """Get next alert."""
        if self.current_index >= len(self.alerts):
            raise StopIteration

        alert = self.alerts[self.current_index]
        self.current_index += 1
        return alert

    def __len__(self) -> int:
        """Get number of alerts."""
        return len(self.alerts)

    @property
    def progress(self) -> float:
        """Get replay progress (0.0 to 1.0)."""
        if len(self.alerts) == 0:
            return 1.0
        return self.current_index / len(self.alerts)

    @property
    def remaining(self) -> int:
        """Get number of remaining alerts."""
        return len(self.alerts) - self.current_index

    def reset(self) -> None:
        """Reset iterator to beginning."""
        self.current_index = 0
