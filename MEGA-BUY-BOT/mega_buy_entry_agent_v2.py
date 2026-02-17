"""
🎯 MEGA BUY Entry Agent v2 — Golden Box Monitor
Surveille les alertes MEGA BUY et détecte les entrées optimales

Conditions d'entrée validées (PineScript ✅) :
  OBLIGATOIRE :
    1. DMI+ > DMI- en 4H
    2. Bougie 4H CLÔTURE > Box High
    3. RSI 4H > RSI référence (Higher High)
    4. Prix > Cloud Top Assyin# en 1H
    5. Prix > Cloud Top Assyin# en 30M
  BONUS :
    B1. Volume > 1.5× avg20
    B2. Retest Box High comme support

Fonctionnement :
  1. Importe les signaux MEGA BUY depuis Google Sheets
  2. Crée automatiquement la Golden Box (High/Low/RSI de la bougie 4H)
  3. Vérifie les 5+2 conditions toutes les 15 minutes
  4. Notifie via Telegram quand ENTRY READY

Auteur: ASSYIN-2026
"""

import requests
import numpy as np
import pandas as pd
import time
import os
import json
from datetime import datetime, timezone, timedelta

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except ImportError:
    GSPREAD_OK = False
    print("⚠️  pip install gspread google-auth")

# ═══════════════════════════════════════════════════════
# ⚙️ CONFIGURATION
# ═══════════════════════════════════════════════════════
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "YOUR_TELEGRAM_TOKEN_HERE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")

GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEET_NAME = "MEGA BUY Alerts"
GOOGLE_CREDS_FILE = "google_creds.json"

CHECK_INTERVAL_MIN = 15
GOLDEN_BOX_EXPIRY_4H = 15       # Max 15 bougies 4H (~60h)

# ── Indicateurs ──
RSI_LENGTH = 14
DMI_LENGTH = 14
ATR_LENGTH = 14

# ── Entry ──
TP_MULTIPLIER = 1.5              # TP = Box High + height × 1.5
SL_ATR_BUFFER = 0.5              # SL = Box Low - ATR × 0.5
VOLUME_BREAK_MULT = 1.5          # Volume > 1.5× avg20
RETEST_TOLERANCE_PCT = 0.5       # ±0.5% du Box High

# ── Assyin# Ichimoku Cloud ──
ICH_TK_MIN = 9;   ICH_TK_MAX = 30
ICH_KJ_MIN = 20;  ICH_KJ_MAX = 60
ICH_SK_MIN = 50;  ICH_SK_MAX = 120
ICH_DYN_PCT = 0.9685             # Taux d'adaptation par bar
ICH_OFFSET = 26                  # Displacement
ICH_CH_FILT = 25                 # Chikou filter period
ICH_VOL_PEAK = 50                # OBV threshold
ICH_ATR_FAST = 14;  ICH_ATR_SLOW = 46


# ═══════════════════════════════════════════════════════
# 📡 BINANCE API
# ═══════════════════════════════════════════════════════
BINANCE_BASE = "https://api.binance.com"

def get_klines(symbol, interval, limit=200):
    """Récupère les bougies Binance"""
    try:
        url = f"{BINANCE_BASE}/api/v3/klines"
        r = requests.get(url, params={
            "symbol": symbol, "interval": interval, "limit": limit
        }, timeout=15)
        data = r.json()
        if not isinstance(data, list):
            return None
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        return df
    except Exception as e:
        print(f"  ⚠️ Klines {symbol} {interval}: {e}")
        return None


# ═══════════════════════════════════════════════════════
# 📊 FONCTIONS UTILITAIRES
# ═══════════════════════════════════════════════════════
def rma(s, length):
    alpha = 1.0 / length
    r = np.zeros(len(s)); r[0] = s[0]
    for i in range(1, len(s)):
        r[i] = alpha * s[i] + (1 - alpha) * r[i - 1]
    return r

def true_range(h, l, c):
    tr = np.zeros(len(h)); tr[0] = h[0] - l[0]
    for i in range(1, len(h)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i-1]), abs(l[i] - c[i-1]))
    return tr

def calc_atr(h, l, c, length=14):
    return rma(true_range(h, l, c), length)

def calc_rsi(close, length=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.maximum(delta, 0)
    loss = -np.minimum(delta, 0)
    ag = rma(gain, length)
    al = rma(loss, length)
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(al == 0, 100, ag / al)
        return np.where(al == 0, 100, 100 - (100 / (1 + rs)))

def calc_dmi(high, low, close, length=14):
    n = len(high)
    pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i-1]; dn = low[i-1] - low[i]
        pdm[i] = up if (up > dn and up > 0) else 0
        mdm[i] = dn if (dn > up and dn > 0) else 0
    tr = true_range(high, low, close)
    atr_v = rma(tr, length)
    safe = np.where(atr_v == 0, 1, atr_v)
    pdi = 100 * rma(pdm, length) / safe
    mdi = 100 * rma(mdm, length) / safe
    return pdi, mdi

def calc_volume_ratio(volume, length=20):
    n = len(volume); ratio = np.zeros(n)
    for i in range(length - 1, n):
        avg = np.mean(volume[i - length + 1:i + 1])
        if avg > 0: ratio[i] = volume[i] / avg
    return ratio


# ═══════════════════════════════════════════════════════
# 🔶 ASSYIN# ICHIMOKU CLOUD — Full Dynamic Engine
# ═══════════════════════════════════════════════════════
def calc_swma(src):
    """SWMA [1,2,2,1] / 6"""
    n = len(src); out = np.full(n, np.nan)
    for i in range(3, n):
        out[i] = (src[i-3] + 2*src[i-2] + 2*src[i-1] + src[i]) / 6
    return out

def calc_heikin_ashi_close(o, h, l, c):
    return (o + h + l + c) / 4

def calc_alt_source(o, h, l, c):
    raw = np.where(c > o, h, l)
    return calc_swma(raw)

def calc_obv_custom(ha_close, volume):
    n = len(ha_close); obv = np.zeros(n)
    for i in range(1, n):
        chg = ha_close[i] - ha_close[i-1]
        sign = 1.0 if chg > 0 else (-1.0 if chg < 0 else 0.0)
        obv[i] = obv[i-1] + sign * volume[i]
    # Normalize to 0-100 range
    _min = np.min(obv); _max = np.max(obv)
    if _max - _min > 0:
        obv = (obv - _min) / (_max - _min) * 100
    return obv

def calc_chikou_filter(alt_src, high, low, period=25):
    n = len(alt_src); sig = np.zeros(n)
    for i in range(period * 2, n):
        h_past = np.max(high[i - period * 2:i - period + 1])
        l_past = np.min(low[i - period * 2:i - period + 1])
        if alt_src[i] > h_past:
            sig[i] = 1.0
        elif alt_src[i] < l_past:
            sig[i] = -1.0
    return sig

def calc_dynamic_length(bull, pct, min_len, max_len, n):
    lengths = np.zeros(n, dtype=int)
    dyn = (min_len + max_len) / 2.0
    for i in range(n):
        if bull[i]:
            dyn = max(min_len, dyn * pct)
        else:
            dyn = min(max_len, dyn * (2.0 - pct))
        lengths[i] = max(int(dyn), 2)
    return lengths

