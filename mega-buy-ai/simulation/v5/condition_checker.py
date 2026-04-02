"""
V5 Condition Checker.

Checks the 6 entry conditions for V5 surveillance:
1. TL Break (close > trendline)
2. EMA100 1H (close > EMA100)
3. EMA20 4H (close > EMA20)
4. Cloud 1H (close > cloud top)
5. Cloud 30M (close > cloud top)
6. CHoCH/BOS (swing high broken)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from .watchlist import WatchlistEntry
from .indicators import TechnicalIndicators
from .trendline import TrendlineDetector
from ..data.binance_client import BinanceClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ConditionCheckResult:
    """Result of condition check."""
    all_met: bool
    conditions: Dict[str, bool]
    values: Dict[str, Any]
    errors: List[str]


class V5ConditionChecker:
    """
    Checks V5 entry conditions for watchlist entries.
    """

    # Required klines per timeframe
    KLINES_REQUIRED = {
        "30m": 60,   # For Ichimoku (52 periods) + margin
        "1h": 110,   # For EMA100 + margin
        "4h": 60,    # For EMA20 + trendline
    }

    def __init__(
        self,
        binance_client: BinanceClient,
        choch_margin_pct: float = 0.5,
        swing_left: int = 5,
        swing_right: int = 3
    ):
        """
        Initialize condition checker.

        Args:
            binance_client: Client for fetching price data
            choch_margin_pct: Margin for CHoCH confirmation
            swing_left: Swing high left parameter
            swing_right: Swing high right parameter
        """
        self.binance_client = binance_client
        self.choch_margin_pct = choch_margin_pct
        self.trendline_detector = TrendlineDetector(
            swing_left=swing_left,
            swing_right=swing_right
        )

    async def check_conditions(
        self,
        entry: WatchlistEntry
    ) -> ConditionCheckResult:
        """
        Check all 6 conditions for a watchlist entry.

        Args:
            entry: Watchlist entry to check

        Returns:
            ConditionCheckResult with all condition states
        """
        conditions = {
            "tl_break": False,
            "ema100_1h": False,
            "ema20_4h": False,
            "cloud_1h": False,
            "cloud_30m": False,
            "choch_bos": False,
        }
        values = {}
        errors = []

        try:
            # Fetch klines for all timeframes
            klines = await self.binance_client.get_multi_timeframe_klines(
                entry.pair,
                self.KLINES_REQUIRED
            )

            # Check each condition
            conditions["tl_break"], values["tl_break"] = self._check_tl_break(
                klines.get("1h", []),
                entry.trendline_price
            )

            conditions["ema100_1h"], values["ema100_1h"] = self._check_ema100_1h(
                klines.get("1h", [])
            )

            conditions["ema20_4h"], values["ema20_4h"] = self._check_ema20_4h(
                klines.get("4h", [])
            )

            conditions["cloud_1h"], values["cloud_1h"] = self._check_cloud(
                klines.get("1h", []),
                "1h"
            )

            conditions["cloud_30m"], values["cloud_30m"] = self._check_cloud(
                klines.get("30m", []),
                "30m"
            )

            conditions["choch_bos"], values["choch_bos"] = self._check_choch_bos(
                klines.get("1h", [])
            )

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Error checking conditions for {entry.pair}: {e}")

        # Update entry
        entry.conditions = conditions
        entry.conditions_values = values
        entry.record_check()

        return ConditionCheckResult(
            all_met=all(conditions.values()),
            conditions=conditions,
            values=values,
            errors=errors
        )

    def _check_tl_break(
        self,
        klines: List[Dict[str, Any]],
        trendline_price: Optional[float]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check TL Break condition."""
        if not klines or trendline_price is None:
            return (False, {"error": "No data or trendline"})

        current_close = klines[-1]["close"]
        is_broken = current_close > trendline_price

        return (is_broken, {
            "close": current_close,
            "trendline": trendline_price,
            "broken": is_broken
        })

    def _check_ema100_1h(
        self,
        klines: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check EMA100 1H condition."""
        if len(klines) < 100:
            return (False, {"error": "Insufficient data"})

        closes = [k["close"] for k in klines]
        ema100 = TechnicalIndicators.get_ema_current(closes, 100)

        if ema100 is None:
            return (False, {"error": "Could not calculate EMA"})

        current_close = closes[-1]
        is_above = current_close > ema100

        return (is_above, {
            "close": current_close,
            "ema100": ema100,
            "above": is_above
        })

    def _check_ema20_4h(
        self,
        klines: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check EMA20 4H condition."""
        if len(klines) < 20:
            return (False, {"error": "Insufficient data"})

        closes = [k["close"] for k in klines]
        ema20 = TechnicalIndicators.get_ema_current(closes, 20)

        if ema20 is None:
            return (False, {"error": "Could not calculate EMA"})

        current_close = closes[-1]
        is_above = current_close > ema20

        return (is_above, {
            "close": current_close,
            "ema20": ema20,
            "above": is_above
        })

    def _check_cloud(
        self,
        klines: List[Dict[str, Any]],
        timeframe: str
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check Cloud Top condition."""
        if len(klines) < 52:
            return (False, {"error": "Insufficient data"})

        highs, lows, closes = TechnicalIndicators.parse_klines(klines)
        cloud_top = TechnicalIndicators.calculate_ichimoku_cloud_top(highs, lows, closes)

        if cloud_top is None:
            return (False, {"error": "Could not calculate cloud"})

        current_close = closes[-1]
        is_above = current_close > cloud_top

        return (is_above, {
            "close": current_close,
            "cloud_top": cloud_top,
            "above": is_above,
            "timeframe": timeframe
        })

    def _check_choch_bos(
        self,
        klines: List[Dict[str, Any]]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check CHoCH/BOS condition."""
        if len(klines) < 20:
            return (False, {"error": "Insufficient data"})

        highs = [k["high"] for k in klines]
        closes = [k["close"] for k in klines]

        is_confirmed, swing_high = TechnicalIndicators.check_choch_bos(
            closes, highs, self.choch_margin_pct
        )

        return (is_confirmed, {
            "close": closes[-1],
            "swing_high": swing_high,
            "confirmed": is_confirmed
        })

    async def check_prerequisites(
        self,
        alert: Dict[str, Any],
        skip_stc: bool = False
    ) -> Tuple[bool, Optional[str], Optional[float]]:
        """
        Check V5 prerequisites before adding to watchlist.

        Prerequisites:
        1. STC Oversold (<0.2) on at least one TF
        2. Not 15m alone (must have 30m or 1h)
        3. Trendline exists

        Args:
            alert: Alert data
            skip_stc: If True, skip STC check (for historical alerts where
                      current STC no longer reflects the alert-time state)

        Returns:
            Tuple of (passes, rejection_reason, trendline_price)
        """
        pair = alert.get("pair", "")
        timeframes = alert.get("timeframes", [])

        # Check not 15m alone
        if timeframes == ["15m"] or (len(timeframes) == 1 and "15m" in timeframes):
            return (False, "REJECTED_15M_ALONE", None)

        # Fetch data for STC and trendline check
        try:
            klines_4h = await self.binance_client.get_klines(pair, "4h", 60)

            # Check trendline exists
            trendline_price = self.trendline_detector.calculate_trendline_from_klines(
                klines_4h, "closest"
            )

            if trendline_price is None:
                return (False, "REJECTED_NO_TL", None)

            # Check STC oversold (simplified - check 1h)
            if not skip_stc:
                klines_1h = await self.binance_client.get_klines(pair, "1h", 60)
                closes = [k["close"] for k in klines_1h]
                stc = TechnicalIndicators.calculate_stc(closes)

                if stc is None or stc >= 0.2:
                    # Also check 30m
                    klines_30m = await self.binance_client.get_klines(pair, "30m", 60)
                    closes_30m = [k["close"] for k in klines_30m]
                    stc_30m = TechnicalIndicators.calculate_stc(closes_30m)

                    if stc_30m is None or stc_30m >= 0.2:
                        return (False, "REJECTED_STC", None)
            else:
                logger.info(f"V5: STC check skipped for {pair} (historical alert)")

            return (True, None, trendline_price)

        except Exception as e:
            logger.error(f"Error checking prerequisites for {pair}: {e}")
            return (False, f"ERROR: {str(e)}", None)


class V5ConditionCheckerSync:
    """Synchronous wrapper for V5ConditionChecker."""

    def __init__(self):
        from ..data.binance_client import BinanceClientSync
        self.binance_client = BinanceClientSync()
        self.trendline_detector = TrendlineDetector()
        self.choch_margin_pct = 0.5

    def check_conditions_sync(self, entry: WatchlistEntry) -> ConditionCheckResult:
        """Check conditions synchronously."""
        import asyncio
        from ..data.binance_client import BinanceClient

        async def _check():
            client = BinanceClient()
            checker = V5ConditionChecker(client, self.choch_margin_pct)
            result = await checker.check_conditions(entry)
            await client.close()
            return result

        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_check())

    def close(self) -> None:
        """Close resources."""
        self.binance_client.close()
