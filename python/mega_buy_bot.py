"""
🟢 MEGA BUY Scanner Bot v2 — Binance + Telegram
Scanne 500+ paires USDT toutes les 30 min
Score /10 — 3 obligatoires (RSI, DMI, AST) + 7 optionnelles
Inclut EC (Entry Confirmation) + CHoCH (swing high break)
Filtre candle pump max %

Auteur: ASSYIN-2026
"""

import requests
import numpy as np
import pandas as pd
import time
import os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False

# Supabase — Push alerts to database
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    from supabase import create_client
    _supabase_url = os.getenv("SUPABASE_URL", "")
    _supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "")
    if _supabase_url and _supabase_key:
        _supabase = create_client(_supabase_url, _supabase_key)
        SUPABASE_OK = True
        print("✅ Supabase connected")
    else:
        _supabase = None
        SUPABASE_OK = False
        print("⚠️ Supabase: missing SUPABASE_URL or SUPABASE_SERVICE_KEY in .env")
except Exception as e:
    _supabase = None
    SUPABASE_OK = False
    print(f"⚠️ Supabase not available: {e}")

# ═══════════════════════════════════════════════════════
# ⚙️ CONFIGURATION — MODIFIER ICI
# ═══════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "COLLE_TON_TOKEN_ICI")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "COLLE_TON_CHAT_ID_ICI")

# Google Sheets — Logging des alertes
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEET_NAME = "MEGA BUY Alerts"              # Nom du Google Sheet
GOOGLE_CREDS_FILE = "google_creds.json"             # Fichier credentials Service Account

TIMEFRAMES = ["15m", "30m", "1h", "4h"]   # Multi-TF scan
SCAN_INTERVAL_MIN = 7                      # 7 min (2x per 15m candle for faster detection)
MIN_VOLUME_USDT = 500_000

# ═══════════════════════════════════════════════════════
# ⚙️ PARAMÈTRES INDICATEURS (identiques PineScript v7)
# ═══════════════════════════════════════════════════════
# RSI
RSI_LENGTH = 14
RSI_MIN_MOVE_BUY = 12.0

# DMI
DMI_LENGTH = 14
DMI_ADX_SMOOTH = 14
DMI_MIN_MOVE_PLUS = 10.0

# ASSYIN SuperTrend
AST_FACTOR = 3.0
AST_PERIOD = 10

# Classic SuperTrend
ST_FACTOR = 3.0
ST_PERIOD = 10

# PP SuperTrend
PP_PIVOT_PERIOD = 2
PP_ATR_FACTOR = 3.0
PP_ATR_PERIOD = 10

# ATR + Volume Regime
AV_ATR_LENGTH = 14
AV_ATR_SMOOTH = 10
AV_ATR_THRESHOLD = 1.2
AV_VOL_LENGTH = 20
AV_VOL_THRESHOLD = 1.5
AV_MIN_MOVE = 250.0

# LazyBar
LB_SPIKE_THRESH = 6.0

# Entry Confirmation (EC)
EC_RSI_PERIOD = 50
EC_SLOW_MA_PERIOD = 50
EC_MIN_MOVE_RSI = 3.0
EC_MIN_MOVE_SLOW_MA = 1.5
EC_PIVOT_LB = 5          # Lookback left & right for divergence pivots
EC_BULL_DIV_MEMORY = 10   # Bars to remember a bullish divergence

# CHoCH — Swing High Break (ta.pivothigh 10,5)
CHOCH_PIVOT_LEFT = 10
CHOCH_PIVOT_RIGHT = 5
CHOCH_BREAK_WINDOW = 6    # Bougies max après break

# MEGA BUY
COMBO_WINDOW = 3
COMBO_THRESHOLD_PCT = 50
MAX_CANDLE_MOVE_PCT = 15.0

# ═══════════════════════════════════════════════════════
# 📡 BINANCE API
# ═══════════════════════════════════════════════════════
BINANCE_BASE = "https://api.binance.com"

# Session HTTP avec connection pooling (thread-safe)
_http_session = requests.Session()
_http_session.mount('https://', requests.adapters.HTTPAdapter(
    pool_connections=20, pool_maxsize=20, max_retries=2))


def _get_trading_symbols():
    """Get symbols with TRADING status from Binance exchangeInfo.
    Excludes delisted pairs (BREAK status)."""
    try:
        url = f"{BINANCE_BASE}/api/v3/exchangeInfo"
        resp = _http_session.get(url, timeout=15)
        data = resp.json()
        return {s["symbol"] for s in data.get("symbols", [])
                if s.get("status") == "TRADING" and s["symbol"].endswith("USDT")}
    except Exception:
        return None  # Fallback: don't filter

_trading_cache = None
_trading_cache_time = 0

def get_24h_volumes():
    global _trading_cache, _trading_cache_time
    url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
    resp = _http_session.get(url, timeout=30)
    data = resp.json()

    # Refresh trading status cache every hour
    if _trading_cache is None or (time.time() - _trading_cache_time) > 3600:
        _trading_cache = _get_trading_symbols()
        _trading_cache_time = time.time()
        if _trading_cache:
            print(f"📋 Trading pairs refreshed: {len(_trading_cache)} active")

    volumes = {}
    for t in data:
        symbol = t["symbol"]
        if symbol.endswith("USDT"):
            # Skip if not in TRADING status (delisted/halted)
            if _trading_cache and symbol not in _trading_cache:
                continue
            volumes[symbol] = float(t["quoteVolume"])
    return volumes


def get_klines(symbol, interval="30m", limit=200):
    url = f"{BINANCE_BASE}/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = _http_session.get(url, params=params, timeout=15)
    data = resp.json()
    if not isinstance(data, list) or len(data) < 50:
        return None
    df = pd.DataFrame(data, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore"
    ])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


# ═══════════════════════════════════════════════════════
# 📊 FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════
def rma(series, length):
    alpha = 1.0 / length
    result = np.zeros(len(series))
    result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def ema(series, length):
    alpha = 2.0 / (length + 1)
    result = np.zeros(len(series))
    result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result


def sma(series, length):
    result = np.full(len(series), np.nan)
    for i in range(length - 1, len(series)):
        result[i] = np.mean(series[i - length + 1:i + 1])
    return result


def true_range(high, low, close):
    tr = np.zeros(len(high))
    tr[0] = high[0] - low[0]
    for i in range(1, len(high)):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i - 1]),
                     abs(low[i] - close[i - 1]))
    return tr