def calc_assyin_cloud(df):
    """
    Cloud Top = max(Span A displaced, Span B displaced)
    - Span A = avg(Tenkan dyn 9-30, Kijun dyn 20-60)
    - Span B = donchian(dyn 50-120)
    - Displacement = 26 bars backward (looking at displaced value)
    """
    o = df["open"].values; h = df["high"].values
    l = df["low"].values; c = df["close"].values
    v = df["volume"].values; n = len(c)

    ha_close = calc_heikin_ashi_close(o, h, l, c)
    alt_src = calc_alt_source(o, h, l, c)
    obv = calc_obv_custom(ha_close, v)
    atr_f = calc_atr(h, l, c, ICH_ATR_FAST)
    atr_s = calc_atr(h, l, c, ICH_ATR_SLOW)
    chi_sig = calc_chikou_filter(alt_src, h, l, ICH_CH_FILT)

    bull = np.array([obv[i] > ICH_VOL_PEAK and atr_f[i] > atr_s[i]
                     and chi_sig[i] == 1.0 for i in range(n)])

    dyn_tk = calc_dynamic_length(bull, ICH_DYN_PCT, ICH_TK_MIN, ICH_TK_MAX, n)
    dyn_kj = calc_dynamic_length(bull, ICH_DYN_PCT, ICH_KJ_MIN, ICH_KJ_MAX, n)
    dyn_sk = calc_dynamic_length(bull, ICH_DYN_PCT, ICH_SK_MIN, ICH_SK_MAX, n)

    # Tenkan-Sen
    tenkan = np.full(n, np.nan)
    for i in range(ICH_TK_MAX, n):
        dl = dyn_tk[i]; s = max(0, i - dl + 1)
        tenkan[i] = (np.max(h[s:i+1]) + np.min(l[s:i+1])) / 2

    # Kijun-Sen
    kijun = np.full(n, np.nan)
    for i in range(ICH_KJ_MAX, n):
        dl = dyn_kj[i]; s = max(0, i - dl + 1)
        kijun[i] = (np.max(h[s:i+1]) + np.min(l[s:i+1])) / 2

    # Span A raw = avg(tenkan, kijun)
    span_a_raw = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(tenkan[i]) and not np.isnan(kijun[i]):
            span_a_raw[i] = (tenkan[i] + kijun[i]) / 2

    # Span B raw = donchian(dyn_sk)
    span_b_raw = np.full(n, np.nan)
    for i in range(ICH_SK_MAX, n):
        dl = dyn_sk[i]; s = max(0, i - dl + 1)
        span_b_raw[i] = (np.max(h[s:i+1]) + np.min(l[s:i+1])) / 2

    # Displacement
    off = ICH_OFFSET
    span_a = np.full(n, np.nan)
    span_b = np.full(n, np.nan)
    for i in range(off, n):
        if not np.isnan(span_a_raw[i - off]):
            span_a[i] = span_a_raw[i - off]
        if not np.isnan(span_b_raw[i - off]):
            span_b[i] = span_b_raw[i - off]

    # Cloud Top = max(Span A, Span B)
    cloud_top = np.full(n, np.nan)
    for i in range(n):
        a = span_a[i]; b = span_b[i]
        if not np.isnan(a) and not np.isnan(b):
            cloud_top[i] = max(a, b)
        elif not np.isnan(a):
            cloud_top[i] = a
        elif not np.isnan(b):
            cloud_top[i] = b

    return cloud_top


# ═══════════════════════════════════════════════════════
# 📦 GOLDEN BOX MANAGER
# ═══════════════════════════════════════════════════════
GOLDEN_BOXES_FILE = "golden_boxes.json"

