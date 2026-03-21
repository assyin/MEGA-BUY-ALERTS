#!/usr/bin/env python3
"""
Volume Profile Analyzer for MEGA BUY Backtest System

Calculates and analyzes Volume Profile to improve trade quality.
Integrates with V1, V3, and V4 strategies.
"""

import numpy as np
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
import pandas as pd


class VolumeProfileAnalyzer:
    """
    Calculates Volume Profile and provides analysis for trading decisions.

    Key metrics:
    - POC (Point of Control): Price level with highest volume
    - VAH (Value Area High): Upper boundary of 70% volume zone
    - VAL (Value Area Low): Lower boundary of 70% volume zone
    - HVN (High Volume Nodes): Strong support/resistance levels
    - LVN (Low Volume Nodes): Fast price movement zones
    """

    def __init__(self, config: dict = None):
        """
        Initialize Volume Profile Analyzer.

        Args:
            config: Configuration dictionary with VP parameters
        """
        config = config or {}

        # Core parameters
        self.num_bins = config.get('VP_NUM_BINS', 50)
        self.va_percentage = config.get('VP_VA_PCT', 70) / 100
        self.hvn_threshold = config.get('VP_HVN_THRESHOLD', 1.5)
        self.lvn_threshold = config.get('VP_LVN_THRESHOLD', 0.5)

        # Lookback periods
        self.lookback_1h = config.get('VP_LOOKBACK_1H', 100)
        self.lookback_4h = config.get('VP_LOOKBACK_4H', 50)

        # Tolerances
        self.poc_tolerance_pct = config.get('VP_POC_TOLERANCE_PCT', 0.5) / 100
        self.hvn_proximity_pct = config.get('VP_HVN_PROXIMITY_PCT', 1.0) / 100

        # Scoring weights
        self.score_entry_at_poc = config.get('VP_ENTRY_AT_POC_BONUS', 20)
        self.score_entry_at_val = config.get('VP_ENTRY_AT_VAL_BONUS', 15)
        self.score_sl_below_hvn = config.get('VP_SL_BELOW_HVN_BONUS', 20)
        self.score_tp_at_vah = config.get('VP_TP_AT_VAH_BONUS', 15)
        self.score_lvn_path = config.get('VP_LVN_PATH_BONUS', 15)
        self.score_ob_hvn_confluence = config.get('VP_OB_HVN_CONFLUENCE_BONUS', 15)

        # Cache for VP calculations
        self._cache = {}

    def calculate(self, df: pd.DataFrame, lookback: int = None) -> Dict:
        """
        Calculate Volume Profile for given OHLCV data.

        Args:
            df: DataFrame with columns [open, high, low, close, volume, datetime]
            lookback: Number of candles to analyze (default: use class setting)

        Returns:
            dict with POC, VAH, VAL, HVN levels, LVN levels, and volume distribution
        """
        if lookback is None:
            lookback = self.lookback_1h

        # Use last N candles
        df_subset = df.tail(lookback).copy()

        if len(df_subset) < 10:
            return self._empty_result()

        # Determine price range
        price_min = df_subset['low'].min()
        price_max = df_subset['high'].max()

        if price_max <= price_min:
            return self._empty_result()

        bin_size = (price_max - price_min) / self.num_bins

        # Initialize volume by level
        volume_by_level = defaultdict(float)

        # Distribute volume from each candle
        for idx, row in df_subset.iterrows():
            self._distribute_candle_volume(
                row, price_min, bin_size, volume_by_level
            )

        if not volume_by_level:
            return self._empty_result()

        # Normalize volumes
        total_volume = sum(volume_by_level.values())
        if total_volume == 0:
            return self._empty_result()

        for level in volume_by_level:
            volume_by_level[level] /= total_volume

        # Find POC (max volume level)
        poc_level = max(volume_by_level, key=volume_by_level.get)
        poc_volume = volume_by_level[poc_level]

        # Calculate Value Area (70% of volume)
        vah, val = self._calculate_value_area(volume_by_level, poc_level)

        # Identify HVN and LVN
        hvn_levels, lvn_levels = self._identify_hvn_lvn(volume_by_level)

        return {
            'poc': poc_level,
            'poc_volume': poc_volume,
            'vah': vah,
            'val': val,
            'hvn_levels': hvn_levels,
            'lvn_levels': lvn_levels,
            'volume_by_level': dict(volume_by_level),
            'total_volume': total_volume,
            'bin_size': bin_size,
            'price_min': price_min,
            'price_max': price_max,
            'num_candles': len(df_subset)
        }

    def _distribute_candle_volume(self, row: pd.Series, price_min: float,
                                   bin_size: float, volume_by_level: dict):
        """
        Distribute candle volume across price levels.
        Uses weighted distribution with more volume near the close.
        """
        candle_low = row['low']
        candle_high = row['high']
        candle_close = row['close']
        candle_open = row['open']
        candle_volume = row['volume']

        if candle_volume <= 0 or candle_high <= candle_low:
            return

        candle_range = candle_high - candle_low

        # Find bins touched by this candle
        start_bin = max(0, int((candle_low - price_min) / bin_size))
        end_bin = min(self.num_bins - 1, int((candle_high - price_min) / bin_size))

        # Determine candle type for weighting
        is_bullish = candle_close > candle_open

        for bin_idx in range(start_bin, end_bin + 1):
            level_price = price_min + (bin_idx + 0.5) * bin_size

            # Weight based on distance to close (more volume near close)
            distance_to_close = abs(level_price - candle_close)
            close_weight = 1 - (distance_to_close / (candle_range + 0.0001))
            close_weight = max(0.1, close_weight)  # Minimum weight

            # Additional weight for body vs wick
            body_low = min(candle_open, candle_close)
            body_high = max(candle_open, candle_close)

            if body_low <= level_price <= body_high:
                body_weight = 1.5  # More volume in body
            else:
                body_weight = 0.7  # Less volume in wicks

            total_weight = close_weight * body_weight
            volume_by_level[level_price] += candle_volume * total_weight

    def _calculate_value_area(self, volume_by_level: dict, poc_level: float) -> Tuple[float, float]:
        """
        Calculate Value Area (70% of total volume) around POC.
        """
        sorted_levels = sorted(volume_by_level.keys())
        poc_idx = min(range(len(sorted_levels)),
                      key=lambda i: abs(sorted_levels[i] - poc_level))

        cumulative_volume = volume_by_level[sorted_levels[poc_idx]]
        va_levels = [sorted_levels[poc_idx]]

        low_idx = poc_idx - 1
        high_idx = poc_idx + 1

        while cumulative_volume < self.va_percentage and (low_idx >= 0 or high_idx < len(sorted_levels)):
            low_vol = volume_by_level[sorted_levels[low_idx]] if low_idx >= 0 else 0
            high_vol = volume_by_level[sorted_levels[high_idx]] if high_idx < len(sorted_levels) else 0

            if low_vol >= high_vol and low_idx >= 0:
                cumulative_volume += low_vol
                va_levels.append(sorted_levels[low_idx])
                low_idx -= 1
            elif high_idx < len(sorted_levels):
                cumulative_volume += high_vol
                va_levels.append(sorted_levels[high_idx])
                high_idx += 1
            else:
                break

        vah = max(va_levels)
        val = min(va_levels)

        return vah, val

    def _identify_hvn_lvn(self, volume_by_level: dict) -> Tuple[List[float], List[float]]:
        """
        Identify High Volume Nodes and Low Volume Nodes.
        """
        volumes = list(volume_by_level.values())
        avg_volume = np.mean(volumes)
        std_volume = np.std(volumes)

        hvn_threshold = avg_volume + std_volume * (self.hvn_threshold - 1)
        lvn_threshold = avg_volume * self.lvn_threshold

        hvn_levels = sorted([l for l, v in volume_by_level.items() if v >= hvn_threshold])
        lvn_levels = sorted([l for l, v in volume_by_level.items() if v <= lvn_threshold])

        # Cluster nearby HVN levels
        hvn_levels = self._cluster_levels(hvn_levels)
        lvn_levels = self._cluster_levels(lvn_levels)

        return hvn_levels, lvn_levels

    def _cluster_levels(self, levels: List[float], tolerance_pct: float = 0.5) -> List[float]:
        """
        Cluster nearby price levels together.
        """
        if not levels:
            return []

        clustered = []
        current_cluster = [levels[0]]

        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance_pct / 100:
                current_cluster.append(level)
            else:
                clustered.append(np.mean(current_cluster))
                current_cluster = [level]

        if current_cluster:
            clustered.append(np.mean(current_cluster))

        return clustered

    def _empty_result(self) -> Dict:
        """Return empty VP result."""
        return {
            'poc': None,
            'poc_volume': None,
            'vah': None,
            'val': None,
            'hvn_levels': [],
            'lvn_levels': [],
            'volume_by_level': {},
            'total_volume': 0,
            'bin_size': 0,
            'price_min': None,
            'price_max': None,
            'num_candles': 0
        }

    # ═══════════════════════════════════════════════════════════════════════
    # ANALYSIS METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def is_at_poc(self, price: float, vp_data: dict, tolerance_pct: float = None) -> bool:
        """Check if price is at or near POC."""
        if not vp_data.get('poc'):
            return False

        tolerance = tolerance_pct or self.poc_tolerance_pct
        return abs(price - vp_data['poc']) / price <= tolerance

    def is_at_val(self, price: float, vp_data: dict, tolerance_pct: float = 0.01) -> bool:
        """Check if price is at or near VAL."""
        if not vp_data.get('val'):
            return False
        return abs(price - vp_data['val']) / price <= tolerance_pct

    def is_at_vah(self, price: float, vp_data: dict, tolerance_pct: float = 0.01) -> bool:
        """Check if price is at or near VAH."""
        if not vp_data.get('vah'):
            return False
        return abs(price - vp_data['vah']) / price <= tolerance_pct

    def is_at_hvn(self, price: float, vp_data: dict, tolerance_pct: float = None) -> bool:
        """Check if price is at a High Volume Node."""
        tolerance = tolerance_pct or self.hvn_proximity_pct

        for hvn in vp_data.get('hvn_levels', []):
            if abs(price - hvn) / price <= tolerance:
                return True
        return False

    def get_nearest_hvn(self, price: float, vp_data: dict, direction: str = 'below') -> Optional[float]:
        """
        Get nearest HVN above or below price.

        Args:
            price: Current price
            vp_data: Volume Profile data
            direction: 'below' or 'above'

        Returns:
            Nearest HVN price or None
        """
        hvn_levels = vp_data.get('hvn_levels', [])

        if not hvn_levels:
            return None

        if direction == 'below':
            candidates = [h for h in hvn_levels if h < price]
            return max(candidates) if candidates else None
        else:
            candidates = [h for h in hvn_levels if h > price]
            return min(candidates) if candidates else None

    def get_nearest_lvn(self, price: float, vp_data: dict, direction: str = 'above') -> Optional[float]:
        """Get nearest LVN above or below price."""
        lvn_levels = vp_data.get('lvn_levels', [])

        if not lvn_levels:
            return None

        if direction == 'below':
            candidates = [l for l in lvn_levels if l < price]
            return max(candidates) if candidates else None
        else:
            candidates = [l for l in lvn_levels if l > price]
            return min(candidates) if candidates else None

    def has_lvn_between(self, price1: float, price2: float, vp_data: dict) -> bool:
        """Check if there's an LVN between two prices (indicates fast movement zone)."""
        low = min(price1, price2)
        high = max(price1, price2)

        for lvn in vp_data.get('lvn_levels', []):
            if low < lvn < high:
                return True
        return False

    def count_lvn_between(self, price1: float, price2: float, vp_data: dict) -> int:
        """Count LVN levels between two prices."""
        low = min(price1, price2)
        high = max(price1, price2)

        return sum(1 for lvn in vp_data.get('lvn_levels', []) if low < lvn < high)

    def is_above_vah(self, price: float, vp_data: dict) -> bool:
        """Check if price is above Value Area High (overextended)."""
        vah = vp_data.get('vah')
        return vah is not None and price > vah

    def is_below_val(self, price: float, vp_data: dict) -> bool:
        """Check if price is below Value Area Low."""
        val = vp_data.get('val')
        return val is not None and price < val

    def get_position_in_va(self, price: float, vp_data: dict) -> str:
        """
        Get position relative to Value Area.

        Returns:
            'ABOVE_VAH', 'IN_VA', 'BELOW_VAL', or 'UNKNOWN'
        """
        vah = vp_data.get('vah')
        val = vp_data.get('val')

        if vah is None or val is None:
            return 'UNKNOWN'

        if price > vah:
            return 'ABOVE_VAH'
        elif price < val:
            return 'BELOW_VAL'
        else:
            return 'IN_VA'

    # ═══════════════════════════════════════════════════════════════════════
    # RETEST DETECTION METHODS
    # Detects if VP levels (VAL/POC/VAH) were retested between signal and entry
    # ═══════════════════════════════════════════════════════════════════════

    def detect_vp_retests(self, df: pd.DataFrame, vp_data: dict,
                          signal_dt, entry_dt,
                          ob_zone_1h: dict = None,
                          ob_zone_4h: dict = None,
                          tolerance_pct: float = 1.0) -> Dict:
        """
        Detect if VP levels (VAL/POC/VAH) were retested between signal and entry.

        This is important because:
        - A retest of VAL/POC before breakout = confirmation of support
        - If retest coincides with OB zone = extra confluence

        Args:
            df: DataFrame with OHLCV data
            vp_data: Volume Profile data with POC/VAH/VAL
            signal_dt: MEGA BUY signal datetime
            entry_dt: Entry datetime
            ob_zone_1h: 1H Order Block zone (optional)
            ob_zone_4h: 4H Order Block zone (optional)
            tolerance_pct: Tolerance % for level touch detection

        Returns:
            dict with retest information
        """
        result = {
            'val_retested': False,
            'val_retest_dt': None,
            'val_retest_price': None,
            'val_retest_rejected': False,
            'poc_retested': False,
            'poc_retest_dt': None,
            'poc_retest_price': None,
            'poc_retest_rejected': False,
            'vah_retested': False,
            'vah_retest_dt': None,
            'vah_retest_price': None,
            'vah_retest_rejected': False,
            'hvn_retested': False,
            'hvn_retest_level': None,
            'hvn_retest_dt': None,
            'ob_confluence': False,
            'ob_confluence_tf': None,
            'pullback_completed': False,
            'pullback_level': None,
            'pullback_quality': None
        }

        if not vp_data.get('poc') or df is None or len(df) == 0:
            return result

        poc = vp_data.get('poc')
        vah = vp_data.get('vah')
        val = vp_data.get('val')
        hvn_levels = vp_data.get('hvn_levels', [])

        # Filter data between signal and entry
        # IMPORTANT: Only detect retests AFTER the MEGA BUY alert
        df_range = df[(df['datetime'] >= signal_dt) & (df['datetime'] <= entry_dt)].copy()

        if len(df_range) == 0:
            return result

        tolerance = tolerance_pct / 100

        # Track previous candle to verify price came FROM ABOVE (for BUY retests)
        prev_close = None
        prev_high = None

        # Check each candle for VP level touches (BUY RETEST = support confirmation)
        for idx, row in df_range.iterrows():
            candle_low = row['low']
            candle_high = row['high']
            candle_close = row['close']
            candle_open = row['open']
            candle_dt = row['datetime']

            # VAL Retest Detection (BUY: price comes DOWN to VAL, bounces UP)
            if val and not result['val_retested']:
                # For a proper BUY retest:
                # 1. Previous candle close was ABOVE VAL (coming from above)
                # 2. Current candle low touches VAL
                # 3. Current candle close is above VAL (rejection/bounce)
                price_was_above = prev_close is None or prev_close > val * (1 - tolerance)
                candle_touched_val = candle_low <= val * (1 + tolerance)
                candle_bounced = candle_close > val

                if price_was_above and candle_touched_val:
                    result['val_retested'] = True
                    result['val_retest_dt'] = candle_dt
                    result['val_retest_price'] = candle_low
                    # Rejected = bounced up (close above VAL) = support confirmed
                    result['val_retest_rejected'] = candle_bounced

            # POC Retest Detection (BUY: price comes DOWN to POC, bounces UP)
            if poc and not result['poc_retested']:
                # For a proper BUY retest:
                # 1. Price was ABOVE POC before
                # 2. Candle low touches POC
                # 3. Candle close is above POC (bounce)
                price_was_above = prev_close is None or prev_close > poc * (1 - tolerance)
                candle_touched_poc = candle_low <= poc * (1 + tolerance) or (candle_low <= poc <= candle_high)
                candle_bounced = candle_close > poc

                if price_was_above and candle_touched_poc:
                    result['poc_retested'] = True
                    result['poc_retest_dt'] = candle_dt
                    result['poc_retest_price'] = min(candle_low, poc)
                    # Rejected = bounced up (close above POC)
                    result['poc_retest_rejected'] = candle_bounced

            # VAH Retest Detection (BUY: pullback to VAH from above, then continuation up)
            if vah and not result['vah_retested']:
                # For VAH retest in a BUY context:
                # Price was above VAH, pulled back to touch VAH, then bounced
                price_was_above = prev_close is None or prev_close > vah
                candle_touched_vah = candle_low <= vah * (1 + tolerance)
                candle_bounced = candle_close > vah

                if price_was_above and candle_touched_vah:
                    result['vah_retested'] = True
                    result['vah_retest_dt'] = candle_dt
                    result['vah_retest_price'] = candle_low
                    result['vah_retest_rejected'] = candle_bounced

            # HVN Retest Detection (BUY: support at HVN level)
            if not result['hvn_retested']:
                for hvn in hvn_levels:
                    price_was_above = prev_close is None or prev_close > hvn * (1 - tolerance)
                    candle_touched_hvn = candle_low <= hvn * (1 + tolerance)
                    candle_bounced = candle_close > hvn

                    if price_was_above and candle_touched_hvn and candle_bounced:
                        result['hvn_retested'] = True
                        result['hvn_retest_level'] = hvn
                        result['hvn_retest_dt'] = candle_dt
                        break

            # Update previous candle values for next iteration
            prev_close = candle_close
            prev_high = candle_high

        # Check OB Confluence
        if result['val_retested'] or result['poc_retested'] or result['hvn_retested']:
            retest_price = result['val_retest_price'] or result['poc_retest_price'] or result['hvn_retest_level']

            # Check 1H OB confluence
            if ob_zone_1h and retest_price:
                ob_high = ob_zone_1h.get('high', 0)
                ob_low = ob_zone_1h.get('low', 0)
                if ob_low <= retest_price <= ob_high * 1.02:
                    result['ob_confluence'] = True
                    result['ob_confluence_tf'] = '1H'

            # Check 4H OB confluence
            if ob_zone_4h and retest_price and not result['ob_confluence']:
                ob_high = ob_zone_4h.get('high', 0)
                ob_low = ob_zone_4h.get('low', 0)
                if ob_low <= retest_price <= ob_high * 1.02:
                    result['ob_confluence'] = True
                    result['ob_confluence_tf'] = '4H'

            # Confluence with both
            if ob_zone_1h and ob_zone_4h and retest_price:
                ob_1h_low = ob_zone_1h.get('low', 0)
                ob_1h_high = ob_zone_1h.get('high', 0)
                ob_4h_low = ob_zone_4h.get('low', 0)
                ob_4h_high = ob_zone_4h.get('high', 0)

                in_1h = ob_1h_low <= retest_price <= ob_1h_high * 1.02
                in_4h = ob_4h_low <= retest_price <= ob_4h_high * 1.02

                if in_1h and in_4h:
                    result['ob_confluence_tf'] = '1H+4H'

        # Determine if pullback is completed
        if result['val_retested'] and result['val_retest_rejected']:
            result['pullback_completed'] = True
            result['pullback_level'] = 'VAL'
            result['pullback_quality'] = 'STRONG' if result['ob_confluence'] else 'GOOD'
        elif result['poc_retested'] and result['poc_retest_rejected']:
            result['pullback_completed'] = True
            result['pullback_level'] = 'POC'
            result['pullback_quality'] = 'STRONG' if result['ob_confluence'] else 'GOOD'
        elif result['hvn_retested']:
            result['pullback_completed'] = True
            result['pullback_level'] = 'HVN'
            result['pullback_quality'] = 'MODERATE'

        return result

    # ═══════════════════════════════════════════════════════════════════════
    # SCORING METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def calculate_vp_score(self, entry_price: float, sl_price: float,
                           tp1_price: float, vp_data: dict,
                           vp_4h_data: dict = None,
                           ob_zone: dict = None,
                           retest_info: dict = None) -> Dict:
        """
        Calculate comprehensive VP score for a trade setup.

        Args:
            entry_price: Planned entry price
            sl_price: Stop loss price
            tp1_price: First take profit price
            vp_data: 1H Volume Profile data
            vp_4h_data: 4H Volume Profile data (optional)
            ob_zone: Order Block zone dict with 'high' and 'low' (optional)
            retest_info: VP retest detection results (optional)

        Returns:
            dict with score, grade, details, and recommendations
        """
        score = 0
        details = []
        recommendations = []
        retest_info = retest_info or {}

        if not vp_data.get('poc'):
            return {
                'vp_score': 0,
                'vp_grade': 'N/A',
                'vp_details': ['No VP data available'],
                'vp_recommendations': [],
                'vp_sl_optimized': None,
                'vp_tp_suggestions': [],
                'vp_retest_info': retest_info
            }

        poc = vp_data['poc']
        vah = vp_data['vah']
        val = vp_data['val']
        hvn_levels = vp_data.get('hvn_levels', [])
        lvn_levels = vp_data.get('lvn_levels', [])

        # ═══════════════════════════════════════════════════════════════════
        # 1. ENTRY POSITION SCORING (max 35 points)
        # ═══════════════════════════════════════════════════════════════════

        poc_distance_pct = abs(entry_price - poc) / entry_price * 100
        val_distance_pct = abs(entry_price - val) / entry_price * 100 if val else 100

        if poc_distance_pct < 0.5:
            score += 25
            details.append(f"Entry AT POC ({poc:.6f}) +25")
        elif poc_distance_pct < 1.0:
            score += 20
            details.append(f"Entry NEAR POC ({poc_distance_pct:.2f}% away) +20")
        elif poc_distance_pct < 2.0:
            score += 15
            details.append(f"Entry CLOSE to POC ({poc_distance_pct:.2f}% away) +15")
        elif val_distance_pct < 1.0:
            score += 15
            details.append(f"Entry NEAR VAL ({val:.6f}) +15")
        elif self.is_at_hvn(entry_price, vp_data):
            score += 15
            details.append("Entry at HVN (support) +15")

        # NEW: POC slightly ABOVE entry = pullback support zone
        # When POC is 0.5-3% above entry, price tends to return to POC and bounce
        if poc > entry_price and poc_distance_pct < 3.0:
            score += 15
            details.append(f"POC ABOVE entry ({poc_distance_pct:.2f}%) = pullback support +15")

        # Entry IN Value Area is generally good (institutional participation)
        if val and vah and val < entry_price < vah:
            score += 5
            details.append("Entry IN Value Area (institutional zone) +5")

        # Penalty if above VAH (overextended)
        if self.is_above_vah(entry_price, vp_data):
            score -= 10
            details.append("Entry ABOVE VAH (overextended) -10")
            recommendations.append("Consider waiting for pullback to VAH")

        # ═══════════════════════════════════════════════════════════════════
        # 2. STOP LOSS PROTECTION (max 30 points)
        # ═══════════════════════════════════════════════════════════════════

        hvn_below_sl = self.get_nearest_hvn(sl_price, vp_data, 'below')
        hvn_above_sl = self.get_nearest_hvn(sl_price, vp_data, 'above')
        sl_protected = False

        # Best case: HVN just above SL (between SL and entry)
        if hvn_above_sl and hvn_above_sl < entry_price:
            distance_to_hvn = (sl_price - hvn_above_sl) / sl_price * 100
            if distance_to_hvn < 1.0:
                score += 25
                sl_protected = True
                details.append(f"SL protected by HVN at {hvn_above_sl:.6f} +25")
            elif distance_to_hvn < 2.0:
                score += 15
                sl_protected = True
                details.append(f"HVN support near SL +15")

        # NEW: VAL between SL and Entry = strong support zone
        # Value Area Low acts as natural support level
        if val and sl_price < val < entry_price:
            val_distance_from_sl = (val - sl_price) / sl_price * 100
            if val_distance_from_sl < 3.0:
                score += 20
                sl_protected = True
                details.append(f"VAL ({val:.6f}) between SL and Entry = natural support +20")
            else:
                score += 10
                sl_protected = True
                details.append(f"VAL ({val:.6f}) provides support zone +10")

        # NEW: POC between SL and Entry = ultra-strong support
        if poc and sl_price < poc < entry_price:
            score += 15
            sl_protected = True
            details.append(f"POC ({poc:.6f}) between SL and Entry = ultra-strong support +15")

        if not sl_protected:
            if hvn_below_sl:
                # There's support below SL (less ideal but still useful)
                score += 5
                details.append(f"HVN support exists below SL +5")
                recommendations.append(f"Consider tighter SL above HVN at {hvn_below_sl:.6f}")
            else:
                # No HVN protection
                details.append("No volume-based support near SL +0")
                recommendations.append("Higher risk: No volume-based support below SL")

        # Optimized SL suggestion
        vp_sl_optimized = None
        if hvn_above_sl and hvn_above_sl < entry_price:
            vp_sl_optimized = hvn_above_sl * 0.995  # 0.5% below HVN
        elif val and val < entry_price:
            vp_sl_optimized = val * 0.995

        # ═══════════════════════════════════════════════════════════════════
        # 3. PATH TO TP (max 20 points)
        # ═══════════════════════════════════════════════════════════════════

        lvn_count = self.count_lvn_between(entry_price, tp1_price, vp_data)

        if lvn_count >= 2:
            score += 20
            details.append(f"Multiple LVN ({lvn_count}) in path to TP (fast move) +20")
        elif lvn_count == 1:
            score += 10
            details.append("LVN in path to TP +10")
        else:
            details.append("No LVN in path (may consolidate) +0")

        # Check for HVN resistance before TP
        hvn_resistance = self.get_nearest_hvn(entry_price, vp_data, 'above')
        if hvn_resistance and hvn_resistance < tp1_price:
            score -= 5
            details.append(f"HVN resistance at {hvn_resistance:.6f} before TP -5")
            recommendations.append(f"Consider partial TP at HVN {hvn_resistance:.6f}")

        # ═══════════════════════════════════════════════════════════════════
        # 4. TP QUALITY (max 20 points)
        # ═══════════════════════════════════════════════════════════════════

        tp_suggestions = []

        # Check if TP1 aligns with VAH
        if vah and abs(tp1_price - vah) / tp1_price < 0.02:
            score += 20
            details.append(f"TP1 aligns with VAH ({vah:.6f}) +20")
        elif vah and entry_price < vah < tp1_price:
            score += 10
            tp_suggestions.append(('VAH', vah))
            details.append(f"VAH at {vah:.6f} is a natural TP +10")

        # Check for POC above entry as target
        if poc > entry_price * 1.05:
            tp_suggestions.append(('POC', poc))
            if not tp_suggestions:
                score += 5
                details.append(f"POC at {poc:.6f} is potential target +5")

        # ═══════════════════════════════════════════════════════════════════
        # 5. MULTI-TF CONFLUENCE (max 10 points)
        # ═══════════════════════════════════════════════════════════════════

        if vp_4h_data and vp_4h_data.get('poc'):
            poc_4h = vp_4h_data['poc']

            # Check POC alignment
            if abs(poc - poc_4h) / poc < 0.02:
                score += 10
                details.append(f"POC 1H-4H aligned at {poc:.6f} +10")

            # Add 4H targets
            if vp_4h_data.get('vah') and vp_4h_data['vah'] > entry_price:
                tp_suggestions.append(('VAH_4H', vp_4h_data['vah']))

        # ═══════════════════════════════════════════════════════════════════
        # 6. OB + HVN CONFLUENCE (bonus 15 points)
        # ═══════════════════════════════════════════════════════════════════

        if ob_zone:
            ob_mid = (ob_zone.get('high', 0) + ob_zone.get('low', 0)) / 2
            if self.is_at_hvn(ob_mid, vp_data, tolerance_pct=0.015):
                score += 15
                details.append("OB + HVN confluence (ultra-strong zone) +15")

        # ═══════════════════════════════════════════════════════════════════
        # 7. VP LEVEL RETEST BONUS (max 25 points)
        # If VAL/POC was retested and rejected BEFORE entry = confirmation
        # ═══════════════════════════════════════════════════════════════════

        pullback_completed = False

        if retest_info:
            # VAL Retest with Rejection = Strong support confirmation
            if retest_info.get('val_retested') and retest_info.get('val_retest_rejected'):
                score += 20
                pullback_completed = True
                details.append("VAL RETESTED & REJECTED ✓ (support confirmed) +20")

                # Extra bonus if OB confluence at retest
                if retest_info.get('ob_confluence'):
                    ob_tf = retest_info.get('ob_confluence_tf', 'OB')
                    score += 10
                    details.append(f"VAL + OB {ob_tf} CONFLUENCE ✓ (ultra-strong) +10")

            # POC Retest with Rejection
            elif retest_info.get('poc_retested') and retest_info.get('poc_retest_rejected'):
                score += 15
                pullback_completed = True
                details.append("POC RETESTED & REJECTED ✓ (support confirmed) +15")

                if retest_info.get('ob_confluence'):
                    ob_tf = retest_info.get('ob_confluence_tf', 'OB')
                    score += 10
                    details.append(f"POC + OB {ob_tf} CONFLUENCE ✓ +10")

            # VAH Retest (pullback from above)
            elif retest_info.get('vah_retested') and retest_info.get('vah_retest_rejected'):
                score += 10
                pullback_completed = True
                details.append("VAH RETESTED ✓ (pullback completed) +10")

            # HVN Retest
            elif retest_info.get('hvn_retested'):
                score += 10
                pullback_completed = True
                hvn_level = retest_info.get('hvn_retest_level', 0)
                details.append(f"HVN RETESTED ✓ at {hvn_level:.6f} +10")

        # Update recommendations based on pullback status
        if pullback_completed:
            # Remove "waiting for pullback" recommendations since it already happened
            recommendations = [r for r in recommendations if 'pullback' not in r.lower() and 'waiting' not in r.lower()]

            # Add positive confirmation
            if retest_info.get('ob_confluence'):
                recommendations.insert(0, f"STRONG: Pullback to {retest_info.get('pullback_level', 'VP level')} + OB {retest_info.get('ob_confluence_tf', '')} confluence ✓")
            else:
                recommendations.insert(0, f"Pullback to {retest_info.get('pullback_level', 'VP level')} completed ✓")
        else:
            # No pullback yet - suggest waiting
            if self.is_above_vah(entry_price, vp_data):
                if 'pullback' not in ' '.join(recommendations).lower():
                    recommendations.append("Consider waiting for pullback to VAH")

        # ═══════════════════════════════════════════════════════════════════
        # FINAL SCORE AND GRADE
        # ═══════════════════════════════════════════════════════════════════

        final_score = max(0, min(100, score))

        if final_score >= 80:
            grade = 'A+'
        elif final_score >= 65:
            grade = 'A'
        elif final_score >= 50:
            grade = 'B+'
        elif final_score >= 35:
            grade = 'B'
        elif final_score >= 20:
            grade = 'C'
        else:
            grade = 'D'

        return {
            'vp_score': final_score,
            'vp_grade': grade,
            'vp_details': details,
            'vp_recommendations': recommendations,
            'vp_sl_optimized': vp_sl_optimized,
            'vp_tp_suggestions': tp_suggestions,
            'vp_poc': poc,
            'vp_vah': vah,
            'vp_val': val,
            'vp_position': self.get_position_in_va(entry_price, vp_data),
            'vp_pullback_completed': pullback_completed,
            'vp_retest_info': retest_info
        }

    def get_vp_grade(self, score: int) -> str:
        """Convert VP score to letter grade."""
        if score >= 80:
            return 'A+'
        elif score >= 65:
            return 'A'
        elif score >= 50:
            return 'B+'
        elif score >= 35:
            return 'B'
        elif score >= 20:
            return 'C'
        else:
            return 'D'


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_volume_profile_for_alert(df_1h: pd.DataFrame, df_4h: pd.DataFrame,
                                        entry_price: float, sl_price: float,
                                        tp1_price: float, config: dict,
                                        ob_zone: dict = None) -> Dict:
    """
    Convenience function to calculate VP analysis for an alert.

    Args:
        df_1h: 1H OHLCV DataFrame
        df_4h: 4H OHLCV DataFrame
        entry_price: Planned entry price
        sl_price: Stop loss price
        tp1_price: Take profit 1 price
        config: VP configuration
        ob_zone: Optional Order Block zone

    Returns:
        Complete VP analysis dict
    """
    analyzer = VolumeProfileAnalyzer(config)

    # Calculate VP for both timeframes
    vp_1h = analyzer.calculate(df_1h, lookback=config.get('VP_LOOKBACK_1H', 100))
    vp_4h = analyzer.calculate(df_4h, lookback=config.get('VP_LOOKBACK_4H', 50))

    # Get comprehensive score
    result = analyzer.calculate_vp_score(
        entry_price=entry_price,
        sl_price=sl_price,
        tp1_price=tp1_price,
        vp_data=vp_1h,
        vp_4h_data=vp_4h,
        ob_zone=ob_zone
    )

    # Add raw VP data
    result['vp_1h_data'] = {
        'poc': vp_1h.get('poc'),
        'vah': vp_1h.get('vah'),
        'val': vp_1h.get('val'),
        'hvn_levels': vp_1h.get('hvn_levels', [])[:5],  # Top 5
        'lvn_levels': vp_1h.get('lvn_levels', [])[:5],
    }

    result['vp_4h_data'] = {
        'poc': vp_4h.get('poc'),
        'vah': vp_4h.get('vah'),
        'val': vp_4h.get('val'),
        'hvn_levels': vp_4h.get('hvn_levels', [])[:5],
        'lvn_levels': vp_4h.get('lvn_levels', [])[:5],
    }

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULT VP CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_VP_CONFIG = {
    # Enabled flag
    'VP_ENABLED': True,

    # Core parameters
    'VP_NUM_BINS': 50,
    'VP_VA_PCT': 70,
    'VP_LOOKBACK_1H': 100,
    'VP_LOOKBACK_4H': 50,

    # Thresholds
    'VP_HVN_THRESHOLD': 1.5,
    'VP_LVN_THRESHOLD': 0.5,

    # Tolerances
    'VP_POC_TOLERANCE_PCT': 0.5,
    'VP_HVN_PROXIMITY_PCT': 1.0,

    # Scoring
    'VP_ENTRY_AT_POC_BONUS': 20,
    'VP_ENTRY_AT_VAL_BONUS': 15,
    'VP_SL_BELOW_HVN_BONUS': 20,
    'VP_TP_AT_VAH_BONUS': 15,
    'VP_LVN_PATH_BONUS': 15,
    'VP_OB_HVN_CONFLUENCE_BONUS': 15,

    # Minimum scores
    'VP_MIN_SCORE_V1': 20,
    'VP_MIN_SCORE_V3': 30,
    'VP_MIN_SCORE_V4': 35,
}