# ═══════════════════════════════════════════════════════
# 📊 CALCULS DES INDICATEURS
# ═══════════════════════════════════════════════════════
def calc_rsi(close, length=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)
    avg_gain = rma(gain, length)
    avg_loss = rma(loss, length)
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(avg_loss == 0, 100, avg_gain / avg_loss)
        return np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))


def calc_dmi(high, low, close, length=14, adx_smooth=14):
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        dn = low[i - 1] - low[i]
        plus_dm[i] = up if (up > dn and up > 0) else 0
        minus_dm[i] = dn if (dn > up and dn > 0) else 0
    tr = true_range(high, low, close)
    atr_vals = rma(tr, length)
    atr_safe = np.where(atr_vals == 0, 1, atr_vals)
    plus_di = 100 * rma(plus_dm, length) / atr_safe
    minus_di = 100 * rma(minus_dm, length) / atr_safe
    di_sum = plus_di + minus_di
    dx = 100 * np.abs(plus_di - minus_di) / np.where(di_sum == 0, 1, di_sum)
    adx = rma(dx, adx_smooth)
    return plus_di, minus_di, adx


def calc_supertrend(high, low, close, factor=3.0, period=10):
    n = len(high)
    tr = true_range(high, low, close)
    atr_vals = rma(tr, period)
    hl2 = (high + low) / 2
    upper = hl2 + factor * atr_vals
    lower = hl2 - factor * atr_vals
    direction = np.ones(n)
    final_upper = np.copy(upper)
    final_lower = np.copy(lower)
    for i in range(1, n):
        if close[i - 1] > final_upper[i - 1]:
            direction[i] = -1
        elif close[i - 1] < final_lower[i - 1]:
            direction[i] = 1
        else:
            direction[i] = direction[i - 1]
        if direction[i] == -1:
            final_lower[i] = max(lower[i], final_lower[i - 1]) if close[i - 1] > final_lower[i - 1] else lower[i]
        else:
            final_upper[i] = min(upper[i], final_upper[i - 1]) if close[i - 1] < final_upper[i - 1] else upper[i]
    return direction


def calc_assyin_supertrend(high, low, close, factor=3.0, period=10):
    n = len(high)
    tr = true_range(high, low, close)
    atr_vals = rma(tr, period)
    hl2 = (high + low) / 2
    upper_raw = hl2 + factor * atr_vals
    lower_raw = hl2 - factor * atr_vals
    upper_band = np.copy(upper_raw)
    lower_band = np.copy(lower_raw)
    ast_dir = np.ones(n)
    for i in range(1, n):
        lower_band[i] = max(lower_raw[i], lower_band[i - 1]) if close[i - 1] > lower_band[i - 1] else lower_raw[i]
        upper_band[i] = min(upper_raw[i], upper_band[i - 1]) if close[i - 1] < upper_band[i - 1] else upper_raw[i]
        if ast_dir[i - 1] == -1:
            ast_dir[i] = 1 if close[i] < lower_band[i] else -1
        else:
            ast_dir[i] = -1 if close[i] > upper_band[i] else 1
    return ast_dir


def calc_pp_supertrend(high, low, close, prd=2, factor=3.0, atr_period=10):
    n = len(high)
    center = np.full(n, np.nan)
    trend = np.ones(n, dtype=int)
    t_up = np.zeros(n)
    t_down = np.zeros(n)
    tr = true_range(high, low, close)
    atr_vals = rma(tr, atr_period)
    last_pp = np.nan
    for i in range(prd, n - prd):
        is_ph = all(high[i] > high[i - j] and high[i] > high[i + j]
                     for j in range(1, prd + 1) if i + j < n and i - j >= 0)
        is_pl = all(low[i] < low[i - j] and low[i] < low[i + j]
                     for j in range(1, prd + 1) if i + j < n and i - j >= 0)
        if is_ph:
            last_pp = high[i]
        if is_pl:
            last_pp = low[i]
        if not np.isnan(last_pp):
            center[i] = last_pp if np.isnan(center[i - 1]) else (center[i - 1] * 2 + last_pp) / 3
    for i in range(1, n):
        if np.isnan(center[i]) and not np.isnan(center[i - 1]):
            center[i] = center[i - 1]
    for i in range(1, n):
        if np.isnan(center[i]):
            continue
        up_val = center[i] - factor * atr_vals[i]
        dn_val = center[i] + factor * atr_vals[i]
        t_up[i] = max(up_val, t_up[i - 1]) if close[i - 1] > t_up[i - 1] else up_val
        t_down[i] = min(dn_val, t_down[i - 1]) if close[i - 1] < t_down[i - 1] else dn_val
        if close[i] > t_down[i - 1]:
            trend[i] = 1
        elif close[i] < t_up[i - 1]:
            trend[i] = -1
        else:
            trend[i] = trend[i - 1]
    return trend


def calc_atr_vol_regime(high, low, close, volume):
    n = len(high)
    tr = true_range(high, low, close)
    atr_raw = rma(tr, AV_ATR_LENGTH)
    atr_smoothed = ema(atr_raw, AV_ATR_SMOOTH)
    atr_slope = np.zeros(n)
    for i in range(1, n):
        if atr_smoothed[i - 1] != 0:
            atr_slope[i] = (atr_smoothed[i] - atr_smoothed[i - 1]) / atr_smoothed[i - 1] * 100
    atr_regime = np.zeros(n, dtype=int)
    for i in range(n):
        if atr_slope[i] > AV_ATR_THRESHOLD:
            atr_regime[i] = 1
        elif atr_slope[i] < -AV_ATR_THRESHOLD:
            atr_regime[i] = -1
    vol_ma = sma(volume, AV_VOL_LENGTH)
    vol_ma_safe = np.where(np.isnan(vol_ma) | (vol_ma == 0), 1, vol_ma)
    vol_ratio = volume / vol_ma_safe
    vol_change = np.zeros(n)
    for i in range(1, n):
        vol_change[i] = (volume[i] - volume[i - 1]) / vol_ma_safe[i] * 100
    vol_regime = np.zeros(n, dtype=int)
    for i in range(n):
        if vol_ratio[i] > AV_VOL_THRESHOLD:
            vol_regime[i] = 1
        elif vol_ratio[i] < 0.8:
            vol_regime[i] = -1
    regime = np.zeros(n, dtype=int)
    for i in range(n):
        if atr_regime[i] == 1 and vol_regime[i] == 1:
            regime[i] = 1
        elif atr_regime[i] == -1 and vol_regime[i] == -1:
            regime[i] = -1
    return regime, np.abs(vol_change), vol_change