def load_golden_boxes():
    if os.path.exists(GOLDEN_BOXES_FILE):
        try:
            with open(GOLDEN_BOXES_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {}

def save_golden_boxes(boxes):
    with open(GOLDEN_BOXES_FILE, 'w') as f:
        json.dump(boxes, f, indent=2, default=str)

def create_golden_box(symbol, signal_time_str, score=0):
    """
    Crée une Golden Box en trouvant la bougie 4H exacte par timestamp.
    Identique au PineScript : auto-détection High/Low/RSI.
    
    signal_time_str: "YYYY-MM-DD HH:MM" ou "DD/MM/YYYY HH:MM"
    """
    # Parse time
    signal_dt = None
    for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:
        try:
            signal_dt = datetime.strptime(signal_time_str, fmt)
            break
        except ValueError:
            continue
    
    if signal_dt is None:
        print(f"  ❌ Cannot parse date: {signal_time_str}")
        return None

    # Add UTC if naive
    if signal_dt.tzinfo is None:
        signal_dt = signal_dt.replace(tzinfo=timezone.utc)
    
    # Match EXACTLY like PineScript:
    # gb_match = gb_h4_time >= gb_startDate and gb_h4_time < gb_startDate + 4h
    # This finds the FIRST 4H bar that opens AFTER the signal time
    # Example: signal=10:00 → finds 12:00 bar (not 08:00 which is still forming)
    search_start = signal_dt
    search_end = signal_dt + timedelta(hours=4)

    # Get 4H klines
    df = get_klines(symbol, "4h", 500)
    if df is None:
        print(f"  ❌ No data for {symbol} 4H")
        return None

    # Find first 4H bar where open_time >= signal_time and < signal_time + 4h
    found_idx = None
    candle_start = None
    for i in range(len(df)):
        ct = df.iloc[i]["open_time"]
        if isinstance(ct, pd.Timestamp):
            ct = ct.to_pydatetime()
        if ct.tzinfo is None:
            ct = ct.replace(tzinfo=timezone.utc)
        
        if ct >= search_start and ct < search_end:
            found_idx = i
            candle_start = ct
            break
    
    if found_idx is None:
        # Fallback: try aligning to nearest 4H boundary
        h4 = (signal_dt.hour // 4) * 4
        candle_start = signal_dt.replace(hour=h4, minute=0, second=0, microsecond=0)
        print(f"  ⚠️ No 4H bar in [{search_start} - {search_end}), trying {candle_start}")
        for i in range(len(df)):
            ct = df.iloc[i]["open_time"]
            if isinstance(ct, pd.Timestamp):
                ct = ct.to_pydatetime()
            if ct.tzinfo is None:
                ct = ct.replace(tzinfo=timezone.utc)
            if abs((ct - candle_start).total_seconds()) < 7200:
                found_idx = i
                candle_start = ct
                break
    
    if found_idx is None:
        print(f"  ❌ 4H candle not found for signal {signal_dt}")
        return None
    
    h = df["high"].values; l = df["low"].values; c = df["close"].values
    rsi = calc_rsi(c, RSI_LENGTH)
    pdi, mdi = calc_dmi(h, l, c, DMI_LENGTH)
    atr = calc_atr(h, l, c, ATR_LENGTH)

    hi = float(h[found_idx])
    lo = float(l[found_idx])
    bh = hi - lo

    # TP / SL
    tp = hi + bh * TP_MULTIPLIER
    sl = lo - float(atr[found_idx]) * SL_ATR_BUFFER

    box = {
        "symbol": symbol,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signal_time": signal_time_str,
        "candle_4h": candle_start.strftime("%Y-%m-%d %H:%M"),
        "high_4h": hi,
        "low_4h": lo,
        "close_4h": float(c[found_idx]),
        "rsi_signal": float(rsi[found_idx]),
        "dmi_plus_signal": float(pdi[found_idx]),
        "dmi_minus_signal": float(mdi[found_idx]),
        "atr_signal": float(atr[found_idx]),
        "box_height": bh,
        "score": score,
        "tp_target": tp,
        "sl_target": sl,
        "checks_count": 0,
        "max_checks": GOLDEN_BOX_EXPIRY_4H * 4,  # 15 × 4H × 4 checks/4H = 60 checks
        "status": "WATCHING",
        "conditions_history": [],
        "entry_price": None,
        "entry_time": None,
        # MEGA BUY alert details (filled by import, defaults for manual)
        "alert_time": signal_time_str,
        "alert_tfs": "",
        "alert_nb_tf": "",
        "alert_emotion": "",
        "alert_prix": "",
        "alert_rsi": "",
        "alert_dip": "",
    }

    print(f"  ✅ Golden Box: {symbol}")
    print(f"     📅 4H: {candle_start.strftime('%d/%m %H:%M')} | ★{score}/10")
    print(f"     📦 H: {hi:.8g} | L: {lo:.8g}")
    print(f"     📊 RSI: {rsi[found_idx]:.1f} | DI+: {pdi[found_idx]:.1f}")
    print(f"     🎯 TP: {tp:.8g} | 🛑 SL: {sl:.8g}")

    return box


def cleanup_expired_boxes(boxes):
    """Expire les boxes qui ont dépassé leur nombre max de checks"""
    expired = []
    for key, box in boxes.items():
        if box["status"] == "WATCHING" and box["checks_count"] >= box["max_checks"]:
            box["status"] = "EXPIRED"
            expired.append(box["symbol"])
            print(f"  ⏰ {box['symbol']} Golden Box expirée")

    # Remove old expired/entered boxes (>96h)
    to_del = []
    for key, box in boxes.items():
        if box["status"] in ["EXPIRED", "ENTERED"]:
            try:
                created = datetime.fromisoformat(box["created_at"])
                if datetime.now(timezone.utc) - created > timedelta(hours=96):
                    to_del.append(key)
            except:
                to_del.append(key)
    for k in to_del:
        del boxes[k]
    
    return boxes


# ═══════════════════════════════════════════════════════
# 🎯 ENTRY CONDITIONS CHECKER
# ═══════════════════════════════════════════════════════
def check_entry_conditions(box):
    """
    Vérifie les 5 conditions obligatoires + 2 bonus.
    Retourne: (conditions_dict, current_price)
    """
    symbol = box["symbol"]
    conds = {
        "c1_dmi_cross": False,
        "c2_break_high": False,
        "c3_rsi_hh": False,
        "c4_cloud_1h": False,
        "c5_cloud_30m": False,
        "b1_volume": False,
        "b1_vol_tf": "",
        "b1_vol_ratio": 0.0,
        "b2_retest": False,
        # Valeurs live
        "live_rsi": 0, "live_dip": 0, "live_dim": 0,
        "live_price": 0, "live_cloud_1h": 0, "live_cloud_30m": 0,
    }

    # ═══ 4H Data ═══
    df_4h = get_klines(symbol, "4h", 100)
    if df_4h is None:
        return conds

    h4 = df_4h["high"].values; l4 = df_4h["low"].values
    c4 = df_4h["close"].values; v4 = df_4h["volume"].values
    n4 = len(c4)

    rsi_4h = calc_rsi(c4, RSI_LENGTH)
    pdi_4h, mdi_4h = calc_dmi(h4, l4, c4, DMI_LENGTH)
    vr_4h = calc_volume_ratio(v4)

    # Current = last closed candle
    ci = n4 - 2 if n4 > 2 else n4 - 1
    conds["live_rsi"] = float(rsi_4h[ci])
    conds["live_dip"] = float(pdi_4h[ci])
    conds["live_dim"] = float(mdi_4h[ci])
    conds["live_price"] = float(c4[ci])

    # C1: DMI+ > DMI- on 4H (current state)
    conds["c1_dmi_cross"] = pdi_4h[ci] > mdi_4h[ci]

    # C2: 4H close > Box High (any of last 3 closed candles)
    for j in range(max(0, n4 - 4), n4 - 1):
        if c4[j] > box["high_4h"]:
            conds["c2_break_high"] = True
            break

    # C3: RSI Higher High (only meaningful if C2 = break)
    if conds["c2_break_high"]:
        conds["c3_rsi_hh"] = rsi_4h[ci] > box["rsi_signal"]

    # Volume 4H bonus
    for j in range(max(0, n4 - 3), n4):
        if vr_4h[j] >= VOLUME_BREAK_MULT:
            conds["b1_volume"] = True
            conds["b1_vol_tf"] = "4H"
            conds["b1_vol_ratio"] = float(vr_4h[j])
            break

    # ═══ 1H Data ═══
    df_1h = get_klines(symbol, "1h", 200)
    if df_1h is not None:
        h1 = df_1h["high"].values; l1 = df_1h["low"].values
        c1 = df_1h["close"].values; v1 = df_1h["volume"].values
        n1 = len(c1)

        # C4: Price > Cloud Top 1H
        cloud_1h = calc_assyin_cloud(df_1h)
        ct_1h = cloud_1h[n1 - 1]
        if np.isnan(ct_1h) and n1 > 2:
            ct_1h = cloud_1h[n1 - 2]
        conds["live_cloud_1h"] = float(ct_1h) if not np.isnan(ct_1h) else 0
        if not np.isnan(ct_1h) and c1[n1 - 1] > ct_1h:
            conds["c4_cloud_1h"] = True

        # Volume 1H
        if not conds["b1_volume"]:
            vr_1h = calc_volume_ratio(v1)
            for j in range(max(0, n1 - 4), n1):
                if vr_1h[j] >= VOLUME_BREAK_MULT:
                    conds["b1_volume"] = True
                    conds["b1_vol_tf"] = "1H"
                    conds["b1_vol_ratio"] = float(vr_1h[j])
                    break

        # B2: Retest support — prix touche Box High ±0.5% puis rebondit
        gb_hi = box["high_4h"]
        tol = gb_hi * RETEST_TOLERANCE_PCT / 100
        for j in range(max(0, n1 - 8), n1):
            if abs(l1[j] - gb_hi) <= tol and c1[j] > gb_hi:
                conds["b2_retest"] = True
                break

    # ═══ 30M Data ═══
    df_30m = get_klines(symbol, "30m", 200)
    if df_30m is not None:
        c30 = df_30m["close"].values; v30 = df_30m["volume"].values
        n30 = len(c30)

        # C5: Price > Cloud Top 30M
        cloud_30m = calc_assyin_cloud(df_30m)
        ct_30m = cloud_30m[n30 - 1]
        if np.isnan(ct_30m) and n30 > 2:
            ct_30m = cloud_30m[n30 - 2]
        conds["live_cloud_30m"] = float(ct_30m) if not np.isnan(ct_30m) else 0
        if not np.isnan(ct_30m) and c30[n30 - 1] > ct_30m:
            conds["c5_cloud_30m"] = True

        # Volume 30M
        if not conds["b1_volume"]:
            vr_30m = calc_volume_ratio(v30)
            for j in range(max(0, n30 - 8), n30):
                if vr_30m[j] >= VOLUME_BREAK_MULT:
                    conds["b1_volume"] = True
                    conds["b1_vol_tf"] = "30M"
                    conds["b1_vol_ratio"] = float(vr_30m[j])
                    break

    return conds


def replay_entry_check(box):
    """
    🔄 REPLAY HISTORIQUE — Scanne barre par barre les 4H après le signal
    pour trouver la PREMIÈRE bougie où les 5 conditions sont réunies.
    Identique au comportement du PineScript.
    
    Returns: (found, entry_conds) where found=True if entry detected
    """
    symbol = box["symbol"]
    box_high = box["high_4h"]
    rsi_ref = box["rsi_signal"]
    
    # Parse signal time
    candle_start = None
    for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"]:
        try:
            candle_start = datetime.strptime(box["candle_4h"], fmt)
            break
        except:
            continue
    if candle_start is None:
        return False, None
    if candle_start.tzinfo is None:
        candle_start = candle_start.replace(tzinfo=timezone.utc)

    print(f"  🔄 Replay depuis {candle_start.strftime('%d/%m %H:%M')}...")

    # ═══ Get all data ═══
    df_4h = get_klines(symbol, "4h", 500)
    df_1h = get_klines(symbol, "1h", 500)
    df_30m = get_klines(symbol, "30m", 500)
    
    if df_4h is None:
        print(f"  ❌ No 4H data")
        return False, None

    # ═══ 4H indicators ═══
    h4 = df_4h["high"].values; l4 = df_4h["low"].values
    c4 = df_4h["close"].values; v4 = df_4h["volume"].values
    n4 = len(c4)
    t4 = df_4h["open_time"].values
    
    rsi_4h = calc_rsi(c4, RSI_LENGTH)
    pdi_4h, mdi_4h = calc_dmi(h4, l4, c4, DMI_LENGTH)
    vr_4h = calc_volume_ratio(v4)

    # ═══ 1H cloud ═══
    cloud_1h = None; t1 = None; c1_arr = None
    if df_1h is not None:
        cloud_1h = calc_assyin_cloud(df_1h)
        t1 = df_1h["open_time"].values
        c1_arr = df_1h["close"].values

    # ═══ 30M cloud ═══
    cloud_30m = None; t30 = None; c30_arr = None
    if df_30m is not None:
        cloud_30m = calc_assyin_cloud(df_30m)
        t30 = df_30m["open_time"].values
        c30_arr = df_30m["close"].values

    # ═══ Find signal bar index in 4H ═══
    signal_idx = None
    signal_ts = pd.Timestamp(candle_start).tz_localize(None)
    for i in range(n4):
        bar_ts = pd.Timestamp(t4[i]).tz_localize(None)
        diff_h = abs((bar_ts - signal_ts).total_seconds()) / 3600
        if diff_h < 2:
            signal_idx = i
            break
    
    if signal_idx is None:
        print(f"  ⚠️ Signal bar not found in 4H data range")
        return False, None

    print(f"     📊 Signal idx: {signal_idx}/{n4-1} ({n4 - signal_idx - 1} bars to scan)")

    # ═══ Helper: find closest bar in lower TF ═══
    def find_tf_bar(tf_timestamps, h4_open_time, offset_hours):
        if tf_timestamps is None:
            return None
        target = pd.Timestamp(h4_open_time).tz_localize(None) + pd.Timedelta(hours=offset_hours)
        best_idx = None; best_diff = float('inf')
        for j in range(len(tf_timestamps)):
            jt = pd.Timestamp(tf_timestamps[j]).tz_localize(None)
            diff = abs((jt - target).total_seconds())
            if diff < best_diff:
                best_diff = diff; best_idx = j
            elif jt > target + pd.Timedelta(hours=2):
                break
        return best_idx

    # ═══ Scan bar by bar ═══
    for i in range(signal_idx + 1, n4 - 1):
        c1_ok = pdi_4h[i] > mdi_4h[i]
        c2_ok = c4[i] > box_high
        c3_ok = c2_ok and rsi_4h[i] > rsi_ref
        
        c4_ok = False
        if cloud_1h is not None:
            j1 = find_tf_bar(t1, t4[i], 3)
            if j1 is not None and j1 < len(cloud_1h):
                ct = cloud_1h[j1]
                if not np.isnan(ct) and c1_arr[j1] > ct:
                    c4_ok = True
        
        c5_ok = False
        if cloud_30m is not None:
            j30 = find_tf_bar(t30, t4[i], 3.5)
            if j30 is not None and j30 < len(cloud_30m):
                ct = cloud_30m[j30]
                if not np.isnan(ct) and c30_arr[j30] > ct:
                    c5_ok = True

        met = sum([c1_ok, c2_ok, c3_ok, c4_ok, c5_ok])
        bar_time = pd.Timestamp(t4[i]).tz_localize(None)
        vol_ratio = float(vr_4h[i])

        print(f"     [{bar_time.strftime('%d/%m %H:%M')}] "
              f"{ic(c1_ok)} DMI {ic(c2_ok)} Brk {ic(c3_ok)} RSI "
              f"{ic(c4_ok)} C1H {ic(c5_ok)} C30 → {met}/5"
              f"{'  🎯 ENTRY!' if met == 5 else ''}")

        if met == 5:
            entry_price = float(c4[i])
            entry_time = bar_time.strftime("%Y-%m-%d %H:%M")
            rr = abs(box["tp_target"] - entry_price) / max(
                abs(entry_price - box["sl_target"]), 0.00000001)
            
            entry_conds = {
                "c1_dmi_cross": True, "c2_break_high": True, "c3_rsi_hh": True,
                "c4_cloud_1h": True, "c5_cloud_30m": True,
                "b1_volume": vol_ratio >= VOLUME_BREAK_MULT,
                "b1_vol_tf": "4H" if vol_ratio >= VOLUME_BREAK_MULT else "",
                "b1_vol_ratio": vol_ratio, "b2_retest": False,
                "live_rsi": float(rsi_4h[i]), "live_dip": float(pdi_4h[i]),
                "live_dim": float(mdi_4h[i]), "live_price": entry_price,
                "live_cloud_1h": 0, "live_cloud_30m": 0,
            }
            
            box["status"] = "ENTRY_READY"
            box["entry_price"] = entry_price
            box["entry_time"] = entry_time
            
            print(f"\n  🎯 ENTRY trouvée le {entry_time}")
            print(f"     💰 Entry: {entry_price:.8g}")
            print(f"     🎯 TP: {box['tp_target']:.8g} | 🛑 SL: {box['sl_target']:.8g}")
            print(f"     📊 R:R 1:{rr:.1f} | RSI: {rsi_4h[i]:.1f}")
            
            return True, entry_conds
    
    # No entry found — return current state
    li = n4 - 2
    last_conds = {
        "c1_dmi_cross": pdi_4h[li] > mdi_4h[li],
        "c2_break_high": c4[li] > box_high,
        "c3_rsi_hh": c4[li] > box_high and rsi_4h[li] > rsi_ref,
        "c4_cloud_1h": False, "c5_cloud_30m": False,
        "b1_volume": False, "b1_vol_tf": "", "b1_vol_ratio": 0,
        "b2_retest": False,
        "live_rsi": float(rsi_4h[li]), "live_dip": float(pdi_4h[li]),
        "live_dim": float(mdi_4h[li]), "live_price": float(c4[li]),
        "live_cloud_1h": 0, "live_cloud_30m": 0,
    }
    met = mandatory_count(last_conds)
    print(f"\n  📦 Pas d'entrée trouvée — actuellement {met}/5")
    return False, last_conds


def is_signal_old(box):
    """Check if signal is more than 8 hours old (needs replay)"""
    try:
        for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M"]:
            try:
                sig_dt = datetime.strptime(box["candle_4h"], fmt)
                break
            except:
                continue
        else:
            return False
        if sig_dt.tzinfo is None:
            sig_dt = sig_dt.replace(tzinfo=timezone.utc)
        age_hours = (datetime.now(timezone.utc) - sig_dt).total_seconds() / 3600
        return age_hours > 8  # More than 2 × 4H bars old
    except:
        return False


def is_entry_ready(c):
    return all([c["c1_dmi_cross"], c["c2_break_high"], c["c3_rsi_hh"],
                c["c4_cloud_1h"], c["c5_cloud_30m"]])

def mandatory_count(c):
    return sum(1 for k in ["c1_dmi_cross", "c2_break_high", "c3_rsi_hh",
                            "c4_cloud_1h", "c5_cloud_30m"] if c[k])

def ic(v):
    return "✅" if v else "❌"

def ib(v):
    return "🟢" if v else "⚪"


# ═══════════════════════════════════════════════════════
# 📱 TELEGRAM NOTIFICATIONS
# ═══════════════════════════════════════════════════════
def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True
        }, timeout=10)
    except Exception as e:
        print(f"  ⚠️ Telegram: {e}")


