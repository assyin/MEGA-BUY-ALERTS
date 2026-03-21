"""
Client for fetching alerts from the MEGA BUY dashboard API.
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..utils.logger import get_logger
from ..utils.helpers import parse_datetime

logger = get_logger(__name__)


class AlertsClient:
    """
    Client for the MEGA BUY alerts API.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:9000",
        timeout: int = 30
    ):
        """
        Initialize alerts client.

        Args:
            base_url: Base URL of the dashboard API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_alerts(
        self,
        limit: int = 50,
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch alerts from the API.

        Args:
            limit: Maximum number of alerts to fetch
            since: Only fetch alerts after this timestamp

        Returns:
            List of alert dictionaries
        """
        try:
            session = await self._get_session()

            params = {"limit": limit}
            if since:
                params["since"] = since.isoformat()

            url = f"{self.base_url}/api/simulation/alerts"

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    alerts = data.get("alerts", data) if isinstance(data, dict) else data
                    return self._process_alerts(alerts)
                else:
                    logger.error(f"Failed to fetch alerts: HTTP {response.status}")
                    return []

        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching alerts: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []

    async def fetch_alert_with_decision(
        self,
        alert_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single alert with its ML decision.

        Args:
            alert_id: Alert ID

        Returns:
            Alert with decision data or None
        """
        try:
            session = await self._get_session()

            # Fetch alert
            url = f"{self.base_url}/api/alerts/{alert_id}"
            async with session.get(url) as response:
                if response.status != 200:
                    return None
                alert = await response.json()

            # Fetch decision
            decision_url = f"{self.base_url}/api/decisions/{alert_id}"
            async with session.get(decision_url) as response:
                if response.status == 200:
                    decision = await response.json()
                    alert["p_success"] = decision.get("p_success")
                    alert["confidence"] = decision.get("confidence")

            return self._process_alert(alert)

        except Exception as e:
            logger.error(f"Error fetching alert {alert_id}: {e}")
            return None

    async def fetch_strategies_data(self) -> Dict[str, Any]:
        """
        Fetch data from the strategies endpoint.

        Returns:
            Strategies data with alerts, decisions, and outcomes
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/strategies"

            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to fetch strategies: HTTP {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error fetching strategies: {e}")
            return {}

    def _process_alerts(self, alerts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process a list of alerts."""
        return [self._process_alert(a) for a in alerts if a]

    def _process_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and normalize an alert.

        Args:
            alert: Raw alert data

        Returns:
            Processed alert
        """
        # Ensure required fields
        processed = {
            "id": alert.get("id") or alert.get("alert_id"),
            "pair": alert.get("pair") or alert.get("symbol"),
            "price": float(alert.get("price", 0)),
            "alert_timestamp": alert.get("alert_timestamp") or alert.get("timestamp"),
            "timeframes": alert.get("timeframes", []),
            "scanner_score": alert.get("scanner_score", 0),
        }

        # ML data
        processed["p_success"] = alert.get("p_success")
        processed["confidence"] = alert.get("confidence")

        # Indicators
        processed["pp"] = alert.get("pp", False)
        processed["ec"] = alert.get("ec", False)
        processed["di_plus_4h"] = alert.get("di_plus_4h") or alert.get("diPlus4h", 0)
        processed["di_minus_4h"] = alert.get("di_minus_4h") or alert.get("diMinus4h", 0)
        processed["adx_4h"] = alert.get("adx_4h") or alert.get("adx4h", 0)

        # Volume - handle both vol_pct_max (direct) and vol_pct (dict) formats
        vol_pct_max = alert.get("vol_pct_max")
        if vol_pct_max is not None:
            processed["vol_pct_max"] = float(vol_pct_max)
        else:
            vol_pct = alert.get("vol_pct", {})
            if isinstance(vol_pct, dict):
                processed["vol_pct_max"] = max(vol_pct.values()) if vol_pct else 0
            else:
                processed["vol_pct_max"] = float(vol_pct) if vol_pct else 0

        # Additional indicators
        processed["choch"] = alert.get("choch", False)
        processed["zone"] = alert.get("zone", False)
        processed["lazy"] = alert.get("lazy", False)
        processed["vol"] = alert.get("vol", False)
        processed["st"] = alert.get("st", False)

        # Raw data for reference
        processed["raw_data"] = alert

        return processed

    async def fetch_alerts_for_period(
        self,
        days: int = 7,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical alerts for a given period (for BACKTEST mode).

        Args:
            days: Number of days to fetch
            limit: Maximum number of alerts

        Returns:
            List of alerts sorted by timestamp (oldest first)
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/simulation/alerts"

            # Fetch alerts (API returns newest first, we'll reverse)
            async with session.get(url, params={"limit": limit}) as response:
                if response.status == 200:
                    data = await response.json()
                    alerts = data.get("alerts", data) if isinstance(data, dict) else data
                    processed = self._process_alerts(alerts)

                    # Filter by date range
                    from datetime import datetime, timedelta
                    cutoff = datetime.utcnow() - timedelta(days=days)

                    filtered = []
                    for alert in processed:
                        ts = alert.get("alert_timestamp")
                        if ts:
                            try:
                                if isinstance(ts, str):
                                    alert_time = datetime.fromisoformat(ts.replace("Z", "+00:00").replace("+00:00", ""))
                                else:
                                    alert_time = ts
                                if alert_time >= cutoff:
                                    filtered.append(alert)
                            except Exception:
                                pass

                    # Sort oldest first for replay
                    filtered.sort(key=lambda x: x.get("alert_timestamp", ""))
                    logger.info(f"Fetched {len(filtered)} alerts for {days}-day backtest")
                    return filtered
                else:
                    logger.error(f"Failed to fetch alerts for backtest: HTTP {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching alerts for backtest: {e}")
            return []

    async def health_check(self) -> bool:
        """
        Check if the API is reachable.

        Returns:
            True if API is healthy
        """
        try:
            session = await self._get_session()
            url = f"{self.base_url}/api/simulation/alerts"

            async with session.get(url, params={"limit": 1}) as response:
                return response.status == 200

        except Exception:
            return False


# Synchronous wrapper for compatibility
class AlertsClientSync:
    """Synchronous wrapper for AlertsClient."""

    def __init__(self, base_url: str = "http://localhost:9000"):
        self.client = AlertsClient(base_url)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def fetch_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch alerts synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.fetch_alerts(limit))

    def health_check(self) -> bool:
        """Check API health synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.health_check())

    def close(self) -> None:
        """Close the client."""
        loop = self._get_loop()
        loop.run_until_complete(self.client.close())