def calc_lazybar(high, low, close):
    n = len(high)
    ht = np.zeros(n)
    for i in range(4, n):
        lb_mid = sum(high[i-j] + low[i-j] for j in range(5)) / 10
        lb_scale = sum(high[i-j] - low[i-j] for j in range(5)) / 5 * 0.2
        if lb_scale != 0:
            ht[i] = (close[i] - lb_mid) / lb_scale
    return ht


def calc_ec(close, high, low):
    """Entry Confirmation V2 — RSI50, SlowMA, Bullish Divergence"""
    n = len(close)
    ec_rsi = calc_rsi(close, EC_RSI_PERIOD)
    ec_slow = sma(ec_rsi, EC_SLOW_MA_PERIOD)

    # Bullish divergence: find RSI pivot lows
    lb = EC_PIVOT_LB
    bull_div = np.zeros(n, dtype=bool)
    pivot_lows = []
    for i in range(lb, n - lb):
        is_piv = True
        for j in range(1, lb + 1):
            if ec_rsi[i] >= ec_rsi[i - j] or (i + j < n and ec_rsi[i] >= ec_rsi[i + j]):
                is_piv = False
                break
        if is_piv:
            pivot_lows.append(i)

    # Price lower low + RSI higher low = bullish divergence
    for k in range(1, len(pivot_lows)):
        curr, prev = pivot_lows[k], pivot_lows[k - 1]
        if low[curr] < low[prev] and ec_rsi[curr] > ec_rsi[prev]:
            conf = min(curr + lb, n - 1)
            bull_div[conf] = True

    return ec_rsi, ec_slow, bull_div


def calc_choch(high, close):
    """CHoCH — Swing High Break: ta.pivothigh(10,5) crossover, 6-bar window"""
    n = len(high)
    left = CHOCH_PIVOT_LEFT
    right = CHOCH_PIVOT_RIGHT

    last_swing_high = np.nan
    last_break_bar = -9999
    choch_active = np.zeros(n, dtype=bool)

    for i in range(left + right, n):
        # Check for confirmed pivot high at (i - right)
        pb = i - right
        if pb >= left:
            is_pivot = True
            for j in range(1, left + 1):
                if pb - j < 0 or high[pb] <= high[pb - j]:
                    is_pivot = False
                    break
            if is_pivot:
                for j in range(1, right + 1):
                    if pb + j >= n or high[pb] <= high[pb + j]:
                        is_pivot = False
                        break
            if is_pivot:
                last_swing_high = high[pb]

        # Crossover: close crosses above swing high
        if (not np.isnan(last_swing_high) and
                close[i] > last_swing_high and
                close[i - 1] <= last_swing_high):
            last_break_bar = i

        # Active within window
        if (i - last_break_bar) <= CHOCH_BREAK_WINDOW:
            choch_active[i] = True

    return choch_active


# ═══════════════════════════════════════════════════════
# 🎯 MEGA BUY DETECTION — Score /10
# ═══════════════════════════════════════════════════════
def detect_mega_buy(df):
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    opn = df["open"].values
    volume = df["volume"].values
    n = len(close)

    if n < 100:
        return None

    # --- Calculer tous les indicateurs ---
    rsi_vals = calc_rsi(close, RSI_LENGTH)
    plus_di, minus_di, adx = calc_dmi(high, low, close, DMI_LENGTH, DMI_ADX_SMOOTH)
    st_dir = calc_supertrend(high, low, close, ST_FACTOR, ST_PERIOD)
    ast_dir = calc_assyin_supertrend(high, low, close, AST_FACTOR, AST_PERIOD)
    pp_trend = calc_pp_supertrend(high, low, close, PP_PIVOT_PERIOD, PP_ATR_FACTOR, PP_ATR_PERIOD)
    regime, vol_move, vol_change = calc_atr_vol_regime(high, low, close, volume)
    ht = calc_lazybar(high, low, close)
    ec_rsi, ec_slow, ec_bull_div = calc_ec(close, high, low)
    choch_active = calc_choch(high, close)

    w = COMBO_WINDOW
    window = w * 2
    combo_min = int(np.ceil(10 * COMBO_THRESHOLD_PCT / 100))

    # Dernière bougie FERMÉE = n-2 (n-1 en cours)
    idx = n - 2
    if idx < window + 20:
        return None

    # === FILTRE CANDLE PUMP ===
    candle_move = max(abs(close[idx] - opn[idx]), high[idx] - low[idx])
    candle_pct = candle_move / min(opn[idx], low[idx]) * 100
    if candle_pct > MAX_CANDLE_MOVE_PCT:
        return None

    # Helper : chercher dans fenêtre
    def in_window(cond_fn):
        for i in range(max(1, idx - window), idx + 1):
            if i < n and cond_fn(i):
                return True
        return False

    # === 3 CONDITIONS OBLIGATOIRES ===
    rsi_ok = in_window(lambda i: (rsi_vals[i] - rsi_vals[i - 1]) >= RSI_MIN_MOVE_BUY)
    dmi_ok = in_window(lambda i: (plus_di[i] - plus_di[i - 1]) > 0 and
                                  abs(plus_di[i] - plus_di[i - 1]) >= DMI_MIN_MOVE_PLUS)
    ast_ok = in_window(lambda i: ast_dir[i] == -1 and ast_dir[i - 1] != -1)

    if not (rsi_ok and dmi_ok and ast_ok):
        return None

    # === 7 CONDITIONS OPTIONNELLES ===
    # 1. Green Zone
    green_ok = regime[idx] != -1

    # 2. LazyBar
    lazy_ok = in_window(lambda i: abs(ht[i]) >= 9.6 or abs(ht[i] - ht[i - 1]) >= LB_SPIKE_THRESH)

    # 3. Volume Move
    vol_ok = vol_move[idx] >= AV_MIN_MOVE and vol_change[idx] > 0

    # 4. SuperTrend break bullish
    st_ok = in_window(lambda i: st_dir[i] == -1 and st_dir[i - 1] == 1)

    # 5. PP SuperTrend buy
    pp_ok = in_window(lambda i: pp_trend[i] == 1 and pp_trend[i - 1] == -1)

    # 6. EC — Entry Confirmation
    ec_ok = False
    # Bullish divergence récente
    for i in range(max(0, idx - EC_BULL_DIV_MEMORY), idx + 1):
        if ec_bull_div[i]:
            ec_ok = True
            break
    # Or RSI50 bullish movement
    if not ec_ok:
        ec_ok = in_window(lambda i: (ec_rsi[i] - ec_rsi[i - 1]) > 0 and
                                     abs(ec_rsi[i] - ec_rsi[i - 1]) >= EC_MIN_MOVE_RSI)
    # Or SlowMA bullish
    if not ec_ok:
        def _slow_check(i):
            if np.isnan(ec_slow[i]) or np.isnan(ec_slow[i - 1]):
                return False
            d = ec_slow[i] - ec_slow[i - 1]
            return d > 0 and abs(d) >= EC_MIN_MOVE_SLOW_MA
        ec_ok = in_window(_slow_check)

    # 7. CHoCH — Swing high break
    choch_ok = choch_active[idx]

    # === SCORE /10 ===
    conds = {
        "RSI":   True,       # obligatoire = toujours vrai ici
        "DMI":   True,
        "AST":   True,
        "CHoCH": choch_ok,
        "Zone":  green_ok,
        "Lazy":  lazy_ok,
        "Vol":   vol_ok,
        "ST":    st_ok,
        "PP":    pp_ok,
        "EC":    ec_ok,
    }
    score = sum(1 for v in conds.values() if v)

    if score >= combo_min:
        # LazyBar value and color
        lz_val = ht[idx]
        lz_color = "Red" if lz_val >= 9.6 else "Yellow" if lz_val >= 6 else "Green" if lz_val > 0 else "Navy"

        # EC RSI move (current - previous)
        ec_move = float(ec_rsi[idx] - ec_rsi[idx - 1]) if idx > 0 else 0

        # RSI move
        rsi_move = float(rsi_vals[idx] - rsi_vals[idx - 1]) if idx > 0 else 0

        # DI moves
        di_plus_move = float(plus_di[idx] - plus_di[idx - 1]) if idx > 0 else 0
        di_minus_move = float(minus_di[idx] - minus_di[idx - 1]) if idx > 0 else 0

        # ADX
        adx_val = float(adx[idx])

        return {
            "score": score,
            "price": close[idx],
            "rsi": rsi_vals[idx],
            "di_plus": plus_di[idx],
            "di_minus": minus_di[idx],
            "adx": adx_val,
            "candle_pct": candle_pct,
            "conditions": conds,
            # Per-TF detailed values
            "lazy_value": float(lz_val),
            "lazy_color": lz_color,
            "ec_move": ec_move,
            "rsi_move": rsi_move,
            "di_plus_move": di_plus_move,
            "di_minus_move": di_minus_move,
            # Volume ratio vs 20-bar average (real vol_pct)
            "vol_pct": float(volume[idx] / np.mean(volume[max(0,idx-20):idx]) * 100) if idx > 20 and np.mean(volume[max(0,idx-20):idx]) > 0 else 0,
        }
    return None


