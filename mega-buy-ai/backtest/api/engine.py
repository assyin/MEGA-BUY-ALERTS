#!/usr/bin/env python3
"""
MEGA BUY Backtest Engine
Processes pairs and stores results in database
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
import time
from typing import List, Dict, Optional
import sys
import os

# Add parent path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import (
    BacktestRun, Alert, Trade,
    SessionLocal, init_db
)

# Volume Profile Analyzer
from api.volume_profile import VolumeProfileAnalyzer, calculate_volume_profile_for_alert


def convert_to_json_serializable(obj):
    """Convert numpy types and pandas Timestamps to JSON serializable Python types"""
    import numpy as np
    import pandas as pd
    from datetime import datetime
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(v) for v in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj) if not np.isnan(obj) else None
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION - Setup complet 1H Trendline Break
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {
    # Trendline
    'TL_SWING_MAJOR': 50,
    'TL_SWING_LOCAL': 10,
    'TL_MIN_BARS': 3,
    'USE_MULTI_LEVEL_TL': True,
    'TL_SELECTION_STRATEGY': 'closest',
    'MAX_TL_DISTANCE_PCT': 100.0,
    'MAX_TL_BREAK_DELAY_HOURS': 72,
    'DATA_WARMUP_BARS': 1500,          # Warmup bars for historical data (1500 = ~62 days for 1H)

    # Anti-False Breaks Filter (rejects TL with too many prior false breaks)
    # A "false break" = price closes ABOVE TL then falls BELOW again
    'TL_ANTI_FALSE_BREAKS_ENABLED': False,  # Disabled to recover more trades
    'TL_MAX_PRIOR_BREAKS': 3,              # Max prior false breaks allowed (increased for long-range TLs)
    'TL_BREAK_CONFIRM_BARS': 2,            # Bars price must stay above TL to count as real break

    # Entry distance
    'MAX_BREAK_DIFF_PCT': 20.0,

    # 15m filter
    'REJECT_15M_ALONE': True,
    'COMBO_TIME_WINDOW_HOURS': 2,

    # PP_buy filter (Pivot Point SuperTrend Buy)
    'REQUIRE_PP_BUY': False,                # Disabled to recover more trades

    # EMA
    'EMA100_PERIOD': 100,
    'EMA20_PERIOD': 20,

    # Ichimoku Cloud - STANDARD parameters (matches TradingView)
    # See: mega-buy-ai/docs/ichimoku-indicateur.md
    'ICHIMOKU_TENKAN': 9,
    'ICHIMOKU_KIJUN': 26,
    'ICHIMOKU_SENKOU_B': 52,
    'ICHIMOKU_DISPLACEMENT': 26,

    # CHoCH/BOS Detection - Swing High parameters
    'SWING_HIGH_LEFT': 5,   # Bars to check on left side
    'SWING_HIGH_RIGHT': 3,  # Bars to check on right side

    # P&L
    'SL_PCT': 5.0,
    'TRAILING_PCT': 10.0,
    'TRAILING_ACTIVATION_PCT': 15.0,  # Same as TP1
    'TP1_PCT': 15.0,
    'TP2_PCT': 50.0,

    # Break-Even Strategy
    'BE_ENABLED': True,              # Enable Break-Even at X%
    'BE_ACTIVATION_PCT': 4.0,        # Move SL to BE after +4% (was 10%)
    'BE_OFFSET_PCT': 0.5,            # Small profit offset (+0.5% above entry)

    # MEGA BUY params
    'RSI_LENGTH': 14,
    'RSI_MIN_MOVE_BUY': 12,
    'DMI_LENGTH': 14,
    'DMI_ADX_SMOOTH': 14,
    'DMI_MIN_MOVE_PLUS': 10,
    'AST_FACTOR': 3.0,
    'AST_PERIOD': 10,
    'STOCH_LENGTH': 50,
    'STOCH_FAST': 50,
    'STOCH_SLOW': 200,
    'COMBO_WINDOW': 3,
    'COMBO_MAX_MOVE': 15,

    # Other
    'AV_ATR_LEN': 14,
    'AV_ATR_SMOOTH': 10,
    'AV_ATR_THRESHOLD': 1.2,
    'AV_VOL_LEN': 20,
    'AV_VOL_THRESHOLD': 1.5,
    'AV_MIN_MOVE': 250.0,
    'LB_SPIKE_THRESH': 6.0,
    'EC_RSI_PERIOD': 50,
    'EC_SLOW_MA_PERIOD': 50,
    'EC_MIN_MOVE_RSI': 4.0,
    'EC_MIN_MOVE_SLOW': 1.5,

    # Fibonacci Bonus Filter
    'FIB_ENABLED': True,             # Enable Fibonacci level check
    'FIB_LEVEL': 0.382,              # 38.2% retracement level
    'FIB_SWING_LOOKBACK': 50,        # Bars to look back for swing high/low on 4H
    'FIB_MIN_SWING_RANGE_PCT': 5.0,  # Min % range between swing high/low

    # Order Block (SMC) Bonus Filter
    'OB_ENABLED': True,              # Enable Order Block detection
    'OB_LOOKBACK': 100,              # Bars to look back for Order Blocks
    'OB_MIN_IMPULSE_PCT': 2.0,       # Min % move for impulsive move
    'OB_MIN_IMPULSE_CANDLES': 3,     # Min consecutive candles for impulse
    'OB_PROXIMITY_PCT': 2.0,         # Max % distance from entry to OB zone
    'OB_MAX_AGE_BARS': 200,          # OB validity (bars since creation)
    'OB_REQUIRE_UNMITIGATED': False,  # False = count mitigated OBs too (zones still relevant)

    # BTC Correlation Bonus Filter
    'BTC_CORR_ENABLED': True,        # Enable BTC correlation check
    'BTC_EMA_SHORT': 20,             # Short EMA period for BTC trend
    'BTC_EMA_LONG': 50,              # Long EMA period for BTC trend
    'BTC_RSI_PERIOD': 14,            # RSI period for BTC
    'BTC_RSI_BULLISH': 50,           # RSI above this = bullish

    # ETH Correlation Bonus Filter
    'ETH_CORR_ENABLED': True,        # Enable ETH correlation check
    'ETH_EMA_SHORT': 20,             # Short EMA period for ETH trend
    'ETH_EMA_LONG': 50,              # Long EMA period for ETH trend
    'ETH_RSI_PERIOD': 14,            # RSI period for ETH
    'ETH_RSI_BULLISH': 50,           # RSI above this = bullish

    # Fair Value Gap (FVG) Bonus Filter
    'FVG_ENABLED': True,             # Enable FVG detection
    'FVG_LOOKBACK': 50,              # Bars to look back for FVGs
    'FVG_MIN_GAP_PCT': 0.3,          # Min gap size as % of price
    'FVG_PROXIMITY_PCT': 3.0,        # Max % distance from entry to FVG zone
    'FVG_MAX_FILLED_PCT': 80,        # Max % filled (exclude fully filled FVGs)

    # Volume Spike Bonus Filter
    'VOL_SPIKE_ENABLED': True,       # Enable volume spike detection
    'VOL_AVG_PERIOD': 20,            # Period for average volume calculation
    'VOL_SPIKE_THRESHOLD': 2.0,      # Multiplier for spike detection (2x = HIGH)
    'VOL_VERY_HIGH_THRESHOLD': 3.0,  # Multiplier for very high volume (3x = VERY_HIGH)

    # RSI Multi-TF Alignment Bonus Filter
    'RSI_MTF_ENABLED': True,         # Enable RSI multi-TF alignment check
    'RSI_MTF_THRESHOLD': 50,         # RSI above this on each TF = bullish
    'RSI_MTF_PERIOD': 14,            # RSI period for all TFs

    # ADX Trend Strength Bonus Filter
    'ADX_ENABLED': True,             # Enable ADX trend strength check
    'ADX_PERIOD': 14,                # ADX period
    'ADX_STRONG_THRESHOLD': 25,      # ADX above this = STRONG trend (bonus)
    'ADX_MODERATE_THRESHOLD': 20,    # ADX above this = MODERATE trend

    # MACD Momentum Bonus Filter
    'MACD_ENABLED': True,            # Enable MACD momentum check
    'MACD_FAST': 12,                 # Fast EMA period
    'MACD_SLOW': 26,                 # Slow EMA period
    'MACD_SIGNAL': 9,                # Signal line EMA period

    # Bollinger Squeeze Bonus Filter
    'BB_SQUEEZE_ENABLED': True,      # Enable Bollinger squeeze detection
    'BB_PERIOD': 20,                 # Bollinger Bands period
    'BB_STD_DEV': 2.0,               # Standard deviation multiplier
    'BB_SQUEEZE_THRESHOLD': 4.0,     # Band width % below this = squeeze
    'BB_SQUEEZE_LOOKBACK': 20,       # Bars to check for squeeze

    # Stochastic RSI Bonus Filter
    'STOCH_RSI_ENABLED': True,       # Enable Stochastic RSI check
    'STOCH_RSI_PERIOD': 14,          # RSI period
    'STOCH_RSI_STOCH_PERIOD': 14,    # Stochastic period
    'STOCH_RSI_K_SMOOTH': 3,         # %K smoothing
    'STOCH_RSI_D_SMOOTH': 3,         # %D smoothing (signal line)
    'STOCH_RSI_OVERSOLD': 20,        # Oversold threshold
    'STOCH_RSI_OVERBOUGHT': 80,      # Overbought threshold

    # EMA Stack Bonus Filter
    'EMA_STACK_ENABLED': True,       # Enable EMA stack check
    'EMA_STACK_8': 8,                # Short EMA period
    'EMA_STACK_21': 21,              # Medium-short EMA period
    'EMA_STACK_50': 50,              # Medium EMA period
    'EMA_STACK_100': 100,            # Long EMA period

    # ═══════════════════════════════════════════════════════════════════════════════
    # V3 GOLDEN BOX RETEST STRATEGY
    # Entry via limit order at Box High, wait for price retest
    # ═══════════════════════════════════════════════════════════════════════════════
    'V3_ENABLED': True,                    # Enable V3 Golden Box Retest strategy
    'V3_REQUIRE_TL_BREAK': False,          # Disabled: TL break not mandatory for V3 (was causing too many rejections)
    'V3_ENTRY_MARGIN_PCT': 0.2,            # Entry at Box High + 0.2% (limit order)
    'V3_SL_MARGIN_PCT': 1.0,               # SL at Box Low - 1%
    'V3_TIMEOUT_HOURS': 48,                # Cancel limit order if not filled in 48h
    'V3_MIN_RETEST_DISTANCE_PCT': 1.0,     # Min price drop % before retest is valid
    'V3_MAX_ENTRY_DELAY_HOURS': 72,        # Max hours after signal for valid entry

    # ═══════════════════════════════════════════════════════════════════════════════
    # V4 OPTIMIZED STRATEGY - Based on Backtest Analysis
    # All filters derived from real performance data analysis
    # Win Rate: 31.9% → 50.7% | P&L: +303% → +558%
    # ═══════════════════════════════════════════════════════════════════════════════
    'V4_ENABLED': True,                    # Enable V4 Optimized strategy

    # MANDATORY FILTER 1: V3 Quality Score >= 6
    # Analysis: V3 Quality 0-5 = 11.1% WR (-131% P&L) vs 6+ = 37.5% WR (+434% P&L)
    'V4_MIN_V3_QUALITY': 6,                # Minimum V3 Quality Score required

    # MANDATORY FILTER 2: TL Break Delay <= 72h
    # Analysis: TL Break >24h gives penalty but allowed up to 72h
    'V4_MAX_TL_BREAK_HOURS': 72,           # Maximum hours for TL break after signal (matches global)

    # MANDATORY FILTER 3: STC must include 1H
    # Analysis: STC 30m alone = 0% WR, STC 15m alone = 20.8% WR
    # Best: STC 30m+1h = 71.4% WR, STC 15m+1h = 41.7% WR
    'V4_STC_REQUIRE_1H': True,             # STC validation must include 1H timeframe
    'V4_STC_REJECT_PATTERNS': ['30m', '15m'],  # Reject these STC patterns (single TF without 1H)

    # MANDATORY FILTER 4: OB Score >= 50
    # Analysis: OB Score 1-49 = 0% WR (-26% P&L)
    'V4_MIN_OB_SCORE': 50,                 # Minimum Order Block Score required

    # OPTIMAL ENTRY TIMING: 24-48h after breakout
    # Analysis: 0-12h = 26.2% WR, 24-48h = 65.0% WR (BEST!)
    'V4_OPTIMAL_ENTRY_MIN_HOURS': 24,      # Minimum hours for optimal entry window
    'V4_OPTIMAL_ENTRY_MAX_HOURS': 48,      # Maximum hours for optimal entry window
    'V4_ENTRY_TIMING_BONUS': True,         # Give bonus score to trades in optimal window

    # TIMEFRAME PRIORITY: Prefer 1H signals
    # Analysis: 1H = 39.1% WR (+232% P&L) vs 30m = 29.2% vs 15m = 31.2%
    'V4_PREFER_1H_TF': True,               # Prioritize 1H timeframe signals
    'V4_1H_SCORE_BONUS': 10,               # Bonus points for 1H signals

    # BLACKLIST PAIRS: Exclude consistently losing pairs
    # Analysis: These pairs have 0% WR with multiple trades
    'V4_BLACKLIST_ENABLED': True,          # Enable pair blacklisting
    'V4_BLACKLIST_PAIRS': [
        'ETHFIUSDT',   # 0% WR, 9 losses, -39.58%
        'SOPHUSDT',    # 0% WR, 9 losses, -66.09%
        'PYTHUSDT',    # 0% WR, 6 losses, -25.68%
        'BONKUSDT',    # 0% WR, 4 losses, -15.66%
        'RAREUSDT',    # 0% WR, 4 losses, -14.67%
        'ARBUSDT',     # 0% WR, 4 losses, -18.10%
    ],

    # COMBO TIMEFRAME FILTER
    # Analysis: 15m+30m+1h combo = 20% WR (poor), 15m+1h = 66.7% WR (best combo)
    'V4_REJECT_BAD_COMBOS': True,          # Reject poor performing combos
    'V4_BAD_COMBOS': ['15m,30m,1h'],       # Combos to reject

    # ORDER BLOCK REQUIREMENTS
    # Analysis: OB_BOTH (1H+4H) = 34.8% WR, OB_RETESTED = 33.6% WR
    'V4_REQUIRE_OB_BOTH': False,           # Require both 1H and 4H OB (optional, very strict)
    'V4_REQUIRE_OB_RETESTED': False,       # Require OB to be retested (optional)
    'V4_OB_RETEST_BONUS': 15,              # Bonus points if OB is retested

    # ═══════════════════════════════════════════════════════════════════════════════
    # VOLUME PROFILE ANALYSIS
    # Identifies key price levels based on volume distribution
    # POC = Point of Control, VAH/VAL = Value Area High/Low
    # HVN = High Volume Nodes (support/resistance), LVN = Low Volume Nodes (breakout zones)
    # ═══════════════════════════════════════════════════════════════════════════════
    'VP_ENABLED': True,                    # Enable Volume Profile analysis

    # Core parameters
    'VP_NUM_BINS': 50,                     # Number of price bins for VP calculation
    'VP_VA_PCT': 70,                       # Value Area percentage (70% of volume)
    'VP_LOOKBACK_1H': 100,                 # 1H candles to include in VP
    'VP_LOOKBACK_4H': 50,                  # 4H candles to include in VP

    # Detection thresholds
    'VP_HVN_THRESHOLD': 1.5,               # Volume above avg*1.5 = HVN
    'VP_LVN_THRESHOLD': 0.5,               # Volume below avg*0.5 = LVN

    # Tolerances for level matching
    'VP_POC_TOLERANCE_PCT': 0.5,           # Price within 0.5% of POC = "at POC"
    'VP_HVN_PROXIMITY_PCT': 1.0,           # Price within 1% of HVN = "near HVN"

    # Scoring bonuses
    'VP_ENTRY_AT_POC_BONUS': 20,           # Entry at POC = +20 points
    'VP_ENTRY_AT_VAL_BONUS': 15,           # Entry at VAL = +15 points
    'VP_SL_BELOW_HVN_BONUS': 20,           # SL protected by HVN = +20 points
    'VP_TP_AT_VAH_BONUS': 15,              # TP aligns with VAH = +15 points
    'VP_LVN_PATH_BONUS': 15,               # LVN between entry and TP = +15 points
    'VP_OB_HVN_CONFLUENCE_BONUS': 15,      # OB + HVN confluence = +15 points

    # Minimum scores by strategy
    'VP_MIN_SCORE_V1': 20,                 # Min VP score for V1 (bonus only)
    'VP_MIN_SCORE_V3': 30,                 # Min VP score for V3 (bonus only)
    'VP_MIN_SCORE_V4': 35,                 # Min VP score for V4 (filter)

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 STRATEGY - V4 + VP TRAJECTORY FILTER
    # Based on deep analysis: Price below VA without bounce = weak setup
    # Key insight: VAL retest rejection (bounce) is the confirmation signal
    # Win Rate improvement: +7-11% by filtering weak VP setups
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_ENABLED': True,                    # Enable V5 (V4 + VP Filter)

    # MANDATORY FILTER: VP Position/Trajectory Analysis
    # If VAL retest REJECTED (bounce) → PASS (even if price was below VA)
    # If price < VAL AND no bounce → REJECT
    # If >60% time below VA AND no bounce → REJECT
    'V5_VP_FILTER_ENABLED': False,          # Disabled to recover more trades
    'V5_REQUIRE_VAL_BOUNCE': True,         # Require VAL retest rejection if below VA
    'V5_MAX_PCT_BELOW_VA': 60.0,           # Max % of time price can be below VA (48h lookback)
    'V5_VP_LOOKBACK_HOURS': 48,            # Hours to analyze price trajectory

    # VP Position Thresholds
    'V5_BELOW_VAL_THRESHOLD': -0.5,        # Alert price X% below VAL = "below VA"
    'V5_ABOVE_VAH_THRESHOLD': 0.5,         # Alert price X% above VAH = "above VA"

    # Scoring bonuses for V5
    'V5_VAL_BOUNCE_BONUS': 15,             # Bonus if VAL retest was rejected (bounce)
    'V5_POC_BOUNCE_BONUS': 10,             # Bonus if POC retest was rejected (bounce)
    'V5_STRONG_TRAJECTORY_BONUS': 10,      # Bonus if <20% time below VA

    # V5 DEEP BELOW VAL FILTER (main rejection criteria)
    'V5_MAX_BELOW_VAL_PCT': -5.0,          # Max % price can go below VAL (-5 = 5% below)
                                            # Reject only if lowest_close < VAL * (1 + threshold/100)
                                            # Example: VAL=0.10, threshold=-5 → reject if close < 0.095

    # V5 VAL-BASED STOP LOSS (improved SL placement)
    'V5_USE_VAL_SL': True,                 # Use VAL as SL reference instead of Box Low
    'V5_VAL_SL_MARGIN_PCT': 3.0,           # SL at VAL - 3% (gives room below VAL support)
                                            # Example: VAL=0.10 → SL = 0.10 * 0.97 = 0.097

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 VP RETEST EXCEPTION (New Logic from INITUSDT Analysis)
    # Allow entries below VAL IF price came from VAH resistance and bounced at support
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_VP_RETEST_EXCEPTION_ENABLED': True,   # Enable VP Retest Exception
    'V5_VP_RETEST_LOOKBACK_BARS': 50,         # Bars 4H to check if price was above VAH
    'V5_VP_RETEST_SUPPORT_TOLERANCE_PCT': 5.0, # Max distance % to POC/VAL to be "at support"
    'V5_VP_RETEST_REJECTION_WICK_RATIO': 1.5, # Min lower_wick/body ratio for rejection candle
    'V5_VP_RETEST_REQUIRE_BULLISH': True,     # Rejection candle must be bullish (close > open)

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 CVD (Cumulative Volume Delta) FILTER
    # Reject trades when CVD shows weakness in both timeframes
    # CVD falling while price rising = bearish divergence = AVOID
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_CVD_FILTER_ENABLED': False,           # Disabled to recover more trades
    'V5_CVD_MIN_SCORE_1H': 30,                # Min CVD score on 1H (reject if below)
    'V5_CVD_MIN_SCORE_4H': 30,                # Min CVD score on 4H (reject if below)
    'V5_CVD_REJECT_BOTH_WEAK': True,          # Reject if BOTH 1H AND 4H are weak
    'V5_CVD_REJECT_BEARISH_DIV': True,        # Reject if bearish divergence detected

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 DMI SPREAD FILTER
    # Reject trades when DMI- > DMI+ at entry (bears in control)
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_DMI_SPREAD_FILTER_ENABLED': False,    # Disabled to recover more trades
    'V5_DMI_MIN_SPREAD': 0.0,                 # Min DMI spread (DI+ - DI-) required
                                               # 0 = DI+ must be >= DI- (bulls must control)
                                               # Negative spread = bears control = reject

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 WEAK BREAKOUT FILTER
    # Reject trades when breakout is too weak (price didn't move enough after TL break)
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_WEAK_BREAKOUT_FILTER_ENABLED': False, # Disabled to recover more trades
    'V5_MIN_BREAKOUT_DISTANCE_PCT': 2.0,      # Min % move after breakout before retest
                                               # If distance < 2% = weak breakout, reject

    # ═══════════════════════════════════════════════════════════════════════════════
    # V5 POWER SCORE FILTER
    # Reject trades with low Golden Box Power Score
    # ═══════════════════════════════════════════════════════════════════════════════
    'V5_POWER_SCORE_FILTER_ENABLED': False,   # Disabled to recover more trades
    'V5_MIN_POWER_SCORE': 50,                 # Min power score (Grade C minimum)
                                               # Grade F/D = weak setup, reject

    # ═══════════════════════════════════════════════════════════════════════════════
    # V6 STRATEGY - Timing + Momentum + Entry Limiter + Combined Scoring
    # Based on analysis of 184 trades with detailed timing/CVD/distance data
    # Key improvements:
    #   - 15m strict timing (WR 64% → 85%)
    #   - Distance filter (reject >20% = 0% WR)
    #   - Entry limiter (avoid FETUSDT -21% multi-entry)
    #   - Combined scoring (40+ = 75.5% WR)
    # ═══════════════════════════════════════════════════════════════════════════════
    'V6_ENABLED': True,

    # ─────────────────────────────────────────────────────────────────────────────
    # V6 TIMING FILTER
    # 15m is most sensitive to timing - strict rules
    # 30m is robust - flexible rules
    # 1h has warning zone (6-24h retest = 47.4% WR)
    # ─────────────────────────────────────────────────────────────────────────────
    'V6_TIMING_FILTER_ENABLED': True,

    # 15m Timing Rules (STRICT - analysis shows 15m needs fast timing)
    'V6_15M_MAX_RETEST_HOURS': 24,            # Retest > 24h = 41.7% WR → REJECT
    'V6_15M_MAX_ENTRY_HOURS': 48,             # Entry > 48h = 28.6% WR → REJECT
    'V6_15M_OPTIMAL_RETEST_HOURS': 6,         # 0-6h = 76.5% WR = FAST bonus

    # 30m Timing Rules (FLEXIBLE - 30m robust even with slow timing)
    'V6_30M_MAX_RETEST_HOURS': 72,            # 30m tolerates slow retest (66.7% WR)
    'V6_30M_MAX_ENTRY_HOURS': 72,
    'V6_30M_OPTIMAL_RETEST_HOURS': 6,         # 0-6h = 76.2% WR = FAST bonus

    # 1h Timing Rules (MEDIUM - has warning zone)
    'V6_1H_MAX_RETEST_HOURS': 72,
    'V6_1H_MAX_ENTRY_HOURS': 72,
    'V6_1H_WARN_RETEST_MIN': 6,               # 6-24h = 47.4% WR = WARNING zone
    'V6_1H_WARN_RETEST_MAX': 24,
    'V6_1H_OPTIMAL_RETEST_HOURS': 6,          # 0-6h = 72.2% WR = FAST bonus

    # Distance Filter (all TFs)
    'V6_MAX_DISTANCE_PCT': 20.0,              # Distance > 20% = 0% WR → REJECT
    'V6_OPTIMAL_DISTANCE_MIN': 5.0,           # 5-10% = optimal risk/reward
    'V6_OPTIMAL_DISTANCE_MAX': 10.0,

    # ─────────────────────────────────────────────────────────────────────────────
    # V6 MOMENTUM FILTER
    # Losers have low max profit potential (1-5%), insufficient to reach TP1
    # ─────────────────────────────────────────────────────────────────────────────
    'V6_MOMENTUM_FILTER_ENABLED': True,

    # Estimated Potential Filter
    'V6_MIN_ESTIMATED_POTENTIAL_PCT': 8.0,    # Min estimated potential 8%
    'V6_POTENTIAL_LOOKBACK_BARS': 50,         # Bars to estimate potential

    # RSI Momentum at entry
    'V6_RSI_MIN_AT_ENTRY': 40,                # RSI 1H min at entry (relaxed)
    'V6_RSI_BULLISH_THRESHOLD': 50,           # RSI > 50 = bonus

    # ADX Trend Strength at entry
    'V6_ADX_MIN_AT_ENTRY': 15,                # ADX min = trend present (relaxed)
    'V6_ADX_STRONG_THRESHOLD': 25,            # ADX > 25 = strong trend = bonus

    # DMI Spread
    'V6_DMI_MIN_SPREAD': 0.0,                 # DI+ - DI- minimum (relaxed, just for scoring)

    # ─────────────────────────────────────────────────────────────────────────────
    # V6 ENTRY LIMITER
    # FETUSDT lost -21% with 3 entries at same price level
    # ─────────────────────────────────────────────────────────────────────────────
    'V6_ENTRY_LIMITER_ENABLED': True,

    # Max entries per breakout zone
    'V6_MAX_ENTRIES_PER_ZONE': 2,             # Max 2 trades per zone ±2%
    'V6_ENTRY_ZONE_PCT': 2.0,                 # Zone = entry_price ± 2%

    # Cooldown between entries
    'V6_ENTRY_COOLDOWN_HOURS': 4,             # Min 4h between entries same pair
    'V6_ENTRY_COOLDOWN_AFTER_LOSS': 12,       # 12h cooldown after a loss

    # ─────────────────────────────────────────────────────────────────────────────
    # V6 COMBINED SCORING
    # Score 40+ = 75.5% WR, Score <10 = 53.8% WR → REJECT
    # ─────────────────────────────────────────────────────────────────────────────
    'V6_SCORING_ENABLED': True,
    'V6_MIN_SCORE': 10,                       # Score < 10 = REJECT (Grade F only)
    'V6_EXCELLENT_SCORE': 40,                 # Score 40+ = EXCELLENT (75.5% WR)
    'V6_GOOD_SCORE': 25,                      # Score 25-39 = GOOD (67.4% WR)

    # Timing Score Weights
    'V6_SCORE_RETEST_FAST': 15,               # Retest 0-6h
    'V6_SCORE_RETEST_MEDIUM': 5,              # Retest 6-24h
    'V6_SCORE_RETEST_SLOW': -10,              # Retest > 24h
    'V6_SCORE_ENTRY_FAST': 10,                # Entry 0-24h
    'V6_SCORE_ENTRY_MEDIUM': 0,               # Entry 24-48h
    'V6_SCORE_ENTRY_SLOW': -10,               # Entry > 48h

    # Distance Score Weights
    'V6_SCORE_DISTANCE_OPTIMAL': 15,          # Distance 5-10%
    'V6_SCORE_DISTANCE_SHORT': 5,             # Distance 0-5%
    'V6_SCORE_DISTANCE_LONG': -5,             # Distance 10-20%
    'V6_SCORE_DISTANCE_EXTREME': -20,         # Distance > 20%

    # Momentum Score Weights
    'V6_SCORE_RSI_BULLISH': 10,               # RSI > 50
    'V6_SCORE_ADX_STRONG': 10,                # ADX > 25
    'V6_SCORE_DMI_POSITIVE': 5,               # DI+ > DI-

    # CVD Score Weights
    'V6_SCORE_CVD_NO_DIV': 10,                # No bearish divergence
    'V6_SCORE_CVD_DIV_30M': 0,                # 30m tolerates divergence (71.4% WR)
    'V6_SCORE_CVD_DIV_OTHER': -10,            # 15m/1h divergence = malus

    # Timeframe Score Weights
    'V6_SCORE_TF_30M': 10,                    # 30m = best overall WR
    'V6_SCORE_TF_1H': 5,                      # 1h = good
    'V6_SCORE_TF_15M': 0,                     # 15m = riskier
}


# ═══════════════════════════════════════════════════════════════════════════════
# INDICATOR CALCULATIONS
# ═══════════════════════════════════════════════════════════════════════════════

def calc_ema(close, period):
    n = len(close)
    ema = np.zeros(n)
    if n < period:
        return ema
    mult = 2 / (period + 1)
    ema[period-1] = np.mean(close[:period])
    for i in range(period, n):
        ema[i] = close[i] * mult + ema[i-1] * (1 - mult)
    return ema


def calc_atr(high, low, close, period=14):
    n = len(close)
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = np.zeros(n)
    if period < n:
        atr[period] = np.mean(tr[1:period+1])
    for i in range(period+1, n):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


def calc_assyin_ichimoku_cloud(high, low, close, atr_period=14, min_senkou=50, max_senkou=120, displacement=26):
    """
    DEPRECATED: Do NOT use this function!

    This was a dynamic Ichimoku with ATR-based Senkou period (50-120).
    TradingView uses STANDARD Ichimoku with fixed parameters.

    Use calc_standard_ichimoku_cloud() instead!
    """
    import warnings
    warnings.warn("calc_assyin_ichimoku_cloud is DEPRECATED. Use calc_standard_ichimoku_cloud() instead!", DeprecationWarning)

    n = len(close)
    atr = calc_atr(high, low, close, atr_period)

    avg_atr = np.zeros(n)
    for i in range(100, n):
        avg_atr[i] = np.mean(atr[i-100:i])

    senkou_period = np.full(n, max_senkou)
    for i in range(100, n):
        if avg_atr[i] > 0:
            ratio = atr[i] / avg_atr[i]
            if ratio > 1.5:
                senkou_period[i] = min_senkou
            elif ratio < 0.5:
                senkou_period[i] = max_senkou
            else:
                senkou_period[i] = int(max_senkou - (ratio - 0.5) * (max_senkou - min_senkou))

    tenkan_period = 9
    tenkan_sen = np.zeros(n)
    for i in range(tenkan_period-1, n):
        tenkan_sen[i] = (np.max(high[i-tenkan_period+1:i+1]) + np.min(low[i-tenkan_period+1:i+1])) / 2

    kijun_period = 26
    kijun_sen = np.zeros(n)
    for i in range(kijun_period-1, n):
        kijun_sen[i] = (np.max(high[i-kijun_period+1:i+1]) + np.min(low[i-kijun_period+1:i+1])) / 2

    senkou_a = np.zeros(n)
    for i in range(kijun_period-1, n-displacement):
        senkou_a[i+displacement] = (tenkan_sen[i] + kijun_sen[i]) / 2

    senkou_b = np.zeros(n)
    for i in range(max_senkou, n - displacement):
        period = int(senkou_period[i])
        senkou_b[i + displacement] = (np.max(high[i-period+1:i+1]) + np.min(low[i-period+1:i+1])) / 2

    cloud_top = np.maximum(senkou_a, senkou_b)
    return cloud_top


def calc_standard_ichimoku_cloud(high, low, close, tenkan_period=9, kijun_period=26, senkou_b_period=52, displacement=26):
    """
    Standard Ichimoku Cloud calculation with FIXED parameters.
    Matches TradingView's 'Assyin# Ichimoku - Kijun / Senkou A & B' indicator.

    Parameters:
        tenkan_period: 9 (Tenkan-Sen / Conversion Line)
        kijun_period: 26 (Kijun-Sen / Base Line)
        senkou_b_period: 52 (Senkou-Span B)
        displacement: 26 (Cloud offset into future, but we need CURRENT cloud)

    Note: In PineScript, the cloud is plotted with offset=26 (future projection).
          But to check "price > cloud" at time T, we need the cloud value AT time T,
          which means we use the senkou calculated 26 bars AGO.
    """
    n = len(close)

    # Tenkan-Sen (Conversion Line) = (Highest High + Lowest Low) / 2 over 9 periods
    tenkan_sen = np.zeros(n)
    for i in range(tenkan_period - 1, n):
        tenkan_sen[i] = (np.max(high[i - tenkan_period + 1:i + 1]) + np.min(low[i - tenkan_period + 1:i + 1])) / 2

    # Kijun-Sen (Base Line) = (Highest High + Lowest Low) / 2 over 26 periods
    kijun_sen = np.zeros(n)
    for i in range(kijun_period - 1, n):
        kijun_sen[i] = (np.max(high[i - kijun_period + 1:i + 1]) + np.min(low[i - kijun_period + 1:i + 1])) / 2

    # Senkou-Span A = (Tenkan-Sen + Kijun-Sen) / 2, displaced forward
    # For checking "price at T > cloud at T", we need senkou_a from T-displacement bars ago
    senkou_a = np.zeros(n)
    for i in range(kijun_period - 1 + displacement, n):
        senkou_a[i] = (tenkan_sen[i - displacement] + kijun_sen[i - displacement]) / 2

    # Senkou-Span B = (Highest High + Lowest Low) / 2 over 52 periods, displaced forward
    senkou_b = np.zeros(n)
    for i in range(senkou_b_period - 1 + displacement, n):
        idx = i - displacement
        senkou_b[i] = (np.max(high[idx - senkou_b_period + 1:idx + 1]) + np.min(low[idx - senkou_b_period + 1:idx + 1])) / 2

    # Cloud Top = max(Senkou-Span A, Senkou-Span B)
    cloud_top = np.maximum(senkou_a, senkou_b)
    return cloud_top


def calc_fibonacci_levels(high, low, close, lookback=50, min_range_pct=5.0):
    """
    Calculate Fibonacci retracement levels based on major swing high/low.

    For a bullish setup (MEGA BUY), we find:
    - Swing Low: Lowest low in lookback period
    - Swing High: Highest high in lookback period

    Fibonacci levels are calculated from swing low to swing high:
    - 0% = Swing Low (start)
    - 23.6% = Low + 0.236 * range
    - 38.2% = Low + 0.382 * range
    - 50.0% = Low + 0.500 * range
    - 61.8% = Low + 0.618 * range
    - 78.6% = Low + 0.786 * range
    - 100% = Swing High (end)

    Returns:
        dict with fib levels and swing info, or None if range too small
    """
    n = len(close)
    if n < lookback:
        return None

    # Find swing high/low in lookback period (from end)
    recent_high = high[-lookback:]
    recent_low = low[-lookback:]

    swing_high = np.max(recent_high)
    swing_low = np.min(recent_low)

    swing_high_idx = n - lookback + np.argmax(recent_high)
    swing_low_idx = n - lookback + np.argmin(recent_low)

    # Calculate range
    fib_range = swing_high - swing_low
    range_pct = (fib_range / swing_low) * 100 if swing_low > 0 else 0

    # Check minimum range
    if range_pct < min_range_pct:
        return None

    # Calculate Fibonacci levels
    fib_levels = {
        '0.0': swing_low,
        '0.236': swing_low + 0.236 * fib_range,
        '0.382': swing_low + 0.382 * fib_range,
        '0.5': swing_low + 0.5 * fib_range,
        '0.618': swing_low + 0.618 * fib_range,
        '0.786': swing_low + 0.786 * fib_range,
        '1.0': swing_high,
    }

    return {
        'swing_high': swing_high,
        'swing_low': swing_low,
        'swing_high_idx': swing_high_idx,
        'swing_low_idx': swing_low_idx,
        'range': fib_range,
        'range_pct': range_pct,
        'levels': fib_levels,
        # Determine trend direction based on which swing came first
        'uptrend': swing_low_idx < swing_high_idx,  # Low before High = uptrend
    }


def check_fib_level_break(close_price, fib_data, level=0.382):
    """
    Check if close price breaks above a Fibonacci level.

    Args:
        close_price: Current close price
        fib_data: Dictionary from calc_fibonacci_levels()
        level: Fibonacci level to check (default 0.382)

    Returns:
        dict with break info or None if no fib data
    """
    if fib_data is None:
        return None

    level_key = str(level)
    if level_key not in fib_data['levels']:
        return None

    fib_price = fib_data['levels'][level_key]

    return {
        'level': level,
        'fib_price': fib_price,
        'close_price': close_price,
        'break': close_price > fib_price,
        'distance_pct': ((close_price - fib_price) / fib_price) * 100 if fib_price > 0 else 0,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ORDER BLOCK (SMC) DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_order_blocks(open_prices, high, low, close, datetimes, lookback=100,
                        min_impulse_pct=2.0, min_impulse_candles=3, max_age_bars=200,
                        check_mitigation_until=None):
    """
    Detect Order Blocks (SMC - Smart Money Concepts).

    A Bullish Order Block is the last bearish candle before an impulsive bullish move.
    The zone (high/low of that candle) acts as a demand zone where price tends to react.

    Args:
        open_prices: Array of open prices
        high: Array of high prices
        low: Array of low prices
        close: Array of close prices
        datetimes: Array of datetimes
        lookback: Bars to look back for Order Blocks
        min_impulse_pct: Minimum % move for impulsive move
        min_impulse_candles: Minimum consecutive candles for impulse
        max_age_bars: Maximum age in bars for valid OB
        check_mitigation_until: Only check mitigation up to this index (default: n-1)

    Returns:
        List of Order Block dictionaries, sorted by recency
    """
    n = len(close)
    if n < lookback:
        return []

    order_blocks = []

    # Scan for impulsive moves
    for i in range(min_impulse_candles + 1, min(lookback, n)):
        idx = n - 1 - i  # Work backwards from end

        if idx < min_impulse_candles:
            continue

        # Check for impulsive bullish move starting at idx
        # An impulsive move = multiple consecutive bullish candles with significant total move
        impulse_start = idx
        impulse_end = idx
        consecutive_bullish = 0

        for j in range(idx, min(idx + 15, n)):  # Check up to 15 candles
            if close[j] > open_prices[j]:  # Bullish candle
                consecutive_bullish += 1
                impulse_end = j
            else:
                if consecutive_bullish >= min_impulse_candles:
                    break
                consecutive_bullish = 0
                impulse_start = j + 1

        if consecutive_bullish < min_impulse_candles:
            continue

        # Calculate impulse move percentage
        if impulse_start > 0 and impulse_end < n:
            impulse_low = min(low[impulse_start:impulse_end + 1])
            impulse_high = max(high[impulse_start:impulse_end + 1])
            impulse_pct = ((impulse_high - impulse_low) / impulse_low) * 100

            if impulse_pct < min_impulse_pct:
                continue

            # Find the Order Block: last bearish candle before impulse
            ob_idx = None
            for k in range(impulse_start - 1, max(0, impulse_start - 10), -1):
                if close[k] < open_prices[k]:  # Bearish candle
                    ob_idx = k
                    break

            if ob_idx is None:
                continue

            # Check if OB is within max age
            age_bars = n - 1 - ob_idx
            if age_bars > max_age_bars:
                continue

            # Order Block zone
            ob_high = high[ob_idx]
            ob_low = low[ob_idx]
            ob_mid = (ob_high + ob_low) / 2

            # Check if OB has been mitigated (price returned to zone)
            # Only check up to check_mitigation_until index if provided
            mitigated = False
            mitigated_idx = None
            mitigation_end = check_mitigation_until if check_mitigation_until is not None else n
            for m in range(ob_idx + 1, mitigation_end):
                if low[m] <= ob_high:  # Price entered the OB zone
                    mitigated = True
                    mitigated_idx = m
                    break

            # Determine OB strength based on impulse
            if impulse_pct >= 5.0:
                strength = 'STRONG'
            elif impulse_pct >= 3.0:
                strength = 'MODERATE'
            else:
                strength = 'WEAK'

            order_blocks.append({
                'type': 'BULLISH',
                'idx': ob_idx,
                'datetime': datetimes[ob_idx] if ob_idx < len(datetimes) else None,
                'high': ob_high,
                'low': ob_low,
                'mid': ob_mid,
                'impulse_pct': impulse_pct,
                'impulse_candles': consecutive_bullish,
                'strength': strength,
                'age_bars': age_bars,
                'mitigated': mitigated,
                'mitigated_idx': mitigated_idx,
            })

    # Remove duplicates (same OB detected multiple times)
    seen_indices = set()
    unique_obs = []
    for ob in order_blocks:
        if ob['idx'] not in seen_indices:
            seen_indices.add(ob['idx'])
            unique_obs.append(ob)

    # Sort by recency (most recent first)
    unique_obs.sort(key=lambda x: x['idx'], reverse=True)

    return unique_obs


def find_nearest_order_block(order_blocks, entry_price, proximity_pct=2.0, require_unmitigated=True):
    """
    Find the nearest valid Order Block to the entry price.

    Args:
        order_blocks: List of Order Blocks from detect_order_blocks()
        entry_price: Entry price to check proximity
        proximity_pct: Maximum % distance from entry to OB zone
        require_unmitigated: Only consider unmitigated OBs

    Returns:
        Dict with OB info and proximity, or None if no valid OB found
    """
    if not order_blocks:
        return None

    best_ob = None
    best_distance = float('inf')

    for ob in order_blocks:
        # Skip mitigated OBs if required
        if require_unmitigated and ob['mitigated']:
            continue

        # Calculate distance from entry to OB zone
        if entry_price >= ob['low'] and entry_price <= ob['high']:
            # Entry is INSIDE the OB zone - perfect!
            distance_pct = 0
            position = 'INSIDE'
        elif entry_price > ob['high']:
            # Entry is ABOVE OB zone
            distance_pct = ((entry_price - ob['high']) / ob['high']) * 100
            position = 'ABOVE'
        else:
            # Entry is BELOW OB zone (less ideal for bullish OB)
            distance_pct = ((ob['low'] - entry_price) / entry_price) * 100
            position = 'BELOW'

        # Check if within proximity
        if distance_pct <= proximity_pct and distance_pct < best_distance:
            best_distance = distance_pct
            best_ob = {
                # Flattened OB data for easy access
                'zone_high': ob['high'],
                'zone_low': ob['low'],
                'datetime': ob['datetime'],
                'strength': ob['strength'],
                'impulse_pct': ob['impulse_pct'],
                'age_bars': ob['age_bars'],
                'mitigated': ob['mitigated'],
                # Analysis results
                'distance_pct': distance_pct,
                'position': position,
                'is_inside': position == 'INSIDE',
                'is_valid': True,
                # Original OB for reference
                'ob': ob,
            }

    return best_ob


def detect_fair_value_gaps(high, low, close, open_prices, timestamps, lookback=50, min_gap_pct=0.3):
    """
    Detect bullish Fair Value Gaps (FVG) in OHLC data.

    A bullish FVG occurs when:
    - candle[i-1].high < candle[i+1].low (gap between high of bar before and low of bar after)
    - The middle candle (i) is typically a large bullish candle

    Args:
        high, low, close, open_prices: OHLC arrays
        timestamps: Array of timestamps
        lookback: Number of bars to look back for FVGs
        min_gap_pct: Minimum gap size as % of price

    Returns:
        List of FVG dicts with zone info
    """
    fvgs = []
    n = len(close)

    # We need at least 3 bars
    if n < 3:
        return fvgs

    # Start from lookback bars ago (or beginning if not enough data)
    start_idx = max(2, n - lookback)

    for i in range(start_idx, n - 1):
        # Check for bullish FVG: high[i-1] < low[i+1]
        prev_high = high[i - 1]
        next_low = low[i + 1]

        if prev_high < next_low:
            # Found a bullish FVG
            fvg_low = prev_high  # Bottom of gap
            fvg_high = next_low   # Top of gap
            mid_price = (fvg_low + fvg_high) / 2

            # Calculate gap size as % of price
            gap_size_pct = ((fvg_high - fvg_low) / mid_price) * 100

            # Filter out tiny gaps
            if gap_size_pct < min_gap_pct:
                continue

            # Check if FVG has been filled (price came back into the zone)
            filled_pct = 0
            for j in range(i + 2, n):
                if low[j] <= fvg_high:
                    # Price entered the FVG zone
                    fill_depth = fvg_high - max(low[j], fvg_low)
                    filled_pct = (fill_depth / (fvg_high - fvg_low)) * 100
                    filled_pct = min(100, max(0, filled_pct))
                    break

            fvgs.append({
                'datetime': timestamps[i],
                'bar_index': i,
                'high': fvg_high,
                'low': fvg_low,
                'size_pct': gap_size_pct,
                'filled_pct': filled_pct,
                'age_bars': n - 1 - i,
                'mid_price': mid_price,
            })

    return fvgs


def find_nearest_fvg(fvgs, entry_price, entry_idx, proximity_pct=3.0, max_filled_pct=80):
    """
    Find the nearest valid Fair Value Gap to the entry price.

    Args:
        fvgs: List of FVGs from detect_fair_value_gaps()
        entry_price: Entry price to check proximity
        entry_idx: Bar index of entry
        proximity_pct: Maximum % distance from entry to FVG zone
        max_filled_pct: Maximum % filled (exclude fully filled FVGs)

    Returns:
        Dict with FVG info and proximity, or None if no valid FVG found
    """
    if not fvgs:
        return None

    best_fvg = None
    best_distance = float('inf')

    for fvg in fvgs:
        # Skip FVGs that were created after entry
        if fvg['bar_index'] >= entry_idx:
            continue

        # Skip mostly filled FVGs
        if fvg['filled_pct'] > max_filled_pct:
            continue

        # Calculate distance from entry to FVG zone
        if entry_price >= fvg['low'] and entry_price <= fvg['high']:
            # Entry is INSIDE the FVG zone - perfect!
            distance_pct = 0
            position = 'INSIDE'
        elif entry_price > fvg['high']:
            # Entry is ABOVE FVG zone
            distance_pct = ((entry_price - fvg['high']) / fvg['high']) * 100
            position = 'ABOVE'
        else:
            # Entry is BELOW FVG zone
            distance_pct = ((fvg['low'] - entry_price) / entry_price) * 100
            position = 'BELOW'

        # Check if within proximity
        if distance_pct <= proximity_pct and distance_pct < best_distance:
            best_distance = distance_pct
            best_fvg = {
                'zone_high': fvg['high'],
                'zone_low': fvg['low'],
                'datetime': fvg['datetime'],
                'size_pct': fvg['size_pct'],
                'filled_pct': fvg['filled_pct'],
                'age_bars': entry_idx - fvg['bar_index'],
                'distance_pct': distance_pct,
                'position': position,
                'is_inside': position == 'INSIDE',
                'is_valid': True,
            }

    return best_fvg


def analyze_volume_spike(volume, entry_idx, avg_period=20, spike_threshold=2.0, very_high_threshold=3.0):
    """
    Analyze volume spike at entry time.

    Volume is considered:
    - NORMAL: < 2x average
    - HIGH: >= 2x average (spike_threshold)
    - VERY_HIGH: >= 3x average (very_high_threshold)

    Returns dict with volume analysis.
    """
    if entry_idx < avg_period:
        return None

    # Calculate average volume over the lookback period
    vol_avg = np.mean(volume[entry_idx - avg_period:entry_idx])
    vol_current = volume[entry_idx]

    if vol_avg <= 0:
        return None

    vol_ratio = vol_current / vol_avg

    # Determine spike level
    if vol_ratio >= very_high_threshold:
        spike_level = 'VERY_HIGH'
        is_bonus = True
    elif vol_ratio >= spike_threshold:
        spike_level = 'HIGH'
        is_bonus = True
    else:
        spike_level = 'NORMAL'
        is_bonus = False

    return {
        'current': float(vol_current),
        'average': float(vol_avg),
        'ratio': float(vol_ratio),
        'spike_level': spike_level,
        'is_bonus': is_bonus,
    }


def analyze_rsi_mtf(rsi_1h, rsi_4h, rsi_daily, threshold=50):
    """
    Analyze RSI alignment across multiple timeframes.

    RSI > 50 on each timeframe = bullish momentum.
    All 3 aligned = strong bonus.

    Returns dict with RSI analysis.
    """
    bullish_count = 0

    # Check 1H
    rsi_1h_bullish = rsi_1h is not None and not np.isnan(rsi_1h) and rsi_1h > threshold
    if rsi_1h_bullish:
        bullish_count += 1

    # Check 4H
    rsi_4h_bullish = rsi_4h is not None and not np.isnan(rsi_4h) and rsi_4h > threshold
    if rsi_4h_bullish:
        bullish_count += 1

    # Check Daily
    rsi_daily_bullish = rsi_daily is not None and not np.isnan(rsi_daily) and rsi_daily > threshold
    if rsi_daily_bullish:
        bullish_count += 1

    # Determine trend
    if bullish_count == 3:
        mtf_trend = 'BULLISH'
        is_bonus = True
    elif bullish_count == 0:
        mtf_trend = 'BEARISH'
        is_bonus = False
    else:
        mtf_trend = 'MIXED'
        is_bonus = False

    return {
        'rsi_1h': float(rsi_1h) if rsi_1h is not None and not np.isnan(rsi_1h) else None,
        'rsi_4h': float(rsi_4h) if rsi_4h is not None and not np.isnan(rsi_4h) else None,
        'rsi_daily': float(rsi_daily) if rsi_daily is not None and not np.isnan(rsi_daily) else None,
        'aligned_count': bullish_count,
        'mtf_trend': mtf_trend,
        'is_bonus': is_bonus,
    }


def calc_adx(high, low, close, period=14):
    """
    Calculate ADX (Average Directional Index) and +DI / -DI.

    ADX measures trend strength:
    - ADX > 25 = Strong trend (bonus)
    - ADX 20-25 = Moderate trend
    - ADX < 20 = Weak/Range (no trade)

    +DI > -DI = Bullish trend
    +DI < -DI = Bearish trend
    """
    n = len(close)
    if n < period + 1:
        return np.zeros(n), np.zeros(n), np.zeros(n)

    # Calculate True Range
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)

    for i in range(1, n):
        high_diff = high[i] - high[i-1]
        low_diff = low[i-1] - low[i]

        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )

        # +DM: If high change > low change and high change > 0
        plus_dm[i] = high_diff if high_diff > low_diff and high_diff > 0 else 0
        # -DM: If low change > high change and low change > 0
        minus_dm[i] = low_diff if low_diff > high_diff and low_diff > 0 else 0

    # Smoothed TR, +DM, -DM using Wilder's smoothing (same as EMA with alpha=1/period)
    atr = np.zeros(n)
    smoothed_plus_dm = np.zeros(n)
    smoothed_minus_dm = np.zeros(n)

    # Initial values
    if period < n:
        atr[period] = np.sum(tr[1:period+1])
        smoothed_plus_dm[period] = np.sum(plus_dm[1:period+1])
        smoothed_minus_dm[period] = np.sum(minus_dm[1:period+1])

    # Wilder smoothing
    for i in range(period + 1, n):
        atr[i] = atr[i-1] - atr[i-1] / period + tr[i]
        smoothed_plus_dm[i] = smoothed_plus_dm[i-1] - smoothed_plus_dm[i-1] / period + plus_dm[i]
        smoothed_minus_dm[i] = smoothed_minus_dm[i-1] - smoothed_minus_dm[i-1] / period + minus_dm[i]

    # Calculate +DI and -DI
    plus_di = np.zeros(n)
    minus_di = np.zeros(n)

    for i in range(period, n):
        if atr[i] > 0:
            plus_di[i] = 100 * smoothed_plus_dm[i] / atr[i]
            minus_di[i] = 100 * smoothed_minus_dm[i] / atr[i]

    # Calculate DX
    dx = np.zeros(n)
    for i in range(period, n):
        di_sum = plus_di[i] + minus_di[i]
        if di_sum > 0:
            dx[i] = 100 * abs(plus_di[i] - minus_di[i]) / di_sum

    # Calculate ADX (smoothed DX)
    adx = np.zeros(n)
    if period * 2 <= n:
        adx[period * 2 - 1] = np.mean(dx[period:period * 2])

    for i in range(period * 2, n):
        adx[i] = (adx[i-1] * (period - 1) + dx[i]) / period

    return adx, plus_di, minus_di


def analyze_adx_trend(high, low, close, entry_idx, period=14, strong_threshold=25, moderate_threshold=20):
    """
    Analyze ADX trend strength at entry time.

    ADX > 25 = STRONG trend (bonus)
    ADX 20-25 = MODERATE trend
    ADX < 20 = WEAK/Range (no bonus)

    Additionally checks +DI > -DI for bullish confirmation.
    """
    if entry_idx < period * 2:
        return None

    adx, plus_di, minus_di = calc_adx(high, low, close, period)

    adx_value = adx[entry_idx]
    plus_di_value = plus_di[entry_idx]
    minus_di_value = minus_di[entry_idx]

    # Determine trend strength
    if adx_value >= strong_threshold:
        strength = 'STRONG'
        is_bonus = True
    elif adx_value >= moderate_threshold:
        strength = 'MODERATE'
        is_bonus = False
    else:
        strength = 'WEAK'
        is_bonus = False

    # For bonus, also require bullish confirmation (+DI > -DI)
    bullish = plus_di_value > minus_di_value
    if is_bonus and not bullish:
        is_bonus = False  # Strong trend but bearish, no bonus

    return {
        'adx': float(adx_value),
        'plus_di': float(plus_di_value),
        'minus_di': float(minus_di_value),
        'strength': strength,
        'bullish': bullish,
        'is_bonus': is_bonus,
    }


def calc_macd(close, fast_period=12, slow_period=26, signal_period=9):
    """
    Calculate MACD (Moving Average Convergence Divergence).

    Returns:
        macd_line: MACD line (fast EMA - slow EMA)
        signal_line: Signal line (EMA of MACD line)
        histogram: MACD histogram (MACD line - Signal line)
    """
    n = len(close)
    if n < slow_period + signal_period:
        return np.zeros(n), np.zeros(n), np.zeros(n)

    # Calculate EMAs
    fast_ema = calc_ema(close, fast_period)
    slow_ema = calc_ema(close, slow_period)

    # MACD Line = Fast EMA - Slow EMA
    macd_line = fast_ema - slow_ema

    # Signal Line = EMA of MACD Line
    signal_line = calc_ema(macd_line, signal_period)

    # Histogram = MACD Line - Signal Line
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def analyze_macd_momentum(close, entry_idx, fast_period=12, slow_period=26, signal_period=9):
    """
    Analyze MACD momentum at entry time.

    BONUS if:
    - Histogram > 0 (MACD above signal = bullish)
    - Histogram growing (current > previous = momentum increasing)
    """
    if entry_idx < slow_period + signal_period + 1:
        return None

    macd_line, signal_line, histogram = calc_macd(close, fast_period, slow_period, signal_period)

    hist_current = histogram[entry_idx]
    hist_previous = histogram[entry_idx - 1]

    # Check if histogram is positive and growing
    hist_positive = hist_current > 0
    hist_growing = hist_current > hist_previous

    # Determine trend
    if hist_positive and hist_growing:
        trend = 'BULLISH'
        is_bonus = True
    elif hist_positive:
        trend = 'BULLISH'
        is_bonus = False  # Positive but not growing
    elif hist_current < 0 and hist_current < hist_previous:
        trend = 'BEARISH'
        is_bonus = False
    else:
        trend = 'NEUTRAL'
        is_bonus = False

    return {
        'macd_line': float(macd_line[entry_idx]),
        'signal_line': float(signal_line[entry_idx]),
        'histogram': float(hist_current),
        'hist_growing': hist_growing,
        'trend': trend,
        'is_bonus': is_bonus,
    }


def calc_bollinger_bands(close, period=20, std_dev=2.0):
    """
    Calculate Bollinger Bands.

    Returns:
        upper: Upper band (SMA + std_dev * std)
        middle: Middle band (SMA)
        lower: Lower band (SMA - std_dev * std)
        width_pct: Band width as percentage of middle
    """
    n = len(close)
    upper = np.zeros(n)
    middle = np.zeros(n)
    lower = np.zeros(n)
    width_pct = np.zeros(n)

    for i in range(period - 1, n):
        window = close[i - period + 1:i + 1]
        sma = np.mean(window)
        std = np.std(window)

        middle[i] = sma
        upper[i] = sma + std_dev * std
        lower[i] = sma - std_dev * std

        if sma > 0:
            width_pct[i] = (upper[i] - lower[i]) / sma * 100

    return upper, middle, lower, width_pct


def analyze_bollinger_squeeze(close, entry_idx, period=20, std_dev=2.0, squeeze_threshold=4.0, lookback=20):
    """
    Analyze Bollinger Squeeze at entry time.

    A squeeze occurs when bands are tight (low volatility).
    BONUS if squeeze + bullish breakout (price > upper band or price > middle and expanding).
    """
    if entry_idx < period + lookback:
        return None

    upper, middle, lower, width_pct = calc_bollinger_bands(close, period, std_dev)

    # Current values
    current_width = width_pct[entry_idx]
    current_price = close[entry_idx]
    current_upper = upper[entry_idx]
    current_middle = middle[entry_idx]
    current_lower = lower[entry_idx]

    # Check for squeeze: current width is below threshold OR below recent average
    recent_widths = width_pct[entry_idx - lookback:entry_idx]
    avg_width = np.mean(recent_widths) if len(recent_widths) > 0 else current_width
    min_width = np.min(recent_widths) if len(recent_widths) > 0 else current_width

    # Squeeze detection: width is near historical minimum or below threshold
    is_squeeze = current_width <= squeeze_threshold or current_width <= min_width * 1.2

    # Breakout detection
    prev_price = close[entry_idx - 1]
    prev_width = width_pct[entry_idx - 1]

    # Bullish breakout: price above middle and bands expanding
    bands_expanding = current_width > prev_width
    price_above_middle = current_price > current_middle
    price_near_upper = current_price > current_upper * 0.98  # Within 2% of upper band

    if price_near_upper or (price_above_middle and bands_expanding):
        breakout = 'UP'
    elif current_price < current_lower * 1.02:
        breakout = 'DOWN'
    else:
        breakout = 'NONE'

    # Bonus: squeeze detected (recently or now) AND bullish breakout
    was_squeeze = any(w <= squeeze_threshold for w in recent_widths[-5:]) if len(recent_widths) >= 5 else is_squeeze
    is_bonus = (is_squeeze or was_squeeze) and breakout == 'UP'

    return {
        'upper': float(current_upper),
        'middle': float(current_middle),
        'lower': float(current_lower),
        'width_pct': float(current_width),
        'squeeze': is_squeeze or was_squeeze,
        'breakout': breakout,
        'is_bonus': is_bonus,
    }


def calc_stochastic_rsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    """
    Calculate Stochastic RSI.

    StochRSI = Stochastic(RSI)
    %K = Smoothed StochRSI
    %D = SMA of %K (signal line)
    """
    n = len(close)
    if n < rsi_period + stoch_period + k_smooth + d_smooth:
        return np.zeros(n), np.zeros(n)

    # Calculate RSI
    rsi = calc_rsi(close, rsi_period)

    # Calculate Stochastic of RSI
    stoch_rsi_raw = np.zeros(n)
    for i in range(stoch_period - 1 + rsi_period, n):
        rsi_window = rsi[i - stoch_period + 1:i + 1]
        rsi_min = np.min(rsi_window)
        rsi_max = np.max(rsi_window)
        if rsi_max - rsi_min > 0:
            stoch_rsi_raw[i] = (rsi[i] - rsi_min) / (rsi_max - rsi_min) * 100
        else:
            stoch_rsi_raw[i] = 50  # Default when no range

    # Smooth %K with SMA
    k_line = np.zeros(n)
    for i in range(k_smooth - 1, n):
        k_line[i] = np.mean(stoch_rsi_raw[i - k_smooth + 1:i + 1])

    # Calculate %D (SMA of %K)
    d_line = np.zeros(n)
    for i in range(d_smooth - 1, n):
        d_line[i] = np.mean(k_line[i - d_smooth + 1:i + 1])

    return k_line, d_line


def analyze_stochastic_rsi(close, entry_idx, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3, oversold=20, overbought=80):
    """
    Analyze Stochastic RSI at entry time.

    BONUS if:
    - K > D (bullish crossover)
    - AND currently in oversold zone (<20) OR recently was in oversold zone
    """
    min_required = rsi_period + stoch_period + k_smooth + d_smooth + 5
    if entry_idx < min_required:
        return None

    k_line, d_line = calc_stochastic_rsi(close, rsi_period, stoch_period, k_smooth, d_smooth)

    k_current = k_line[entry_idx]
    d_current = d_line[entry_idx]
    k_prev = k_line[entry_idx - 1]
    d_prev = d_line[entry_idx - 1]

    # Determine zone
    if k_current < oversold:
        zone = 'OVERSOLD'
    elif k_current > overbought:
        zone = 'OVERBOUGHT'
    else:
        zone = 'NEUTRAL'

    # Check for bullish crossover (K crosses above D)
    bullish_cross = k_current > d_current and k_prev <= d_prev
    bearish_cross = k_current < d_current and k_prev >= d_prev

    if k_current > d_current:
        cross = 'BULLISH'
    elif k_current < d_current:
        cross = 'BEARISH'
    else:
        cross = 'NONE'

    # Check if recently was in oversold zone (last 5 bars)
    was_oversold = any(k_line[i] < oversold for i in range(max(0, entry_idx - 5), entry_idx + 1))

    # Bonus: K > D AND (currently oversold OR recently oversold)
    is_bonus = k_current > d_current and was_oversold

    return {
        'k': float(k_current),
        'd': float(d_current),
        'zone': zone,
        'cross': cross,
        'bullish_cross': bullish_cross,
        'was_oversold': was_oversold,
        'is_bonus': is_bonus,
    }


def analyze_ema_stack(close, entry_idx, ema8_period=8, ema21_period=21, ema50_period=50, ema100_period=100):
    """
    Analyze EMA Stack at entry time.

    Perfect bullish stack: EMA8 > EMA21 > EMA50 > EMA100
    Price should also be above all EMAs for strongest signal.

    BONUS if all 4 EMAs are properly stacked (perfect bullish structure).
    """
    if entry_idx < ema100_period + 10:
        return None

    # Calculate all EMAs
    ema8 = calc_ema(close, ema8_period)
    ema21 = calc_ema(close, ema21_period)
    ema50 = calc_ema(close, ema50_period)
    ema100 = calc_ema(close, ema100_period)

    # Get current values
    ema8_val = ema8[entry_idx]
    ema21_val = ema21[entry_idx]
    ema50_val = ema50[entry_idx]
    ema100_val = ema100[entry_idx]
    price = close[entry_idx]

    # Count how many pairs are properly stacked
    stack_count = 0
    if ema8_val > ema21_val:
        stack_count += 1
    if ema21_val > ema50_val:
        stack_count += 1
    if ema50_val > ema100_val:
        stack_count += 1

    # Determine trend
    if stack_count == 3:
        trend = 'PERFECT'
        is_bonus = True
    elif stack_count >= 2:
        trend = 'PARTIAL'
        is_bonus = False
    elif stack_count == 0 and ema8_val < ema21_val < ema50_val < ema100_val:
        trend = 'INVERSE'
        is_bonus = False
    else:
        trend = 'MIXED'
        is_bonus = False

    # Extra confirmation: price above all EMAs
    price_above_all = price > ema8_val > ema21_val > ema50_val > ema100_val

    return {
        'ema8': float(ema8_val),
        'ema21': float(ema21_val),
        'ema50': float(ema50_val),
        'ema100': float(ema100_val),
        'stack_count': stack_count,
        'trend': trend,
        'price_above_all': price_above_all,
        'is_bonus': is_bonus,
    }


def analyze_btc_trend(btc_close, btc_high, btc_low, entry_idx, ema_short=20, ema_long=50, rsi_period=14, rsi_bullish=50):
    """
    Analyze BTC trend at entry time.

    BTC is considered BULLISH if:
    - Price > EMA20 (short-term trend)
    - Price > EMA50 (medium-term trend)
    - RSI > 50 (momentum positive)

    Returns dict with trend analysis.
    """
    if entry_idx < max(ema_short, ema_long, rsi_period + 1):
        return None

    # Calculate EMAs
    ema_short_vals = calc_ema(btc_close[:entry_idx + 1], ema_short)
    ema_long_vals = calc_ema(btc_close[:entry_idx + 1], ema_long)

    # Calculate RSI
    rsi_vals = calc_rsi(btc_close[:entry_idx + 1], rsi_period)

    # Get values at entry
    price = btc_close[entry_idx]
    ema20 = ema_short_vals[entry_idx]
    ema50 = ema_long_vals[entry_idx]
    rsi = rsi_vals[entry_idx]

    # Determine trend
    above_ema20 = price > ema20
    above_ema50 = price > ema50
    rsi_bullish_flag = rsi > rsi_bullish

    # Count bullish conditions
    bullish_count = sum([above_ema20, above_ema50, rsi_bullish_flag])

    if bullish_count >= 2:
        trend = 'BULLISH'
        is_bonus = True
    elif bullish_count == 0:
        trend = 'BEARISH'
        is_bonus = False
    else:
        trend = 'NEUTRAL'
        is_bonus = False

    return {
        'price': float(price),
        'ema20': float(ema20),
        'ema50': float(ema50),
        'rsi': float(rsi) if not np.isnan(rsi) else None,
        'above_ema20': above_ema20,
        'above_ema50': above_ema50,
        'rsi_bullish': rsi_bullish_flag,
        'trend': trend,
        'is_bonus': is_bonus,
    }


def calc_rsi(close, period=14):
    n = len(close)
    if n < period + 1:
        return np.full(n, np.nan)
    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    rsi = np.full(n, np.nan)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, n):
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
        if i < n - 1:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    return rsi


# ═══════════════════════════════════════════════════════════════════════════════
# GB POWER SCORE - Mesure la puissance du Golden Box Setup (0-100)
# ═══════════════════════════════════════════════════════════════════════════════

def calc_gb_power_score(alert_data: dict, v3_data: dict = None) -> dict:
    """
    Calculate the Golden Box Power Score (0-100).

    Combines multiple indicators into a single power score:
    - Volume Breakout Strength (25%)
    - ADX Trend Strength (20%)
    - EMA Stack Alignment (15%)
    - MACD Momentum (15%)
    - Fibonacci Position (10%)
    - DMI Spread (10%)
    - BTC/RSI Confluence (5%)

    For V3, also includes:
    - Retest Quality Score

    Returns dict with all component scores and final grade.
    """
    scores = {}

    # ═══════════════════════════════════════════════════════════════════════════
    # 1. VOLUME BREAKOUT SCORE (0-100) - Weight: 25%
    # ═══════════════════════════════════════════════════════════════════════════
    vol_ratio_1h = alert_data.get('vol_ratio_1h') or 0
    vol_ratio_4h = alert_data.get('vol_ratio_4h') or 0
    vol_ratio = max(vol_ratio_1h, vol_ratio_4h)  # Use best timeframe

    if vol_ratio >= 3.0:
        vol_score = 100  # VERY_HIGH
    elif vol_ratio >= 2.5:
        vol_score = 85
    elif vol_ratio >= 2.0:
        vol_score = 70  # HIGH
    elif vol_ratio >= 1.5:
        vol_score = 50  # NORMAL+
    elif vol_ratio >= 1.0:
        vol_score = 25
    else:
        vol_score = 0
    scores['gb_volume_score'] = vol_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 2. ADX TREND STRENGTH SCORE (0-100) - Weight: 20%
    # ═══════════════════════════════════════════════════════════════════════════
    adx_4h = alert_data.get('adx_value_4h') or 0
    adx_1h = alert_data.get('adx_value_1h') or 0
    adx_val = max(adx_4h, adx_1h)  # Use stronger trend

    if adx_val >= 40:
        adx_score = 100  # VERY_STRONG
    elif adx_val >= 30:
        adx_score = 80
    elif adx_val >= 25:
        adx_score = 60  # STRONG
    elif adx_val >= 20:
        adx_score = 40  # MODERATE
    elif adx_val >= 15:
        adx_score = 20
    else:
        adx_score = 0  # WEAK
    scores['gb_adx_score'] = adx_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 3. EMA STACK ALIGNMENT SCORE (0-100) - Weight: 15%
    # ═══════════════════════════════════════════════════════════════════════════
    ema_stack_count_4h = alert_data.get('ema_stack_count_4h') or 0
    ema_stack_count_1h = alert_data.get('ema_stack_count_1h') or 0
    ema_trend_4h = alert_data.get('ema_stack_trend_4h') or ''

    # Perfect stack = 100, Partial = 66, Mixed = 33
    if ema_trend_4h == 'PERFECT':
        ema_score = 100
    elif ema_stack_count_4h >= 3:
        ema_score = 85
    elif ema_stack_count_4h >= 2:
        ema_score = 60
    elif ema_stack_count_1h >= 3:
        ema_score = 50  # Fallback to 1H
    elif ema_stack_count_1h >= 2:
        ema_score = 35
    else:
        ema_score = 0
    scores['gb_ema_alignment_score'] = ema_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 4. MACD MOMENTUM SCORE (0-100) - Weight: 15%
    # ═══════════════════════════════════════════════════════════════════════════
    macd_hist_4h = alert_data.get('macd_histogram_4h') or 0
    macd_growing_4h = alert_data.get('macd_hist_growing_4h') or False
    macd_hist_1h = alert_data.get('macd_histogram_1h') or 0
    macd_growing_1h = alert_data.get('macd_hist_growing_1h') or False

    # Best case: 4H histogram > 0 AND growing
    if macd_hist_4h > 0 and macd_growing_4h:
        macd_score = 100
    elif macd_hist_4h > 0:
        macd_score = 70
    elif macd_hist_1h > 0 and macd_growing_1h:
        macd_score = 60  # 1H fallback
    elif macd_growing_4h:  # Growing but negative
        macd_score = 40
    elif macd_hist_1h > 0:
        macd_score = 30
    else:
        macd_score = 0
    scores['gb_macd_momentum_score'] = macd_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 5. FIBONACCI POSITION SCORE (0-100) - Weight: 10%
    # ═══════════════════════════════════════════════════════════════════════════
    fib_bonus = alert_data.get('fib_bonus') or False
    fib_levels = alert_data.get('fib_levels') or {}

    # Check which Fib levels are broken
    fib_618_broken = fib_levels.get('0.618', {}).get('broken', False) if isinstance(fib_levels, dict) else False
    fib_50_broken = fib_levels.get('0.5', {}).get('broken', False) if isinstance(fib_levels, dict) else False
    fib_382_broken = fib_bonus

    if fib_618_broken:
        fib_score = 100  # Above 61.8%
    elif fib_50_broken:
        fib_score = 70  # Above 50%
    elif fib_382_broken:
        fib_score = 50  # Above 38.2%
    else:
        fib_score = 0
    scores['gb_fib_position_score'] = fib_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 6. DMI SPREAD SCORE (0-100) - Weight: 10%
    # ═══════════════════════════════════════════════════════════════════════════
    plus_di_4h = alert_data.get('adx_plus_di_4h') or 0
    minus_di_4h = alert_data.get('adx_minus_di_4h') or 0
    dmi_spread = plus_di_4h - minus_di_4h

    scores['gb_dmi_spread'] = dmi_spread

    if dmi_spread >= 25:
        dmi_score = 100  # Very bullish
    elif dmi_spread >= 20:
        dmi_score = 85
    elif dmi_spread >= 15:
        dmi_score = 70
    elif dmi_spread >= 10:
        dmi_score = 50
    elif dmi_spread >= 5:
        dmi_score = 30
    elif dmi_spread > 0:
        dmi_score = 15
    else:
        dmi_score = 0  # Bearish or neutral
    scores['gb_dmi_spread_score'] = dmi_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 7. RSI MULTI-TF STRENGTH (0-100) - Weight: 5%
    # ═══════════════════════════════════════════════════════════════════════════
    rsi_1h = alert_data.get('rsi_1h') or 50
    rsi_4h = alert_data.get('rsi_4h') or 50
    rsi_daily = alert_data.get('rsi_daily') or 50
    rsi_aligned_count = alert_data.get('rsi_aligned_count') or 0

    # All RSI > 50 = bullish alignment
    if rsi_aligned_count >= 3:
        rsi_score = 100
    elif rsi_aligned_count >= 2:
        rsi_score = 70
    elif rsi_4h > 55 and rsi_1h > 55:
        rsi_score = 60
    elif rsi_4h > 50:
        rsi_score = 40
    else:
        rsi_score = 0
    scores['gb_rsi_strength_score'] = rsi_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 8. BTC CORRELATION - DISABLED (not used in analysis)
    # ═══════════════════════════════════════════════════════════════════════════
    scores['gb_btc_correlation_score'] = 0  # BTC correlation disabled

    # ═══════════════════════════════════════════════════════════════════════════
    # 9. RETEST QUALITY (V3 only) - Weight: 15% when V3
    # ═══════════════════════════════════════════════════════════════════════════
    retest_score = 0
    if v3_data:
        box_high = v3_data.get('box_high') or 0
        retest_price = v3_data.get('retest_price') or box_high
        if box_high > 0 and retest_price > 0:
            precision_pct = abs(retest_price - box_high) / box_high * 100

            if precision_pct <= 0.3:
                retest_score = 100  # Perfect retest
            elif precision_pct <= 0.5:
                retest_score = 90
            elif precision_pct <= 1.0:
                retest_score = 75
            elif precision_pct <= 1.5:
                retest_score = 60
            elif precision_pct <= 2.0:
                retest_score = 45
            elif precision_pct <= 3.0:
                retest_score = 30
            else:
                retest_score = 10
    scores['gb_retest_quality_score'] = retest_score

    # ═══════════════════════════════════════════════════════════════════════════
    # 10. CONFLUENCE SCORE - How many bonuses are active
    # ═══════════════════════════════════════════════════════════════════════════
    bonuses_active = sum([
        alert_data.get('vol_spike_bonus_4h') or False,
        alert_data.get('adx_bonus_4h') or False,
        alert_data.get('macd_bonus_4h') or False,
        alert_data.get('ema_stack_bonus_4h') or False,
        alert_data.get('fib_bonus') or False,
        # btc_corr_bonus_4h removed - BTC correlation disabled
        alert_data.get('rsi_mtf_bonus') or False,
        alert_data.get('ob_bonus_4h') or False,
        alert_data.get('fvg_bonus_4h') or False,
    ])

    # Each bonus = ~11 points (9 bonuses max = 100)
    confluence_score = min(100, bonuses_active * 11)
    scores['gb_confluence_score'] = confluence_score

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL POWER SCORE CALCULATION (BTC correlation removed)
    # ═══════════════════════════════════════════════════════════════════════════
    if v3_data:
        # V3 mode: include retest quality
        power_score = int(
            vol_score * 0.21 +
            adx_score * 0.19 +
            ema_score * 0.12 +
            macd_score * 0.12 +
            fib_score * 0.08 +
            dmi_score * 0.08 +
            rsi_score * 0.05 +
            retest_score * 0.15
        )
    else:
        # Standard mode
        power_score = int(
            vol_score * 0.26 +
            adx_score * 0.21 +
            ema_score * 0.15 +
            macd_score * 0.15 +
            fib_score * 0.10 +
            dmi_score * 0.10 +
            rsi_score * 0.03
        )

    scores['gb_power_score'] = power_score

    # ═══════════════════════════════════════════════════════════════════════════
    # GRADE CALCULATION (A-F)
    # ═══════════════════════════════════════════════════════════════════════════
    if power_score >= 80:
        grade = 'A'
    elif power_score >= 65:
        grade = 'B'
    elif power_score >= 50:
        grade = 'C'
    elif power_score >= 35:
        grade = 'D'
    else:
        grade = 'F'
    scores['gb_power_grade'] = grade

    return scores


def calc_v3_risk_score(v3_data: dict) -> dict:
    """
    Calculate V3 Risk Score based on statistical analysis.

    Risk factors identified from backtest data:
    - DiffTL >= 40h: 0% win rate (CRITICAL)
    - DiffTL >= 30h: 20% win rate (HIGH)
    - Distance Before Retest < 3%: 45.9% win rate (MEDIUM)
    - Box Range <= 2%: 26.7% win rate (HIGH)
    - SL Distance <= 3%: 15.4% win rate (HIGH - gets stopped out easily)
    - Hours to Entry > 50h: 28.6% win rate (MEDIUM)

    Returns dict with risk_level, risk_score, and risk_reasons.
    """
    risk_score = 0
    risk_reasons = []

    diff_tl = v3_data.get('hours_retest_vs_tl') or 0
    dist_retest = v3_data.get('distance_before_retest') or 0
    box_range = v3_data.get('box_range_pct') or 0
    sl_distance = v3_data.get('sl_distance_pct') or 0
    hours_to_entry = v3_data.get('hours_to_entry') or 0

    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL RISK: DiffTL >= 40h (0% win rate historically)
    # ═══════════════════════════════════════════════════════════════════════════
    if diff_tl >= 40:
        risk_score += 40
        risk_reasons.append({
            'factor': 'DIFF_TL_CRITICAL',
            'message': f'Diff Retest/TL = {diff_tl:.0f}h (≥40h = 0% win rate)',
            'severity': 'CRITICAL',
            'value': diff_tl
        })
    elif diff_tl >= 30:
        risk_score += 25
        risk_reasons.append({
            'factor': 'DIFF_TL_HIGH',
            'message': f'Diff Retest/TL = {diff_tl:.0f}h (≥30h = 20% win rate)',
            'severity': 'HIGH',
            'value': diff_tl
        })
    elif diff_tl >= 20:
        risk_score += 10
        risk_reasons.append({
            'factor': 'DIFF_TL_MEDIUM',
            'message': f'Diff Retest/TL = {diff_tl:.0f}h (≥20h = 43% win rate)',
            'severity': 'MEDIUM',
            'value': diff_tl
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # Distance Before Retest < 3% (45.9% win rate)
    # ═══════════════════════════════════════════════════════════════════════════
    if dist_retest < 2:
        risk_score += 20
        risk_reasons.append({
            'factor': 'DIST_RETEST_LOW',
            'message': f'Distance Before Retest = {dist_retest:.2f}% (<2% = weak breakout)',
            'severity': 'HIGH',
            'value': dist_retest
        })
    elif dist_retest < 3:
        risk_score += 10
        risk_reasons.append({
            'factor': 'DIST_RETEST_MEDIUM',
            'message': f'Distance Before Retest = {dist_retest:.2f}% (<3% = 46% win rate)',
            'severity': 'MEDIUM',
            'value': dist_retest
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # Box Range <= 2% (26.7% win rate)
    # ═══════════════════════════════════════════════════════════════════════════
    if box_range <= 1:
        risk_score += 25
        risk_reasons.append({
            'factor': 'BOX_RANGE_TINY',
            'message': f'Box Range = {box_range:.2f}% (≤1% = unreliable zone)',
            'severity': 'HIGH',
            'value': box_range
        })
    elif box_range <= 2:
        risk_score += 15
        risk_reasons.append({
            'factor': 'BOX_RANGE_SMALL',
            'message': f'Box Range = {box_range:.2f}% (≤2% = 27% win rate)',
            'severity': 'HIGH',
            'value': box_range
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # SL Distance <= 3% (15.4% win rate - easily stopped out)
    # ═══════════════════════════════════════════════════════════════════════════
    if sl_distance <= 2:
        risk_score += 20
        risk_reasons.append({
            'factor': 'SL_TOO_TIGHT',
            'message': f'SL Distance = {sl_distance:.2f}% (≤2% = easily stopped out)',
            'severity': 'HIGH',
            'value': sl_distance
        })
    elif sl_distance <= 3:
        risk_score += 10
        risk_reasons.append({
            'factor': 'SL_TIGHT',
            'message': f'SL Distance = {sl_distance:.2f}% (≤3% = 15% win rate)',
            'severity': 'MEDIUM',
            'value': sl_distance
        })

    # ═══════════════════════════════════════════════════════════════════════════
    # Hours to Entry > 50h (28.6% win rate)
    # ═══════════════════════════════════════════════════════════════════════════
    if hours_to_entry > 60:
        risk_score += 15
        risk_reasons.append({
            'factor': 'ENTRY_DELAY_HIGH',
            'message': f'Hours to Entry = {hours_to_entry:.0f}h (>60h = momentum lost)',
            'severity': 'MEDIUM',
            'value': hours_to_entry
        })
    elif hours_to_entry > 50:
        risk_score += 8
        risk_reasons.append({
            'factor': 'ENTRY_DELAY_MEDIUM',
            'message': f'Hours to Entry = {hours_to_entry:.0f}h (>50h = 29% win rate)',
            'severity': 'LOW',
            'value': hours_to_entry
        })

    # Cap risk score at 100
    risk_score = min(100, risk_score)

    # Determine risk level
    if risk_score >= 60:
        risk_level = 'CRITICAL'
    elif risk_score >= 40:
        risk_level = 'HIGH'
    elif risk_score >= 20:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'

    return {
        'v3_risk_level': risk_level,
        'v3_risk_score': risk_score,
        'v3_risk_reasons': risk_reasons
    }


def calc_cvd_analysis(df, volume, close, open_prices, high, low,
                       break_idx=None, breakout_idx=None, retest_idx=None, entry_idx=None,
                       lookback=20):
    """
    Calculate Cumulative Volume Delta (CVD) analysis at key trading moments.

    CVD = Cumulative sum of (Buying Volume - Selling Volume)

    Approximation method:
    - If close > open: Buying Volume = volume * (close - low) / (high - low)
    - If close < open: Selling Volume = volume * (high - close) / (high - low)

    Returns dict with CVD values and signals at each key moment.
    """
    n = len(close)

    # Calculate buying and selling volume for each candle
    buying_vol = np.zeros(n)
    selling_vol = np.zeros(n)

    for i in range(n):
        candle_range = high[i] - low[i]
        if candle_range > 0:
            # Proportion of candle that's bullish vs bearish
            close_position = (close[i] - low[i]) / candle_range
            buying_vol[i] = volume[i] * close_position
            selling_vol[i] = volume[i] * (1 - close_position)
        else:
            # Doji - split volume equally
            buying_vol[i] = volume[i] * 0.5
            selling_vol[i] = volume[i] * 0.5

    # Calculate delta (buying - selling)
    delta = buying_vol - selling_vol

    # Calculate CVD (cumulative delta)
    cvd = np.cumsum(delta)

    # Calculate average volume for ratio
    avg_volume = np.zeros(n)
    for i in range(n):
        start = max(0, i - lookback)
        avg_volume[i] = np.mean(volume[start:i+1]) if i > 0 else volume[i]

    def get_cvd_trend(idx, window=5):
        """Determine if CVD is rising, falling, or flat"""
        if idx is None or idx < window:
            return 'NEUTRAL'
        cvd_change = cvd[idx] - cvd[idx - window]
        cvd_pct_change = cvd_change / (abs(cvd[idx - window]) + 1e-10) * 100
        if cvd_pct_change > 5:
            return 'RISING'
        elif cvd_pct_change < -5:
            return 'FALLING'
        return 'FLAT'

    def get_volume_ratio(idx):
        """Get volume / average volume ratio"""
        if idx is None or avg_volume[idx] == 0:
            return 1.0
        return volume[idx] / avg_volume[idx]

    def is_volume_spike(idx, threshold=1.5):
        """Check if volume is spiking"""
        return get_volume_ratio(idx) >= threshold

    result = {
        'cvd_bonus': False,
        'cvd_score': 0,
        'cvd_label': 'NO_DATA',
        'cvd_description': 'Insufficient data for CVD analysis',

        # At TL Break
        'cvd_at_break': None,
        'cvd_at_break_trend': 'NEUTRAL',
        'cvd_at_break_signal': 'NEUTRAL',

        # At Breakout
        'cvd_at_breakout': None,
        'cvd_at_breakout_spike': False,
        'cvd_at_breakout_signal': 'NEUTRAL',

        # At Retest
        'cvd_at_retest': None,
        'cvd_at_retest_trend': 'NEUTRAL',
        'cvd_at_retest_signal': 'NEUTRAL',

        # At Entry
        'cvd_at_entry': None,
        'cvd_at_entry_trend': 'NEUTRAL',
        'cvd_at_entry_signal': 'NEUTRAL',

        # Divergence
        'cvd_divergence': False,
        'cvd_divergence_type': 'NONE',

        # Volume ratios
        'vol_at_break_ratio': None,
        'vol_at_breakout_ratio': None,
        'vol_at_retest_ratio': None,
        'vol_at_entry_ratio': None,
    }

    score = 0
    signals = []

    # ═══════════════════════════════════════════════════════════════════════════
    # CVD AT TL BREAK
    # ═══════════════════════════════════════════════════════════════════════════
    if break_idx is not None and break_idx < n:
        result['cvd_at_break'] = float(cvd[break_idx])
        result['cvd_at_break_trend'] = get_cvd_trend(break_idx)
        result['vol_at_break_ratio'] = get_volume_ratio(break_idx)

        # Signal analysis
        if delta[break_idx] > 0 and result['cvd_at_break_trend'] == 'RISING':
            result['cvd_at_break_signal'] = 'BULLISH'
            score += 25
            signals.append('TL Break: Volume acheteur confirmé ✅')
        elif delta[break_idx] > 0:
            result['cvd_at_break_signal'] = 'NEUTRAL'
            score += 10
            signals.append('TL Break: Volume positif mais CVD plat ⚠️')
        else:
            result['cvd_at_break_signal'] = 'BEARISH'
            signals.append('TL Break: Volume vendeur dominant ❌')

    # ═══════════════════════════════════════════════════════════════════════════
    # CVD AT BREAKOUT (Box High break)
    # ═══════════════════════════════════════════════════════════════════════════
    if breakout_idx is not None and breakout_idx < n:
        result['cvd_at_breakout'] = float(cvd[breakout_idx])
        result['cvd_at_breakout_spike'] = is_volume_spike(breakout_idx)
        result['vol_at_breakout_ratio'] = get_volume_ratio(breakout_idx)

        # Signal analysis
        if result['cvd_at_breakout_spike'] and delta[breakout_idx] > 0:
            result['cvd_at_breakout_signal'] = 'STRONG_BUY'
            score += 30
            signals.append(f'Breakout: Spike volume {result["vol_at_breakout_ratio"]:.1f}x + acheteurs ✅✅')
        elif delta[breakout_idx] > 0:
            result['cvd_at_breakout_signal'] = 'BUY'
            score += 15
            signals.append('Breakout: Volume acheteur modéré ✅')
        elif delta[breakout_idx] < 0:
            result['cvd_at_breakout_signal'] = 'SELL'
            signals.append('Breakout: Attention - vendeurs actifs ⚠️')
        else:
            result['cvd_at_breakout_signal'] = 'NEUTRAL'
            score += 5
            signals.append('Breakout: Volume neutre')

    # ═══════════════════════════════════════════════════════════════════════════
    # CVD AT RETEST
    # ═══════════════════════════════════════════════════════════════════════════
    if retest_idx is not None and retest_idx < n:
        result['cvd_at_retest'] = float(cvd[retest_idx])
        result['cvd_at_retest_trend'] = get_cvd_trend(retest_idx)
        result['vol_at_retest_ratio'] = get_volume_ratio(retest_idx)

        # Compare CVD at retest vs breakout
        cvd_stable = True
        if breakout_idx is not None and breakout_idx < n:
            cvd_change = cvd[retest_idx] - cvd[breakout_idx]
            cvd_pct_drop = cvd_change / (abs(cvd[breakout_idx]) + 1e-10) * 100
            if cvd_pct_drop < -20:
                cvd_stable = False

        # Signal analysis
        if cvd_stable and result['cvd_at_retest_trend'] in ['RISING', 'FLAT']:
            result['cvd_at_retest_signal'] = 'ACCUMULATION'
            score += 25
            signals.append('Retest: Accumulation - CVD stable ✅')
        elif not cvd_stable:
            result['cvd_at_retest_signal'] = 'DISTRIBUTION'
            signals.append('Retest: Distribution - CVD en chute ❌')
        else:
            result['cvd_at_retest_signal'] = 'NEUTRAL'
            score += 10
            signals.append('Retest: CVD neutre ⚠️')

    # ═══════════════════════════════════════════════════════════════════════════
    # CVD AT ENTRY
    # ═══════════════════════════════════════════════════════════════════════════
    if entry_idx is not None and entry_idx < n:
        result['cvd_at_entry'] = float(cvd[entry_idx])
        result['cvd_at_entry_trend'] = get_cvd_trend(entry_idx, window=3)
        result['vol_at_entry_ratio'] = get_volume_ratio(entry_idx)

        # Signal analysis
        if result['cvd_at_entry_trend'] == 'RISING' and delta[entry_idx] > 0:
            result['cvd_at_entry_signal'] = 'CONFIRMED'
            score += 20
            signals.append('Entry: CVD en hausse - CONFIRMÉ ✅✅')
        elif result['cvd_at_entry_trend'] == 'FALLING':
            result['cvd_at_entry_signal'] = 'DANGER'
            signals.append('Entry: CVD en baisse - DANGER ❌')
        else:
            result['cvd_at_entry_signal'] = 'WARNING'
            score += 5
            signals.append('Entry: CVD neutre - prudence ⚠️')

    # ═══════════════════════════════════════════════════════════════════════════
    # DIVERGENCE DETECTION
    # ═══════════════════════════════════════════════════════════════════════════
    if break_idx is not None and entry_idx is not None and entry_idx > break_idx:
        price_up = close[entry_idx] > close[break_idx]
        cvd_down = cvd[entry_idx] < cvd[break_idx]

        if price_up and cvd_down:
            result['cvd_divergence'] = True
            result['cvd_divergence_type'] = 'BEARISH'
            score -= 20
            signals.append('⚠️ DIVERGENCE BAISSIÈRE: Prix monte mais CVD descend!')
        elif not price_up and not cvd_down:
            result['cvd_divergence'] = True
            result['cvd_divergence_type'] = 'BULLISH'
            score += 10
            signals.append('Divergence haussière: Prix consolide mais CVD monte')

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL SCORE AND LABEL
    # ═══════════════════════════════════════════════════════════════════════════
    result['cvd_score'] = max(0, min(100, score))

    # Determine label based on score
    if result['cvd_score'] >= 80:
        result['cvd_label'] = 'STRONG BUY'
        result['cvd_bonus'] = True
        result['cvd_description'] = 'CVD confirme fortement: volume acheteur dominant à chaque étape'
    elif result['cvd_score'] >= 60:
        result['cvd_label'] = 'BUY'
        result['cvd_bonus'] = True
        result['cvd_description'] = 'CVD positif: pression acheteuse confirmée'
    elif result['cvd_score'] >= 40:
        result['cvd_label'] = 'NEUTRAL'
        result['cvd_bonus'] = False
        result['cvd_description'] = 'CVD mixte: signaux contradictoires'
    elif result['cvd_score'] >= 20:
        result['cvd_label'] = 'WEAK'
        result['cvd_bonus'] = False
        result['cvd_description'] = 'CVD faible: manque de conviction acheteuse'
    else:
        result['cvd_label'] = 'AVOID'
        result['cvd_bonus'] = False
        result['cvd_description'] = 'CVD négatif: pression vendeuse dominante'

    # Add detailed description with all signals
    if signals:
        result['cvd_description'] = ' | '.join(signals)

    return result


def calc_adx_di_analysis(df, high, low, close,
                          break_idx=None, breakout_idx=None, retest_idx=None, entry_idx=None,
                          adx_len=3, adx_threshold=20):
    """
    Calculate ADX/DI analysis at key trading moments.

    Based on PineScript ADX and DI indicator:
    - ADX = Average Directional Index (trend strength)
    - DI+ = Positive Directional Indicator (bullish pressure)
    - DI- = Negative Directional Indicator (bearish pressure)

    Key signals:
    - DI+ > DI- = Bullish trend
    - DI- > DI+ = Bearish trend
    - DI+ > 60 = Extreme bullish (overbought zone)
    - DI- > 60 = Extreme bearish (oversold zone)
    - ADX > 20 = Strong trend

    Parameters:
    - adx_len: Smoothing period (default 3, very reactive like in the PineScript)
    - adx_threshold: ADX threshold for strong trend (default 20)
    """
    n = len(close)

    # Calculate True Range and Directional Movement (matching PineScript logic)
    tr = np.zeros(n)
    dm_plus = np.zeros(n)
    dm_minus = np.zeros(n)

    for i in range(1, n):
        # True Range
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )

        # Directional Movement Plus
        up_move = high[i] - high[i-1]
        down_move = low[i-1] - low[i]

        if up_move > down_move and up_move > 0:
            dm_plus[i] = up_move
        else:
            dm_plus[i] = 0

        # Directional Movement Minus
        if down_move > up_move and down_move > 0:
            dm_minus[i] = down_move
        else:
            dm_minus[i] = 0

    # Smoothed values (Wilder's smoothing as in PineScript)
    smoothed_tr = np.zeros(n)
    smoothed_dm_plus = np.zeros(n)
    smoothed_dm_minus = np.zeros(n)

    for i in range(1, n):
        if i == 1:
            smoothed_tr[i] = tr[i]
            smoothed_dm_plus[i] = dm_plus[i]
            smoothed_dm_minus[i] = dm_minus[i]
        else:
            smoothed_tr[i] = smoothed_tr[i-1] - (smoothed_tr[i-1] / adx_len) + tr[i]
            smoothed_dm_plus[i] = smoothed_dm_plus[i-1] - (smoothed_dm_plus[i-1] / adx_len) + dm_plus[i]
            smoothed_dm_minus[i] = smoothed_dm_minus[i-1] - (smoothed_dm_minus[i-1] / adx_len) + dm_minus[i]

    # Calculate DI+ and DI-
    di_plus = np.zeros(n)
    di_minus = np.zeros(n)
    dx = np.zeros(n)

    for i in range(adx_len, n):
        if smoothed_tr[i] > 0:
            di_plus[i] = (smoothed_dm_plus[i] / smoothed_tr[i]) * 100
            di_minus[i] = (smoothed_dm_minus[i] / smoothed_tr[i]) * 100

        # Calculate DX
        di_sum = di_plus[i] + di_minus[i]
        if di_sum > 0:
            dx[i] = abs(di_plus[i] - di_minus[i]) / di_sum * 100

    # Calculate ADX (SMA of DX)
    adx = np.zeros(n)
    for i in range(adx_len * 2, n):
        adx[i] = np.mean(dx[max(0, i - adx_len + 1):i + 1])

    # Initialize result
    result = {
        'adx_di_bonus': False,
        'adx_di_score': 0,
        'adx_di_label': 'NO_DATA',

        # At TL Break
        'adx_at_break': None,
        'di_plus_at_break': None,
        'di_minus_at_break': None,
        'di_spread_at_break': None,
        'adx_di_at_break_signal': 'NEUTRAL',

        # At Breakout
        'adx_at_breakout': None,
        'di_plus_at_breakout': None,
        'di_minus_at_breakout': None,
        'di_spread_at_breakout': None,
        'adx_di_at_breakout_signal': 'NEUTRAL',

        # At Retest
        'adx_at_retest': None,
        'di_plus_at_retest': None,
        'di_minus_at_retest': None,
        'di_spread_at_retest': None,
        'adx_di_at_retest_signal': 'NEUTRAL',

        # At Entry
        'adx_at_entry': None,
        'di_plus_at_entry': None,
        'di_minus_at_entry': None,
        'di_spread_at_entry': None,
        'adx_di_at_entry_signal': 'NEUTRAL',

        # Extreme zones
        'di_plus_overbought': False,
        'di_minus_oversold': False,
    }

    score = 0
    signals = []

    def analyze_moment(idx, moment_name):
        """Analyze ADX/DI at a specific moment"""
        nonlocal score

        if idx is None or idx >= n or idx < adx_len * 2:
            return None, None, None, None, 'NEUTRAL'

        adx_val = float(adx[idx])
        di_plus_val = float(di_plus[idx])
        di_minus_val = float(di_minus[idx])
        di_spread = di_plus_val - di_minus_val

        # Determine signal
        signal = 'NEUTRAL'

        # Strong trend with DI+ dominant
        if adx_val >= adx_threshold and di_spread > 10:
            if moment_name in ['TL Break', 'Breakout']:
                signal = 'STRONG_BUY' if di_spread > 20 else 'BUY'
                score += 25 if di_spread > 20 else 15
                signals.append(f'{moment_name}: Forte tendance haussière ADX={adx_val:.0f} DI+={di_plus_val:.0f} ✅')
            elif moment_name == 'Retest':
                signal = 'ACCUMULATION'
                score += 20
                signals.append(f'{moment_name}: DI+ domine - accumulation ✅')
            elif moment_name == 'Entry':
                signal = 'CONFIRMED'
                score += 25
                signals.append(f'{moment_name}: Tendance confirmée DI+>DI- ✅✅')

        # DI+ > DI- but weak trend
        elif di_spread > 5:
            if moment_name in ['TL Break', 'Breakout']:
                signal = 'BUY'
                score += 10
                signals.append(f'{moment_name}: DI+ > DI- mais tendance faible ⚠️')
            elif moment_name == 'Retest':
                signal = 'NEUTRAL'
                score += 5
            elif moment_name == 'Entry':
                signal = 'WARNING'
                score += 5
                signals.append(f'{moment_name}: Tendance faible - prudence ⚠️')

        # DI- dominant (bearish)
        elif di_spread < -5:
            if moment_name in ['TL Break', 'Breakout']:
                signal = 'SELL'
                signals.append(f'{moment_name}: DI- domine - pression vendeuse ❌')
            elif moment_name == 'Retest':
                signal = 'DISTRIBUTION'
                signals.append(f'{moment_name}: Distribution - DI- dominant ❌')
            elif moment_name == 'Entry':
                signal = 'DANGER'
                signals.append(f'{moment_name}: DANGER - DI- > DI+ ❌')

        # Ranging market
        else:
            signal = 'NEUTRAL'
            score += 2
            if moment_name == 'Entry':
                signals.append(f'{moment_name}: Marché en range - DI+ ≈ DI-')

        return adx_val, di_plus_val, di_minus_val, di_spread, signal

    # ═══════════════════════════════════════════════════════════════════════════
    # ADX/DI AT TL BREAK
    # ═══════════════════════════════════════════════════════════════════════════
    adx_val, di_plus_val, di_minus_val, di_spread, signal = analyze_moment(break_idx, 'TL Break')
    if adx_val is not None:
        result['adx_at_break'] = adx_val
        result['di_plus_at_break'] = di_plus_val
        result['di_minus_at_break'] = di_minus_val
        result['di_spread_at_break'] = di_spread
        result['adx_di_at_break_signal'] = signal

    # ═══════════════════════════════════════════════════════════════════════════
    # ADX/DI AT BREAKOUT
    # ═══════════════════════════════════════════════════════════════════════════
    adx_val, di_plus_val, di_minus_val, di_spread, signal = analyze_moment(breakout_idx, 'Breakout')
    if adx_val is not None:
        result['adx_at_breakout'] = adx_val
        result['di_plus_at_breakout'] = di_plus_val
        result['di_minus_at_breakout'] = di_minus_val
        result['di_spread_at_breakout'] = di_spread
        result['adx_di_at_breakout_signal'] = signal

    # ═══════════════════════════════════════════════════════════════════════════
    # ADX/DI AT RETEST
    # ═══════════════════════════════════════════════════════════════════════════
    adx_val, di_plus_val, di_minus_val, di_spread, signal = analyze_moment(retest_idx, 'Retest')
    if adx_val is not None:
        result['adx_at_retest'] = adx_val
        result['di_plus_at_retest'] = di_plus_val
        result['di_minus_at_retest'] = di_minus_val
        result['di_spread_at_retest'] = di_spread
        result['adx_di_at_retest_signal'] = signal

    # ═══════════════════════════════════════════════════════════════════════════
    # ADX/DI AT ENTRY
    # ═══════════════════════════════════════════════════════════════════════════
    adx_val, di_plus_val, di_minus_val, di_spread, signal = analyze_moment(entry_idx, 'Entry')
    if adx_val is not None:
        result['adx_at_entry'] = adx_val
        result['di_plus_at_entry'] = di_plus_val
        result['di_minus_at_entry'] = di_minus_val
        result['di_spread_at_entry'] = di_spread
        result['adx_di_at_entry_signal'] = signal

        # Check extreme zones at entry
        if di_plus_val > 60:
            result['di_plus_overbought'] = True
            score += 10
            signals.append('🔥 DI+ > 60: Zone de surachat - momentum extrême!')
        if di_minus_val > 60:
            result['di_minus_oversold'] = True
            score -= 10
            signals.append('⚠️ DI- > 60: Zone de survente - attention!')

    # ═══════════════════════════════════════════════════════════════════════════
    # FINAL SCORE AND LABEL
    # ═══════════════════════════════════════════════════════════════════════════
    result['adx_di_score'] = max(0, min(100, score))

    # Determine label based on score
    if result['adx_di_score'] >= 80:
        result['adx_di_label'] = 'STRONG TREND'
        result['adx_di_bonus'] = True
    elif result['adx_di_score'] >= 60:
        result['adx_di_label'] = 'TREND'
        result['adx_di_bonus'] = True
    elif result['adx_di_score'] >= 40:
        result['adx_di_label'] = 'WEAK TREND'
        result['adx_di_bonus'] = False
    elif result['adx_di_score'] >= 20:
        result['adx_di_label'] = 'RANGING'
        result['adx_di_bonus'] = False
    else:
        result['adx_di_label'] = 'NO TREND'
        result['adx_di_bonus'] = False

    return result


def calc_agent_decision(alert_data: dict) -> dict:
    """
    AI Agent Decision System - Meta-analysis of all indicators.

    Reads ALL available indicators and makes a trade decision WITHOUT seeing P&L results.
    The agent provides:
    - Decision: STRONG_BUY, BUY, HOLD, AVOID
    - Confidence: 0-100%
    - Score: 0-100 overall rating
    - Grade: A+, A, B+, B, C, D, F
    - Bullish/Bearish factors
    - Full reasoning

    This function is called after all indicators are computed to provide a meta-analysis.
    """
    import json

    result = {
        'agent_decision': 'HOLD',
        'agent_confidence': 50,
        'agent_score': 50,
        'agent_grade': 'C',
        'agent_bullish_count': 0,
        'agent_bearish_count': 0,
        'agent_neutral_count': 0,
        'agent_bullish_factors': '[]',
        'agent_bearish_factors': '[]',
        'agent_reasoning': '',
        'agent_cvd_score': 0,
        'agent_adx_score': 0,
        'agent_trend_score': 0,
        'agent_momentum_score': 0,
        'agent_volume_score': 0,
        'agent_confluence_score': 0,
    }

    bullish_factors = []
    bearish_factors = []
    neutral_factors = []

    # ═══════════════════════════════════════════════════════════════════════════════
    # 1. CVD ANALYSIS SCORE (Cumulative Volume Delta)
    # ═══════════════════════════════════════════════════════════════════════════════
    cvd_1h_score = alert_data.get('cvd_1h_score', 0) or 0
    cvd_4h_score = alert_data.get('cvd_4h_score', 0) or 0
    cvd_1h_label = alert_data.get('cvd_1h_label', 'NO_DATA')
    cvd_4h_label = alert_data.get('cvd_4h_label', 'NO_DATA')

    # Combined CVD score (weighted average: 4H is more important)
    cvd_combined = int((cvd_1h_score * 0.4) + (cvd_4h_score * 0.6))
    result['agent_cvd_score'] = cvd_combined

    if cvd_combined >= 80:
        bullish_factors.append(f"CVD FORT: Score {cvd_combined}/100 - Pression d'achat dominante")
    elif cvd_combined >= 60:
        bullish_factors.append(f"CVD Positif: Score {cvd_combined}/100 - Acheteurs présents")
    elif cvd_combined >= 40:
        neutral_factors.append(f"CVD Neutre: Score {cvd_combined}/100")
    elif cvd_combined >= 20:
        bearish_factors.append(f"CVD Faible: Score {cvd_combined}/100 - Vendeurs présents")
    else:
        bearish_factors.append(f"CVD NÉGATIF: Score {cvd_combined}/100 - Pression vendeuse")

    # Check CVD signals at key moments
    cvd_entry_1h = alert_data.get('cvd_1h_at_entry_signal', 'NEUTRAL')
    cvd_entry_4h = alert_data.get('cvd_4h_at_entry_signal', 'NEUTRAL')

    if cvd_entry_1h == 'STRONG_BUY' and cvd_entry_4h == 'STRONG_BUY':
        bullish_factors.append("CVD Entry: ACHAT FORT sur 1H et 4H")
    elif cvd_entry_1h in ['STRONG_BUY', 'BUY'] and cvd_entry_4h in ['STRONG_BUY', 'BUY']:
        bullish_factors.append("CVD Entry: Signal d'achat confirmé multi-TF")
    elif cvd_entry_1h in ['SELL', 'STRONG_SELL'] or cvd_entry_4h in ['SELL', 'STRONG_SELL']:
        bearish_factors.append("CVD Entry: Signal de vente détecté")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 2. ADX/DI ANALYSIS SCORE (Trend Strength)
    # ═══════════════════════════════════════════════════════════════════════════════
    adx_1h_score = alert_data.get('adx_di_1h_score', 0) or 0
    adx_4h_score = alert_data.get('adx_di_4h_score', 0) or 0
    adx_1h_label = alert_data.get('adx_di_1h_label', 'NO_DATA')
    adx_4h_label = alert_data.get('adx_di_4h_label', 'NO_DATA')

    # Combined ADX score
    adx_combined = int((adx_1h_score * 0.4) + (adx_4h_score * 0.6))
    result['agent_adx_score'] = adx_combined

    # Check DI spread at entry (positive = bullish)
    di_spread_1h = alert_data.get('di_spread_1h_at_entry', 0) or 0
    di_spread_4h = alert_data.get('di_spread_4h_at_entry', 0) or 0

    if adx_1h_label in ['STRONG TREND', 'TREND'] and di_spread_1h > 0:
        bullish_factors.append(f"ADX 1H: {adx_1h_label} haussier (DI+ domine)")
    elif adx_1h_label in ['STRONG TREND', 'TREND'] and di_spread_1h < 0:
        bearish_factors.append(f"ADX 1H: {adx_1h_label} mais DI- domine")
    elif adx_1h_label in ['WEAK TREND', 'RANGING', 'NO TREND']:
        neutral_factors.append(f"ADX 1H: {adx_1h_label}")

    if adx_4h_label in ['STRONG TREND', 'TREND'] and di_spread_4h > 0:
        bullish_factors.append(f"ADX 4H: {adx_4h_label} haussier (DI+ domine)")
    elif adx_4h_label in ['STRONG TREND', 'TREND'] and di_spread_4h < 0:
        bearish_factors.append(f"ADX 4H: {adx_4h_label} mais DI- domine")

    # Extreme zones
    if alert_data.get('di_plus_1h_overbought') or alert_data.get('di_plus_4h_overbought'):
        bullish_factors.append("DI+ > 60: Zone de momentum extrême!")
    if alert_data.get('di_minus_1h_oversold') or alert_data.get('di_minus_4h_oversold'):
        bearish_factors.append("DI- > 60: Pression vendeuse extrême!")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 3. GOLDEN BOX POWER SCORE (V3 Entry Quality)
    # ═══════════════════════════════════════════════════════════════════════════════
    gb_power_score = alert_data.get('gb_power_score', 0) or 0
    gb_power_grade = alert_data.get('gb_power_grade', 'F')
    v3_quality_score = alert_data.get('v3_quality_score', 0) or 0
    v3_prog_count = alert_data.get('v3_progressive_count', 0) or 0

    # Trend score from GB Power
    result['agent_trend_score'] = gb_power_score

    if gb_power_score >= 80:
        bullish_factors.append(f"GB Power: {gb_power_score}/100 ({gb_power_grade}) - EXCELLENT")
    elif gb_power_score >= 60:
        bullish_factors.append(f"GB Power: {gb_power_score}/100 ({gb_power_grade}) - BON")
    elif gb_power_score >= 40:
        neutral_factors.append(f"GB Power: {gb_power_score}/100 ({gb_power_grade})")
    else:
        bearish_factors.append(f"GB Power: {gb_power_score}/100 ({gb_power_grade}) - FAIBLE")

    # V3 Progressive Conditions
    if v3_prog_count == 5:
        bullish_factors.append(f"V3: 5/5 conditions remplies - SETUP PARFAIT")
    elif v3_prog_count >= 4:
        bullish_factors.append(f"V3: {v3_prog_count}/5 conditions - SETUP FORT")
    elif v3_prog_count >= 3:
        neutral_factors.append(f"V3: {v3_prog_count}/5 conditions")
    elif v3_prog_count > 0:
        bearish_factors.append(f"V3: Seulement {v3_prog_count}/5 conditions")

    # ═══════════════════════════════════════════════════════════════════════════════
    # 4. MOMENTUM ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════
    momentum_score = 50  # Start neutral

    # MEGA BUY Score
    mega_buy_score = alert_data.get('score', 0) or 0
    if mega_buy_score >= 8:
        momentum_score += 20
        bullish_factors.append(f"MEGA BUY: Score {mega_buy_score}/10 - Signal FORT")
    elif mega_buy_score >= 6:
        momentum_score += 10
        bullish_factors.append(f"MEGA BUY: Score {mega_buy_score}/10 - Signal BON")
    elif mega_buy_score >= 4:
        neutral_factors.append(f"MEGA BUY: Score {mega_buy_score}/10")
    else:
        momentum_score -= 10
        bearish_factors.append(f"MEGA BUY: Score {mega_buy_score}/10 - Signal FAIBLE")

    # Stoch RSI bonuses
    if alert_data.get('stoch_rsi_bonus_1h') and alert_data.get('stoch_rsi_bonus_4h'):
        momentum_score += 15
        bullish_factors.append("Stoch RSI: Oversold confirmé multi-TF")
    elif alert_data.get('stoch_rsi_bonus_1h') or alert_data.get('stoch_rsi_bonus_4h'):
        momentum_score += 8
        bullish_factors.append("Stoch RSI: Oversold détecté")

    # MACD bonuses
    if alert_data.get('macd_bonus_1h') and alert_data.get('macd_bonus_4h'):
        momentum_score += 15
        bullish_factors.append("MACD: Signal haussier multi-TF")
    elif alert_data.get('macd_bonus_1h') or alert_data.get('macd_bonus_4h'):
        momentum_score += 8
        bullish_factors.append("MACD: Signal haussier détecté")

    # RSI MTF bonus
    if alert_data.get('rsi_mtf_bonus'):
        momentum_score += 10
        bullish_factors.append("RSI MTF: Alignement haussier")

    result['agent_momentum_score'] = max(0, min(100, momentum_score))

    # ═══════════════════════════════════════════════════════════════════════════════
    # 5. VOLUME ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════════
    volume_score = 50  # Start neutral

    if alert_data.get('vol_spike_bonus_1h') and alert_data.get('vol_spike_bonus_4h'):
        volume_score += 25
        bullish_factors.append("Volume: Spike confirmé 1H et 4H")
    elif alert_data.get('vol_spike_bonus_1h') or alert_data.get('vol_spike_bonus_4h'):
        volume_score += 15
        bullish_factors.append("Volume: Spike détecté")

    # CVD volume at entry
    vol_entry_1h = alert_data.get('vol_1h_at_entry_ratio', 1.0) or 1.0
    vol_entry_4h = alert_data.get('vol_4h_at_entry_ratio', 1.0) or 1.0

    if vol_entry_1h > 2.0 or vol_entry_4h > 2.0:
        volume_score += 20
        bullish_factors.append(f"Volume Entry: {max(vol_entry_1h, vol_entry_4h):.1f}x - TRÈS FORT")
    elif vol_entry_1h > 1.5 or vol_entry_4h > 1.5:
        volume_score += 10
        bullish_factors.append(f"Volume Entry: {max(vol_entry_1h, vol_entry_4h):.1f}x - FORT")
    elif vol_entry_1h < 0.5 and vol_entry_4h < 0.5:
        volume_score -= 15
        bearish_factors.append("Volume Entry: FAIBLE - Manque de participation")

    result['agent_volume_score'] = max(0, min(100, volume_score))

    # ═══════════════════════════════════════════════════════════════════════════════
    # 6. CONFLUENCE ANALYSIS (Multi-factor alignment)
    # ═══════════════════════════════════════════════════════════════════════════════
    confluence_score = 0

    # EMA Stack alignments
    if alert_data.get('ema_stack_bonus_1h') and alert_data.get('ema_stack_bonus_4h'):
        confluence_score += 20
        bullish_factors.append("EMA Stack: Alignement parfait multi-TF")
    elif alert_data.get('ema_stack_bonus_1h') or alert_data.get('ema_stack_bonus_4h'):
        confluence_score += 10
        bullish_factors.append("EMA Stack: Alignement partiel")

    # ETH correlation (BTC correlation removed from analysis)
    if alert_data.get('eth_corr_bonus_1h') or alert_data.get('eth_corr_bonus_4h'):
        confluence_score += 10
        bullish_factors.append("ETH: Corrélation positive")

    # Bollinger squeeze
    if alert_data.get('bb_squeeze_bonus_1h') or alert_data.get('bb_squeeze_bonus_4h'):
        confluence_score += 15
        bullish_factors.append("BB Squeeze: Expansion de volatilité attendue")

    # Order Block / FVG
    if alert_data.get('ob_bonus') or alert_data.get('ob_bonus_4h'):
        confluence_score += 15
        bullish_factors.append("Order Block: Zone de demande institutionnelle")

    if alert_data.get('fvg_bonus_1h') or alert_data.get('fvg_bonus_4h'):
        confluence_score += 10
        bullish_factors.append("FVG: Fair Value Gap haussier")

    # Fibonacci bonus
    if alert_data.get('fib_bonus'):
        confluence_score += 15
        bullish_factors.append("Fibonacci: Au-dessus du niveau 38.2%")

    # ADX bonuses
    if alert_data.get('adx_bonus_1h') and alert_data.get('adx_bonus_4h'):
        confluence_score += 15
        bullish_factors.append("ADX: Trend fort confirmé multi-TF")

    result['agent_confluence_score'] = max(0, min(100, confluence_score))

    # ═══════════════════════════════════════════════════════════════════════════════
    # 7. KILL SIGNALS - Critical red flags that force AVOID
    # These override all other signals because they historically lead to losses
    # ═══════════════════════════════════════════════════════════════════════════════
    kill_signals = []
    kill_score_penalty = 0

    # Get all DI Spread values at different moments
    di_spread_at_entry_1h = alert_data.get('di_spread_1h_at_entry', 0) or 0
    di_spread_at_entry_4h = alert_data.get('di_spread_4h_at_entry', 0) or 0
    di_spread_at_breakout_1h = alert_data.get('di_spread_1h_at_breakout', 0) or 0
    di_spread_at_breakout_4h = alert_data.get('di_spread_4h_at_breakout', 0) or 0
    di_spread_at_break_1h = alert_data.get('di_spread_1h_at_break', 0) or 0

    # Check if OB was retested (this changes how we interpret DI at entry)
    ob_1h_retested = alert_data.get('fc_ob_1h_retest', False)
    ob_4h_retested = alert_data.get('fc_ob_4h_retest', False)
    ob_retested = ob_1h_retested or ob_4h_retested

    # ═══════════════════════════════════════════════════════════════════════════════
    # IMPORTANT: During OB retest (pullback), DI- naturally dominates temporarily
    # This is EXPECTED behavior - the pullback IS the retest
    # What matters is: Was DI+ dominant at BREAKOUT? If yes, retest is healthy
    # ═══════════════════════════════════════════════════════════════════════════════

    # KILL SIGNAL 1: DI Spread analysis - context-aware
    # If OB was retested AND breakout was bullish → DON'T penalize entry DI
    # If NO OB retest AND entry DI negative → This is a real warning

    if ob_retested and di_spread_at_breakout_1h > 10:
        # OB retest with bullish breakout = HEALTHY pullback, give bonus
        bullish_factors.append(f"OB Retest: Pullback sain (DI+ dominait au breakout: +{di_spread_at_breakout_1h:.1f})")
        # Don't add kill signal for negative DI at entry
    else:
        # No OB protection - check DI at entry more carefully
        if di_spread_at_entry_1h < -10 and di_spread_at_breakout_1h < 0:
            # Both breakout AND entry are bearish = real problem
            kill_signals.append(f"🚨 DI INVERSION 1H: Breakout {di_spread_at_breakout_1h:.1f} → Entry {di_spread_at_entry_1h:.1f}")
            bearish_factors.append(f"DI INVERSION 1H: Spread {di_spread_at_entry_1h:.1f} = Vendeurs dominent")
            kill_score_penalty += 25
        elif di_spread_at_entry_1h < -20 and not ob_retested:
            # Very negative at entry without OB support
            kill_signals.append(f"🚨 DI SPREAD 1H TRÈS NÉGATIF: {di_spread_at_entry_1h:.1f} sans OB support")
            bearish_factors.append(f"DI INVERSION 1H: Spread {di_spread_at_entry_1h:.1f} = Vendeurs dominent")
            kill_score_penalty += 20

    # 4H DI check - more important, check breakout not entry
    if di_spread_at_breakout_4h < -5 and di_spread_at_entry_4h < -5:
        # 4H bearish at both breakout and entry = structural problem
        kill_signals.append(f"🚨 DI 4H BAISSIER: Breakout {di_spread_at_breakout_4h:.1f} → Entry {di_spread_at_entry_4h:.1f}")
        bearish_factors.append(f"DI INVERSION 4H: Tendance structurellement baissière")
        kill_score_penalty += 25

    # KILL SIGNAL 2: Hours to Entry > 50 = Only 29% win rate historically
    hours_to_entry = alert_data.get('v3_hours_to_entry', 0) or 0
    if hours_to_entry > 50:
        kill_signals.append(f"🚨 DÉLAI EXCESSIF: {hours_to_entry:.0f}h (>50h = seulement 29% win rate)")
        bearish_factors.append(f"Délai Entry: {hours_to_entry:.0f}h - Statistiquement perdant")
        kill_score_penalty += 20

    # KILL SIGNAL 3: V3 Quality Score < 5 = Poor setup quality
    v3_quality = alert_data.get('v3_quality_score', 10) or 10
    if v3_quality < 5:
        kill_signals.append(f"🚨 V3 QUALITY FAIBLE: {v3_quality}/10 (<5 = setup de mauvaise qualité)")
        bearish_factors.append(f"V3 Quality: {v3_quality}/10 - Setup dégradé")
        kill_score_penalty += 15

    # KILL SIGNAL 4: CVD Divergence Bearish = Price up but volume down
    # IMPORTANT: If OB is retested, CVD divergence during pullback is less critical
    # The OB provides structural support that CVD doesn't capture
    cvd_1h_divergence = alert_data.get('cvd_1h_divergence', False)
    cvd_4h_divergence = alert_data.get('cvd_4h_divergence', False)
    cvd_1h_div_type = alert_data.get('cvd_1h_divergence_type', 'NONE')
    cvd_4h_div_type = alert_data.get('cvd_4h_divergence_type', 'NONE')

    if cvd_4h_divergence and cvd_4h_div_type == 'BEARISH':
        if ob_retested:
            # OB retested = divergence is less critical, just note it
            bearish_factors.append("CVD Divergence 4H: BEARISH (mais OB support présent)")
            kill_score_penalty += 5  # Reduced penalty
        else:
            # No OB support = divergence is a real warning
            kill_signals.append("🚨 CVD DIVERGENCE 4H: Prix monte mais volume baisse = Faiblesse cachée")
            bearish_factors.append("CVD Divergence 4H: BEARISH - Acheteurs s'épuisent")
            kill_score_penalty += 20

    if cvd_1h_divergence and cvd_1h_div_type == 'BEARISH' and not ob_retested:
        bearish_factors.append("CVD Divergence 1H: BEARISH")
        kill_score_penalty += 10

    # KILL SIGNAL 5: CVD Score très faible = Sellers dominating
    if cvd_combined < 25:
        kill_signals.append(f"🚨 CVD TRÈS FAIBLE: {cvd_combined}/100 - Pression vendeuse forte")
        kill_score_penalty += 15

    # BTC correlation removed from analysis - no kill signal for BTC

    # KILL SIGNAL 6: Entry Signal at CVD is WARNING or DANGER
    cvd_entry_signal_1h = alert_data.get('cvd_1h_at_entry_signal', 'NEUTRAL')
    if cvd_entry_signal_1h in ['WARNING', 'DANGER']:
        kill_signals.append(f"🚨 CVD ENTRY SIGNAL: {cvd_entry_signal_1h} - Volume non confirmatif")
        bearish_factors.append(f"CVD Entry: {cvd_entry_signal_1h}")
        kill_score_penalty += 10

    # KILL SIGNAL 7: ADX shows RANGING at entry with negative DI spread
    adx_1h_at_entry = alert_data.get('adx_1h_at_entry', 25) or 25
    if adx_1h_at_entry < 20 and di_spread_at_entry_1h < 0:
        kill_signals.append(f"🚨 RANGING + DI NÉGATIF: ADX={adx_1h_at_entry:.0f} avec DI->{di_spread_at_entry_1h:.1f}")
        bearish_factors.append("Marché sans trend + baissier")
        kill_score_penalty += 15

    # Store kill signals count
    kill_signal_count = len(kill_signals)

    # ═══════════════════════════════════════════════════════════════════════════════
    # 8. FINAL DECISION CALCULATION
    # ═══════════════════════════════════════════════════════════════════════════════

    # Weight factors for final score
    weights = {
        'cvd': 0.20,        # 20% - Volume delta analysis
        'adx': 0.15,        # 15% - Trend strength
        'trend': 0.15,      # 15% - GB Power / V3 Quality
        'momentum': 0.20,   # 20% - MEGA BUY + oscillators
        'volume': 0.15,     # 15% - Volume confirmation
        'confluence': 0.15, # 15% - Multi-factor alignment
    }

    final_score = int(
        (result['agent_cvd_score'] * weights['cvd']) +
        (result['agent_adx_score'] * weights['adx']) +
        (result['agent_trend_score'] * weights['trend']) +
        (result['agent_momentum_score'] * weights['momentum']) +
        (result['agent_volume_score'] * weights['volume']) +
        (result['agent_confluence_score'] * weights['confluence'])
    )

    # ═══════════════════════════════════════════════════════════════════════════════
    # APPLY KILL SIGNAL PENALTIES
    # These penalties are applied AFTER base score calculation
    # ═══════════════════════════════════════════════════════════════════════════════
    original_score = final_score
    final_score = max(0, final_score - kill_score_penalty)

    result['agent_score'] = final_score
    result['agent_bullish_count'] = len(bullish_factors)
    result['agent_bearish_count'] = len(bearish_factors)
    result['agent_neutral_count'] = len(neutral_factors)

    # Determine decision based on score and factor balance
    bullish_weight = len(bullish_factors)
    bearish_weight = len(bearish_factors)
    factor_balance = bullish_weight - bearish_weight

    # Calculate confidence (higher when factors are decisive one way)
    if factor_balance > 0:
        confidence = min(100, 50 + (factor_balance * 8) + (final_score - 50))
    elif factor_balance < 0:
        confidence = max(0, 50 + (factor_balance * 8) - (50 - final_score))
    else:
        confidence = max(30, min(70, final_score))

    result['agent_confidence'] = int(confidence)

    # ═══════════════════════════════════════════════════════════════════════════════
    # OB RETEST BONUS - Strong structural support that can override some warnings
    # ═══════════════════════════════════════════════════════════════════════════════
    ob_retest_bonus = 0
    fc_ob_score = alert_data.get('fc_ob_score', 0) or 0

    if ob_1h_retested and ob_4h_retested:
        ob_retest_bonus = 25  # Very strong - multi-TF OB confluence
        bullish_factors.append("OB CONFLUENCE: Retest 1H + 4H = Support institutionnel fort")
    elif ob_4h_retested:
        ob_retest_bonus = 20  # 4H OB is stronger timeframe
        bullish_factors.append("OB 4H RETESTÉ: Support institutionnel 4H")
    elif ob_1h_retested:
        ob_retest_bonus = 15  # 1H OB still good
        bullish_factors.append("OB 1H RETESTÉ: Support institutionnel 1H")

    # Add FC OB score bonus
    if fc_ob_score >= 80:
        ob_retest_bonus += 10
    elif fc_ob_score >= 60:
        ob_retest_bonus += 5

    # Apply OB bonus to final score (can partially offset kill penalties)
    final_score = min(100, final_score + ob_retest_bonus)
    result['agent_score'] = final_score

    # ═══════════════════════════════════════════════════════════════════════════════
    # KILL SIGNAL OVERRIDE - Force AVOID if critical red flags detected
    # BUT: OB retest can provide protection against some signals
    # ═══════════════════════════════════════════════════════════════════════════════
    force_avoid = False

    # Force AVOID if 3+ kill signals detected AND no OB retest protection
    if kill_signal_count >= 3 and not ob_retested:
        force_avoid = True
        result['agent_decision'] = 'AVOID'
        result['agent_grade'] = 'F'
        result['agent_confidence'] = min(result['agent_confidence'], 30)

    # If 3+ kill signals BUT OB is retested, downgrade to HOLD instead of AVOID
    elif kill_signal_count >= 3 and ob_retested:
        force_avoid = True
        result['agent_decision'] = 'HOLD'
        result['agent_grade'] = 'C'
        result['agent_confidence'] = min(result['agent_confidence'], 50)
        bullish_factors.append("OB PROTECTION: Kill signals atténués par retest OB")

    # Force AVOID if DI spread is strongly negative on BOTH timeframes AT BREAKOUT (not just entry)
    elif di_spread_at_breakout_1h < -10 and di_spread_at_breakout_4h < -5:
        force_avoid = True
        result['agent_decision'] = 'AVOID'
        result['agent_grade'] = 'F'
        result['agent_confidence'] = min(result['agent_confidence'], 25)

    # Force AVOID if delay >50h AND another kill signal AND no OB protection
    elif hours_to_entry > 50 and kill_signal_count >= 1 and not ob_retested:
        force_avoid = True
        result['agent_decision'] = 'AVOID'
        result['agent_grade'] = 'D'
        result['agent_confidence'] = min(result['agent_confidence'], 35)

    # If delay >50h but OB is retested, allow HOLD
    elif hours_to_entry > 50 and ob_retested:
        if final_score >= 50:
            # OB retest gives some protection
            result['agent_decision'] = 'HOLD'
            result['agent_grade'] = 'B'
        else:
            result['agent_decision'] = 'HOLD'
            result['agent_grade'] = 'C'

    # Force HOLD if 2 kill signals without OB protection
    elif kill_signal_count >= 2 and not ob_retested:
        force_avoid = True  # Prevents BUY
        if final_score >= 40:
            result['agent_decision'] = 'HOLD'
            result['agent_grade'] = 'C'
        else:
            result['agent_decision'] = 'AVOID'
            result['agent_grade'] = 'D'

    # 2 kill signals BUT with OB protection = can still consider entry
    elif kill_signal_count >= 2 and ob_retested and final_score >= 50:
        # OB provides enough protection to consider entry
        result['agent_decision'] = 'HOLD'
        result['agent_grade'] = 'B'
        bullish_factors.append("OB MITIGATION: Warnings présents mais OB retesté")

    # Normal decision flow if no force_avoid
    if not force_avoid:
        # Decision thresholds - stricter than before
        if final_score >= 75 and bullish_weight >= 8 and bearish_weight <= 2 and kill_signal_count == 0:
            result['agent_decision'] = 'STRONG_BUY'
            result['agent_grade'] = 'A+'
        elif final_score >= 65 and bullish_weight >= 6 and bearish_weight <= 3 and kill_signal_count == 0:
            result['agent_decision'] = 'BUY'
            result['agent_grade'] = 'A'
        elif final_score >= 55 and bullish_weight >= 4 and bearish_weight <= 4 and kill_signal_count <= 1:
            result['agent_decision'] = 'BUY'
            result['agent_grade'] = 'B+'
        elif final_score >= 45 and bullish_weight > bearish_weight:
            result['agent_decision'] = 'HOLD'
            result['agent_grade'] = 'B'
        elif final_score >= 35:
            result['agent_decision'] = 'HOLD'
            result['agent_grade'] = 'C'
        elif final_score >= 25 and bearish_weight > bullish_weight:
            result['agent_decision'] = 'AVOID'
            result['agent_grade'] = 'D'
        else:
            result['agent_decision'] = 'AVOID'
            result['agent_grade'] = 'F'

    # Generate reasoning
    reasoning_parts = []

    # Summary
    decision_labels = {
        'STRONG_BUY': '🚀 ACHAT FORT',
        'BUY': '✅ ACHAT',
        'HOLD': '⏸️ ATTENDRE',
        'AVOID': '❌ ÉVITER'
    }

    reasoning_parts.append(f"DÉCISION: {decision_labels.get(result['agent_decision'], result['agent_decision'])}")
    reasoning_parts.append(f"Score Global: {final_score}/100 (Grade: {result['agent_grade']})")
    if kill_score_penalty > 0 or ob_retest_bonus > 0:
        score_detail = f"Score Base: {original_score}/100"
        if kill_score_penalty > 0:
            score_detail += f" - Pénalité: {kill_score_penalty}"
        if ob_retest_bonus > 0:
            score_detail += f" + OB Bonus: {ob_retest_bonus}"
        reasoning_parts.append(score_detail)
    reasoning_parts.append(f"Confiance: {result['agent_confidence']}%")
    reasoning_parts.append("")

    # OB RETEST STATUS (important context)
    if ob_retested:
        reasoning_parts.append("🛡️ OB RETEST PROTECTION:")
        if ob_1h_retested and ob_4h_retested:
            reasoning_parts.append("  ✅ OB 1H + 4H retestés = Support institutionnel FORT")
        elif ob_4h_retested:
            reasoning_parts.append("  ✅ OB 4H retesté = Support institutionnel solide")
        elif ob_1h_retested:
            reasoning_parts.append("  ✅ OB 1H retesté = Support institutionnel")
        reasoning_parts.append(f"  FC OB Score: {fc_ob_score}/100")
        reasoning_parts.append("")

    # KILL SIGNALS SECTION (if any)
    if kill_signals:
        reasoning_parts.append(f"⛔ KILL SIGNALS DÉTECTÉS ({len(kill_signals)}):")
        for signal in kill_signals:
            reasoning_parts.append(f"  {signal}")
        reasoning_parts.append("")

    # Component scores summary
    reasoning_parts.append("📊 SCORES PAR COMPOSANT:")
    reasoning_parts.append(f"  • CVD (Volume Delta): {result['agent_cvd_score']}/100")
    reasoning_parts.append(f"  • ADX/DI (Trend): {result['agent_adx_score']}/100")
    reasoning_parts.append(f"  • GB Power (Setup): {result['agent_trend_score']}/100")
    reasoning_parts.append(f"  • Momentum: {result['agent_momentum_score']}/100")
    reasoning_parts.append(f"  • Volume: {result['agent_volume_score']}/100")
    reasoning_parts.append(f"  • Confluence: {result['agent_confluence_score']}/100")
    reasoning_parts.append("")

    # DI Spread analysis (show both breakout and entry)
    reasoning_parts.append("📈 DI SPREAD ANALYSE:")
    reasoning_parts.append("  Breakout (moment clé):")
    spread_bo_1h_status = "✅" if di_spread_at_breakout_1h > 0 else "⚠️" if di_spread_at_breakout_1h > -10 else "❌"
    spread_bo_4h_status = "✅" if di_spread_at_breakout_4h > 0 else "⚠️" if di_spread_at_breakout_4h > -10 else "❌"
    reasoning_parts.append(f"    1H: {spread_bo_1h_status} {di_spread_at_breakout_1h:+.1f}")
    reasoning_parts.append(f"    4H: {spread_bo_4h_status} {di_spread_at_breakout_4h:+.1f}")
    reasoning_parts.append("  Entry/Retest:")
    spread_1h_status = "✅" if di_spread_at_entry_1h > 0 else "⚠️ Pullback" if ob_retested else "❌"
    spread_4h_status = "✅" if di_spread_at_entry_4h > 0 else "⚠️" if di_spread_at_entry_4h > -10 else "❌"
    reasoning_parts.append(f"    1H: {spread_1h_status} {di_spread_at_entry_1h:+.1f}")
    reasoning_parts.append(f"    4H: {spread_4h_status} {di_spread_at_entry_4h:+.1f}")
    if ob_retested and di_spread_at_entry_1h < 0 and di_spread_at_breakout_1h > 0:
        reasoning_parts.append("  ℹ️ DI- domine au retest = pullback normal si OB support")
    reasoning_parts.append("")

    # Factors breakdown
    if bullish_factors:
        reasoning_parts.append(f"✅ FACTEURS HAUSSIERS ({len(bullish_factors)}):")
        for factor in bullish_factors[:6]:  # Limit to top 6
            reasoning_parts.append(f"  • {factor}")
        reasoning_parts.append("")

    if bearish_factors:
        reasoning_parts.append(f"❌ FACTEURS BAISSIERS ({len(bearish_factors)}):")
        for factor in bearish_factors[:6]:  # Increased from 4 to 6
            reasoning_parts.append(f"  • {factor}")
        reasoning_parts.append("")

    # Final verdict with context
    if result['agent_decision'] == 'STRONG_BUY':
        reasoning_parts.append("🎯 VERDICT: Setup de haute qualité avec confluence multi-TF. Entrée recommandée.")
    elif result['agent_decision'] == 'BUY':
        reasoning_parts.append("🎯 VERDICT: Setup solide avec bons indicateurs. Entrée possible avec gestion du risque.")
    elif result['agent_decision'] == 'HOLD':
        if kill_signal_count > 0:
            reasoning_parts.append(f"🎯 VERDICT: {kill_signal_count} signal(s) d'alerte détecté(s). NE PAS ENTRER - Attendre setup plus propre.")
        else:
            reasoning_parts.append("🎯 VERDICT: Signaux mixtes. Attendre une meilleure opportunité ou confirmation.")
    else:
        if kill_signal_count >= 3:
            reasoning_parts.append(f"🎯 VERDICT: {kill_signal_count} KILL SIGNALS! Ce trade a une forte probabilité de perte. ÉVITER ABSOLUMENT.")
        elif kill_signal_count >= 2:
            reasoning_parts.append(f"🎯 VERDICT: {kill_signal_count} signaux critiques détectés. Trop risqué - ÉVITER ce trade.")
        else:
            reasoning_parts.append("🎯 VERDICT: Trop de signaux négatifs. Éviter ce trade.")

    result['agent_reasoning'] = '\n'.join(reasoning_parts)
    result['agent_bullish_factors'] = json.dumps(bullish_factors, ensure_ascii=False)
    result['agent_bearish_factors'] = json.dumps(bearish_factors, ensure_ascii=False)

    return result


def calc_dmi(high, low, close, dmi_len=14, adx_smooth=14):
    n = len(close)
    tr = np.zeros(n)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
        up_move = high[i] - high[i-1]
        down_move = low[i-1] - low[i]
        plus_dm[i] = up_move if up_move > down_move and up_move > 0 else 0
        minus_dm[i] = down_move if down_move > up_move and down_move > 0 else 0
    atr = np.zeros(n)
    smooth_plus = np.zeros(n)
    smooth_minus = np.zeros(n)
    if dmi_len < n:
        atr[dmi_len] = np.mean(tr[1:dmi_len+1])
        smooth_plus[dmi_len] = np.mean(plus_dm[1:dmi_len+1])
        smooth_minus[dmi_len] = np.mean(minus_dm[1:dmi_len+1])
    for i in range(dmi_len+1, n):
        atr[i] = (atr[i-1] * (dmi_len - 1) + tr[i]) / dmi_len
        smooth_plus[i] = (smooth_plus[i-1] * (dmi_len - 1) + plus_dm[i]) / dmi_len
        smooth_minus[i] = (smooth_minus[i-1] * (dmi_len - 1) + minus_dm[i]) / dmi_len
    plus_di = np.zeros(n)
    minus_di = np.zeros(n)
    for i in range(dmi_len, n):
        if atr[i] > 0:
            plus_di[i] = 100 * smooth_plus[i] / atr[i]
            minus_di[i] = 100 * smooth_minus[i] / atr[i]
    return plus_di, minus_di


def calc_supertrend(high, low, close, factor=3.0, period=10):
    n = len(close)
    if n < period + 1:
        return np.zeros(n), np.zeros(n)
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = np.zeros(n)
    if period < n:
        atr[period] = np.mean(tr[1:period+1])
    for i in range(period+1, n):
        atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    hl2 = (high + low) / 2
    upper_band = hl2 + factor * atr
    lower_band = hl2 - factor * atr
    direction = np.ones(n)
    final_upper = np.copy(upper_band)
    final_lower = np.copy(lower_band)
    for i in range(period + 1, n):
        if final_lower[i] < final_lower[i-1] and close[i-1] > final_lower[i-1]:
            final_lower[i] = final_lower[i-1]
        if final_upper[i] > final_upper[i-1] and close[i-1] < final_upper[i-1]:
            final_upper[i] = final_upper[i-1]
        if direction[i-1] == 1:
            direction[i] = -1 if close[i] > final_upper[i-1] else 1
        else:
            direction[i] = 1 if close[i] < final_lower[i-1] else -1
    return direction, np.zeros(n)


def calc_adaptive_stochastic(close, length=50, fast=50, slow=200):
    n = len(close)
    if n < slow + 1:
        return np.full(n, np.nan)
    src = np.full(n, np.nan)
    diff = abs(slow - fast)
    for i in range(diff, n):
        x = np.arange(diff)
        y = close[i-diff+1:i+1]
        if len(y) == diff:
            slope, intercept = np.polyfit(x, y, 1)
            src[i] = intercept + slope * (diff - 1)
    sc = np.full(n, np.nan)
    for i in range(length, n):
        change_sum = np.sum(np.abs(np.diff(close[i-length:i+1])))
        sc[i] = abs(close[i] - close[i-length]) / change_sum if change_sum > 0 else 0
    stc = np.full(n, np.nan)
    for i in range(max(slow, length), n):
        if np.isnan(src[i]) or np.isnan(sc[i]):
            continue
        src_fast = src[max(0, i-fast+1):i+1]
        src_slow = src[max(0, i-slow+1):i+1]
        src_fast = src_fast[~np.isnan(src_fast)]
        src_slow = src_slow[~np.isnan(src_slow)]
        if len(src_fast) == 0 or len(src_slow) == 0:
            continue
        a = sc[i] * np.max(src_fast) + (1 - sc[i]) * np.max(src_slow)
        b = sc[i] * np.min(src_fast) + (1 - sc[i]) * np.min(src_slow)
        stc[i] = (src[i] - b) / (a - b) if a != b else 0.5
    return stc


def calc_lazybar(high, low, close):
    n = len(close)
    ht = np.full(n, np.nan)
    for i in range(4, n):
        middle = sum([high[i-j] + low[i-j] for j in range(5)]) / 10
        scale = sum([high[i-j] - low[i-j] for j in range(5)]) / 5 * 0.2
        if scale != 0:
            ht[i] = (close[i] - middle) / scale
    return ht


def calc_atr_vol_regime(high, low, close, volume, config):
    n = len(close)
    atr_len = config['AV_ATR_LEN']
    atr_smooth = config['AV_ATR_SMOOTH']
    vol_len = config['AV_VOL_LEN']

    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr_raw = np.zeros(n)
    if atr_len < n:
        atr_raw[atr_len] = np.mean(tr[1:atr_len+1])
    for i in range(atr_len+1, n):
        atr_raw[i] = (atr_raw[i-1] * (atr_len - 1) + tr[i]) / atr_len
    atr = np.zeros(n)
    if atr_smooth < n:
        atr[atr_smooth] = atr_raw[atr_smooth]
    mult = 2 / (atr_smooth + 1)
    for i in range(atr_smooth+1, n):
        atr[i] = atr_raw[i] * mult + atr[i-1] * (1 - mult)
    atr_slope = np.zeros(n)
    for i in range(1, n):
        if atr[i-1] > 0:
            atr_slope[i] = (atr[i] - atr[i-1]) / atr[i-1] * 100
    vol_ma = np.zeros(n)
    for i in range(vol_len, n):
        vol_ma[i] = np.mean(volume[i-vol_len+1:i+1])
    vol_ratio = np.zeros(n)
    vol_change = np.zeros(n)
    for i in range(vol_len, n):
        if vol_ma[i] > 0:
            vol_ratio[i] = volume[i] / vol_ma[i]
            vol_change[i] = (volume[i] - volume[i-1]) / vol_ma[i] * 100
    atr_regime = np.zeros(n)
    vol_regime = np.zeros(n)
    av_regime = np.zeros(n)
    for i in range(1, n):
        if atr_slope[i] > config['AV_ATR_THRESHOLD']:
            atr_regime[i] = 1
        elif atr_slope[i] < -config['AV_ATR_THRESHOLD']:
            atr_regime[i] = -1
        if vol_ratio[i] > config['AV_VOL_THRESHOLD']:
            vol_regime[i] = 1
        elif vol_ratio[i] < 0.8:
            vol_regime[i] = -1
        if atr_regime[i] == 1 and vol_regime[i] == 1:
            av_regime[i] = 1
        elif atr_regime[i] == -1 and vol_regime[i] == -1:
            av_regime[i] = -1
    vol_move = np.abs(vol_change)
    return av_regime, vol_change, vol_move, vol_ratio


def calc_pp_supertrend(high, low, close, prd=2, factor=3, pd_atr=10):
    n = len(close)
    ph = np.full(n, np.nan)
    pl = np.full(n, np.nan)
    for i in range(prd, n - prd):
        is_ph = True
        is_pl = True
        for j in range(1, prd + 1):
            if high[i] <= high[i-j] or high[i] <= high[i+j]:
                is_ph = False
            if low[i] >= low[i-j] or low[i] >= low[i+j]:
                is_pl = False
        if is_ph:
            ph[i] = high[i]
        if is_pl:
            pl[i] = low[i]
    center = np.zeros(n)
    last_pp = np.nan
    for i in range(n):
        if not np.isnan(ph[i]):
            last_pp = ph[i]
        if not np.isnan(pl[i]):
            last_pp = pl[i]
        if not np.isnan(last_pp):
            if center[i-1] == 0:
                center[i] = last_pp
            else:
                center[i] = (center[i-1] * 2 + last_pp) / 3
        elif i > 0:
            center[i] = center[i-1]
    tr = np.zeros(n)
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i-1]), abs(low[i] - close[i-1]))
    atr = np.zeros(n)
    if pd_atr < n:
        atr[pd_atr] = np.mean(tr[1:pd_atr+1])
    for i in range(pd_atr+1, n):
        atr[i] = (atr[i-1] * (pd_atr - 1) + tr[i]) / pd_atr
    TUp = np.zeros(n)
    TDown = np.zeros(n)
    Trend = np.ones(n)
    for i in range(1, n):
        Up = center[i] - factor * atr[i]
        Dn = center[i] + factor * atr[i]
        if close[i-1] > TUp[i-1]:
            TUp[i] = max(Up, TUp[i-1])
        else:
            TUp[i] = Up
        if close[i-1] < TDown[i-1]:
            TDown[i] = min(Dn, TDown[i-1])
        else:
            TDown[i] = Dn
        if close[i] > TDown[i-1]:
            Trend[i] = 1
        elif close[i] < TUp[i-1]:
            Trend[i] = -1
        else:
            Trend[i] = Trend[i-1]
    return Trend


def calc_ec_rsi(close, period=50, slow_period=50):
    n = len(close)
    if n < period + 1:
        return np.full(n, np.nan), np.full(n, np.nan)
    delta = np.diff(close)
    gains = np.where(delta > 0, delta, 0)
    losses = np.where(delta < 0, -delta, 0)
    rsi = np.full(n, np.nan)
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, n):
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
        if i < n - 1:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    slow_ma = np.full(n, np.nan)
    for i in range(slow_period, n):
        valid_rsi = rsi[i-slow_period+1:i+1]
        valid_rsi = valid_rsi[~np.isnan(valid_rsi)]
        if len(valid_rsi) > 0:
            slow_ma[i] = np.mean(valid_rsi)
    return rsi, slow_ma


def calc_swing_highs(high, left=10, right=5):
    n = len(high)
    swing_highs = []
    for i in range(left, n - right):
        is_pivot = True
        for j in range(1, left + 1):
            if high[i-j] >= high[i]:
                is_pivot = False
                break
        if is_pivot:
            for j in range(1, right + 1):
                if i + j < n and high[i+j] >= high[i]:
                    is_pivot = False
                    break
        if is_pivot:
            swing_highs.append({'idx': i, 'price': high[i]})
    return swing_highs


def find_pivot_highs_luxalgo(high, swing_len):
    n = len(high)
    pivots = []
    for i in range(swing_len, n - swing_len):
        is_pivot = True
        for j in range(1, swing_len + 1):
            if high[i - j] > high[i]:
                is_pivot = False
                break
        if is_pivot:
            for j in range(1, swing_len + 1):
                if i + j < n and high[i + j] >= high[i]:
                    is_pivot = False
                    break
        if is_pivot:
            pivots.append({'idx': i, 'price': high[i]})
    return pivots


def find_swing_highs(high, left=5, right=3):
    n = len(high)
    swing_highs = []
    for i in range(left, n - right):
        is_pivot = True
        for j in range(i - left, i):
            if high[j] > high[i]:
                is_pivot = False
                break
        if is_pivot:
            for j in range(i + 1, i + right + 1):
                if j < n and high[j] >= high[i]:
                    is_pivot = False
                    break
        if is_pivot:
            swing_highs.append({'idx': i, 'price': high[i]})
    return swing_highs


def count_tl_prior_false_breaks(close, tl, start_idx, end_idx, confirm_bars=2):
    """
    Count prior FALSE BREAKS on a trendline before the final break.

    A FALSE BREAK is defined as:
    1. Price closes ABOVE the TL for at least 1 bar
    2. Price then closes BELOW the TL again

    This pattern (break above → fall below) makes the TL "worn out" and unreliable.

    Args:
        close: Array of close prices
        tl: Trendline dict with 'p1_idx', 'p1_price', 'slope'
        start_idx: Index to start checking (usually signal bar)
        end_idx: Index of the final break (we check BEFORE this)
        confirm_bars: Number of bars price must stay above TL to count as "break"
                      (default 2 = even quick breaks above/below count as false breaks)

    Returns:
        tuple: (false_break_count, list of false break details)
    """
    false_breaks = []
    i = start_idx

    while i < end_idx:
        # Calculate TL price at this bar
        tl_price = tl['p1_price'] + tl['slope'] * (i - tl['p1_idx'])

        # Check if price breaks above TL
        if close[i] > tl_price:
            break_start_idx = i
            break_start_price = close[i]
            bars_above = 1

            # Count how many bars price stays above TL
            j = i + 1
            while j < end_idx:
                tl_price_j = tl['p1_price'] + tl['slope'] * (j - tl['p1_idx'])
                if close[j] > tl_price_j:
                    bars_above += 1
                    j += 1
                else:
                    # Price fell back below TL - this is a FALSE BREAK
                    false_breaks.append({
                        'break_idx': break_start_idx,
                        'break_price': break_start_price,
                        'bars_above': bars_above,
                        'fall_idx': j,
                        'fall_price': close[j]
                    })
                    i = j  # Continue from where price fell back
                    break
            else:
                # Price stayed above until end_idx - this is the FINAL break, not a false break
                break

        i += 1

    return len(false_breaks), false_breaks


def get_lazybar_color(lz_value):
    """
    Get LazyBar color based on value.
    - Orange: value >= 9.6 (strong bullish)
    - Yellow: value >= 6 (bullish)
    - Green: value >= 0 (neutral bullish)
    - Red: value < 0 (bearish)
    """
    if lz_value is None or np.isnan(lz_value):
        return None
    if abs(lz_value) >= 9.6:
        return "Orange"
    elif abs(lz_value) >= 6:
        return "Yellow"
    elif lz_value >= 0:
        return "Green"
    else:
        return "Red"


def get_lazybar_move(lz_current, lz_prev):
    """
    Get LazyBar move indicator.
    - 🟣 Purple: Strong spike (move >= 6)
    - 🔴 Red: Moderate move (move >= 3)
    - None: No significant move
    """
    if lz_current is None or lz_prev is None:
        return None
    if np.isnan(lz_current) or np.isnan(lz_prev):
        return None
    move = abs(lz_current - lz_prev)
    if move >= 6:
        return "🟣"
    elif move >= 3:
        return "🔴"
    return None


def calculate_mega_buy_details(data, indicators_full, mb_dt, config):
    """
    Calculate full MEGA BUY indicator details for all timeframes (15m, 30m, 1h, 4h).

    Returns structure:
    {
        "dmi": {"15m": {"di_plus_move": x, "di_minus_move": x, "adx_move": x, "di_plus": x, "di_minus": x, "adx": x}, ...},
        "rsi": {"15m": {"rsi_move": x, "rsi_value": x, "rsi_signal": x}, ...},
        "volume": {"15m": {"vol_pct": x}, ...},
        "lazybar": {"15m": {"lz_value": x, "lz_color": "Orange", "lz_move": "🟣"}, ...},
        "ec": {"15m": {"ec_move": x}, ...}
    }
    """
    details = {
        "dmi": {},
        "rsi": {},
        "volume": {},
        "lazybar": {},
        "ec": {}
    }

    for tf in ["15m", "30m", "1h", "4h"]:
        if tf not in data or tf not in indicators_full:
            # Initialize empty values for missing TF
            details["dmi"][tf] = {"di_plus_move": None, "di_minus_move": None, "adx_move": None, "di_plus": None, "di_minus": None, "adx": None}
            details["rsi"][tf] = {"rsi_move": None, "rsi_value": None, "rsi_signal": None}
            details["volume"][tf] = {"vol_pct": None}
            details["lazybar"][tf] = {"lz_value": None, "lz_color": None, "lz_move": None}
            details["ec"][tf] = {"ec_move": None}
            continue

        df_tf = data[tf]
        ind_tf = indicators_full[tf]

        # Find closest index to alert datetime
        closest_idx = None
        for i, row in df_tf.iterrows():
            if row['datetime'] <= mb_dt:
                closest_idx = i

        if closest_idx is None or closest_idx < 1:
            details["dmi"][tf] = {"di_plus_move": None, "di_minus_move": None, "adx_move": None, "di_plus": None, "di_minus": None, "adx": None}
            details["rsi"][tf] = {"rsi_move": None, "rsi_value": None, "rsi_signal": None}
            details["volume"][tf] = {"vol_pct": None}
            details["lazybar"][tf] = {"lz_value": None, "lz_color": None, "lz_move": None}
            details["ec"][tf] = {"ec_move": None}
            continue

        # DMI/ADX data
        di_plus = ind_tf.get('plus_di')
        di_minus = ind_tf.get('minus_di')
        adx = ind_tf.get('adx')

        di_plus_val = float(di_plus[closest_idx]) if di_plus is not None and closest_idx < len(di_plus) and not np.isnan(di_plus[closest_idx]) else None
        di_minus_val = float(di_minus[closest_idx]) if di_minus is not None and closest_idx < len(di_minus) and not np.isnan(di_minus[closest_idx]) else None
        adx_val = float(adx[closest_idx]) if adx is not None and closest_idx < len(adx) and not np.isnan(adx[closest_idx]) else None

        di_plus_prev = float(di_plus[closest_idx-1]) if di_plus is not None and closest_idx-1 < len(di_plus) and not np.isnan(di_plus[closest_idx-1]) else None
        di_minus_prev = float(di_minus[closest_idx-1]) if di_minus is not None and closest_idx-1 < len(di_minus) and not np.isnan(di_minus[closest_idx-1]) else None
        adx_prev = float(adx[closest_idx-1]) if adx is not None and closest_idx-1 < len(adx) and not np.isnan(adx[closest_idx-1]) else None

        di_plus_move = round(di_plus_val - di_plus_prev, 1) if di_plus_val is not None and di_plus_prev is not None else None
        di_minus_move = round(di_minus_val - di_minus_prev, 1) if di_minus_val is not None and di_minus_prev is not None else None
        adx_move = round(adx_val - adx_prev, 1) if adx_val is not None and adx_prev is not None else None

        details["dmi"][tf] = {
            "di_plus_move": di_plus_move,
            "di_minus_move": di_minus_move,
            "adx_move": adx_move,
            "di_plus": round(di_plus_val, 1) if di_plus_val is not None else None,
            "di_minus": round(di_minus_val, 1) if di_minus_val is not None else None,
            "adx": round(adx_val, 1) if adx_val is not None else None
        }

        # RSI data
        rsi = ind_tf.get('rsi')
        rsi_val = float(rsi[closest_idx]) if rsi is not None and closest_idx < len(rsi) and not np.isnan(rsi[closest_idx]) else None
        rsi_prev = float(rsi[closest_idx-1]) if rsi is not None and closest_idx-1 < len(rsi) and not np.isnan(rsi[closest_idx-1]) else None
        rsi_move = round(rsi_val - rsi_prev, 1) if rsi_val is not None and rsi_prev is not None else None

        # RSI Signal (for 4H primarily)
        rsi_signal = None
        if rsi_val is not None:
            if rsi_val >= 70:
                rsi_signal = "OVERBOUGHT"
            elif rsi_val <= 30:
                rsi_signal = "OVERSOLD"
            else:
                rsi_signal = round(rsi_val, 1)

        details["rsi"][tf] = {
            "rsi_move": rsi_move,
            "rsi_value": round(rsi_val, 1) if rsi_val is not None else None,
            "rsi_signal": rsi_signal
        }

        # Volume % (current volume vs avg20)
        vol_avg = ind_tf.get('vol_avg')
        volume = df_tf['volume'].values
        vol_current = float(volume[closest_idx]) if closest_idx < len(volume) else None
        vol_avg_val = float(vol_avg[closest_idx]) if vol_avg is not None and closest_idx < len(vol_avg) and not np.isnan(vol_avg[closest_idx]) else None

        vol_pct = None
        if vol_current is not None and vol_avg_val is not None and vol_avg_val > 0:
            vol_pct = int(round((vol_current / vol_avg_val) * 100))

        details["volume"][tf] = {"vol_pct": vol_pct}

        # LazyBar
        lazybar = ind_tf.get('lazybar')
        lz_val = float(lazybar[closest_idx]) if lazybar is not None and closest_idx < len(lazybar) and not np.isnan(lazybar[closest_idx]) else None
        lz_prev = float(lazybar[closest_idx-1]) if lazybar is not None and closest_idx-1 < len(lazybar) and not np.isnan(lazybar[closest_idx-1]) else None

        lz_color = get_lazybar_color(lz_val)
        lz_move = get_lazybar_move(lz_val, lz_prev)

        # Format lz_value with arrow if positive
        lz_display = None
        if lz_val is not None:
            if lz_val > 0:
                lz_display = f"⬆️ {round(abs(lz_val), 1)}"
            else:
                lz_display = f"⬇️ {round(abs(lz_val), 1)}"

        details["lazybar"][tf] = {
            "lz_value": lz_display,
            "lz_raw": round(lz_val, 1) if lz_val is not None else None,
            "lz_color": lz_color,
            "lz_move": lz_move
        }

        # EC RSI Move
        ec_rsi = ind_tf.get('ec_rsi')
        ec_val = float(ec_rsi[closest_idx]) if ec_rsi is not None and closest_idx < len(ec_rsi) and not np.isnan(ec_rsi[closest_idx]) else None
        ec_prev = float(ec_rsi[closest_idx-1]) if ec_rsi is not None and closest_idx-1 < len(ec_rsi) and not np.isnan(ec_rsi[closest_idx-1]) else None
        ec_move = round(ec_val - ec_prev, 1) if ec_val is not None and ec_prev is not None else None

        details["ec"][tf] = {"ec_move": ec_move}

    return details


def detect_foreign_candle_ob(df, open_prices, high, low, close,
                              min_before=2, min_after=2, lookback=100):
    """
    Detect "Foreign Candle" Order Blocks - SMC Pattern

    A Foreign Candle is a candle of different color (direction) that appears
    within a sequence of same-colored candles. This often represents:
    - Institutional entry point
    - Demand/Supply zone
    - High-probability retest area

    Pattern Types:
    1. BULLISH OB: Bearish candle surrounded by bullish candles (like in CVXUSDT chart)
       - Red candle inside green candles = demand zone
       - When price returns to this zone after breakout, expect bounce

    2. BEARISH OB: Bullish candle surrounded by bearish candles
       - Green candle inside red candles = supply zone
       - When price returns to this zone after breakdown, expect rejection

    Parameters:
    - df: DataFrame with datetime column
    - open_prices, high, low, close: Price arrays
    - min_before: Minimum same-color candles before foreign candle (default 2)
    - min_after: Minimum same-color candles after foreign candle (default 2)
    - lookback: How many bars to look back for OBs (default 100)

    Returns: List of Order Blocks with:
    - idx: Index of the foreign candle
    - datetime: Datetime of the foreign candle
    - type: 'BULLISH' or 'BEARISH'
    - zone_high: High of the foreign candle (resistance level for bullish OB)
    - zone_low: Low of the foreign candle (support level for bullish OB)
    - zone_mid: Midpoint of the zone
    - strength: How many same-color candles surrounded it (more = stronger)
    - before_count: Count of same-color candles before
    - after_count: Count of same-color candles after
    """
    n = len(close)
    if n < min_before + min_after + 1:
        return []

    order_blocks = []
    start_idx = max(0, n - lookback)

    # Determine candle colors (bullish = green, bearish = red)
    # True = bullish (close > open), False = bearish (close < open)
    is_bullish = close > open_prices

    for i in range(start_idx + min_before, n - min_after):
        current_color = is_bullish[i]

        # Count same-color candles BEFORE this candle (looking for opposite color)
        before_count = 0
        for j in range(i - 1, max(start_idx - 1, i - 10 - 1), -1):  # Look back up to 10 candles
            if is_bullish[j] != current_color:  # Opposite color
                before_count += 1
            else:
                break

        # Count same-color candles AFTER this candle
        after_count = 0
        for j in range(i + 1, min(n, i + 10 + 1)):  # Look forward up to 10 candles
            if is_bullish[j] != current_color:  # Opposite color
                after_count += 1
            else:
                break

        # Check if this is a foreign candle (surrounded by opposite color candles)
        if before_count >= min_before and after_count >= min_after:
            # This candle is "foreign" - different color from surrounding candles

            # Determine OB type based on foreign candle color:
            # - If foreign candle is BEARISH (red) and surrounded by BULLISH (green) = BULLISH OB (demand)
            # - If foreign candle is BULLISH (green) and surrounded by BEARISH (red) = BEARISH OB (supply)
            if current_color == False:  # Bearish foreign candle in bullish context
                ob_type = 'BULLISH'  # This is a demand zone
            else:  # Bullish foreign candle in bearish context
                ob_type = 'BEARISH'  # This is a supply zone

            # Get datetime if available
            dt = df.iloc[i]['datetime'] if 'datetime' in df.columns else None

            order_blocks.append({
                'idx': i,
                'datetime': dt,
                'type': ob_type,
                'zone_high': float(high[i]),
                'zone_low': float(low[i]),
                'zone_mid': float((high[i] + low[i]) / 2),
                'zone_range_pct': float((high[i] - low[i]) / low[i] * 100),
                'strength': before_count + after_count,
                'before_count': before_count,
                'after_count': after_count,
                'candle_body': abs(float(close[i] - open_prices[i])),
                'is_strong': before_count >= 3 and after_count >= 2,
            })

    return order_blocks


def find_ob_retest(price, ob_zones, direction='BULLISH', tolerance_pct=0.5):
    """
    Check if a price is retesting an Order Block zone.

    For BULLISH OB: Price should pull back and touch/enter the zone from above
    For BEARISH OB: Price should rally and touch/enter the zone from below

    Parameters:
    - price: Current price to check
    - ob_zones: List of Order Block dictionaries
    - direction: 'BULLISH' or 'BEARISH' to filter OB type
    - tolerance_pct: How far outside the zone to still consider a retest (%)

    Returns: The OB being retested (or None)
    """
    for ob in ob_zones:
        if ob['type'] != direction:
            continue

        zone_high = ob['zone_high']
        zone_low = ob['zone_low']
        tolerance = (zone_high - zone_low) * tolerance_pct / 100

        if direction == 'BULLISH':
            # For bullish OB, price should touch or enter zone from above
            # Valid retest: price low reaches zone_high or enters zone
            if price <= zone_high + tolerance and price >= zone_low - tolerance:
                return ob
        else:
            # For bearish OB, price should touch or enter zone from below
            # Valid retest: price high reaches zone_low or enters zone
            if price >= zone_low - tolerance and price <= zone_high + tolerance:
                return ob

    return None


def analyze_foreign_candle_ob(df_1h, df_4h, alert_idx_1h, tl_break_idx_1h,
                               entry_idx_1h, entry_price, retest_low,
                               lookback_1h=150, lookback_4h=80):
    """
    Full analysis of Foreign Candle Order Blocks for a trade setup.

    This function:
    1. Detects all Foreign Candle OBs in 1H and 4H data (before TL break)
    2. Checks if the retest/entry touched any BULLISH OB
    3. Returns scoring and details for the setup

    Parameters:
    - df_1h, df_4h: DataFrames with OHLC data
    - alert_idx_1h: Index of the MEGA BUY alert in 1H data
    - tl_break_idx_1h: Index of trendline break in 1H data
    - entry_idx_1h: Index of entry/retest in 1H data
    - entry_price: The entry price
    - retest_low: The low of the retest candle
    - lookback_1h, lookback_4h: How many bars to look back for OBs

    Returns: Dictionary with analysis results
    """
    result = {
        # 1H Foreign Candle OB
        'fc_ob_1h_found': False,
        'fc_ob_1h_count': 0,
        'fc_ob_1h_type': None,
        'fc_ob_1h_zone_high': None,
        'fc_ob_1h_zone_low': None,
        'fc_ob_1h_strength': None,
        'fc_ob_1h_retest': False,
        'fc_ob_1h_distance_pct': None,
        'fc_ob_1h_datetime': None,  # Datetime of the Foreign Candle
        'fc_ob_1h_in_zone': 0,       # OBs in retest zone
        'fc_ob_1h_retested': 0,      # OBs retested in zone
        'fc_ob_1h_all_obs': [],      # All OB details in zone

        # 4H Foreign Candle OB
        'fc_ob_4h_found': False,
        'fc_ob_4h_count': 0,
        'fc_ob_4h_type': None,
        'fc_ob_4h_zone_high': None,
        'fc_ob_4h_zone_low': None,
        'fc_ob_4h_strength': None,
        'fc_ob_4h_retest': False,
        'fc_ob_4h_distance_pct': None,
        'fc_ob_4h_datetime': None,  # Datetime of the Foreign Candle
        'fc_ob_4h_in_zone': 0,       # OBs in retest zone
        'fc_ob_4h_retested': 0,      # OBs retested in zone
        'fc_ob_4h_all_obs': [],      # All OB details in zone

        # Combined analysis
        'fc_ob_bonus': False,
        'fc_ob_score': 0,
        'fc_ob_label': 'NO_OB',
    }

    # ═══════════════════════════════════════════════════════════════════════════════
    # GET TL BREAK DATETIME FOR FILTERING OBs
    # Only OBs created BEFORE the TL break are valid
    # ═══════════════════════════════════════════════════════════════════════════════
    tl_break_datetime = None
    tl_break_price = None
    if tl_break_idx_1h is not None and df_1h is not None and tl_break_idx_1h < len(df_1h):
        tl_break_datetime = df_1h.iloc[tl_break_idx_1h]['open_time'] if 'open_time' in df_1h.columns else None
        tl_break_price = df_1h.iloc[tl_break_idx_1h]['close'] if 'close' in df_1h.columns else None

    # ═══════════════════════════════════════════════════════════════════════════════
    # 1H FOREIGN CANDLE ORDER BLOCK DETECTION
    # ═══════════════════════════════════════════════════════════════════════════════
    if df_1h is not None and len(df_1h) > 0 and alert_idx_1h is not None:
        # Look for OBs BEFORE the alert (institutional footprint before the move)
        search_end = min(alert_idx_1h + 5, len(df_1h))  # Include a few candles after alert
        search_start = max(0, alert_idx_1h - lookback_1h)

        if search_end > search_start:
            df_search = df_1h.iloc[search_start:search_end].reset_index(drop=True)

            obs_1h = detect_foreign_candle_ob(
                df=df_search,
                open_prices=df_search['open'].values,
                high=df_search['high'].values,
                low=df_search['low'].values,
                close=df_search['close'].values,
                min_before=1,  # Reduced from 2 to detect more OBs
                min_after=1,   # Reduced from 2 to detect more OBs
                lookback=len(df_search)
            )

            # Filter to BULLISH OBs only (demand zones for long entries)
            bullish_obs_1h = [ob for ob in obs_1h if ob['type'] == 'BULLISH']

            # ═══════════════════════════════════════════════════════════════
            # CRITICAL FILTER 1: Only OBs created BEFORE TL break are valid
            # OBs formed after TL break are NOT institutional footprints
            # ═══════════════════════════════════════════════════════════════
            if tl_break_datetime is not None:
                bullish_obs_1h = [ob for ob in bullish_obs_1h
                                  if ob.get('datetime') is not None and ob['datetime'] < tl_break_datetime]

            # ═══════════════════════════════════════════════════════════════
            # CRITICAL FILTER 2: OB must be BELOW TL break price
            # For bullish retest, the OB zone must be below the breakout level
            # This ensures the OB is a demand zone that price pulls back TO
            # ═══════════════════════════════════════════════════════════════
            if tl_break_price is not None:
                bullish_obs_1h = [ob for ob in bullish_obs_1h
                                  if ob['zone_high'] < tl_break_price * 1.02]  # 2% tolerance

            # IMPORTANT: For bullish retest, OB must be BELOW entry price (demand zone)
            # Price pulls back DOWN to retest the OB zone, then bounces up
            reference_price = retest_low if retest_low is not None else entry_price
            if reference_price is not None:
                bullish_obs_1h = [ob for ob in bullish_obs_1h if ob['zone_high'] <= reference_price * 1.02]  # 2% tolerance

            if bullish_obs_1h:
                result['fc_ob_1h_found'] = True
                result['fc_ob_1h_count'] = len(bullish_obs_1h)

                # ═══════════════════════════════════════════════════════════════
                # ANALYZE ALL OBs IN ZONE - Check which ones are near retest zone
                # ═══════════════════════════════════════════════════════════════
                obs_in_zone = []
                retested_count = 0
                best_ob = None
                best_distance = float('inf')

                for ob in bullish_obs_1h:
                    # Calculate distance from retest/entry to OB zone
                    ref_price = retest_low if retest_low is not None else entry_price
                    distance = abs(ref_price - ob['zone_high']) if ref_price else float('inf')

                    # Check if this OB is in the retest zone (within 5% of retest price)
                    zone_tolerance = ref_price * 0.05 if ref_price else 0
                    in_zone = ref_price is not None and ob['zone_high'] >= ref_price - zone_tolerance

                    # Check if retest touched this OB
                    # Use larger tolerance: max of 150% zone range OR 2% of price
                    zone_range = ob['zone_high'] - ob['zone_low']
                    ob_tolerance = max(zone_range * 1.5, ref_price * 0.02) if ref_price else zone_range * 1.5
                    retested = False
                    if retest_low is not None:
                        if retest_low <= ob['zone_high'] + ob_tolerance and retest_low >= ob['zone_low'] - ob_tolerance:
                            retested = True
                            retested_count += 1

                    if in_zone or retested:
                        obs_in_zone.append({
                            'datetime': ob.get('datetime'),
                            'zone_high': ob['zone_high'],
                            'zone_low': ob['zone_low'],
                            'strength': ob['strength'],
                            'retested': retested,
                            'distance': distance
                        })

                    # Track best (closest) OB
                    if distance < best_distance:
                        best_distance = distance
                        best_ob = ob

                # Store zone analysis
                result['fc_ob_1h_in_zone'] = len(obs_in_zone)
                result['fc_ob_1h_retested'] = retested_count
                result['fc_ob_1h_all_obs'] = obs_in_zone

                if best_ob:
                    result['fc_ob_1h_type'] = best_ob['type']
                    result['fc_ob_1h_zone_high'] = best_ob['zone_high']
                    result['fc_ob_1h_zone_low'] = best_ob['zone_low']
                    result['fc_ob_1h_strength'] = best_ob['strength']
                    result['fc_ob_1h_distance_pct'] = (best_distance / best_ob['zone_mid'] * 100) if best_ob['zone_mid'] > 0 else None
                    result['fc_ob_1h_datetime'] = best_ob.get('datetime')

                    # Mark as retest if ANY OB was retested
                    if retested_count > 0:
                        result['fc_ob_1h_retest'] = True

    # ═══════════════════════════════════════════════════════════════════════════════
    # 4H FOREIGN CANDLE ORDER BLOCK DETECTION
    # ═══════════════════════════════════════════════════════════════════════════════
    if df_4h is not None and len(df_4h) > 0:
        obs_4h = detect_foreign_candle_ob(
            df=df_4h,
            open_prices=df_4h['open'].values,
            high=df_4h['high'].values,
            low=df_4h['low'].values,
            close=df_4h['close'].values,
            min_before=1,  # Reduced from 2 to detect more OBs
            min_after=1,   # Reduced from 2 to detect more OBs
            lookback=lookback_4h
        )

        # Filter to BULLISH OBs only
        bullish_obs_4h = [ob for ob in obs_4h if ob['type'] == 'BULLISH']

        # ═══════════════════════════════════════════════════════════════
        # CRITICAL FILTER 1: Only OBs created BEFORE TL break are valid
        # OBs formed after TL break are NOT institutional footprints
        # ═══════════════════════════════════════════════════════════════
        if tl_break_datetime is not None:
            bullish_obs_4h = [ob for ob in bullish_obs_4h
                              if ob.get('datetime') is not None and ob['datetime'] < tl_break_datetime]

        # ═══════════════════════════════════════════════════════════════
        # CRITICAL FILTER 2: OB must be BELOW TL break price
        # For bullish retest, the OB zone must be below the breakout level
        # This ensures the OB is a demand zone that price pulls back TO
        # ═══════════════════════════════════════════════════════════════
        if tl_break_price is not None:
            bullish_obs_4h = [ob for ob in bullish_obs_4h
                              if ob['zone_high'] < tl_break_price * 1.03]  # 3% tolerance for 4H

        # IMPORTANT: For bullish retest, OB must be BELOW entry price (demand zone)
        # Price pulls back DOWN to retest the OB zone, then bounces up
        reference_price = retest_low if retest_low is not None else entry_price
        if reference_price is not None:
            bullish_obs_4h = [ob for ob in bullish_obs_4h if ob['zone_high'] <= reference_price * 1.03]  # 3% tolerance for 4H

        if bullish_obs_4h:
            result['fc_ob_4h_found'] = True
            result['fc_ob_4h_count'] = len(bullish_obs_4h)

            # ═══════════════════════════════════════════════════════════════
            # ANALYZE ALL OBs IN ZONE - Check which ones are near retest zone
            # ═══════════════════════════════════════════════════════════════
            obs_in_zone = []
            retested_count = 0
            best_ob = None
            best_distance = float('inf')

            for ob in bullish_obs_4h:
                # Calculate distance from retest/entry to OB zone
                ref_price = retest_low if retest_low is not None else entry_price
                distance = abs(ref_price - ob['zone_high']) if ref_price else float('inf')

                # Check if this OB is in the retest zone (within 7% of retest price for 4H)
                zone_tolerance = ref_price * 0.07 if ref_price else 0
                in_zone = ref_price is not None and ob['zone_high'] >= ref_price - zone_tolerance

                # Check if retest touched this OB
                # Use larger tolerance: max of 150% zone range OR 3% of price (4H is wider)
                zone_range = ob['zone_high'] - ob['zone_low']
                ob_tolerance = max(zone_range * 1.5, ref_price * 0.03) if ref_price else zone_range * 1.5
                retested = False
                if retest_low is not None:
                    if retest_low <= ob['zone_high'] + ob_tolerance and retest_low >= ob['zone_low'] - ob_tolerance:
                        retested = True
                        retested_count += 1

                if in_zone or retested:
                    obs_in_zone.append({
                        'datetime': ob.get('datetime'),
                        'zone_high': ob['zone_high'],
                        'zone_low': ob['zone_low'],
                        'strength': ob['strength'],
                        'retested': retested,
                        'distance': distance
                    })

                # Track best (closest) OB
                if distance < best_distance:
                    best_distance = distance
                    best_ob = ob

            # Store zone analysis
            result['fc_ob_4h_in_zone'] = len(obs_in_zone)
            result['fc_ob_4h_retested'] = retested_count
            result['fc_ob_4h_all_obs'] = obs_in_zone

            if best_ob:
                result['fc_ob_4h_type'] = best_ob['type']
                result['fc_ob_4h_zone_high'] = best_ob['zone_high']
                result['fc_ob_4h_zone_low'] = best_ob['zone_low']
                result['fc_ob_4h_strength'] = best_ob['strength']
                result['fc_ob_4h_distance_pct'] = (best_distance / best_ob['zone_mid'] * 100) if best_ob['zone_mid'] > 0 else None
                result['fc_ob_4h_datetime'] = best_ob.get('datetime')

                # Mark as retest if ANY OB was retested
                if retested_count > 0:
                    result['fc_ob_4h_retest'] = True

    # ═══════════════════════════════════════════════════════════════════════════════
    # SCORING AND LABEL
    # ═══════════════════════════════════════════════════════════════════════════════
    score = 0

    # 1H OB Scoring
    if result['fc_ob_1h_retest']:
        score += 40  # Major bonus for confirmed retest
        if result['fc_ob_1h_strength'] and result['fc_ob_1h_strength'] >= 5:
            score += 15  # Strong OB
        # Bonus for multiple OBs retested in 1H
        if result['fc_ob_1h_retested'] >= 2:
            score += 15  # Multiple OBs confluence
    elif result['fc_ob_1h_found']:
        if result['fc_ob_1h_distance_pct'] is not None and result['fc_ob_1h_distance_pct'] < 3:
            score += 20  # Close to OB
        else:
            score += 10  # OB exists but not retested

    # 4H OB Scoring
    if result['fc_ob_4h_retest']:
        score += 30  # 4H OB retest
        if result['fc_ob_4h_strength'] and result['fc_ob_4h_strength'] >= 4:
            score += 10
        # Bonus for multiple OBs retested in 4H
        if result['fc_ob_4h_retested'] >= 2:
            score += 10  # Multiple OBs confluence
    elif result['fc_ob_4h_found']:
        score += 10

    # Confluence bonus: OBs in same zone across timeframes
    if result['fc_ob_1h_retest'] and result['fc_ob_4h_retest']:
        score += 20  # Strong confluence

    result['fc_ob_score'] = min(100, score)

    # Determine label with retest count info
    total_in_zone = result['fc_ob_1h_in_zone'] + result['fc_ob_4h_in_zone']
    total_retested = result['fc_ob_1h_retested'] + result['fc_ob_4h_retested']

    if result['fc_ob_1h_retest'] and result['fc_ob_4h_retest']:
        result['fc_ob_label'] = f'STRONG ({total_retested}/{total_in_zone})'
        result['fc_ob_bonus'] = True
    elif result['fc_ob_1h_retest']:
        result['fc_ob_label'] = f'RETEST 1H ({result["fc_ob_1h_retested"]}/{result["fc_ob_1h_in_zone"]})'
        result['fc_ob_bonus'] = True
    elif result['fc_ob_4h_retest']:
        result['fc_ob_label'] = f'RETEST 4H ({result["fc_ob_4h_retested"]}/{result["fc_ob_4h_in_zone"]})'
        result['fc_ob_bonus'] = True
    elif result['fc_ob_1h_found'] or result['fc_ob_4h_found']:
        result['fc_ob_label'] = f'OB NEARBY ({total_in_zone})'
        result['fc_ob_bonus'] = False
    else:
        result['fc_ob_label'] = 'NO_OB'
        result['fc_ob_bonus'] = False

    return result


def detect_choch_bos(df, close, high, swing_highs, start_idx, max_bars=50):
    """
    Detect CHoCH/BOS (Change of Character / Break of Structure)

    Looks for swing highs that formed:
    1. In the 50 bars BEFORE the alert (original logic)
    2. OR between the alert and current check point (new logic)

    A CHoCH/BOS is confirmed when close > swing_high + 0.5% margin
    """
    breaks = []
    end_idx = min(start_idx + max_bars, len(close))

    for check_idx in range(start_idx, end_idx):
        # Find swing highs that are:
        # - Before current check point (sh['idx'] < check_idx)
        # - Within 50 bars before alert OR between alert and now
        relevant_shs = [sh for sh in swing_highs
                        if sh['idx'] < check_idx  # Must be before current candle
                        and sh['idx'] >= start_idx - 50]  # Within 50 bars before alert start

        if not relevant_shs:
            continue

        for sh in relevant_shs:
            # Check if this is a first-time break (close crosses above SH)
            if close[check_idx] > sh['price'] and (check_idx == 0 or close[check_idx-1] <= sh['price']):
                break_margin_pct = (close[check_idx] - sh['price']) / sh['price'] * 100
                if break_margin_pct >= 0.5:
                    # Check if this SH break was already recorded
                    if not any(b['sh_idx'] == sh['idx'] for b in breaks):
                        breaks.append({
                            'idx': check_idx,
                            'dt': df.iloc[check_idx]['datetime'],
                            'price': close[check_idx],
                            'sh_idx': sh['idx'],
                            'sh_price': sh['price'],
                            'break_pct': break_margin_pct
                        })
    return breaks


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def get_binance_klines(symbol, interval, start_date, end_date, warmup_bars=600):
    interval_hours = {"15m": 0.25, "30m": 0.5, "1h": 1, "4h": 4}
    hours = interval_hours.get(interval, 1)
    start_ts = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp() * 1000)
    end_ts = int((datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).timestamp() * 1000)
    warmup_ms = int(warmup_bars * hours * 60 * 60 * 1000)
    warmup_start = start_ts - warmup_ms
    all_data = []
    url = "https://api.binance.com/api/v3/klines"
    current_start = warmup_start
    while current_start < end_ts:
        params = {'symbol': symbol, 'interval': interval, 'startTime': current_start, 'endTime': end_ts, 'limit': 1000}
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            if not data or isinstance(data, dict):
                break
            all_data.extend(data)
            if len(data) < 1000:
                break
            current_start = data[-1][0] + 1
            time.sleep(0.05)
        except Exception as e:
            print(f"Error: {e}")
            break
    if not all_data:
        return pd.DataFrame()
    df = pd.DataFrame(all_data, columns=['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_volume', 'trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
    return df.reset_index(drop=True)


# ═══════════════════════════════════════════════════════════════════════════════
# MEGA BUY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

def detect_mega_buy_full(df, tf_name, config):
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_price = df['open'].values
    volume = df['volume'].values

    combo_window = config['COMBO_WINDOW']
    window_size = combo_window * 2

    rsi = calc_rsi(close, config['RSI_LENGTH'])
    plus_di, minus_di = calc_dmi(high, low, close, config['DMI_LENGTH'], config['DMI_ADX_SMOOTH'])
    ast_dir, _ = calc_supertrend(high, low, close, config['AST_FACTOR'], config['AST_PERIOD'])
    st_dir, _ = calc_supertrend(high, low, close, 3.0, 10)
    lazybar = calc_lazybar(high, low, close)
    stc = calc_adaptive_stochastic(close, config['STOCH_LENGTH'], config['STOCH_FAST'], config['STOCH_SLOW'])
    av_regime, vol_change, vol_move, vol_ratio = calc_atr_vol_regime(high, low, close, volume, config)
    pp_trend = calc_pp_supertrend(high, low, close)
    ec_rsi, ec_slow = calc_ec_rsi(close, config['EC_RSI_PERIOD'], config['EC_SLOW_MA_PERIOD'])
    swing_highs = calc_swing_highs(high, left=10, right=5)

    mega_buys = []
    last_mega_buy_idx = -999

    for i in range(50, len(df)):
        if i - last_mega_buy_idx <= window_size:
            continue

        candle_move = max(abs(close[i] - open_price[i]), high[i] - low[i]) / min(open_price[i], low[i]) * 100
        if candle_move > config['COMBO_MAX_MOVE']:
            continue

        rsi_found = False
        max_rsi_move = 0
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0 and not np.isnan(rsi[idx]) and not np.isnan(rsi[idx-1]):
                rsi_delta = rsi[idx] - rsi[idx-1]
                if rsi_delta >= config['RSI_MIN_MOVE_BUY']:
                    rsi_found = True
                    if rsi_delta > max_rsi_move:
                        max_rsi_move = rsi_delta

        dmi_found = False
        max_dmi_move = 0
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0:
                dmi_delta = plus_di[idx] - plus_di[idx-1]
                if dmi_delta > 0 and dmi_delta >= config['DMI_MIN_MOVE_PLUS']:
                    dmi_found = True
                    if dmi_delta > max_dmi_move:
                        max_dmi_move = dmi_delta

        ast_found = False
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0:
                if ast_dir[idx] == -1 and ast_dir[idx-1] != -1:
                    ast_found = True

        if not (rsi_found and dmi_found and ast_found):
            continue

        choch_found = False
        for sh in swing_highs:
            if sh['idx'] < i:
                for j in range(min(6, i - sh['idx'])):
                    check_idx = i - j
                    if check_idx > 0 and close[check_idx] > sh['price'] and close[check_idx-1] <= sh['price']:
                        choch_found = True
                        break

        green_zone = av_regime[i] != -1

        lazy_found = False
        lazy_value = lazybar[i] if not np.isnan(lazybar[i]) else 0
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0 and not np.isnan(lazybar[idx]):
                if abs(lazybar[idx]) >= 9.6:
                    lazy_found = True
                if not np.isnan(lazybar[idx-1]):
                    if abs(lazybar[idx] - lazybar[idx-1]) >= config['LB_SPIKE_THRESH']:
                        lazy_found = True

        vol_cond = vol_move[i] >= config['AV_MIN_MOVE'] and vol_change[i] > 0

        st_found = False
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0:
                if st_dir[idx] < 0 and st_dir[idx-1] > 0:
                    st_found = True

        pp_found = False
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0:
                if pp_trend[idx] == 1 and pp_trend[idx-1] == -1:
                    pp_found = True

        ec_found = False
        for j in range(window_size + 1):
            idx = i - j
            if idx > 0:
                if not np.isnan(ec_rsi[idx]) and not np.isnan(ec_rsi[idx-1]):
                    ec_delta = ec_rsi[idx] - ec_rsi[idx-1]
                    if ec_delta > 0 and abs(ec_delta) >= config['EC_MIN_MOVE_RSI']:
                        ec_found = True
                if not np.isnan(ec_slow[idx]) and not np.isnan(ec_slow[idx-1]):
                    ec_slow_delta = ec_slow[idx] - ec_slow[idx-1]
                    if ec_slow_delta > 0 and abs(ec_slow_delta) >= config['EC_MIN_MOVE_SLOW']:
                        ec_found = True

        score = sum([rsi_found, dmi_found, ast_found, choch_found, green_zone,
                     lazy_found, vol_cond, st_found, pp_found, ec_found])

        if score < 7:
            continue

        mega_buys.append({
            'idx': i,
            'datetime': df.iloc[i]['datetime'],
            'tf': tf_name,
            'open': open_price[i],
            'high': high[i],
            'low': low[i],
            'close': close[i],
            'volume': volume[i],
            'score': score,
            'rsi': rsi[i],
            'rsi_prev': rsi[i-1] if i > 0 else np.nan,
            'rsi_move': max_rsi_move,
            'di_plus': plus_di[i],
            'di_minus': minus_di[i],
            'dmi_move': max_dmi_move,
            'stc': stc[i],
            'lazybar': lazy_value,
            'vol_change': vol_change[i],
            'vol_ratio': vol_ratio[i],
            'ast_dir': 'BULLISH' if ast_dir[i] == -1 else 'BEARISH',
            'st_dir': 'BULLISH' if st_dir[i] == -1 else 'BEARISH',
            'pp_trend': 'BUY' if pp_trend[i] == 1 else 'SELL',
            'conditions': {
                'RSI_surge': rsi_found,
                'DI+_surge': dmi_found,
                'AST_flip': ast_found,
                'CHoCH': choch_found,
                'Green_Zone': green_zone,
                'LazyBar': lazy_found,
                'Volume': vol_cond,
                'ST_break': st_found,
                'PP_buy': pp_found,
                'Entry_Confirm': ec_found
            }
        })
        last_mega_buy_idx = i

    return mega_buys, stc, rsi, plus_di, minus_di


# ═══════════════════════════════════════════════════════════════════════════════
# V3 GOLDEN BOX RETEST STRATEGY
# Entry via limit order at Box High, wait for price to retest after breakout
# ═══════════════════════════════════════════════════════════════════════════════

def find_v3_golden_box_retest_entry(df_1h, signal_idx, box_high, box_low, config):
    """
    V3 Golden Box Retest Strategy: Find entry when price retests the Box High.

    Strategy Logic:
    1. Golden Box = Signal candle's High/Low (acts as support/resistance)
    2. Wait for price to break ABOVE Box High (breakout)
    3. Then wait for price to PULL BACK and retest Box High as support
    4. Entry: At Box High + margin% when price comes back to test it
    5. SL: Box Low - margin%

    This strategy gives better entry prices and tighter stop losses compared to V1/V2.

    Args:
        df_1h: 1H DataFrame
        signal_idx: Index of signal candle in df_1h
        box_high: Golden Box High (signal candle high)
        box_low: Golden Box Low (signal candle low)
        config: Configuration dict

    Returns:
        dict with entry details or None if no valid retest found
    """
    n = len(df_1h)
    if signal_idx >= n - 1:
        return None

    # V3 Parameters
    entry_margin_pct = config.get('V3_ENTRY_MARGIN_PCT', 0.2)
    sl_margin_pct = config.get('V3_SL_MARGIN_PCT', 1.0)
    timeout_hours = config.get('V3_TIMEOUT_HOURS', 48)
    min_retest_distance_pct = config.get('V3_MIN_RETEST_DISTANCE_PCT', 1.0)
    max_delay_hours = config.get('V3_MAX_ENTRY_DELAY_HOURS', 72)

    # Calculate entry and SL prices
    entry_price_target = box_high * (1 + entry_margin_pct / 100)  # Buy just above Box High
    sl_price = box_low * (1 - sl_margin_pct / 100)  # SL just below Box Low

    signal_dt = df_1h.iloc[signal_idx]['datetime']
    max_entry_dt = signal_dt + timedelta(hours=max_delay_hours)

    # Track price movement after signal
    breakout_confirmed = False
    breakout_idx = None
    breakout_high = box_high
    retest_entry = None

    close_arr = df_1h['close'].values
    high_arr = df_1h['high'].values
    low_arr = df_1h['low'].values

    for i in range(signal_idx + 1, n):
        current_dt = df_1h.iloc[i]['datetime']

        # Check timeout
        if current_dt > max_entry_dt:
            break

        current_close = close_arr[i]
        current_high = high_arr[i]
        current_low = low_arr[i]

        # Phase 1: Wait for breakout above Box High
        if not breakout_confirmed:
            if current_close > box_high:
                breakout_confirmed = True
                breakout_idx = i
                breakout_high = current_high
            continue

        # Track highest price after breakout
        if current_high > breakout_high:
            breakout_high = current_high

        # Phase 2: Wait for retest of Box High zone
        # Retest = price pulls back and touches/approaches Box High

        # Check if we've moved enough away from Box High first (min distance)
        distance_from_box = (breakout_high - box_high) / box_high * 100
        if distance_from_box < min_retest_distance_pct:
            continue

        # Check for retest: Low comes close to or touches Box High zone
        # Entry zone = Box High to Box High + entry_margin%
        entry_zone_top = entry_price_target
        entry_zone_bottom = box_high * 0.998  # Allow 0.2% below Box High for retest

        # Retest conditions:
        # 1. Low touches the entry zone (price came back to Box High)
        # 2. Close is above the entry zone (bounce confirmed)
        if current_low <= entry_zone_top and current_close >= box_high:
            # Valid retest! Entry at the higher of: entry_price_target or current candle close
            # In reality, limit order would fill at entry_price_target
            actual_entry_price = entry_price_target

            # Calculate metrics
            hours_to_entry = (current_dt - signal_dt).total_seconds() / 3600
            entry_diff_from_signal = (actual_entry_price - df_1h.iloc[signal_idx]['close']) / df_1h.iloc[signal_idx]['close'] * 100
            sl_distance_pct = (actual_entry_price - sl_price) / actual_entry_price * 100
            box_range_pct = (box_high - box_low) / box_low * 100

            retest_entry = {
                'dt': current_dt,
                'idx': i,
                'price': actual_entry_price,
                'sl_price': sl_price,
                'box_high': box_high,
                'box_low': box_low,
                'box_range_pct': box_range_pct,
                'breakout_idx': breakout_idx,
                'breakout_dt': df_1h.iloc[breakout_idx]['datetime'],
                'breakout_high': breakout_high,
                'retest_low': current_low,
                'hours_to_breakout': (df_1h.iloc[breakout_idx]['datetime'] - signal_dt).total_seconds() / 3600,
                'hours_to_entry': hours_to_entry,
                'entry_diff_from_signal_pct': entry_diff_from_signal,
                'sl_distance_pct': sl_distance_pct,
                'distance_before_retest_pct': distance_from_box,
            }
            break

    return retest_entry


def validate_v3_entry(retest_entry, alert_data, config):
    """
    V3 Validation: Check if retest entry meets quality criteria.

    Returns (is_valid, reason, quality_score)
    """
    if retest_entry is None:
        return False, "NO_RETEST_FOUND", 0

    # Quality scoring for V3 entries
    score = 0

    # 1. Hours to entry (faster = better, but not too fast)
    hours_to_entry = retest_entry.get('hours_to_entry', 999)
    if 4 <= hours_to_entry <= 24:
        score += 3  # Ideal timing
    elif 24 < hours_to_entry <= 48:
        score += 2  # Good timing
    elif hours_to_entry > 48:
        score += 1  # Acceptable

    # 2. SL distance (tighter = better R:R)
    sl_distance = retest_entry.get('sl_distance_pct', 999)
    if sl_distance <= 5:
        score += 3  # Excellent R:R potential
    elif sl_distance <= 8:
        score += 2  # Good R:R
    elif sl_distance <= 12:
        score += 1  # Acceptable

    # 3. Distance before retest (more = stronger breakout)
    distance_before_retest = retest_entry.get('distance_before_retest_pct', 0)
    if distance_before_retest >= 5:
        score += 2  # Strong breakout
    elif distance_before_retest >= 2:
        score += 1  # Moderate breakout

    # 4. Box range quality (smaller = tighter zone)
    box_range = retest_entry.get('box_range_pct', 999)
    if box_range <= 3:
        score += 2  # Tight box
    elif box_range <= 6:
        score += 1  # Acceptable box

    # Optional: Apply V2 filters as bonus/malus
    if alert_data:
        # RSI MTF aligned = bonus
        if alert_data.get('rsi_mtf_bonus'):
            score += 2
        # ADX Strong = bonus
        if alert_data.get('adx_strength_1h') == 'STRONG':
            score += 1
        # Volume spike 4H = bonus
        if alert_data.get('vol_spike_bonus_4h'):
            score += 1

    return True, "VALID_RETEST", score


# ═══════════════════════════════════════════════════════════════════════════════
# V4 OPTIMIZED STRATEGY VALIDATION
# Based on comprehensive backtest analysis - improves WR from 31.9% to 50.7%
# ═══════════════════════════════════════════════════════════════════════════════

def validate_v4_filters(alert_data: dict, symbol: str, config: dict) -> tuple:
    """
    V4 Validation: Apply all optimized filters based on backtest analysis.

    Returns (is_valid, rejection_reason, v4_score, rejection_details)

    MANDATORY FILTERS (reject trade if triggered):
    1. V3 Quality < 6 (0-5 = 11.1% WR, -131% P&L)
    2. TL Break > 24h (0% WR, -35% P&L)
    3. STC without 1H (30m alone = 0% WR, 15m alone = 20.8% WR)
    4. OB Score < 50 (1-49 = 0% WR, -26% P&L)
    5. Blacklisted pairs (consistently 0% WR)

    SCORING BONUSES:
    - Entry timing 24-48h: +15 points (65% WR sweet spot)
    - 1H timeframe: +10 points (39.1% WR vs 29% for others)
    - OB retested: +15 points (33.6% WR)
    - OB Both (1H+4H): +10 points (34.8% WR)
    """

    rejection_details = []
    v4_score = 50  # Base score

    # ═══════════════════════════════════════════════════════════════════════════
    # MANDATORY FILTER 1: Blacklist check
    # ═══════════════════════════════════════════════════════════════════════════
    if config.get('V4_BLACKLIST_ENABLED', True):
        blacklist = config.get('V4_BLACKLIST_PAIRS', [])
        if symbol.upper() in [p.upper() for p in blacklist]:
            return False, 'V4_BLACKLIST', 0, [f"Pair {symbol} in V4 blacklist (0% historical WR)"]

    # ═══════════════════════════════════════════════════════════════════════════
    # MANDATORY FILTER 2: V3 Quality Score >= 6
    # Analysis: V3 Quality 0-5 = 11.1% WR, V3 Quality 6+ = 37.5% WR
    # ═══════════════════════════════════════════════════════════════════════════
    v3_quality = alert_data.get('v3_quality_score') or 0
    min_v3_quality = config.get('V4_MIN_V3_QUALITY', 6)

    if v3_quality < min_v3_quality:
        rejection_details.append(f"V3 Quality {v3_quality} < {min_v3_quality}")
        return False, f'V4_V3_QUALITY_{v3_quality}', v3_quality * 10, rejection_details

    # Add quality score
    v4_score += (v3_quality - 5) * 5  # 6=+5, 7=+10, 8=+15, etc.

    # ═══════════════════════════════════════════════════════════════════════════
    # MANDATORY FILTER 3: TL Break Delay <= 24h
    # Analysis: TL Break >24h = 0% WR
    # ═══════════════════════════════════════════════════════════════════════════
    tl_break_delay = alert_data.get('tl_break_delay_hours') or 0
    max_tl_delay = config.get('V4_MAX_TL_BREAK_HOURS', 24)

    if tl_break_delay > max_tl_delay:
        rejection_details.append(f"TL Break delay {tl_break_delay:.1f}h > {max_tl_delay}h")
        return False, f'V4_TL_DELAY_{int(tl_break_delay)}H', v4_score, rejection_details

    # Bonus/Penalty based on TL break timing
    if 6 <= tl_break_delay <= 24:
        v4_score += 10  # Optimal timing
    elif tl_break_delay > 48:
        v4_score -= 10  # Slow TL break penalty
    elif tl_break_delay > 24:
        v4_score -= 5   # Moderate delay penalty

    # ═══════════════════════════════════════════════════════════════════════════
    # MANDATORY FILTER 4: STC must include 1H
    # Analysis: 30m alone = 0% WR, 15m alone = 20.8% WR
    # Best: 30m+1h = 71.4% WR, 15m+1h = 41.7% WR
    # ═══════════════════════════════════════════════════════════════════════════
    if config.get('V4_STC_REQUIRE_1H', True):
        stc_valid_tfs = alert_data.get('stc_valid_tfs') or ''
        reject_patterns = config.get('V4_STC_REJECT_PATTERNS', ['30m', '15m'])

        # Check if STC is only 30m or only 15m (without 1h)
        if stc_valid_tfs in reject_patterns:
            rejection_details.append(f"STC '{stc_valid_tfs}' without 1H (poor WR)")
            return False, f'V4_STC_NO_1H_{stc_valid_tfs.upper()}', v4_score, rejection_details

        # Bonus for best STC combos
        if stc_valid_tfs == '30m,1h':
            v4_score += 20  # 71.4% WR - best combo!
        elif stc_valid_tfs == '15m,1h':
            v4_score += 10  # 41.7% WR
        elif '1h' in stc_valid_tfs:
            v4_score += 5   # Has 1H

    # ═══════════════════════════════════════════════════════════════════════════
    # MANDATORY FILTER 5: OB Score >= 50
    # Analysis: OB Score 1-49 = 0% WR
    # ═══════════════════════════════════════════════════════════════════════════
    ob_score = alert_data.get('fc_ob_score') or 0
    min_ob_score = config.get('V4_MIN_OB_SCORE', 50)

    # Only reject if OB exists but is weak (0 means no OB found, which is allowed)
    if 0 < ob_score < min_ob_score:
        rejection_details.append(f"OB Score {ob_score} < {min_ob_score} (weak OB)")
        return False, f'V4_WEAK_OB_{ob_score}', v4_score, rejection_details

    # Bonus for strong OB
    if ob_score >= 80:
        v4_score += 15  # Strong OB
    elif ob_score >= 50:
        v4_score += 8   # Medium OB

    # ═══════════════════════════════════════════════════════════════════════════
    # OPTIONAL FILTER: Reject bad combo patterns
    # Analysis: 15m+30m+1h combo = 20% WR (poor)
    # ═══════════════════════════════════════════════════════════════════════════
    if config.get('V4_REJECT_BAD_COMBOS', True):
        combo_tfs = alert_data.get('combo_tfs') or ''
        bad_combos = config.get('V4_BAD_COMBOS', ['15m,30m,1h'])

        if combo_tfs in bad_combos:
            rejection_details.append(f"Combo '{combo_tfs}' in poor performers")
            return False, f'V4_BAD_COMBO_{combo_tfs.replace(",", "_").upper()}', v4_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # SCORING BONUSES
    # ═══════════════════════════════════════════════════════════════════════════

    # Entry timing bonus (24-48h = 65% WR sweet spot)
    hours_to_entry = alert_data.get('v3_hours_to_entry') or 0
    if config.get('V4_ENTRY_TIMING_BONUS', True):
        opt_min = config.get('V4_OPTIMAL_ENTRY_MIN_HOURS', 24)
        opt_max = config.get('V4_OPTIMAL_ENTRY_MAX_HOURS', 48)
        if opt_min <= hours_to_entry <= opt_max:
            v4_score += 15  # Optimal entry timing
        elif 12 <= hours_to_entry < 24:
            v4_score += 5   # Good timing

    # 1H timeframe bonus
    if config.get('V4_PREFER_1H_TF', True):
        timeframe = alert_data.get('timeframe') or ''
        if timeframe == '1h':
            v4_score += config.get('V4_1H_SCORE_BONUS', 10)

    # OB retested bonus
    ob_1h_retested = alert_data.get('fc_ob_1h_retested') or False
    ob_4h_retested = alert_data.get('fc_ob_4h_retested') or False
    if ob_1h_retested or ob_4h_retested:
        v4_score += config.get('V4_OB_RETEST_BONUS', 15)

    # OB Both (1H + 4H) bonus
    ob_1h_found = alert_data.get('fc_ob_1h_found') or False
    ob_4h_found = alert_data.get('fc_ob_4h_found') or False
    if ob_1h_found and ob_4h_found:
        v4_score += 10  # Strong institutional footprint

    # Cap score at 100
    v4_score = min(100, v4_score)

    return True, 'V4_VALID', v4_score, []


def get_v4_grade(score: int) -> str:
    """Convert V4 score to grade"""
    if score >= 85:
        return 'A+'
    elif score >= 75:
        return 'A'
    elif score >= 65:
        return 'B+'
    elif score >= 55:
        return 'B'
    elif score >= 45:
        return 'C'
    else:
        return 'D'


def count_candles_below_val(df_1h, alert_dt, entry_dt, val_price: float, lookback_hours: int = 48) -> dict:
    """
    Count how many 1H candles closed below VAL in the structure period.

    IMPORTANT: This checks candles from (alert_dt - lookback_hours) to entry_dt
    to catch price movements below VAL that happened BEFORE the alert.

    This is crucial for V5 filter: if price made movements below VAL
    at ANY point in the structure, the setup is weak and should be rejected.

    Args:
        df_1h: 1H OHLC DataFrame with 'datetime' and 'close' columns
        alert_dt: Alert datetime
        entry_dt: Entry datetime
        val_price: Value Area Low price
        lookback_hours: Hours to look back BEFORE alert_dt (default 48h)

    Returns:
        dict with:
        - candles_below_val: number of candles that closed below VAL
        - total_candles: total candles in the range
        - pct_below_val: percentage of candles below VAL
        - lowest_close: lowest close price in the range
        - lowest_vs_val_pct: how far below VAL the lowest close was (%)
    """
    from datetime import timedelta

    if df_1h is None or val_price is None or val_price <= 0:
        return {
            'candles_below_val': 0,
            'total_candles': 0,
            'pct_below_val': 0,
            'lowest_close': None,
            'lowest_vs_val_pct': 0,
            'has_candles_below': False
        }

    # EXTENDED LOOKBACK: Check from (alert_dt - lookback_hours) to entry_dt
    # This catches price movements below VAL that happened BEFORE the alert
    lookback_start = alert_dt - timedelta(hours=lookback_hours)
    mask = (df_1h['datetime'] >= lookback_start) & (df_1h['datetime'] <= entry_dt)
    df_range = df_1h[mask].copy()

    if len(df_range) == 0:
        return {
            'candles_below_val': 0,
            'total_candles': 0,
            'pct_below_val': 0,
            'lowest_close': None,
            'lowest_vs_val_pct': 0,
            'has_candles_below': False
        }

    # Count candles that closed below VAL
    candles_below = df_range[df_range['close'] < val_price]
    candles_below_count = len(candles_below)
    total_candles = len(df_range)

    # Calculate percentage
    pct_below = (candles_below_count / total_candles * 100) if total_candles > 0 else 0

    # Find lowest close
    lowest_close = df_range['close'].min()
    lowest_vs_val_pct = ((lowest_close - val_price) / val_price * 100) if val_price > 0 else 0

    return {
        'candles_below_val': candles_below_count,
        'total_candles': total_candles,
        'pct_below_val': pct_below,
        'lowest_close': lowest_close,
        'lowest_vs_val_pct': lowest_vs_val_pct,
        'has_candles_below': candles_below_count > 0
    }


def check_vp_retest_exception(alert_data: dict, config: dict) -> tuple:
    """
    VP Retest Exception: Allow entry below VAL if specific conditions are met.

    Based on INITUSDT analysis (+176% move captured by V4, missed by V5):
    - Price came from ABOVE VAH (resistance)
    - Price found support at POC or VAL
    - Rejection candle detected (long lower wick, bullish)

    Returns (is_exception, exception_details)
    """
    if not config.get('V5_VP_RETEST_EXCEPTION_ENABLED', True):
        return False, []

    exception_details = []

    # Get VP levels
    vp_val = alert_data.get('vp_val_1h') or alert_data.get('vp_val_4h')
    vp_poc = alert_data.get('vp_poc_1h') or alert_data.get('vp_poc_4h')
    vp_vah = alert_data.get('vp_vah_1h') or alert_data.get('vp_vah_4h')

    if not vp_val or not vp_poc or not vp_vah:
        return False, ["No VP data for retest exception check"]

    # Get price data for analysis
    entry_price = alert_data.get('entry_price') or alert_data.get('alert_price') or alert_data.get('price_close')
    recent_high = alert_data.get('recent_high_4h')  # Highest high in lookback period
    rejection_candle = alert_data.get('rejection_candle_detected', False)
    rejection_wick_ratio = alert_data.get('rejection_wick_ratio', 0)

    if not entry_price:
        return False, ["No entry price for retest exception check"]

    # ═══════════════════════════════════════════════════════════════════════════
    # CONDITION 1: Price was above VAH recently (came from resistance)
    # ═══════════════════════════════════════════════════════════════════════════
    was_above_vah = False
    if recent_high and recent_high > vp_vah:
        was_above_vah = True
        exception_details.append(f"Price was above VAH (high={recent_high:.5f} > VAH={vp_vah:.5f})")

    # Alternative: Check if high_4h from alert data indicates price was above VAH
    high_4h = alert_data.get('high_4h') or alert_data.get('bar_4h_high')
    if not was_above_vah and high_4h and high_4h > vp_vah:
        was_above_vah = True
        exception_details.append(f"4H High above VAH (high={high_4h:.5f} > VAH={vp_vah:.5f})")

    if not was_above_vah:
        return False, ["Price was not above VAH - no descending pattern"]

    # ═══════════════════════════════════════════════════════════════════════════
    # CONDITION 2: Entry price is near POC or VAL (at support)
    # ═══════════════════════════════════════════════════════════════════════════
    tolerance_pct = config.get('V5_VP_RETEST_SUPPORT_TOLERANCE_PCT', 5.0)

    dist_to_poc = abs(entry_price - vp_poc) / vp_poc * 100 if vp_poc > 0 else 999
    dist_to_val = abs(entry_price - vp_val) / vp_val * 100 if vp_val > 0 else 999

    near_poc = dist_to_poc <= tolerance_pct
    near_val = dist_to_val <= tolerance_pct
    at_support = near_poc or near_val

    if not at_support:
        return False, [f"Entry not at support (dist_to_POC={dist_to_poc:.1f}%, dist_to_VAL={dist_to_val:.1f}%, tolerance={tolerance_pct}%)"]

    support_zone = "POC" if near_poc else "VAL"
    support_dist = dist_to_poc if near_poc else dist_to_val
    exception_details.append(f"Entry at {support_zone} support (dist={support_dist:.1f}%)")

    # ═══════════════════════════════════════════════════════════════════════════
    # CONDITION 3: Rejection candle detected (optional but preferred)
    # ═══════════════════════════════════════════════════════════════════════════
    min_wick_ratio = config.get('V5_VP_RETEST_REJECTION_WICK_RATIO', 1.5)

    if rejection_candle or rejection_wick_ratio >= min_wick_ratio:
        exception_details.append(f"Rejection candle detected (wick_ratio={rejection_wick_ratio:.1f})")
    else:
        # Rejection candle not mandatory, but check if we have candle data
        candle_body = alert_data.get('candle_body_4h', 0)
        candle_lower_wick = alert_data.get('candle_lower_wick_4h', 0)
        candle_is_bullish = alert_data.get('candle_is_bullish_4h', False)

        if candle_body > 0 and candle_lower_wick > 0:
            calc_wick_ratio = candle_lower_wick / candle_body
            if calc_wick_ratio >= min_wick_ratio and candle_is_bullish:
                exception_details.append(f"Calculated rejection (wick_ratio={calc_wick_ratio:.1f})")
            else:
                exception_details.append("No rejection candle, but conditions 1&2 met")

    # ═══════════════════════════════════════════════════════════════════════════
    # ALL CONDITIONS MET: VP RETEST EXCEPTION GRANTED
    # ═══════════════════════════════════════════════════════════════════════════
    exception_details.append("VP_RETEST_EXCEPTION: Entry below VAL allowed due to descent from VAH + support")

    return True, exception_details


def validate_v5_filters(alert_data: dict, symbol: str, config: dict) -> tuple:
    """
    V5 Validation: V4 filters + VP Trajectory Filter

    The key insight from deep analysis:
    - Price movements BELOW VAL = WEAK setup = higher LOSS probability
    - Even if there was a bounce, candles closing below VAL indicate weakness

    MANDATORY FILTER (v5.1 - stricter):
    1. If ANY candle closed below VAL between alert and entry → REJECT
       (bounce does NOT override this - the weakness is already shown)
    2. If no VP data available → Pass to V4

    EXCEPTION (v5.2 - VP Retest):
    If price came from above VAH and found support at POC/VAL → Allow entry

    Returns (is_valid, rejection_reason, v5_score, rejection_details)
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 1: Run V4 validation first
    # V5 = V4 + VP Filter, so V4 must pass
    # ═══════════════════════════════════════════════════════════════════════════
    v4_valid, v4_rejection_reason, v4_score, v4_details = validate_v4_filters(
        alert_data, symbol, config
    )

    if not v4_valid:
        # V4 failed, propagate rejection with V5 prefix
        return False, f'V5_{v4_rejection_reason}', v4_score, v4_details

    # Start with V4 score
    v5_score = v4_score
    rejection_details = []

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2: V5 CVD (Cumulative Volume Delta) FILTER
    # Reject trades when CVD shows weakness in both timeframes
    # CVD falling while price rising = bearish divergence = AVOID
    # ═══════════════════════════════════════════════════════════════════════════

    if config.get('V5_CVD_FILTER_ENABLED', True):
        # CVD 1H uses 'cvd_score', CVD 4H uses 'cvd_4h_score'
        cvd_1h_score = alert_data.get('cvd_score', 0) or alert_data.get('cvd_1h_score', 0) or 0
        cvd_4h_score = alert_data.get('cvd_4h_score', 0) or 0
        cvd_1h_divergence = alert_data.get('cvd_divergence', False) or alert_data.get('cvd_1h_divergence', False)
        cvd_4h_divergence = alert_data.get('cvd_4h_divergence', False)
        cvd_1h_div_type = alert_data.get('cvd_divergence_type', 'NONE') or alert_data.get('cvd_1h_divergence_type', 'NONE')
        cvd_4h_div_type = alert_data.get('cvd_4h_divergence_type', 'NONE')

        min_cvd_1h = config.get('V5_CVD_MIN_SCORE_1H', 30)
        min_cvd_4h = config.get('V5_CVD_MIN_SCORE_4H', 30)

        # Check for bearish divergence (price up, CVD down)
        if config.get('V5_CVD_REJECT_BEARISH_DIV', True):
            if cvd_4h_divergence and cvd_4h_div_type == 'BEARISH':
                rejection_details.append(
                    f"CVD 4H BEARISH DIVERGENCE: Price rising but CVD falling (Score: {cvd_4h_score}/100)"
                )
                return False, 'V5_CVD_BEARISH_DIV_4H', v5_score, rejection_details

            if cvd_1h_divergence and cvd_1h_div_type == 'BEARISH':
                rejection_details.append(
                    f"CVD 1H BEARISH DIVERGENCE: Price rising but CVD falling (Score: {cvd_1h_score}/100)"
                )
                return False, 'V5_CVD_BEARISH_DIV_1H', v5_score, rejection_details

        # Check if BOTH timeframes are weak
        if config.get('V5_CVD_REJECT_BOTH_WEAK', True):
            cvd_1h_weak = cvd_1h_score < min_cvd_1h
            cvd_4h_weak = cvd_4h_score < min_cvd_4h

            if cvd_1h_weak and cvd_4h_weak:
                rejection_details.append(
                    f"CVD WEAK on BOTH TFs: 1H={cvd_1h_score}/100 (min:{min_cvd_1h}), "
                    f"4H={cvd_4h_score}/100 (min:{min_cvd_4h})"
                )
                return False, 'V5_CVD_BOTH_WEAK', v5_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2b: V5 DMI SPREAD FILTER
    # Reject if DMI- > DMI+ at entry (bears in control)
    # ═══════════════════════════════════════════════════════════════════════════

    if config.get('V5_DMI_SPREAD_FILTER_ENABLED', True):
        # Get DMI spread at entry (DI+ - DI-)
        dmi_spread = alert_data.get('dmi_spread_at_entry', 0) or 0
        adx_di_plus = alert_data.get('adx_di_plus_at_entry', 0) or 0
        adx_di_minus = alert_data.get('adx_di_minus_at_entry', 0) or 0

        # Calculate spread if not provided
        if dmi_spread == 0 and (adx_di_plus > 0 or adx_di_minus > 0):
            dmi_spread = adx_di_plus - adx_di_minus

        min_dmi_spread = config.get('V5_DMI_MIN_SPREAD', 5.0)

        if dmi_spread < min_dmi_spread:
            rejection_details.append(
                f"DMI SPREAD WEAK: DI+ - DI- = {dmi_spread:.1f} (min: {min_dmi_spread}). "
                f"Bears in control at entry."
            )
            return False, 'V5_DMI_SPREAD_WEAK', v5_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2c: V5 WEAK BREAKOUT FILTER
    # Reject if breakout distance is too small (price didn't confirm breakout)
    # ═══════════════════════════════════════════════════════════════════════════

    if config.get('V5_WEAK_BREAKOUT_FILTER_ENABLED', True):
        distance_before_retest = alert_data.get('distance_before_retest_pct', 0) or 0
        min_breakout_distance = config.get('V5_MIN_BREAKOUT_DISTANCE_PCT', 2.0)

        if distance_before_retest < min_breakout_distance:
            rejection_details.append(
                f"WEAK BREAKOUT: Distance before retest = {distance_before_retest:.2f}% "
                f"(min: {min_breakout_distance}%). Breakout not confirmed."
            )
            return False, 'V5_WEAK_BREAKOUT', v5_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 2d: V5 POWER SCORE FILTER
    # Reject if Golden Box Power Score is too low
    # ═══════════════════════════════════════════════════════════════════════════

    if config.get('V5_POWER_SCORE_FILTER_ENABLED', True):
        power_score = alert_data.get('gb_power_score', 0) or 0
        min_power_score = config.get('V5_MIN_POWER_SCORE', 50)

        if power_score < min_power_score:
            power_grade = alert_data.get('gb_power_grade', 'F')
            rejection_details.append(
                f"POWER SCORE LOW: {power_score}/100 (Grade {power_grade}), "
                f"min required: {min_power_score} (Grade C)"
            )
            return False, 'V5_POWER_SCORE_LOW', v5_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # STEP 3: V5 VP TRAJECTORY FILTER (STRICT VERSION)
    # KEY: Any candle closing below VAL = REJECT
    # ═══════════════════════════════════════════════════════════════════════════

    if not config.get('V5_VP_FILTER_ENABLED', True):
        # V5 VP filter disabled, just return V4 result with V5 label
        return True, 'V5_VALID', v5_score, []

    # Get VP data from alert
    vp_val_1h = alert_data.get('vp_val_1h')
    vp_poc_1h = alert_data.get('vp_poc_1h')
    vp_vah_1h = alert_data.get('vp_vah_1h')
    alert_price = alert_data.get('alert_price') or alert_data.get('price_close')

    # Skip VP filter if no VP data
    if not vp_val_1h or not vp_poc_1h or not vp_vah_1h or not alert_price:
        # No VP data available, pass V5 filter (rely on V4)
        return True, 'V5_VALID_NO_VP', v5_score, []

    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL V5 FILTER: Check for significant price movements below VAL
    # Only reject if price went MORE THAN 5% below VAL (configurable)
    # Small dips below VAL are acceptable, deep dives are not
    # ═══════════════════════════════════════════════════════════════════════════

    candles_below_val = alert_data.get('candles_below_val', 0)
    total_candles = alert_data.get('total_candles_checked', 0)
    pct_below_val = alert_data.get('pct_candles_below_val', 0)
    lowest_vs_val_pct = alert_data.get('lowest_vs_val_pct', 0)

    # V5 THRESHOLD FILTER: Reject only if price went > X% below VAL
    # lowest_vs_val_pct is negative when below VAL (e.g., -5.0 means 5% below)
    max_below_val_pct = config.get('V5_MAX_BELOW_VAL_PCT', -5.0)  # Default: -5% (5% below VAL)

    if lowest_vs_val_pct < max_below_val_pct:
        # ═══════════════════════════════════════════════════════════════════════════
        # BEFORE REJECTING: Check for VP Retest Exception
        # If price came from VAH and found support at POC/VAL → Allow entry
        # (Based on INITUSDT analysis: +176% move, V4 captured +78%, V5 rejected)
        # ═══════════════════════════════════════════════════════════════════════════
        is_exception, exception_details = check_vp_retest_exception(alert_data, config)

        if is_exception:
            # VP Retest Exception granted - allow entry despite being below VAL
            v5_score += 10  # Bonus for valid VP retest pattern
            rejection_details.extend(exception_details)
            rejection_details.append(
                f"VP_RETEST_EXCEPTION: Price was {abs(lowest_vs_val_pct):.2f}% below VAL but exception granted"
            )
            # Don't reject, continue to scoring section
        else:
            # No exception, reject as normal
            rejection_details.append(
                f"Price went {abs(lowest_vs_val_pct):.2f}% below VAL (max allowed: {abs(max_below_val_pct):.1f}%), "
                f"{candles_below_val} candles below VAL"
            )
            if exception_details:
                rejection_details.extend(exception_details)
            return False, 'V5_DEEP_BELOW_VAL', v5_score, rejection_details

    # ═══════════════════════════════════════════════════════════════════════════
    # PASSED: No candles closed below VAL - valid setup
    # ═══════════════════════════════════════════════════════════════════════════

    # VAL/POC retest status (bonus points, not rejection criteria)
    val_retest_rejected = alert_data.get('vp_val_retest_rejected', False)
    poc_retest_rejected = alert_data.get('vp_poc_retest_rejected', False)

    # BONUS: VAL retest with bounce (price touched VAL but stayed above it)
    if val_retest_rejected:
        v5_score += config.get('V5_VAL_BOUNCE_BONUS', 15)
        rejection_details.append(f"VAL retest REJECTED (bounce) +{config.get('V5_VAL_BOUNCE_BONUS', 15)}pts")

    # BONUS: POC retest with bounce
    if poc_retest_rejected:
        v5_score += config.get('V5_POC_BOUNCE_BONUS', 10)
        rejection_details.append(f"POC retest REJECTED (bounce) +{config.get('V5_POC_BOUNCE_BONUS', 10)}pts")

    # BONUS: Strong trajectory (no candles near VAL)
    pct_time_below_va = alert_data.get('vp_pct_time_below_va', 0)
    if pct_time_below_va < 20:
        v5_score += config.get('V5_STRONG_TRAJECTORY_BONUS', 10)
        rejection_details.append(f"Strong trajectory +{config.get('V5_STRONG_TRAJECTORY_BONUS', 10)}pts")

    # Cap score at 100
    v5_score = min(100, v5_score)

    return True, 'V5_VALID', v5_score, rejection_details


def get_v5_grade(score: int) -> str:
    """Convert V5 score to grade (same as V4)"""
    return get_v4_grade(score)


# ═══════════════════════════════════════════════════════════════════════════════
# V2 OPTIMIZATION FILTERS
# Based on analysis of 249 trades - see IMPLEMENTATION_GUIDE.md
# ═══════════════════════════════════════════════════════════════════════════════

def count_fib_levels_broken(fib_levels: dict) -> int:
    """Count how many Fibonacci levels are broken"""
    if not fib_levels:
        return 0
    return sum(1 for lvl in fib_levels.values() if isinstance(lvl, dict) and lvl.get('break', False))


def validate_v2_filters(alert_data: dict) -> tuple:
    """
    V2 Validation: Apply optimized filters based on backtest analysis.
    Returns (is_valid, rejection_reason, trade_score)

    CRITICAL FILTERS (reject trade if triggered):
    1. Fib 4H > Fib 1H (5.9% WR)
    2. Combo Mortel: Fib 4H > 1H + ETH BOTH TRUE (0% WR)
    3. ADX WEAK (32.6% WR)
    4. StochRSI 1H TRUE (34.4% WR)
    5. Timeframe 1H seul (38.9% WR)
    6. Bonus Count < 8 (25-28% WR)
    7. Fib 4H saturated (5 levels = 10% WR)
    8. Fib 1H empty (0 levels = 0% WR)
    """

    # Extract Fibonacci data
    fib_levels_4h = alert_data.get('fib_levels', {}) or {}
    fib_levels_1h = alert_data.get('fib_levels_1h', {}) or {}

    # Parse if string (from JSON)
    import json
    if isinstance(fib_levels_4h, str):
        try:
            fib_levels_4h = json.loads(fib_levels_4h)
        except:
            fib_levels_4h = {}
    if isinstance(fib_levels_1h, str):
        try:
            fib_levels_1h = json.loads(fib_levels_1h)
        except:
            fib_levels_1h = {}

    count_4h = count_fib_levels_broken(fib_levels_4h)
    count_1h = count_fib_levels_broken(fib_levels_1h)

    # ETH Correlation
    eth_1h = alert_data.get('eth_corr_bonus_1h', False)
    eth_4h = alert_data.get('eth_corr_bonus_4h', False)
    eth_trend_1h = alert_data.get('eth_trend_1h', '')

    # BTC Trend - DISABLED (removed from analysis)

    # Other indicators
    adx_strength_1h = alert_data.get('adx_strength_1h', '')
    stoch_rsi_bonus_1h = alert_data.get('stoch_rsi_bonus_1h', False)
    combo_tfs = alert_data.get('combo_tfs', '')
    rsi_mtf_bonus = alert_data.get('rsi_mtf_bonus', False)
    ema_stack_bonus_4h = alert_data.get('ema_stack_bonus_4h', False)
    vol_spike_bonus_4h = alert_data.get('vol_spike_bonus_4h', False)
    mega_buy_score = alert_data.get('score', 0)

    # Count bonus filters
    bonus_count = sum([
        bool(alert_data.get('fib_bonus')),
        bool(alert_data.get('ob_bonus')),
        bool(alert_data.get('ob_bonus_4h')),
        bool(alert_data.get('btc_corr_bonus_1h')),
        bool(alert_data.get('btc_corr_bonus_4h')),
        bool(eth_1h),
        bool(eth_4h),
        bool(alert_data.get('fvg_bonus_1h')),
        bool(alert_data.get('fvg_bonus_4h')),
        bool(alert_data.get('vol_spike_bonus_1h')),
        bool(vol_spike_bonus_4h),
        bool(rsi_mtf_bonus),
        bool(alert_data.get('adx_bonus_1h')),
        bool(alert_data.get('adx_bonus_4h')),
        bool(alert_data.get('macd_bonus_1h')),
        bool(alert_data.get('macd_bonus_4h')),
        bool(alert_data.get('bb_squeeze_bonus_1h')),
        bool(alert_data.get('bb_squeeze_bonus_4h')),
        bool(stoch_rsi_bonus_1h),
        bool(alert_data.get('stoch_rsi_bonus_4h')),
        bool(alert_data.get('ema_stack_bonus_1h')),
        bool(ema_stack_bonus_4h),
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # CRITICAL REJECTION FILTERS
    # ═══════════════════════════════════════════════════════════════════════════

    # 1. COMBO MORTEL: Fib 4H > 1H + ETH BOTH TRUE (0% WR)
    if count_4h > count_1h and eth_1h and eth_4h:
        return False, "REJECTED_COMBO_MORTEL", -999

    # 2. Fib 4H > Fib 1H (5.9% WR)
    if count_4h > count_1h:
        return False, "REJECTED_FIB_4H_HIGHER", -100

    # 3. ADX WEAK (32.6% WR)
    if adx_strength_1h == "WEAK":
        return False, "REJECTED_ADX_WEAK", -50

    # 4. StochRSI 1H TRUE (34.4% WR) - counterintuitive but confirmed
    if stoch_rsi_bonus_1h:
        return False, "REJECTED_STOCHRSI_1H", -50

    # 5. Timeframe 1H seul (38.9% WR)
    if combo_tfs and combo_tfs.strip() == "1h":
        return False, "REJECTED_1H_ALONE", -80

    # 6. Bonus Count < 8 (25-28% WR)
    if bonus_count < 8:
        return False, "REJECTED_LOW_BONUS", -50

    # 7. Fib 4H saturated (5 levels = 10% WR)
    if count_4h >= 5:
        return False, "REJECTED_FIB_4H_SATURATED", -100

    # 8. Fib 1H empty (0 levels = 0% WR)
    if count_1h == 0:
        return False, "REJECTED_FIB_1H_EMPTY", -100

    # ═══════════════════════════════════════════════════════════════════════════
    # CALCULATE TRADE SCORE
    # ═══════════════════════════════════════════════════════════════════════════
    score = 0

    # BONUS POSITIFS
    if count_1h > count_4h:
        score += 5  # 93.3% WR
    if rsi_mtf_bonus:
        score += 5  # 83.3% WR
    if ema_stack_bonus_4h:
        score += 4  # 81.2% WR
    if eth_4h and not eth_1h:
        score += 3  # 66.7% WR (ETH 4H ONLY)
    if eth_trend_1h == "NEUTRAL":
        score += 3  # 58.3% WR
    # BTC trend check removed from analysis
    if adx_strength_1h == "STRONG":
        score += 2  # 57% WR
    if vol_spike_bonus_4h:
        score += 2  # 53.8% WR
    if count_1h == count_4h == 2:
        score += 2  # 59.6% WR (sweet spot)
    if mega_buy_score == 10:
        score += 2  # 56.9% WR

    # MALUS
    if eth_1h and eth_4h:
        score -= 3  # 41.2% WR
    if eth_trend_1h == "BULLISH":
        score -= 2  # 42.4% WR
    if mega_buy_score == 9:
        score -= 2  # 39.3% WR

    # Score minimum check
    if score < -5:
        return False, "REJECTED_LOW_SCORE", score

    return True, "VALIDATED", score


# ═══════════════════════════════════════════════════════════════════════════════
# V6 FILTER FUNCTIONS
# Timing + Momentum + Entry Limiter + Combined Scoring
# ═══════════════════════════════════════════════════════════════════════════════

def check_v6_timing_filter(timeframe: str, retest_hours: float, entry_hours: float,
                           distance_pct: float, config: Dict) -> tuple:
    """
    V6 Timing Filter - Rejects trades with inappropriate timing

    Returns: (passed: bool, rejection_reason: str or None, score_adjustment: int)
    """
    if not config.get('V6_TIMING_FILTER_ENABLED', True):
        return True, None, 0

    score_adj = 0

    # Distance filter (all TFs) - HARD REJECT
    if distance_pct > config.get('V6_MAX_DISTANCE_PCT', 20.0):
        return False, "V6_DISTANCE_TOO_HIGH", -20

    # Distance scoring
    dist_min = config.get('V6_OPTIMAL_DISTANCE_MIN', 5.0)
    dist_max = config.get('V6_OPTIMAL_DISTANCE_MAX', 10.0)
    if dist_min <= distance_pct <= dist_max:
        score_adj += config.get('V6_SCORE_DISTANCE_OPTIMAL', 15)
    elif distance_pct < dist_min:
        score_adj += config.get('V6_SCORE_DISTANCE_SHORT', 5)
    elif distance_pct > dist_max:
        score_adj += config.get('V6_SCORE_DISTANCE_LONG', -5)

    # 15m STRICT timing rules
    if timeframe == '15m':
        max_retest = config.get('V6_15M_MAX_RETEST_HOURS', 24)
        max_entry = config.get('V6_15M_MAX_ENTRY_HOURS', 48)
        optimal_retest = config.get('V6_15M_OPTIMAL_RETEST_HOURS', 6)

        if retest_hours > max_retest:
            return False, "V6_15M_SLOW_RETEST", config.get('V6_SCORE_RETEST_SLOW', -10)
        if entry_hours > max_entry:
            return False, "V6_15M_SLOW_ENTRY", config.get('V6_SCORE_ENTRY_SLOW', -10)

        # Scoring
        if retest_hours <= optimal_retest:
            score_adj += config.get('V6_SCORE_RETEST_FAST', 15)
        elif retest_hours <= 24:
            score_adj += config.get('V6_SCORE_RETEST_MEDIUM', 5)

        if entry_hours <= 24:
            score_adj += config.get('V6_SCORE_ENTRY_FAST', 10)
        elif entry_hours <= 48:
            score_adj += config.get('V6_SCORE_ENTRY_MEDIUM', 0)

    # 30m FLEXIBLE timing rules (no hard rejections)
    elif timeframe == '30m':
        optimal_retest = config.get('V6_30M_OPTIMAL_RETEST_HOURS', 6)

        if retest_hours <= optimal_retest:
            score_adj += config.get('V6_SCORE_RETEST_FAST', 15)
        elif retest_hours <= 24:
            score_adj += config.get('V6_SCORE_RETEST_MEDIUM', 5)
        else:
            score_adj += config.get('V6_SCORE_RETEST_SLOW', -10)

        if entry_hours <= 24:
            score_adj += config.get('V6_SCORE_ENTRY_FAST', 10)
        elif entry_hours <= 48:
            score_adj += config.get('V6_SCORE_ENTRY_MEDIUM', 0)
        else:
            score_adj += config.get('V6_SCORE_ENTRY_SLOW', -10)

    # 1h MEDIUM timing rules (warning zone)
    elif timeframe == '1h':
        optimal_retest = config.get('V6_1H_OPTIMAL_RETEST_HOURS', 6)
        warn_min = config.get('V6_1H_WARN_RETEST_MIN', 6)
        warn_max = config.get('V6_1H_WARN_RETEST_MAX', 24)

        if retest_hours <= optimal_retest:
            score_adj += config.get('V6_SCORE_RETEST_FAST', 15)
        elif warn_min < retest_hours <= warn_max:
            # Warning zone - 47.4% WR
            score_adj += config.get('V6_SCORE_RETEST_MEDIUM', 5)
            score_adj -= 5  # Extra penalty for warning zone
        else:
            score_adj += config.get('V6_SCORE_RETEST_SLOW', -10)

        if entry_hours <= 24:
            score_adj += config.get('V6_SCORE_ENTRY_FAST', 10)
        elif entry_hours <= 48:
            score_adj += config.get('V6_SCORE_ENTRY_MEDIUM', 0)
        else:
            score_adj += config.get('V6_SCORE_ENTRY_SLOW', -10)

    return True, None, score_adj


def check_v6_momentum_filter(rsi_1h: float, adx: float, di_plus: float, di_minus: float,
                             estimated_potential: float, config: Dict) -> tuple:
    """
    V6 Momentum Filter - Rejects trades without sufficient momentum

    Returns: (passed: bool, rejection_reason: str or None, score_adjustment: int)
    """
    if not config.get('V6_MOMENTUM_FILTER_ENABLED', True):
        return True, None, 0

    score_adj = 0

    # Estimated potential filter (soft - only reject if very low)
    min_potential = config.get('V6_MIN_ESTIMATED_POTENTIAL_PCT', 8.0)
    if estimated_potential < min_potential * 0.5:  # Only reject if < 4%
        return False, "V6_LOW_POTENTIAL", -15

    # RSI filter (soft)
    rsi_min = config.get('V6_RSI_MIN_AT_ENTRY', 40)
    rsi_bullish = config.get('V6_RSI_BULLISH_THRESHOLD', 50)

    if rsi_1h and rsi_1h < rsi_min * 0.8:  # Only reject if RSI < 32
        return False, "V6_RSI_TOO_LOW", -10

    # Scoring
    if rsi_1h and rsi_1h > rsi_bullish:
        score_adj += config.get('V6_SCORE_RSI_BULLISH', 10)

    # ADX filter (soft)
    adx_min = config.get('V6_ADX_MIN_AT_ENTRY', 15)
    adx_strong = config.get('V6_ADX_STRONG_THRESHOLD', 25)

    if adx and adx > adx_strong:
        score_adj += config.get('V6_SCORE_ADX_STRONG', 10)
    elif adx and adx < adx_min * 0.5:  # Only reject if ADX < 7.5
        return False, "V6_ADX_TOO_LOW", -10

    # DMI scoring
    if di_plus and di_minus and di_plus > di_minus:
        score_adj += config.get('V6_SCORE_DMI_POSITIVE', 5)

    return True, None, score_adj


def check_v6_entry_limiter(symbol: str, entry_price: float, entry_time,
                           recent_trades: list, config: Dict) -> tuple:
    """
    V6 Entry Limiter - Limits multiple entries on same breakout zone

    recent_trades: list of dicts with keys: symbol, entry_price, entry_time, pnl

    Returns: (passed: bool, rejection_reason: str or None)
    """
    if not config.get('V6_ENTRY_LIMITER_ENABLED', True):
        return True, None

    zone_pct = config.get('V6_ENTRY_ZONE_PCT', 2.0)
    zone_min = entry_price * (1 - zone_pct / 100)
    zone_max = entry_price * (1 + zone_pct / 100)

    # Count entries in zone for same symbol
    entries_in_zone = [
        t for t in recent_trades
        if t.get('symbol') == symbol
        and zone_min <= t.get('entry_price', 0) <= zone_max
    ]

    max_entries = config.get('V6_MAX_ENTRIES_PER_ZONE', 2)
    if len(entries_in_zone) >= max_entries:
        return False, "V6_MAX_ENTRIES_ZONE"

    # Check cooldown
    symbol_trades = [t for t in recent_trades if t.get('symbol') == symbol]
    if symbol_trades:
        # Get most recent trade
        last_trade = max(symbol_trades, key=lambda t: t.get('entry_time', entry_time))
        last_time = last_trade.get('entry_time')

        if last_time and entry_time:
            try:
                if isinstance(last_time, str):
                    from datetime import datetime
                    last_time = datetime.fromisoformat(last_time.replace('Z', '+00:00'))
                if isinstance(entry_time, str):
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))

                hours_since = (entry_time - last_time).total_seconds() / 3600

                # Different cooldown if last trade was a loss
                if last_trade.get('pnl', 0) < 0:
                    cooldown = config.get('V6_ENTRY_COOLDOWN_AFTER_LOSS', 12)
                else:
                    cooldown = config.get('V6_ENTRY_COOLDOWN_HOURS', 4)

                if hours_since < cooldown:
                    return False, "V6_ENTRY_COOLDOWN"
            except:
                pass  # If datetime parsing fails, skip cooldown check

    return True, None


def calculate_v6_score(timeframe: str, retest_hours: float, entry_hours: float,
                       distance_pct: float, rsi_1h: float, adx: float,
                       di_plus: float, di_minus: float, has_cvd_divergence: bool,
                       config: Dict) -> int:
    """
    V6 Combined Scoring - Calculates total V6 score for trade quality

    Returns: score (int) - higher is better, 40+ = excellent, <10 = poor
    """
    if not config.get('V6_SCORING_ENABLED', True):
        return 50  # Default neutral score

    score = 0

    # 1. Timing Score
    _, _, timing_score = check_v6_timing_filter(
        timeframe, retest_hours, entry_hours, distance_pct, config
    )
    score += timing_score

    # 2. Momentum Score
    _, _, momentum_score = check_v6_momentum_filter(
        rsi_1h, adx, di_plus, di_minus, 10.0, config  # Use default potential
    )
    score += momentum_score

    # 3. CVD Score
    if not has_cvd_divergence:
        score += config.get('V6_SCORE_CVD_NO_DIV', 10)
    elif timeframe == '30m':
        score += config.get('V6_SCORE_CVD_DIV_30M', 0)  # 30m tolerates divergence
    else:
        score += config.get('V6_SCORE_CVD_DIV_OTHER', -10)

    # 4. Timeframe Score
    if timeframe == '30m':
        score += config.get('V6_SCORE_TF_30M', 10)
    elif timeframe == '1h':
        score += config.get('V6_SCORE_TF_1H', 5)
    else:
        score += config.get('V6_SCORE_TF_15M', 0)

    return score


def get_v6_score_grade(score: int, config: Dict) -> str:
    """Get letter grade for V6 score"""
    excellent = config.get('V6_EXCELLENT_SCORE', 40)
    good = config.get('V6_GOOD_SCORE', 25)
    min_score = config.get('V6_MIN_SCORE', 10)

    if score >= excellent:
        return 'A'  # Excellent - 75.5% WR
    elif score >= good:
        return 'B'  # Good - 67.4% WR
    elif score >= min_score:
        return 'C'  # Medium - 63.0% WR
    else:
        return 'F'  # Poor - 53.8% WR → Should reject


def estimate_profit_potential(df_4h, entry_price: float, lookback: int = 50) -> float:
    """
    Estimate profit potential based on:
    1. Recent swing high distance
    2. ATR volatility

    Returns: estimated potential in %
    """
    if df_4h is None or len(df_4h) < lookback:
        return 15.0  # Default estimate

    try:
        # Get recent high
        recent_data = df_4h.tail(lookback)
        recent_high = recent_data['high'].max()

        # Calculate ATR
        high = recent_data['high'].values
        low = recent_data['low'].values
        close = recent_data['close'].values

        tr = np.maximum(high[1:] - low[1:],
                       np.maximum(np.abs(high[1:] - close[:-1]),
                                 np.abs(low[1:] - close[:-1])))
        atr = np.mean(tr[-14:]) if len(tr) >= 14 else np.mean(tr)

        # Potential = distance to recent high + 1.5 ATR
        if entry_price > 0:
            high_potential = (recent_high - entry_price) / entry_price * 100
            atr_potential = (atr * 1.5) / entry_price * 100

            total_potential = max(high_potential, 0) + atr_potential
            return min(total_potential, 50.0)  # Cap at 50%

        return 15.0
    except:
        return 15.0


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class BacktestEngine:
    def __init__(self, config: Dict = None):
        self.config = config or DEFAULT_CONFIG.copy()
        init_db()

    def _get_vp_label(self, vp_result: dict, vp_data: dict, entry_price: float = None) -> str:
        """Generate a human-readable VP label based on analysis."""
        score = vp_result.get('vp_score', 0)
        position = vp_result.get('vp_position', 'UNKNOWN')
        poc = vp_data.get('poc')

        # Check if POC is above entry (pullback support zone)
        poc_above_entry = False
        if poc and entry_price and poc > entry_price:
            poc_distance_pct = (poc - entry_price) / entry_price * 100
            if poc_distance_pct < 3.0:
                poc_above_entry = True

        if score >= 70:
            if poc_above_entry:
                return "STRONG POC SUPPORT"
            elif position == 'AT_POC' or position == 'IN_VA':
                return "STRONG SUPPORT (POC/VA)"
            else:
                return "EXCELLENT SETUP"
        elif score >= 50:
            if poc_above_entry:
                return "POC SUPPORT ZONE"
            elif position == 'IN_VA':
                return "GOOD SUPPORT (IN VA)"
            elif position == 'ABOVE_VAH':
                return "BREAKOUT ZONE"
            else:
                return "GOOD SETUP"
        elif score >= 30:
            if poc_above_entry:
                return "POC PULLBACK SUPPORT"
            return "MODERATE SUPPORT"
        else:
            if position == 'ABOVE_VAH':
                return "OVEREXTENDED"
            return "WEAK SUPPORT"

    def run_backtest(self, symbol: str, start_date: str, end_date: str, progress_callback=None, strategy_version: str = 'v1') -> int:
        """
        Run complete backtest for a symbol and return the backtest_run_id
        strategy_version:
            'v1' = legacy (no filters)
            'v2' = optimized (with advanced filters)
            'v3' = Golden Box retest entry
            'v4' = V3 + optimized filters (quality, timing, OB)
            'v5' = V4 + VP trajectory filter (bounce confirmation)
        """
        db = SessionLocal()

        try:
            if progress_callback:
                progress_callback(f"Starting backtest for {symbol} ({strategy_version.upper()})...")

            # Create backtest run record
            backtest_run = BacktestRun(
                symbol=symbol,
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d"),
                config=self.config,
                strategy_version=strategy_version,
                v2_rejected_count=0,
                v2_rejection_reasons={}
            )
            db.add(backtest_run)
            db.commit()
            db.refresh(backtest_run)

            if progress_callback:
                progress_callback(f"Fetching data...")

            # Fetch data - increased warmup for TL detection (1500 bars = ~62 days for 1H)
            data = {}
            warmup = self.config.get('DATA_WARMUP_BARS', 1500)
            for tf in ["15m", "30m", "1h", "4h"]:
                df = get_binance_klines(symbol, tf, start_date, end_date, warmup_bars=warmup)
                data[tf] = df
                if progress_callback:
                    progress_callback(f"  {tf}: {len(df)} bars")

            # Fetch BTC data for correlation (if not already trading BTC)
            btc_data = {}
            if symbol != 'BTCUSDT' and self.config.get('BTC_CORR_ENABLED', False):
                if progress_callback:
                    progress_callback(f"Fetching BTC data for correlation...")
                for tf in ["1h", "4h"]:
                    btc_df = get_binance_klines('BTCUSDT', tf, start_date, end_date, warmup_bars=600)
                    btc_data[tf] = btc_df
                    if progress_callback:
                        progress_callback(f"  BTC {tf}: {len(btc_df)} bars")

            # Fetch ETH data for correlation (if not already trading ETH)
            eth_data = {}
            if symbol != 'ETHUSDT' and self.config.get('ETH_CORR_ENABLED', False):
                if progress_callback:
                    progress_callback(f"Fetching ETH data for correlation...")
                for tf in ["1h", "4h"]:
                    eth_df = get_binance_klines('ETHUSDT', tf, start_date, end_date, warmup_bars=600)
                    eth_data[tf] = eth_df
                    if progress_callback:
                        progress_callback(f"  ETH {tf}: {len(eth_df)} bars")

            # Fetch Daily data for RSI Multi-TF alignment
            daily_data = None
            if self.config.get('RSI_MTF_ENABLED', False):
                if progress_callback:
                    progress_callback(f"Fetching Daily data for RSI MTF...")
                daily_data = get_binance_klines(symbol, '1d', start_date, end_date, warmup_bars=100)
                if progress_callback:
                    progress_callback(f"  Daily: {len(daily_data)} bars")

            # Calculate indicators
            if progress_callback:
                progress_callback(f"Calculating indicators...")

            indicators = {}
            indicators_full = {}  # Full indicators for mega_buy_details

            # Calculate for 15m, 30m, 1h, 4h (all TFs)
            for tf in ["15m", "30m", "1h", "4h"]:
                df = data[tf]
                high = df['high'].values
                low = df['low'].values
                close = df['close'].values
                volume = df['volume'].values

                stc = calc_adaptive_stochastic(close, self.config['STOCH_LENGTH'], self.config['STOCH_FAST'], self.config['STOCH_SLOW'])
                rsi = calc_rsi(close, self.config['RSI_LENGTH'])
                adx, plus_di, minus_di = calc_adx(high, low, close, self.config['DMI_LENGTH'])
                lazybar = calc_lazybar(high, low, close)
                ec_rsi, ec_slow = calc_ec_rsi(close, self.config['EC_RSI_PERIOD'], self.config['EC_SLOW_MA_PERIOD'])

                # Volume average (20 bars)
                n = len(volume)
                vol_avg = np.zeros(n)
                for i in range(20, n):
                    vol_avg[i] = np.mean(volume[i-20+1:i+1])

                # Basic indicators for STC validation (15m, 30m, 1h only)
                if tf in ["15m", "30m", "1h"]:
                    indicators[tf] = {
                        'stc': stc,
                        'rsi': rsi,
                        'plus_di': plus_di,
                        'minus_di': minus_di
                    }

                # Full indicators for mega_buy_details (all TFs)
                indicators_full[tf] = {
                    'stc': stc,
                    'rsi': rsi,
                    'plus_di': plus_di,
                    'minus_di': minus_di,
                    'adx': adx,
                    'lazybar': lazybar,
                    'ec_rsi': ec_rsi,
                    'vol_avg': vol_avg
                }

            # Progressive indicators
            df_1h = data["1h"]
            ema100_1h = calc_ema(df_1h['close'].values, self.config['EMA100_PERIOD'])
            df_4h = data["4h"]
            ema20_4h = calc_ema(df_4h['close'].values, self.config['EMA20_PERIOD'])

            # Use STANDARD Ichimoku (fixed parameters) - matches TradingView indicator
            # See: mega-buy-ai/docs/ichimoku-indicateur.md
            cloud_top_1h = calc_standard_ichimoku_cloud(
                df_1h['high'].values, df_1h['low'].values, df_1h['close'].values,
                tenkan_period=self.config['ICHIMOKU_TENKAN'],
                kijun_period=self.config['ICHIMOKU_KIJUN'],
                senkou_b_period=self.config['ICHIMOKU_SENKOU_B'],
                displacement=self.config['ICHIMOKU_DISPLACEMENT']
            )

            df_30m = data["30m"]
            cloud_top_30m = calc_standard_ichimoku_cloud(
                df_30m['high'].values, df_30m['low'].values, df_30m['close'].values,
                tenkan_period=self.config['ICHIMOKU_TENKAN'],
                kijun_period=self.config['ICHIMOKU_KIJUN'],
                senkou_b_period=self.config['ICHIMOKU_SENKOU_B'],
                displacement=self.config['ICHIMOKU_DISPLACEMENT']
            )

            # Fibonacci data on 4H (will be calculated dynamically per entry point)
            fib_4h_high = df_4h['high'].values
            fib_4h_low = df_4h['low'].values
            fib_4h_close = df_4h['close'].values

            # Fibonacci data on 1H
            fib_1h_high = df_1h['high'].values
            fib_1h_low = df_1h['low'].values
            fib_1h_close = df_1h['close'].values

            progressive_indicators = {
                '1h': {'ema100': ema100_1h, 'cloud_top': cloud_top_1h, 'high': fib_1h_high, 'low': fib_1h_low, 'close': fib_1h_close, 'volume': df_1h['volume'].values, 'rsi': indicators['1h']['rsi']},
                '30m': {'cloud_top': cloud_top_30m},
                '4h': {'ema20': ema20_4h, 'high': fib_4h_high, 'low': fib_4h_low, 'close': fib_4h_close, 'volume': df_4h['volume'].values, 'rsi': calc_rsi(df_4h['close'].values, self.config['RSI_LENGTH'])}
            }

            # Detect trendlines
            high_1h = df_1h['high'].values
            close_1h = df_1h['close'].values

            def build_trendlines(pivots, tl_type):
                tls = []
                for i in range(len(pivots)):
                    for j in range(i + 1, len(pivots)):
                        p1 = pivots[i]
                        p2 = pivots[j]
                        if p2['price'] >= p1['price']:
                            continue
                        if p2['idx'] - p1['idx'] < self.config['TL_MIN_BARS']:
                            continue
                        slope = (p2['price'] - p1['price']) / (p2['idx'] - p1['idx'])
                        tls.append({
                            'p1_idx': p1['idx'],
                            'p1_price': p1['price'],
                            'p2_idx': p2['idx'],
                            'p2_price': p2['price'],
                            'slope': slope,
                            'p1_dt': df_1h.iloc[p1['idx']]['datetime'],
                            'p2_dt': df_1h.iloc[p2['idx']]['datetime'],
                            'type': tl_type
                        })
                return tls

            pivots_major = find_pivot_highs_luxalgo(high_1h, self.config['TL_SWING_MAJOR'])
            trendlines_major = build_trendlines(pivots_major, 'major')

            trendlines_local = []
            if self.config['USE_MULTI_LEVEL_TL']:
                pivots_local = find_pivot_highs_luxalgo(high_1h, self.config['TL_SWING_LOCAL'])
                trendlines_local = build_trendlines(pivots_local, 'local')

            trendlines = trendlines_major + trendlines_local

            # Detect MEGA BUY signals
            if progress_callback:
                progress_callback(f"Detecting MEGA BUY signals...")

            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)

            all_mega_buys = []
            for tf in ["15m", "30m", "1h"]:
                mega_buys, _, _, _, _ = detect_mega_buy_full(data[tf], tf, self.config)
                for mb in mega_buys:
                    if start_dt <= mb['datetime'] < end_dt:
                        mb_dt = mb['datetime']

                        # Get indicators for all TFs
                        ind_all = {}
                        for check_tf in ["15m", "30m", "1h"]:
                            df_check = data[check_tf]
                            closest_idx = None
                            for i, row in df_check.iterrows():
                                if row['datetime'] <= mb_dt:
                                    closest_idx = i

                            if closest_idx is not None:
                                ind_all[check_tf] = {
                                    'stc': float(indicators[check_tf]['stc'][closest_idx]) if closest_idx < len(indicators[check_tf]['stc']) and not np.isnan(indicators[check_tf]['stc'][closest_idx]) else None,
                                    'rsi': float(indicators[check_tf]['rsi'][closest_idx]) if closest_idx < len(indicators[check_tf]['rsi']) and not np.isnan(indicators[check_tf]['rsi'][closest_idx]) else None,
                                    'di_plus': float(indicators[check_tf]['plus_di'][closest_idx]) if closest_idx < len(indicators[check_tf]['plus_di']) else None,
                                    'di_minus': float(indicators[check_tf]['minus_di'][closest_idx]) if closest_idx < len(indicators[check_tf]['minus_di']) else None,
                                }
                            else:
                                ind_all[check_tf] = {'stc': None, 'rsi': None, 'di_plus': None, 'di_minus': None}

                        mb['indicators_all_tf'] = ind_all
                        mb['stc_oversold_any'] = any(
                            ind_all[tf]['stc'] is not None and ind_all[tf]['stc'] < 0.2
                            for tf in ["15m", "30m", "1h"]
                        )

                        # Calculate full MEGA BUY details for all TFs (DMI moves, RSI moves, Volume %, LazyBar, EC RSI)
                        mb['mega_buy_details'] = calculate_mega_buy_details(data, indicators_full, mb_dt, self.config)

                        # Find trendline
                        mb_1h_idx = None
                        for i, row in df_1h.iterrows():
                            if row['datetime'] <= mb_dt:
                                mb_1h_idx = i

                        active_tl = None
                        tl_price_at_mb = None
                        all_active_tls = []
                        if mb_1h_idx is not None:
                            mb_price = close_1h[mb_1h_idx]
                            for tl in trendlines:
                                if tl['p2_idx'] <= mb_1h_idx:
                                    tl_price = tl['p1_price'] + tl['slope'] * (mb_1h_idx - tl['p1_idx'])
                                    if mb_price < tl_price:
                                        distance_pct = (tl_price - mb_price) / mb_price * 100
                                        if distance_pct <= self.config['MAX_TL_DISTANCE_PCT']:
                                            all_active_tls.append({
                                                'tl': tl,
                                                'price': tl_price,
                                                'distance_pct': distance_pct
                                            })

                            if all_active_tls:
                                if self.config['TL_SELECTION_STRATEGY'] == 'highest':
                                    all_active_tls.sort(key=lambda x: x['price'], reverse=True)
                                else:
                                    all_active_tls.sort(key=lambda x: x['price'], reverse=False)
                                active_tl = all_active_tls[0]['tl']
                                tl_price_at_mb = all_active_tls[0]['price']

                        mb['trendline'] = active_tl
                        mb['tl_price_at_mb'] = tl_price_at_mb
                        mb['mb_1h_idx'] = mb_1h_idx

                        # Find TL break and entry
                        swing_highs_1h = find_swing_highs(high_1h, left=self.config['SWING_HIGH_LEFT'], right=self.config['SWING_HIGH_RIGHT'])
                        tl_break = None
                        entry_point = None
                        tl_retest_count = 0

                        if active_tl and mb_1h_idx:
                            # Count retests before break (high touches TL but close stays below)
                            for i in range(mb_1h_idx + 1, len(df_1h)):
                                tl_price = active_tl['p1_price'] + active_tl['slope'] * (i - active_tl['p1_idx'])
                                # Check if this candle retests (high >= TL price but close < TL price)
                                # A retest = wick touches/crosses TL but body stays below
                                if high_1h[i] >= tl_price * 0.998 and close_1h[i] < tl_price:
                                    tl_retest_count += 1
                                # Stop counting if we have a break (close above TL)
                                if close_1h[i] > tl_price:
                                    break

                            # Now find the actual break
                            tl_prior_false_breaks = 0
                            tl_false_break_details = []
                            tl_rejected_false_breaks = False

                            for i in range(mb_1h_idx + 1, len(df_1h)):
                                tl_price = active_tl['p1_price'] + active_tl['slope'] * (i - active_tl['p1_idx'])
                                tl_price_prev = active_tl['p1_price'] + active_tl['slope'] * (i - 1 - active_tl['p1_idx'])
                                if close_1h[i] > tl_price and close_1h[i-1] <= tl_price_prev:
                                    # Found a break - check for prior false breaks
                                    if self.config.get('TL_ANTI_FALSE_BREAKS_ENABLED', True):
                                        confirm_bars = self.config.get('TL_BREAK_CONFIRM_BARS', 2)
                                        max_prior_breaks = self.config.get('TL_MAX_PRIOR_BREAKS', 1)

                                        # Count false breaks from TL P2 (TL formation) to this break
                                        # This captures ALL false breaks on the TL, not just since signal
                                        tl_start_idx = active_tl['p2_idx'] + 1  # Start checking after TL is formed
                                        tl_prior_false_breaks, tl_false_break_details = count_tl_prior_false_breaks(
                                            close_1h, active_tl, tl_start_idx, i, confirm_bars
                                        )

                                        # If too many prior false breaks, this TL is unreliable
                                        if tl_prior_false_breaks > max_prior_breaks:
                                            tl_rejected_false_breaks = True
                                            # Don't accept this break, continue looking for a better TL break
                                            # or skip entirely
                                            continue

                                    alert_price = mb['close']
                                    break_price = close_1h[i]
                                    diff_pct = (break_price - alert_price) / alert_price * 100
                                    break_dt = df_1h.iloc[i]['datetime']
                                    delay_hours = (break_dt - mb_dt).total_seconds() / 3600

                                    tl_break = {
                                        'dt': break_dt,
                                        'idx': i,
                                        'price': break_price,
                                        'tl_price': tl_price,
                                        'delay_hours': delay_hours,
                                        'alert_price': alert_price,
                                        'diff_pct': diff_pct,
                                        'tl_type': active_tl.get('type', 'unknown'),
                                        'retest_count': tl_retest_count,
                                        'prior_false_breaks': tl_prior_false_breaks,
                                        'false_break_details': tl_false_break_details,
                                    }

                                    # Search for entry point
                                    for entry_idx in range(i, min(i + 50, len(df_1h))):
                                        entry_dt = df_1h.iloc[entry_idx]['datetime']
                                        entry_price = close_1h[entry_idx]

                                        entry_diff_pct = (entry_price - break_price) / break_price * 100
                                        if entry_diff_pct > self.config['MAX_BREAK_DIFF_PCT']:
                                            break

                                        entry_idx_30m = None
                                        entry_idx_4h = None
                                        for idx_30m, row_30m in data["30m"].iterrows():
                                            if row_30m['datetime'] >= entry_dt:
                                                entry_idx_30m = idx_30m
                                                break
                                            entry_idx_30m = idx_30m
                                        for idx_4h, row_4h in data["4h"].iterrows():
                                            if row_4h['datetime'] >= entry_dt:
                                                entry_idx_4h = idx_4h
                                                break
                                            entry_idx_4h = idx_4h

                                        ema100_val = progressive_indicators['1h']['ema100'][entry_idx] if entry_idx < len(progressive_indicators['1h']['ema100']) else 0
                                        cloud_1h_val = progressive_indicators['1h']['cloud_top'][entry_idx] if entry_idx < len(progressive_indicators['1h']['cloud_top']) else 0
                                        cloud_30m_val = progressive_indicators['30m']['cloud_top'][entry_idx_30m] if entry_idx_30m and entry_idx_30m < len(progressive_indicators['30m']['cloud_top']) else 0
                                        ema20_4h_val = progressive_indicators['4h']['ema20'][entry_idx_4h] if entry_idx_4h and entry_idx_4h < len(progressive_indicators['4h']['ema20']) else 0
                                        price_30m = data["30m"]['close'].values[entry_idx_30m] if entry_idx_30m else entry_price
                                        price_4h = data["4h"]['close'].values[entry_idx_4h] if entry_idx_4h else entry_price

                                        cond_ema100 = entry_price > ema100_val if ema100_val > 0 else False
                                        cond_ema20_4h = price_4h > ema20_4h_val if ema20_4h_val > 0 else False
                                        cond_cloud_1h = entry_price > cloud_1h_val if cloud_1h_val > 0 else False
                                        cond_cloud_30m = price_30m > cloud_30m_val if cloud_30m_val > 0 else False

                                        choch_bos_breaks = detect_choch_bos(df_1h, close_1h, high_1h, swing_highs_1h, mb_1h_idx, entry_idx - mb_1h_idx + 10)
                                        choch_bos_valid = any(brk['idx'] <= entry_idx for brk in choch_bos_breaks)
                                        first_choch_bos = next((brk for brk in choch_bos_breaks if brk['idx'] <= entry_idx), None)

                                        # Fibonacci levels check on 4H
                                        fib_bonus = False
                                        fib_data = None
                                        fib_levels_status = {}
                                        if self.config.get('FIB_ENABLED', False) and entry_idx_4h:
                                            # Calculate Fib using data UP TO entry point (lookback from entry_idx_4h)
                                            lookback = self.config.get('FIB_SWING_LOOKBACK', 50)
                                            min_range = self.config.get('FIB_MIN_SWING_RANGE_PCT', 5.0)
                                            fib_level = self.config.get('FIB_LEVEL', 0.382)

                                            # Get 4H data up to entry point
                                            if entry_idx_4h >= lookback:
                                                fib_high = progressive_indicators['4h']['high'][:entry_idx_4h + 1]
                                                fib_low = progressive_indicators['4h']['low'][:entry_idx_4h + 1]
                                                fib_close = progressive_indicators['4h']['close'][:entry_idx_4h + 1]

                                                fib_data = calc_fibonacci_levels(fib_high, fib_low, fib_close, lookback, min_range)
                                                if fib_data:
                                                    # Check all important Fibonacci levels
                                                    # Use entry_price (not price_4h) for consistent comparison
                                                    fib_levels_to_check = [0.236, 0.382, 0.5, 0.618, 0.786]
                                                    for level in fib_levels_to_check:
                                                        level_info = check_fib_level_break(entry_price, fib_data, level)
                                                        if level_info:
                                                            fib_levels_status[str(level)] = {
                                                                'price': level_info['fib_price'],
                                                                'break': level_info['break'],
                                                                'distance_pct': level_info['distance_pct']
                                                            }
                                                    # Main bonus is based on 38.2% level
                                                    if '0.382' in fib_levels_status and fib_levels_status['0.382']['break']:
                                                        fib_bonus = True

                                        # Fibonacci levels check on 1H
                                        fib_data_1h = None
                                        fib_levels_status_1h = {}
                                        if self.config.get('FIB_ENABLED', False) and entry_idx:
                                            lookback_1h = self.config.get('FIB_SWING_LOOKBACK', 50) * 4  # More bars for 1H (200 = ~50 on 4H)
                                            min_range = self.config.get('FIB_MIN_SWING_RANGE_PCT', 5.0)

                                            # Get 1H data up to entry point
                                            if entry_idx >= lookback_1h:
                                                fib_high_1h = progressive_indicators['1h']['high'][:entry_idx + 1]
                                                fib_low_1h = progressive_indicators['1h']['low'][:entry_idx + 1]
                                                fib_close_1h = progressive_indicators['1h']['close'][:entry_idx + 1]

                                                fib_data_1h = calc_fibonacci_levels(fib_high_1h, fib_low_1h, fib_close_1h, lookback_1h, min_range)
                                                if fib_data_1h:
                                                    # Check all important Fibonacci levels on 1H
                                                    for level in [0.236, 0.382, 0.5, 0.618, 0.786]:
                                                        level_info = check_fib_level_break(entry_price, fib_data_1h, level)
                                                        if level_info:
                                                            fib_levels_status_1h[str(level)] = {
                                                                'price': level_info['fib_price'],
                                                                'break': level_info['break'],
                                                                'distance_pct': level_info['distance_pct']
                                                            }

                                        # Order Block detection on 1H
                                        ob_bonus = False
                                        ob_result = None
                                        if self.config.get('OB_ENABLED', False) and entry_idx:
                                            ob_lookback = self.config.get('OB_LOOKBACK', 100)
                                            ob_min_impulse = self.config.get('OB_MIN_IMPULSE_PCT', 2.0)
                                            ob_min_candles = self.config.get('OB_MIN_IMPULSE_CANDLES', 3)
                                            ob_max_age = self.config.get('OB_MAX_AGE_BARS', 200)
                                            ob_proximity = self.config.get('OB_PROXIMITY_PCT', 2.0)
                                            ob_require_unmitigated = self.config.get('OB_REQUIRE_UNMITIGATED', True)

                                            # Detect Order Blocks up to entry point
                                            ob_open = progressive_indicators['1h']['close'][:entry_idx + 1]  # Use close as proxy for open
                                            ob_high = progressive_indicators['1h']['high'][:entry_idx + 1]
                                            ob_low = progressive_indicators['1h']['low'][:entry_idx + 1]
                                            ob_close = progressive_indicators['1h']['close'][:entry_idx + 1]
                                            ob_datetimes = [df_1h.iloc[j]['datetime'] for j in range(entry_idx + 1)]

                                            # Shift close by 1 to approximate open
                                            ob_open_approx = np.roll(ob_close, 1)
                                            ob_open_approx[0] = ob_close[0]

                                            order_blocks = detect_order_blocks(
                                                ob_open_approx, ob_high, ob_low, ob_close, ob_datetimes,
                                                lookback=ob_lookback,
                                                min_impulse_pct=ob_min_impulse,
                                                min_impulse_candles=ob_min_candles,
                                                max_age_bars=ob_max_age
                                            )

                                            if order_blocks:
                                                ob_result = find_nearest_order_block(
                                                    order_blocks, entry_price,
                                                    proximity_pct=ob_proximity,
                                                    require_unmitigated=ob_require_unmitigated
                                                )
                                                if ob_result and ob_result['is_valid']:
                                                    ob_bonus = True

                                        # Order Block detection on 4H
                                        ob_bonus_4h = False
                                        ob_result_4h = None
                                        if self.config.get('OB_ENABLED', False) and entry_idx_4h is not None:
                                            # Use 4H data for OB detection
                                            ob_high_4h = progressive_indicators['4h']['high'][:entry_idx_4h + 1]
                                            ob_low_4h = progressive_indicators['4h']['low'][:entry_idx_4h + 1]
                                            ob_close_4h = progressive_indicators['4h']['close'][:entry_idx_4h + 1]
                                            ob_datetimes_4h = [df_4h.iloc[j]['datetime'] for j in range(entry_idx_4h + 1)]

                                            # Approximate open from close
                                            ob_open_4h = np.roll(ob_close_4h, 1)
                                            ob_open_4h[0] = ob_close_4h[0]

                                            order_blocks_4h = detect_order_blocks(
                                                ob_open_4h, ob_high_4h, ob_low_4h, ob_close_4h, ob_datetimes_4h,
                                                lookback=ob_lookback,
                                                min_impulse_pct=ob_min_impulse,
                                                min_impulse_candles=ob_min_candles,
                                                max_age_bars=ob_max_age // 4  # Adjust for 4H timeframe
                                            )

                                            if order_blocks_4h:
                                                ob_result_4h = find_nearest_order_block(
                                                    order_blocks_4h, entry_price,
                                                    proximity_pct=ob_proximity,
                                                    require_unmitigated=ob_require_unmitigated
                                                )
                                                if ob_result_4h and ob_result_4h['is_valid']:
                                                    ob_bonus_4h = True

                                        # BTC Correlation analysis (only for altcoins)
                                        btc_corr_1h = None
                                        btc_corr_4h = None
                                        if self.config.get('BTC_CORR_ENABLED', False) and symbol != 'BTCUSDT' and btc_data:
                                            # Find BTC entry index for 1H
                                            if '1h' in btc_data:
                                                btc_df_1h = btc_data['1h']
                                                btc_entry_idx_1h = None
                                                for idx, row in btc_df_1h.iterrows():
                                                    if row['datetime'] >= entry_dt:
                                                        btc_entry_idx_1h = idx
                                                        break
                                                if btc_entry_idx_1h is not None:
                                                    btc_corr_1h = analyze_btc_trend(
                                                        btc_df_1h['close'].values,
                                                        btc_df_1h['high'].values,
                                                        btc_df_1h['low'].values,
                                                        btc_entry_idx_1h,
                                                        ema_short=self.config.get('BTC_EMA_SHORT', 20),
                                                        ema_long=self.config.get('BTC_EMA_LONG', 50),
                                                        rsi_period=self.config.get('BTC_RSI_PERIOD', 14),
                                                        rsi_bullish=self.config.get('BTC_RSI_BULLISH', 50)
                                                    )

                                            # Find BTC entry index for 4H
                                            if '4h' in btc_data:
                                                btc_df_4h = btc_data['4h']
                                                btc_entry_idx_4h = None
                                                for idx, row in btc_df_4h.iterrows():
                                                    if row['datetime'] >= entry_dt:
                                                        btc_entry_idx_4h = idx
                                                        break
                                                if btc_entry_idx_4h is not None:
                                                    btc_corr_4h = analyze_btc_trend(
                                                        btc_df_4h['close'].values,
                                                        btc_df_4h['high'].values,
                                                        btc_df_4h['low'].values,
                                                        btc_entry_idx_4h,
                                                        ema_short=self.config.get('BTC_EMA_SHORT', 20),
                                                        ema_long=self.config.get('BTC_EMA_LONG', 50),
                                                        rsi_period=self.config.get('BTC_RSI_PERIOD', 14),
                                                        rsi_bullish=self.config.get('BTC_RSI_BULLISH', 50)
                                                    )

                                        # ETH Correlation analysis (only for altcoins)
                                        eth_corr_1h = None
                                        eth_corr_4h = None
                                        if self.config.get('ETH_CORR_ENABLED', False) and symbol != 'ETHUSDT' and eth_data:
                                            # Find ETH entry index for 1H
                                            if '1h' in eth_data:
                                                eth_df_1h = eth_data['1h']
                                                eth_entry_idx_1h = None
                                                for idx, row in eth_df_1h.iterrows():
                                                    if row['datetime'] >= entry_dt:
                                                        eth_entry_idx_1h = idx
                                                        break
                                                if eth_entry_idx_1h is not None:
                                                    eth_corr_1h = analyze_btc_trend(
                                                        eth_df_1h['close'].values,
                                                        eth_df_1h['high'].values,
                                                        eth_df_1h['low'].values,
                                                        eth_entry_idx_1h,
                                                        ema_short=self.config.get('ETH_EMA_SHORT', 20),
                                                        ema_long=self.config.get('ETH_EMA_LONG', 50),
                                                        rsi_period=self.config.get('ETH_RSI_PERIOD', 14),
                                                        rsi_bullish=self.config.get('ETH_RSI_BULLISH', 50)
                                                    )

                                            # Find ETH entry index for 4H
                                            if '4h' in eth_data:
                                                eth_df_4h = eth_data['4h']
                                                eth_entry_idx_4h = None
                                                for idx, row in eth_df_4h.iterrows():
                                                    if row['datetime'] >= entry_dt:
                                                        eth_entry_idx_4h = idx
                                                        break
                                                if eth_entry_idx_4h is not None:
                                                    eth_corr_4h = analyze_btc_trend(
                                                        eth_df_4h['close'].values,
                                                        eth_df_4h['high'].values,
                                                        eth_df_4h['low'].values,
                                                        eth_entry_idx_4h,
                                                        ema_short=self.config.get('ETH_EMA_SHORT', 20),
                                                        ema_long=self.config.get('ETH_EMA_LONG', 50),
                                                        rsi_period=self.config.get('ETH_RSI_PERIOD', 14),
                                                        rsi_bullish=self.config.get('ETH_RSI_BULLISH', 50)
                                                    )

                                        # Fair Value Gap (FVG) detection on 1H
                                        fvg_bonus_1h = False
                                        fvg_result_1h = None
                                        if self.config.get('FVG_ENABLED', False) and entry_idx:
                                            fvg_high = progressive_indicators['1h']['high'][:entry_idx + 1]
                                            fvg_low = progressive_indicators['1h']['low'][:entry_idx + 1]
                                            fvg_close = progressive_indicators['1h']['close'][:entry_idx + 1]
                                            fvg_datetimes = [df_1h.iloc[j]['datetime'] for j in range(entry_idx + 1)]

                                            # Approximate open from close
                                            fvg_open = np.roll(fvg_close, 1)
                                            fvg_open[0] = fvg_close[0]

                                            fvgs_1h = detect_fair_value_gaps(
                                                fvg_high, fvg_low, fvg_close, fvg_open, fvg_datetimes,
                                                lookback=self.config.get('FVG_LOOKBACK', 50),
                                                min_gap_pct=self.config.get('FVG_MIN_GAP_PCT', 0.3)
                                            )

                                            if fvgs_1h:
                                                fvg_result_1h = find_nearest_fvg(
                                                    fvgs_1h, entry_price, entry_idx,
                                                    proximity_pct=self.config.get('FVG_PROXIMITY_PCT', 3.0),
                                                    max_filled_pct=self.config.get('FVG_MAX_FILLED_PCT', 80)
                                                )
                                                if fvg_result_1h and fvg_result_1h['is_valid']:
                                                    fvg_bonus_1h = True

                                        # Fair Value Gap (FVG) detection on 4H
                                        fvg_bonus_4h = False
                                        fvg_result_4h = None
                                        if self.config.get('FVG_ENABLED', False) and entry_idx_4h is not None:
                                            fvg_high_4h = progressive_indicators['4h']['high'][:entry_idx_4h + 1]
                                            fvg_low_4h = progressive_indicators['4h']['low'][:entry_idx_4h + 1]
                                            fvg_close_4h = progressive_indicators['4h']['close'][:entry_idx_4h + 1]
                                            fvg_datetimes_4h = [df_4h.iloc[j]['datetime'] for j in range(entry_idx_4h + 1)]

                                            # Approximate open from close
                                            fvg_open_4h = np.roll(fvg_close_4h, 1)
                                            fvg_open_4h[0] = fvg_close_4h[0]

                                            fvgs_4h = detect_fair_value_gaps(
                                                fvg_high_4h, fvg_low_4h, fvg_close_4h, fvg_open_4h, fvg_datetimes_4h,
                                                lookback=self.config.get('FVG_LOOKBACK', 50) // 4,  # Adjust for 4H
                                                min_gap_pct=self.config.get('FVG_MIN_GAP_PCT', 0.3)
                                            )

                                            if fvgs_4h:
                                                fvg_result_4h = find_nearest_fvg(
                                                    fvgs_4h, entry_price, entry_idx_4h,
                                                    proximity_pct=self.config.get('FVG_PROXIMITY_PCT', 3.0),
                                                    max_filled_pct=self.config.get('FVG_MAX_FILLED_PCT', 80)
                                                )
                                                if fvg_result_4h and fvg_result_4h['is_valid']:
                                                    fvg_bonus_4h = True

                                        # Volume Spike analysis on 1H
                                        vol_spike_1h = None
                                        vol_spike_bonus_1h = False
                                        if self.config.get('VOL_SPIKE_ENABLED', False) and entry_idx:
                                            vol_spike_1h = analyze_volume_spike(
                                                progressive_indicators['1h']['volume'][:entry_idx + 1],
                                                entry_idx,
                                                avg_period=self.config.get('VOL_AVG_PERIOD', 20),
                                                spike_threshold=self.config.get('VOL_SPIKE_THRESHOLD', 2.0),
                                                very_high_threshold=self.config.get('VOL_VERY_HIGH_THRESHOLD', 3.0)
                                            )
                                            if vol_spike_1h and vol_spike_1h['is_bonus']:
                                                vol_spike_bonus_1h = True

                                        # Volume Spike analysis on 4H
                                        vol_spike_4h = None
                                        vol_spike_bonus_4h = False
                                        if self.config.get('VOL_SPIKE_ENABLED', False) and entry_idx_4h is not None:
                                            vol_spike_4h = analyze_volume_spike(
                                                progressive_indicators['4h']['volume'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                avg_period=self.config.get('VOL_AVG_PERIOD', 20) // 4,  # Adjust for 4H
                                                spike_threshold=self.config.get('VOL_SPIKE_THRESHOLD', 2.0),
                                                very_high_threshold=self.config.get('VOL_VERY_HIGH_THRESHOLD', 3.0)
                                            )
                                            if vol_spike_4h and vol_spike_4h['is_bonus']:
                                                vol_spike_bonus_4h = True

                                        # RSI Multi-TF alignment analysis
                                        rsi_mtf = None
                                        rsi_mtf_bonus = False
                                        if self.config.get('RSI_MTF_ENABLED', False) and entry_idx:
                                            # Get RSI values from each timeframe
                                            rsi_1h_val = progressive_indicators['1h']['rsi'][entry_idx] if entry_idx < len(progressive_indicators['1h']['rsi']) else None
                                            rsi_4h_val = progressive_indicators['4h']['rsi'][entry_idx_4h] if entry_idx_4h is not None and entry_idx_4h < len(progressive_indicators['4h']['rsi']) else None

                                            # Calculate Daily RSI
                                            rsi_daily_val = None
                                            if daily_data is not None and len(daily_data) > 0:
                                                # Find the daily bar at entry time
                                                daily_entry_idx = None
                                                for idx, row in daily_data.iterrows():
                                                    if row['datetime'].date() >= entry_dt.date():
                                                        daily_entry_idx = idx
                                                        break
                                                if daily_entry_idx is not None and daily_entry_idx > self.config.get('RSI_MTF_PERIOD', 14):
                                                    daily_rsi = calc_rsi(daily_data['close'].values[:daily_entry_idx + 1], self.config.get('RSI_MTF_PERIOD', 14))
                                                    if len(daily_rsi) > 0:
                                                        rsi_daily_val = daily_rsi[-1]

                                            rsi_mtf = analyze_rsi_mtf(
                                                rsi_1h_val, rsi_4h_val, rsi_daily_val,
                                                threshold=self.config.get('RSI_MTF_THRESHOLD', 50)
                                            )
                                            if rsi_mtf and rsi_mtf['is_bonus']:
                                                rsi_mtf_bonus = True

                                        # ADX Trend Strength analysis on 1H
                                        adx_1h = None
                                        adx_bonus_1h = False
                                        if self.config.get('ADX_ENABLED', False) and entry_idx:
                                            adx_1h = analyze_adx_trend(
                                                progressive_indicators['1h']['high'][:entry_idx + 1],
                                                progressive_indicators['1h']['low'][:entry_idx + 1],
                                                progressive_indicators['1h']['close'][:entry_idx + 1],
                                                entry_idx,
                                                period=self.config.get('ADX_PERIOD', 14),
                                                strong_threshold=self.config.get('ADX_STRONG_THRESHOLD', 25),
                                                moderate_threshold=self.config.get('ADX_MODERATE_THRESHOLD', 20)
                                            )
                                            if adx_1h and adx_1h['is_bonus']:
                                                adx_bonus_1h = True

                                        # ADX Trend Strength analysis on 4H
                                        adx_4h = None
                                        adx_bonus_4h = False
                                        if self.config.get('ADX_ENABLED', False) and entry_idx_4h is not None:
                                            adx_4h = analyze_adx_trend(
                                                progressive_indicators['4h']['high'][:entry_idx_4h + 1],
                                                progressive_indicators['4h']['low'][:entry_idx_4h + 1],
                                                progressive_indicators['4h']['close'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                period=self.config.get('ADX_PERIOD', 14),
                                                strong_threshold=self.config.get('ADX_STRONG_THRESHOLD', 25),
                                                moderate_threshold=self.config.get('ADX_MODERATE_THRESHOLD', 20)
                                            )
                                            if adx_4h and adx_4h['is_bonus']:
                                                adx_bonus_4h = True

                                        # MACD Momentum analysis on 1H
                                        macd_1h = None
                                        macd_bonus_1h = False
                                        if self.config.get('MACD_ENABLED', False) and entry_idx:
                                            macd_1h = analyze_macd_momentum(
                                                progressive_indicators['1h']['close'][:entry_idx + 1],
                                                entry_idx,
                                                fast_period=self.config.get('MACD_FAST', 12),
                                                slow_period=self.config.get('MACD_SLOW', 26),
                                                signal_period=self.config.get('MACD_SIGNAL', 9)
                                            )
                                            if macd_1h and macd_1h['is_bonus']:
                                                macd_bonus_1h = True

                                        # MACD Momentum analysis on 4H
                                        macd_4h = None
                                        macd_bonus_4h = False
                                        if self.config.get('MACD_ENABLED', False) and entry_idx_4h is not None:
                                            macd_4h = analyze_macd_momentum(
                                                progressive_indicators['4h']['close'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                fast_period=self.config.get('MACD_FAST', 12),
                                                slow_period=self.config.get('MACD_SLOW', 26),
                                                signal_period=self.config.get('MACD_SIGNAL', 9)
                                            )
                                            if macd_4h and macd_4h['is_bonus']:
                                                macd_bonus_4h = True

                                        # Bollinger Squeeze analysis on 1H
                                        bb_1h = None
                                        bb_squeeze_bonus_1h = False
                                        if self.config.get('BB_SQUEEZE_ENABLED', False) and entry_idx:
                                            bb_1h = analyze_bollinger_squeeze(
                                                progressive_indicators['1h']['close'][:entry_idx + 1],
                                                entry_idx,
                                                period=self.config.get('BB_PERIOD', 20),
                                                std_dev=self.config.get('BB_STD_DEV', 2.0),
                                                squeeze_threshold=self.config.get('BB_SQUEEZE_THRESHOLD', 4.0),
                                                lookback=self.config.get('BB_SQUEEZE_LOOKBACK', 20)
                                            )
                                            if bb_1h and bb_1h['is_bonus']:
                                                bb_squeeze_bonus_1h = True

                                        # Bollinger Squeeze analysis on 4H
                                        bb_4h = None
                                        bb_squeeze_bonus_4h = False
                                        if self.config.get('BB_SQUEEZE_ENABLED', False) and entry_idx_4h is not None:
                                            bb_4h = analyze_bollinger_squeeze(
                                                progressive_indicators['4h']['close'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                period=self.config.get('BB_PERIOD', 20),
                                                std_dev=self.config.get('BB_STD_DEV', 2.0),
                                                squeeze_threshold=self.config.get('BB_SQUEEZE_THRESHOLD', 4.0),
                                                lookback=self.config.get('BB_SQUEEZE_LOOKBACK', 20)
                                            )
                                            if bb_4h and bb_4h['is_bonus']:
                                                bb_squeeze_bonus_4h = True

                                        # Stochastic RSI analysis on 1H
                                        stoch_rsi_1h = None
                                        stoch_rsi_bonus_1h = False
                                        if self.config.get('STOCH_RSI_ENABLED', False) and entry_idx:
                                            stoch_rsi_1h = analyze_stochastic_rsi(
                                                progressive_indicators['1h']['close'][:entry_idx + 1],
                                                entry_idx,
                                                rsi_period=self.config.get('STOCH_RSI_PERIOD', 14),
                                                stoch_period=self.config.get('STOCH_RSI_STOCH_PERIOD', 14),
                                                k_smooth=self.config.get('STOCH_RSI_K_SMOOTH', 3),
                                                d_smooth=self.config.get('STOCH_RSI_D_SMOOTH', 3),
                                                oversold=self.config.get('STOCH_RSI_OVERSOLD', 20),
                                                overbought=self.config.get('STOCH_RSI_OVERBOUGHT', 80)
                                            )
                                            if stoch_rsi_1h and stoch_rsi_1h['is_bonus']:
                                                stoch_rsi_bonus_1h = True

                                        # Stochastic RSI analysis on 4H
                                        stoch_rsi_4h = None
                                        stoch_rsi_bonus_4h = False
                                        if self.config.get('STOCH_RSI_ENABLED', False) and entry_idx_4h is not None:
                                            stoch_rsi_4h = analyze_stochastic_rsi(
                                                progressive_indicators['4h']['close'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                rsi_period=self.config.get('STOCH_RSI_PERIOD', 14),
                                                stoch_period=self.config.get('STOCH_RSI_STOCH_PERIOD', 14),
                                                k_smooth=self.config.get('STOCH_RSI_K_SMOOTH', 3),
                                                d_smooth=self.config.get('STOCH_RSI_D_SMOOTH', 3),
                                                oversold=self.config.get('STOCH_RSI_OVERSOLD', 20),
                                                overbought=self.config.get('STOCH_RSI_OVERBOUGHT', 80)
                                            )
                                            if stoch_rsi_4h and stoch_rsi_4h['is_bonus']:
                                                stoch_rsi_bonus_4h = True

                                        # EMA Stack analysis on 1H
                                        ema_stack_1h = None
                                        ema_stack_bonus_1h = False
                                        if self.config.get('EMA_STACK_ENABLED', False) and entry_idx:
                                            ema_stack_1h = analyze_ema_stack(
                                                progressive_indicators['1h']['close'][:entry_idx + 1],
                                                entry_idx,
                                                ema8_period=self.config.get('EMA_STACK_8', 8),
                                                ema21_period=self.config.get('EMA_STACK_21', 21),
                                                ema50_period=self.config.get('EMA_STACK_50', 50),
                                                ema100_period=self.config.get('EMA_STACK_100', 100)
                                            )
                                            if ema_stack_1h and ema_stack_1h['is_bonus']:
                                                ema_stack_bonus_1h = True

                                        # EMA Stack analysis on 4H
                                        ema_stack_4h = None
                                        ema_stack_bonus_4h = False
                                        if self.config.get('EMA_STACK_ENABLED', False) and entry_idx_4h is not None:
                                            ema_stack_4h = analyze_ema_stack(
                                                progressive_indicators['4h']['close'][:entry_idx_4h + 1],
                                                entry_idx_4h,
                                                ema8_period=self.config.get('EMA_STACK_8', 8),
                                                ema21_period=self.config.get('EMA_STACK_21', 21),
                                                ema50_period=self.config.get('EMA_STACK_50', 50),
                                                ema100_period=self.config.get('EMA_STACK_100', 100)
                                            )
                                            if ema_stack_4h and ema_stack_4h['is_bonus']:
                                                ema_stack_bonus_4h = True

                                        all_progressive_valid = cond_ema100 and cond_ema20_4h and cond_cloud_1h and cond_cloud_30m and choch_bos_valid

                                        if all_progressive_valid:
                                            entry_point = {
                                                'dt': entry_dt,
                                                'idx': entry_idx,
                                                'price': entry_price,
                                                'diff_from_break_pct': entry_diff_pct,
                                                'diff_from_alert_pct': (entry_price - alert_price) / alert_price * 100,
                                                'progressive': {
                                                    # Indicator VALUES
                                                    'ema100_1h': ema100_val,
                                                    'ema20_4h': ema20_4h_val,
                                                    'cloud_1h': cloud_1h_val,
                                                    'cloud_30m': cloud_30m_val,
                                                    'first_choch_bos': first_choch_bos,
                                                    # Price VALUES used for checks
                                                    'price_1h': entry_price,
                                                    'price_30m': price_30m,
                                                    'price_4h': price_4h,
                                                    # Validation RESULTS (True/False)
                                                    'valid_ema100_1h': cond_ema100,
                                                    'valid_ema20_4h': cond_ema20_4h,
                                                    'valid_cloud_1h': cond_cloud_1h,
                                                    'valid_cloud_30m': cond_cloud_30m,
                                                    'valid_choch_bos': choch_bos_valid,
                                                    # Fibonacci BONUS on 4H (not required for entry)
                                                    'fib_bonus': fib_bonus,
                                                    'fib_swing_high': fib_data['swing_high'] if fib_data else None,
                                                    'fib_swing_low': fib_data['swing_low'] if fib_data else None,
                                                    'fib_levels': fib_levels_status,  # All Fib levels 4H with break status
                                                    # Fibonacci on 1H
                                                    'fib_swing_high_1h': fib_data_1h['swing_high'] if fib_data_1h else None,
                                                    'fib_swing_low_1h': fib_data_1h['swing_low'] if fib_data_1h else None,
                                                    'fib_levels_1h': fib_levels_status_1h,  # All Fib levels 1H with break status
                                                    # Order Block BONUS (SMC) - 1H
                                                    'ob_bonus': ob_bonus,
                                                    'ob_data': ob_result if ob_result and ob_result['is_valid'] else None,
                                                    # Order Block BONUS (SMC) - 4H
                                                    'ob_bonus_4h': ob_bonus_4h,
                                                    'ob_data_4h': ob_result_4h if ob_result_4h and ob_result_4h['is_valid'] else None,
                                                    # BTC Correlation BONUS - 1H
                                                    'btc_corr_1h': btc_corr_1h,
                                                    # BTC Correlation BONUS - 4H
                                                    'btc_corr_4h': btc_corr_4h,
                                                    # ETH Correlation BONUS - 1H
                                                    'eth_corr_1h': eth_corr_1h,
                                                    # ETH Correlation BONUS - 4H
                                                    'eth_corr_4h': eth_corr_4h,
                                                    # Fair Value Gap (FVG) BONUS - 1H
                                                    'fvg_bonus_1h': fvg_bonus_1h,
                                                    'fvg_data_1h': fvg_result_1h if fvg_result_1h and fvg_result_1h['is_valid'] else None,
                                                    # Fair Value Gap (FVG) BONUS - 4H
                                                    'fvg_bonus_4h': fvg_bonus_4h,
                                                    'fvg_data_4h': fvg_result_4h if fvg_result_4h and fvg_result_4h['is_valid'] else None,
                                                    # Volume Spike BONUS - 1H
                                                    'vol_spike_bonus_1h': vol_spike_bonus_1h,
                                                    'vol_spike_1h': vol_spike_1h,
                                                    # Volume Spike BONUS - 4H
                                                    'vol_spike_bonus_4h': vol_spike_bonus_4h,
                                                    'vol_spike_4h': vol_spike_4h,
                                                    # RSI Multi-TF Alignment BONUS
                                                    'rsi_mtf_bonus': rsi_mtf_bonus,
                                                    'rsi_mtf': rsi_mtf,
                                                    # ADX Trend Strength BONUS - 1H
                                                    'adx_bonus_1h': adx_bonus_1h,
                                                    'adx_1h': adx_1h,
                                                    # ADX Trend Strength BONUS - 4H
                                                    'adx_bonus_4h': adx_bonus_4h,
                                                    'adx_4h': adx_4h,
                                                    # MACD Momentum BONUS - 1H
                                                    'macd_bonus_1h': macd_bonus_1h,
                                                    'macd_1h': macd_1h,
                                                    # MACD Momentum BONUS - 4H
                                                    'macd_bonus_4h': macd_bonus_4h,
                                                    'macd_4h': macd_4h,
                                                    # Bollinger Squeeze BONUS - 1H
                                                    'bb_squeeze_bonus_1h': bb_squeeze_bonus_1h,
                                                    'bb_1h': bb_1h,
                                                    # Bollinger Squeeze BONUS - 4H
                                                    'bb_squeeze_bonus_4h': bb_squeeze_bonus_4h,
                                                    'bb_4h': bb_4h,
                                                    # Stochastic RSI BONUS - 1H
                                                    'stoch_rsi_bonus_1h': stoch_rsi_bonus_1h,
                                                    'stoch_rsi_1h': stoch_rsi_1h,
                                                    # Stochastic RSI BONUS - 4H
                                                    'stoch_rsi_bonus_4h': stoch_rsi_bonus_4h,
                                                    'stoch_rsi_4h': stoch_rsi_4h,
                                                    # EMA Stack BONUS - 1H
                                                    'ema_stack_bonus_1h': ema_stack_bonus_1h,
                                                    'ema_stack_1h': ema_stack_1h,
                                                    # EMA Stack BONUS - 4H
                                                    'ema_stack_bonus_4h': ema_stack_bonus_4h,
                                                    'ema_stack_4h': ema_stack_4h,
                                                }
                                            }
                                            break
                                    break

                        mb['tl_break'] = tl_break
                        mb['entry_point'] = entry_point
                        mb['tl_rejected_false_breaks'] = tl_rejected_false_breaks if 'tl_rejected_false_breaks' in dir() else False
                        mb['tl_prior_false_breaks'] = tl_prior_false_breaks if 'tl_prior_false_breaks' in dir() else 0
                        all_mega_buys.append(mb)

            all_mega_buys.sort(key=lambda x: x['datetime'])

            # 15m alone filter
            if self.config['REJECT_15M_ALONE']:
                for mb in all_mega_buys:
                    mb['is_15m_alone'] = False
                    mb['combo_tfs'] = [mb['tf']]

                    if mb['tf'] == '15m':
                        mb_dt = mb['datetime']
                        has_combo = False
                        combo_tfs = ['15m']

                        for other_mb in all_mega_buys:
                            if other_mb['tf'] in ['30m', '1h']:
                                time_diff = abs((other_mb['datetime'] - mb_dt).total_seconds() / 3600)
                                if time_diff <= self.config['COMBO_TIME_WINDOW_HOURS']:
                                    has_combo = True
                                    if other_mb['tf'] not in combo_tfs:
                                        combo_tfs.append(other_mb['tf'])

                        mb['is_15m_alone'] = not has_combo
                        mb['combo_tfs'] = combo_tfs

            # ═══════════════════════════════════════════════════════════════════════════════
            # COMBO PRIMARY TF DETECTION: Only create ONE trade per COMBO using primary TF
            # Priority: 1h > 30m > 15m (use largest TF's box values)
            # ═══════════════════════════════════════════════════════════════════════════════
            TF_PRIORITY = {'1h': 3, '30m': 2, '15m': 1, '4h': 4}
            combo_groups = {}  # Key: combo_key, Value: list of mbs in that combo

            for mb in all_mega_buys:
                combo_tfs = mb.get('combo_tfs', [mb['tf']])
                if len(combo_tfs) > 1:
                    # This is part of a COMBO - create a key based on datetime range
                    mb_dt = mb['datetime']
                    # Find combo key: round to nearest COMBO_TIME_WINDOW_HOURS
                    combo_hour = mb_dt.replace(minute=0, second=0, microsecond=0)
                    combo_key = f"{symbol}_{combo_hour.isoformat()}"

                    if combo_key not in combo_groups:
                        combo_groups[combo_key] = []
                    combo_groups[combo_key].append(mb)

            # For each combo group, mark the primary TF
            for combo_key, mbs in combo_groups.items():
                # Find the highest priority (largest) TF in this combo
                primary_mb = max(mbs, key=lambda x: TF_PRIORITY.get(x['tf'], 0))
                primary_tf = primary_mb['tf']

                # Store primary TF's box values for all alerts in this combo
                primary_box_high = primary_mb['high']
                primary_box_low = primary_mb['low']

                for mb in mbs:
                    mb['combo_primary_tf'] = primary_tf
                    mb['combo_primary_box_high'] = primary_box_high
                    mb['combo_primary_box_low'] = primary_box_low
                    mb['is_combo_primary'] = (mb['tf'] == primary_tf)

            # Mark non-combo alerts as primary (they're the only one)
            for mb in all_mega_buys:
                if 'is_combo_primary' not in mb:
                    mb['is_combo_primary'] = True
                    mb['combo_primary_tf'] = mb['tf']
                    mb['combo_primary_box_high'] = mb['high']
                    mb['combo_primary_box_low'] = mb['low']

            # Store alerts and calculate P&L
            if progress_callback:
                progress_callback(f"Storing {len(all_mega_buys)} alerts...")

            # Stats counters
            stats = {
                'total_alerts': len(all_mega_buys),
                'stc_validated': 0,
                'rejected_15m_alone': 0,
                'rejected_pp_buy': 0,
                'valid_combos': 0,
                'with_tl_break': 0,
                'delay_respected': 0,
                'delay_exceeded': 0,
                'expired': 0,
                'waiting': 0,
                'valid_entries': 0,
                'no_entry': 0,
            }

            total_pnl_c = 0
            total_pnl_d = 0
            trades_count = 0
            processed_entries = set()  # Track unique entries to avoid duplicate P&L counting

            for mb in all_mega_buys:
                # Determine status
                is_15m_alone = mb.get('is_15m_alone', False)
                hours_since = (end_dt - mb['datetime']).total_seconds() / 3600

                # Check PP_buy condition
                pp_buy = mb['conditions'].get('PP_buy', True)

                if not mb['stc_oversold_any']:
                    status = 'REJECTED_STC'
                elif is_15m_alone and self.config['REJECT_15M_ALONE']:
                    status = 'REJECTED_15M_ALONE'
                    stats['rejected_15m_alone'] += 1
                elif self.config.get('REQUIRE_PP_BUY', False) and not pp_buy:
                    status = 'REJECTED_PP_BUY'
                    stats['rejected_pp_buy'] += 1
                elif not mb['trendline']:
                    status = 'REJECTED_NO_TL'
                elif mb.get('tl_rejected_false_breaks', False) and not mb['tl_break']:
                    # TL had too many prior false breaks (price broke above and fell below repeatedly)
                    status = 'REJECTED_TL_FALSE_BREAKS'
                    stats['rejected_tl_false_breaks'] = stats.get('rejected_tl_false_breaks', 0) + 1
                elif not mb['tl_break']:
                    if hours_since > self.config['MAX_TL_BREAK_DELAY_HOURS']:
                        status = 'EXPIRED'
                        stats['expired'] += 1
                    else:
                        status = 'WAITING'
                        stats['waiting'] += 1
                elif mb['tl_break']['delay_hours'] > self.config['MAX_TL_BREAK_DELAY_HOURS']:
                    status = 'REJECTED_DELAY'
                    stats['delay_exceeded'] += 1
                elif not mb['entry_point']:
                    status = 'REJECTED_NO_ENTRY'
                    stats['no_entry'] += 1
                else:
                    status = 'VALID'
                    stats['valid_entries'] += 1

                if mb['stc_oversold_any']:
                    stats['stc_validated'] += 1
                if mb['stc_oversold_any'] and not is_15m_alone:
                    stats['valid_combos'] += 1
                if mb['tl_break']:
                    stats['with_tl_break'] += 1
                    if mb['tl_break']['delay_hours'] <= self.config['MAX_TL_BREAK_DELAY_HOURS']:
                        stats['delay_respected'] += 1

                # Create alert record
                stc_valid_tfs = ','.join([tf for tf in ["15m", "30m", "1h"]
                                          if mb['indicators_all_tf'][tf]['stc'] is not None
                                          and mb['indicators_all_tf'][tf]['stc'] < 0.2])

                alert = Alert(
                    backtest_run_id=backtest_run.id,
                    alert_datetime=mb['datetime'],
                    timeframe=mb['tf'],
                    price_open=float(mb['open']),
                    price_high=float(mb['high']),
                    price_low=float(mb['low']),
                    price_close=float(mb['close']),
                    volume=float(mb['volume']),
                    score=int(mb['score']),
                    conditions=convert_to_json_serializable(mb['conditions']),
                    indicators_15m=convert_to_json_serializable(mb['indicators_all_tf']['15m']),
                    indicators_30m=convert_to_json_serializable(mb['indicators_all_tf']['30m']),
                    indicators_1h=convert_to_json_serializable(mb['indicators_all_tf']['1h']),
                    mega_buy_details=convert_to_json_serializable(mb.get('mega_buy_details', {})),
                    stc_validated=bool(mb['stc_oversold_any']),
                    stc_valid_tfs=stc_valid_tfs,
                    is_15m_alone=bool(is_15m_alone),
                    combo_tfs=','.join(mb.get('combo_tfs', [mb['tf']])),
                    has_trendline=mb['trendline'] is not None,
                    status=status
                )

                if mb['trendline']:
                    alert.tl_type = mb['trendline'].get('type', 'unknown')
                    alert.tl_price_at_alert = mb['tl_price_at_mb']
                    alert.tl_p1_date = mb['trendline']['p1_dt']
                    alert.tl_p1_price = mb['trendline']['p1_price']
                    alert.tl_p2_date = mb['trendline']['p2_dt']
                    alert.tl_p2_price = mb['trendline']['p2_price']

                if mb['tl_break']:
                    alert.has_tl_break = True
                    alert.tl_break_datetime = mb['tl_break']['dt']
                    alert.tl_break_price = mb['tl_break']['price']
                    alert.tl_break_delay_hours = mb['tl_break']['delay_hours']
                    alert.tl_retest_count = mb['tl_break'].get('retest_count', 0)
                    alert.tl_prior_false_breaks = mb['tl_break'].get('prior_false_breaks', 0)
                    alert.delay_exceeded = mb['tl_break']['delay_hours'] > self.config['MAX_TL_BREAK_DELAY_HOURS']

                if mb['entry_point']:
                    alert.has_entry = True
                    alert.entry_datetime = mb['entry_point']['dt']
                    alert.entry_price = mb['entry_point']['price']
                    alert.entry_diff_vs_alert = mb['entry_point']['diff_from_alert_pct']
                    alert.entry_diff_vs_break = mb['entry_point']['diff_from_break_pct']

                    prog = mb['entry_point']['progressive']
                    # Indicator VALUES
                    alert.prog_ema100_1h = prog['ema100_1h']
                    alert.prog_ema20_4h = prog['ema20_4h']
                    alert.prog_cloud_1h = prog['cloud_1h']
                    alert.prog_cloud_30m = prog['cloud_30m']

                    # Price VALUES used for checks
                    alert.prog_price_1h = prog.get('price_1h')
                    alert.prog_price_30m = prog.get('price_30m')
                    alert.prog_price_4h = prog.get('price_4h')

                    # Validation RESULTS (True/False)
                    alert.prog_valid_ema100_1h = prog.get('valid_ema100_1h', False)
                    alert.prog_valid_ema20_4h = prog.get('valid_ema20_4h', False)
                    alert.prog_valid_cloud_1h = prog.get('valid_cloud_1h', False)
                    alert.prog_valid_cloud_30m = prog.get('valid_cloud_30m', False)

                    if prog['first_choch_bos']:
                        alert.prog_choch_bos_valid = True
                        alert.prog_choch_bos_datetime = prog['first_choch_bos']['dt']
                        alert.prog_choch_bos_sh_price = prog['first_choch_bos']['sh_price']

                    # Fibonacci BONUS on 4H (not required for entry)
                    alert.fib_bonus = prog.get('fib_bonus', False)
                    alert.fib_swing_high = prog.get('fib_swing_high')
                    alert.fib_swing_low = prog.get('fib_swing_low')
                    alert.fib_levels = convert_to_json_serializable(prog.get('fib_levels', {}))

                    # Fibonacci on 1H
                    alert.fib_swing_high_1h = prog.get('fib_swing_high_1h')
                    alert.fib_swing_low_1h = prog.get('fib_swing_low_1h')
                    alert.fib_levels_1h = convert_to_json_serializable(prog.get('fib_levels_1h', {}))

                    # Order Block BONUS (SMC) - 1H
                    alert.ob_bonus = prog.get('ob_bonus', False)
                    ob_data = prog.get('ob_data')
                    if ob_data:
                        alert.ob_zone_high = ob_data.get('zone_high')
                        alert.ob_zone_low = ob_data.get('zone_low')
                        alert.ob_datetime = ob_data.get('datetime')
                        alert.ob_distance_pct = ob_data.get('distance_pct')
                        alert.ob_position = ob_data.get('position')
                        alert.ob_strength = ob_data.get('strength')
                        alert.ob_impulse_pct = ob_data.get('impulse_pct')
                        alert.ob_age_bars = ob_data.get('age_bars')
                        alert.ob_mitigated = ob_data.get('mitigated', False)
                        alert.ob_data = convert_to_json_serializable(ob_data)

                    # Order Block BONUS (SMC) - 4H
                    alert.ob_bonus_4h = prog.get('ob_bonus_4h', False)
                    ob_data_4h = prog.get('ob_data_4h')
                    if ob_data_4h:
                        alert.ob_zone_high_4h = ob_data_4h.get('zone_high')
                        alert.ob_zone_low_4h = ob_data_4h.get('zone_low')
                        alert.ob_datetime_4h = ob_data_4h.get('datetime')
                        alert.ob_distance_pct_4h = ob_data_4h.get('distance_pct')
                        alert.ob_position_4h = ob_data_4h.get('position')
                        alert.ob_strength_4h = ob_data_4h.get('strength')
                        alert.ob_impulse_pct_4h = ob_data_4h.get('impulse_pct')
                        alert.ob_age_bars_4h = ob_data_4h.get('age_bars')
                        alert.ob_mitigated_4h = ob_data_4h.get('mitigated', False)
                        alert.ob_data_4h = convert_to_json_serializable(ob_data_4h)

                    # BTC Correlation BONUS - 1H
                    btc_corr_1h = prog.get('btc_corr_1h')
                    if btc_corr_1h:
                        alert.btc_corr_bonus_1h = btc_corr_1h.get('is_bonus', False)
                        alert.btc_price_1h = btc_corr_1h.get('price')
                        alert.btc_ema20_1h = btc_corr_1h.get('ema20')
                        alert.btc_ema50_1h = btc_corr_1h.get('ema50')
                        alert.btc_rsi_1h = btc_corr_1h.get('rsi')
                        alert.btc_trend_1h = btc_corr_1h.get('trend')

                    # BTC Correlation BONUS - 4H
                    btc_corr_4h = prog.get('btc_corr_4h')
                    if btc_corr_4h:
                        alert.btc_corr_bonus_4h = btc_corr_4h.get('is_bonus', False)
                        alert.btc_price_4h = btc_corr_4h.get('price')
                        alert.btc_ema20_4h = btc_corr_4h.get('ema20')
                        alert.btc_ema50_4h = btc_corr_4h.get('ema50')
                        alert.btc_rsi_4h = btc_corr_4h.get('rsi')
                        alert.btc_trend_4h = btc_corr_4h.get('trend')

                    # ETH Correlation BONUS - 1H
                    eth_corr_1h = prog.get('eth_corr_1h')
                    if eth_corr_1h:
                        alert.eth_corr_bonus_1h = eth_corr_1h.get('is_bonus', False)
                        alert.eth_price_1h = eth_corr_1h.get('price')
                        alert.eth_ema20_1h = eth_corr_1h.get('ema20')
                        alert.eth_ema50_1h = eth_corr_1h.get('ema50')
                        alert.eth_rsi_1h = eth_corr_1h.get('rsi')
                        alert.eth_trend_1h = eth_corr_1h.get('trend')

                    # ETH Correlation BONUS - 4H
                    eth_corr_4h = prog.get('eth_corr_4h')
                    if eth_corr_4h:
                        alert.eth_corr_bonus_4h = eth_corr_4h.get('is_bonus', False)
                        alert.eth_price_4h = eth_corr_4h.get('price')
                        alert.eth_ema20_4h = eth_corr_4h.get('ema20')
                        alert.eth_ema50_4h = eth_corr_4h.get('ema50')
                        alert.eth_rsi_4h = eth_corr_4h.get('rsi')
                        alert.eth_trend_4h = eth_corr_4h.get('trend')

                    # Fair Value Gap (FVG) BONUS - 1H
                    alert.fvg_bonus_1h = prog.get('fvg_bonus_1h', False)
                    fvg_data_1h = prog.get('fvg_data_1h')
                    if fvg_data_1h:
                        alert.fvg_zone_high_1h = fvg_data_1h.get('zone_high')
                        alert.fvg_zone_low_1h = fvg_data_1h.get('zone_low')
                        alert.fvg_datetime_1h = fvg_data_1h.get('datetime')
                        alert.fvg_distance_pct_1h = fvg_data_1h.get('distance_pct')
                        alert.fvg_position_1h = fvg_data_1h.get('position')
                        alert.fvg_filled_pct_1h = fvg_data_1h.get('filled_pct')
                        alert.fvg_size_pct_1h = fvg_data_1h.get('size_pct')
                        alert.fvg_age_bars_1h = fvg_data_1h.get('age_bars')
                        alert.fvg_data_1h = convert_to_json_serializable(fvg_data_1h)

                    # Fair Value Gap (FVG) BONUS - 4H
                    alert.fvg_bonus_4h = prog.get('fvg_bonus_4h', False)
                    fvg_data_4h = prog.get('fvg_data_4h')
                    if fvg_data_4h:
                        alert.fvg_zone_high_4h = fvg_data_4h.get('zone_high')
                        alert.fvg_zone_low_4h = fvg_data_4h.get('zone_low')
                        alert.fvg_datetime_4h = fvg_data_4h.get('datetime')
                        alert.fvg_distance_pct_4h = fvg_data_4h.get('distance_pct')
                        alert.fvg_position_4h = fvg_data_4h.get('position')
                        alert.fvg_filled_pct_4h = fvg_data_4h.get('filled_pct')
                        alert.fvg_size_pct_4h = fvg_data_4h.get('size_pct')
                        alert.fvg_age_bars_4h = fvg_data_4h.get('age_bars')
                        alert.fvg_data_4h = convert_to_json_serializable(fvg_data_4h)

                    # Volume Spike BONUS - 1H
                    alert.vol_spike_bonus_1h = prog.get('vol_spike_bonus_1h', False)
                    vol_spike_1h = prog.get('vol_spike_1h')
                    if vol_spike_1h:
                        alert.vol_current_1h = vol_spike_1h.get('current')
                        alert.vol_avg_1h = vol_spike_1h.get('average')
                        alert.vol_ratio_1h = vol_spike_1h.get('ratio')
                        alert.vol_spike_level_1h = vol_spike_1h.get('spike_level')

                    # Volume Spike BONUS - 4H
                    alert.vol_spike_bonus_4h = prog.get('vol_spike_bonus_4h', False)
                    vol_spike_4h = prog.get('vol_spike_4h')
                    if vol_spike_4h:
                        alert.vol_current_4h = vol_spike_4h.get('current')
                        alert.vol_avg_4h = vol_spike_4h.get('average')
                        alert.vol_ratio_4h = vol_spike_4h.get('ratio')
                        alert.vol_spike_level_4h = vol_spike_4h.get('spike_level')

                    # RSI Multi-TF Alignment BONUS
                    alert.rsi_mtf_bonus = prog.get('rsi_mtf_bonus', False)
                    rsi_mtf = prog.get('rsi_mtf')
                    if rsi_mtf:
                        alert.rsi_1h = rsi_mtf.get('rsi_1h')
                        alert.rsi_4h = rsi_mtf.get('rsi_4h')
                        alert.rsi_daily = rsi_mtf.get('rsi_daily')
                        alert.rsi_aligned_count = rsi_mtf.get('aligned_count')
                        alert.rsi_mtf_trend = rsi_mtf.get('mtf_trend')

                    # ADX Trend Strength BONUS - 1H
                    alert.adx_bonus_1h = prog.get('adx_bonus_1h', False)
                    adx_1h = prog.get('adx_1h')
                    if adx_1h:
                        alert.adx_value_1h = adx_1h.get('adx')
                        alert.adx_plus_di_1h = adx_1h.get('plus_di')
                        alert.adx_minus_di_1h = adx_1h.get('minus_di')
                        alert.adx_strength_1h = adx_1h.get('strength')

                    # ADX Trend Strength BONUS - 4H
                    alert.adx_bonus_4h = prog.get('adx_bonus_4h', False)
                    adx_4h = prog.get('adx_4h')
                    if adx_4h:
                        alert.adx_value_4h = adx_4h.get('adx')
                        alert.adx_plus_di_4h = adx_4h.get('plus_di')
                        alert.adx_minus_di_4h = adx_4h.get('minus_di')
                        alert.adx_strength_4h = adx_4h.get('strength')

                    # MACD Momentum BONUS - 1H
                    alert.macd_bonus_1h = prog.get('macd_bonus_1h', False)
                    macd_1h = prog.get('macd_1h')
                    if macd_1h:
                        alert.macd_line_1h = macd_1h.get('macd_line')
                        alert.macd_signal_1h = macd_1h.get('signal_line')
                        alert.macd_histogram_1h = macd_1h.get('histogram')
                        alert.macd_hist_growing_1h = macd_1h.get('hist_growing')
                        alert.macd_trend_1h = macd_1h.get('trend')

                    # MACD Momentum BONUS - 4H
                    alert.macd_bonus_4h = prog.get('macd_bonus_4h', False)
                    macd_4h = prog.get('macd_4h')
                    if macd_4h:
                        alert.macd_line_4h = macd_4h.get('macd_line')
                        alert.macd_signal_4h = macd_4h.get('signal_line')
                        alert.macd_histogram_4h = macd_4h.get('histogram')
                        alert.macd_hist_growing_4h = macd_4h.get('hist_growing')
                        alert.macd_trend_4h = macd_4h.get('trend')

                    # Bollinger Squeeze BONUS - 1H
                    alert.bb_squeeze_bonus_1h = prog.get('bb_squeeze_bonus_1h', False)
                    bb_1h = prog.get('bb_1h')
                    if bb_1h:
                        alert.bb_upper_1h = bb_1h.get('upper')
                        alert.bb_middle_1h = bb_1h.get('middle')
                        alert.bb_lower_1h = bb_1h.get('lower')
                        alert.bb_width_pct_1h = bb_1h.get('width_pct')
                        alert.bb_squeeze_1h = bb_1h.get('squeeze')
                        alert.bb_breakout_1h = bb_1h.get('breakout')

                    # Bollinger Squeeze BONUS - 4H
                    alert.bb_squeeze_bonus_4h = prog.get('bb_squeeze_bonus_4h', False)
                    bb_4h = prog.get('bb_4h')
                    if bb_4h:
                        alert.bb_upper_4h = bb_4h.get('upper')
                        alert.bb_middle_4h = bb_4h.get('middle')
                        alert.bb_lower_4h = bb_4h.get('lower')
                        alert.bb_width_pct_4h = bb_4h.get('width_pct')
                        alert.bb_squeeze_4h = bb_4h.get('squeeze')
                        alert.bb_breakout_4h = bb_4h.get('breakout')

                    # Stochastic RSI BONUS - 1H
                    alert.stoch_rsi_bonus_1h = prog.get('stoch_rsi_bonus_1h', False)
                    stoch_rsi_1h = prog.get('stoch_rsi_1h')
                    if stoch_rsi_1h:
                        alert.stoch_rsi_k_1h = stoch_rsi_1h.get('k')
                        alert.stoch_rsi_d_1h = stoch_rsi_1h.get('d')
                        alert.stoch_rsi_zone_1h = stoch_rsi_1h.get('zone')
                        alert.stoch_rsi_cross_1h = stoch_rsi_1h.get('cross')

                    # Stochastic RSI BONUS - 4H
                    alert.stoch_rsi_bonus_4h = prog.get('stoch_rsi_bonus_4h', False)
                    stoch_rsi_4h = prog.get('stoch_rsi_4h')
                    if stoch_rsi_4h:
                        alert.stoch_rsi_k_4h = stoch_rsi_4h.get('k')
                        alert.stoch_rsi_d_4h = stoch_rsi_4h.get('d')
                        alert.stoch_rsi_zone_4h = stoch_rsi_4h.get('zone')
                        alert.stoch_rsi_cross_4h = stoch_rsi_4h.get('cross')

                    # EMA Stack BONUS - 1H
                    alert.ema_stack_bonus_1h = prog.get('ema_stack_bonus_1h', False)
                    ema_stack_1h = prog.get('ema_stack_1h')
                    if ema_stack_1h:
                        alert.ema8_1h = ema_stack_1h.get('ema8')
                        alert.ema21_1h = ema_stack_1h.get('ema21')
                        alert.ema50_1h = ema_stack_1h.get('ema50')
                        alert.ema100_1h_stack = ema_stack_1h.get('ema100')
                        alert.ema_stack_count_1h = ema_stack_1h.get('stack_count')
                        alert.ema_stack_trend_1h = ema_stack_1h.get('trend')

                    # EMA Stack BONUS - 4H
                    alert.ema_stack_bonus_4h = prog.get('ema_stack_bonus_4h', False)
                    ema_stack_4h = prog.get('ema_stack_4h')
                    if ema_stack_4h:
                        alert.ema8_4h = ema_stack_4h.get('ema8')
                        alert.ema21_4h = ema_stack_4h.get('ema21')
                        alert.ema50_4h = ema_stack_4h.get('ema50')
                        alert.ema100_4h_stack = ema_stack_4h.get('ema100')
                        alert.ema_stack_count_4h = ema_stack_4h.get('stack_count')
                        alert.ema_stack_trend_4h = ema_stack_4h.get('trend')

                # ═══════════════════════════════════════════════════════════════
                # GB POWER SCORE CALCULATION
                # ═══════════════════════════════════════════════════════════════
                try:
                    # Build alert data dict for power score calculation
                    alert_data_for_power = {
                        # Volume
                        'vol_ratio_1h': alert.vol_ratio_1h,
                        'vol_ratio_4h': alert.vol_ratio_4h,
                        'vol_spike_bonus_1h': alert.vol_spike_bonus_1h,
                        'vol_spike_bonus_4h': alert.vol_spike_bonus_4h,
                        # ADX
                        'adx_value_1h': alert.adx_value_1h,
                        'adx_value_4h': alert.adx_value_4h,
                        'adx_plus_di_4h': alert.adx_plus_di_4h,
                        'adx_minus_di_4h': alert.adx_minus_di_4h,
                        'adx_bonus_1h': alert.adx_bonus_1h,
                        'adx_bonus_4h': alert.adx_bonus_4h,
                        # EMA Stack
                        'ema_stack_count_1h': alert.ema_stack_count_1h,
                        'ema_stack_count_4h': alert.ema_stack_count_4h,
                        'ema_stack_trend_4h': alert.ema_stack_trend_4h,
                        'ema_stack_bonus_4h': alert.ema_stack_bonus_4h,
                        # MACD
                        'macd_histogram_1h': alert.macd_histogram_1h,
                        'macd_histogram_4h': alert.macd_histogram_4h,
                        'macd_hist_growing_1h': alert.macd_hist_growing_1h,
                        'macd_hist_growing_4h': alert.macd_hist_growing_4h,
                        'macd_bonus_1h': alert.macd_bonus_1h,
                        'macd_bonus_4h': alert.macd_bonus_4h,
                        # Fibonacci
                        'fib_bonus': alert.fib_bonus,
                        'fib_levels': alert.fib_levels,
                        # RSI Multi-TF
                        'rsi_1h': alert.rsi_1h,
                        'rsi_4h': alert.rsi_4h,
                        'rsi_daily': alert.rsi_daily,
                        'rsi_aligned_count': alert.rsi_aligned_count,
                        'rsi_mtf_bonus': alert.rsi_mtf_bonus,
                        # BTC Correlation
                        'btc_trend_1h': alert.btc_trend_1h,
                        'btc_trend_4h': alert.btc_trend_4h,
                        'btc_corr_bonus_1h': alert.btc_corr_bonus_1h,
                        'btc_corr_bonus_4h': alert.btc_corr_bonus_4h,
                        # Other bonuses
                        'ob_bonus_4h': alert.ob_bonus_4h,
                        'fvg_bonus_4h': alert.fvg_bonus_4h,
                    }

                    # Calculate power score (V3 data will be added later if applicable)
                    power_scores = calc_gb_power_score(alert_data_for_power)

                    # Store power score in alert
                    alert.gb_power_score = power_scores.get('gb_power_score')
                    alert.gb_power_grade = power_scores.get('gb_power_grade')
                    alert.gb_volume_score = power_scores.get('gb_volume_score')
                    alert.gb_adx_score = power_scores.get('gb_adx_score')
                    alert.gb_ema_alignment_score = power_scores.get('gb_ema_alignment_score')
                    alert.gb_macd_momentum_score = power_scores.get('gb_macd_momentum_score')
                    alert.gb_fib_position_score = power_scores.get('gb_fib_position_score')
                    alert.gb_retest_quality_score = power_scores.get('gb_retest_quality_score')
                    alert.gb_dmi_spread_score = power_scores.get('gb_dmi_spread_score')
                    alert.gb_rsi_strength_score = power_scores.get('gb_rsi_strength_score')
                    alert.gb_btc_correlation_score = power_scores.get('gb_btc_correlation_score')
                    alert.gb_confluence_score = power_scores.get('gb_confluence_score')
                    alert.gb_dmi_spread = power_scores.get('gb_dmi_spread')

                except Exception as e:
                    # Power score calculation failed, continue without it
                    if progress_callback:
                        progress_callback(f"    Warning: Power score calculation failed: {e}")

                # ═══════════════════════════════════════════════════════════════
                # VOLUME PROFILE ANALYSIS (V1 - for entries before V3/V4 processing)
                # Runs only for V1 with valid entry, V3/V4 calculates VP later at retest
                # ═══════════════════════════════════════════════════════════════
                if strategy_version == 'v1' and alert.has_entry and self.config.get('VP_ENABLED', True):
                    try:
                        # Initialize VP analyzer
                        vp_analyzer = VolumeProfileAnalyzer(self.config)

                        # Calculate VP for 1H and 4H data
                        vp_1h = vp_analyzer.calculate(
                            df_1h,
                            lookback=self.config.get('VP_LOOKBACK_1H', 100)
                        )
                        vp_4h = vp_analyzer.calculate(
                            df_4h,
                            lookback=self.config.get('VP_LOOKBACK_4H', 50)
                        )

                        # Get entry/SL/TP prices for V1
                        vp_entry_price = alert.entry_price
                        vp_sl_price = vp_entry_price * (1 - self.config.get('SL_PCT', 5.0) / 100)
                        vp_tp1_price = vp_entry_price * (1 + self.config.get('TP1_PCT', 15.0) / 100)

                        # Get OB zone for confluence check
                        vp_ob_zone = None
                        if alert.ob_zone_high and alert.ob_zone_low:
                            vp_ob_zone = {
                                'high': alert.ob_zone_high,
                                'low': alert.ob_zone_low
                            }

                        # Calculate VP score
                        vp_result = vp_analyzer.calculate_vp_score(
                            entry_price=vp_entry_price,
                            sl_price=vp_sl_price,
                            tp1_price=vp_tp1_price,
                            vp_data=vp_1h,
                            vp_4h_data=vp_4h,
                            ob_zone=vp_ob_zone
                        )

                        # Store VP results in alert
                        alert.vp_bonus = vp_result.get('vp_score', 0) >= self.config.get('VP_MIN_SCORE_V1', 20)
                        alert.vp_score = vp_result.get('vp_score', 0)
                        alert.vp_grade = vp_result.get('vp_grade', 'N/A')

                        # 1H levels
                        alert.vp_poc_1h = vp_1h.get('poc')
                        alert.vp_vah_1h = vp_1h.get('vah')
                        alert.vp_val_1h = vp_1h.get('val')
                        alert.vp_hvn_levels_1h = vp_1h.get('hvn_levels', [])[:5]
                        alert.vp_lvn_levels_1h = vp_1h.get('lvn_levels', [])[:5]
                        alert.vp_total_volume_1h = vp_1h.get('total_volume')

                        # 4H levels
                        alert.vp_poc_4h = vp_4h.get('poc')
                        alert.vp_vah_4h = vp_4h.get('vah')
                        alert.vp_val_4h = vp_4h.get('val')
                        alert.vp_hvn_levels_4h = vp_4h.get('hvn_levels', [])[:5]
                        alert.vp_lvn_levels_4h = vp_4h.get('lvn_levels', [])[:5]
                        alert.vp_total_volume_4h = vp_4h.get('total_volume')

                        # Entry position analysis
                        alert.vp_entry_position_1h = vp_result.get('vp_position', 'UNKNOWN')
                        alert.vp_entry_position_4h = vp_analyzer.get_position_in_va(vp_entry_price, vp_4h)
                        if vp_1h.get('poc'):
                            alert.vp_entry_vs_poc_pct_1h = abs(vp_entry_price - vp_1h['poc']) / vp_entry_price * 100
                        if vp_4h.get('poc'):
                            alert.vp_entry_vs_poc_pct_4h = abs(vp_entry_price - vp_4h['poc']) / vp_entry_price * 100

                        # SL analysis
                        nearest_hvn_below_sl = vp_analyzer.get_nearest_hvn(vp_sl_price, vp_1h, 'above')
                        if nearest_hvn_below_sl and nearest_hvn_below_sl < vp_entry_price:
                            alert.vp_sl_near_hvn = True
                            alert.vp_sl_hvn_level = nearest_hvn_below_sl
                            alert.vp_sl_hvn_distance_pct = abs(vp_sl_price - nearest_hvn_below_sl) / vp_sl_price * 100
                        alert.vp_sl_optimized = vp_result.get('vp_sl_optimized')

                        # Naked POC detection
                        if vp_1h.get('poc') and vp_1h['poc'] > vp_entry_price * 1.02:
                            alert.vp_naked_poc_1h = True
                            alert.vp_naked_poc_level_1h = vp_1h['poc']
                        if vp_4h.get('poc') and vp_4h['poc'] > vp_entry_price * 1.02:
                            alert.vp_naked_poc_4h = True
                            alert.vp_naked_poc_level_4h = vp_4h['poc']

                        # Summary
                        alert.vp_label = self._get_vp_label(vp_result, vp_1h, vp_entry_price)
                        alert.vp_recommendation = '; '.join(vp_result.get('vp_recommendations', [])[:2])
                        alert.vp_details = convert_to_json_serializable({
                            'details': vp_result.get('vp_details', []),
                            'tp_suggestions': vp_result.get('vp_tp_suggestions', [])
                        })

                        # ═══════════════════════════════════════════════════════════════
                        # VP RETEST DETECTION (V1)
                        # Detect if VAL/POC/VAH were retested AFTER MEGA BUY alert
                        # For BUY direction: price comes FROM ABOVE, touches support, bounces UP
                        # ═══════════════════════════════════════════════════════════════
                        try:
                            signal_dt_v1 = mb['datetime']
                            entry_dt_v1 = alert.entry_datetime

                            if signal_dt_v1 and entry_dt_v1:
                                # Filter data between signal and entry
                                df_1h_retest = df_1h[(df_1h['datetime'] >= signal_dt_v1) & (df_1h['datetime'] <= entry_dt_v1)].copy()

                                if len(df_1h_retest) > 0:
                                    # Get OB zones for confluence check
                                    fc_ob_zone_1h_v1 = None
                                    if alert.fc_ob_1h_found and alert.fc_ob_1h_zone_high and alert.fc_ob_1h_zone_low:
                                        fc_ob_zone_1h_v1 = {
                                            'high': alert.fc_ob_1h_zone_high,
                                            'low': alert.fc_ob_1h_zone_low
                                        }
                                    fc_ob_zone_4h_v1 = None
                                    if alert.fc_ob_4h_found and alert.fc_ob_4h_zone_high and alert.fc_ob_4h_zone_low:
                                        fc_ob_zone_4h_v1 = {
                                            'high': alert.fc_ob_4h_zone_high,
                                            'low': alert.fc_ob_4h_zone_low
                                        }

                                    # Detect VP retests
                                    vp_retest_info_v1 = vp_analyzer.detect_vp_retests(
                                        df=df_1h_retest,
                                        vp_data=vp_1h,
                                        signal_dt=signal_dt_v1,
                                        entry_dt=entry_dt_v1,
                                        ob_zone_1h=fc_ob_zone_1h_v1,
                                        ob_zone_4h=fc_ob_zone_4h_v1,
                                        tolerance_pct=1.5
                                    )

                                    # Store VP retest results
                                    if vp_retest_info_v1:
                                        alert.vp_val_retested = vp_retest_info_v1.get('val_retested', False)
                                        alert.vp_val_retest_rejected = vp_retest_info_v1.get('val_retest_rejected', False)
                                        alert.vp_val_retest_dt = vp_retest_info_v1.get('val_retest_dt')
                                        alert.vp_poc_retested = vp_retest_info_v1.get('poc_retested', False)
                                        alert.vp_poc_retest_rejected = vp_retest_info_v1.get('poc_retest_rejected', False)
                                        alert.vp_poc_retest_dt = vp_retest_info_v1.get('poc_retest_dt')
                                        alert.vp_vah_retested = vp_retest_info_v1.get('vah_retested', False)
                                        alert.vp_hvn_retested = vp_retest_info_v1.get('hvn_retested', False)
                                        alert.vp_hvn_retest_level = vp_retest_info_v1.get('hvn_retest_level')
                                        alert.vp_ob_confluence = vp_retest_info_v1.get('ob_confluence', False)
                                        alert.vp_ob_confluence_tf = vp_retest_info_v1.get('ob_confluence_tf')
                                        alert.vp_pullback_completed = vp_retest_info_v1.get('pullback_completed', False)
                                        alert.vp_pullback_level = vp_retest_info_v1.get('pullback_level')
                                        alert.vp_pullback_quality = vp_retest_info_v1.get('pullback_quality')
                        except Exception as vp_retest_v1_err:
                            # VP retest detection failed, continue without it
                            pass

                    except Exception as vp_v1_err:
                        # VP calculation failed, continue without it
                        pass

                db.add(alert)
                db.commit()
                db.refresh(alert)

                # ═══════════════════════════════════════════════════════════════
                # V2 OPTIMIZATION FILTERS (if enabled)
                # ═══════════════════════════════════════════════════════════════
                v2_rejected = False
                v2_rejection_reason = None
                trade_score = None

                # ═══════════════════════════════════════════════════════════════
                # V3 GOLDEN BOX RETEST STRATEGY
                # ═══════════════════════════════════════════════════════════════
                v3_entry = None
                v3_rejected = False
                v3_rejection_reason = None
                v3_quality_score = None

                if strategy_version in ['v3', 'v4', 'v5', 'v6']:
                    # V3/V4/V5 GOLDEN BOX RETEST + 5/5 PROGRESSIVE CONDITIONS REQUIRED
                    # V4 uses V3 entry detection + additional ML-based filters
                    # V5 uses V4 + VP trajectory filter
                    # First find retest, then validate 5/5 conditions at retest time

                    # Golden Box = PRIMARY TF's candle High/Low for COMBO alerts
                    # This ensures all alerts in a COMBO use the same box values
                    box_high = mb.get('combo_primary_box_high', mb['high'])
                    box_low = mb.get('combo_primary_box_low', mb['low'])

                    # Find signal index in 1H data
                    mb_1h_idx = mb.get('mb_1h_idx')
                    if mb_1h_idx is None:
                        # Find it manually
                        for idx_find, row_find in df_1h.iterrows():
                            if row_find['datetime'] <= mb['datetime']:
                                mb_1h_idx = idx_find

                    if mb_1h_idx is not None:
                        # Check prerequisites (STC, 15m alone, PP_buy)
                        is_15m_alone = mb.get('is_15m_alone', False)
                        pp_buy = mb['conditions'].get('PP_buy', True)

                        v3_prerequisites_met = (
                            mb['stc_oversold_any'] and
                            not (is_15m_alone and self.config['REJECT_15M_ALONE']) and
                            (not self.config.get('REQUIRE_PP_BUY', False) or pp_buy)
                        )

                        if v3_prerequisites_met:
                            # Look for V3 retest entry
                            v3_entry = find_v3_golden_box_retest_entry(
                                df_1h, mb_1h_idx, box_high, box_low, self.config
                            )

                            if v3_entry:
                                # Get retest index for progressive conditions check
                                retest_idx = v3_entry['idx']
                                retest_price = v3_entry['price']
                                retest_low = v3_entry.get('retest_low', v3_entry['price'])
                                retest_dt = v3_entry['dt']

                                # Compare retest datetime with TL break datetime
                                tl_break_info = mb.get('tl_break')
                                if tl_break_info and tl_break_info.get('dt'):
                                    tl_break_dt = tl_break_info['dt']
                                    hours_diff = (retest_dt - tl_break_dt).total_seconds() / 3600
                                    if hours_diff < 0:
                                        v3_retest_vs_tl = 'BEFORE_TL'  # Retest happened BEFORE TL break
                                    else:
                                        v3_retest_vs_tl = 'AFTER_TL'   # Retest happened AFTER TL break
                                else:
                                    tl_break_dt = None
                                    hours_diff = None
                                    v3_retest_vs_tl = 'NO_TL_BREAK'

                                # ═══════════════════════════════════════════════════════════════════
                                # V3 REQUIRE TL BREAK: Reject if no TL break
                                # This ensures all V3/V4/V5 entries have a confirmed TL break
                                # ═══════════════════════════════════════════════════════════════════
                                if self.config.get('V3_REQUIRE_TL_BREAK', True) and v3_retest_vs_tl == 'NO_TL_BREAK':
                                    alert.v3_entry_found = False
                                    alert.v3_rejected = True
                                    alert.v3_rejection_reason = 'NO_TL_BREAK'
                                    alert.v3_retest_vs_tl_break = 'NO_TL_BREAK'
                                    alert.status = 'V3_NO_TL_BREAK'
                                    db.commit()

                                    if progress_callback:
                                        progress_callback(f"    V3 REJECTED: No TL break (TL break is REQUIRED)")
                                    continue  # Skip this V3 entry - no TL break

                                # Find corresponding indices in 30m and 4H
                                retest_idx_30m = None
                                retest_idx_4h = None

                                for idx_30m, row_30m in data["30m"].iterrows():
                                    if row_30m['datetime'] >= retest_dt:
                                        retest_idx_30m = idx_30m
                                        break

                                for idx_4h, row_4h in df_4h.iterrows():
                                    if row_4h['datetime'] >= retest_dt:
                                        retest_idx_4h = idx_4h
                                        break

                                # Calculate 5 progressive conditions at retest time
                                ema100_1h_val = progressive_indicators['1h']['ema100'][retest_idx] if retest_idx < len(progressive_indicators['1h']['ema100']) else 0
                                cloud_1h_val = progressive_indicators['1h']['cloud_top'][retest_idx] if retest_idx < len(progressive_indicators['1h']['cloud_top']) else 0
                                cloud_30m_val = progressive_indicators['30m']['cloud_top'][retest_idx_30m] if retest_idx_30m and retest_idx_30m < len(progressive_indicators['30m']['cloud_top']) else 0
                                ema20_4h_val = progressive_indicators['4h']['ema20'][retest_idx_4h] if retest_idx_4h and retest_idx_4h < len(progressive_indicators['4h']['ema20']) else 0

                                # Evaluate conditions
                                cond_ema100 = retest_price > ema100_1h_val if ema100_1h_val > 0 else False
                                cond_ema20_4h = retest_price > ema20_4h_val if ema20_4h_val > 0 else False
                                cond_cloud_1h = retest_price > cloud_1h_val if cloud_1h_val > 0 else False
                                cond_cloud_30m = retest_price > cloud_30m_val if cloud_30m_val > 0 else False

                                # CHoCH/BOS check at retest time
                                swing_highs_v3 = find_swing_highs(high_1h, left=self.config['SWING_HIGH_LEFT'], right=self.config['SWING_HIGH_RIGHT'])
                                choch_bos_breaks = detect_choch_bos(df_1h, close_1h, high_1h, swing_highs_v3, mb_1h_idx, retest_idx - mb_1h_idx + 10)
                                choch_bos_valid = any(brk['idx'] <= retest_idx for brk in choch_bos_breaks)

                                # Count valid conditions (0-5)
                                v3_prog_count = sum([cond_ema100, cond_ema20_4h, cond_cloud_1h, cond_cloud_30m, choch_bos_valid])

                                # Store progressive conditions in alert
                                alert.v3_prog_valid_ema100_1h = cond_ema100
                                alert.v3_prog_valid_ema20_4h = cond_ema20_4h
                                alert.v3_prog_valid_cloud_1h = cond_cloud_1h
                                alert.v3_prog_valid_cloud_30m = cond_cloud_30m
                                alert.v3_prog_choch_bos_valid = choch_bos_valid
                                alert.v3_prog_count = v3_prog_count
                                alert.v3_prog_ema100_1h_val = ema100_1h_val
                                alert.v3_prog_ema20_4h_val = ema20_4h_val
                                alert.v3_prog_cloud_1h_val = cloud_1h_val
                                alert.v3_prog_cloud_30m_val = cloud_30m_val
                                alert.v3_retest_price = retest_low
                                alert.v3_retest_datetime = retest_dt

                                # ═══════════════════════════════════════════════════════════════════
                                # FOREIGN CANDLE ORDER BLOCK ANALYSIS
                                # Detects "red candle in green sequence" patterns as retest zones
                                # Like the CVXUSDT chart example - price pullback to OB zone
                                # ═══════════════════════════════════════════════════════════════════
                                try:
                                    fc_ob_result = analyze_foreign_candle_ob(
                                        df_1h=df_1h,
                                        df_4h=df_4h,
                                        alert_idx_1h=mb_1h_idx,
                                        tl_break_idx_1h=tl_break_idx if 'tl_break_idx' in dir() else None,
                                        entry_idx_1h=retest_idx,
                                        entry_price=retest_price,
                                        retest_low=retest_low,
                                        lookback_1h=150,
                                        lookback_4h=80
                                    )

                                    # Store FC OB 1H results
                                    alert.fc_ob_1h_found = fc_ob_result.get('fc_ob_1h_found', False)
                                    alert.fc_ob_1h_count = fc_ob_result.get('fc_ob_1h_count')
                                    alert.fc_ob_1h_type = fc_ob_result.get('fc_ob_1h_type')
                                    alert.fc_ob_1h_zone_high = fc_ob_result.get('fc_ob_1h_zone_high')
                                    alert.fc_ob_1h_zone_low = fc_ob_result.get('fc_ob_1h_zone_low')
                                    alert.fc_ob_1h_strength = fc_ob_result.get('fc_ob_1h_strength')
                                    alert.fc_ob_1h_retest = fc_ob_result.get('fc_ob_1h_retest', False)
                                    alert.fc_ob_1h_distance_pct = fc_ob_result.get('fc_ob_1h_distance_pct')
                                    alert.fc_ob_1h_datetime = fc_ob_result.get('fc_ob_1h_datetime')
                                    alert.fc_ob_1h_in_zone = fc_ob_result.get('fc_ob_1h_in_zone', 0)
                                    alert.fc_ob_1h_retested = fc_ob_result.get('fc_ob_1h_retested', 0)

                                    # Store FC OB 4H results
                                    alert.fc_ob_4h_found = fc_ob_result.get('fc_ob_4h_found', False)
                                    alert.fc_ob_4h_count = fc_ob_result.get('fc_ob_4h_count')
                                    alert.fc_ob_4h_type = fc_ob_result.get('fc_ob_4h_type')
                                    alert.fc_ob_4h_zone_high = fc_ob_result.get('fc_ob_4h_zone_high')
                                    alert.fc_ob_4h_zone_low = fc_ob_result.get('fc_ob_4h_zone_low')
                                    alert.fc_ob_4h_strength = fc_ob_result.get('fc_ob_4h_strength')
                                    alert.fc_ob_4h_retest = fc_ob_result.get('fc_ob_4h_retest', False)
                                    alert.fc_ob_4h_distance_pct = fc_ob_result.get('fc_ob_4h_distance_pct')
                                    alert.fc_ob_4h_datetime = fc_ob_result.get('fc_ob_4h_datetime')
                                    alert.fc_ob_4h_in_zone = fc_ob_result.get('fc_ob_4h_in_zone', 0)
                                    alert.fc_ob_4h_retested = fc_ob_result.get('fc_ob_4h_retested', 0)

                                    # Store combined FC OB results
                                    alert.fc_ob_bonus = fc_ob_result.get('fc_ob_bonus', False)
                                    alert.fc_ob_score = fc_ob_result.get('fc_ob_score', 0)
                                    alert.fc_ob_label = fc_ob_result.get('fc_ob_label', 'NO_OB')

                                    if fc_ob_result.get('fc_ob_bonus'):
                                        if progress_callback:
                                            progress_callback(f"    Foreign Candle OB: {fc_ob_result.get('fc_ob_label')} (Score: {fc_ob_result.get('fc_ob_score')}/100)")
                                except Exception as fc_ob_err:
                                    # Foreign Candle OB analysis failed, continue
                                    pass

                                # V3 REQUIRES 5/5 progressive conditions
                                if v3_prog_count < 5:
                                    v3_rejected = True
                                    v3_rejection_reason = f'PROG_{v3_prog_count}_5'
                                    alert.v3_entry_found = True  # Retest found but rejected due to conditions
                                    alert.v3_entry_datetime = retest_dt
                                    alert.v3_entry_price = retest_price
                                    alert.v3_sl_price = v3_entry['sl_price']
                                    alert.v3_box_high = box_high
                                    alert.v3_box_low = box_low
                                    alert.v3_box_range_pct = v3_entry['box_range_pct']
                                    alert.v3_hours_to_entry = v3_entry['hours_to_entry']
                                    alert.v3_sl_distance_pct = v3_entry['sl_distance_pct']
                                    alert.v3_breakout_dt = v3_entry['breakout_dt']
                                    alert.v3_breakout_high = v3_entry['breakout_high']
                                    alert.v3_distance_before_retest = v3_entry['distance_before_retest_pct']
                                    alert.v3_rejected = True
                                    alert.v3_rejection_reason = v3_rejection_reason
                                    alert.status = f'V3_PROG_{v3_prog_count}_5'
                                    # Retest vs TL Break comparison
                                    alert.v3_retest_vs_tl_break = v3_retest_vs_tl
                                    alert.v3_tl_break_datetime = tl_break_dt
                                    alert.v3_hours_retest_vs_tl = hours_diff

                                    # Recalculate GB Power Score with V3 retest data
                                    try:
                                        v3_data_for_power = {
                                            'box_high': box_high,
                                            'retest_price': retest_low
                                        }
                                        power_scores_v3 = calc_gb_power_score(alert_data_for_power, v3_data_for_power)
                                        alert.gb_power_score = power_scores_v3.get('gb_power_score')
                                        alert.gb_power_grade = power_scores_v3.get('gb_power_grade')
                                        alert.gb_retest_quality_score = power_scores_v3.get('gb_retest_quality_score')
                                    except:
                                        pass

                                    # Calculate V3 Risk Score
                                    try:
                                        v3_risk_data = {
                                            'hours_retest_vs_tl': hours_diff,
                                            'distance_before_retest': v3_entry['distance_before_retest_pct'],
                                            'box_range_pct': v3_entry['box_range_pct'],
                                            'sl_distance_pct': v3_entry['sl_distance_pct'],
                                            'hours_to_entry': v3_entry['hours_to_entry']
                                        }
                                        risk_result = calc_v3_risk_score(v3_risk_data)
                                        alert.v3_risk_level = risk_result['v3_risk_level']
                                        alert.v3_risk_score = risk_result['v3_risk_score']
                                        alert.v3_risk_reasons = risk_result['v3_risk_reasons']
                                    except:
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # VP RETEST DETECTION (V3 REJECTED)
                                    # Calculate VP retests even for rejected V3 entries for analysis
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        if self.config.get('VP_ENABLED', True):
                                            vp_analyzer_rej = VolumeProfileAnalyzer(self.config)
                                            signal_dt_rej = mb['datetime']
                                            entry_dt_rej = retest_dt

                                            # Filter 1H data for VP calculation
                                            df_1h_vp_rej = df_1h[(df_1h['datetime'] >= signal_dt_rej) & (df_1h['datetime'] <= entry_dt_rej)].copy()

                                            if len(df_1h_vp_rej) < 10:
                                                signal_idx_rej = None
                                                for idx_r, row_r in df_1h.iterrows():
                                                    if row_r['datetime'] >= signal_dt_rej:
                                                        signal_idx_rej = idx_r
                                                        break
                                                if signal_idx_rej is not None:
                                                    start_idx_rej = max(0, signal_idx_rej - 20)
                                                    end_idx_rej = retest_idx + 1 if retest_idx < len(df_1h) else len(df_1h)
                                                    df_1h_vp_rej = df_1h.iloc[start_idx_rej:end_idx_rej].copy()

                                            # Calculate VP
                                            vp_1h_rej = vp_analyzer_rej.calculate(df_1h_vp_rej, lookback=len(df_1h_vp_rej))
                                            vp_4h_rej = vp_analyzer_rej.calculate(df_4h, lookback=self.config.get('VP_LOOKBACK_4H', 50))

                                            # Store VP levels
                                            alert.vp_poc_1h = vp_1h_rej.get('poc')
                                            alert.vp_vah_1h = vp_1h_rej.get('vah')
                                            alert.vp_val_1h = vp_1h_rej.get('val')
                                            alert.vp_poc_4h = vp_4h_rej.get('poc')
                                            alert.vp_vah_4h = vp_4h_rej.get('vah')
                                            alert.vp_val_4h = vp_4h_rej.get('val')

                                            # Detect VP retests
                                            vp_retest_rej = vp_analyzer_rej.detect_vp_retests(
                                                df=df_1h_vp_rej,
                                                vp_data=vp_1h_rej,
                                                signal_dt=signal_dt_rej,
                                                entry_dt=entry_dt_rej,
                                                tolerance_pct=1.5
                                            )

                                            if vp_retest_rej:
                                                alert.vp_val_retested = vp_retest_rej.get('val_retested', False)
                                                alert.vp_val_retest_rejected = vp_retest_rej.get('val_retest_rejected', False)
                                                alert.vp_val_retest_dt = vp_retest_rej.get('val_retest_dt')
                                                alert.vp_poc_retested = vp_retest_rej.get('poc_retested', False)
                                                alert.vp_poc_retest_rejected = vp_retest_rej.get('poc_retest_rejected', False)
                                                alert.vp_poc_retest_dt = vp_retest_rej.get('poc_retest_dt')
                                                alert.vp_vah_retested = vp_retest_rej.get('vah_retested', False)
                                                alert.vp_hvn_retested = vp_retest_rej.get('hvn_retested', False)
                                                alert.vp_pullback_completed = vp_retest_rej.get('pullback_completed', False)
                                                alert.vp_pullback_level = vp_retest_rej.get('pullback_level')
                                                alert.vp_pullback_quality = vp_retest_rej.get('pullback_quality')
                                    except Exception as vp_rej_err:
                                        pass

                                    if progress_callback:
                                        progress_callback(f"    V3 REJECTED: Conditions {v3_prog_count}/5 (need 5/5)")
                                else:
                                    # 5/5 conditions met - validate V3 entry quality
                                    alert_data_for_v3 = {
                                        'rsi_mtf_bonus': alert.rsi_mtf_bonus if hasattr(alert, 'rsi_mtf_bonus') else False,
                                        'adx_strength_1h': alert.adx_strength_1h if hasattr(alert, 'adx_strength_1h') else None,
                                        'vol_spike_bonus_4h': alert.vol_spike_bonus_4h if hasattr(alert, 'vol_spike_bonus_4h') else False,
                                    }
                                    is_valid_v3, v3_val_reason, v3_quality_score = validate_v3_entry(v3_entry, alert_data_for_v3, self.config)

                                    # Store V3 data in alert
                                    alert.v3_entry_found = True
                                    alert.v3_entry_datetime = retest_dt
                                    alert.v3_entry_price = retest_price
                                    alert.v3_sl_price = v3_entry['sl_price']
                                    alert.v3_box_high = box_high
                                    alert.v3_box_low = box_low
                                    alert.v3_box_range_pct = v3_entry['box_range_pct']
                                    alert.v3_hours_to_entry = v3_entry['hours_to_entry']
                                    alert.v3_sl_distance_pct = v3_entry['sl_distance_pct']
                                    alert.v3_quality_score = v3_quality_score
                                    alert.v3_breakout_dt = v3_entry['breakout_dt']
                                    alert.v3_breakout_high = v3_entry['breakout_high']
                                    alert.v3_distance_before_retest = v3_entry['distance_before_retest_pct']
                                    alert.status = 'VALID_V3'
                                    # Retest vs TL Break comparison
                                    alert.v3_retest_vs_tl_break = v3_retest_vs_tl
                                    alert.v3_tl_break_datetime = tl_break_dt
                                    alert.v3_hours_retest_vs_tl = hours_diff

                                    # Recalculate GB Power Score with V3 retest data
                                    try:
                                        v3_data_for_power = {
                                            'box_high': box_high,
                                            'retest_price': retest_low
                                        }
                                        power_scores_v3 = calc_gb_power_score(alert_data_for_power, v3_data_for_power)
                                        alert.gb_power_score = power_scores_v3.get('gb_power_score')
                                        alert.gb_power_grade = power_scores_v3.get('gb_power_grade')
                                        alert.gb_retest_quality_score = power_scores_v3.get('gb_retest_quality_score')
                                    except:
                                        pass

                                    # Calculate V3 Risk Score
                                    try:
                                        v3_risk_data = {
                                            'hours_retest_vs_tl': hours_diff,
                                            'distance_before_retest': v3_entry['distance_before_retest_pct'],
                                            'box_range_pct': v3_entry['box_range_pct'],
                                            'sl_distance_pct': v3_entry['sl_distance_pct'],
                                            'hours_to_entry': v3_entry['hours_to_entry']
                                        }
                                        risk_result = calc_v3_risk_score(v3_risk_data)
                                        alert.v3_risk_level = risk_result['v3_risk_level']
                                        alert.v3_risk_score = risk_result['v3_risk_score']
                                        alert.v3_risk_reasons = risk_result['v3_risk_reasons']
                                    except:
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # CVD (Cumulative Volume Delta) Analysis
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        # Get indices for CVD analysis
                                        cvd_break_idx = tl_break_info.get('idx') if tl_break_info else None
                                        cvd_breakout_idx = v3_entry.get('breakout_idx')
                                        cvd_retest_idx = retest_idx
                                        cvd_entry_idx = retest_idx  # Entry at retest for V3

                                        # Calculate CVD using 1H data
                                        cvd_result = calc_cvd_analysis(
                                            df=df_1h,
                                            volume=df_1h['volume'].values,
                                            close=close_1h,
                                            open_prices=df_1h['open'].values,
                                            high=high_1h,
                                            low=df_1h['low'].values,
                                            break_idx=cvd_break_idx,
                                            breakout_idx=cvd_breakout_idx,
                                            retest_idx=cvd_retest_idx,
                                            entry_idx=cvd_entry_idx,
                                            lookback=20
                                        )

                                        # Store CVD results in alert
                                        alert.cvd_bonus = cvd_result.get('cvd_bonus', False)
                                        alert.cvd_score = cvd_result.get('cvd_score', 0)
                                        alert.cvd_label = cvd_result.get('cvd_label', 'NO_DATA')
                                        alert.cvd_description = cvd_result.get('cvd_description', '')

                                        alert.cvd_at_break = cvd_result.get('cvd_at_break')
                                        alert.cvd_at_break_trend = cvd_result.get('cvd_at_break_trend')
                                        alert.cvd_at_break_signal = cvd_result.get('cvd_at_break_signal')

                                        alert.cvd_at_breakout = cvd_result.get('cvd_at_breakout')
                                        alert.cvd_at_breakout_spike = cvd_result.get('cvd_at_breakout_spike')
                                        alert.cvd_at_breakout_signal = cvd_result.get('cvd_at_breakout_signal')

                                        alert.cvd_at_retest = cvd_result.get('cvd_at_retest')
                                        alert.cvd_at_retest_trend = cvd_result.get('cvd_at_retest_trend')
                                        alert.cvd_at_retest_signal = cvd_result.get('cvd_at_retest_signal')

                                        alert.cvd_at_entry = cvd_result.get('cvd_at_entry')
                                        alert.cvd_at_entry_trend = cvd_result.get('cvd_at_entry_trend')
                                        alert.cvd_at_entry_signal = cvd_result.get('cvd_at_entry_signal')

                                        alert.cvd_divergence = cvd_result.get('cvd_divergence', False)
                                        alert.cvd_divergence_type = cvd_result.get('cvd_divergence_type', 'NONE')

                                        alert.vol_at_break_ratio = cvd_result.get('vol_at_break_ratio')
                                        alert.vol_at_breakout_ratio = cvd_result.get('vol_at_breakout_ratio')
                                        alert.vol_at_retest_ratio = cvd_result.get('vol_at_retest_ratio')
                                        alert.vol_at_entry_ratio = cvd_result.get('vol_at_entry_ratio')
                                    except Exception as cvd_err:
                                        # CVD calculation failed, log but don't block
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # CVD 4H ANALYSIS - Cumulative Volume Delta on 4H timeframe
                                    # Smoother signals, better aligned with Golden Box strategy
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        # Convert 1H indices to 4H indices (4H = 4 x 1H bars)
                                        # Find closest 4H bar for each key moment
                                        def find_4h_idx_for_datetime(dt, df_4h):
                                            """Find the 4H bar index that contains this datetime"""
                                            if dt is None:
                                                return None
                                            for i, row in df_4h.iterrows():
                                                if row['datetime'] >= dt:
                                                    return i
                                            return len(df_4h) - 1 if len(df_4h) > 0 else None

                                        # Get datetimes from 1H for each moment
                                        break_dt = df_1h.iloc[cvd_break_idx]['datetime'] if cvd_break_idx is not None and cvd_break_idx < len(df_1h) else None
                                        breakout_dt = df_1h.iloc[cvd_breakout_idx]['datetime'] if cvd_breakout_idx is not None and cvd_breakout_idx < len(df_1h) else None
                                        retest_dt = df_1h.iloc[cvd_retest_idx]['datetime'] if cvd_retest_idx is not None and cvd_retest_idx < len(df_1h) else None
                                        entry_dt = df_1h.iloc[cvd_entry_idx]['datetime'] if cvd_entry_idx is not None and cvd_entry_idx < len(df_1h) else None

                                        # Convert to 4H indices
                                        cvd_4h_break_idx = find_4h_idx_for_datetime(break_dt, df_4h)
                                        cvd_4h_breakout_idx = find_4h_idx_for_datetime(breakout_dt, df_4h)
                                        cvd_4h_retest_idx = find_4h_idx_for_datetime(retest_dt, df_4h)
                                        cvd_4h_entry_idx = find_4h_idx_for_datetime(entry_dt, df_4h)

                                        # Calculate CVD using 4H data
                                        cvd_4h_result = calc_cvd_analysis(
                                            df=df_4h,
                                            volume=df_4h['volume'].values,
                                            close=df_4h['close'].values,
                                            open_prices=df_4h['open'].values,
                                            high=df_4h['high'].values,
                                            low=df_4h['low'].values,
                                            break_idx=cvd_4h_break_idx,
                                            breakout_idx=cvd_4h_breakout_idx,
                                            retest_idx=cvd_4h_retest_idx,
                                            entry_idx=cvd_4h_entry_idx,
                                            lookback=10  # Fewer bars for 4H (10 bars = 40 hours)
                                        )

                                        # Store CVD 4H results in alert
                                        alert.cvd_4h_bonus = cvd_4h_result.get('cvd_bonus', False)
                                        alert.cvd_4h_score = cvd_4h_result.get('cvd_score', 0)
                                        alert.cvd_4h_label = cvd_4h_result.get('cvd_label', 'NO_DATA')
                                        alert.cvd_4h_description = cvd_4h_result.get('cvd_description', '')

                                        alert.cvd_4h_at_break = cvd_4h_result.get('cvd_at_break')
                                        alert.cvd_4h_at_break_trend = cvd_4h_result.get('cvd_at_break_trend')
                                        alert.cvd_4h_at_break_signal = cvd_4h_result.get('cvd_at_break_signal')

                                        alert.cvd_4h_at_breakout = cvd_4h_result.get('cvd_at_breakout')
                                        alert.cvd_4h_at_breakout_spike = cvd_4h_result.get('cvd_at_breakout_spike')
                                        alert.cvd_4h_at_breakout_signal = cvd_4h_result.get('cvd_at_breakout_signal')

                                        alert.cvd_4h_at_retest = cvd_4h_result.get('cvd_at_retest')
                                        alert.cvd_4h_at_retest_trend = cvd_4h_result.get('cvd_at_retest_trend')
                                        alert.cvd_4h_at_retest_signal = cvd_4h_result.get('cvd_at_retest_signal')

                                        alert.cvd_4h_at_entry = cvd_4h_result.get('cvd_at_entry')
                                        alert.cvd_4h_at_entry_trend = cvd_4h_result.get('cvd_at_entry_trend')
                                        alert.cvd_4h_at_entry_signal = cvd_4h_result.get('cvd_at_entry_signal')

                                        alert.cvd_4h_divergence = cvd_4h_result.get('cvd_divergence', False)
                                        alert.cvd_4h_divergence_type = cvd_4h_result.get('cvd_divergence_type', 'NONE')

                                        alert.vol_4h_at_break_ratio = cvd_4h_result.get('vol_at_break_ratio')
                                        alert.vol_4h_at_breakout_ratio = cvd_4h_result.get('vol_at_breakout_ratio')
                                        alert.vol_4h_at_retest_ratio = cvd_4h_result.get('vol_at_retest_ratio')
                                        alert.vol_4h_at_entry_ratio = cvd_4h_result.get('vol_at_entry_ratio')
                                    except Exception as cvd_4h_err:
                                        # CVD 4H calculation failed, log but don't block
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # ADX/DI 1H ANALYSIS - Directional Movement Index
                                    # Measures trend strength and direction at key moments
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        adx_di_1h_result = calc_adx_di_analysis(
                                            df=df_1h,
                                            high=high_1h,
                                            low=df_1h['low'].values,
                                            close=close_1h,
                                            break_idx=cvd_break_idx,
                                            breakout_idx=cvd_breakout_idx,
                                            retest_idx=cvd_retest_idx,
                                            entry_idx=cvd_entry_idx,
                                            adx_len=3,  # Short period like in PineScript
                                            adx_threshold=20
                                        )

                                        # Store ADX/DI 1H results
                                        alert.adx_di_1h_bonus = adx_di_1h_result.get('adx_di_bonus', False)
                                        alert.adx_di_1h_score = adx_di_1h_result.get('adx_di_score', 0)
                                        alert.adx_di_1h_label = adx_di_1h_result.get('adx_di_label', 'NO_DATA')

                                        alert.adx_1h_at_break = adx_di_1h_result.get('adx_at_break')
                                        alert.di_plus_1h_at_break = adx_di_1h_result.get('di_plus_at_break')
                                        alert.di_minus_1h_at_break = adx_di_1h_result.get('di_minus_at_break')
                                        alert.di_spread_1h_at_break = adx_di_1h_result.get('di_spread_at_break')
                                        alert.adx_di_1h_at_break_signal = adx_di_1h_result.get('adx_di_at_break_signal')

                                        alert.adx_1h_at_breakout = adx_di_1h_result.get('adx_at_breakout')
                                        alert.di_plus_1h_at_breakout = adx_di_1h_result.get('di_plus_at_breakout')
                                        alert.di_minus_1h_at_breakout = adx_di_1h_result.get('di_minus_at_breakout')
                                        alert.di_spread_1h_at_breakout = adx_di_1h_result.get('di_spread_at_breakout')
                                        alert.adx_di_1h_at_breakout_signal = adx_di_1h_result.get('adx_di_at_breakout_signal')

                                        alert.adx_1h_at_retest = adx_di_1h_result.get('adx_at_retest')
                                        alert.di_plus_1h_at_retest = adx_di_1h_result.get('di_plus_at_retest')
                                        alert.di_minus_1h_at_retest = adx_di_1h_result.get('di_minus_at_retest')
                                        alert.di_spread_1h_at_retest = adx_di_1h_result.get('di_spread_at_retest')
                                        alert.adx_di_1h_at_retest_signal = adx_di_1h_result.get('adx_di_at_retest_signal')

                                        alert.adx_1h_at_entry = adx_di_1h_result.get('adx_at_entry')
                                        alert.di_plus_1h_at_entry = adx_di_1h_result.get('di_plus_at_entry')
                                        alert.di_minus_1h_at_entry = adx_di_1h_result.get('di_minus_at_entry')
                                        alert.di_spread_1h_at_entry = adx_di_1h_result.get('di_spread_at_entry')
                                        alert.adx_di_1h_at_entry_signal = adx_di_1h_result.get('adx_di_at_entry_signal')

                                        alert.di_plus_1h_overbought = adx_di_1h_result.get('di_plus_overbought', False)
                                        alert.di_minus_1h_oversold = adx_di_1h_result.get('di_minus_oversold', False)
                                    except Exception as adx_1h_err:
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # ADX/DI 4H ANALYSIS - Smoother trend signals
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        adx_di_4h_result = calc_adx_di_analysis(
                                            df=df_4h,
                                            high=df_4h['high'].values,
                                            low=df_4h['low'].values,
                                            close=df_4h['close'].values,
                                            break_idx=cvd_4h_break_idx,
                                            breakout_idx=cvd_4h_breakout_idx,
                                            retest_idx=cvd_4h_retest_idx,
                                            entry_idx=cvd_4h_entry_idx,
                                            adx_len=3,
                                            adx_threshold=20
                                        )

                                        # Store ADX/DI 4H results
                                        alert.adx_di_4h_bonus = adx_di_4h_result.get('adx_di_bonus', False)
                                        alert.adx_di_4h_score = adx_di_4h_result.get('adx_di_score', 0)
                                        alert.adx_di_4h_label = adx_di_4h_result.get('adx_di_label', 'NO_DATA')

                                        alert.adx_4h_at_break = adx_di_4h_result.get('adx_at_break')
                                        alert.di_plus_4h_at_break = adx_di_4h_result.get('di_plus_at_break')
                                        alert.di_minus_4h_at_break = adx_di_4h_result.get('di_minus_at_break')
                                        alert.di_spread_4h_at_break = adx_di_4h_result.get('di_spread_at_break')
                                        alert.adx_di_4h_at_break_signal = adx_di_4h_result.get('adx_di_at_break_signal')

                                        alert.adx_4h_at_breakout = adx_di_4h_result.get('adx_at_breakout')
                                        alert.di_plus_4h_at_breakout = adx_di_4h_result.get('di_plus_at_breakout')
                                        alert.di_minus_4h_at_breakout = adx_di_4h_result.get('di_minus_at_breakout')
                                        alert.di_spread_4h_at_breakout = adx_di_4h_result.get('di_spread_at_breakout')
                                        alert.adx_di_4h_at_breakout_signal = adx_di_4h_result.get('adx_di_at_breakout_signal')

                                        alert.adx_4h_at_retest = adx_di_4h_result.get('adx_at_retest')
                                        alert.di_plus_4h_at_retest = adx_di_4h_result.get('di_plus_at_retest')
                                        alert.di_minus_4h_at_retest = adx_di_4h_result.get('di_minus_at_retest')
                                        alert.di_spread_4h_at_retest = adx_di_4h_result.get('di_spread_at_retest')
                                        alert.adx_di_4h_at_retest_signal = adx_di_4h_result.get('adx_di_at_retest_signal')

                                        alert.adx_4h_at_entry = adx_di_4h_result.get('adx_at_entry')
                                        alert.di_plus_4h_at_entry = adx_di_4h_result.get('di_plus_at_entry')
                                        alert.di_minus_4h_at_entry = adx_di_4h_result.get('di_minus_at_entry')
                                        alert.di_spread_4h_at_entry = adx_di_4h_result.get('di_spread_at_entry')
                                        alert.adx_di_4h_at_entry_signal = adx_di_4h_result.get('adx_di_at_entry_signal')

                                        alert.di_plus_4h_overbought = adx_di_4h_result.get('di_plus_overbought', False)
                                        alert.di_minus_4h_oversold = adx_di_4h_result.get('di_minus_oversold', False)
                                    except Exception as adx_4h_err:
                                        pass

                                    # ═══════════════════════════════════════════════════════════════════
                                    # VOLUME PROFILE ANALYSIS
                                    # Calculates POC, VAH, VAL, HVN, LVN for entry quality assessment
                                    # IMPORTANT: VP is calculated on the SIGNAL → ENTRY range
                                    # (Golden Box structure), NOT on historical data
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        if self.config.get('VP_ENABLED', True):
                                            # Initialize VP analyzer
                                            vp_analyzer = VolumeProfileAnalyzer(self.config)

                                            # Get signal and entry times
                                            signal_dt = mb['datetime']
                                            entry_dt = retest_dt

                                            # Filter 1H data: from SIGNAL to ENTRY (Golden Box range)
                                            # This gives VP on the structure that matters for the trade
                                            df_1h_vp = df_1h[(df_1h['datetime'] >= signal_dt) & (df_1h['datetime'] <= entry_dt)].copy()

                                            # If not enough candles, extend lookback slightly before signal
                                            if len(df_1h_vp) < 10:
                                                # Get some context before signal (up to 20 candles)
                                                signal_idx = None
                                                for idx, row in df_1h.iterrows():
                                                    if row['datetime'] >= signal_dt:
                                                        signal_idx = idx
                                                        break
                                                if signal_idx is not None:
                                                    start_idx = max(0, signal_idx - 20)
                                                    df_1h_vp = df_1h.iloc[start_idx:retest_idx + 1].copy()

                                            # Calculate VP for 1H data on Golden Box range
                                            vp_1h = vp_analyzer.calculate(
                                                df_1h_vp,
                                                lookback=len(df_1h_vp)  # Use all candles in range
                                            )

                                            # Filter 4H data: same logic
                                            df_4h_vp = df_4h[(df_4h['datetime'] >= signal_dt) & (df_4h['datetime'] <= entry_dt)].copy()

                                            if len(df_4h_vp) < 5:
                                                # Get some context before signal
                                                signal_idx_4h = None
                                                for idx, row in df_4h.iterrows():
                                                    if row['datetime'] >= signal_dt:
                                                        signal_idx_4h = idx
                                                        break
                                                if signal_idx_4h is not None:
                                                    start_idx_4h = max(0, signal_idx_4h - 10)
                                                    entry_idx_4h = retest_idx_4h if retest_idx_4h else signal_idx_4h + 20
                                                    df_4h_vp = df_4h.iloc[start_idx_4h:entry_idx_4h + 1].copy()

                                            # Calculate VP for 4H data on Golden Box range
                                            vp_4h = vp_analyzer.calculate(
                                                df_4h_vp,
                                                lookback=len(df_4h_vp)  # Use all candles in range
                                            )

                                            # Get entry/SL/TP prices for scoring
                                            vp_entry_price = retest_price
                                            vp_sl_price = alert.v3_sl_price
                                            vp_tp1_price = vp_entry_price * (1 + self.config.get('TP1_PCT', 15.0) / 100)

                                            # Get OB zones for confluence check
                                            vp_ob_zone = None
                                            if alert.ob_zone_high and alert.ob_zone_low:
                                                vp_ob_zone = {
                                                    'high': alert.ob_zone_high,
                                                    'low': alert.ob_zone_low
                                                }

                                            # Get FC OB zones for retest confluence
                                            fc_ob_zone_1h = None
                                            if alert.fc_ob_1h_found and alert.fc_ob_1h_zone_high and alert.fc_ob_1h_zone_low:
                                                fc_ob_zone_1h = {
                                                    'high': alert.fc_ob_1h_zone_high,
                                                    'low': alert.fc_ob_1h_zone_low
                                                }
                                            fc_ob_zone_4h = None
                                            if alert.fc_ob_4h_found and alert.fc_ob_4h_zone_high and alert.fc_ob_4h_zone_low:
                                                fc_ob_zone_4h = {
                                                    'high': alert.fc_ob_4h_zone_high,
                                                    'low': alert.fc_ob_4h_zone_low
                                                }

                                            # Detect VP level retests (VAL/POC/VAH touched before entry)
                                            vp_retest_info = vp_analyzer.detect_vp_retests(
                                                df=df_1h_vp,
                                                vp_data=vp_1h,
                                                signal_dt=signal_dt,
                                                entry_dt=entry_dt,
                                                ob_zone_1h=fc_ob_zone_1h,
                                                ob_zone_4h=fc_ob_zone_4h,
                                                tolerance_pct=1.5
                                            )

                                            # Calculate VP score with retest info
                                            vp_result = vp_analyzer.calculate_vp_score(
                                                entry_price=vp_entry_price,
                                                sl_price=vp_sl_price,
                                                tp1_price=vp_tp1_price,
                                                vp_data=vp_1h,
                                                vp_4h_data=vp_4h,
                                                ob_zone=vp_ob_zone,
                                                retest_info=vp_retest_info
                                            )

                                            # Store VP results in alert
                                            alert.vp_bonus = vp_result.get('vp_score', 0) >= self.config.get('VP_MIN_SCORE_V3', 30)
                                            alert.vp_score = vp_result.get('vp_score', 0)
                                            alert.vp_grade = vp_result.get('vp_grade', 'N/A')

                                            # 1H levels
                                            alert.vp_poc_1h = vp_1h.get('poc')
                                            alert.vp_vah_1h = vp_1h.get('vah')
                                            alert.vp_val_1h = vp_1h.get('val')
                                            alert.vp_hvn_levels_1h = vp_1h.get('hvn_levels', [])[:5]
                                            alert.vp_lvn_levels_1h = vp_1h.get('lvn_levels', [])[:5]
                                            alert.vp_total_volume_1h = vp_1h.get('total_volume')

                                            # 4H levels
                                            alert.vp_poc_4h = vp_4h.get('poc')
                                            alert.vp_vah_4h = vp_4h.get('vah')
                                            alert.vp_val_4h = vp_4h.get('val')
                                            alert.vp_hvn_levels_4h = vp_4h.get('hvn_levels', [])[:5]
                                            alert.vp_lvn_levels_4h = vp_4h.get('lvn_levels', [])[:5]
                                            alert.vp_total_volume_4h = vp_4h.get('total_volume')

                                            # Entry position analysis
                                            alert.vp_entry_position_1h = vp_result.get('vp_position', 'UNKNOWN')
                                            alert.vp_entry_position_4h = vp_analyzer.get_position_in_va(vp_entry_price, vp_4h)
                                            if vp_1h.get('poc'):
                                                alert.vp_entry_vs_poc_pct_1h = abs(vp_entry_price - vp_1h['poc']) / vp_entry_price * 100
                                            if vp_4h.get('poc'):
                                                alert.vp_entry_vs_poc_pct_4h = abs(vp_entry_price - vp_4h['poc']) / vp_entry_price * 100

                                            # SL analysis - is it protected by HVN?
                                            nearest_hvn_below_sl = vp_analyzer.get_nearest_hvn(vp_sl_price, vp_1h, 'above')
                                            if nearest_hvn_below_sl and nearest_hvn_below_sl < vp_entry_price:
                                                alert.vp_sl_near_hvn = True
                                                alert.vp_sl_hvn_level = nearest_hvn_below_sl
                                                alert.vp_sl_hvn_distance_pct = abs(vp_sl_price - nearest_hvn_below_sl) / vp_sl_price * 100
                                            alert.vp_sl_optimized = vp_result.get('vp_sl_optimized')

                                            # Naked POC detection (untested POC = magnet)
                                            if vp_1h.get('poc'):
                                                # Simple check: if POC is above entry, it's a potential magnet
                                                if vp_1h['poc'] > vp_entry_price * 1.02:
                                                    alert.vp_naked_poc_1h = True
                                                    alert.vp_naked_poc_level_1h = vp_1h['poc']
                                            if vp_4h.get('poc'):
                                                if vp_4h['poc'] > vp_entry_price * 1.02:
                                                    alert.vp_naked_poc_4h = True
                                                    alert.vp_naked_poc_level_4h = vp_4h['poc']

                                            # Summary
                                            alert.vp_label = self._get_vp_label(vp_result, vp_1h, vp_entry_price)
                                            alert.vp_recommendation = '; '.join(vp_result.get('vp_recommendations', [])[:2])
                                            alert.vp_details = convert_to_json_serializable({
                                                'details': vp_result.get('vp_details', []),
                                                'tp_suggestions': vp_result.get('vp_tp_suggestions', [])
                                            })

                                            # VP Retest Info (VAL/POC/VAH touched before entry)
                                            if vp_retest_info:
                                                alert.vp_val_retested = vp_retest_info.get('val_retested', False)
                                                alert.vp_val_retest_rejected = vp_retest_info.get('val_retest_rejected', False)
                                                alert.vp_val_retest_dt = vp_retest_info.get('val_retest_dt')
                                                alert.vp_poc_retested = vp_retest_info.get('poc_retested', False)
                                                alert.vp_poc_retest_rejected = vp_retest_info.get('poc_retest_rejected', False)
                                                alert.vp_poc_retest_dt = vp_retest_info.get('poc_retest_dt')
                                                alert.vp_vah_retested = vp_retest_info.get('vah_retested', False)
                                                alert.vp_hvn_retested = vp_retest_info.get('hvn_retested', False)
                                                alert.vp_hvn_retest_level = vp_retest_info.get('hvn_retest_level')
                                                alert.vp_ob_confluence = vp_retest_info.get('ob_confluence', False)
                                                alert.vp_ob_confluence_tf = vp_retest_info.get('ob_confluence_tf')
                                                alert.vp_pullback_completed = vp_retest_info.get('pullback_completed', False)
                                                alert.vp_pullback_level = vp_retest_info.get('pullback_level')
                                                alert.vp_pullback_quality = vp_retest_info.get('pullback_quality')

                                                if vp_retest_info.get('pullback_completed') and progress_callback:
                                                    ob_conf = f" + OB {vp_retest_info.get('ob_confluence_tf')}" if vp_retest_info.get('ob_confluence') else ""
                                                    progress_callback(f"    VP Retest: {vp_retest_info.get('pullback_level')} RETESTED ✓{ob_conf}")
                                    except Exception as vp_err:
                                        # VP calculation failed, log error and continue
                                        if progress_callback:
                                            progress_callback(f"    VP Error: {str(vp_err)[:100]}")

                                    # ═══════════════════════════════════════════════════════════════════
                                    # AI AGENT DECISION - Meta-analysis of all indicators
                                    # The agent reads all indicators and makes a trade decision
                                    # WITHOUT seeing P&L results (unbiased)
                                    # ═══════════════════════════════════════════════════════════════════
                                    try:
                                        # Build alert data dict with all indicator values
                                        # Note: CVD 1H uses 'cvd_score' (not 'cvd_1h_score')
                                        agent_alert_data = {
                                            # CVD 1H (stored without _1h suffix)
                                            'cvd_1h_score': alert.cvd_score,
                                            'cvd_1h_label': alert.cvd_label,
                                            'cvd_1h_at_entry_signal': alert.cvd_at_entry_signal,
                                            'cvd_1h_divergence': alert.cvd_divergence,
                                            'cvd_1h_divergence_type': alert.cvd_divergence_type,
                                            # CVD 4H
                                            'cvd_4h_score': alert.cvd_4h_score,
                                            'cvd_4h_label': alert.cvd_4h_label,
                                            'cvd_4h_at_entry_signal': alert.cvd_4h_at_entry_signal,
                                            'cvd_4h_divergence': alert.cvd_4h_divergence,
                                            'cvd_4h_divergence_type': alert.cvd_4h_divergence_type,
                                            # ADX/DI 1H - Entry AND Breakout spreads
                                            'adx_di_1h_score': alert.adx_di_1h_score,
                                            'adx_di_1h_label': alert.adx_di_1h_label,
                                            'di_spread_1h_at_entry': alert.di_spread_1h_at_entry,
                                            'di_spread_1h_at_breakout': alert.di_spread_1h_at_breakout,
                                            'di_spread_1h_at_break': alert.di_spread_1h_at_break,
                                            'di_plus_1h_overbought': alert.di_plus_1h_overbought,
                                            'di_minus_1h_oversold': alert.di_minus_1h_oversold,
                                            'adx_1h_at_entry': alert.adx_1h_at_entry,
                                            # ADX/DI 4H - Entry AND Breakout spreads
                                            'adx_di_4h_score': alert.adx_di_4h_score,
                                            'adx_di_4h_label': alert.adx_di_4h_label,
                                            'di_spread_4h_at_entry': alert.di_spread_4h_at_entry,
                                            'di_spread_4h_at_breakout': alert.di_spread_4h_at_breakout,
                                            'di_plus_4h_overbought': alert.di_plus_4h_overbought,
                                            'di_minus_4h_oversold': alert.di_minus_4h_oversold,
                                            # GB Power Score
                                            'gb_power_score': alert.gb_power_score,
                                            'gb_power_grade': alert.gb_power_grade,
                                            # V3 Quality and Hours
                                            'v3_quality_score': alert.v3_quality_score,
                                            'v3_progressive_count': alert.v3_prog_count,
                                            'v3_hours_to_entry': alert.v3_hours_to_entry,
                                            # Foreign Candle Order Block
                                            'fc_ob_1h_retest': alert.fc_ob_1h_retest,
                                            'fc_ob_4h_retest': alert.fc_ob_4h_retest,
                                            'fc_ob_score': alert.fc_ob_score,
                                            'fc_ob_bonus': alert.fc_ob_bonus,
                                            # BTC/ETH Trends
                                            'btc_trend_1h': alert.btc_trend_1h,
                                            'btc_trend_4h': alert.btc_trend_4h,
                                            # Volume (1H stored without _1h suffix)
                                            'vol_1h_at_entry_ratio': alert.vol_at_entry_ratio,
                                            'vol_4h_at_entry_ratio': alert.vol_4h_at_entry_ratio,
                                            'vol_spike_bonus_1h': alert.vol_spike_bonus_1h,
                                            'vol_spike_bonus_4h': alert.vol_spike_bonus_4h,
                                            # MEGA BUY Score
                                            'score': alert.score,
                                            # Bonuses
                                            'stoch_rsi_bonus_1h': alert.stoch_rsi_bonus_1h,
                                            'stoch_rsi_bonus_4h': alert.stoch_rsi_bonus_4h,
                                            'macd_bonus_1h': alert.macd_bonus_1h,
                                            'macd_bonus_4h': alert.macd_bonus_4h,
                                            'rsi_mtf_bonus': alert.rsi_mtf_bonus,
                                            'ema_stack_bonus_1h': alert.ema_stack_bonus_1h,
                                            'ema_stack_bonus_4h': alert.ema_stack_bonus_4h,
                                            'btc_corr_bonus_1h': alert.btc_corr_bonus_1h,
                                            'btc_corr_bonus_4h': alert.btc_corr_bonus_4h,
                                            'eth_corr_bonus_1h': alert.eth_corr_bonus_1h,
                                            'eth_corr_bonus_4h': alert.eth_corr_bonus_4h,
                                            'bb_squeeze_bonus_1h': alert.bb_squeeze_bonus_1h,
                                            'bb_squeeze_bonus_4h': alert.bb_squeeze_bonus_4h,
                                            'ob_bonus': alert.ob_bonus,
                                            'ob_bonus_4h': alert.ob_bonus_4h,
                                            'fvg_bonus_1h': alert.fvg_bonus_1h,
                                            'fvg_bonus_4h': alert.fvg_bonus_4h,
                                            'fib_bonus': alert.fib_bonus,
                                            'adx_bonus_1h': alert.adx_bonus_1h,
                                            'adx_bonus_4h': alert.adx_bonus_4h,
                                            # Volume Profile
                                            'vp_bonus': alert.vp_bonus,
                                            'vp_score': alert.vp_score,
                                            'vp_grade': alert.vp_grade,
                                            'vp_label': alert.vp_label,
                                            'vp_entry_position_1h': alert.vp_entry_position_1h,
                                            'vp_sl_near_hvn': alert.vp_sl_near_hvn,
                                        }

                                        agent_result = calc_agent_decision(agent_alert_data)

                                        # Store Agent Decision results
                                        alert.agent_decision = agent_result.get('agent_decision')
                                        alert.agent_confidence = agent_result.get('agent_confidence')
                                        alert.agent_score = agent_result.get('agent_score')
                                        alert.agent_grade = agent_result.get('agent_grade')
                                        alert.agent_bullish_count = agent_result.get('agent_bullish_count')
                                        alert.agent_bearish_count = agent_result.get('agent_bearish_count')
                                        alert.agent_neutral_count = agent_result.get('agent_neutral_count')
                                        alert.agent_bullish_factors = agent_result.get('agent_bullish_factors')
                                        alert.agent_bearish_factors = agent_result.get('agent_bearish_factors')
                                        alert.agent_reasoning = agent_result.get('agent_reasoning')
                                        alert.agent_cvd_score = agent_result.get('agent_cvd_score')
                                        alert.agent_adx_score = agent_result.get('agent_adx_score')
                                        alert.agent_trend_score = agent_result.get('agent_trend_score')
                                        alert.agent_momentum_score = agent_result.get('agent_momentum_score')
                                        alert.agent_volume_score = agent_result.get('agent_volume_score')
                                        alert.agent_confluence_score = agent_result.get('agent_confluence_score')

                                        if progress_callback:
                                            progress_callback(f"    Agent Decision: {alert.agent_decision} (Score: {alert.agent_score}/100, Grade: {alert.agent_grade})")
                                    except Exception as agent_err:
                                        # Agent decision failed, log but don't block
                                        pass

                                    if not is_valid_v3:
                                        v3_rejected = True
                                        alert.v3_rejected = True
                                        alert.v3_rejection_reason = v3_val_reason
                                        alert.status = f'V3_{v3_val_reason}'

                                    if progress_callback:
                                        progress_callback(f"    V3 Entry: {v3_prog_count}/5 conditions, quality={v3_quality_score}")
                            else:
                                # No retest found
                                v3_rejected = True
                                v3_rejection_reason = 'NO_RETEST_FOUND'
                                alert.v3_entry_found = False
                                alert.v3_rejected = True
                                alert.v3_rejection_reason = v3_rejection_reason
                                alert.v3_box_high = box_high
                                alert.v3_box_low = box_low
                                alert.status = 'V3_NO_RETEST'
                        else:
                            # Prerequisites not met for V3
                            v3_rejected = True
                            if not mb['stc_oversold_any']:
                                v3_rejection_reason = 'REJECTED_STC'
                            elif is_15m_alone and self.config['REJECT_15M_ALONE']:
                                v3_rejection_reason = 'REJECTED_15M_ALONE'
                            else:
                                v3_rejection_reason = 'REJECTED_PP_BUY'
                            alert.v3_rejected = True
                            alert.v3_rejection_reason = v3_rejection_reason

                        db.commit()

                if status == 'VALID' and strategy_version == 'v2':
                    # Build alert data dict for V2 validation
                    alert_data_for_v2 = {
                        'fib_levels': alert.fib_levels,
                        'fib_levels_1h': alert.fib_levels_1h,
                        'fib_bonus': alert.fib_bonus,
                        'eth_corr_bonus_1h': alert.eth_corr_bonus_1h,
                        'eth_corr_bonus_4h': alert.eth_corr_bonus_4h,
                        'eth_trend_1h': alert.eth_trend_1h,
                        'btc_trend_1h': alert.btc_trend_1h,
                        'adx_strength_1h': alert.adx_strength_1h,
                        'stoch_rsi_bonus_1h': alert.stoch_rsi_bonus_1h,
                        'combo_tfs': alert.combo_tfs,
                        'rsi_mtf_bonus': alert.rsi_mtf_bonus,
                        'ema_stack_bonus_4h': alert.ema_stack_bonus_4h,
                        'vol_spike_bonus_4h': alert.vol_spike_bonus_4h,
                        'score': alert.score,
                        'ob_bonus': alert.ob_bonus,
                        'ob_bonus_4h': alert.ob_bonus_4h,
                        'btc_corr_bonus_1h': alert.btc_corr_bonus_1h,
                        'btc_corr_bonus_4h': alert.btc_corr_bonus_4h,
                        'fvg_bonus_1h': alert.fvg_bonus_1h,
                        'fvg_bonus_4h': alert.fvg_bonus_4h,
                        'vol_spike_bonus_1h': alert.vol_spike_bonus_1h,
                        'adx_bonus_1h': alert.adx_bonus_1h,
                        'adx_bonus_4h': alert.adx_bonus_4h,
                        'macd_bonus_1h': alert.macd_bonus_1h,
                        'macd_bonus_4h': alert.macd_bonus_4h,
                        'bb_squeeze_bonus_1h': alert.bb_squeeze_bonus_1h,
                        'bb_squeeze_bonus_4h': alert.bb_squeeze_bonus_4h,
                        'stoch_rsi_bonus_4h': alert.stoch_rsi_bonus_4h,
                        'ema_stack_bonus_1h': alert.ema_stack_bonus_1h,
                    }

                    is_valid_v2, v2_rejection_reason, trade_score = validate_v2_filters(alert_data_for_v2)

                    # Store V2 results in alert
                    alert.trade_score = trade_score
                    alert.v2_rejected = not is_valid_v2
                    alert.v2_rejection_reason = v2_rejection_reason if not is_valid_v2 else None

                    if not is_valid_v2:
                        v2_rejected = True
                        # Update backtest stats
                        backtest_run.v2_rejected_count = (backtest_run.v2_rejected_count or 0) + 1
                        rejection_reasons = backtest_run.v2_rejection_reasons or {}
                        rejection_reasons[v2_rejection_reason] = rejection_reasons.get(v2_rejection_reason, 0) + 1
                        backtest_run.v2_rejection_reasons = rejection_reasons

                        # Update alert status
                        alert.status = v2_rejection_reason
                        db.commit()

                        if progress_callback:
                            progress_callback(f"    V2 REJECTED: {v2_rejection_reason} (score: {trade_score})")

                # Calculate P&L for valid setups (skip if V2 rejected)
                # V3/V4/V5: Use V3 entry if available, otherwise skip
                # V4 adds additional filtering on top of V3
                # V5 adds VP trajectory filter on top of V4
                if strategy_version in ['v3', 'v4', 'v5', 'v6']:
                    # V3/V4/V5 P&L Calculation
                    v4_rejected = False
                    v4_rejection_reason = None
                    v4_score = 0
                    v5_rejected = False
                    v5_rejection_reason = None
                    v5_score = 0

                    if v3_entry and not v3_rejected:
                        # ═══════════════════════════════════════════════════════════════════
                        # V4 VALIDATION: Apply all optimized filters
                        # This runs for strategy_version == 'v4' or 'v5'
                        # ═══════════════════════════════════════════════════════════════════
                        if strategy_version in ['v4', 'v5', 'v6']:
                            # Build alert data dict for V4/V5 validation
                            v4_alert_data = {
                                'v3_quality_score': alert.v3_quality_score,
                                'tl_break_delay_hours': alert.tl_break_delay_hours,
                                'stc_valid_tfs': alert.stc_valid_tfs,
                                'fc_ob_score': alert.fc_ob_score,
                                'fc_ob_1h_found': alert.fc_ob_1h_found,
                                'fc_ob_4h_found': alert.fc_ob_4h_found,
                                'fc_ob_1h_retested': alert.fc_ob_1h_retested,
                                'fc_ob_4h_retested': alert.fc_ob_4h_retested,
                                'v3_hours_to_entry': alert.v3_hours_to_entry,
                                'timeframe': mb.get('tf'),
                                'combo_tfs': alert.combo_tfs,
                            }

                            if strategy_version == 'v4':
                                # Run V4 validation only
                                v4_valid, v4_rejection_reason, v4_score, v4_details = validate_v4_filters(
                                    v4_alert_data, symbol, self.config
                                )

                                # Store V4 results in alert
                                alert.v4_score = v4_score
                                alert.v4_grade = get_v4_grade(v4_score)

                                if not v4_valid:
                                    v4_rejected = True
                                    alert.v4_rejected = True
                                    alert.v4_rejection_reason = v4_rejection_reason
                                    alert.status = f'V4_{v4_rejection_reason}'
                                    db.commit()

                                    if progress_callback:
                                        progress_callback(f"    V4 REJECTED: {v4_rejection_reason} (score: {v4_score})")
                                    continue  # Skip this trade

                                # V4 passed - update alert status
                                alert.status = 'VALID_V4'
                                alert.v4_rejected = False
                                if progress_callback:
                                    progress_callback(f"    V4 VALID: Score {v4_score}/100 (Grade: {get_v4_grade(v4_score)})")

                            elif strategy_version in ['v5', 'v6']:
                                # ═══════════════════════════════════════════════════════════════════
                                # V5 VALIDATION: V4 + VP Trajectory Filter (STRICT)
                                # Key: Reject if ANY candle closed below VAL
                                # ═══════════════════════════════════════════════════════════════════

                                # Add VP data for V5 filter
                                v4_alert_data['vp_val_1h'] = alert.vp_val_1h
                                v4_alert_data['vp_poc_1h'] = alert.vp_poc_1h
                                v4_alert_data['vp_vah_1h'] = alert.vp_vah_1h
                                v4_alert_data['alert_price'] = mb['close']
                                v4_alert_data['price_close'] = mb['close']
                                v4_alert_data['vp_val_retested'] = alert.vp_val_retested
                                v4_alert_data['vp_val_retest_rejected'] = alert.vp_val_retest_rejected
                                v4_alert_data['vp_poc_retested'] = alert.vp_poc_retested
                                v4_alert_data['vp_poc_retest_rejected'] = alert.vp_poc_retest_rejected

                                # Add CVD data for V5 filter
                                v4_alert_data['cvd_score'] = alert.cvd_score
                                v4_alert_data['cvd_4h_score'] = alert.cvd_4h_score

                                # Add DMI/ADX data for V5 DMI spread filter
                                v4_alert_data['adx_di_plus_at_entry'] = getattr(alert, 'adx_1h_at_entry_di_plus', 0)
                                v4_alert_data['adx_di_minus_at_entry'] = getattr(alert, 'adx_1h_at_entry_di_minus', 0)
                                v4_alert_data['dmi_spread_at_entry'] = (
                                    (getattr(alert, 'adx_1h_at_entry_di_plus', 0) or 0) -
                                    (getattr(alert, 'adx_1h_at_entry_di_minus', 0) or 0)
                                )

                                # Add distance before retest for weak breakout filter
                                v4_alert_data['distance_before_retest_pct'] = alert.v3_distance_before_retest

                                # Add power score for power score filter
                                v4_alert_data['gb_power_score'] = alert.gb_power_score
                                v4_alert_data['gb_power_grade'] = alert.gb_power_grade
                                v4_alert_data['cvd_divergence'] = alert.cvd_divergence
                                v4_alert_data['cvd_divergence_type'] = alert.cvd_divergence_type
                                v4_alert_data['cvd_4h_divergence'] = getattr(alert, 'cvd_4h_divergence', False)
                                v4_alert_data['cvd_4h_divergence_type'] = getattr(alert, 'cvd_4h_divergence_type', 'NONE')

                                # ═══════════════════════════════════════════════════════════════════
                                # NEW V5: Calculate candles below VAL between alert and entry
                                # This is the STRICT filter - any candle below VAL = REJECT
                                # ═══════════════════════════════════════════════════════════════════
                                if alert.vp_val_1h and alert.vp_val_1h > 0:
                                    alert_dt = mb['datetime']
                                    entry_dt = v3_entry['dt']
                                    lookback_hours = self.config.get('V5_VP_LOOKBACK_HOURS', 48)
                                    candles_below_result = count_candles_below_val(
                                        df_1h, alert_dt, entry_dt, alert.vp_val_1h, lookback_hours
                                    )
                                    v4_alert_data['candles_below_val'] = candles_below_result['candles_below_val']
                                    v4_alert_data['total_candles_checked'] = candles_below_result['total_candles']
                                    v4_alert_data['pct_candles_below_val'] = candles_below_result['pct_below_val']
                                    v4_alert_data['lowest_vs_val_pct'] = candles_below_result['lowest_vs_val_pct']

                                    if progress_callback and candles_below_result['candles_below_val'] > 0:
                                        progress_callback(
                                            f"    VP Check: {candles_below_result['candles_below_val']}/{candles_below_result['total_candles']} "
                                            f"candles below VAL (lookback {lookback_hours}h, {candles_below_result['pct_below_val']:.1f}%)"
                                        )
                                else:
                                    v4_alert_data['candles_below_val'] = 0
                                    v4_alert_data['total_candles_checked'] = 0
                                    v4_alert_data['pct_candles_below_val'] = 0
                                    v4_alert_data['lowest_vs_val_pct'] = 0

                                v4_alert_data['vp_pct_time_below_va'] = v4_alert_data.get('pct_candles_below_val', 0)

                                # ═══════════════════════════════════════════════════════════════════
                                # VP RETEST EXCEPTION DATA (for V5.2)
                                # Based on INITUSDT analysis: Allow below-VAL entries if descent from VAH
                                # ═══════════════════════════════════════════════════════════════════
                                v4_alert_data['entry_price'] = v3_entry['price']

                                # Calculate recent high on 4H (lookback period)
                                lookback_bars = self.config.get('V5_VP_RETEST_LOOKBACK_BARS', 50)
                                entry_dt_vp = v3_entry['dt']

                                # Find entry bar index in 4H data
                                entry_bar_4h = None
                                if 'datetime' in df_4h.columns:
                                    for idx in range(len(df_4h)):
                                        bar_dt = df_4h.iloc[idx]['datetime']
                                        if isinstance(bar_dt, str):
                                            bar_dt = pd.to_datetime(bar_dt)
                                        if bar_dt <= entry_dt_vp:
                                            entry_bar_4h = idx

                                if entry_bar_4h is not None:
                                    # Calculate recent high in lookback period
                                    start_idx = max(0, entry_bar_4h - lookback_bars)
                                    recent_high_4h = df_4h.iloc[start_idx:entry_bar_4h + 1]['high'].max()
                                    v4_alert_data['recent_high_4h'] = recent_high_4h

                                    # Get entry candle data for rejection detection
                                    entry_candle = df_4h.iloc[entry_bar_4h]
                                    candle_open = entry_candle['open']
                                    candle_close = entry_candle['close']
                                    candle_high = entry_candle['high']
                                    candle_low = entry_candle['low']

                                    candle_body = abs(candle_close - candle_open)
                                    candle_lower_wick = min(candle_open, candle_close) - candle_low
                                    candle_is_bullish = candle_close > candle_open

                                    v4_alert_data['candle_body_4h'] = candle_body
                                    v4_alert_data['candle_lower_wick_4h'] = candle_lower_wick
                                    v4_alert_data['candle_is_bullish_4h'] = candle_is_bullish
                                    v4_alert_data['high_4h'] = candle_high

                                    # Calculate rejection wick ratio
                                    if candle_body > 0:
                                        v4_alert_data['rejection_wick_ratio'] = candle_lower_wick / candle_body
                                    else:
                                        v4_alert_data['rejection_wick_ratio'] = 0

                                    # Check for rejection candle
                                    min_wick_ratio = self.config.get('V5_VP_RETEST_REJECTION_WICK_RATIO', 1.5)
                                    v4_alert_data['rejection_candle_detected'] = (
                                        candle_lower_wick > candle_body * min_wick_ratio and
                                        candle_is_bullish
                                    )

                                # Run V5 validation (includes V4)
                                v5_valid, v5_rejection_reason, v5_score, v5_details = validate_v5_filters(
                                    v4_alert_data, symbol, self.config
                                )

                                # Store V5 results in alert (using V4 fields)
                                alert.v4_score = v5_score
                                alert.v4_grade = get_v5_grade(v5_score)

                                if not v5_valid:
                                    v5_rejected = True
                                    alert.v4_rejected = True
                                    alert.v4_rejection_reason = v5_rejection_reason
                                    # Don't add V5_ prefix if reason already starts with V5_
                                    alert.status = v5_rejection_reason if v5_rejection_reason.startswith('V5_') else f'V5_{v5_rejection_reason}'
                                    db.commit()

                                    if progress_callback:
                                        progress_callback(f"    V5 REJECTED: {v5_rejection_reason} (score: {v5_score})")
                                    continue  # Skip this trade

                                # V5 passed - update alert status
                                alert.status = 'VALID_V5'
                                alert.v4_rejected = False
                                if progress_callback:
                                    progress_callback(f"    V5 VALID: Score {v5_score}/100 (Grade: {get_v5_grade(v5_score)})")

                                # ═══════════════════════════════════════════════════════════════════
                                # V6 VALIDATION: Advanced Timing + Momentum + Entry Limiter + Scoring
                                # Based on deep analysis of 91 trades showing timing/CVD patterns
                                # ═══════════════════════════════════════════════════════════════════
                                v6_rejected = False
                                v6_rejection_reason = None
                                v6_score = 0

                                if self.config.get('V6_ENABLED', True):
                                    try:
                                        # Get V6 data from alert
                                        v6_timeframe = mb.get('tf', '1h')
                                        v6_retest_hours = alert.v3_hours_to_entry or 0
                                        v6_entry_hours = v6_retest_hours  # Using same for now
                                        v6_distance_pct = alert.v3_distance_before_retest or 0

                                        # Get momentum data
                                        v6_rsi_1h = getattr(alert, 'rsi_1h_at_entry', None) or getattr(alert, 'rsi_at_entry', 50)
                                        v6_adx = getattr(alert, 'adx_1h_at_entry', None) or 20
                                        v6_di_plus = getattr(alert, 'di_plus_1h_at_entry', None) or 20
                                        v6_di_minus = getattr(alert, 'di_minus_1h_at_entry', None) or 15
                                        v6_has_cvd_div = getattr(alert, 'cvd_divergence', False)

                                        # Calculate estimated profit potential
                                        v6_entry_price = v3_entry['price']
                                        v6_potential = estimate_profit_potential(df_4h, v6_entry_price, lookback=50)

                                        # 1. V6 Timing Filter
                                        v6_timing_ok, v6_timing_reason, v6_timing_adj = check_v6_timing_filter(
                                            v6_timeframe, v6_retest_hours, v6_entry_hours, v6_distance_pct, self.config
                                        )

                                        # 2. V6 Momentum Filter
                                        v6_momentum_ok, v6_momentum_reason, v6_momentum_adj = check_v6_momentum_filter(
                                            v6_rsi_1h, v6_adx, v6_di_plus, v6_di_minus, v6_potential, self.config
                                        )

                                        # 3. V6 Entry Limiter (build recent trades list)
                                        v6_recent_trades = []
                                        # Note: For backtesting, we don't have real recent trades context
                                        # Entry limiter is more useful for live trading
                                        v6_entry_ok, v6_entry_reason = check_v6_entry_limiter(
                                            symbol, v6_entry_price, v3_entry['dt'], v6_recent_trades, self.config
                                        )

                                        # 4. Calculate V6 Score
                                        v6_score = calculate_v6_score(
                                            v6_timeframe, v6_retest_hours, v6_entry_hours, v6_distance_pct,
                                            v6_rsi_1h, v6_adx, v6_di_plus, v6_di_minus, v6_has_cvd_div, self.config
                                        )
                                        v6_grade = get_v6_score_grade(v6_score, self.config)

                                        # Store V6 data in alert
                                        alert.v6_score = v6_score
                                        alert.v6_grade = v6_grade
                                        alert.v6_retest_hours = v6_retest_hours
                                        alert.v6_entry_hours = v6_entry_hours
                                        alert.v6_distance_pct = v6_distance_pct
                                        alert.v6_rsi_at_entry = v6_rsi_1h
                                        alert.v6_adx_at_entry = v6_adx
                                        alert.v6_potential_pct = v6_potential
                                        alert.v6_has_cvd_divergence = v6_has_cvd_div
                                        alert.v6_timing_adj = v6_timing_adj
                                        alert.v6_momentum_adj = v6_momentum_adj

                                        # Check for V6 rejection
                                        if not v6_timing_ok:
                                            v6_rejected = True
                                            v6_rejection_reason = v6_timing_reason
                                        elif not v6_momentum_ok:
                                            v6_rejected = True
                                            v6_rejection_reason = v6_momentum_reason
                                        elif not v6_entry_ok:
                                            v6_rejected = True
                                            v6_rejection_reason = v6_entry_reason
                                        elif v6_score < self.config.get('V6_MIN_SCORE', 10):
                                            v6_rejected = True
                                            v6_rejection_reason = "V6_SCORE_TOO_LOW"

                                        if v6_rejected:
                                            alert.v6_rejected = True
                                            alert.v6_rejection_reason = v6_rejection_reason
                                            alert.status = v6_rejection_reason
                                            db.commit()

                                            if progress_callback:
                                                progress_callback(f"    V6 REJECTED: {v6_rejection_reason} (score: {v6_score}, grade: {v6_grade})")
                                            continue  # Skip this trade

                                        # V6 passed
                                        alert.v6_rejected = False
                                        alert.status = 'VALID_V6'
                                        if progress_callback:
                                            progress_callback(f"    V6 VALID: Score {v6_score} (Grade: {v6_grade})")

                                    except Exception as v6_err:
                                        # V6 validation failed, log but don't block
                                        if progress_callback:
                                            progress_callback(f"    V6 Error: {str(v6_err)[:50]}")
                                        # Continue with trade even if V6 fails
                                        alert.v6_score = 0
                                        alert.v6_grade = 'F'
                                        alert.v6_rejected = False

                        entry_price = v3_entry['price']
                        entry_dt = v3_entry['dt']
                        alert_price = mb['close']
                        sl_price = v3_entry['sl_price']  # Default: Box Low - margin

                        # V5: Use VAL-based SL if available (stronger support level)
                        if strategy_version in ['v5', 'v6'] and self.config.get('V5_USE_VAL_SL', True):
                            if alert.vp_val_1h and alert.vp_val_1h > 0:
                                val_sl_margin_pct = self.config.get('V5_VAL_SL_MARGIN_PCT', 3.0)
                                val_based_sl = alert.vp_val_1h * (1 - val_sl_margin_pct / 100)
                                # Use VAL-based SL (gives more room based on VP support)
                                sl_price = val_based_sl
                                if progress_callback:
                                    progress_callback(f"    V5 SL: VAL {alert.vp_val_1h:.6f} - {val_sl_margin_pct}% = {sl_price:.6f}")

                        # Strategy label for exit reasons
                        strat_label = 'V6' if strategy_version == 'v6' else ('V5' if strategy_version == 'v5' else ('V4' if strategy_version == 'v4' else 'V3'))

                        # Create unique entry key (datetime + price)
                        entry_key = f"{entry_dt.isoformat()}_{entry_price:.8f}"

                        # Check if this entry has already been processed (combined alerts)
                        is_duplicate_entry = entry_key in processed_entries
                        if not is_duplicate_entry:
                            processed_entries.add(entry_key)

                        # ═══════════════════════════════════════════════════════════════════
                        # COMBO: Only create trade for PRIMARY TF, skip others
                        # This ensures ONE trade per COMBO with primary TF's box values
                        # ═══════════════════════════════════════════════════════════════════
                        is_combo_primary = mb.get('is_combo_primary', True)
                        if not is_combo_primary:
                            # This alert is part of a COMBO but not the primary TF
                            # Skip trade creation, but keep the alert data
                            alert.trade_id = None  # No trade for this alert
                            if progress_callback:
                                primary_tf = mb.get('combo_primary_tf', 'unknown')
                                progress_callback(f"    COMBO: Skipping trade for {mb['tf']} (using {primary_tf} as primary)")
                            continue  # Skip to next alert

                        # V3/V4 uses same TP logic as V1/V2
                        tp1_price = entry_price * (1 + self.config['TP1_PCT'] / 100)
                        tp2_price = entry_price * (1 + self.config['TP2_PCT'] / 100)
                        trailing_activation_price = entry_price * (1 + self.config['TRAILING_ACTIVATION_PCT'] / 100)

                        # Break-Even configuration
                        be_enabled = self.config.get('BE_ENABLED', True)
                        be_activation_pct = self.config.get('BE_ACTIVATION_PCT', 4.0)
                        be_offset_pct = self.config.get('BE_OFFSET_PCT', 0.5)
                        be_activation_price = entry_price * (1 + be_activation_pct / 100)
                        be_sl_price = entry_price * (1 + be_offset_pct / 100)  # Small profit

                        entry_idx = v3_entry['idx']

                        # Strategy C: Trailing Stop with Break-Even
                        highest_price = entry_price
                        trailing_active = False
                        be_active = False
                        be_activated_dt = None
                        trailing_sl = sl_price
                        exit_price_c = None
                        exit_dt_c = None
                        exit_reason_c = ""
                        trailing_just_activated = False
                        be_just_activated = False

                        for idx in range(entry_idx + 1, len(df_1h)):
                            row = df_1h.iloc[idx]
                            high_val = row['high']
                            low_val = row['low']

                            trailing_just_activated = False
                            be_just_activated = False

                            if high_val > highest_price:
                                highest_price = high_val

                            # Break-Even activation (before trailing)
                            if be_enabled and not be_active and not trailing_active and highest_price >= be_activation_price:
                                be_active = True
                                be_activated_dt = row['datetime']
                                be_just_activated = True

                            if not trailing_active and highest_price >= trailing_activation_price:
                                trailing_active = True
                                trailing_sl = highest_price * (1 - self.config['TRAILING_PCT'] / 100)
                                trailing_just_activated = True

                            if trailing_active and not trailing_just_activated:
                                new_trailing_sl = highest_price * (1 - self.config['TRAILING_PCT'] / 100)
                                if new_trailing_sl > trailing_sl:
                                    trailing_sl = new_trailing_sl

                            # Determine current SL: Trailing > BE > Original
                            if trailing_active:
                                current_sl = trailing_sl
                            elif be_active:
                                current_sl = be_sl_price
                            else:
                                current_sl = sl_price

                            # Check SL hit (skip if just activated to avoid same-bar exit)
                            if not trailing_just_activated and not be_just_activated and low_val <= current_sl:
                                exit_price_c = current_sl
                                exit_dt_c = row['datetime']
                                if trailing_active:
                                    exit_reason_c = f"{strat_label} Trailing SL @ {current_sl:.6f}"
                                elif be_active:
                                    exit_reason_c = f"{strat_label} Break-Even SL @ {current_sl:.6f} (BE+{be_offset_pct}%)"
                                else:
                                    exit_reason_c = f"{strat_label} SL (Box Low) @ {current_sl:.6f}"
                                break

                        if exit_price_c is None:
                            exit_price_c = df_1h.iloc[-1]['close']
                            exit_dt_c = df_1h.iloc[-1]['datetime']
                            exit_reason_c = f"{strat_label} Position ouverte @ {exit_price_c:.6f}"

                        pnl_c = (exit_price_c - entry_price) / entry_price * 100

                        # Strategy D: Multi-TP with Break-Even
                        tp1_hit = False
                        tp2_hit = False
                        be_active_d = False
                        be_activated_dt_d = None
                        highest_price_d = entry_price
                        current_sl_d = sl_price
                        exit_price_d = None
                        exit_dt_d = None
                        exit_reason_d = ""
                        pnl_d_tp1 = 0
                        pnl_d_tp2 = 0

                        for idx in range(entry_idx + 1, len(df_1h)):
                            row = df_1h.iloc[idx]
                            high_val = row['high']
                            low_val = row['low']
                            be_just_activated_d = False

                            # Track highest price for BE activation
                            if high_val > highest_price_d:
                                highest_price_d = high_val

                            # Break-Even activation at +10% (before TP1)
                            if be_enabled and not be_active_d and not tp1_hit and highest_price_d >= be_activation_price:
                                be_active_d = True
                                be_activated_dt_d = row['datetime']
                                current_sl_d = be_sl_price  # Move SL to BE + offset
                                be_just_activated_d = True

                            if not tp1_hit and high_val >= tp1_price:
                                tp1_hit = True
                                pnl_d_tp1 = self.config['TP1_PCT'] / 2
                                current_sl_d = entry_price  # TP1 hit moves SL to exact entry

                            if tp1_hit and not tp2_hit and high_val >= tp2_price:
                                tp2_hit = True
                                pnl_d_tp2 = self.config['TP2_PCT'] / 2
                                exit_price_d = tp2_price
                                exit_dt_d = row['datetime']
                                exit_reason_d = f"{strat_label} TP2 hit @ {tp2_price:.6f}"
                                break

                            # Check SL hit (skip if BE just activated)
                            if not be_just_activated_d and low_val <= current_sl_d:
                                exit_price_d = current_sl_d
                                exit_dt_d = row['datetime']
                                if tp1_hit:
                                    exit_reason_d = f"{strat_label} Breakeven SL (post-TP1) @ {current_sl_d:.6f}"
                                    pnl_d_tp2 = 0
                                elif be_active_d:
                                    exit_reason_d = f"{strat_label} Break-Even SL @ {current_sl_d:.6f} (BE+{be_offset_pct}%)"
                                    # BE exit = small profit
                                    be_pnl = (current_sl_d - entry_price) / entry_price * 100
                                    pnl_d_tp1 = be_pnl / 2
                                    pnl_d_tp2 = be_pnl / 2
                                else:
                                    exit_reason_d = f"{strat_label} SL (Box Low) @ {current_sl_d:.6f}"
                                    sl_loss_pct = (entry_price - sl_price) / entry_price * 100
                                    pnl_d_tp1 = -sl_loss_pct / 2
                                    pnl_d_tp2 = -sl_loss_pct / 2
                                break

                        if exit_price_d is None:
                            exit_price_d = df_1h.iloc[-1]['close']
                            exit_dt_d = df_1h.iloc[-1]['datetime']
                            if tp1_hit:
                                remaining_pnl = (exit_price_d - entry_price) / entry_price * 100 / 2
                                pnl_d_tp2 = remaining_pnl
                                exit_reason_d = f"{strat_label} TP1 hit, 50% restant ouvert @ {exit_price_d:.6f}"
                            else:
                                current_pnl = (exit_price_d - entry_price) / entry_price * 100
                                pnl_d_tp1 = current_pnl / 2
                                pnl_d_tp2 = current_pnl / 2
                                exit_reason_d = f"{strat_label} Position ouverte @ {exit_price_d:.6f}"

                        pnl_d = pnl_d_tp1 + pnl_d_tp2

                        # Create V3/V4 trade record
                        trade = Trade(
                            backtest_run_id=backtest_run.id,
                            alert_id=alert.id,
                            alert_datetime=mb['datetime'],
                            timeframe=mb['tf'],
                            alert_price=alert_price,
                            entry_datetime=entry_dt,
                            entry_price=entry_price,
                            sl_price=sl_price,
                            tp1_price=tp1_price,
                            tp2_price=tp2_price,
                            trailing_activation_price=trailing_activation_price,
                            highest_price=highest_price,
                            trailing_active=trailing_active,
                            trailing_sl=trailing_sl,
                            exit_datetime_c=exit_dt_c,
                            exit_price_c=exit_price_c,
                            exit_reason_c=exit_reason_c,
                            pnl_c=pnl_c,
                            # Break-Even tracking (Strategy C)
                            be_active_c=be_active,
                            be_activated_dt_c=be_activated_dt,
                            be_activation_price=be_activation_price,
                            be_sl_price=be_sl_price,
                            tp1_hit=tp1_hit,
                            tp2_hit=tp2_hit,
                            exit_datetime_d=exit_dt_d,
                            exit_price_d=exit_price_d,
                            exit_reason_d=exit_reason_d,
                            pnl_d_tp1=pnl_d_tp1,
                            pnl_d_tp2=pnl_d_tp2,
                            pnl_d=pnl_d,
                            # Break-Even tracking (Strategy D)
                            be_active_d=be_active_d,
                            be_activated_dt_d=be_activated_dt_d,
                            # V3 specific fields
                            strategy_version='v3',
                            v3_box_high=v3_entry['box_high'],
                            v3_box_low=v3_entry['box_low'],
                            v3_hours_to_entry=v3_entry['hours_to_entry'],
                            v3_sl_distance_pct=v3_entry['sl_distance_pct'],
                            v3_quality_score=v3_quality_score,
                            v3_breakout_dt=v3_entry.get('breakout_dt'),
                            v3_breakout_high=v3_entry.get('breakout_high'),
                            v3_retest_datetime=v3_entry.get('dt'),
                            v3_retest_price=v3_entry.get('retest_low', v3_entry.get('price')),
                            v3_prog_count=alert.v3_prog_count,
                        )
                        db.add(trade)

                        # Only count P&L once for combined entries
                        if not is_duplicate_entry:
                            total_pnl_c += pnl_c
                            total_pnl_d += pnl_d
                            trades_count += 1

                elif status == 'VALID' and not v2_rejected:
                    entry = mb['entry_point']
                    entry_price = entry['price']
                    entry_dt = entry['dt']
                    alert_price = mb['close']

                    # Create unique entry key (datetime + price)
                    entry_key = f"{entry_dt.isoformat()}_{entry_price:.8f}"

                    # Check if this entry has already been processed (combined alerts)
                    is_duplicate_entry = entry_key in processed_entries
                    if not is_duplicate_entry:
                        processed_entries.add(entry_key)

                    # COMBO: Only create trade for PRIMARY TF, skip others
                    is_combo_primary = mb.get('is_combo_primary', True)
                    if not is_combo_primary:
                        alert.trade_id = None
                        continue  # Skip to next alert

                    sl_price = alert_price * (1 - self.config['SL_PCT'] / 100)
                    tp1_price = entry_price * (1 + self.config['TP1_PCT'] / 100)
                    tp2_price = entry_price * (1 + self.config['TP2_PCT'] / 100)
                    trailing_activation_price = entry_price * (1 + self.config['TRAILING_ACTIVATION_PCT'] / 100)

                    entry_idx = None
                    for idx, row in df_1h.iterrows():
                        if row['datetime'] >= entry_dt:
                            entry_idx = idx
                            break

                    if entry_idx is None:
                        continue

                    # Strategy C: Trailing Stop
                    highest_price = entry_price
                    trailing_active = False
                    trailing_sl = sl_price
                    exit_price_c = None
                    exit_dt_c = None
                    exit_reason_c = ""
                    trailing_just_activated = False  # Flag to skip SL check on activation candle

                    # Start from entry_idx + 1: we enter at CLOSE of entry candle,
                    # so the LOW of entry candle already happened BEFORE our entry
                    for idx in range(entry_idx + 1, len(df_1h)):
                        row = df_1h.iloc[idx]
                        high_val = row['high']
                        low_val = row['low']

                        # Reset flag at start of each candle
                        trailing_just_activated = False

                        if high_val > highest_price:
                            highest_price = high_val

                        if not trailing_active and highest_price >= trailing_activation_price:
                            trailing_active = True
                            trailing_sl = highest_price * (1 - self.config['TRAILING_PCT'] / 100)
                            trailing_just_activated = True  # Don't check SL on this candle

                        if trailing_active and not trailing_just_activated:
                            new_trailing_sl = highest_price * (1 - self.config['TRAILING_PCT'] / 100)
                            if new_trailing_sl > trailing_sl:
                                trailing_sl = new_trailing_sl

                        current_sl = trailing_sl if trailing_active else sl_price

                        # Don't check SL on the candle where trailing just activated
                        if not trailing_just_activated and low_val <= current_sl:
                            exit_price_c = current_sl
                            exit_dt_c = row['datetime']
                            if trailing_active:
                                exit_reason_c = f"Trailing SL @ {current_sl:.6f}"
                            else:
                                exit_reason_c = f"SL initial @ {current_sl:.6f}"
                            break

                    if exit_price_c is None:
                        exit_price_c = df_1h.iloc[-1]['close']
                        exit_dt_c = df_1h.iloc[-1]['datetime']
                        exit_reason_c = f"Position ouverte @ {exit_price_c:.6f}"

                    pnl_c = (exit_price_c - entry_price) / entry_price * 100

                    # Strategy D: Multi-TP
                    tp1_hit = False
                    tp2_hit = False
                    current_sl_d = sl_price
                    exit_price_d = None
                    exit_dt_d = None
                    exit_reason_d = ""
                    pnl_d_tp1 = 0
                    pnl_d_tp2 = 0

                    # Start from entry_idx + 1: we enter at CLOSE of entry candle
                    for idx in range(entry_idx + 1, len(df_1h)):
                        row = df_1h.iloc[idx]
                        high_val = row['high']
                        low_val = row['low']

                        if not tp1_hit and high_val >= tp1_price:
                            tp1_hit = True
                            pnl_d_tp1 = self.config['TP1_PCT'] / 2
                            current_sl_d = entry_price

                        if tp1_hit and not tp2_hit and high_val >= tp2_price:
                            tp2_hit = True
                            pnl_d_tp2 = self.config['TP2_PCT'] / 2
                            exit_price_d = tp2_price
                            exit_dt_d = row['datetime']
                            exit_reason_d = f"TP2 hit @ {tp2_price:.6f}"
                            break

                        if low_val <= current_sl_d:
                            exit_price_d = current_sl_d
                            exit_dt_d = row['datetime']
                            if tp1_hit:
                                exit_reason_d = f"Breakeven SL @ {current_sl_d:.6f}"
                                pnl_d_tp2 = 0
                            else:
                                exit_reason_d = f"SL initial @ {current_sl_d:.6f}"
                                pnl_d_tp1 = -self.config['SL_PCT'] / 2
                                pnl_d_tp2 = -self.config['SL_PCT'] / 2
                            break

                    if exit_price_d is None:
                        exit_price_d = df_1h.iloc[-1]['close']
                        exit_dt_d = df_1h.iloc[-1]['datetime']
                        if tp1_hit:
                            remaining_pnl = (exit_price_d - entry_price) / entry_price * 100 / 2
                            pnl_d_tp2 = remaining_pnl
                            exit_reason_d = f"TP1 hit, 50% restant ouvert @ {exit_price_d:.6f}"
                        else:
                            current_pnl = (exit_price_d - entry_price) / entry_price * 100
                            pnl_d_tp1 = current_pnl / 2
                            pnl_d_tp2 = current_pnl / 2
                            exit_reason_d = f"Position ouverte @ {exit_price_d:.6f}"

                    pnl_d = pnl_d_tp1 + pnl_d_tp2

                    # Post-SL Recovery Analysis
                    # Track price movement after SL hit to identify "false stop-outs"
                    sl_then_recovered = False
                    post_sl_max_price = None
                    post_sl_max_gain_pct = None
                    post_sl_fib_levels = {}
                    post_sl_monitoring_hours = None
                    post_sl_would_have_won = False

                    # Check if trade exited on initial SL (not trailing)
                    hit_initial_sl = pnl_c < 0 and not trailing_active

                    if hit_initial_sl and exit_dt_c:
                        # Find exit index
                        exit_idx = None
                        for idx, row in df_1h.iterrows():
                            if row['datetime'] >= exit_dt_c:
                                exit_idx = idx
                                break

                        if exit_idx:
                            # Monitor price for 72 hours (or until end of data)
                            # Start from 0 to track actual max high after SL
                            post_sl_high = 0.0
                            post_sl_end_dt = exit_dt_c + timedelta(hours=72)
                            monitoring_end_dt = exit_dt_c

                            for idx in range(exit_idx + 1, len(df_1h)):
                                row = df_1h.iloc[idx]
                                if row['datetime'] > post_sl_end_dt:
                                    break

                                monitoring_end_dt = row['datetime']
                                if row['high'] > post_sl_high:
                                    post_sl_high = row['high']

                            # If we found at least one candle after SL
                            if post_sl_high > 0:
                                post_sl_max_price = post_sl_high
                                post_sl_max_gain_pct = (post_sl_high - entry_price) / entry_price * 100
                                post_sl_monitoring_hours = (monitoring_end_dt - exit_dt_c).total_seconds() / 3600

                                # Check if price recovered above entry (with 0.5% tolerance)
                                recovery_threshold = entry_price * 1.005
                                sl_then_recovered = post_sl_max_price > recovery_threshold

                                # Would have won if price reached at least TP1
                                post_sl_would_have_won = post_sl_max_price >= tp1_price
                            else:
                                # No candles after SL (end of data)
                                post_sl_max_price = None
                                post_sl_max_gain_pct = None
                                post_sl_monitoring_hours = 0.0

                            # Check Fibonacci levels after SL (only if we have post-SL data)
                            if post_sl_max_price is not None:
                                # Get Fibonacci data (from entry point analysis)
                                fib_levels_at_entry = mb['entry_point']['progressive'].get('fib_levels', {})
                                for level_key, level_data in fib_levels_at_entry.items():
                                    fib_price = level_data.get('price', 0)
                                    was_broken_before_sl = level_data.get('break', False)
                                    broken_after_sl = post_sl_max_price >= fib_price if fib_price > 0 else False

                                    post_sl_fib_levels[level_key] = {
                                        'price': fib_price,
                                        'broken_before_sl': was_broken_before_sl,
                                        'broken_after_sl': broken_after_sl,
                                        'post_sl_max': post_sl_max_price
                                    }

                    # Create trade record
                    trade = Trade(
                        backtest_run_id=backtest_run.id,
                        alert_id=alert.id,
                        alert_datetime=mb['datetime'],
                        timeframe=mb['tf'],
                        alert_price=alert_price,
                        entry_datetime=entry_dt,
                        entry_price=entry_price,
                        sl_price=sl_price,
                        tp1_price=tp1_price,
                        tp2_price=tp2_price,
                        trailing_activation_price=trailing_activation_price,
                        highest_price=highest_price,
                        trailing_active=trailing_active,
                        trailing_sl=trailing_sl,
                        exit_datetime_c=exit_dt_c,
                        exit_price_c=exit_price_c,
                        exit_reason_c=exit_reason_c,
                        pnl_c=pnl_c,
                        tp1_hit=tp1_hit,
                        tp2_hit=tp2_hit,
                        exit_datetime_d=exit_dt_d,
                        exit_price_d=exit_price_d,
                        exit_reason_d=exit_reason_d,
                        pnl_d_tp1=pnl_d_tp1,
                        pnl_d_tp2=pnl_d_tp2,
                        pnl_d=pnl_d,
                        # Post-SL Recovery Analysis
                        sl_then_recovered=sl_then_recovered,
                        post_sl_max_price=post_sl_max_price,
                        post_sl_max_gain_pct=post_sl_max_gain_pct,
                        post_sl_fib_levels=convert_to_json_serializable(post_sl_fib_levels) if post_sl_fib_levels else None,
                        post_sl_monitoring_hours=post_sl_monitoring_hours,
                        post_sl_would_have_won=post_sl_would_have_won
                    )
                    db.add(trade)

                    # Only count P&L once for combined entries
                    if not is_duplicate_entry:
                        total_pnl_c += pnl_c
                        total_pnl_d += pnl_d
                        trades_count += 1

            # Update backtest run with stats
            backtest_run.total_alerts = stats['total_alerts']
            backtest_run.stc_validated = stats['stc_validated']
            backtest_run.rejected_15m_alone = stats['rejected_15m_alone']
            backtest_run.rejected_pp_buy = stats['rejected_pp_buy']
            backtest_run.valid_combos = stats['valid_combos']
            backtest_run.with_tl_break = stats['with_tl_break']
            backtest_run.delay_respected = stats['delay_respected']
            backtest_run.delay_exceeded = stats['delay_exceeded']
            backtest_run.expired = stats['expired']
            backtest_run.waiting = stats['waiting']
            backtest_run.valid_entries = stats['valid_entries']
            backtest_run.no_entry = stats['no_entry']
            backtest_run.total_trades = trades_count
            backtest_run.pnl_strategy_c = total_pnl_c
            backtest_run.pnl_strategy_d = total_pnl_d
            backtest_run.avg_pnl_c = total_pnl_c / trades_count if trades_count > 0 else 0
            backtest_run.avg_pnl_d = total_pnl_d / trades_count if trades_count > 0 else 0

            db.commit()

            if progress_callback:
                progress_callback(f"Backtest complete! {trades_count} trades, P&L C: {total_pnl_c:.2f}%, P&L D: {total_pnl_d:.2f}%")

            return backtest_run.id

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()


if __name__ == "__main__":
    engine = BacktestEngine()

    def progress(msg):
        print(msg)

    # Test with ENSOUSDT
    run_id = engine.run_backtest("ENSOUSDT", "2026-02-01", "2026-02-24", progress)
    print(f"Backtest run ID: {run_id}")
