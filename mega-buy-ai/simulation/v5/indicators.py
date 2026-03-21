"""
Technical Indicators for V5 Surveillance.

Calculates EMA, Ichimoku Cloud, and other indicators needed for V5 conditions.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """
    Calculator for technical indicators.
    """

    # Ichimoku parameters (STANDARD - do not change)
    ICHIMOKU_TENKAN = 9
    ICHIMOKU_KIJUN = 26
    ICHIMOKU_SENKOU_B = 52

    @staticmethod
    def calculate_ema(closes: List[float], period: int) -> List[float]:
        """
        Calculate Exponential Moving Average.

        Args:
            closes: List of close prices
            period: EMA period

        Returns:
            List of EMA values
        """
        if len(closes) < period:
            return []

        multiplier = 2 / (period + 1)
        ema_values = []

        # Initial SMA
        sma = sum(closes[:period]) / period
        ema_values.append(sma)

        # Calculate EMA
        for i in range(period, len(closes)):
            ema = (closes[i] * multiplier) + (ema_values[-1] * (1 - multiplier))
            ema_values.append(ema)

        return ema_values

    @staticmethod
    def get_ema_current(closes: List[float], period: int) -> Optional[float]:
        """
        Get current EMA value.

        Args:
            closes: List of close prices
            period: EMA period

        Returns:
            Current EMA value or None
        """
        ema_values = TechnicalIndicators.calculate_ema(closes, period)
        return ema_values[-1] if ema_values else None

    @staticmethod
    def calculate_ichimoku_cloud_top(
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> Optional[float]:
        """
        Calculate Ichimoku Cloud Top (max of Senkou-A and Senkou-B).

        Uses STANDARD parameters:
        - Tenkan-Sen: 9
        - Kijun-Sen: 26
        - Senkou-Span B: 52

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices

        Returns:
            Cloud top value or None
        """
        if len(closes) < TechnicalIndicators.ICHIMOKU_SENKOU_B:
            return None

        # Tenkan-Sen (Conversion Line): (9-period high + 9-period low) / 2
        tenkan_high = max(highs[-TechnicalIndicators.ICHIMOKU_TENKAN:])
        tenkan_low = min(lows[-TechnicalIndicators.ICHIMOKU_TENKAN:])
        tenkan = (tenkan_high + tenkan_low) / 2

        # Kijun-Sen (Base Line): (26-period high + 26-period low) / 2
        kijun_high = max(highs[-TechnicalIndicators.ICHIMOKU_KIJUN:])
        kijun_low = min(lows[-TechnicalIndicators.ICHIMOKU_KIJUN:])
        kijun = (kijun_high + kijun_low) / 2

        # Senkou-Span A: (Tenkan + Kijun) / 2
        senkou_a = (tenkan + kijun) / 2

        # Senkou-Span B: (52-period high + 52-period low) / 2
        senkou_b_high = max(highs[-TechnicalIndicators.ICHIMOKU_SENKOU_B:])
        senkou_b_low = min(lows[-TechnicalIndicators.ICHIMOKU_SENKOU_B:])
        senkou_b = (senkou_b_high + senkou_b_low) / 2

        # Cloud Top = max(Senkou-A, Senkou-B)
        cloud_top = max(senkou_a, senkou_b)

        return cloud_top

    @staticmethod
    def find_swing_highs(
        highs: List[float],
        left: int = 5,
        right: int = 3
    ) -> List[Tuple[int, float]]:
        """
        Find swing highs in price data.

        A swing high at index i is valid if:
        high[i] > all highs in [i-left, i-1] AND [i+1, i+right]

        Args:
            highs: List of high prices
            left: Bars to check on left side
            right: Bars to check on right side

        Returns:
            List of (index, price) tuples for swing highs
        """
        swing_highs = []

        for i in range(left, len(highs) - right):
            high_i = highs[i]

            # Check left side
            is_higher_than_left = all(
                high_i > highs[j] for j in range(i - left, i)
            )

            # Check right side
            is_higher_than_right = all(
                high_i > highs[j] for j in range(i + 1, i + right + 1)
            )

            if is_higher_than_left and is_higher_than_right:
                swing_highs.append((i, high_i))

        return swing_highs

    @staticmethod
    def check_choch_bos(
        closes: List[float],
        highs: List[float],
        margin_pct: float = 0.5
    ) -> Tuple[bool, Optional[float]]:
        """
        Check for CHoCH/BOS (Change of Character / Break of Structure).

        CHoCH/BOS is confirmed when close breaks above a previous swing high
        with more than margin_pct margin.

        Args:
            closes: List of close prices
            highs: List of high prices
            margin_pct: Margin percentage for confirmation

        Returns:
            Tuple of (is_confirmed, swing_high_price)
        """
        # Find swing highs
        swing_highs = TechnicalIndicators.find_swing_highs(highs)

        if not swing_highs:
            return (False, None)

        # Get the most recent swing high (excluding very recent bars)
        recent_swing_highs = [
            (idx, price) for idx, price in swing_highs
            if idx < len(closes) - 3  # Must be at least 3 bars old
        ]

        if not recent_swing_highs:
            return (False, None)

        # Get the highest recent swing high
        _, swing_high_price = max(recent_swing_highs, key=lambda x: x[1])

        # Check if current close breaks above swing high with margin
        current_close = closes[-1]
        threshold = swing_high_price * (1 + margin_pct / 100)

        is_confirmed = current_close > threshold

        return (is_confirmed, swing_high_price)

    @staticmethod
    def calculate_stc(
        closes: List[float],
        length: int = 50,
        fast: int = 50,
        slow: int = 200
    ) -> Optional[float]:
        """
        Calculate Adaptive Stochastic (STC).

        Args:
            closes: List of close prices
            length: Stochastic length
            fast: Fast period
            slow: Slow period

        Returns:
            STC value (0-1) or None
        """
        if len(closes) < max(length, slow):
            return None

        recent = closes[-length:]
        highest = max(recent)
        lowest = min(recent)

        if highest == lowest:
            return 0.5

        stc = (closes[-1] - lowest) / (highest - lowest)
        return stc

    @staticmethod
    def parse_klines(klines: List[Dict[str, Any]]) -> Tuple[List[float], List[float], List[float]]:
        """
        Parse klines into separate lists.

        Args:
            klines: List of kline dictionaries

        Returns:
            Tuple of (highs, lows, closes)
        """
        highs = [k["high"] for k in klines]
        lows = [k["low"] for k in klines]
        closes = [k["close"] for k in klines]
        return (highs, lows, closes)