# ═══════════════════════════════════════════════════════
# 📤 SUPABASE — Push alerts to database
# ═══════════════════════════════════════════════════════
def push_alerts_to_supabase(sorted_signals, candle_key):
    """Push detected MEGA BUY alerts to Supabase for the dashboard."""
    if not SUPABASE_OK or _supabase is None:
        return

    now_ts = datetime.now(timezone.utc).isoformat()

    filtered_out = 0
    for symbol, tf_results in sorted_signals:
        try:
            # Get best score across all TFs
            best_score = max(r["score"] for r in tf_results.values())
            tfs = list(tf_results.keys())

            # Get detection details from best TF (highest score, prefer longer TF)
            tf_priority = {"4h": 4, "1h": 3, "30m": 2, "15m": 1}
            best_tf_key = max(tf_results.keys(), key=lambda t: (tf_results[t]["score"], tf_priority.get(t, 0)))
            first_tf = tf_results[best_tf_key]
            conditions = first_tf.get("conditions", {})

            # Pre-filter: skip dead candles (no real movement)
            # Fetch current 4H candle body to check if there's actual movement
            try:
                _r4h = requests.get("https://api.binance.com/api/v3/klines",
                    params={"symbol": symbol, "interval": "4h", "limit": 1}, timeout=5)
                _k4h = _r4h.json()
                if _k4h and isinstance(_k4h, list) and len(_k4h) > 0:
                    _o4h, _c4h = float(_k4h[0][1]), float(_k4h[0][4])
                    _body4h = abs(_c4h - _o4h) / _o4h * 100 if _o4h > 0 else 0
                    if _body4h < 1.0:
                        filtered_out += 1
                        continue  # Skip dead candle — body < 1%
            except:
                pass

            # Build alert record matching Supabase schema
            # Convert numpy types to native Python types for JSON
            def _py(v):
                if hasattr(v, 'item'): return v.item()  # numpy scalar
                return v

            alert_data = {
                "pair": symbol,
                "price": float(first_tf.get("price", 0)),
                "alert_timestamp": now_ts,
                "timeframes": tfs,
                "scanner_score": int(best_score),
                "bougie_4h": candle_key.replace("_", " ") + "h",
                # Mandatory conditions (keys match detect_mega_buy output)
                "rsi_check": bool(conditions.get("RSI", False)),
                "dmi_check": bool(conditions.get("DMI", False)),
                "ast_check": bool(conditions.get("AST", False)),
                # Optional conditions
                "choch": bool(conditions.get("CHoCH", False)),
                "zone": bool(conditions.get("Zone", False)),
                "lazy": bool(conditions.get("Lazy", False)),
                "vol": bool(conditions.get("Vol", False)),
                "st": bool(conditions.get("ST", False)),
                "pp": bool(conditions.get("PP", False)),
                "ec": bool(conditions.get("EC", False)),
                # Indicators
                "di_plus_4h": float(first_tf["di_plus"]) if first_tf.get("di_plus") is not None else None,
                "di_minus_4h": float(first_tf["di_minus"]) if first_tf.get("di_minus") is not None else None,
                "adx_4h": float(first_tf["adx"]) if first_tf.get("adx") is not None else None,
                # Volume per TF
                "vol_pct": {tf: float(r.get("vol_pct", 0)) for tf, r in tf_results.items()},
                # LazyBar values per TF
                "lazy_values": {
                    tf: f"{abs(r.get('lazy_value', 0)):.1f} {r.get('lazy_color', '')}"
                    for tf, r in tf_results.items()
                    if r.get("lazy_value") is not None
                } or None,
                # LazyBar moves (color indicator)
                "lazy_moves": {
                    tf: "🔴" if r.get("lazy_color") == "Red" else "🟡" if r.get("lazy_color") == "Yellow" else "🟢" if r.get("lazy_color") == "Green" else "🟣"
                    for tf, r in tf_results.items()
                } or None,
                # EC RSI moves per TF
                "ec_moves": {
                    tf: round(float(r.get("ec_move", 0)), 2)
                    for tf, r in tf_results.items()
                } or None,
                # RSI moves per TF
                "rsi_moves": {
                    tf: round(float(r.get("rsi_move", 0)), 2)
                    for tf, r in tf_results.items()
                } or None,
                # DI moves per TF
                "di_plus_moves": {
                    tf: round(float(r.get("di_plus_move", 0)), 2)
                    for tf, r in tf_results.items()
                } or None,
                "di_minus_moves": {
                    tf: round(float(r.get("di_minus_move", 0)), 2)
                    for tf, r in tf_results.items()
                } or None,
                # RSI — numeric column in Supabase, use best TF value
                "rsi": round(float(first_tf.get("rsi", 0)), 2),
                # ADX moves per TF — JSONB column
                "adx_moves": {
                    tf: round(float(r.get("adx", 0)), 2)
                    for tf, r in tf_results.items()
                } or None,
                # Puissance (best score)
                "puissance": int(best_score),
                # Number of TFs
                "nb_timeframes": len(tfs),
            }

            _supabase.table("alerts").upsert(alert_data, on_conflict="pair,bougie_4h,timeframes").execute()

        except Exception as e:
            print(f"  ⚠️ Supabase push error for {symbol}: {e}")

    if filtered_out > 0:
        print(f"  🚫 Pre-filtered {filtered_out} dead candles (body 4H < 1%)")