def send_entry_notification(box, conds):
    """Notification Telegram complète quand ENTRY READY"""
    s = box["symbol"]
    ep = conds["live_price"]
    tp = box["tp_target"]
    sl = box["sl_target"]
    rr = abs(tp - ep) / max(abs(ep - sl), 0.00000001)
    
    tfs = box.get("alert_tfs", "")
    alert_t = box.get("alert_time", "")

    msg = (
        f"🎯🎯🎯 <b>ENTRY READY</b> 🎯🎯🎯\n"
        f"\n"
        f"📊 <b>{s}</b> | ★{box['score']}/10\n"
        f"\n"
        f"━━ MEGA BUY ━━\n"
        f"⏰ Alert: {alert_t}\n"
        f"📡 TFs: {tfs if tfs else 'Manual'}\n"
        f"📅 4H: {box['candle_4h']}\n"
        f"\n"
        f"━━ OBLIGATOIRE ━━\n"
        f"{ic(conds['c1_dmi_cross'])} DMI+ &gt; DMI- (4H)\n"
        f"{ic(conds['c2_break_high'])} Break Box High (4H)\n"
        f"{ic(conds['c3_rsi_hh'])} RSI HH &gt; {box['rsi_signal']:.1f} (4H)\n"
        f"{ic(conds['c4_cloud_1h'])} Prix &gt; Cloud (1H)\n"
        f"{ic(conds['c5_cloud_30m'])} Prix &gt; Cloud (30M)\n"
        f"\n"
        f"━━ BONUS ━━\n"
        f"{ib(conds['b1_volume'])} Volume {conds['b1_vol_ratio']:.1f}× ({conds['b1_vol_tf']})\n"
        f"{ib(conds['b2_retest'])} Retest Support\n"
        f"\n"
        f"━━ ENTRY ━━\n"
        f"💰 Entry: <b>{ep:.8g}</b>\n"
        f"🎯 TP: <b>{tp:.8g}</b>\n"
        f"🛑 SL: <b>{sl:.8g}</b>\n"
        f"📊 R:R <b>1:{rr:.1f}</b>\n"
        f"\n"
        f"📈 RSI: {conds['live_rsi']:.1f} | DI+: {conds['live_dip']:.1f} DI-: {conds['live_dim']:.1f}"
    )
    send_telegram(msg)


