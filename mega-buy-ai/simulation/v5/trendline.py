"""
Trendline Detection for V5 Surveillance.

Detects and tracks trendlines based on swing highs.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .indicators import TechnicalIndicators
from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Trendline:
    """Represents a trendline."""
    point1_idx: int
    point1_price: float
    point2_idx: int
    point2_price: float
    slope: float
    current_price: float

    @property
    def is_descending(self) -> bool:
        """Check if trendline is descending."""
        return self.slope < 0

    def get_price_at_index(self, index: int) -> float:
        """Get trendline price at a specific index."""
        bars_from_point2 = index - self.point2_idx
        return self.point2_price + (self.slope * bars_from_point2)


class TrendlineDetector:
    """
    Detects trendlines from swing highs.
    """

    def __init__(
        self,
        swing_left: int = 5,
        swing_right: int = 3,
        min_bars_between: int = 3,
        max_distance_pct: float = 100.0
    ):
        """
        Initialize trendline detector.

        Args:
            swing_left: Bars to check on left for swing high
            swing_right: Bars to check on right for swing high
            min_bars_between: Minimum bars between trendline points
            max_distance_pct: Maximum distance from price to trendline (%)
        """
        self.swing_left = swing_left
        self.swing_right = swing_right
        self.min_bars_between = min_bars_between
        self.max_distance_pct = max_distance_pct

    def detect_trendline(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        strategy: str = "closest"
    ) -> Optional[Trendline]:
        """
        Detect a trendline from the price data.

        Args:
            highs: List of high prices
            lows: List of low prices
            closes: List of close prices
            strategy: "closest" or "highest"

        Returns:
            Trendline or None if not found
        """
        # Find swing highs
        swing_highs = TechnicalIndicators.find_swing_highs(
            highs, self.swing_left, self.swing_right
        )

        if len(swing_highs) < 2:
            return None

        # Get last two swing highs
        swing_highs_sorted = sorted(swing_highs, key=lambda x: x[0], reverse=True)

        # Find valid pairs (at least min_bars_between apart)
        valid_pairs = []
        for i in range(len(swing_highs_sorted) - 1):
            for j in range(i + 1, len(swing_highs_sorted)):
                idx1, price1 = swing_highs_sorted[i]
                idx2, price2 = swing_highs_sorted[j]

                if idx1 - idx2 >= self.min_bars_between:
                    valid_pairs.append((idx2, price2, idx1, price1))

        if not valid_pairs:
            return None

        current_price = closes[-1]
        current_idx = len(closes) - 1

        # Calculate trendlines and their current values
        trendlines = []
        for p1_idx, p1_price, p2_idx, p2_price in valid_pairs:
            # Calculate slope
            slope = (p2_price - p1_price) / (p2_idx - p1_idx) if p2_idx != p1_idx else 0

            # Calculate trendline price at current index
            bars_from_p2 = current_idx - p2_idx
            tl_price = p2_price + (slope * bars_from_p2)

            # Check if within max distance
            distance_pct = abs(tl_price - current_price) / current_price * 100
            if distance_pct <= self.max_distance_pct:
                trendlines.append(Trendline(
                    point1_idx=p1_idx,
                    point1_price=p1_price,
                    point2_idx=p2_idx,
                    point2_price=p2_price,
                    slope=slope,
                    current_price=tl_price
                ))

        if not trendlines:
            return None

        # Select based on strategy
        if strategy == "closest":
            # Select trendline closest to current price
            return min(trendlines, key=lambda t: abs(t.current_price - current_price))
        else:
            # Select highest trendline
            return max(trendlines, key=lambda t: t.current_price)

    def check_tl_break(
        self,
        close: float,
        trendline_price: float
    ) -> bool:
        """
        Check if price has broken above trendline.

        Args:
            close: Current close price
            trendline_price: Trendline price

        Returns:
            True if trendline is broken
        """
        return close > trendline_price

    def calculate_trendline_from_klines(
        self,
        klines: List[Dict[str, Any]],
        strategy: str = "closest"
    ) -> Optional[float]:
        """
        Calculate trendline price from klines.

        Args:
            klines: List of kline dictionaries
            strategy: Selection strategy

        Returns:
            Trendline price or None
        """
        highs, lows, closes = TechnicalIndicators.parse_klines(klines)

        trendline = self.detect_trendline(highs, lows, closes, strategy)

        if trendline:
            return trendline.current_price
        return None
