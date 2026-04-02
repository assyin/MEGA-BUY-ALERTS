"""
Real-time alert analysis module.

Fetches live Binance klines and computes ~197 indicator fields
using the existing engine.py functions.
"""

import json
import time
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from api.engine import (
    calc_rsi, calc_ema, calc_atr,
    calc_standard_ichimoku_cloud,
    calc_adx, calc_macd,
    calc_bollinger_bands, calc_stochastic_rsi,
    calc_adaptive_stochastic, calc_fibonacci_levels,
    detect_order_blocks, find_nearest_order_block,
    detect_fair_value_gaps, find_nearest_fvg,
    find_swing_highs,
    analyze_ema_stack, analyze_btc_trend,
)
from api.volume_profile import VolumeProfileAnalyzer

BINANCE_URL = "https://api.binance.com/api/v3/klines"


def get_klines_at_time(symbol: str, interval: str, limit: int = 500, end_ts_ms: int = None) -> pd.DataFrame:
    """
    Fetch klines from Binance ending at a specific timestamp.

    If end_ts_ms is provided, fetches the N bars BEFORE that timestamp.
    This gives us the market state AT the time of the alert, not now.
    If end_ts_ms is None, fetches the most recent bars (live mode).
    """
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    if end_ts_ms is not None:
        params['endTime'] = end_ts_ms

    try:
        resp = requests.get(BINANCE_URL, params=params, timeout=15)
        data = resp.json()
        if not data or isinstance(data, dict):
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_volume', 'trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['datetime'] = pd.to_datetime(df['open_time'], unit='ms')
    return df.reset_index(drop=True)