def send_new_box_notification(box):
    """Notification quand nouvelle Golden Box créée"""
    tfs = box.get("alert_tfs", "")
    emotion = box.get("alert_emotion", "")
    alert_t = box.get("alert_time", "")
    
    tfs_line = f"\n📡 TFs: {tfs}" if tfs else ""
    emotion_line = f"\n{emotion}" if emotion else ""
    alert_line = f"\n⏰ Alert: {alert_t}" if alert_t else ""
    
    msg = (
        f"📦 <b>Nouvelle Golden Box</b>\n"
        f"\n"
        f"📊 <b>{box['symbol']}</b> | ★{box['score']}/10\n"
        f"📅 4H: {box['candle_4h']}\n"
        f"📦 H: {box['high_4h']:.8g} | L: {box['low_4h']:.8g}\n"
        f"📊 RSI ref: {box['rsi_signal']:.1f}"
        f"{tfs_line}{alert_line}{emotion_line}\n"
        f"\n"
        f"🎯 TP: {box['tp_target']:.8g} | SL: {box['sl_target']:.8g}\n"
        f"🔍 Surveillance démarrée ({CHECK_INTERVAL_MIN}min)"
    )
    send_telegram(msg)


def send_watching_update(boxes):
    """Résumé périodique des boxes en surveillance"""
    watching = {k: v for k, v in boxes.items() if v["status"] == "WATCHING"}
    if not watching:
        return
    
    lines = ["📦 <b>Golden Boxes actives</b>\n"]
    for key, box in watching.items():
        conds = box.get("last_conditions", {})
        met = sum(1 for k in ["c1_dmi_cross", "c2_break_high", "c3_rsi_hh",
                               "c4_cloud_1h", "c5_cloud_30m"] if conds.get(k, False))
        lines.append(
            f"• <b>{box['symbol']}</b> ★{box['score']} | "
            f"{met}/5 | check {box['checks_count']}/{box['max_checks']}"
        )
    
    send_telegram("\n".join(lines))


def send_check_update(box, conds, met, check_num, max_chk):
    """Notification Telegram UNIQUEMENT pour les boxes proches (≥4/5)"""
    if met < 4:
        return  # Skip — sera inclus dans le résumé groupé
    
    s = box["symbol"]
    bar = "█" * met + "░" * (5 - met)
    
    msg = (
        f"{'🎯🎯🎯' if met == 5 else '🔥'} <b>{'ENTRY READY' if met == 5 else 'HOT'} — {s}</b> ★{box['score']}\n"
        f"Check {check_num}/{max_chk}\n"
        f"\n"
        f"[{bar}] <b>{met}/5</b>\n"
        f"\n"
        f"{ic(conds['c1_dmi_cross'])} DMI+ &gt; DMI- (4H)\n"
        f"{ic(conds['c2_break_high'])} Break Box High (4H)\n"
        f"{ic(conds['c3_rsi_hh'])} RSI HH &gt; {box['rsi_signal']:.1f} (4H)\n"
        f"{ic(conds['c4_cloud_1h'])} Prix &gt; Cloud (1H)\n"
        f"{ic(conds['c5_cloud_30m'])} Prix &gt; Cloud (30M)\n"
        f"\n"
        f"{ib(conds['b1_volume'])} Vol {conds['b1_vol_ratio']:.1f}× {conds['b1_vol_tf']}  "
        f"{ib(conds['b2_retest'])} Retest\n"
        f"\n"
        f"💰 {conds['live_price']:.8g} | RSI:{conds['live_rsi']:.1f} | "
        f"DI+:{conds['live_dip']:.1f} DI-:{conds['live_dim']:.1f}"
    )
    send_telegram(msg)


def send_check_summary(results):
    """Résumé groupé de toutes les boxes après un check cycle"""
    if not results:
        return
    
    # Group by met count
    hot = [(s, m) for s, m, sc in results if m >= 4]
    warm = [(s, m) for s, m, sc in results if m == 3]
    cold = [(s, m) for s, m, sc in results if m <= 2]
    
    lines = [f"📊 <b>Check Summary</b> — {len(results)} boxes\n"]
    
    if hot:
        lines.append("🔥 <b>HOT (4-5/5):</b>")
        for s, m in hot:
            lines.append(f"  • {s} → <b>{m}/5</b>")
    
    if warm:
        lines.append(f"\n🟡 <b>WARM (3/5):</b> {', '.join(s for s, m in warm)}")
    
    if cold:
        lines.append(f"\n⚪ <b>COLD (0-2/5):</b> {len(cold)} boxes")
    
    send_telegram("\n".join(lines))


# ═══════════════════════════════════════════════════════
# 📊 GOOGLE SHEETS
# ═══════════════════════════════════════════════════════
_gs_spreadsheet = None

def init_google_sheets():
    global _gs_spreadsheet
    if not GOOGLE_SHEETS_ENABLED or not GSPREAD_OK:
        return False
    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDS_FILE,
            scopes=["https://spreadsheets.google.com/feeds",
                     "https://www.googleapis.com/auth/drive"])
        gc = gspread.authorize(creds)
        _gs_spreadsheet = gc.open(GOOGLE_SHEET_NAME)
        return True
    except Exception as e:
        print(f"  ⚠️ Google Sheets: {e}")
        return False