# ═══════════════════════════════════════════════════════
# 📱 TELEGRAM
# ═══════════════════════════════════════════════════════
def send_telegram(message):
    if TELEGRAM_TOKEN == "COLLE_TON_TOKEN_ICI":
        print(f"[TELEGRAM DISABLED] {message}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
    except Exception as e:
        print(f"❌ Telegram error: {e}")


# ═══════════════════════════════════════════════════════
# 📊 GOOGLE SHEETS — Logging des alertes
# ═══════════════════════════════════════════════════════
_gs_client = None
_gs_sheet = None


def init_google_sheets():
    """Initialise la connexion Google Sheets + crée/formate le header"""
    global _gs_client, _gs_sheet

    if not GOOGLE_SHEETS_ENABLED or not GSPREAD_OK:
        return False

    if not os.path.exists(GOOGLE_CREDS_FILE):
        print(f"  ⚠️ Google Sheets: {GOOGLE_CREDS_FILE} introuvable")
        return False

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=scopes)
        _gs_client = gspread.authorize(creds)

        # Ouvrir ou créer le sheet
        try:
            spreadsheet = _gs_client.open(GOOGLE_SHEET_NAME)
            _gs_sheet = spreadsheet.get_worksheet(0)  # Premier onglet par index
            print(f"  ✅ Google Sheet ouvert: {GOOGLE_SHEET_NAME}")
        except gspread.SpreadsheetNotFound:
            sh = _gs_client.create(GOOGLE_SHEET_NAME)
            _gs_sheet = sh.get_worksheet(0)
            print(f"  ✅ Google Sheet créé: {GOOGLE_SHEET_NAME}")
            print(f"  📎 Partage avec ton email dans Google Drive !")

        # Vérifier si headers existent
        try:
            first_cell = _gs_sheet.cell(1, 1).value
        except:
            first_cell = None

        if not first_cell:
            _setup_sheet_headers()

        return True

    except Exception as e:
        print(f"  ❌ Google Sheets init error: {e}")
        return False


def _setup_sheet_headers():
    """Crée les headers avec style"""
    headers = [
        "Date/Heure", "Paire", "Score", "TFs", "Nb TF", "Émotion",
        "Prix", "RSI", "DI+",
        "RSI✓", "DMI✓", "AST✓",
        "CHoCH", "Zone", "Lazy", "Vol", "ST", "PP", "EC",
        "Bougie 4H"
    ]

    _gs_sheet.update(values=[headers], range_name='A1:T1')

    # Largeurs de colonnes
    body = {"requests": [
        # Header: fond noir, texte blanc, bold
        {"repeatCell": {
            "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1,
                       "startColumnIndex": 0, "endColumnIndex": 20},
            "cell": {"userEnteredFormat": {
                "backgroundColor": {"red": 0.1, "green": 0.1, "blue": 0.15},
                "textFormat": {"bold": True, "fontSize": 10,
                               "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER",
                "borders": {
                    "bottom": {"style": "SOLID_THICK",
                               "color": {"red": 0.2, "green": 0.8, "blue": 0.2}}
                }
            }},
            "fields": "userEnteredFormat"
        }},
        # Figer la 1ère ligne
        {"updateSheetProperties": {
            "properties": {"sheetId": 0,
                           "gridProperties": {"frozenRowCount": 1}},
            "fields": "gridProperties.frozenRowCount"
        }},
        # Largeurs colonnes
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS",
                       "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 160}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS",
                       "startIndex": 1, "endIndex": 2},
            "properties": {"pixelSize": 130}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS",
                       "startIndex": 2, "endIndex": 3},
            "properties": {"pixelSize": 60}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS",
                       "startIndex": 3, "endIndex": 4},
            "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
        {"updateDimensionProperties": {
            "range": {"sheetId": 0, "dimension": "COLUMNS",
                       "startIndex": 5, "endIndex": 6},
            "properties": {"pixelSize": 140}, "fields": "pixelSize"}},
        # Onglet style
    ]}

    _gs_sheet.spreadsheet.batch_update(body)
    print("  ✅ Headers Google Sheet créés avec style")