def _safe_float(v):
    """Convert numpy/pandas types to Python float for JSON serialization."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return None


def _compute_entry_conditions(klines: dict, alert_price: float = None) -> dict:
    """
    Compute the 6 progressive entry conditions.

    Uses alert_price (exact price at alert time) instead of candle close
    for price comparisons. Indicator values (EMA, Cloud) are from the
    last fully closed candle before the alert.
    """
    result = {}

    # Use alert_price for all "is price above X?" checks
    # Fall back to last candle close if alert_price not provided
    df_1h = klines.get('1h')
    df_4h = klines.get('4h')
    df_30m = klines.get('30m')

    price = alert_price  # exact price at alert moment

    # 1. EMA100 1H
    if df_1h is not None and len(df_1h) > 110:
        close_1h = df_1h['close'].values
        ema100 = calc_ema(close_1h, 100)
        p = price or close_1h[-1]
        ema100_val = ema100[-1]
        result['ema100_1h'] = {
            'valid': bool(p > ema100_val and ema100_val > 0),
            'price': _safe_float(p),
            'value': _safe_float(ema100_val),
            'distance_pct': _safe_float((p - ema100_val) / ema100_val * 100) if ema100_val > 0 else None,
        }

    # 2. EMA20 4H
    if df_4h is not None and len(df_4h) > 30:
        close_4h = df_4h['close'].values
        ema20 = calc_ema(close_4h, 20)
        p = price or close_4h[-1]
        ema20_val = ema20[-1]
        result['ema20_4h'] = {
            'valid': bool(p > ema20_val and ema20_val > 0),
            'price': _safe_float(p),
            'value': _safe_float(ema20_val),
            'distance_pct': _safe_float((p - ema20_val) / ema20_val * 100) if ema20_val > 0 else None,
        }

    # 3. Cloud Top 1H
    if df_1h is not None and len(df_1h) > 60:
        cloud_1h = calc_standard_ichimoku_cloud(
            df_1h['high'].values, df_1h['low'].values, df_1h['close'].values
        )
        cloud_val = cloud_1h[-1]
        p = price or df_1h['close'].values[-1]
        result['cloud_1h'] = {
            'valid': bool(p > cloud_val and cloud_val > 0),
            'price': _safe_float(p),
            'value': _safe_float(cloud_val),
            'distance_pct': _safe_float((p - cloud_val) / cloud_val * 100) if cloud_val > 0 else None,
        }

    # 4. Cloud Top 30M
    if df_30m is not None and len(df_30m) > 60:
        cloud_30m = calc_standard_ichimoku_cloud(
            df_30m['high'].values, df_30m['low'].values, df_30m['close'].values
        )
        cloud_val = cloud_30m[-1]
        p = price or df_30m['close'].values[-1]
        result['cloud_30m'] = {
            'valid': bool(p > cloud_val and cloud_val > 0),
            'price': _safe_float(p),
            'value': _safe_float(cloud_val),
            'distance_pct': _safe_float((p - cloud_val) / cloud_val * 100) if cloud_val > 0 else None,
        }

    # 5. CHoCH/BOS (1H) - uses alert_price to check if swing high broken
    if df_1h is not None and len(df_1h) > 20:
        high_1h = df_1h['high'].values
        close_1h = df_1h['close'].values
        shs = find_swing_highs(high_1h, left=5, right=3)
        choch_valid = False
        choch_price = None
        p = price or close_1h[-1]
        if shs:
            last_sh = shs[-1]
            margin = last_sh['price'] * 1.005
            if p > margin:
                choch_valid = True
                choch_price = last_sh['price']
        result['choch_bos'] = {
            'valid': choch_valid,
            'swing_high_price': _safe_float(choch_price),
            'current_price': _safe_float(p),
        }

    # Count
    valid_count = sum(1 for v in result.values() if isinstance(v, dict) and v.get('valid'))
    result['count'] = valid_count
    result['total'] = 5

    return result


def _compute_prerequisites(klines: dict, alert_price: float = None) -> dict:
    """Compute V5 prerequisites: STC, 15m filter, trendline."""
    result = {}

    # STC Oversold check on 15m, 30m, 1h
    stc_valid_tfs = []
    stc_values = {}
    for tf in ['15m', '30m', '1h']:
        df = klines.get(tf)
        if df is not None and len(df) > 250:
            close = df['close'].values
            stc = calc_adaptive_stochastic(close, length=50, fast=50, slow=200)
            stc_val = stc[-1] if len(stc) > 0 else None
            stc_values[tf] = _safe_float(stc_val)
            if stc_val is not None and stc_val < 0.2:
                stc_valid_tfs.append(tf)

    result['stc_oversold'] = {
        'valid': len(stc_valid_tfs) > 0,
        'valid_tfs': stc_valid_tfs,
        'values': stc_values,
    }

    # Trendline detection on 4H, 1H, 30M — find best descending resistance
    # Try each TF and pick the closest/most relevant trendline
    tl_found = False
    tl_data = {}
    best_tl_distance = float('inf')

    for tf_key in ['4h', '1h', '30m']:
        df_tf = klines.get(tf_key)
        if df_tf is None or len(df_tf) < 30:
            continue

        high_tf = df_tf['high'].values
        datetimes_tf = df_tf['datetime'].values if 'datetime' in df_tf.columns else None
        shs = find_swing_highs(high_tf, left=5, right=3)
        current_price = alert_price if alert_price else high_tf[-1]

        if len(shs) < 2:
            continue

        # Find best descending trendline on this TF
        tf_best_p1 = None
        tf_best_p2 = None
        tf_best_dist = float('inf')

        for i in range(len(shs) - 1):
            for j in range(i + 1, len(shs)):
                p1c = shs[i]
                p2c = shs[j]
                # P1 >= P2 (descending) and both above or near current price
                if (p1c['price'] >= p2c['price'] * 0.98 and
                    p2c['price'] >= current_price * 0.90 and
                    p2c['idx'] - p1c['idx'] >= 3):
                    # Calculate where trendline would be at current bar
                    slope = (p2c['price'] - p1c['price']) / (p2c['idx'] - p1c['idx'])
                    tl_at_now = p2c['price'] + slope * (len(df_tf) - 1 - p2c['idx'])
                    dist = abs(tl_at_now - current_price) / current_price * 100
                    if dist < tf_best_dist:
                        tf_best_dist = dist
                        tf_best_p1 = p1c
                        tf_best_p2 = p2c

        # Fallback: last 2 swing highs
        if tf_best_p1 is None:
            tf_best_p1 = shs[-2]
            tf_best_p2 = shs[-1]
            slope = (tf_best_p2['price'] - tf_best_p1['price']) / max(1, tf_best_p2['idx'] - tf_best_p1['idx'])
            tl_at_now = tf_best_p2['price'] + slope * (len(df_tf) - 1 - tf_best_p2['idx'])
            tf_best_dist = abs(tl_at_now - current_price) / current_price * 100

        # Keep the trendline closest to current price across all TFs
        if tf_best_dist < best_tl_distance and datetimes_tf is not None:
            best_tl_distance = tf_best_dist
            tl_found = True
            tl_data = {
                'tf': tf_key,
                'p1_price': _safe_float(tf_best_p1['price']),
                'p1_idx': tf_best_p1['idx'],
                'p1_time': int(pd.Timestamp(datetimes_tf[tf_best_p1['idx']]).timestamp() * 1000),
                'p1_date': str(datetimes_tf[tf_best_p1['idx']]),
                'p2_price': _safe_float(tf_best_p2['price']),
                'p2_idx': tf_best_p2['idx'],
                'p2_time': int(pd.Timestamp(datetimes_tf[tf_best_p2['idx']]).timestamp() * 1000),
                'p2_date': str(datetimes_tf[tf_best_p2['idx']]),
                'slope': 'descending' if tf_best_p1['price'] > tf_best_p2['price'] else 'ascending',
                'distance_pct': _safe_float(best_tl_distance),
                'price_at_alert': _safe_float(tf_best_p2['price']),
            }

    result['trendline'] = {
        'valid': tl_found,
        'price': _safe_float(tl_data.get('p2_price')),
        **tl_data,
    }

    return result


def _compute_bonus_filters(klines: dict, alert_price: float = None) -> dict:
    """Compute all 22 bonus filters using alert_price for comparisons."""
    result = {}

    # --- Fibonacci 4H ---
    df_4h = klines.get('4h')
    if df_4h is not None and len(df_4h) > 50:
        fib = calc_fibonacci_levels(df_4h['high'].values, df_4h['low'].values, df_4h['close'].values, lookback=50)
        if fib:
            price = alert_price or df_4h['close'].values[-1]
            fib_38 = fib['levels'].get(0.382, 0)
            result['fib_4h'] = {
                'bonus': bool(price > fib_38),
                'price': _safe_float(price),
                'level_382': _safe_float(fib_38),
                'swing_high': _safe_float(fib.get('swing_high')),
                'swing_low': _safe_float(fib.get('swing_low')),
                'levels': {str(k): _safe_float(v) for k, v in fib.get('levels', {}).items()},
            }
        else:
            result['fib_4h'] = {'bonus': False}
    else:
        result['fib_4h'] = {'bonus': False}

    # --- Fibonacci 1H ---
    df_1h = klines.get('1h')
    if df_1h is not None and len(df_1h) > 50:
        fib_1h = calc_fibonacci_levels(df_1h['high'].values, df_1h['low'].values, df_1h['close'].values, lookback=50)
        if fib_1h:
            price = alert_price or df_1h['close'].values[-1]
            fib_38 = fib_1h['levels'].get(0.382, 0)
            result['fib_1h'] = {
                'bonus': bool(price > fib_38),
                'level_382': _safe_float(fib_38),
                'levels': {str(k): _safe_float(v) for k, v in fib_1h.get('levels', {}).items()},
            }
        else:
            result['fib_1h'] = {'bonus': False}
    else:
        result['fib_1h'] = {'bonus': False}

    # --- Order Blocks 1H + 4H (detailed) ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 50:
            obs = detect_order_blocks(
                df['open'].values, df['high'].values, df['low'].values,
                df['close'].values, df['datetime'].values, lookback=100
            )
            entry_price = alert_price or df['close'].values[-1]
            nearest = find_nearest_order_block(obs, entry_price, proximity_pct=3.0) if obs else None

            # Build detailed OB list (max 5 closest)
            ob_list = []
            for ob in sorted(obs, key=lambda x: abs(entry_price - (x['high'] + x['low'])/2))[:5]:
                ob_mid = (ob['high'] + ob['low']) / 2
                distance_pct = (entry_price - ob_mid) / ob_mid * 100 if ob_mid > 0 else 0
                position = 'INSIDE' if ob['low'] <= entry_price <= ob['high'] else ('ABOVE' if entry_price > ob['high'] else 'BELOW')
                ob_list.append({
                    'zone_high': _safe_float(ob['high']),
                    'zone_low': _safe_float(ob['low']),
                    'strength': ob.get('strength', 0),
                    'type': ob.get('type', 'BULLISH'),
                    'datetime': str(ob.get('datetime', '')),
                    'age_bars': ob.get('age_bars', 0),
                    'mitigated': ob.get('mitigated', False),
                    'impulse_pct': _safe_float(ob.get('impulse_pct', 0)),
                    'distance_pct': _safe_float(distance_pct),
                    'position': position,
                })

            result[f'ob_{tf}'] = {
                'bonus': nearest is not None,
                'count': len(obs),
                'blocks': ob_list,
                'nearest': {
                    'zone_high': _safe_float(nearest['high']),
                    'zone_low': _safe_float(nearest['low']),
                    'strength': nearest.get('strength'),
                    'type': nearest.get('type'),
                    'distance_pct': _safe_float((entry_price - (nearest['high']+nearest['low'])/2) / ((nearest['high']+nearest['low'])/2) * 100) if nearest else None,
                    'position': 'INSIDE' if nearest and nearest['low'] <= entry_price <= nearest['high'] else ('ABOVE' if nearest and entry_price > nearest['high'] else 'BELOW'),
                } if nearest else None,
            }
        else:
            result[f'ob_{tf}'] = {'bonus': False, 'count': 0, 'blocks': []}

    # --- FVG 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 50:
            fvgs = detect_fair_value_gaps(
                df['high'].values, df['low'].values, df['close'].values,
                df['open'].values, df['datetime'].values, lookback=50
            )
            entry_price = alert_price or df['close'].values[-1]
            nearest = find_nearest_fvg(fvgs, entry_price, len(df) - 1) if fvgs else None
            result[f'fvg_{tf}'] = {
                'bonus': nearest is not None,
                'count': len(fvgs),
                'position': nearest.get('position') if nearest else None,
            }
        else:
            result[f'fvg_{tf}'] = {'bonus': False, 'count': 0}

    # --- BTC/ETH Correlation 1H + 4H ---
    for asset in ['btc', 'eth']:
        for tf in ['1h', '4h']:
            key = f'{asset}_{tf}'
            df = klines.get(key)
            if df is not None and len(df) > 60:
                close = df['close'].values
                high = df['high'].values
                low = df['low'].values
                trend_data = analyze_btc_trend(close, high, low, len(df) - 1)
                if trend_data:
                    result[f'{asset}_corr_{tf}'] = {
                        'bonus': trend_data.get('is_bonus', False),
                        'trend': trend_data.get('trend', 'UNKNOWN'),
                        'price': _safe_float(trend_data.get('price')),
                        'rsi': _safe_float(trend_data.get('rsi')),
                    }
                else:
                    result[f'{asset}_corr_{tf}'] = {'bonus': False, 'trend': 'N/A'}
            else:
                result[f'{asset}_corr_{tf}'] = {'bonus': False, 'trend': 'N/A'}

    # --- Volume Spike 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 20:
            vol = df['volume'].values
            avg_vol = np.mean(vol[-21:-1]) if len(vol) > 21 else np.mean(vol[:-1])
            cur_vol = vol[-1]
            ratio = cur_vol / avg_vol if avg_vol > 0 else 0
            result[f'vol_spike_{tf}'] = {
                'bonus': bool(ratio >= 2.0),
                'ratio': _safe_float(ratio),
                'level': 'VERY_HIGH' if ratio >= 3 else 'HIGH' if ratio >= 2 else 'NORMAL',
            }
        else:
            result[f'vol_spike_{tf}'] = {'bonus': False, 'ratio': 0}

    # --- RSI Multi-TF ---
    rsi_values = {}
    for tf_key, tf_df in [('1h', df_1h), ('4h', df_4h), ('1d', klines.get('1d'))]:
        if tf_df is not None and len(tf_df) > 15:
            rsi = calc_rsi(tf_df['close'].values, 14)
            rsi_values[tf_key] = _safe_float(rsi[-1])
        else:
            rsi_values[tf_key] = None
    rsi_above = sum(1 for v in rsi_values.values() if v is not None and v > 50)
    result['rsi_mtf'] = {
        'bonus': rsi_above == len([v for v in rsi_values.values() if v is not None]),
        'values': rsi_values,
        'aligned_count': rsi_above,
    }

    # --- ADX 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 20:
            adx, di_plus, di_minus = calc_adx(df['high'].values, df['low'].values, df['close'].values)
            result[f'adx_{tf}'] = {
                'bonus': bool(adx[-1] > 25),
                'adx': _safe_float(adx[-1]),
                'di_plus': _safe_float(di_plus[-1]),
                'di_minus': _safe_float(di_minus[-1]),
                'di_spread': _safe_float(di_plus[-1] - di_minus[-1]),
                'strength': 'STRONG' if adx[-1] > 25 else 'MODERATE' if adx[-1] > 20 else 'WEAK',
            }
        else:
            result[f'adx_{tf}'] = {'bonus': False}

    # --- MACD 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 30:
            macd_line, signal, histogram = calc_macd(df['close'].values)
            hist_growing = bool(histogram[-1] > histogram[-2]) if len(histogram) > 1 else False
            result[f'macd_{tf}'] = {
                'bonus': bool(histogram[-1] > 0 and hist_growing),
                'line': _safe_float(macd_line[-1]),
                'signal': _safe_float(signal[-1]),
                'histogram': _safe_float(histogram[-1]),
                'growing': hist_growing,
                'trend': 'BULLISH' if histogram[-1] > 0 else 'BEARISH',
            }
        else:
            result[f'macd_{tf}'] = {'bonus': False}

    # --- Bollinger Bands 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 25:
            upper, middle, lower, width = calc_bollinger_bands(df['close'].values)
            price = alert_price or df['close'].values[-1]
            squeeze = bool(width[-1] < 2.0)
            breakout = 'UP' if price > upper[-1] else 'DOWN' if price < lower[-1] else 'NONE'
            result[f'bb_{tf}'] = {
                'bonus': bool(squeeze and breakout == 'UP'),
                'upper': _safe_float(upper[-1]),
                'middle': _safe_float(middle[-1]),
                'lower': _safe_float(lower[-1]),
                'width_pct': _safe_float(width[-1]),
                'squeeze': squeeze,
                'breakout': breakout,
            }
        else:
            result[f'bb_{tf}'] = {'bonus': False}

    # --- Stochastic RSI 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 40:
            k, d = calc_stochastic_rsi(df['close'].values)
            k_val, d_val = k[-1], d[-1]
            zone = 'OVERSOLD' if k_val < 20 else 'OVERBOUGHT' if k_val > 80 else 'NEUTRAL'
            cross = 'BULLISH' if k_val > d_val else 'BEARISH'
            result[f'stochrsi_{tf}'] = {
                'bonus': bool(zone == 'OVERSOLD' and cross == 'BULLISH'),
                'k': _safe_float(k_val),
                'd': _safe_float(d_val),
                'zone': zone,
                'cross': cross,
            }
        else:
            result[f'stochrsi_{tf}'] = {'bonus': False}

    # --- EMA Stack 1H + 4H ---
    for tf, df in [('1h', df_1h), ('4h', df_4h)]:
        if df is not None and len(df) > 110:
            stack = analyze_ema_stack(df['close'].values, len(df) - 1)
            if stack:
                result[f'ema_stack_{tf}'] = {
                    'bonus': stack.get('is_bonus', False),
                    'count': stack.get('stack_count', 0),
                    'trend': stack.get('trend', 'UNKNOWN'),
                    'ema8': _safe_float(stack.get('ema8')),
                    'ema21': _safe_float(stack.get('ema21')),
                    'ema50': _safe_float(stack.get('ema50')),
                    'ema100': _safe_float(stack.get('ema100')),
                }
            else:
                result[f'ema_stack_{tf}'] = {'bonus': False}
        else:
            result[f'ema_stack_{tf}'] = {'bonus': False}

    # Count total bonuses
    bonus_count = sum(1 for v in result.values() if isinstance(v, dict) and v.get('bonus'))
    total_filters = len([v for v in result.values() if isinstance(v, dict) and 'bonus' in v])
    result['count'] = bonus_count
    result['total'] = total_filters

    return result


def _compute_volume_profile(klines: dict, alert_price: float = None) -> dict:
    """Compute Volume Profile for 1H and 4H."""
    result = {}
    vp_analyzer = VolumeProfileAnalyzer()

    for tf_key, lookback in [('1h', 100), ('4h', 50)]:
        df = klines.get(tf_key)
        if df is None or len(df) < 20:
            result[tf_key] = None
            continue

        try:
            vp_data = vp_analyzer.calculate(df, lookback=lookback)
            if not vp_data or vp_data.get('poc') is None:
                result[tf_key] = None
                continue

            entry_price = alert_price or df['close'].values[-1]
            poc = vp_data.get('poc', 0)
            vah = vp_data.get('vah', 0)
            val_ = vp_data.get('val', 0)

            # Determine position
            if val_ <= entry_price <= vah:
                position = 'IN_VA'
            elif entry_price > vah:
                position = 'ABOVE_VAH'
            elif entry_price < val_:
                position = 'BELOW_VAL'
            else:
                position = 'UNKNOWN'

            # Distance to POC
            poc_dist = ((entry_price - poc) / poc * 100) if poc > 0 else 0

            # HVN/LVN levels
            hvn_levels = [_safe_float(h) for h in vp_data.get('hvn_levels', [])[:5]]
            lvn_levels = [_safe_float(l) for l in vp_data.get('lvn_levels', [])[:5]]

            result[tf_key] = {
                'poc': _safe_float(poc),
                'vah': _safe_float(vah),
                'val': _safe_float(val_),
                'position': position,
                'poc_distance_pct': _safe_float(poc_dist),
                'hvn_levels': hvn_levels,
                'lvn_levels': lvn_levels,
                'entry_price': _safe_float(entry_price),
            }
        except Exception as e:
            result[tf_key] = {'error': str(e)}

    return result


def _compute_indicators(klines: dict, alert_price: float = None) -> dict:
    """Compute indicator values from last closed candle. Price = alert_price."""
    result = {}

    for tf_key in ['15m', '30m', '1h', '4h', '1d']:
        df = klines.get(tf_key)
        if df is None or len(df) < 15:
            continue

        close = df['close'].values
        high = df['high'].values
        low = df['low'].values

        # Show alert_price as "price" for main pair, candle close for BTC/ETH
        tf_data = {'price': _safe_float(alert_price or close[-1])}

        # RSI
        rsi = calc_rsi(close, 14)
        tf_data['rsi'] = _safe_float(rsi[-1])

        # ADX/DI
        if len(df) > 20:
            adx, di_plus, di_minus = calc_adx(high, low, close)
            tf_data['adx'] = _safe_float(adx[-1])
            tf_data['di_plus'] = _safe_float(di_plus[-1])
            tf_data['di_minus'] = _safe_float(di_minus[-1])

        # EMA
        if len(df) > 110:
            tf_data['ema20'] = _safe_float(calc_ema(close, 20)[-1])
            tf_data['ema50'] = _safe_float(calc_ema(close, 50)[-1])
            tf_data['ema100'] = _safe_float(calc_ema(close, 100)[-1])

        # Cloud
        if len(df) > 60:
            cloud = calc_standard_ichimoku_cloud(high, low, close)
            tf_data['cloud_top'] = _safe_float(cloud[-1])

        # STC
        if len(df) > 250:
            stc = calc_adaptive_stochastic(close, length=50, fast=50, slow=200)
            tf_data['stc'] = _safe_float(stc[-1])

        result[tf_key] = tf_data

    return result


def _parse_alert_timestamp(timestamp: str):
    """Parse alert timestamp to milliseconds for Binance endTime."""
    if not timestamp:
        return None
    try:
        ts = timestamp.replace('Z', '+00:00')
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return int(dt.timestamp() * 1000)
    except Exception:
        return None


def _floor_to_interval(ts_ms: int, interval: str) -> int:
    """
    Floor a timestamp to the START of its candle interval.

    This ensures we only get FULLY CLOSED candles before the alert.
    Example: alert at 11:03:34 on 1h interval → endTime = 11:00:00
    So the last candle returned is 10:00-11:00 (fully closed).
    """
    interval_ms = {
        '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000,
        '1h':  60 * 60 * 1000,
        '4h':  4 * 60 * 60 * 1000,
        '1d':  24 * 60 * 60 * 1000,
    }
    ms = interval_ms.get(interval, 60 * 60 * 1000)
    # Floor to interval start, then subtract 1ms to exclude the open candle
    return (ts_ms // ms) * ms - 1


def analyze_alert_realtime(pair: str, timestamp: str = '', alert_price: float = 0) -> dict:
    """
    Compute full technical analysis for an alert AT THE TIME of the alert.

    Uses only FULLY CLOSED candles before the alert timestamp so that
    indicator values reflect the market state when the alert fired,
    NOT the state after the candle containing the alert closed.

    Args:
        pair: Trading pair (e.g., 'BTCUSDT')
        timestamp: Alert timestamp (ISO format). If provided, fetches data
                   using only candles that closed BEFORE this time.
                   If empty, uses current time (live analysis).
        alert_price: The exact price at alert time (from Supabase).
                     Used as "current price" instead of the last candle close.

    Returns:
        Dict with all computed fields, JSON-serializable
    """
    start_time = time.time()
    pair = pair.upper()

    # Parse timestamp
    end_ts_ms = _parse_alert_timestamp(timestamp)
    mode = 'historical' if end_ts_ms else 'live'

    # Fetch klines (9 calls, ~50ms between each)
    # For historical mode: floor endTime to interval start so we only get
    # fully closed candles BEFORE the alert fired
    klines = {}
    fetch_plan = [
        (pair, '15m', 300),
        (pair, '30m', 500),
        (pair, '1h', 500),
        (pair, '4h', 200),
        (pair, '1d', 100),
        ('BTCUSDT', '1h', 200),
        ('BTCUSDT', '4h', 100),
        ('ETHUSDT', '1h', 200),
        ('ETHUSDT', '4h', 100),
    ]

    for symbol, interval, limit in fetch_plan:
        key = interval if symbol == pair else f"{'btc' if 'BTC' in symbol else 'eth'}_{interval}"
        # Floor endTime per interval to get only fully closed candles
        floored_end = _floor_to_interval(end_ts_ms, interval) if end_ts_ms else None
        klines[key] = get_klines_at_time(symbol, interval, limit, floored_end)
        time.sleep(0.05)

    fetch_time = time.time() - start_time

    # Use alert_price as the "current price" for all calculations
    # This is the exact price when the alert fired, not the candle close
    ap = alert_price if alert_price > 0 else None

    # Compute all sections
    entry_conditions = _compute_entry_conditions(klines, ap)
    prerequisites = _compute_prerequisites(klines, ap)
    bonus_filters = _compute_bonus_filters(klines, ap)
    indicators = _compute_indicators(klines, ap)
    volume_profile = _compute_volume_profile(klines, ap)

    # Futures data (funding rate + open interest)
    futures_data = _compute_futures_data(pair, ap)

    # Accumulation detection (uses 4H klines already loaded)
    accumulation = _compute_accumulation(klines, ap)

    compute_time = time.time() - start_time - fetch_time

    return {
        'pair': pair,
        'timestamp': timestamp,
        'alert_price': alert_price if alert_price > 0 else None,
        'mode': mode,
        'computed_at': datetime.now(timezone.utc).isoformat(),
        'timing': {
            'fetch_seconds': round(fetch_time, 2),
            'compute_seconds': round(compute_time, 2),
            'total_seconds': round(time.time() - start_time, 2),
        },
        'entry_conditions': entry_conditions,
        'prerequisites': prerequisites,
        'bonus_filters': bonus_filters,
        'indicators': indicators,
        'volume_profile': volume_profile,
        'futures_data': futures_data,
        'accumulation': accumulation,
    }


def _compute_accumulation(klines: dict, alert_price: float = None) -> dict:
    """Detect accumulation phase by analyzing 4H klines backward.

    Walks backward from the most recent candle and counts consecutive candles
    where the price stays within a tight range (< 10% from the range's low).
    Uses REAL kline data, not proxies.

    Returns:
        {
            "detected": True/False,
            "days": 6.8,
            "hours": 164,
            "candles_4h": 41,
            "range_pct": 8.5,
            "range_high": 0.142,
            "range_low": 0.131,
            "volume_trend": "decreasing"  (volume decreasing during accumulation = stronger)
        }
    """
    try:
        k4h = klines.get('4h')
        if k4h is None or (hasattr(k4h, 'empty') and k4h.empty) or len(k4h) < 10:
            return {"detected": False, "days": 0, "reason": "insufficient 4H data"}

        # Get OHLCV from 4H klines — handle both DataFrame and raw list formats
        if hasattr(k4h, 'columns'):
            # DataFrame format
            closes = k4h['close'].astype(float).tolist()
            highs = k4h['high'].astype(float).tolist()
            lows = k4h['low'].astype(float).tolist()
            volumes = k4h['volume'].astype(float).tolist()
        else:
            # Raw list format [[ts, o, h, l, c, v, ...], ...]
            closes = [float(c[4]) for c in k4h]
            highs = [float(c[2]) for c in k4h]
            lows = [float(c[3]) for c in k4h]
            volumes = [float(c[5]) for c in k4h]

        if not closes:
            return {"detected": False, "days": 0}

        # Walk backward from the last candle
        # Define the initial range from the last candle
        n = len(closes)
        range_high = highs[-1]
        range_low = lows[-1]
        acc_count = 1

        for i in range(n - 2, max(n - 120, -1), -1):  # Max 120 candles back (20 days)
            # Expand range with this candle
            new_high = max(range_high, highs[i])
            new_low = min(range_low, lows[i])
            range_pct = (new_high - new_low) / new_low * 100 if new_low > 0 else 0

            if range_pct <= 10:
                # Still in accumulation range
                range_high = new_high
                range_low = new_low
                acc_count += 1
            else:
                # Price broke out of range — accumulation ends here
                break

        hours = acc_count * 4
        days = round(hours / 24, 1)

        final_range_pct = round((range_high - range_low) / range_low * 100, 2) if range_low > 0 else 0

        # Volume trend during accumulation (is volume decreasing?)
        if acc_count >= 3:
            acc_volumes = volumes[-(acc_count):]
            first_half_vol = sum(acc_volumes[:len(acc_volumes)//2])
            second_half_vol = sum(acc_volumes[len(acc_volumes)//2:])
            vol_trend = "decreasing" if second_half_vol < first_half_vol * 0.8 else "stable" if second_half_vol < first_half_vol * 1.2 else "increasing"
        else:
            vol_trend = "unknown"

        return {
            "detected": days >= 2,
            "days": days,
            "hours": hours,
            "candles_4h": acc_count,
            "range_pct": final_range_pct,
            "range_high": round(range_high, 8),
            "range_low": round(range_low, 8),
            "volume_trend": vol_trend,
        }
    except Exception as e:
        return {"detected": False, "days": 0, "error": str(e)}


def _compute_futures_data(symbol: str, alert_price: float = None) -> dict:
    """
    Fetch funding rate and open interest from Binance Futures API.

    Returns dict with funding rate, open interest, OI 24h change, and a signal.
    If the pair has no futures contract or the API fails, returns {"available": false}.
    """
    FAPI_BASE = "https://fapi.binance.com"
    TIMEOUT = 5

    try:
        # 1. Funding rate
        resp_fr = requests.get(
            f"{FAPI_BASE}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": 1},
            timeout=TIMEOUT,
        )
        if resp_fr.status_code != 200:
            return {"available": False, "reason": "no futures contract"}
        fr_data = resp_fr.json()
        if not fr_data or isinstance(fr_data, dict):
            return {"available": False, "reason": "no futures contract"}
        funding_rate = float(fr_data[0].get("fundingRate", 0))

        time.sleep(0.05)

        # 2. Current open interest
        resp_oi = requests.get(
            f"{FAPI_BASE}/fapi/v1/openInterest",
            params={"symbol": symbol},
            timeout=TIMEOUT,
        )
        if resp_oi.status_code != 200:
            return {"available": False, "reason": "open interest unavailable"}
        oi_data = resp_oi.json()
        open_interest = float(oi_data.get("openInterest", 0))

        time.sleep(0.05)

        # 3. Open interest history (24h)
        resp_oi_hist = requests.get(
            f"{FAPI_BASE}/futures/data/openInterestHist",
            params={"symbol": symbol, "period": "1h", "limit": 24},
            timeout=TIMEOUT,
        )
        oi_change_24h_pct = 0.0
        if resp_oi_hist.status_code == 200:
            oi_hist = resp_oi_hist.json()
            if oi_hist and isinstance(oi_hist, list) and len(oi_hist) >= 2:
                oi_oldest = float(oi_hist[0].get("sumOpenInterest", 0))
                oi_newest = float(oi_hist[-1].get("sumOpenInterest", 0))
                if oi_oldest > 0:
                    oi_change_24h_pct = round((oi_newest - oi_oldest) / oi_oldest * 100, 2)

        # Compute OI in USDT
        price = alert_price if alert_price and alert_price > 0 else 0
        open_interest_usd = round(open_interest * price, 2) if price > 0 else None

        # Determine signal
        oi_rising = oi_change_24h_pct > 2.0
        oi_dropping = oi_change_24h_pct < -2.0
        funding_negative = funding_rate < 0
        funding_positive = funding_rate > 0.0005  # above neutral threshold

        if funding_negative and oi_rising:
            signal = "BULLISH"
        elif funding_positive and oi_dropping:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "available": True,
            "funding_rate": funding_rate,
            "funding_rate_pct": round(funding_rate * 100, 6),
            "open_interest": open_interest,
            "open_interest_usd": open_interest_usd,
            "oi_change_24h_pct": oi_change_24h_pct,
            "signal": signal,
        }

    except Exception:
        return {"available": False, "reason": "no futures contract"}


if __name__ == '__main__':
    import sys
    pair = sys.argv[1] if len(sys.argv) > 1 else 'BTCUSDT'
    ts = sys.argv[2] if len(sys.argv) > 2 else ''
    result = analyze_alert_realtime(pair, ts)
    print(json.dumps(result, indent=2))