def get_or_create_daily_sheet():
    """Crée/récupère la feuille du jour pour les entrées"""
    if _gs_spreadsheet is None:
        return None
    today = datetime.now(timezone.utc).strftime("Entry - %d/%m/%Y")
    try:
        return _gs_spreadsheet.worksheet(today)
    except gspread.WorksheetNotFound:
        ws = _gs_spreadsheet.add_worksheet(title=today, rows=100, cols=35)
        headers = [
            # ── ENTRY ──
            "Heure",            # A
            "Paire",            # B
            "Entry",            # C
            "TP",               # D
            "SL",               # E
            "R:R",              # F
            # ── CONDITIONS ──
            "DMI+>-",           # G
            "Break",            # H
            "RSI↑",             # I
            "Cloud 1H",         # J
            "Cloud 30M",        # K
            # ── BONUS ──
            "Volume",           # L
            "Retest",           # M
            # ── MEGA BUY SIGNAL ──
            "Alert Time",       # N: quand le MEGA BUY a fire
            "Alert TFs",        # O: 15m,30m,1h,4h
            "Nb TF",            # P: nombre de TFs
            "Émotion",          # Q: émotion du signal
            "Prix Signal",      # R: prix au moment du signal
            "RSI Signal",       # S: RSI au moment du signal
            "DI+ Signal",       # T: DI+ au moment du signal
            "★ Score",          # U
            # ── GOLDEN BOX ──
            "Box High",         # V
            "Box Low",          # W
            "RSI Ref",          # X: RSI de la bougie 4H
            "4H Candle",        # Y: datetime de la bougie 4H
            "Status",           # Z
            # ── LIVE VALUES ──
            "RSI",              # AA
            "DI+",              # AB
            "DI-",              # AC
            "Vol ×",            # AD
            "Vol TF",           # AE
            # ── META ──
            "Entry Date",       # AF
            "Mode",             # AG: LIVE / REPLAY
        ]
        ws.append_row(headers)
        return ws


def log_entry_to_sheet(box, conds, mode="LIVE"):
    """Log une entrée dans la feuille Google Sheets du jour"""
    ws = get_or_create_daily_sheet()
    if ws is None:
        return
    
    ep = conds["live_price"]
    tp = box["tp_target"]
    sl = box["sl_target"]
    rr = abs(tp - ep) / max(abs(ep - sl), 0.00000001)

    try:
        row = [
            # ── ENTRY ──
            datetime.now(timezone.utc).strftime("%H:%M:%S"),
            box["symbol"].replace("USDT", ""),
            round(ep, 8),
            round(tp, 8),
            round(sl, 8),
            f"1:{rr:.1f}",
            # ── CONDITIONS ──
            "✓" if conds["c1_dmi_cross"] else "✗",
            "✓" if conds["c2_break_high"] else "✗",
            "✓" if conds["c3_rsi_hh"] else "✗",
            "✓" if conds["c4_cloud_1h"] else "✗",
            "✓" if conds["c5_cloud_30m"] else "✗",
            # ── BONUS ──
            f"✓ {conds['b1_vol_ratio']:.1f}× {conds['b1_vol_tf']}" if conds["b1_volume"] else "✗",
            "✓" if conds["b2_retest"] else "✗",
            # ── MEGA BUY SIGNAL ──
            box.get("alert_time", ""),
            box.get("alert_tfs", ""),
            box.get("alert_nb_tf", ""),
            box.get("alert_emotion", ""),
            box.get("alert_prix", ""),
            box.get("alert_rsi", ""),
            box.get("alert_dip", ""),
            box["score"],
            # ── GOLDEN BOX ──
            round(box["high_4h"], 8),
            round(box["low_4h"], 8),
            round(box["rsi_signal"], 1),
            box["candle_4h"],
            box["status"],
            # ── LIVE VALUES ──
            round(conds["live_rsi"], 1),
            round(conds["live_dip"], 1),
            round(conds["live_dim"], 1),
            round(conds["b1_vol_ratio"], 1),
            conds["b1_vol_tf"],
            # ── META ──
            box.get("entry_time", ""),
            mode,
        ]
        ws.append_row(row)
        print(f"  📊 Sheet: {box['symbol']} logged ({mode})")
    except Exception as e:
        print(f"  ⚠️ Sheet log: {e}")


def import_new_alerts_from_sheet(boxes):
    """
    Importe les nouvelles alertes MEGA BUY depuis Google Sheets.
    Format du Bot Scanner (feuille 'Alerts') :
      Col A: Date/Heure (alert detection time)
      Col B: Paire (BTCUSDT)
      Col C: Score /10
      Col D: TFs (15m,30m,1h,4h)
      Col E: Nb TF
      Col F: Émotion
      Col G: Prix
      Col H: RSI
      Col I: DI+
    """
    if _gs_spreadsheet is None:
        return boxes
    try:
        # First worksheet = alerts
        alerts_ws = _gs_spreadsheet.get_worksheet(0)
        all_data = alerts_ws.get_all_values()
        if len(all_data) <= 1:
            return boxes

        added = 0
        for row in all_data[-50:]:
            if len(row) < 2:
                continue
            
            date_str = row[0].strip()
            symbol_raw = row[1].strip().upper()
            
            # Skip header
            if "date" in date_str.lower() or "symbol" in symbol_raw.lower() or "paire" in symbol_raw.lower():
                continue
            
            # Ensure USDT suffix
            symbol = symbol_raw if symbol_raw.endswith("USDT") else symbol_raw + "USDT"
            
            # Score
            score = 0
            if len(row) >= 3:
                try:
                    score = int(row[2])
                except:
                    pass

            # TFs (col D)
            alert_tfs = row[3].strip() if len(row) >= 4 else ""
            
            # ── FILTRE: rejeter les signaux 15m seul ──
            if alert_tfs:
                tfs_list = [t.strip().lower() for t in alert_tfs.replace(",", " ").split()]
                if tfs_list == ["15m"]:
                    continue  # 15m seul → skip
            
            # Nb TF (col E)
            alert_nb_tf = row[4].strip() if len(row) >= 5 else ""
            
            # Émotion (col F)
            alert_emotion = row[5].strip() if len(row) >= 6 else ""
            
            # Prix at alert (col G)
            alert_prix = row[6].strip() if len(row) >= 7 else ""
            
            # RSI at alert (col H)
            alert_rsi = row[7].strip() if len(row) >= 8 else ""
            
            # DI+ at alert (col I)
            alert_dip = row[8].strip() if len(row) >= 9 else ""

            # Unique key
            box_key = f"{symbol}_{date_str}"
            if box_key in boxes:
                continue

            # Skip old alerts (>72h)
            try:
                for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"]:
                    try:
                        alert_dt = datetime.strptime(date_str, fmt)
                        break
                    except:
                        continue
                else:
                    continue
                if (datetime.now() - alert_dt).total_seconds() / 3600 > 72:
                    continue
            except:
                continue

            print(f"  📦 Nouvelle alerte: {symbol} ({date_str}) ★{score} [{alert_tfs}]")
            box = create_golden_box(symbol, date_str, score=score)
            if box:
                # Store MEGA BUY alert details
                box["alert_time"] = date_str
                box["alert_tfs"] = alert_tfs
                box["alert_nb_tf"] = alert_nb_tf
                box["alert_emotion"] = alert_emotion
                box["alert_prix"] = alert_prix
                box["alert_rsi"] = alert_rsi
                box["alert_dip"] = alert_dip
                
                boxes[box_key] = box
                send_new_box_notification(box)
                added += 1
                time.sleep(0.2)

        if added:
            print(f"  ✅ {added} nouvelles Golden Boxes créées")
            save_golden_boxes(boxes)

    except Exception as e:
        print(f"  ⚠️ Import: {e}")
    
    return boxes