def log_signals_to_sheets(sorted_signals, candle_key):
    """Enregistre les signaux dans Google Sheet avec couleurs"""
    global _gs_sheet

    if not GOOGLE_SHEETS_ENABLED or not GSPREAD_OK or _gs_sheet is None:
        return

    try:
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        rows = []

        for symbol, tf_results in sorted_signals:
            best = max(tf_results.values(), key=lambda r: r["score"])
            s = best["score"]
            tf_list = sorted(tf_results.keys(),
                             key=lambda t: ["15m","30m","1h","4h"].index(t))
            ntf = len(tf_results)

            if ntf >= 4: emotion = "🔥🔥🔥 LEGENDARY"
            elif ntf >= 3: emotion = "🔥🔥 ULTRA"
            elif ntf >= 2: emotion = "🔥 STRONG"
            else: emotion = ""

            conds = best["conditions"]

            row = [
                now_str,
                symbol.replace("USDT", ""),
                s,
                ", ".join(tf_list),
                ntf,
                emotion,
                best["price"],
                round(best["rsi"], 1),
                round(best["di_plus"], 1),
                "✓" if conds.get("RSI") else "✗",
                "✓" if conds.get("DMI") else "✗",
                "✓" if conds.get("AST") else "✗",
                "✓" if conds.get("CHoCH") else "✗",
                "✓" if conds.get("Zone") else "✗",
                "✓" if conds.get("Lazy") else "✗",
                "✓" if conds.get("Vol") else "✗",
                "✓" if conds.get("ST") else "✗",
                "✓" if conds.get("PP") else "✗",
                "✓" if conds.get("EC") else "✗",
                candle_key.replace("_", " ") + "h"
            ]
            rows.append(row)

        if not rows:
            return

        # Insérer après le header (row 2+)
        next_row = len(_gs_sheet.get_all_values()) + 1
        end_col = chr(ord('A') + len(rows[0]) - 1)
        cell_range = f"A{next_row}:{end_col}{next_row + len(rows) - 1}"
        _gs_sheet.update(values=rows, range_name=cell_range)

        # Appliquer les couleurs par ligne
        format_requests = []
        for i, (symbol, tf_results) in enumerate(sorted_signals):
            best = max(tf_results.values(), key=lambda r: r["score"])
            s = best["score"]
            ntf = len(tf_results)
            row_idx = next_row - 1 + i  # 0-indexed

            # Couleur de fond selon score
            if s >= 9:
                bg = {"red": 0.1, "green": 0.35, "blue": 0.1}   # Vert foncé
                fg = {"red": 0.6, "green": 1, "blue": 0.6}       # Texte vert clair
            elif s >= 7:
                bg = {"red": 0.35, "green": 0.35, "blue": 0.05}  # Jaune foncé
                fg = {"red": 1, "green": 1, "blue": 0.6}         # Texte jaune
            else:
                bg = {"red": 0.3, "green": 0.2, "blue": 0.05}    # Orange foncé
                fg = {"red": 1, "green": 0.8, "blue": 0.4}       # Texte orange

            # Fond de la ligne
            format_requests.append({
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": row_idx,
                              "endRowIndex": row_idx + 1,
                              "startColumnIndex": 0, "endColumnIndex": 20},
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": bg,
                        "textFormat": {"foregroundColor": fg, "fontSize": 10},
                        "horizontalAlignment": "CENTER"
                    }},
                    "fields": "userEnteredFormat"
                }
            })

            # Score cell: bold + taille plus grande
            format_requests.append({
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": row_idx,
                              "endRowIndex": row_idx + 1,
                              "startColumnIndex": 2, "endColumnIndex": 3},
                    "cell": {"userEnteredFormat": {
                        "textFormat": {"bold": True, "fontSize": 13,
                                       "foregroundColor": fg}
                    }},
                    "fields": "userEnteredFormat.textFormat"
                }
            })

            # Paire cell: bold
            format_requests.append({
                "repeatCell": {
                    "range": {"sheetId": 0, "startRowIndex": row_idx,
                              "endRowIndex": row_idx + 1,
                              "startColumnIndex": 1, "endColumnIndex": 2},
                    "cell": {"userEnteredFormat": {
                        "textFormat": {"bold": True, "fontSize": 11,
                                       "foregroundColor": fg}
                    }},
                    "fields": "userEnteredFormat.textFormat"
                }
            })

            # Conditions: vert pour ✓, rouge pour ✗
            for col_idx in range(9, 19):  # Colonnes J à S (conditions)
                val = rows[i][col_idx]
                c_fg = ({"red": 0.2, "green": 0.9, "blue": 0.2} if val == "✓"
                        else {"red": 0.7, "green": 0.3, "blue": 0.3})
                format_requests.append({
                    "repeatCell": {
                        "range": {"sheetId": 0, "startRowIndex": row_idx,
                                  "endRowIndex": row_idx + 1,
                                  "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1},
                        "cell": {"userEnteredFormat": {
                            "textFormat": {"bold": True, "foregroundColor": c_fg}
                        }},
                        "fields": "userEnteredFormat.textFormat"
                    }
                })

            # Multi-TF highlight (Nb TF >= 2: bordure spéciale)
            if ntf >= 2:
                border_color = ({"red": 1, "green": 0.2, "blue": 0.2} if ntf >= 4
                                else {"red": 1, "green": 0.6, "blue": 0.1} if ntf >= 3
                                else {"red": 1, "green": 0.8, "blue": 0.2})
                format_requests.append({
                    "updateBorders": {
                        "range": {"sheetId": 0, "startRowIndex": row_idx,
                                  "endRowIndex": row_idx + 1,
                                  "startColumnIndex": 0, "endColumnIndex": 20},
                        "left": {"style": "SOLID_THICK", "color": border_color},
                        "right": {"style": "SOLID_THICK", "color": border_color},
                    }
                })

        if format_requests:
            _gs_sheet.spreadsheet.batch_update({"requests": format_requests})

        print(f"  📊 {len(rows)} signaux logués dans Google Sheet")

    except Exception as e:
        print(f"  ⚠️ Google Sheets log error: {e}")


def get_4h_candle_key():
    """Retourne la clé de la bougie 4H en cours (ex: '2026-02-15_12')"""
    now = datetime.now(timezone.utc)
    h4 = (now.hour // 4) * 4
    return f"{now.strftime('%Y-%m-%d')}_{h4:02d}"


def format_signal_multi(symbol, tf_results):
    """Formate un signal multi-TF pour Telegram"""
    # Meilleur score parmi les TF
    best = max(tf_results.values(), key=lambda r: r["score"])
    s = best["score"]
    emoji = "🟢" if s >= 9 else ("🟡" if s >= 7 else "🟠")

    # TF badges
    tf_list = sorted(tf_results.keys(), key=lambda t: ["15m","30m","1h","4h"].index(t))
    tf_badges = " ".join(f"[{tf}]" for tf in tf_list)

    # Emotion badge par nombre de TF
    ntf = len(tf_results)
    if ntf >= 4:
        emotion = "🔥🔥🔥 LEGENDARY"
    elif ntf >= 3:
        emotion = "🔥🔥 ULTRA STRONG"
    elif ntf >= 2:
        emotion = "🔥 STRONG"
    else:
        emotion = ""

    # Conditions du meilleur score
    conds = best["conditions"]
    req = "RSI✓ DMI✓ AST✓"
    opt_names = ["CHoCH", "Zone", "Lazy", "Vol", "ST", "PP", "EC"]
    opt = " ".join(f"{'✅' if conds.get(k) else '❌'}{k}" for k in opt_names)

    msg = f"{emoji} <b>{symbol}</b> → <b>{s}/10</b> {tf_badges}\n"
    if emotion:
        msg += f"    {emotion}\n"
    msg += (
        f"💰 {best['price']:.6f}  📊 RSI {best['rsi']:.1f} | DI+ {best['di_plus']:.1f}\n"
        f"<b>{req}</b>\n"
        f"{opt}"
    )

    # Détail par TF si multi
    if ntf > 1:
        msg += "\n    📊 "
        msg += " | ".join(f"{tf}:{tf_results[tf]['score']}/10" for tf in tf_list)

    return msg


# ═══════════════════════════════════════════════════════
# 🔄 SCANNER PRINCIPAL — Multi-TF + 4H Dedup
# ═══════════════════════════════════════════════════════
# notified_pairs = { "2026-02-15_12": {"BTCUSDT": {"30m": result, "1h": result}, ...} }
notified_pairs = {}
last_signals = {}


def run_scan():
    global notified_pairs, last_signals
    now_dt = datetime.now(timezone.utc)
    now = now_dt.strftime("%Y-%m-%d %H:%M UTC")
    candle_key = get_4h_candle_key()

    # Nettoyer les anciennes bougies 4H (garder seulement la courante)
    old_keys = [k for k in notified_pairs if k != candle_key]
    for k in old_keys:
        del notified_pairs[k]

    if candle_key not in notified_pairs:
        notified_pairs[candle_key] = {}

    print(f"\n{'='*60}")
    print(f"🔍 Scan Multi-TF démarré — {now}")
    print(f"📦 Bougie 4H: {candle_key} | Déjà notifié: {len(notified_pairs[candle_key])} paires")
    print(f"{'='*60}")

    try:
        print("📋 Récupération des paires USDT...")
        volumes = get_24h_volumes()

        # Exclude stablecoins, pegged assets, forex, wrapped tokens
        STABLECOIN_BLACKLIST = {
            "USDCUSDT", "FDUSDUSDT", "TUSDUSDT", "BUSDUSDT", "DAIUSDT",
            "USDPUSDT", "USTCUSDT", "LUSDUSDT", "FRAXUSDT", "USDDUSDT",
            "USDTUSDT", "USD1USDT", "USDEUSDT", "PYUSDUSDT", "GUSDUSDT",
            "USDYUSDT", "CEURUSDT", "EURCUSDT",
            "PAXGUSDT", "XAUTUSDT",
            "EURUSDT", "GBPUSDT", "JPYUSDT", "AUDUSDT", "TRYUSDT",
            "WBTCUSDT", "WBETHUSDT", "BETHUSDT", "STETHUSDT", "CBETHUSDT",
        }

        pairs = [p for p, v in volumes.items()
                 if v >= MIN_VOLUME_USDT and p not in STABLECOIN_BLACKLIST]
        pairs.sort(key=lambda p: volumes.get(p, 0), reverse=True)
        print(f"✅ {len(pairs)} paires avec volume > ${MIN_VOLUME_USDT:,.0f} (excl. {len(STABLECOIN_BLACKLIST)} stablecoins)")

        # Collecter les nouveaux signaux par paire (multi-TF)
        new_signals = {}  # { "BTCUSDT": {"30m": result, "1h": result} }
        errors = 0
        MAX_WORKERS = 12  # Threads parallèles (Binance limite: 1200 req/min)

        def scan_pair(symbol, tf):
            """Scanne une paire sur un TF — thread-safe"""
            try:
                df = get_klines(symbol, tf, 200)
                if df is None:
                    return None
                result = detect_mega_buy(df)
                return (symbol, tf, result)
            except Exception as e:
                return (symbol, tf, "ERROR", str(e))

        for tf in TIMEFRAMES:
            print(f"\n  ⏱️ Scan {tf}...")
            tf_count = 0

            # Filtrer les paires déjà notifiées pour ce TF
            pairs_to_scan = []
            for symbol in pairs:
                already = notified_pairs[candle_key].get(symbol, {})
                if tf not in already:
                    pairs_to_scan.append(symbol)

            # Scan parallèle
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {executor.submit(scan_pair, sym, tf): sym
                           for sym in pairs_to_scan}

                done_count = 0
                for future in as_completed(futures):
                    done_count += 1
                    if done_count % 100 == 0:
                        print(f"    📊 {tf} — {done_count}/{len(pairs_to_scan)}...")

                    result = future.result()
                    if result is None:
                        continue
                    if len(result) == 4 and result[2] == "ERROR":
                        errors += 1
                        if errors <= 5:
                            print(f"    ⚠️ {result[0]}/{tf}: {result[3]}")
                        continue

                    symbol, _, detection = result
                    if detection:
                        if symbol not in new_signals:
                            new_signals[symbol] = {}
                        new_signals[symbol][tf] = detection
                        tf_count += 1

            print(f"  ✅ {tf}: {tf_count} nouveaux signaux")

        # Fusionner avec les signaux déjà notifiés dans cette 4H
        # pour grouper les TF ensemble
        to_notify = {}  # paires avec AU MOINS 1 nouveau TF

        for symbol, tf_results in new_signals.items():
            # Merge avec les anciens TF déjà notifiés
            existing = notified_pairs[candle_key].get(symbol, {})
            merged = {**existing, **tf_results}

            # Si c'est une paire déjà notifiée mais avec un NOUVEAU TF → re-notifier
            new_tfs = set(tf_results.keys()) - set(existing.keys())
            if new_tfs:
                to_notify[symbol] = merged
                # Enregistrer tous les TF comme notifiés
                notified_pairs[candle_key][symbol] = merged

        print(f"\n📊 Résultat: {len(to_notify)} paires à notifier "
              f"({sum(len(v) for v in to_notify.values())} signaux TF)")

        if to_notify:
            # Trier par meilleur score, puis par nombre de TF
            sorted_signals = sorted(
                to_notify.items(),
                key=lambda x: (len(x[1]), max(r["score"] for r in x[1].values())),
                reverse=True
            )

            header = (
                f"🚨 <b>MEGA BUY SCAN — {now}</b>\n"
                f"📊 {len(sorted_signals)} paire(s) | "
                f"Bougie 4H: {candle_key.replace('_', ' ')}h\n"
                f"{'─' * 30}\n\n"
            )

            msg = header
            for symbol, tf_results in sorted_signals[:15]:
                sig_msg = format_signal_multi(symbol, tf_results)
                if len(msg) + len(sig_msg) > 3800:
                    msg += f"\n... et {len(sorted_signals) - 15} autres"
                    break
                msg += sig_msg + "\n\n"

            send_telegram(msg)
            log_signals_to_sheets(sorted_signals, candle_key)
            push_alerts_to_supabase(sorted_signals, candle_key)
            last_signals = dict(sorted_signals)
        else:
            print("  ℹ️ Aucun nouveau signal à notifier")

        if errors > 5:
            print(f"  ⚠️ {errors} erreurs au total")

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"❌ Erreur critique: {e}")
        send_telegram(f"❌ Erreur scanner: {e}")


# ═══════════════════════════════════════════════════════
# 📱 COMMANDES TELEGRAM
# ═══════════════════════════════════════════════════════
def check_telegram_commands():
    if TELEGRAM_TOKEN == "COLLE_TON_TOKEN_ICI":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        resp = requests.get(url, params={"timeout": 1, "offset": -1}, timeout=5)
        data = resp.json()
        if not data.get("result"):
            return
        update = data["result"][-1]
        text = update.get("message", {}).get("text", "")

        if text == "/scan":
            send_telegram("🔄 Scan manuel lancé...")
            run_scan()
        elif text == "/status":
            candle_key = get_4h_candle_key()
            n_notified = len(notified_pairs.get(candle_key, {}))
            send_telegram(
                f"🤖 <b>Bot v3 — Multi-TF</b>\n"
                f"✅ En ligne\n"
                f"📊 TF: {', '.join(TIMEFRAMES)}\n"
                f"📦 Bougie 4H: {candle_key}\n"
                f"🔕 Déjà notifié: {n_notified} paires\n"
                f"⏰ Scan toutes les {SCAN_INTERVAL_MIN} min\n"
                f"🎯 Score /10 — Seuil {COMBO_THRESHOLD_PCT}%\n"
                f"🚫 Max candle: {MAX_CANDLE_MOVE_PCT}%"
            )
        elif text == "/top":
            if last_signals:
                msg = "📊 <b>Derniers signaux :</b>\n\n"
                for sym, tf_res in sorted(last_signals.items(),
                                          key=lambda x: max(r["score"] for r in x[1].values()),
                                          reverse=True)[:10]:
                    msg += format_signal_multi(sym, tf_res) + "\n\n"
                send_telegram(msg)
            else:
                send_telegram("ℹ️ Aucun signal récent")
        elif text == "/reset":
            notified_pairs.clear()
            send_telegram("🗑️ Cooldown reset — toutes les paires seront re-notifiées")
        elif text == "/help":
            send_telegram(
                "🤖 <b>Commandes :</b>\n\n"
                "/scan — Scan immédiat\n"
                "/status — État du bot\n"
                "/top — Derniers signaux\n"
                "/reset — Reset cooldown 4H\n"
                "/help — Aide"
            )
    except:
        pass


# ═══════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════
def main():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║     🟢 MEGA BUY Scanner Bot v3               ║
    ║     Multi-TF + 4H Dedup + Pump Filter        ║
    ║     Binance USDT — Telegram Alerts           ║
    ║     ASSYIN-2026                              ║
    ╚═══════════════════════════════════════════════╝
    """)
    print(f"⚙️  Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"⚙️  Score /10 — Seuil: {COMBO_THRESHOLD_PCT}% ({int(np.ceil(10 * COMBO_THRESHOLD_PCT / 100))}/10)")
    print(f"⚙️  Max candle move: {MAX_CANDLE_MOVE_PCT}%")
    print(f"⚙️  Scan toutes les {SCAN_INTERVAL_MIN} min")
    print(f"⚙️  Volume min: ${MIN_VOLUME_USDT:,.0f}")
    print(f"⚙️  Cooldown: 1 notif par paire par bougie 4H")

    if TELEGRAM_TOKEN == "COLLE_TON_TOKEN_ICI":
        print("\n⚠️  TELEGRAM NON CONFIGURÉ — signaux en console uniquement")
        print("    Modifie TELEGRAM_TOKEN et TELEGRAM_CHAT_ID\n")
    else:
        send_telegram(
            "🟢 <b>MEGA BUY Scanner v3 démarré !</b>\n"
            f"📊 Multi-TF: {', '.join(TIMEFRAMES)}\n"
            "🔕 Cooldown: 1x par paire / bougie 4H\n"
            f"🚫 Pump filter: {MAX_CANDLE_MOVE_PCT}%"
        )
        print("✅ Telegram connecté\n")

    # Google Sheets
    if GOOGLE_SHEETS_ENABLED:
        if not GSPREAD_OK:
            print("⚠️  Google Sheets: installe gspread → pip install gspread google-auth")
        elif init_google_sheets():
            print("✅ Google Sheets connecté\n")
        else:
            print("⚠️  Google Sheets non connecté\n")

    run_scan()

    while True:
        try:
            now = datetime.now(timezone.utc)
            minutes = now.minute
            seconds = now.second

            # Aligner sur les intervalles de 15 min (0, 15, 30, 45)
            next_slot = ((minutes // SCAN_INTERVAL_MIN) + 1) * SCAN_INTERVAL_MIN
            if next_slot >= 60:
                wait_min = 60 - minutes
            else:
                wait_min = next_slot - minutes
            wait_sec = wait_min * 60 - seconds + 15  # +15 sec marge

            print(f"\n⏰ Prochain scan dans {wait_sec // 60} min {wait_sec % 60} sec")

            elapsed = 0
            while elapsed < wait_sec:
                time.sleep(10)
                elapsed += 10
                check_telegram_commands()

            run_scan()

        except KeyboardInterrupt:
            print("\n\n🛑 Bot arrêté")
            send_telegram("🔴 <b>MEGA BUY Scanner arrêté</b>")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")
            time.sleep(60)


if __name__ == "__main__":
    main()
