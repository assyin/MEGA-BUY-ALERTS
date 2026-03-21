import { NextRequest, NextResponse } from "next/server"
import { spawn } from "child_process"
import path from "path"

const BACKTEST_DIR = path.join(process.cwd(), "..", "backtest")
const PYTHON_PATH = path.join(BACKTEST_DIR, "venv", "bin", "python")

async function runPython(script: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON_PATH, ["-c", script], {
      cwd: BACKTEST_DIR
    })

    let stdout = ""
    let stderr = ""

    proc.stdout.on("data", (data) => {
      stdout += data.toString()
    })

    proc.stderr.on("data", (data) => {
      stderr += data.toString()
    })

    proc.on("close", (code) => {
      if (code === 0) {
        resolve(stdout)
      } else {
        reject(new Error(stderr || `Process exited with code ${code}`))
      }
    })
  })
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const id = searchParams.get("id")

    if (!id) {
      return NextResponse.json({ error: "Missing id" }, { status: 400 })
    }

    const script = `
import json
import sys
sys.path.insert(0, '.')
from api.models import SessionLocal, Alert

db = SessionLocal()
alerts = db.query(Alert).filter(Alert.backtest_run_id == ${id}).order_by(Alert.alert_datetime).all()

result = []
for a in alerts:
    result.append({
        'id': a.id,
        'alert_datetime': a.alert_datetime.isoformat() if a.alert_datetime else None,
        'timeframe': a.timeframe,
        'price_open': a.price_open,
        'price_high': a.price_high,
        'price_low': a.price_low,
        'price_close': a.price_close,
        'volume': a.volume,
        'score': a.score,

        # MEGA BUY 10 Conditions (3 mandatory + 7 optional)
        'conditions': a.conditions or {},

        # Indicators by timeframe
        'indicators_15m': a.indicators_15m or {},
        'indicators_30m': a.indicators_30m or {},
        'indicators_1h': a.indicators_1h or {},

        # STC Validation
        'stc_validated': a.stc_validated,
        'stc_valid_tfs': a.stc_valid_tfs,

        # 15m Filter
        'is_15m_alone': a.is_15m_alone,
        'combo_tfs': a.combo_tfs,

        # Trendline Info
        'has_trendline': a.has_trendline,
        'tl_type': a.tl_type,
        'tl_price_at_alert': a.tl_price_at_alert,
        'tl_p1_date': a.tl_p1_date.isoformat() if a.tl_p1_date else None,
        'tl_p1_price': a.tl_p1_price,
        'tl_p2_date': a.tl_p2_date.isoformat() if a.tl_p2_date else None,
        'tl_p2_price': a.tl_p2_price,

        # TL Break Info
        'has_tl_break': a.has_tl_break,
        'tl_break_datetime': a.tl_break_datetime.isoformat() if a.tl_break_datetime else None,
        'tl_break_price': a.tl_break_price,
        'tl_break_delay_hours': a.tl_break_delay_hours,
        'tl_retest_count': getattr(a, 'tl_retest_count', 0),
        'delay_exceeded': a.delay_exceeded,

        # Entry Info
        'has_entry': a.has_entry,
        'entry_datetime': a.entry_datetime.isoformat() if a.entry_datetime else None,
        'entry_price': a.entry_price,
        'entry_diff_vs_alert': a.entry_diff_vs_alert,
        'entry_diff_vs_break': a.entry_diff_vs_break,

        # Progressive Conditions - Indicator VALUES
        'prog_ema100_1h': a.prog_ema100_1h,
        'prog_ema20_4h': a.prog_ema20_4h,
        'prog_cloud_1h': a.prog_cloud_1h,
        'prog_cloud_30m': a.prog_cloud_30m,
        'prog_choch_bos_datetime': a.prog_choch_bos_datetime.isoformat() if a.prog_choch_bos_datetime else None,
        'prog_choch_bos_sh_price': a.prog_choch_bos_sh_price,

        # Progressive Conditions - Price VALUES used
        'prog_price_1h': a.prog_price_1h,
        'prog_price_30m': a.prog_price_30m,
        'prog_price_4h': a.prog_price_4h,

        # Progressive Conditions - Validation RESULTS (True/False)
        'prog_valid_ema100_1h': a.prog_valid_ema100_1h,
        'prog_valid_ema20_4h': a.prog_valid_ema20_4h,
        'prog_valid_cloud_1h': a.prog_valid_cloud_1h,
        'prog_valid_cloud_30m': a.prog_valid_cloud_30m,
        'prog_choch_bos_valid': a.prog_choch_bos_valid,

        # Fibonacci Bonus (4H)
        'fib_bonus': a.fib_bonus,
        'fib_swing_high': a.fib_swing_high,
        'fib_swing_low': a.fib_swing_low,
        'fib_levels': a.fib_levels or {},

        # Fibonacci (1H)
        'fib_swing_high_1h': a.fib_swing_high_1h,
        'fib_swing_low_1h': a.fib_swing_low_1h,
        'fib_levels_1h': a.fib_levels_1h or {},

        # Order Block (SMC) - 1H
        'ob_bonus': a.ob_bonus,
        'ob_zone_high': a.ob_zone_high,
        'ob_zone_low': a.ob_zone_low,
        'ob_datetime': a.ob_datetime.isoformat() if a.ob_datetime else None,
        'ob_distance_pct': a.ob_distance_pct,
        'ob_position': a.ob_position,
        'ob_strength': a.ob_strength,
        'ob_impulse_pct': a.ob_impulse_pct,
        'ob_age_bars': a.ob_age_bars,
        'ob_mitigated': a.ob_mitigated,
        'ob_data': a.ob_data or {},

        # Order Block (SMC) - 4H
        'ob_bonus_4h': a.ob_bonus_4h,
        'ob_zone_high_4h': a.ob_zone_high_4h,
        'ob_zone_low_4h': a.ob_zone_low_4h,
        'ob_datetime_4h': a.ob_datetime_4h.isoformat() if a.ob_datetime_4h else None,
        'ob_distance_pct_4h': a.ob_distance_pct_4h,
        'ob_position_4h': a.ob_position_4h,
        'ob_strength_4h': a.ob_strength_4h,
        'ob_impulse_pct_4h': a.ob_impulse_pct_4h,
        'ob_age_bars_4h': a.ob_age_bars_4h,
        'ob_mitigated_4h': a.ob_mitigated_4h,
        'ob_data_4h': a.ob_data_4h or {},

        # BTC Correlation BONUS - 1H
        'btc_corr_bonus_1h': a.btc_corr_bonus_1h,
        'btc_price_1h': a.btc_price_1h,
        'btc_ema20_1h': a.btc_ema20_1h,
        'btc_ema50_1h': a.btc_ema50_1h,
        'btc_rsi_1h': a.btc_rsi_1h,
        'btc_trend_1h': a.btc_trend_1h,

        # BTC Correlation BONUS - 4H
        'btc_corr_bonus_4h': a.btc_corr_bonus_4h,
        'btc_price_4h': a.btc_price_4h,
        'btc_ema20_4h': a.btc_ema20_4h,
        'btc_ema50_4h': a.btc_ema50_4h,
        'btc_rsi_4h': a.btc_rsi_4h,
        'btc_trend_4h': a.btc_trend_4h,

        # ETH Correlation BONUS - 1H
        'eth_corr_bonus_1h': a.eth_corr_bonus_1h,
        'eth_price_1h': a.eth_price_1h,
        'eth_ema20_1h': a.eth_ema20_1h,
        'eth_ema50_1h': a.eth_ema50_1h,
        'eth_rsi_1h': a.eth_rsi_1h,
        'eth_trend_1h': a.eth_trend_1h,

        # ETH Correlation BONUS - 4H
        'eth_corr_bonus_4h': a.eth_corr_bonus_4h,
        'eth_price_4h': a.eth_price_4h,
        'eth_ema20_4h': a.eth_ema20_4h,
        'eth_ema50_4h': a.eth_ema50_4h,
        'eth_rsi_4h': a.eth_rsi_4h,
        'eth_trend_4h': a.eth_trend_4h,

        # Fair Value Gap (FVG) BONUS - 1H
        'fvg_bonus_1h': a.fvg_bonus_1h,
        'fvg_zone_high_1h': a.fvg_zone_high_1h,
        'fvg_zone_low_1h': a.fvg_zone_low_1h,
        'fvg_datetime_1h': a.fvg_datetime_1h.isoformat() if a.fvg_datetime_1h else None,
        'fvg_distance_pct_1h': a.fvg_distance_pct_1h,
        'fvg_position_1h': a.fvg_position_1h,
        'fvg_filled_pct_1h': a.fvg_filled_pct_1h,
        'fvg_size_pct_1h': a.fvg_size_pct_1h,
        'fvg_age_bars_1h': a.fvg_age_bars_1h,
        'fvg_data_1h': a.fvg_data_1h or {},

        # Fair Value Gap (FVG) BONUS - 4H
        'fvg_bonus_4h': a.fvg_bonus_4h,
        'fvg_zone_high_4h': a.fvg_zone_high_4h,
        'fvg_zone_low_4h': a.fvg_zone_low_4h,
        'fvg_datetime_4h': a.fvg_datetime_4h.isoformat() if a.fvg_datetime_4h else None,
        'fvg_distance_pct_4h': a.fvg_distance_pct_4h,
        'fvg_position_4h': a.fvg_position_4h,
        'fvg_filled_pct_4h': a.fvg_filled_pct_4h,
        'fvg_size_pct_4h': a.fvg_size_pct_4h,
        'fvg_age_bars_4h': a.fvg_age_bars_4h,
        'fvg_data_4h': a.fvg_data_4h or {},

        # Volume Spike BONUS - 1H
        'vol_spike_bonus_1h': a.vol_spike_bonus_1h,
        'vol_current_1h': a.vol_current_1h,
        'vol_avg_1h': a.vol_avg_1h,
        'vol_ratio_1h': a.vol_ratio_1h,
        'vol_spike_level_1h': a.vol_spike_level_1h,

        # Volume Spike BONUS - 4H
        'vol_spike_bonus_4h': a.vol_spike_bonus_4h,
        'vol_current_4h': a.vol_current_4h,
        'vol_avg_4h': a.vol_avg_4h,
        'vol_ratio_4h': a.vol_ratio_4h,
        'vol_spike_level_4h': a.vol_spike_level_4h,

        # RSI Multi-TF Alignment BONUS
        'rsi_mtf_bonus': a.rsi_mtf_bonus,
        'rsi_1h': a.rsi_1h,
        'rsi_4h': a.rsi_4h,
        'rsi_daily': a.rsi_daily,
        'rsi_aligned_count': a.rsi_aligned_count,
        'rsi_mtf_trend': a.rsi_mtf_trend,

        # ADX Trend Strength BONUS - 1H
        'adx_bonus_1h': a.adx_bonus_1h,
        'adx_value_1h': a.adx_value_1h,
        'adx_plus_di_1h': a.adx_plus_di_1h,
        'adx_minus_di_1h': a.adx_minus_di_1h,
        'adx_strength_1h': a.adx_strength_1h,

        # ADX Trend Strength BONUS - 4H
        'adx_bonus_4h': a.adx_bonus_4h,
        'adx_value_4h': a.adx_value_4h,
        'adx_plus_di_4h': a.adx_plus_di_4h,
        'adx_minus_di_4h': a.adx_minus_di_4h,
        'adx_strength_4h': a.adx_strength_4h,

        # MACD Momentum BONUS - 1H
        'macd_bonus_1h': a.macd_bonus_1h,
        'macd_line_1h': a.macd_line_1h,
        'macd_signal_1h': a.macd_signal_1h,
        'macd_histogram_1h': a.macd_histogram_1h,
        'macd_hist_growing_1h': a.macd_hist_growing_1h,
        'macd_trend_1h': a.macd_trend_1h,

        # MACD Momentum BONUS - 4H
        'macd_bonus_4h': a.macd_bonus_4h,
        'macd_line_4h': a.macd_line_4h,
        'macd_signal_4h': a.macd_signal_4h,
        'macd_histogram_4h': a.macd_histogram_4h,
        'macd_hist_growing_4h': a.macd_hist_growing_4h,
        'macd_trend_4h': a.macd_trend_4h,

        # Bollinger Squeeze BONUS - 1H
        'bb_squeeze_bonus_1h': a.bb_squeeze_bonus_1h,
        'bb_upper_1h': a.bb_upper_1h,
        'bb_middle_1h': a.bb_middle_1h,
        'bb_lower_1h': a.bb_lower_1h,
        'bb_width_pct_1h': a.bb_width_pct_1h,
        'bb_squeeze_1h': a.bb_squeeze_1h,
        'bb_breakout_1h': a.bb_breakout_1h,

        # Bollinger Squeeze BONUS - 4H
        'bb_squeeze_bonus_4h': a.bb_squeeze_bonus_4h,
        'bb_upper_4h': a.bb_upper_4h,
        'bb_middle_4h': a.bb_middle_4h,
        'bb_lower_4h': a.bb_lower_4h,
        'bb_width_pct_4h': a.bb_width_pct_4h,
        'bb_squeeze_4h': a.bb_squeeze_4h,
        'bb_breakout_4h': a.bb_breakout_4h,

        # Stochastic RSI BONUS - 1H
        'stoch_rsi_bonus_1h': a.stoch_rsi_bonus_1h,
        'stoch_rsi_k_1h': a.stoch_rsi_k_1h,
        'stoch_rsi_d_1h': a.stoch_rsi_d_1h,
        'stoch_rsi_zone_1h': a.stoch_rsi_zone_1h,
        'stoch_rsi_cross_1h': a.stoch_rsi_cross_1h,

        # Stochastic RSI BONUS - 4H
        'stoch_rsi_bonus_4h': a.stoch_rsi_bonus_4h,
        'stoch_rsi_k_4h': a.stoch_rsi_k_4h,
        'stoch_rsi_d_4h': a.stoch_rsi_d_4h,
        'stoch_rsi_zone_4h': a.stoch_rsi_zone_4h,
        'stoch_rsi_cross_4h': a.stoch_rsi_cross_4h,

        # EMA Stack BONUS - 1H
        'ema_stack_bonus_1h': a.ema_stack_bonus_1h,
        'ema8_1h': a.ema8_1h,
        'ema21_1h': a.ema21_1h,
        'ema50_1h': a.ema50_1h,
        'ema100_1h_stack': a.ema100_1h_stack,
        'ema_stack_count_1h': a.ema_stack_count_1h,
        'ema_stack_trend_1h': a.ema_stack_trend_1h,

        # EMA Stack BONUS - 4H
        'ema_stack_bonus_4h': a.ema_stack_bonus_4h,
        'ema8_4h': a.ema8_4h,
        'ema21_4h': a.ema21_4h,
        'ema50_4h': a.ema50_4h,
        'ema100_4h_stack': a.ema100_4h_stack,
        'ema_stack_count_4h': a.ema_stack_count_4h,
        'ema_stack_trend_4h': a.ema_stack_trend_4h,

        # V3 Golden Box Retest
        'v3_entry_found': getattr(a, 'v3_entry_found', None),
        'v3_entry_datetime': a.v3_entry_datetime.isoformat() if getattr(a, 'v3_entry_datetime', None) else None,
        'v3_entry_price': getattr(a, 'v3_entry_price', None),
        'v3_sl_price': getattr(a, 'v3_sl_price', None),
        'v3_box_high': getattr(a, 'v3_box_high', None),
        'v3_box_low': getattr(a, 'v3_box_low', None),
        'v3_box_range_pct': getattr(a, 'v3_box_range_pct', None),
        'v3_hours_to_entry': getattr(a, 'v3_hours_to_entry', None),
        'v3_sl_distance_pct': getattr(a, 'v3_sl_distance_pct', None),
        'v3_quality_score': int.from_bytes(a.v3_quality_score, 'little') if isinstance(getattr(a, 'v3_quality_score', None), bytes) else getattr(a, 'v3_quality_score', None),
        'v3_breakout_dt': a.v3_breakout_dt.isoformat() if getattr(a, 'v3_breakout_dt', None) else None,
        'v3_breakout_high': getattr(a, 'v3_breakout_high', None),
        'v3_distance_before_retest': getattr(a, 'v3_distance_before_retest', None),
        'v3_rejected': getattr(a, 'v3_rejected', None),
        'v3_rejection_reason': getattr(a, 'v3_rejection_reason', None),
        # V3 Progressive Conditions at retest time
        'v3_prog_valid_ema100_1h': getattr(a, 'v3_prog_valid_ema100_1h', None),
        'v3_prog_valid_ema20_4h': getattr(a, 'v3_prog_valid_ema20_4h', None),
        'v3_prog_valid_cloud_1h': getattr(a, 'v3_prog_valid_cloud_1h', None),
        'v3_prog_valid_cloud_30m': getattr(a, 'v3_prog_valid_cloud_30m', None),
        'v3_prog_choch_bos_valid': getattr(a, 'v3_prog_choch_bos_valid', None),
        'v3_prog_count': int.from_bytes(a.v3_prog_count, 'little') if isinstance(getattr(a, 'v3_prog_count', None), bytes) else getattr(a, 'v3_prog_count', None),
        'v3_prog_ema100_1h_val': getattr(a, 'v3_prog_ema100_1h_val', None),
        'v3_prog_ema20_4h_val': getattr(a, 'v3_prog_ema20_4h_val', None),
        'v3_prog_cloud_1h_val': getattr(a, 'v3_prog_cloud_1h_val', None),
        'v3_prog_cloud_30m_val': getattr(a, 'v3_prog_cloud_30m_val', None),
        'v3_retest_price': getattr(a, 'v3_retest_price', None),
        'v3_retest_datetime': a.v3_retest_datetime.isoformat() if getattr(a, 'v3_retest_datetime', None) else None,
        # V3 Retest vs TL Break
        'v3_retest_vs_tl_break': getattr(a, 'v3_retest_vs_tl_break', None),
        'v3_tl_break_datetime': a.v3_tl_break_datetime.isoformat() if getattr(a, 'v3_tl_break_datetime', None) else None,
        'v3_hours_retest_vs_tl': getattr(a, 'v3_hours_retest_vs_tl', None),

        # V3 Risk Indicators
        'v3_risk_level': getattr(a, 'v3_risk_level', None),
        'v3_risk_score': getattr(a, 'v3_risk_score', None),
        'v3_risk_reasons': getattr(a, 'v3_risk_reasons', None),

        # GB Power Score
        'gb_power_score': getattr(a, 'gb_power_score', None),
        'gb_power_grade': getattr(a, 'gb_power_grade', None),
        'gb_volume_score': getattr(a, 'gb_volume_score', None),
        'gb_adx_score': getattr(a, 'gb_adx_score', None),
        'gb_ema_alignment_score': getattr(a, 'gb_ema_alignment_score', None),
        'gb_macd_momentum_score': getattr(a, 'gb_macd_momentum_score', None),
        'gb_fib_position_score': getattr(a, 'gb_fib_position_score', None),
        'gb_retest_quality_score': getattr(a, 'gb_retest_quality_score', None),
        'gb_dmi_spread_score': getattr(a, 'gb_dmi_spread_score', None),
        'gb_rsi_strength_score': getattr(a, 'gb_rsi_strength_score', None),
        'gb_btc_correlation_score': getattr(a, 'gb_btc_correlation_score', None),
        'gb_confluence_score': getattr(a, 'gb_confluence_score', None),
        'gb_dmi_spread': getattr(a, 'gb_dmi_spread', None),

        # CVD (Cumulative Volume Delta) Analysis
        'cvd_bonus': getattr(a, 'cvd_bonus', False),
        'cvd_score': getattr(a, 'cvd_score', None),
        'cvd_label': getattr(a, 'cvd_label', None),
        'cvd_description': getattr(a, 'cvd_description', None),
        'cvd_at_break': getattr(a, 'cvd_at_break', None),
        'cvd_at_break_trend': getattr(a, 'cvd_at_break_trend', None),
        'cvd_at_break_signal': getattr(a, 'cvd_at_break_signal', None),
        'cvd_at_breakout': getattr(a, 'cvd_at_breakout', None),
        'cvd_at_breakout_spike': getattr(a, 'cvd_at_breakout_spike', None),
        'cvd_at_breakout_signal': getattr(a, 'cvd_at_breakout_signal', None),
        'cvd_at_retest': getattr(a, 'cvd_at_retest', None),
        'cvd_at_retest_trend': getattr(a, 'cvd_at_retest_trend', None),
        'cvd_at_retest_signal': getattr(a, 'cvd_at_retest_signal', None),
        'cvd_at_entry': getattr(a, 'cvd_at_entry', None),
        'cvd_at_entry_trend': getattr(a, 'cvd_at_entry_trend', None),
        'cvd_at_entry_signal': getattr(a, 'cvd_at_entry_signal', None),
        'cvd_divergence': getattr(a, 'cvd_divergence', False),
        'cvd_divergence_type': getattr(a, 'cvd_divergence_type', None),
        'vol_at_break_ratio': getattr(a, 'vol_at_break_ratio', None),
        'vol_at_breakout_ratio': getattr(a, 'vol_at_breakout_ratio', None),
        'vol_at_retest_ratio': getattr(a, 'vol_at_retest_ratio', None),
        'vol_at_entry_ratio': getattr(a, 'vol_at_entry_ratio', None),

        # CVD 4H (Cumulative Volume Delta - 4H timeframe)
        'cvd_4h_bonus': getattr(a, 'cvd_4h_bonus', False),
        'cvd_4h_score': getattr(a, 'cvd_4h_score', None),
        'cvd_4h_label': getattr(a, 'cvd_4h_label', None),
        'cvd_4h_description': getattr(a, 'cvd_4h_description', None),
        'cvd_4h_at_break': getattr(a, 'cvd_4h_at_break', None),
        'cvd_4h_at_break_trend': getattr(a, 'cvd_4h_at_break_trend', None),
        'cvd_4h_at_break_signal': getattr(a, 'cvd_4h_at_break_signal', None),
        'cvd_4h_at_breakout': getattr(a, 'cvd_4h_at_breakout', None),
        'cvd_4h_at_breakout_spike': getattr(a, 'cvd_4h_at_breakout_spike', None),
        'cvd_4h_at_breakout_signal': getattr(a, 'cvd_4h_at_breakout_signal', None),
        'cvd_4h_at_retest': getattr(a, 'cvd_4h_at_retest', None),
        'cvd_4h_at_retest_trend': getattr(a, 'cvd_4h_at_retest_trend', None),
        'cvd_4h_at_retest_signal': getattr(a, 'cvd_4h_at_retest_signal', None),
        'cvd_4h_at_entry': getattr(a, 'cvd_4h_at_entry', None),
        'cvd_4h_at_entry_trend': getattr(a, 'cvd_4h_at_entry_trend', None),
        'cvd_4h_at_entry_signal': getattr(a, 'cvd_4h_at_entry_signal', None),
        'cvd_4h_divergence': getattr(a, 'cvd_4h_divergence', False),
        'cvd_4h_divergence_type': getattr(a, 'cvd_4h_divergence_type', None),
        'vol_4h_at_break_ratio': getattr(a, 'vol_4h_at_break_ratio', None),
        'vol_4h_at_breakout_ratio': getattr(a, 'vol_4h_at_breakout_ratio', None),
        'vol_4h_at_retest_ratio': getattr(a, 'vol_4h_at_retest_ratio', None),
        'vol_4h_at_entry_ratio': getattr(a, 'vol_4h_at_entry_ratio', None),

        # ADX/DI Analysis (1H)
        'adx_di_1h_bonus': getattr(a, 'adx_di_1h_bonus', False),
        'adx_di_1h_score': getattr(a, 'adx_di_1h_score', None),
        'adx_di_1h_label': getattr(a, 'adx_di_1h_label', None),
        'adx_1h_at_break': getattr(a, 'adx_1h_at_break', None),
        'di_plus_1h_at_break': getattr(a, 'di_plus_1h_at_break', None),
        'di_minus_1h_at_break': getattr(a, 'di_minus_1h_at_break', None),
        'di_spread_1h_at_break': getattr(a, 'di_spread_1h_at_break', None),
        'adx_di_1h_at_break_signal': getattr(a, 'adx_di_1h_at_break_signal', None),
        'adx_1h_at_breakout': getattr(a, 'adx_1h_at_breakout', None),
        'di_plus_1h_at_breakout': getattr(a, 'di_plus_1h_at_breakout', None),
        'di_minus_1h_at_breakout': getattr(a, 'di_minus_1h_at_breakout', None),
        'di_spread_1h_at_breakout': getattr(a, 'di_spread_1h_at_breakout', None),
        'adx_di_1h_at_breakout_signal': getattr(a, 'adx_di_1h_at_breakout_signal', None),
        'adx_1h_at_retest': getattr(a, 'adx_1h_at_retest', None),
        'di_plus_1h_at_retest': getattr(a, 'di_plus_1h_at_retest', None),
        'di_minus_1h_at_retest': getattr(a, 'di_minus_1h_at_retest', None),
        'di_spread_1h_at_retest': getattr(a, 'di_spread_1h_at_retest', None),
        'adx_di_1h_at_retest_signal': getattr(a, 'adx_di_1h_at_retest_signal', None),
        'adx_1h_at_entry': getattr(a, 'adx_1h_at_entry', None),
        'di_plus_1h_at_entry': getattr(a, 'di_plus_1h_at_entry', None),
        'di_minus_1h_at_entry': getattr(a, 'di_minus_1h_at_entry', None),
        'di_spread_1h_at_entry': getattr(a, 'di_spread_1h_at_entry', None),
        'adx_di_1h_at_entry_signal': getattr(a, 'adx_di_1h_at_entry_signal', None),
        'di_plus_1h_overbought': getattr(a, 'di_plus_1h_overbought', False),
        'di_minus_1h_oversold': getattr(a, 'di_minus_1h_oversold', False),

        # ADX/DI Analysis (4H)
        'adx_di_4h_bonus': getattr(a, 'adx_di_4h_bonus', False),
        'adx_di_4h_score': getattr(a, 'adx_di_4h_score', None),
        'adx_di_4h_label': getattr(a, 'adx_di_4h_label', None),
        'adx_4h_at_break': getattr(a, 'adx_4h_at_break', None),
        'di_plus_4h_at_break': getattr(a, 'di_plus_4h_at_break', None),
        'di_minus_4h_at_break': getattr(a, 'di_minus_4h_at_break', None),
        'di_spread_4h_at_break': getattr(a, 'di_spread_4h_at_break', None),
        'adx_di_4h_at_break_signal': getattr(a, 'adx_di_4h_at_break_signal', None),
        'adx_4h_at_breakout': getattr(a, 'adx_4h_at_breakout', None),
        'di_plus_4h_at_breakout': getattr(a, 'di_plus_4h_at_breakout', None),
        'di_minus_4h_at_breakout': getattr(a, 'di_minus_4h_at_breakout', None),
        'di_spread_4h_at_breakout': getattr(a, 'di_spread_4h_at_breakout', None),
        'adx_di_4h_at_breakout_signal': getattr(a, 'adx_di_4h_at_breakout_signal', None),
        'adx_4h_at_retest': getattr(a, 'adx_4h_at_retest', None),
        'di_plus_4h_at_retest': getattr(a, 'di_plus_4h_at_retest', None),
        'di_minus_4h_at_retest': getattr(a, 'di_minus_4h_at_retest', None),
        'di_spread_4h_at_retest': getattr(a, 'di_spread_4h_at_retest', None),
        'adx_di_4h_at_retest_signal': getattr(a, 'adx_di_4h_at_retest_signal', None),
        'adx_4h_at_entry': getattr(a, 'adx_4h_at_entry', None),
        'di_plus_4h_at_entry': getattr(a, 'di_plus_4h_at_entry', None),
        'di_minus_4h_at_entry': getattr(a, 'di_minus_4h_at_entry', None),
        'di_spread_4h_at_entry': getattr(a, 'di_spread_4h_at_entry', None),
        'adx_di_4h_at_entry_signal': getattr(a, 'adx_di_4h_at_entry_signal', None),
        'di_plus_4h_overbought': getattr(a, 'di_plus_4h_overbought', False),
        'di_minus_4h_oversold': getattr(a, 'di_minus_4h_oversold', False),

        # ========== AI AGENT DECISION ==========
        'agent_decision': getattr(a, 'agent_decision', None),
        'agent_confidence': getattr(a, 'agent_confidence', None),
        'agent_score': getattr(a, 'agent_score', None),
        'agent_grade': getattr(a, 'agent_grade', None),
        'agent_bullish_count': getattr(a, 'agent_bullish_count', None),
        'agent_bearish_count': getattr(a, 'agent_bearish_count', None),
        'agent_neutral_count': getattr(a, 'agent_neutral_count', None),
        'agent_bullish_factors': getattr(a, 'agent_bullish_factors', None),
        'agent_bearish_factors': getattr(a, 'agent_bearish_factors', None),
        'agent_reasoning': getattr(a, 'agent_reasoning', None),
        'agent_cvd_score': getattr(a, 'agent_cvd_score', None),
        'agent_adx_score': getattr(a, 'agent_adx_score', None),
        'agent_trend_score': getattr(a, 'agent_trend_score', None),
        'agent_momentum_score': getattr(a, 'agent_momentum_score', None),
        'agent_volume_score': getattr(a, 'agent_volume_score', None),
        'agent_confluence_score': getattr(a, 'agent_confluence_score', None),

        # ========== FOREIGN CANDLE ORDER BLOCK ==========
        'fc_ob_1h_found': getattr(a, 'fc_ob_1h_found', False),
        'fc_ob_1h_count': getattr(a, 'fc_ob_1h_count', None),
        'fc_ob_1h_type': getattr(a, 'fc_ob_1h_type', None),
        'fc_ob_1h_zone_high': getattr(a, 'fc_ob_1h_zone_high', None),
        'fc_ob_1h_zone_low': getattr(a, 'fc_ob_1h_zone_low', None),
        'fc_ob_1h_strength': getattr(a, 'fc_ob_1h_strength', None),
        'fc_ob_1h_retest': getattr(a, 'fc_ob_1h_retest', False),
        'fc_ob_1h_distance_pct': getattr(a, 'fc_ob_1h_distance_pct', None),
        'fc_ob_1h_datetime': getattr(a, 'fc_ob_1h_datetime', None).isoformat() if getattr(a, 'fc_ob_1h_datetime', None) else None,
        'fc_ob_1h_in_zone': getattr(a, 'fc_ob_1h_in_zone', 0),
        'fc_ob_1h_retested': getattr(a, 'fc_ob_1h_retested', 0),
        'fc_ob_4h_found': getattr(a, 'fc_ob_4h_found', False),
        'fc_ob_4h_count': getattr(a, 'fc_ob_4h_count', None),
        'fc_ob_4h_type': getattr(a, 'fc_ob_4h_type', None),
        'fc_ob_4h_zone_high': getattr(a, 'fc_ob_4h_zone_high', None),
        'fc_ob_4h_zone_low': getattr(a, 'fc_ob_4h_zone_low', None),
        'fc_ob_4h_strength': getattr(a, 'fc_ob_4h_strength', None),
        'fc_ob_4h_retest': getattr(a, 'fc_ob_4h_retest', False),
        'fc_ob_4h_distance_pct': getattr(a, 'fc_ob_4h_distance_pct', None),
        'fc_ob_4h_datetime': getattr(a, 'fc_ob_4h_datetime', None).isoformat() if getattr(a, 'fc_ob_4h_datetime', None) else None,
        'fc_ob_4h_in_zone': getattr(a, 'fc_ob_4h_in_zone', 0),
        'fc_ob_4h_retested': getattr(a, 'fc_ob_4h_retested', 0),
        'fc_ob_bonus': getattr(a, 'fc_ob_bonus', False),
        'fc_ob_score': getattr(a, 'fc_ob_score', None),
        'fc_ob_label': getattr(a, 'fc_ob_label', None),

        # ========== VOLUME PROFILE ANALYSIS ==========
        'vp_bonus': getattr(a, 'vp_bonus', False),
        'vp_score': getattr(a, 'vp_score', None),
        'vp_grade': getattr(a, 'vp_grade', None),
        'vp_poc_1h': getattr(a, 'vp_poc_1h', None),
        'vp_vah_1h': getattr(a, 'vp_vah_1h', None),
        'vp_val_1h': getattr(a, 'vp_val_1h', None),
        'vp_hvn_levels_1h': getattr(a, 'vp_hvn_levels_1h', None),
        'vp_lvn_levels_1h': getattr(a, 'vp_lvn_levels_1h', None),
        'vp_total_volume_1h': getattr(a, 'vp_total_volume_1h', None),
        'vp_poc_4h': getattr(a, 'vp_poc_4h', None),
        'vp_vah_4h': getattr(a, 'vp_vah_4h', None),
        'vp_val_4h': getattr(a, 'vp_val_4h', None),
        'vp_hvn_levels_4h': getattr(a, 'vp_hvn_levels_4h', None),
        'vp_lvn_levels_4h': getattr(a, 'vp_lvn_levels_4h', None),
        'vp_total_volume_4h': getattr(a, 'vp_total_volume_4h', None),
        'vp_entry_position_1h': getattr(a, 'vp_entry_position_1h', None),
        'vp_entry_position_4h': getattr(a, 'vp_entry_position_4h', None),
        'vp_entry_vs_poc_pct_1h': getattr(a, 'vp_entry_vs_poc_pct_1h', None),
        'vp_entry_vs_poc_pct_4h': getattr(a, 'vp_entry_vs_poc_pct_4h', None),
        'vp_sl_near_hvn': getattr(a, 'vp_sl_near_hvn', False),
        'vp_sl_hvn_level': getattr(a, 'vp_sl_hvn_level', None),
        'vp_sl_hvn_distance_pct': getattr(a, 'vp_sl_hvn_distance_pct', None),
        'vp_sl_optimized': getattr(a, 'vp_sl_optimized', None),
        'vp_naked_poc_1h': getattr(a, 'vp_naked_poc_1h', False),
        'vp_naked_poc_level_1h': getattr(a, 'vp_naked_poc_level_1h', None),
        'vp_naked_poc_4h': getattr(a, 'vp_naked_poc_4h', False),
        'vp_naked_poc_level_4h': getattr(a, 'vp_naked_poc_level_4h', None),
        'vp_label': getattr(a, 'vp_label', None),
        'vp_recommendation': getattr(a, 'vp_recommendation', None),
        'vp_details': getattr(a, 'vp_details', None),

        # VP Retest Detection
        'vp_val_retested': getattr(a, 'vp_val_retested', False),
        'vp_val_retest_rejected': getattr(a, 'vp_val_retest_rejected', False),
        'vp_val_retest_dt': str(getattr(a, 'vp_val_retest_dt', None)) if getattr(a, 'vp_val_retest_dt', None) else None,
        'vp_poc_retested': getattr(a, 'vp_poc_retested', False),
        'vp_poc_retest_rejected': getattr(a, 'vp_poc_retest_rejected', False),
        'vp_poc_retest_dt': str(getattr(a, 'vp_poc_retest_dt', None)) if getattr(a, 'vp_poc_retest_dt', None) else None,
        'vp_vah_retested': getattr(a, 'vp_vah_retested', False),
        'vp_hvn_retested': getattr(a, 'vp_hvn_retested', False),
        'vp_hvn_retest_level': getattr(a, 'vp_hvn_retest_level', None),
        'vp_ob_confluence': getattr(a, 'vp_ob_confluence', False),
        'vp_ob_confluence_tf': getattr(a, 'vp_ob_confluence_tf', None),
        'vp_pullback_completed': getattr(a, 'vp_pullback_completed', False),
        'vp_pullback_level': getattr(a, 'vp_pullback_level', None),
        'vp_pullback_quality': getattr(a, 'vp_pullback_quality', None),

        # ========== V6 ADVANCED SCORING ==========
        'v6_rejected': getattr(a, 'v6_rejected', False),
        'v6_rejection_reason': getattr(a, 'v6_rejection_reason', None),
        'v6_score': getattr(a, 'v6_score', None),
        'v6_grade': getattr(a, 'v6_grade', None),
        'v6_retest_hours': getattr(a, 'v6_retest_hours', None),
        'v6_entry_hours': getattr(a, 'v6_entry_hours', None),
        'v6_distance_pct': getattr(a, 'v6_distance_pct', None),
        'v6_rsi_at_entry': getattr(a, 'v6_rsi_at_entry', None),
        'v6_adx_at_entry': getattr(a, 'v6_adx_at_entry', None),
        'v6_potential_pct': getattr(a, 'v6_potential_pct', None),
        'v6_has_cvd_divergence': getattr(a, 'v6_has_cvd_divergence', False),
        'v6_timing_adj': getattr(a, 'v6_timing_adj', None),
        'v6_momentum_adj': getattr(a, 'v6_momentum_adj', None),

        # MEGA BUY Full Details (DMI, RSI, Volume, LazyBar, EC per TF)
        'mega_buy_details': a.mega_buy_details or {},

        # Status
        'status': a.status
    })

db.close()
print(json.dumps(result))
`

    const output = await runPython(script)
    const alerts = JSON.parse(output.trim())
    return NextResponse.json({ alerts })
  } catch (error) {
    console.error("Error fetching alerts:", error)
    return NextResponse.json({ error: String(error), alerts: [] }, { status: 500 })
  }
}
