"""
Alert Capture Service.

Captures MEGA BUY alerts from the dashboard API,
enriches them with filter calculations, and distributes to portfolios.
"""

import asyncio
from typing import List, Dict, Any, Set, Optional, Callable
from datetime import datetime

from ..data.alerts_client import AlertsClient
from ..data.database import Database
from ..utils.logger import get_logger
from ..utils.helpers import now_utc

logger = get_logger(__name__)


class AlertCapture:
    """
    Service for capturing and processing MEGA BUY alerts.
    """

    def __init__(
        self,
        alerts_client: AlertsClient,
        database: Database,
        on_alert_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize alert capture service.

        Args:
            alerts_client: Client for fetching alerts
            database: Database for persistence
            on_alert_callback: Callback function when new alert is captured
        """
        self.alerts_client = alerts_client
        self.database = database
        self.on_alert_callback = on_alert_callback

        self._seen_alert_ids: Set[str] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, polling_interval: int = 30) -> None:
        """
        Start the alert capture service.

        Args:
            polling_interval: Seconds between API polls
        """
        if self._running:
            logger.warning("Alert capture already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop(polling_interval))
        logger.info(f"Alert capture started (polling every {polling_interval}s)")

    async def stop(self) -> None:
        """Stop the alert capture service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Alert capture stopped")

    async def _poll_loop(self, interval: int) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._fetch_and_process_alerts()
            except Exception as e:
                logger.error(f"Error in alert poll loop: {e}")

            await asyncio.sleep(interval)

    async def _fetch_and_process_alerts(self) -> None:
        """Fetch and process new alerts."""
        alerts = await self.alerts_client.fetch_alerts(limit=50)

        for alert in alerts:
            alert_id = alert.get("id")
            if not alert_id:
                continue

            # Skip already seen alerts
            if alert_id in self._seen_alert_ids:
                continue

            # Skip if already in database
            if self.database.alert_exists(alert_id):
                self._seen_alert_ids.add(alert_id)
                continue

            # Process new alert
            await self._process_new_alert(alert)

    async def _process_new_alert(self, alert: Dict[str, Any]) -> None:
        """
        Process a new alert.

        Args:
            alert: Alert data
        """
        alert_id = alert["id"]

        # Calculate empirical filters
        alert = self._calculate_filters(alert)

        # Save to database
        self.database.save_alert(alert)

        # Mark as seen
        self._seen_alert_ids.add(alert_id)

        # Log
        logger.info(
            f"New alert captured: {alert['pair']} @ {alert['price']:.4f} "
            f"(MaxWR={alert.get('filter_max_wr')}, Bal={alert.get('filter_balanced')}, "
            f"BigWin={alert.get('filter_big_winners')}, p={alert.get('p_success', 'N/A')})"
        )

        # Callback
        if self.on_alert_callback:
            try:
                self.on_alert_callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")

    def _calculate_filters(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate empirical filters for an alert.

        Filters:
        - filter_max_wr: PP + EC + DI- >= 22 + DI+ <= 25 + ADX >= 35 + Vol >= 100%
        - filter_balanced: PP + EC + DI- >= 22 + DI+ <= 20 + ADX >= 21 + Vol >= 100%
        - filter_big_winners: PP + EC + DI- >= 22 + DI+ <= 25 + ADX >= 21 + Vol >= 100%

        Args:
            alert: Alert data

        Returns:
            Alert with filter flags added
        """
        pp = alert.get("pp", False)
        ec = alert.get("ec", False)
        di_plus = alert.get("di_plus_4h", 0) or 0
        di_minus = alert.get("di_minus_4h", 0) or 0
        adx = alert.get("adx_4h", 0) or 0
        vol = alert.get("vol_pct_max", 0) or 0

        # Max Win Rate filter (82% WR)
        alert["filter_max_wr"] = (
            pp and ec and
            di_minus >= 22 and di_plus <= 25 and
            adx >= 35 and vol >= 100
        )

        # Balanced filter (73% WR)
        alert["filter_balanced"] = (
            pp and ec and
            di_minus >= 22 and di_plus <= 20 and
            adx >= 21 and vol >= 100
        )

        # Big Winners filter (71% WR)
        alert["filter_big_winners"] = (
            pp and ec and
            di_minus >= 22 and di_plus <= 25 and
            adx >= 21 and vol >= 100
        )

        return alert

    def process_alert_sync(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an alert synchronously (for manual testing).

        Args:
            alert: Alert data

        Returns:
            Processed alert with filters
        """
        return self._calculate_filters(alert)

    def get_seen_count(self) -> int:
        """Get count of seen alerts."""
        return len(self._seen_alert_ids)

    def clear_seen(self) -> None:
        """Clear seen alerts cache."""
        self._seen_alert_ids.clear()


class AlertCaptureSync:
    """Synchronous wrapper for AlertCapture."""

    def __init__(self, base_url: str = "http://localhost:9000", db_path: str = "data/simulation.db"):
        from ..data.alerts_client import AlertsClientSync
        self.alerts_client = AlertsClientSync(base_url)
        self.database = Database(db_path)
        self._seen_alert_ids: Set[str] = set()

    def fetch_new_alerts(self) -> List[Dict[str, Any]]:
        """Fetch and process new alerts."""
        alerts = self.alerts_client.fetch_alerts(limit=50)
        new_alerts = []

        for alert in alerts:
            alert_id = alert.get("id")
            if not alert_id or alert_id in self._seen_alert_ids:
                continue

            if self.database.alert_exists(alert_id):
                self._seen_alert_ids.add(alert_id)
                continue

            # Calculate filters
            alert = self._calculate_filters(alert)

            # Save to database
            self.database.save_alert(alert)

            # Mark as seen
            self._seen_alert_ids.add(alert_id)
            new_alerts.append(alert)

        return new_alerts

    def _calculate_filters(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate empirical filters."""
        pp = alert.get("pp", False)
        ec = alert.get("ec", False)
        di_plus = alert.get("di_plus_4h", 0) or 0
        di_minus = alert.get("di_minus_4h", 0) or 0
        adx = alert.get("adx_4h", 0) or 0
        vol = alert.get("vol_pct_max", 0) or 0

        alert["filter_max_wr"] = (
            pp and ec and di_minus >= 22 and di_plus <= 25 and adx >= 35 and vol >= 100
        )
        alert["filter_balanced"] = (
            pp and ec and di_minus >= 22 and di_plus <= 20 and adx >= 21 and vol >= 100
        )
        alert["filter_big_winners"] = (
            pp and ec and di_minus >= 22 and di_plus <= 25 and adx >= 21 and vol >= 100
        )

        return alert

    def close(self) -> None:
        """Close resources."""
        self.alerts_client.close()
