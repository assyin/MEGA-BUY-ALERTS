"""
Client for fetching price data from Binance API.
"""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.logger import get_logger

logger = get_logger(__name__)


class BinanceClient:
    """
    Client for Binance public API.
    """

    BASE_URL = "https://api.binance.com"

    def __init__(self, timeout: int = 30):
        """
        Initialize Binance client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._session: Optional[aiohttp.ClientSession] = None
        self._price_cache: Dict[str, float] = {}
        self._cache_time: Optional[datetime] = None
        self._cache_ttl = timedelta(seconds=5)

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def get_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")

        Returns:
            Current price or None
        """
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v3/ticker/price"

            async with session.get(url, params={"symbol": symbol}) as response:
                if response.status == 200:
                    data = await response.json()
                    return float(data["price"])
                else:
                    logger.warning(f"Failed to get price for {symbol}: HTTP {response.status}")
                    return None

        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return None

    async def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get current prices for multiple symbols.

        Args:
            symbols: List of trading pairs

        Returns:
            Dictionary of symbol -> price
        """
        # Check cache
        now = datetime.now()
        if self._cache_time and (now - self._cache_time) < self._cache_ttl:
            # Return cached prices for requested symbols
            return {s: self._price_cache.get(s, 0) for s in symbols if s in self._price_cache}

        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v3/ticker/price"

            # Fetch all prices (more efficient than individual requests)
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()

                    # Update cache
                    self._price_cache = {
                        item["symbol"]: float(item["price"])
                        for item in data
                    }
                    self._cache_time = now

                    # Return requested symbols
                    return {s: self._price_cache.get(s, 0) for s in symbols}
                else:
                    logger.warning(f"Failed to get prices: HTTP {response.status}")
                    return {}

        except Exception as e:
            logger.error(f"Error getting prices: {e}")
            return {}

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get OHLCV klines for a symbol.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            interval: Kline interval (1m, 5m, 15m, 30m, 1h, 4h, 1d)
            limit: Number of klines to fetch

        Returns:
            List of kline dictionaries
        """
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v3/klines"

            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_klines(data)
                else:
                    logger.warning(f"Failed to get klines for {symbol}: HTTP {response.status}")
                    return []

        except Exception as e:
            logger.error(f"Error getting klines for {symbol}: {e}")
            return []

    def _parse_klines(self, raw_klines: List[List]) -> List[Dict[str, Any]]:
        """
        Parse raw kline data into dictionaries.

        Args:
            raw_klines: Raw kline data from API

        Returns:
            List of parsed kline dictionaries
        """
        klines = []
        for k in raw_klines:
            klines.append({
                "open_time": k[0],
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "close_time": k[6],
                "quote_volume": float(k[7]),
                "trades": k[8],
                "taker_buy_volume": float(k[9]),
                "taker_buy_quote_volume": float(k[10]),
            })
        return klines

    async def get_multi_timeframe_klines(
        self,
        symbol: str,
        timeframes: Dict[str, int]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get klines for multiple timeframes.

        Args:
            symbol: Trading pair
            timeframes: Dict of interval -> limit (e.g., {"30m": 52, "1h": 100, "4h": 50})

        Returns:
            Dict of interval -> klines
        """
        results = {}

        # Fetch all timeframes concurrently
        tasks = [
            self.get_klines(symbol, interval, limit)
            for interval, limit in timeframes.items()
        ]

        klines_list = await asyncio.gather(*tasks)

        for interval, klines in zip(timeframes.keys(), klines_list):
            results[interval] = klines

        return results

    async def health_check(self) -> bool:
        """
        Check if Binance API is reachable.

        Returns:
            True if API is healthy
        """
        try:
            session = await self._get_session()
            url = f"{self.BASE_URL}/api/v3/ping"

            async with session.get(url) as response:
                return response.status == 200

        except Exception:
            return False


# Synchronous wrapper
class BinanceClientSync:
    """Synchronous wrapper for BinanceClient."""

    def __init__(self):
        self.client = BinanceClient()

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        """Get or create event loop."""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop

    def get_price(self, symbol: str) -> Optional[float]:
        """Get price synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.get_price(symbol))

    def get_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.get_prices(symbols))

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get klines synchronously."""
        loop = self._get_loop()
        return loop.run_until_complete(self.client.get_klines(symbol, interval, limit))

    def close(self) -> None:
        """Close the client."""
        loop = self._get_loop()
        loop.run_until_complete(self.client.close())
