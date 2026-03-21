"""
Price Monitor Service.

Monitors prices for open positions and checks exit conditions.
"""

import asyncio
from typing import Dict, List, Set, Callable, Optional, Any
from datetime import datetime

from ..data.binance_client import BinanceClient
from ..utils.logger import get_logger
from ..utils.helpers import now_utc

logger = get_logger(__name__)


class PriceMonitor:
    """
    Service for monitoring prices and triggering exit checks.
    """

    def __init__(
        self,
        binance_client: BinanceClient,
        on_price_update: Optional[Callable[[Dict[str, float]], None]] = None
    ):
        """
        Initialize price monitor.

        Args:
            binance_client: Client for fetching prices
            on_price_update: Callback when prices are updated
        """
        self.binance_client = binance_client
        self.on_price_update = on_price_update

        self._watched_symbols: Set[str] = set()
        self._prices: Dict[str, float] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_update: Optional[datetime] = None

    async def start(self, polling_interval: int = 15) -> None:
        """
        Start the price monitor.

        Args:
            polling_interval: Seconds between price updates
        """
        if self._running:
            logger.warning("Price monitor already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._poll_loop(polling_interval))
        logger.info(f"Price monitor started (polling every {polling_interval}s)")

    async def stop(self) -> None:
        """Stop the price monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Price monitor stopped")

    async def _poll_loop(self, interval: int) -> None:
        """Main polling loop."""
        while self._running:
            try:
                if self._watched_symbols:
                    await self._update_prices()
            except Exception as e:
                logger.error(f"Error in price poll loop: {e}")

            await asyncio.sleep(interval)

    async def _update_prices(self) -> None:
        """Fetch and update prices."""
        if not self._watched_symbols:
            return

        symbols = list(self._watched_symbols)
        prices = await self.binance_client.get_prices(symbols)

        if prices:
            self._prices.update(prices)
            self._last_update = now_utc()

            # Callback
            if self.on_price_update:
                try:
                    self.on_price_update(prices)
                except Exception as e:
                    logger.error(f"Error in price update callback: {e}")

    def add_symbol(self, symbol: str) -> None:
        """
        Add a symbol to watch.

        Args:
            symbol: Trading pair to watch (e.g., "BTCUSDT")
        """
        self._watched_symbols.add(symbol)
        logger.debug(f"Added symbol to watch: {symbol}")

    def remove_symbol(self, symbol: str) -> None:
        """
        Remove a symbol from watch.

        Args:
            symbol: Trading pair to stop watching
        """
        self._watched_symbols.discard(symbol)
        self._prices.pop(symbol, None)
        logger.debug(f"Removed symbol from watch: {symbol}")

    def add_symbols(self, symbols: List[str]) -> None:
        """Add multiple symbols to watch."""
        for symbol in symbols:
            self.add_symbol(symbol)

    def remove_symbols(self, symbols: List[str]) -> None:
        """Remove multiple symbols from watch."""
        for symbol in symbols:
            self.remove_symbol(symbol)

    def get_price(self, symbol: str) -> Optional[float]:
        """
        Get the last known price for a symbol.

        Args:
            symbol: Trading pair

        Returns:
            Price or None if not available
        """
        return self._prices.get(symbol)

    def get_prices(self) -> Dict[str, float]:
        """Get all current prices."""
        return self._prices.copy()

    def get_watched_symbols(self) -> Set[str]:
        """Get set of watched symbols."""
        return self._watched_symbols.copy()

    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last price update."""
        return self._last_update

    @property
    def is_running(self) -> bool:
        """Check if monitor is running."""
        return self._running


class PriceMonitorSync:
    """Synchronous wrapper for PriceMonitor."""

    def __init__(self):
        from ..data.binance_client import BinanceClientSync
        self.binance_client = BinanceClientSync()
        self._watched_symbols: Set[str] = set()
        self._prices: Dict[str, float] = {}

    def add_symbol(self, symbol: str) -> None:
        """Add a symbol to watch."""
        self._watched_symbols.add(symbol)

    def add_symbols(self, symbols: List[str]) -> None:
        """Add multiple symbols to watch."""
        self._watched_symbols.update(symbols)

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from watch."""
        self._watched_symbols.discard(symbol)
        self._prices.pop(symbol, None)

    def update_prices(self) -> Dict[str, float]:
        """Fetch and update prices."""
        if not self._watched_symbols:
            return {}

        symbols = list(self._watched_symbols)
        prices = self.binance_client.get_prices(symbols)
        self._prices.update(prices)
        return prices

    def get_price(self, symbol: str) -> Optional[float]:
        """Get last known price."""
        return self._prices.get(symbol)

    def get_prices(self) -> Dict[str, float]:
        """Get all prices."""
        return self._prices.copy()

    def close(self) -> None:
        """Close resources."""
        self.binance_client.close()
