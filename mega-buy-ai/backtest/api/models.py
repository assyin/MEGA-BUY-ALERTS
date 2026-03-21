"""
Database Models for MEGA BUY Backtest System
"""
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.pool import StaticPool
from datetime import datetime
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_PATH = os.path.join(BASE_DIR, 'data', 'backtest.db')

# Use StaticPool for SQLite to handle concurrent access better
engine = create_engine(
    f'sqlite:///{DATABASE_PATH}',
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BacktestRun(Base):
    """A complete backtest run for a symbol"""
    __tablename__ = 'backtest_runs'

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Summary stats
    total_alerts = Column(Integer, default=0)
    stc_validated = Column(Integer, default=0)
    rejected_15m_alone = Column(Integer, default=0)
    rejected_pp_buy = Column(Integer, default=0)
    valid_combos = Column(Integer, default=0)
    with_tl_break = Column(Integer, default=0)
    delay_respected = Column(Integer, default=0)
    delay_exceeded = Column(Integer, default=0)
    expired = Column(Integer, default=0)
    waiting = Column(Integer, default=0)
    valid_entries = Column(Integer, default=0)
    no_entry = Column(Integer, default=0)

    # P&L Summary
    total_trades = Column(Integer, default=0)
    pnl_strategy_c = Column(Float, default=0.0)
    pnl_strategy_d = Column(Float, default=0.0)
    avg_pnl_c = Column(Float, default=0.0)
    avg_pnl_d = Column(Float, default=0.0)

    # Configuration used
    config = Column(JSON)

    # Strategy Version (v1 = legacy, v2 = optimized)
    strategy_version = Column(String(10), default='v1')

    # V2 Rejection Stats
    v2_rejected_count = Column(Integer, default=0)
    v2_rejection_reasons = Column(JSON, default=dict)

    # V3 Golden Box Retest Stats
    v3_entries_found = Column(Integer, default=0)           # Number of V3 retest entries found
    v3_rejected_count = Column(Integer, default=0)          # Number of V3 entries rejected
    v3_rejection_reasons = Column(JSON, default=dict)       # V3 rejection reasons breakdown
    v3_avg_hours_to_entry = Column(Float, default=0.0)      # Average hours to V3 entry
    v3_avg_sl_distance = Column(Float, default=0.0)         # Average SL distance %
    v3_avg_quality_score = Column(Float, default=0.0)       # Average V3 quality score

    # V4 Optimized Strategy Stats
    v4_entries_found = Column(Integer, default=0)           # Number of V4 entries that passed all filters
    v4_rejected_count = Column(Integer, default=0)          # Number of V4 entries rejected
    v4_rejection_reasons = Column(JSON, default=dict)       # V4 rejection reasons breakdown
    v4_avg_score = Column(Float, default=0.0)               # Average V4 optimization score
    v4_blacklist_rejected = Column(Integer, default=0)      # Number rejected due to blacklist

    # Relationships
    alerts = relationship("Alert", back_populates="backtest_run", cascade="all, delete-orphan")
    trades = relationship("Trade", back_populates="backtest_run", cascade="all, delete-orphan")


class Alert(Base):
    """Individual MEGA BUY alert"""
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey('backtest_runs.id'))

    # Alert info
    alert_datetime = Column(DateTime)
    timeframe = Column(String(10))
    price_open = Column(Float)
    price_high = Column(Float)
    price_low = Column(Float)
    price_close = Column(Float)
    volume = Column(Float)

    # Score
    score = Column(Integer)

    # Conditions (JSON for flexibility)
    conditions = Column(JSON)

    # Indicators per TF
    indicators_15m = Column(JSON)
    indicators_30m = Column(JSON)
    indicators_1h = Column(JSON)

    # Full MEGA BUY indicator details for all timeframes (15m, 30m, 1h, 4h)
    # Structure: {
    #   "dmi": {"15m": {"di_plus_move": x, "di_minus_move": x, "adx_move": x, "di_plus": x, "di_minus": x, "adx": x}, ...},
    #   "rsi": {"15m": {"rsi_move": x, "rsi_value": x, "rsi_signal": x}, ...},
    #   "volume": {"15m": {"vol_pct": x}, ...},
    #   "lazybar": {"15m": {"lz_value": x, "lz_color": "Orange", "lz_move": "🟣"}, ...},
    #   "ec": {"15m": {"ec_move": x}, ...}
    # }
    mega_buy_details = Column(JSON)

    # Filter results
    stc_validated = Column(Boolean, default=False)
    stc_valid_tfs = Column(String(50))
    is_15m_alone = Column(Boolean, default=False)
    combo_tfs = Column(String(50))

    # Trendline info
    has_trendline = Column(Boolean, default=False)
    tl_type = Column(String(20))
    tl_price_at_alert = Column(Float)
    tl_p1_date = Column(DateTime)
    tl_p1_price = Column(Float)
    tl_p2_date = Column(DateTime)
    tl_p2_price = Column(Float)

    # TL Break info
    has_tl_break = Column(Boolean, default=False)
    tl_break_datetime = Column(DateTime)
    tl_break_price = Column(Float)
    tl_break_delay_hours = Column(Float)
    tl_retest_count = Column(Integer, default=0)  # Number of times TL was retested before break
    tl_prior_false_breaks = Column(Integer, default=0)  # Number of prior false breaks (price crossed above TL then fell below)
    delay_exceeded = Column(Boolean, default=False)

    # Progressive conditions at entry - Indicator VALUES
    prog_ema100_1h = Column(Float)
    prog_ema20_4h = Column(Float)
    prog_cloud_1h = Column(Float)
    prog_cloud_30m = Column(Float)
    prog_choch_bos_datetime = Column(DateTime)
    prog_choch_bos_sh_price = Column(Float)

    # Progressive conditions - PRICE VALUES used for checks
    prog_price_1h = Column(Float)  # 1H close at entry time
    prog_price_30m = Column(Float)  # 30m close at entry time
    prog_price_4h = Column(Float)  # 4H close at entry time

    # Progressive conditions - VALIDATION RESULTS (True/False)
    prog_valid_ema100_1h = Column(Boolean, default=False)  # price_1h > ema100_1h
    prog_valid_ema20_4h = Column(Boolean, default=False)   # price_4h > ema20_4h
    prog_valid_cloud_1h = Column(Boolean, default=False)   # price_1h > cloud_1h
    prog_valid_cloud_30m = Column(Boolean, default=False)  # price_30m > cloud_30m
    prog_choch_bos_valid = Column(Boolean, default=False)  # CHoCH/BOS detected

    # Fibonacci BONUS on 4H (not required for entry, improves scoring)
    fib_bonus = Column(Boolean, default=False)  # price_4h > fib 38.2%
    fib_swing_high = Column(Float)              # Swing high used for Fib calc (4H)
    fib_swing_low = Column(Float)               # Swing low used for Fib calc (4H)
    fib_levels = Column(JSON)                   # All Fib levels 4H with break status

    # Fibonacci on 1H
    fib_swing_high_1h = Column(Float)           # Swing high used for Fib calc (1H)
    fib_swing_low_1h = Column(Float)            # Swing low used for Fib calc (1H)
    fib_levels_1h = Column(JSON)                # All Fib levels 1H with break status

    # Order Block BONUS (SMC - Smart Money Concepts) - 1H
    ob_bonus = Column(Boolean, default=False)   # Entry near a bullish Order Block (1H)?
    ob_zone_high = Column(Float)                # OB zone high price (1H)
    ob_zone_low = Column(Float)                 # OB zone low price (1H)
    ob_datetime = Column(DateTime)              # When the OB was created (1H)
    ob_distance_pct = Column(Float)             # Distance from entry to OB zone (1H)
    ob_position = Column(String(10))            # INSIDE, ABOVE, BELOW (1H)
    ob_strength = Column(String(10))            # STRONG, MODERATE, WEAK (1H)
    ob_impulse_pct = Column(Float)              # Impulse move % that created the OB (1H)
    ob_age_bars = Column(Integer)               # Age of OB in bars (1H)
    ob_mitigated = Column(Boolean)              # Has OB been tested already? (1H)
    ob_data = Column(JSON)                      # Full OB data for display (1H)

    # Order Block BONUS (SMC) - 4H
    ob_bonus_4h = Column(Boolean, default=False)   # Entry near a bullish Order Block (4H)?
    ob_zone_high_4h = Column(Float)                # OB zone high price (4H)
    ob_zone_low_4h = Column(Float)                 # OB zone low price (4H)
    ob_datetime_4h = Column(DateTime)              # When the OB was created (4H)
    ob_distance_pct_4h = Column(Float)             # Distance from entry to OB zone (4H)
    ob_position_4h = Column(String(10))            # INSIDE, ABOVE, BELOW (4H)
    ob_strength_4h = Column(String(10))            # STRONG, MODERATE, WEAK (4H)
    ob_impulse_pct_4h = Column(Float)              # Impulse move % that created the OB (4H)
    ob_age_bars_4h = Column(Integer)               # Age of OB in bars (4H)
    ob_mitigated_4h = Column(Boolean)              # Has OB been tested already? (4H)
    ob_data_4h = Column(JSON)                      # Full OB data for display (4H)

    # BTC Correlation BONUS - 1H
    btc_corr_bonus_1h = Column(Boolean, default=False)  # BTC bullish on 1H at entry?
    btc_price_1h = Column(Float)                        # BTC price at entry (1H)
    btc_ema20_1h = Column(Float)                        # BTC EMA20 value (1H)
    btc_ema50_1h = Column(Float)                        # BTC EMA50 value (1H)
    btc_rsi_1h = Column(Float)                          # BTC RSI value (1H)
    btc_trend_1h = Column(String(10))                   # BULLISH, BEARISH, NEUTRAL (1H)

    # BTC Correlation BONUS - 4H
    btc_corr_bonus_4h = Column(Boolean, default=False)  # BTC bullish on 4H at entry?
    btc_price_4h = Column(Float)                        # BTC price at entry (4H)
    btc_ema20_4h = Column(Float)                        # BTC EMA20 value (4H)
    btc_ema50_4h = Column(Float)                        # BTC EMA50 value (4H)
    btc_rsi_4h = Column(Float)                          # BTC RSI value (4H)
    btc_trend_4h = Column(String(10))                   # BULLISH, BEARISH, NEUTRAL (4H)

    # ETH Correlation BONUS - 1H
    eth_corr_bonus_1h = Column(Boolean, default=False)  # ETH bullish on 1H at entry?
    eth_price_1h = Column(Float)                        # ETH price at entry (1H)
    eth_ema20_1h = Column(Float)                        # ETH EMA20 value (1H)
    eth_ema50_1h = Column(Float)                        # ETH EMA50 value (1H)
    eth_rsi_1h = Column(Float)                          # ETH RSI value (1H)
    eth_trend_1h = Column(String(10))                   # BULLISH, BEARISH, NEUTRAL (1H)

    # ETH Correlation BONUS - 4H
    eth_corr_bonus_4h = Column(Boolean, default=False)  # ETH bullish on 4H at entry?
    eth_price_4h = Column(Float)                        # ETH price at entry (4H)
    eth_ema20_4h = Column(Float)                        # ETH EMA20 value (4H)
    eth_ema50_4h = Column(Float)                        # ETH EMA50 value (4H)
    eth_rsi_4h = Column(Float)                          # ETH RSI value (4H)
    eth_trend_4h = Column(String(10))                   # BULLISH, BEARISH, NEUTRAL (4H)

    # Fair Value Gap (FVG) BONUS - 1H
    fvg_bonus_1h = Column(Boolean, default=False)       # Entry near/inside a bullish FVG (1H)?
    fvg_zone_high_1h = Column(Float)                    # FVG zone high price (1H)
    fvg_zone_low_1h = Column(Float)                     # FVG zone low price (1H)
    fvg_datetime_1h = Column(DateTime)                  # When the FVG was created (1H)
    fvg_distance_pct_1h = Column(Float)                 # Distance from entry to FVG zone (1H)
    fvg_position_1h = Column(String(10))                # INSIDE, ABOVE, BELOW (1H)
    fvg_filled_pct_1h = Column(Float)                   # How much of the FVG has been filled (1H)
    fvg_size_pct_1h = Column(Float)                     # Size of FVG as % of price (1H)
    fvg_age_bars_1h = Column(Integer)                   # Age of FVG in bars (1H)
    fvg_data_1h = Column(JSON)                          # Full FVG data for display (1H)

    # Fair Value Gap (FVG) BONUS - 4H
    fvg_bonus_4h = Column(Boolean, default=False)       # Entry near/inside a bullish FVG (4H)?
    fvg_zone_high_4h = Column(Float)                    # FVG zone high price (4H)
    fvg_zone_low_4h = Column(Float)                     # FVG zone low price (4H)
    fvg_datetime_4h = Column(DateTime)                  # When the FVG was created (4H)
    fvg_distance_pct_4h = Column(Float)                 # Distance from entry to FVG zone (4H)
    fvg_position_4h = Column(String(10))                # INSIDE, ABOVE, BELOW (4H)
    fvg_filled_pct_4h = Column(Float)                   # How much of the FVG has been filled (4H)
    fvg_size_pct_4h = Column(Float)                     # Size of FVG as % of price (4H)
    fvg_age_bars_4h = Column(Integer)                   # Age of FVG in bars (4H)
    fvg_data_4h = Column(JSON)                          # Full FVG data for display (4H)

    # Volume Spike BONUS - 1H
    vol_spike_bonus_1h = Column(Boolean, default=False)  # Volume > 2x average on 1H?
    vol_current_1h = Column(Float)                       # Current volume at entry (1H)
    vol_avg_1h = Column(Float)                           # Average volume 20 bars (1H)
    vol_ratio_1h = Column(Float)                         # Ratio: current / average (1H)
    vol_spike_level_1h = Column(String(10))              # NORMAL, HIGH (>2x), VERY_HIGH (>3x)

    # Volume Spike BONUS - 4H
    vol_spike_bonus_4h = Column(Boolean, default=False)  # Volume > 2x average on 4H?
    vol_current_4h = Column(Float)                       # Current volume at entry (4H)
    vol_avg_4h = Column(Float)                           # Average volume 20 bars (4H)
    vol_ratio_4h = Column(Float)                         # Ratio: current / average (4H)
    vol_spike_level_4h = Column(String(10))              # NORMAL, HIGH (>2x), VERY_HIGH (>3x)

    # RSI Multi-TF Alignment BONUS
    rsi_mtf_bonus = Column(Boolean, default=False)       # RSI > 50 on all TFs (1H, 4H, Daily)?
    rsi_1h = Column(Float)                               # RSI value on 1H at entry
    rsi_4h = Column(Float)                               # RSI value on 4H at entry
    rsi_daily = Column(Float)                            # RSI value on Daily at entry
    rsi_aligned_count = Column(Integer)                  # How many TFs have RSI > 50 (0-3)
    rsi_mtf_trend = Column(String(10))                   # BULLISH (3/3), MIXED, BEARISH (0/3)

    # ADX Trend Strength BONUS - 1H
    adx_bonus_1h = Column(Boolean, default=False)        # ADX > 25 = Strong trend (1H)?
    adx_value_1h = Column(Float)                         # ADX value at entry (1H)
    adx_plus_di_1h = Column(Float)                       # +DI value at entry (1H)
    adx_minus_di_1h = Column(Float)                      # -DI value at entry (1H)
    adx_strength_1h = Column(String(12))                 # STRONG (>25), MODERATE (20-25), WEAK (<20)

    # ADX Trend Strength BONUS - 4H
    adx_bonus_4h = Column(Boolean, default=False)        # ADX > 25 = Strong trend (4H)?
    adx_value_4h = Column(Float)                         # ADX value at entry (4H)
    adx_plus_di_4h = Column(Float)                       # +DI value at entry (4H)
    adx_minus_di_4h = Column(Float)                      # -DI value at entry (4H)
    adx_strength_4h = Column(String(12))                 # STRONG (>25), MODERATE (20-25), WEAK (<20)

    # MACD Momentum BONUS - 1H
    macd_bonus_1h = Column(Boolean, default=False)       # Histogram > 0 AND growing (1H)?
    macd_line_1h = Column(Float)                         # MACD line value (1H)
    macd_signal_1h = Column(Float)                       # Signal line value (1H)
    macd_histogram_1h = Column(Float)                    # Histogram value (1H)
    macd_hist_growing_1h = Column(Boolean)               # Histogram growing? (1H)
    macd_trend_1h = Column(String(12))                   # BULLISH, BEARISH, NEUTRAL

    # MACD Momentum BONUS - 4H
    macd_bonus_4h = Column(Boolean, default=False)       # Histogram > 0 AND growing (4H)?
    macd_line_4h = Column(Float)                         # MACD line value (4H)
    macd_signal_4h = Column(Float)                       # Signal line value (4H)
    macd_histogram_4h = Column(Float)                    # Histogram value (4H)
    macd_hist_growing_4h = Column(Boolean)               # Histogram growing? (4H)
    macd_trend_4h = Column(String(12))                   # BULLISH, BEARISH, NEUTRAL

    # Bollinger Squeeze BONUS - 1H
    bb_squeeze_bonus_1h = Column(Boolean, default=False) # Squeeze detected + breakout (1H)?
    bb_upper_1h = Column(Float)                          # Upper band (1H)
    bb_middle_1h = Column(Float)                         # Middle band / SMA20 (1H)
    bb_lower_1h = Column(Float)                          # Lower band (1H)
    bb_width_pct_1h = Column(Float)                      # Band width as % of price (1H)
    bb_squeeze_1h = Column(Boolean)                      # Bands tight? (1H)
    bb_breakout_1h = Column(String(12))                  # UP, DOWN, NONE

    # Bollinger Squeeze BONUS - 4H
    bb_squeeze_bonus_4h = Column(Boolean, default=False) # Squeeze detected + breakout (4H)?
    bb_upper_4h = Column(Float)                          # Upper band (4H)
    bb_middle_4h = Column(Float)                         # Middle band / SMA20 (4H)
    bb_lower_4h = Column(Float)                          # Lower band (4H)
    bb_width_pct_4h = Column(Float)                      # Band width as % of price (4H)
    bb_squeeze_4h = Column(Boolean)                      # Bands tight? (4H)
    bb_breakout_4h = Column(String(12))                  # UP, DOWN, NONE

    # Stochastic RSI BONUS - 1H
    stoch_rsi_bonus_1h = Column(Boolean, default=False)  # K > D crossover in oversold zone (1H)?
    stoch_rsi_k_1h = Column(Float)                       # %K value (1H)
    stoch_rsi_d_1h = Column(Float)                       # %D value (1H)
    stoch_rsi_zone_1h = Column(String(12))               # OVERSOLD (<20), OVERBOUGHT (>80), NEUTRAL
    stoch_rsi_cross_1h = Column(String(12))              # BULLISH (K>D), BEARISH (K<D), NONE

    # Stochastic RSI BONUS - 4H
    stoch_rsi_bonus_4h = Column(Boolean, default=False)  # K > D crossover in oversold zone (4H)?
    stoch_rsi_k_4h = Column(Float)                       # %K value (4H)
    stoch_rsi_d_4h = Column(Float)                       # %D value (4H)
    stoch_rsi_zone_4h = Column(String(12))               # OVERSOLD (<20), OVERBOUGHT (>80), NEUTRAL
    stoch_rsi_cross_4h = Column(String(12))              # BULLISH (K>D), BEARISH (K<D), NONE

    # EMA Stack BONUS - 1H
    ema_stack_bonus_1h = Column(Boolean, default=False)  # EMA8 > EMA21 > EMA50 > EMA100 (1H)?
    ema8_1h = Column(Float)                              # EMA8 value (1H)
    ema21_1h = Column(Float)                             # EMA21 value (1H)
    ema50_1h = Column(Float)                             # EMA50 value (1H)
    ema100_1h_stack = Column(Float)                      # EMA100 value for stack (1H)
    ema_stack_count_1h = Column(Integer)                 # How many EMAs are stacked (0-3)
    ema_stack_trend_1h = Column(String(12))              # PERFECT, PARTIAL, INVERSE

    # EMA Stack BONUS - 4H
    ema_stack_bonus_4h = Column(Boolean, default=False)  # EMA8 > EMA21 > EMA50 > EMA100 (4H)?
    ema8_4h = Column(Float)                              # EMA8 value (4H)
    ema21_4h = Column(Float)                             # EMA21 value (4H)
    ema50_4h = Column(Float)                             # EMA50 value (4H)
    ema100_4h_stack = Column(Float)                      # EMA100 value for stack (4H)
    ema_stack_count_4h = Column(Integer)                 # How many EMAs are stacked (0-3)
    ema_stack_trend_4h = Column(String(12))              # PERFECT, PARTIAL, INVERSE

    # Entry point
    has_entry = Column(Boolean, default=False)
    entry_datetime = Column(DateTime)
    entry_price = Column(Float)
    entry_diff_vs_alert = Column(Float)
    entry_diff_vs_break = Column(Float)

    # Final status
    status = Column(String(50))  # VALID, REJECTED_STC, REJECTED_15M_ALONE, REJECTED_NO_TL, REJECTED_DELAY, REJECTED_NO_ENTRY, WAITING, EXPIRED

    # V2 Optimization Score
    trade_score = Column(Integer)  # Calculated trade quality score
    v2_rejected = Column(Boolean, default=False)  # Was rejected by V2 filters
    v2_rejection_reason = Column(String(50))  # Specific V2 rejection reason

    # ═══════════════════════════════════════════════════════════════════════════════
    # V3 GOLDEN BOX RETEST STRATEGY
    # Entry via limit order at Box High, wait for price retest after breakout
    # ═══════════════════════════════════════════════════════════════════════════════
    v3_entry_found = Column(Boolean, default=False)      # V3 retest entry found?
    v3_entry_datetime = Column(DateTime)                  # V3 entry datetime
    v3_entry_price = Column(Float)                        # V3 entry price (Box High + margin)
    v3_sl_price = Column(Float)                           # V3 stop loss (Box Low - margin)
    v3_box_high = Column(Float)                           # Golden Box High (signal candle high)
    v3_box_low = Column(Float)                            # Golden Box Low (signal candle low)
    v3_box_range_pct = Column(Float)                      # Box range as % of price
    v3_hours_to_entry = Column(Float)                     # Hours from signal to entry
    v3_sl_distance_pct = Column(Float)                    # SL distance from entry as %
    v3_quality_score = Column(Integer)                    # V3 entry quality score
    v3_breakout_dt = Column(DateTime)                     # When price broke above Box High
    v3_breakout_high = Column(Float)                      # Highest price before retest
    v3_distance_before_retest = Column(Float)             # Price distance before retest
    v3_rejected = Column(Boolean, default=False)          # Was rejected by V3 validation
    v3_rejection_reason = Column(String(50))              # V3 rejection reason

    # V3 Progressive conditions at retest time (must be 5/5)
    v3_prog_valid_ema100_1h = Column(Boolean, default=False)   # price > ema100_1h at retest
    v3_prog_valid_ema20_4h = Column(Boolean, default=False)    # price > ema20_4h at retest
    v3_prog_valid_cloud_1h = Column(Boolean, default=False)    # price > cloud_1h at retest
    v3_prog_valid_cloud_30m = Column(Boolean, default=False)   # price > cloud_30m at retest
    v3_prog_choch_bos_valid = Column(Boolean, default=False)   # CHoCH/BOS valid at retest
    v3_prog_count = Column(Integer, default=0)                 # Count of valid progressive conditions (0-5)
    v3_prog_ema100_1h_val = Column(Float)                      # EMA100 value at retest
    v3_prog_ema20_4h_val = Column(Float)                       # EMA20 4H value at retest
    v3_prog_cloud_1h_val = Column(Float)                       # Cloud 1H value at retest
    v3_prog_cloud_30m_val = Column(Float)                      # Cloud 30m value at retest
    v3_retest_price = Column(Float)                            # Exact retest price (low touching box_high)
    v3_retest_datetime = Column(DateTime)                      # Exact retest datetime
    v3_retest_vs_tl_break = Column(String(20))                 # 'BEFORE_TL', 'AFTER_TL', 'NO_TL_BREAK'
    v3_tl_break_datetime = Column(DateTime)                    # TL break datetime for reference
    v3_hours_retest_vs_tl = Column(Float)                      # Hours between retest and TL break (negative = before)

    # ═══════════════════════════════════════════════════════════════════════════════
    # GB POWER SCORE - Score de puissance du Golden Box (0-100)
    # Combine tous les indicateurs pour mesurer la force du setup
    # ═══════════════════════════════════════════════════════════════════════════════
    gb_power_score = Column(Integer)                           # Score total 0-100
    gb_power_grade = Column(String(1))                         # A, B, C, D, F

    # V3 RISK INDICATORS - Alertes de risque basées sur l'analyse statistique
    v3_risk_level = Column(String(10))                         # LOW, MEDIUM, HIGH, CRITICAL
    v3_risk_score = Column(Integer)                            # Score de risque 0-100 (100 = très risqué)
    v3_risk_reasons = Column(JSON)                             # Liste des raisons du risque

    # ═══════════════════════════════════════════════════════════════════════════════
    # V4 OPTIMIZED STRATEGY - Based on backtest analysis
    # Improves WR from 31.9% to 50.7%, P&L from +303% to +558%
    # ═══════════════════════════════════════════════════════════════════════════════
    v4_score = Column(Integer)                                 # V4 optimization score (0-100)
    v4_grade = Column(String(2))                               # A+, A, B+, B, C, D
    v4_rejected = Column(Boolean, default=False)               # Was rejected by V4 filters
    v4_rejection_reason = Column(String(50))                   # V4 rejection reason

    # Component scores (0-100 each, weighted for final)
    gb_volume_score = Column(Integer)                          # Volume breakout strength (0-100)
    gb_adx_score = Column(Integer)                             # ADX trend strength (0-100)
    gb_ema_alignment_score = Column(Integer)                   # EMA stack alignment (0-100)
    gb_macd_momentum_score = Column(Integer)                   # MACD momentum (0-100)
    gb_fib_position_score = Column(Integer)                    # Fibonacci position (0-100)
    gb_retest_quality_score = Column(Integer)                  # Retest precision (V3) (0-100)
    gb_dmi_spread_score = Column(Integer)                      # DMI+ - DMI- spread (0-100)
    gb_rsi_strength_score = Column(Integer)                    # RSI multi-TF strength (0-100)
    gb_btc_correlation_score = Column(Integer)                 # BTC correlation bonus (0-100)
    gb_confluence_score = Column(Integer)                      # Overall confluence (0-100)

    # Additional power metrics
    gb_dmi_spread = Column(Float)                              # DMI+ - DMI- value
    gb_box_consolidation_bars = Column(Integer)                # Bars in consolidation zone
    gb_breakout_strength_pct = Column(Float)                   # % move on breakout candle

    # ============================================
    # CVD (Cumulative Volume Delta) BONUS
    # ============================================
    # CVD measures buying vs selling pressure
    # Positive CVD = more buyers, Negative = more sellers

    cvd_bonus = Column(Boolean, default=False)                 # Overall CVD confirms entry?
    cvd_score = Column(Integer)                                # CVD score (0-100)
    cvd_label = Column(String(50))                             # Human readable: "STRONG BUY", "WEAK", etc.
    cvd_description = Column(String(200))                      # Detailed explanation

    # CVD at TL Break moment
    cvd_at_break = Column(Float)                               # CVD value at TL break
    cvd_at_break_trend = Column(String(12))                    # RISING, FALLING, FLAT
    cvd_at_break_signal = Column(String(20))                   # BULLISH, BEARISH, NEUTRAL

    # CVD at Breakout moment (Box High break)
    cvd_at_breakout = Column(Float)                            # CVD value at breakout
    cvd_at_breakout_spike = Column(Boolean)                    # Volume spike detected?
    cvd_at_breakout_signal = Column(String(20))                # STRONG_BUY, BUY, NEUTRAL, SELL

    # CVD at Retest moment
    cvd_at_retest = Column(Float)                              # CVD value at retest
    cvd_at_retest_trend = Column(String(12))                   # RISING, FALLING, FLAT
    cvd_at_retest_signal = Column(String(20))                  # ACCUMULATION, DISTRIBUTION, NEUTRAL

    # CVD at Entry moment
    cvd_at_entry = Column(Float)                               # CVD value at entry
    cvd_at_entry_trend = Column(String(12))                    # RISING, FALLING, FLAT
    cvd_at_entry_signal = Column(String(20))                   # CONFIRMED, WARNING, DANGER

    # CVD Divergence detection
    cvd_divergence = Column(Boolean, default=False)            # Price up but CVD down?
    cvd_divergence_type = Column(String(20))                   # BULLISH, BEARISH, NONE

    # Volume analysis at key moments (1H)
    vol_at_break_ratio = Column(Float)                         # Volume / Avg volume at break
    vol_at_breakout_ratio = Column(Float)                      # Volume / Avg volume at breakout
    vol_at_retest_ratio = Column(Float)                        # Volume / Avg volume at retest
    vol_at_entry_ratio = Column(Float)                         # Volume / Avg volume at entry

    # ========== CVD 4H (Cumulative Volume Delta - 4H timeframe) ==========
    # Same analysis as CVD 1H but on 4H timeframe for smoother signals
    cvd_4h_bonus = Column(Boolean, default=False)              # Overall CVD 4H confirms entry?
    cvd_4h_score = Column(Integer)                             # CVD 4H score (0-100)
    cvd_4h_label = Column(String(50))                          # Human readable: "STRONG BUY", "WEAK", etc.
    cvd_4h_description = Column(String(200))                   # Detailed explanation

    # CVD 4H at TL Break moment
    cvd_4h_at_break = Column(Float)                            # CVD value at TL break
    cvd_4h_at_break_trend = Column(String(12))                 # RISING, FALLING, FLAT
    cvd_4h_at_break_signal = Column(String(20))                # BULLISH, BEARISH, NEUTRAL

    # CVD 4H at Breakout moment (Box High break)
    cvd_4h_at_breakout = Column(Float)                         # CVD value at breakout
    cvd_4h_at_breakout_spike = Column(Boolean)                 # Volume spike detected?
    cvd_4h_at_breakout_signal = Column(String(20))             # STRONG_BUY, BUY, NEUTRAL, SELL

    # CVD 4H at Retest moment
    cvd_4h_at_retest = Column(Float)                           # CVD value at retest
    cvd_4h_at_retest_trend = Column(String(12))                # RISING, FALLING, FLAT
    cvd_4h_at_retest_signal = Column(String(20))               # ACCUMULATION, DISTRIBUTION, NEUTRAL

    # CVD 4H at Entry moment
    cvd_4h_at_entry = Column(Float)                            # CVD value at entry
    cvd_4h_at_entry_trend = Column(String(12))                 # RISING, FALLING, FLAT
    cvd_4h_at_entry_signal = Column(String(20))                # CONFIRMED, WARNING, DANGER

    # CVD 4H Divergence detection
    cvd_4h_divergence = Column(Boolean, default=False)         # Price up but CVD down?
    cvd_4h_divergence_type = Column(String(20))                # BULLISH, BEARISH, NONE

    # Volume analysis at key moments (4H)
    vol_4h_at_break_ratio = Column(Float)                      # Volume / Avg volume at break
    vol_4h_at_breakout_ratio = Column(Float)                   # Volume / Avg volume at breakout
    vol_4h_at_retest_ratio = Column(Float)                     # Volume / Avg volume at retest
    vol_4h_at_entry_ratio = Column(Float)                      # Volume / Avg volume at entry

    # ========== ADX/DI Analysis (1H timeframe) ==========
    # ADX = Average Directional Index (trend strength)
    # DI+ = Positive Directional Indicator (bullish pressure)
    # DI- = Negative Directional Indicator (bearish pressure)
    adx_di_1h_bonus = Column(Boolean, default=False)           # Overall ADX/DI confirms entry?
    adx_di_1h_score = Column(Integer)                          # ADX/DI score (0-100)
    adx_di_1h_label = Column(String(50))                       # STRONG TREND, TREND, WEAK, RANGING

    # ADX/DI at TL Break moment (1H)
    adx_1h_at_break = Column(Float)                            # ADX value at TL break
    di_plus_1h_at_break = Column(Float)                        # DI+ value at TL break
    di_minus_1h_at_break = Column(Float)                       # DI- value at TL break
    di_spread_1h_at_break = Column(Float)                      # DI+ - DI- spread
    adx_di_1h_at_break_signal = Column(String(20))             # BULLISH, BEARISH, NEUTRAL

    # ADX/DI at Breakout moment (1H)
    adx_1h_at_breakout = Column(Float)                         # ADX value at breakout
    di_plus_1h_at_breakout = Column(Float)                     # DI+ value at breakout
    di_minus_1h_at_breakout = Column(Float)                    # DI- value at breakout
    di_spread_1h_at_breakout = Column(Float)                   # DI+ - DI- spread
    adx_di_1h_at_breakout_signal = Column(String(20))          # STRONG_BUY, BUY, NEUTRAL, SELL

    # ADX/DI at Retest moment (1H)
    adx_1h_at_retest = Column(Float)                           # ADX value at retest
    di_plus_1h_at_retest = Column(Float)                       # DI+ value at retest
    di_minus_1h_at_retest = Column(Float)                      # DI- value at retest
    di_spread_1h_at_retest = Column(Float)                     # DI+ - DI- spread
    adx_di_1h_at_retest_signal = Column(String(20))            # ACCUMULATION, DISTRIBUTION, NEUTRAL

    # ADX/DI at Entry moment (1H)
    adx_1h_at_entry = Column(Float)                            # ADX value at entry
    di_plus_1h_at_entry = Column(Float)                        # DI+ value at entry
    di_minus_1h_at_entry = Column(Float)                       # DI- value at entry
    di_spread_1h_at_entry = Column(Float)                      # DI+ - DI- spread
    adx_di_1h_at_entry_signal = Column(String(20))             # CONFIRMED, WARNING, DANGER

    # ADX/DI extreme zones (1H)
    di_plus_1h_overbought = Column(Boolean, default=False)     # DI+ > 60 (extreme bullish)
    di_minus_1h_oversold = Column(Boolean, default=False)      # DI- > 60 (extreme bearish)

    # ========== ADX/DI Analysis (4H timeframe) ==========
    adx_di_4h_bonus = Column(Boolean, default=False)           # Overall ADX/DI 4H confirms entry?
    adx_di_4h_score = Column(Integer)                          # ADX/DI 4H score (0-100)
    adx_di_4h_label = Column(String(50))                       # STRONG TREND, TREND, WEAK, RANGING

    # ADX/DI at TL Break moment (4H)
    adx_4h_at_break = Column(Float)                            # ADX value at TL break
    di_plus_4h_at_break = Column(Float)                        # DI+ value at TL break
    di_minus_4h_at_break = Column(Float)                       # DI- value at TL break
    di_spread_4h_at_break = Column(Float)                      # DI+ - DI- spread
    adx_di_4h_at_break_signal = Column(String(20))             # BULLISH, BEARISH, NEUTRAL

    # ADX/DI at Breakout moment (4H)
    adx_4h_at_breakout = Column(Float)                         # ADX value at breakout
    di_plus_4h_at_breakout = Column(Float)                     # DI+ value at breakout
    di_minus_4h_at_breakout = Column(Float)                    # DI- value at breakout
    di_spread_4h_at_breakout = Column(Float)                   # DI+ - DI- spread
    adx_di_4h_at_breakout_signal = Column(String(20))          # STRONG_BUY, BUY, NEUTRAL, SELL

    # ADX/DI at Retest moment (4H)
    adx_4h_at_retest = Column(Float)                           # ADX value at retest
    di_plus_4h_at_retest = Column(Float)                       # DI+ value at retest
    di_minus_4h_at_retest = Column(Float)                      # DI- value at retest
    di_spread_4h_at_retest = Column(Float)                     # DI+ - DI- spread
    adx_di_4h_at_retest_signal = Column(String(20))            # ACCUMULATION, DISTRIBUTION, NEUTRAL

    # ADX/DI at Entry moment (4H)
    adx_4h_at_entry = Column(Float)                            # ADX value at entry
    di_plus_4h_at_entry = Column(Float)                        # DI+ value at entry
    di_minus_4h_at_entry = Column(Float)                       # DI- value at entry
    di_spread_4h_at_entry = Column(Float)                      # DI+ - DI- spread
    adx_di_4h_at_entry_signal = Column(String(20))             # CONFIRMED, WARNING, DANGER

    # ADX/DI extreme zones (4H)
    di_plus_4h_overbought = Column(Boolean, default=False)     # DI+ > 60 (extreme bullish)
    di_minus_4h_oversold = Column(Boolean, default=False)      # DI- > 60 (extreme bearish)

    # ========== AI AGENT DECISION ==========
    # Meta-analysis combining all indicators into a single trade decision
    # The agent reads all indicators and decides whether to trade WITHOUT seeing P&L
    agent_decision = Column(String(20))                        # STRONG_BUY, BUY, HOLD, AVOID
    agent_confidence = Column(Integer)                         # 0-100% confidence
    agent_score = Column(Integer)                              # Overall score 0-100
    agent_grade = Column(String(2))                            # A+, A, B+, B, C, D, F

    # Agent analysis breakdown
    agent_bullish_count = Column(Integer)                      # Number of bullish signals
    agent_bearish_count = Column(Integer)                      # Number of bearish signals
    agent_neutral_count = Column(Integer)                      # Number of neutral signals

    # Key factors that influenced the decision
    agent_bullish_factors = Column(Text)                       # JSON list of bullish reasons
    agent_bearish_factors = Column(Text)                       # JSON list of bearish reasons
    agent_reasoning = Column(Text)                             # Full reasoning text

    # Individual component scores (0-100)
    agent_cvd_score = Column(Integer)                          # Combined CVD score
    agent_adx_score = Column(Integer)                          # Combined ADX/DI score
    agent_trend_score = Column(Integer)                        # Trend alignment score
    agent_momentum_score = Column(Integer)                     # Momentum score
    agent_volume_score = Column(Integer)                       # Volume confirmation score
    agent_confluence_score = Column(Integer)                   # Confluence of signals

    # ========== FOREIGN CANDLE ORDER BLOCK (SMC) ==========
    # Detects candles of opposite color within same-colored sequence
    # Red candle in green sequence = bullish demand zone (like CVXUSDT chart)

    # 1H Foreign Candle OB
    fc_ob_1h_found = Column(Boolean, default=False)            # OB detected on 1H
    fc_ob_1h_count = Column(Integer)                           # Number of OBs found
    fc_ob_1h_type = Column(String(10))                         # BULLISH or BEARISH
    fc_ob_1h_zone_high = Column(Float)                         # Top of OB zone
    fc_ob_1h_zone_low = Column(Float)                          # Bottom of OB zone
    fc_ob_1h_strength = Column(Integer)                        # Strength (surrounding candles)
    fc_ob_1h_retest = Column(Boolean, default=False)           # Price retested the OB
    fc_ob_1h_distance_pct = Column(Float)                      # Distance to OB zone %
    fc_ob_1h_datetime = Column(DateTime)                       # Datetime of the Foreign Candle
    fc_ob_1h_in_zone = Column(Integer, default=0)              # OBs in retest zone
    fc_ob_1h_retested = Column(Integer, default=0)             # OBs retested in zone

    # 4H Foreign Candle OB
    fc_ob_4h_found = Column(Boolean, default=False)            # OB detected on 4H
    fc_ob_4h_count = Column(Integer)                           # Number of OBs found
    fc_ob_4h_type = Column(String(10))                         # BULLISH or BEARISH
    fc_ob_4h_zone_high = Column(Float)                         # Top of OB zone
    fc_ob_4h_zone_low = Column(Float)                          # Bottom of OB zone
    fc_ob_4h_strength = Column(Integer)                        # Strength (surrounding candles)
    fc_ob_4h_retest = Column(Boolean, default=False)           # Price retested the OB
    fc_ob_4h_distance_pct = Column(Float)                      # Distance to OB zone %
    fc_ob_4h_datetime = Column(DateTime)                       # Datetime of the Foreign Candle
    fc_ob_4h_in_zone = Column(Integer, default=0)              # OBs in retest zone
    fc_ob_4h_retested = Column(Integer, default=0)             # OBs retested in zone

    # Combined Foreign Candle OB Analysis
    fc_ob_bonus = Column(Boolean, default=False)               # OB retest confirmed
    fc_ob_score = Column(Integer)                              # Combined score 0-100
    fc_ob_label = Column(String(30))                           # STRONG RETEST (2/3), etc.

    # ========== VOLUME PROFILE ANALYSIS ==========
    # Volume Profile identifies key price levels based on volume distribution
    # POC = Point of Control (highest volume), VAH/VAL = Value Area High/Low
    # HVN = High Volume Nodes (support/resistance), LVN = Low Volume Nodes (breakout zones)

    vp_bonus = Column(Boolean, default=False)                  # Overall VP confirms entry?
    vp_score = Column(Integer)                                 # VP score (0-100)
    vp_grade = Column(String(2))                               # A+, A, B+, B, C, D

    # VP Key Levels - 1H
    vp_poc_1h = Column(Float)                                  # Point of Control (1H)
    vp_vah_1h = Column(Float)                                  # Value Area High (1H)
    vp_val_1h = Column(Float)                                  # Value Area Low (1H)
    vp_hvn_levels_1h = Column(JSON)                            # High Volume Nodes list (1H)
    vp_lvn_levels_1h = Column(JSON)                            # Low Volume Nodes list (1H)
    vp_total_volume_1h = Column(Float)                         # Total volume in profile (1H)

    # VP Key Levels - 4H
    vp_poc_4h = Column(Float)                                  # Point of Control (4H)
    vp_vah_4h = Column(Float)                                  # Value Area High (4H)
    vp_val_4h = Column(Float)                                  # Value Area Low (4H)
    vp_hvn_levels_4h = Column(JSON)                            # High Volume Nodes list (4H)
    vp_lvn_levels_4h = Column(JSON)                            # Low Volume Nodes list (4H)
    vp_total_volume_4h = Column(Float)                         # Total volume in profile (4H)

    # VP Position Analysis at Entry
    vp_entry_position_1h = Column(String(20))                  # AT_POC, IN_VA, ABOVE_VA, BELOW_VA
    vp_entry_position_4h = Column(String(20))                  # AT_POC, IN_VA, ABOVE_VA, BELOW_VA
    vp_entry_vs_poc_pct_1h = Column(Float)                     # Distance from POC as % (1H)
    vp_entry_vs_poc_pct_4h = Column(Float)                     # Distance from POC as % (4H)

    # VP at SL position
    vp_sl_near_hvn = Column(Boolean, default=False)            # SL near a High Volume Node?
    vp_sl_hvn_level = Column(Float)                            # Nearest HVN to SL
    vp_sl_hvn_distance_pct = Column(Float)                     # Distance SL to HVN as %
    vp_sl_optimized = Column(Float)                            # Optimized SL based on HVN

    # VP Naked POC (untested POC = magnet)
    vp_naked_poc_1h = Column(Boolean, default=False)           # Untested POC exists? (1H)
    vp_naked_poc_level_1h = Column(Float)                      # Naked POC price (1H)
    vp_naked_poc_4h = Column(Boolean, default=False)           # Untested POC exists? (4H)
    vp_naked_poc_level_4h = Column(Float)                      # Naked POC price (4H)

    # VP Summary
    vp_label = Column(String(50))                              # STRONG SUPPORT, BREAKOUT ZONE, etc.
    vp_recommendation = Column(String(100))                    # Entry/SL suggestion
    vp_details = Column(JSON)                                  # Full VP data for display

    # VP Retest Detection (VAL/POC/VAH retest before entry)
    vp_val_retested = Column(Boolean, default=False)           # VAL was retested before entry
    vp_val_retest_rejected = Column(Boolean, default=False)    # VAL retest was rejected (bounce)
    vp_val_retest_dt = Column(DateTime)                        # VAL retest datetime
    vp_poc_retested = Column(Boolean, default=False)           # POC was retested
    vp_poc_retest_rejected = Column(Boolean, default=False)    # POC retest was rejected
    vp_poc_retest_dt = Column(DateTime)                        # POC retest datetime
    vp_vah_retested = Column(Boolean, default=False)           # VAH was retested (pullback)
    vp_hvn_retested = Column(Boolean, default=False)           # HVN was retested
    vp_hvn_retest_level = Column(Float)                        # HVN retest level
    vp_ob_confluence = Column(Boolean, default=False)          # VP retest + OB confluence
    vp_ob_confluence_tf = Column(String(10))                   # OB timeframe (1H, 4H, 1H+4H)
    vp_pullback_completed = Column(Boolean, default=False)     # Pullback to VP level completed
    vp_pullback_level = Column(String(10))                     # VAL, POC, VAH, HVN
    vp_pullback_quality = Column(String(20))                   # STRONG, GOOD, MODERATE

    # ═══════════════════════════════════════════════════════════════════════════════
    # V6 ADVANCED SCORING STRATEGY
    # Based on deep analysis of 91 trades: timing, CVD, distance patterns
    # Improves win rate from 65% to 72-75% by filtering low-quality entries
    # ═══════════════════════════════════════════════════════════════════════════════

    # V6 Validation Status
    v6_rejected = Column(Boolean, default=False)               # Rejected by V6 filters?
    v6_rejection_reason = Column(String(50))                   # V6_DISTANCE_TOO_HIGH, V6_15M_SLOW_RETEST, etc.

    # V6 Score & Grade
    v6_score = Column(Integer)                                 # Combined V6 score (40+ = excellent)
    v6_grade = Column(String(2))                               # A, B, C, F (A = 75.5% WR)

    # V6 Timing Metrics
    v6_retest_hours = Column(Float)                            # Hours from alert to retest
    v6_entry_hours = Column(Float)                             # Hours from alert to entry
    v6_distance_pct = Column(Float)                            # Distance % before retest
    v6_timing_adj = Column(Integer)                            # Timing score adjustment

    # V6 Momentum Metrics
    v6_rsi_at_entry = Column(Float)                            # RSI at entry time
    v6_adx_at_entry = Column(Float)                            # ADX at entry time
    v6_potential_pct = Column(Float)                           # Estimated profit potential %
    v6_momentum_adj = Column(Integer)                          # Momentum score adjustment

    # V6 CVD Analysis
    v6_has_cvd_divergence = Column(Boolean, default=False)     # CVD divergence detected?

    backtest_run = relationship("BacktestRun", back_populates="alerts")