# ═══════════════════════════════════════════════════════
# 🖥️ MANUAL INPUT & MANAGEMENT
# ═══════════════════════════════════════════════════════
def add_box_manual(boxes):
    """Ajout manuel d'une Golden Box depuis le terminal"""
    print("\n📦 Ajout manuel d'une Golden Box")
    print("─" * 40)
    
    symbol = input("  📊 Symbol (ex: LINEAUSDT) : ").strip().upper()
    if not symbol:
        return boxes
    if not symbol.endswith("USDT"):
        symbol += "USDT"
    
    date_str = input("  📅 4H Candle (ex: 09/02/2026 12:00) : ").strip()
    if not date_str:
        return boxes
    
    score_str = input("  ★ Score /10 [8] : ").strip()
    score = int(score_str) if score_str else 8

    box_key = f"{symbol}_{date_str}"
    if box_key in boxes:
        rep = input(f"  ⚠️ Box déjà existante. Remplacer ? (o/n) [n] : ").strip().lower()
        if rep != "o":
            return boxes
        del boxes[box_key]
        print(f"  🗑️ Ancienne box supprimée")

    box = create_golden_box(symbol, date_str, score=score)
    if box:
        boxes[box_key] = box
        save_golden_boxes(boxes)
        send_new_box_notification(box)
        print(f"  ✅ Golden Box créée et Telegram notifié")
        
        # Immediate check: REPLAY for old signals, LIVE for new
        if is_signal_old(box):
            print(f"\n  🔄 Signal ancien — lancement du replay historique...")
            found, entry_conds = replay_entry_check(box)
            if found:
                save_golden_boxes(boxes)
                send_entry_notification(box, entry_conds)
                send_telegram(
                    f"📜 <b>Replay historique</b> — {symbol}\n"
                    f"Entry trouvée le {box['entry_time']}\n"
                    f"💰 {box['entry_price']:.8g}"
                )
                print(f"\n  🎯🎯🎯 ENTRY READY (replay) — {symbol} 🎯🎯🎯")
                log_entry_to_sheet(box, entry_conds, mode="REPLAY")
            else:
                if entry_conds:
                    box["last_conditions"] = entry_conds
                    met = mandatory_count(entry_conds)
                    send_check_update(box, entry_conds, met, 1, box["max_checks"])
                print(f"  📦 Pas d'entrée historique — surveillance live activée")
        else:
            print(f"\n  🔍 Check immédiat (signal récent)...")
            conds = check_entry_conditions(box)
            box["last_conditions"] = conds
            box["checks_count"] += 1
            met = mandatory_count(conds)
            
            print(f"     {ic(conds['c1_dmi_cross'])} DMI+>DMI-  "
                  f"{ic(conds['c2_break_high'])} Break  "
                  f"{ic(conds['c3_rsi_hh'])} RSI HH  "
                  f"{ic(conds['c4_cloud_1h'])} CL-1H  "
                  f"{ic(conds['c5_cloud_30m'])} CL-30M  → {met}/5")
            
            send_check_update(box, conds, met, 1, box["max_checks"])
            
            if is_entry_ready(conds):
                box["status"] = "ENTRY_READY"
                box["entry_price"] = conds["live_price"]
                box["entry_time"] = datetime.now(timezone.utc).isoformat()
                send_entry_notification(box, conds)
                log_entry_to_sheet(box, conds, mode="LIVE")
                print(f"\n  🎯🎯🎯 ENTRY READY — {symbol} 🎯🎯🎯")
        
        save_golden_boxes(boxes)
    
    return boxes


def list_boxes(boxes):
    """Affiche toutes les Golden Boxes"""
    if not boxes:
        print("\n  ℹ️ Aucune Golden Box")
        return
    
    watching = [(k, b) for k, b in boxes.items() if b["status"] == "WATCHING"]
    ready = [(k, b) for k, b in boxes.items() if b["status"] == "ENTRY_READY"]
    expired = [(k, b) for k, b in boxes.items() if b["status"] == "EXPIRED"]
    
    print(f"\n{'─'*60}")
    print(f"  📦 Golden Boxes — Total: {len(boxes)}")
    print(f"  🔍 Watching: {len(watching)} | 🎯 Ready: {len(ready)} | ⏰ Expired: {len(expired)}")
    print(f"{'─'*60}")
    
    for status_name, items, emoji in [
        ("WATCHING", watching, "🔍"),
        ("ENTRY_READY", ready, "🎯"),
        ("EXPIRED", expired, "⏰")
    ]:
        if not items:
            continue
        print(f"\n  {emoji} {status_name}:")
        for i, (key, box) in enumerate(items):
            conds = box.get("last_conditions", {})
            met = sum(1 for k in ["c1_dmi_cross", "c2_break_high", "c3_rsi_hh",
                                   "c4_cloud_1h", "c5_cloud_30m"] if conds.get(k, False))
            print(f"    [{i+1}] {box['symbol']:<14} ★{box['score']} | "
                  f"{met}/5 | chk {box['checks_count']}/{box['max_checks']} | "
                  f"H:{box['high_4h']:.6g} L:{box['low_4h']:.6g}")
    print()


def delete_box(boxes):
    """Supprimer une Golden Box"""
    if not boxes:
        print("\n  ℹ️ Aucune Golden Box à supprimer")
        return boxes
    
    # List with numbers
    keys = list(boxes.keys())
    print(f"\n{'─'*60}")
    for i, key in enumerate(keys):
        box = boxes[key]
        print(f"  [{i+1}] {box['symbol']:<14} ★{box['score']} | {box['status']} | {box['candle_4h']}")
    print(f"  [0] Annuler")
    print(f"{'─'*60}")
    
    choice = input("  🗑️ Numéro à supprimer : ").strip()
    if not choice or choice == "0":
        return boxes
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(keys):
            key = keys[idx]
            sym = boxes[key]["symbol"]
            del boxes[key]
            save_golden_boxes(boxes)
            print(f"  ✅ {sym} supprimé")
        else:
            print("  ❌ Numéro invalide")
    except ValueError:
        # Try by symbol name
        symbol = choice.upper()
        if not symbol.endswith("USDT"):
            symbol += "USDT"
        found = [k for k in keys if boxes[k]["symbol"] == symbol]
        if found:
            for k in found:
                del boxes[k]
            save_golden_boxes(boxes)
            print(f"  ✅ {len(found)} box(es) {symbol} supprimée(s)")
        else:
            print(f"  ❌ {symbol} non trouvé")
    
    return boxes


def clear_all_boxes(boxes):
    """Supprimer TOUTES les Golden Boxes"""
    if not boxes:
        print("\n  ℹ️ Déjà vide")
        return boxes
    
    n = len(boxes)
    confirm = input(f"\n  ⚠️ Supprimer les {n} Golden Boxes ? (oui/non) : ").strip().lower()
    if confirm == "oui":
        boxes.clear()
        save_golden_boxes(boxes)
        print(f"  ✅ {n} boxes supprimées")
    else:
        print("  ❌ Annulé")
    
    return boxes