class Trade(Base):
    """Trade result for a valid setup"""
    __tablename__ = 'trades'

    id = Column(Integer, primary_key=True, index=True)
    backtest_run_id = Column(Integer, ForeignKey('backtest_runs.id'))
    alert_id = Column(Integer, ForeignKey('alerts.id'))

    # Entry info
    alert_datetime = Column(DateTime)
    timeframe = Column(String(10))
    alert_price = Column(Float)
    entry_datetime = Column(DateTime)
    entry_price = Column(Float)

    # SL/TP levels
    sl_price = Column(Float)
    tp1_price = Column(Float)
    tp2_price = Column(Float)
    trailing_activation_price = Column(Float)

    # Strategy C results
    highest_price = Column(Float)
    trailing_active = Column(Boolean, default=False)
    trailing_sl = Column(Float)
    exit_datetime_c = Column(DateTime)
    exit_price_c = Column(Float)
    exit_reason_c = Column(String(100))
    pnl_c = Column(Float)

    # Break-Even tracking (Strategy C)
    be_active_c = Column(Boolean, default=False)
    be_activated_dt_c = Column(DateTime)
    be_activation_price = Column(Float)
    be_sl_price = Column(Float)

    # Strategy D results
    tp1_hit = Column(Boolean, default=False)
    tp2_hit = Column(Boolean, default=False)
    exit_datetime_d = Column(DateTime)
    exit_price_d = Column(Float)
    exit_reason_d = Column(String(100))
    pnl_d_tp1 = Column(Float)
    pnl_d_tp2 = Column(Float)
    pnl_d = Column(Float)

    # Break-Even tracking (Strategy D)
    be_active_d = Column(Boolean, default=False)
    be_activated_dt_d = Column(DateTime)

    # Post-SL Recovery Analysis (tracks price after stop loss hit)
    sl_then_recovered = Column(Boolean, default=False)      # Did price recover after SL?
    post_sl_max_price = Column(Float)                       # Highest price after SL hit
    post_sl_max_gain_pct = Column(Float)                    # Max gain % vs entry after SL
    post_sl_fib_levels = Column(JSON)                       # Fib levels broken after SL
    post_sl_monitoring_hours = Column(Float)                # Hours monitored after SL
    post_sl_would_have_won = Column(Boolean, default=False) # Would have been profitable

    # ═══════════════════════════════════════════════════════════════════════════════
    # V3 GOLDEN BOX RETEST STRATEGY - Trade specific fields
    # ═══════════════════════════════════════════════════════════════════════════════
    strategy_version = Column(String(10), default='v1')     # v1, v2, or v3
    v3_box_high = Column(Float)                             # Golden Box High
    v3_box_low = Column(Float)                              # Golden Box Low
    v3_hours_to_entry = Column(Float)                       # Hours from signal to V3 entry
    v3_sl_distance_pct = Column(Float)                      # V3 SL distance from entry
    v3_quality_score = Column(Integer)                      # V3 entry quality score
    v3_breakout_dt = Column(DateTime)                       # When breakout occurred
    v3_breakout_high = Column(Float)                        # Highest price before retest
    v3_retest_datetime = Column(DateTime)                   # Exact retest datetime
    v3_retest_price = Column(Float)                         # Exact retest price
    v3_prog_count = Column(Integer)                         # Progressive conditions count (0-5)

    backtest_run = relationship("BacktestRun", back_populates="trades")


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {DATABASE_PATH}")