# ═══════════════════════════════════════════════════════
# 🔄 MAIN CHECK LOOP
# ═══════════════════════════════════════════════════════
def run_check(boxes):
    """Vérifie toutes les Golden Boxes actives"""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    watching = {k: v for k, v in boxes.items() if v["status"] == "WATCHING"}

    print(f"\n{'═'*60}")
    print(f"🎯 Entry Check — {now}")
    print(f"📦 {len(watching)} Golden Boxes actives")
    print(f"{'═'*60}")

    if not watching:
        print("  ℹ️ Aucune Golden Box à surveiller")
        return boxes

    entries_found = 0
    check_results = []  # (symbol, met, score) for summary

    for key, box in list(watching.items()):
        symbol = box["symbol"]
        box["checks_count"] += 1
        check_num = box["checks_count"]
        max_chk = box["max_checks"]

        print(f"\n  📦 {symbol} ★{box['score']} | check {check_num}/{max_chk}")

        # Old signal + first check → replay historique
        if check_num == 1 and is_signal_old(box):
            found, entry_conds = replay_entry_check(box)
            if found:
                send_entry_notification(box, entry_conds)
                send_telegram(
                    f"📜 <b>Replay</b> — {symbol}\n"
                    f"Entry: {box['entry_time']} | 💰 {box['entry_price']:.8g}"
                )
                log_entry_to_sheet(box, entry_conds, mode="REPLAY")
                entries_found += 1
                check_results.append((symbol, 5, box["score"]))
            else:
                if entry_conds:
                    box["last_conditions"] = entry_conds
                met = mandatory_count(entry_conds) if entry_conds else 0
                check_results.append((symbol, met, box["score"]))
            continue

        conds = check_entry_conditions(box)
        box["last_conditions"] = conds
        met = mandatory_count(conds)

        # Print conditions
        print(f"     {ic(conds['c1_dmi_cross'])} DMI+>DMI-  "
              f"{ic(conds['c2_break_high'])} Break  "
              f"{ic(conds['c3_rsi_hh'])} RSI HH  "
              f"{ic(conds['c4_cloud_1h'])} CL-1H  "
              f"{ic(conds['c5_cloud_30m'])} CL-30M  → {met}/5")
        print(f"     {ib(conds['b1_volume'])} Vol {conds['b1_vol_ratio']:.1f}× {conds['b1_vol_tf']}  "
              f"{ib(conds['b2_retest'])} Retest")
        print(f"     📊 RSI:{conds['live_rsi']:.1f} DI+:{conds['live_dip']:.1f} "
              f"DI-:{conds['live_dim']:.1f} | 💰 {conds['live_price']:.8g}")

        # Track history
        box["conditions_history"].append({
            "time": now,
            "met": met,
            "entry_ready": is_entry_ready(conds)
        })

        # ── Telegram: send individual update only for hot boxes (≥4/5) ──
        send_check_update(box, conds, met, check_num, max_chk)
        check_results.append((symbol, met, box["score"]))

        if is_entry_ready(conds):
            box["status"] = "ENTRY_READY"
            box["entry_price"] = conds["live_price"]
            box["entry_time"] = now

            rr = abs(box["tp_target"] - box["entry_price"]) / max(
                abs(box["entry_price"] - box["sl_target"]), 0.00000001)

            print(f"\n  🎯🎯🎯 ENTRY READY — {symbol} 🎯🎯🎯")
            print(f"     💰 Entry: {box['entry_price']:.8g}")
            print(f"     🎯 TP: {box['tp_target']:.8g}")
            print(f"     🛑 SL: {box['sl_target']:.8g}")
            print(f"     📊 R:R 1:{rr:.1f}")

            send_entry_notification(box, conds)
            log_entry_to_sheet(box, conds)
            entries_found += 1

    boxes = cleanup_expired_boxes(boxes)
    save_golden_boxes(boxes)

    # Send grouped Telegram summary
    send_check_summary(check_results)

    if entries_found:
        print(f"\n  🎯 {entries_found} ENTRY(s) détectée(s) !")

    return boxes


# ═══════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════
def main():
    import sys
    auto_mode = "--auto" in sys.argv

    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     🎯 MEGA BUY Entry Agent v2                   ║
    ║     Golden Box + Cloud Assyin# + DMI Cross       ║
    ║     5 Mandatory + 2 Bonus conditions             ║
    ║     ASSYIN-2026                                  ║
    ╚═══════════════════════════════════════════════════╝
    """)
    print(f"⚙️  Check: {CHECK_INTERVAL_MIN}min | Expiry: {GOLDEN_BOX_EXPIRY_4H}×4H")
    print(f"⚙️  TP: High + {TP_MULTIPLIER}× height | SL: Low - {SL_ATR_BUFFER}× ATR")
    print(f"⚙️  Cloud: Assyin# Dynamic {ICH_SK_MIN}-{ICH_SK_MAX}")
    print(f"⚙️  Volume: {VOLUME_BREAK_MULT}× avg20\n")

    # Telegram startup
    send_telegram(
        "🎯 <b>Entry Agent v2 démarré !</b>\n"
        f"📦 Expiry: {GOLDEN_BOX_EXPIRY_4H}×4H | Check: {CHECK_INTERVAL_MIN}min\n"
        f"📊 5 Conditions: DMI + Break + RSI + Cloud 1H/30M\n"
        f"🔶 Ichimoku: Assyin# Dynamic {ICH_SK_MIN}-{ICH_SK_MAX}"
    )
    print("✅ Telegram connecté")

    # Google Sheets
    gs_ok = init_google_sheets()
    if gs_ok:
        print("✅ Google Sheets connecté")
    else:
        print("⚠️ Google Sheets non disponible (mode manuel)")

    # Load existing boxes
    boxes = load_golden_boxes()
    w = sum(1 for b in boxes.values() if b["status"] == "WATCHING")
    print(f"📦 {w} Golden Boxes chargées\n")

    # Menu initial (skip in auto mode)
    if not auto_mode:
        print("━" * 40)
        print("  Commandes : ")
        print("    [a] Ajouter une Golden Box")
        print("    [l] Lister les Golden Boxes")
        print("    [d] Supprimer une Golden Box")
        print("    [c] Supprimer TOUTES les boxes")
        print("    [s] Démarrer la surveillance")
        print("    [q] Quitter")
        print("━" * 40)

        while True:
            cmd = input("\n  > ").strip().lower()
            if cmd == "a":
                boxes = add_box_manual(boxes)
            elif cmd == "l":
                list_boxes(boxes)
            elif cmd == "d":
                boxes = delete_box(boxes)
            elif cmd == "c":
                boxes = clear_all_boxes(boxes)
            elif cmd == "s":
                break
            elif cmd == "q":
                print("👋 Au revoir")
                return
            elif cmd == "":
                break
            else:
                print("  ❓ Commande inconnue (a/l/d/c/s/q)")
    else:
        print("🤖 Mode automatique activé")

    # Initial import + check
    if gs_ok:
        boxes = import_new_alerts_from_sheet(boxes)
    boxes = run_check(boxes)

    # Main loop
    cycle = 0
    while True:
        try:
            now = datetime.now(timezone.utc)
            m = now.minute; s = now.second
            ns = ((m // CHECK_INTERVAL_MIN) + 1) * CHECK_INTERVAL_MIN
            wait = max(((ns if ns < 60 else 60) - m) * 60 - s + 5, 30)
            nt = now + timedelta(seconds=wait)
            print(f"\n⏳ Prochain check: {nt.strftime('%H:%M')} UTC ({wait}s)")

            time.sleep(wait)
            cycle += 1

            # Import new alerts
            if gs_ok:
                boxes = import_new_alerts_from_sheet(boxes)

            # Check all boxes
            boxes = run_check(boxes)

            # Periodic Telegram summary (every ~4h = 16 × 15min)
            if cycle % 16 == 0:
                send_watching_update(boxes)

        except KeyboardInterrupt:
            print("\n🛑 Arrêt de l'agent")
            save_golden_boxes(boxes)
            send_telegram("🛑 Entry Agent v2 arrêté")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
