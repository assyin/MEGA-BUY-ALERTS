"""
🎯 MEGA BUY Entry Agent v1 — Golden Box Monitor
Surveille les alertes MEGA BUY et détecte les entrées optimales
Conditions d'entrée :
  ✅ DMI+ cross above DMI- en 4H
  ✅ Bougie 4H CLÔTURE > High Golden Box
  ✅ RSI break > RSI signal (4H)
  ✅ Prix > Span B en 1H (obligatoire)
  ✅ Prix > Span B en 30M (obligatoire)
  ✅ Volume break > 1.5× avg20 sur au moins 1 TF (bonus)
  ✅ Retest du High comme support (bonus)

Auteur: ASSYIN-2026
"""

import requests
import numpy as np
import pandas as pd
import time
import os
import json
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

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
TELEGRAM_TOKEN = "8577547027:AAEtfLHY0RlGISvN_RpwoLMtIVmrGVV74mo"
TELEGRAM_CHAT_ID = "308638133"

GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEET_NAME = "MEGA BUY Alerts"
GOOGLE_CREDS_FILE = "google_creds.json"

CHECK_INTERVAL_MIN = 15
GOLDEN_BOX_EXPIRY_4H = 15       # Max 15 bougies 4H (~60h)

VOLUME_BREAK_MULTIPLIER = 1.5

TP_MULTIPLIER = 1.5              # TP = 1.5× hauteur Golden Box
SL_ATR_BUFFER = 0.5              # SL = Low - 0.5× ATR

RSI_LENGTH = 14
DMI_LENGTH = 14
DMI_ADX_SMOOTH = 14
ATR_LENGTH = 14

# ═══════════════════════════════════════════════════════
# 📡 BINANCE API
# ═══════════════════════════════════════════════════════
BINANCE_BASE = "https://api.binance.com"
_http = requests.Session()
_http.mount('https://', requests.adapters.HTTPAdapter(
    pool_connections=20, pool_maxsize=20, max_retries=2))


def get_klines(symbol, interval, limit=200):
    try:
        resp = _http.get(f"{BINANCE_BASE}/api/v3/klines",
                         params={"symbol": symbol, "interval": interval, "limit": limit},
                         timeout=15)
        data = resp.json()
        if not isinstance(data, list) or len(data) < 50:
            return None
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"])
        for c in ["open", "high", "low", "close", "volume"]:
            df[c] = df[c].astype(float)
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        return df
    except Exception as e:
        return None


# ═══════════════════════════════════════════════════════
# 📊 INDICATEURS
# ═══════════════════════════════════════════════════════
def rma(s, l):
    a = 1.0 / l; r = np.zeros(len(s)); r[0] = s[0]
    for i in range(1, len(s)): r[i] = a * s[i] + (1 - a) * r[i - 1]
    return r

def true_range(h, l, c):
    tr = np.zeros(len(h)); tr[0] = h[0] - l[0]
    for i in range(1, len(h)):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    return tr

def calc_rsi(close, length=14):
    delta = np.diff(close, prepend=close[0])
    g = np.maximum(delta, 0); lo = -np.minimum(delta, 0)
    ag = rma(g, length); al = rma(lo, length)
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(al == 0, 100, ag / al)
        return np.where(al == 0, 100, 100 - (100 / (1 + rs)))

def calc_dmi(high, low, close, length=14):
    n = len(high); pdm = np.zeros(n); mdm = np.zeros(n)
    for i in range(1, n):
        u = high[i] - high[i - 1]; d = low[i - 1] - low[i]
        pdm[i] = u if (u > d and u > 0) else 0
        mdm[i] = d if (d > u and d > 0) else 0
    tr = true_range(high, low, close); atr = rma(tr, length)
    asf = np.where(atr == 0, 1, atr)
    pdi = 100 * rma(pdm, length) / asf
    mdi = 100 * rma(mdm, length) / asf
    return pdi, mdi

def calc_atr(high, low, close, length=14):
    return rma(true_range(high, low, close), length)

# ═══════════════════════════════════════════════════════
# 🔶 ASSYIN# ICHIMOKU KINKO — Moteur complet
# Reproduction exacte du PineScript avec :
#   - Source alternative (close>open ? high : low) + SWMA
#   - Volume Heikin Ashi + OBV
#   - ATR Volatilité (fast 14 > slow 46)
#   - Chikou Trend Filter (period 25)
#   - Longueur dynamique adaptative (50-120, 96.85%)
#   - Span B avec displacement 25
# ═══════════════════════════════════════════════════════

# Paramètres Ichimoku (identiques au PineScript)
# Tenkan dynamic
ICH_TK_MIN = 9            # Tenkan Min Length
ICH_TK_MAX = 30           # Tenkan Max Length
ICH_TK_PCT = 0.9685       # 96.85%
# Kijun dynamic
ICH_KJ_MIN = 20           # Kijun Min Length
ICH_KJ_MAX = 60           # Kijun Max Length
ICH_KJ_PCT = 0.9685
# Senkou dynamic
ICH_SK_MIN = 50            # Senkou-Span Min Length
ICH_SK_MAX = 120           # Senkou-Span Max Length
ICH_SK_PCT = 0.9685
ICH_SK_OFFSET = 25         # Senkou-Span Offset (26-1)
# Filters
ICH_CH_FILT_PER = 25       # Chikou Filter Period
ICH_VOL_PEAK = 50          # Volume Peak threshold
ICH_ATR_FAST = 14          # ATR Fast Length
ICH_ATR_SLOW = 46          # ATR Slow Length


def calc_swma(src):
    """Symmetrically Weighted Moving Average (4 bars) — [1,2,2,1]/6"""
    n = len(src); out = np.copy(src)
    for i in range(3, n):
        out[i] = (src[i - 3] * 1 + src[i - 2] * 2 + src[i - 1] * 2 + src[i] * 1) / 6.0
    return out


def calc_heikin_ashi_close(open_, high, low, close):
    """HA close = ohlc4"""
    return (open_ + high + low + close) / 4.0


def calc_alt_source(open_, high, low, close):
    """Source alternative: (close > open ? high : low) + SWMA lissage"""
    alt = np.where(close > open_, high, low)
    return calc_swma(alt)


def calc_obv_custom(ha_close, volume):
    """OBV avec source Heikin Ashi (comme le PineScript)"""
    n = len(ha_close); obv = np.zeros(n)
    for i in range(1, n):
        d = ha_close[i] - ha_close[i - 1]
        s = 1.0 if d > 0 else (-1.0 if d < 0 else 0.0)
        obv[i] = obv[i - 1] + s * volume[i]
    return obv


def calc_chikou_filter(altsrcres, high, low, period=25):
    """
    Chikou Trend Filter — exactement comme le PineScript :
    isup   = src > ta.highest(high, period)[period]
    isdown = src < ta.lowest(low, period)[period]
    
    ta.highest(high, 25)[25] à bar i = max(high[i-49:i-24])
    → fenêtre de 25 bars, finissant 25 bars dans le passé
    """
    n = len(high); sig = np.zeros(n)
    for i in range(period * 2, n):
        hh_back = np.max(high[i - period * 2 + 1:i - period + 1])
        ll_back = np.min(low[i - period * 2 + 1:i - period + 1])
        if altsrcres[i] > hh_back:
            sig[i] = 1.0    # Bullish
        elif altsrcres[i] < ll_back:
            sig[i] = -1.0   # Bearish
        else:
            sig[i] = 0.0    # Consolidation
    return sig


def calc_dynamic_length(conditions_bull, adapt_pct, min_len, max_len, n):
    """
    Longueur dynamique adaptative — var stateful comme PineScript :
    Bullish → len se contracte vers min (momentum fort)
    Bearish → len se dilate vers max (momentum faible)
    """
    dyn = np.zeros(n, dtype=int)
    current = (min_len + max_len) / 2.0  # Démarre au milieu (85)

    for i in range(n):
        if conditions_bull[i]:
            current = max(min_len, current * adapt_pct)
        else:
            current = min(max_len, current * (2.0 - adapt_pct))
        dyn[i] = max(int(current), 1)
    return dyn


def calc_assyin_cloud(df):
    """
    Calcul COMPLET du Kumo Cloud Assyin# Ichimoku Kinko.
    Retourne cloud_top = max(Span A, Span B) — la condition est :
    prix > cloud_top = au-dessus de Span A ET Span B
    
    Composants :
    - Tenkan (dyn 9-30) + Kijun (dyn 20-60) → Span A = avg(tk, kj)
    - Senkou (dyn 50-120) → Span B = donchian(dyn)
    - Cloud Top = max(Span A, Span B) avec displacement
    """
    o = df["open"].values; h = df["high"].values
    l = df["low"].values; c = df["close"].values
    v = df["volume"].values; n = len(c)

    # 1. Heikin Ashi close
    ha_close = calc_heikin_ashi_close(o, h, l, c)

    # 2. Source alternative + SWMA
    altsrcres = calc_alt_source(o, h, l, c)

    # 3. OBV via HA close
    obv = calc_obv_custom(ha_close, v)

    # 4. ATR fast vs slow
    atr_fast = calc_atr(h, l, c, ICH_ATR_FAST)
    atr_slow = calc_atr(h, l, c, ICH_ATR_SLOW)

    # 5. Chikou filter
    chikou_sig = calc_chikou_filter(altsrcres, h, l, ICH_CH_FILT_PER)

    # 6. Conditions bullish (mêmes pour TK, KJ, SK)
    bull = np.zeros(n, dtype=bool)
    for i in range(n):
        bull[i] = (obv[i] > ICH_VOL_PEAK and
                   atr_fast[i] > atr_slow[i] and
                   chikou_sig[i] == 1.0)

    # 7. Longueurs dynamiques pour chaque composant
    dyn_tk = calc_dynamic_length(bull, ICH_TK_PCT, ICH_TK_MIN, ICH_TK_MAX, n)
    dyn_kj = calc_dynamic_length(bull, ICH_KJ_PCT, ICH_KJ_MIN, ICH_KJ_MAX, n)
    dyn_sk = calc_dynamic_length(bull, ICH_SK_PCT, ICH_SK_MIN, ICH_SK_MAX, n)

    # 8. Tenkan-Sen = donchian(dyn_tk)
    tenkan = np.full(n, np.nan)
    for i in range(ICH_TK_MAX, n):
        dl = dyn_tk[i]; start = max(0, i - dl + 1)
        tenkan[i] = (np.max(h[start:i+1]) + np.min(l[start:i+1])) / 2.0

    # 9. Kijun-Sen = f_kjv2 (donchian + donchian/divider) / 2
    kijun = np.full(n, np.nan)
    for i in range(ICH_KJ_MAX, n):
        dl = dyn_kj[i]; start = max(0, i - dl + 1)
        kj_base = (np.max(h[start:i+1]) + np.min(l[start:i+1])) / 2.0
        # Divider = 1 → conv = base (identique)
        kj_conv = kj_base
        kijun[i] = (kj_base + kj_conv) / 2.0

    # 10. Span A = avg(Tenkan, Kijun)
    span_a_raw = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(tenkan[i]) and not np.isnan(kijun[i]):
            span_a_raw[i] = (tenkan[i] + kijun[i]) / 2.0

    # 11. Span B = donchian(dyn_sk)
    span_b_raw = np.full(n, np.nan)
    for i in range(ICH_SK_MAX, n):
        dl = dyn_sk[i]; start = max(0, i - dl + 1)
        span_b_raw[i] = (np.max(h[start:i+1]) + np.min(l[start:i+1])) / 2.0

    # 12. Displacement (offset vers le futur)
    span_a = np.full(n, np.nan)
    span_b = np.full(n, np.nan)
    for i in range(ICH_SK_OFFSET, n):
        if not np.isnan(span_a_raw[i - ICH_SK_OFFSET]):
            span_a[i] = span_a_raw[i - ICH_SK_OFFSET]
        if not np.isnan(span_b_raw[i - ICH_SK_OFFSET]):
            span_b[i] = span_b_raw[i - ICH_SK_OFFSET]

    # 13. Cloud Top = max(Span A, Span B)
    cloud_top = np.full(n, np.nan)
    for i in range(n):
        if not np.isnan(span_a[i]) and not np.isnan(span_b[i]):
            cloud_top[i] = max(span_a[i], span_b[i])
        elif not np.isnan(span_a[i]):
            cloud_top[i] = span_a[i]
        elif not np.isnan(span_b[i]):
            cloud_top[i] = span_b[i]

    return cloud_top

def calc_volume_ratio(volume, length=20):
    n = len(volume); ratio = np.zeros(n)
    for i in range(length - 1, n):
        avg = np.mean(volume[i - length + 1:i + 1])
        if avg > 0: ratio[i] = volume[i] / avg
    return ratio


# ═══════════════════════════════════════════════════════
# 📦 GOLDEN BOX MANAGER
# ═══════════════════════════════════════════════════════
GOLDEN_BOXES_FILE = "golden_boxes.json"

def load_golden_boxes():
    if os.path.exists(GOLDEN_BOXES_FILE):
        try:
            with open(GOLDEN_BOXES_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {}

def save_golden_boxes(boxes):
    with open(GOLDEN_BOXES_FILE, 'w') as f:
        json.dump(boxes, f, indent=2, default=str)

def create_golden_box(symbol, signal_time_str):
    """Crée une Golden Box : High/Low de la bougie 4H + RSI/DMI de référence"""
    df = get_klines(symbol, "4h", 100)
    if df is None:
        return None

    h = df["high"].values; l = df["low"].values; c = df["close"].values
    idx = len(c) - 2  # Dernière bougie fermée
    if idx < 20: return None

    rsi = calc_rsi(c, RSI_LENGTH)
    pdi, mdi = calc_dmi(h, l, c, DMI_LENGTH)
    atr = calc_atr(h, l, c, ATR_LENGTH)

    return {
        "symbol": symbol,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "signal_time": signal_time_str,
        "high_4h": float(h[idx]),
        "low_4h": float(l[idx]),
        "close_4h": float(c[idx]),
        "rsi_signal": float(rsi[idx]),
        "dmi_plus_signal": float(pdi[idx]),
        "dmi_minus_signal": float(mdi[idx]),
        "atr_signal": float(atr[idx]),
        "box_height": float(h[idx] - l[idx]),
        "checks_count": 0,
        "max_checks": GOLDEN_BOX_EXPIRY_4H * 4,
        "status": "WATCHING",
        "conditions_met": {},
        "entry_price": None, "tp_price": None, "sl_price": None,
    }

def cleanup_expired_boxes(boxes):
    to_remove = []
    for key, box in boxes.items():
        if box["status"] in ["EXPIRED", "ENTERED"]:
            try:
                created = datetime.fromisoformat(box["created_at"])
                if datetime.now(timezone.utc) - created > timedelta(hours=96):
                    to_remove.append(key)
            except: to_remove.append(key)
        elif box["checks_count"] >= box["max_checks"]:
            box["status"] = "EXPIRED"
            print(f"  ⏰ {box['symbol']} Golden Box expirée")
    for k in to_remove: del boxes[k]
    return boxes


# ═══════════════════════════════════════════════════════
# 🎯 ENTRY CONDITIONS CHECKER
# ═══════════════════════════════════════════════════════
def check_entry_conditions(box):
    """Vérifie toutes les conditions d'entrée pour une Golden Box"""
    symbol = box["symbol"]
    results = {
        "dmi_cross_4h": False, "break_high_4h": False, "rsi_higher_4h": False,
        "above_cloud_1h": False, "above_cloud_30m": False,
        "volume_break": False, "volume_tf": "", "retest_support": False,
    }
    current_price = None; entry_price = None

    # ── 4H : DMI cross + Break High + RSI Higher ──
    df_4h = get_klines(symbol, "4h", 100)
    if df_4h is None:
        return results, current_price, entry_price

    h4 = df_4h["high"].values; l4 = df_4h["low"].values
    c4 = df_4h["close"].values; v4 = df_4h["volume"].values
    n4 = len(c4)

    rsi_4h = calc_rsi(c4, RSI_LENGTH)
    pdi_4h, mdi_4h = calc_dmi(h4, l4, c4, DMI_LENGTH)
    vr_4h = calc_volume_ratio(v4)

    current_price = c4[n4 - 1]

    # DMI+ > DMI- (sur les 3 dernières fermées)
    for j in range(max(0, n4 - 4), n4 - 1):
        if pdi_4h[j] > mdi_4h[j]:
            results["dmi_cross_4h"] = True; break

    # Close 4H > Golden Box High (3 dernières fermées)
    for j in range(max(0, n4 - 4), n4 - 1):
        if c4[j] > box["high_4h"]:
            results["break_high_4h"] = True
            entry_price = c4[j]
            # RSI de la bougie de break > RSI signal
            if rsi_4h[j] > box["rsi_signal"]:
                results["rsi_higher_4h"] = True
            break

    # Volume 4H
    for j in range(max(0, n4 - 3), n4):
        if vr_4h[j] >= VOLUME_BREAK_MULTIPLIER:
            results["volume_break"] = True
            results["volume_tf"] = "4h"; break

    # ── 1H : Span B + Volume + Retest ──
    df_1h = get_klines(symbol, "1h", 200)
    if df_1h is not None:
        h1 = df_1h["high"].values; l1 = df_1h["low"].values
        c1 = df_1h["close"].values; v1 = df_1h["volume"].values
        n1 = len(c1)

        cloud_1h = calc_assyin_cloud(df_1h)
        cloud_top_1h = cloud_1h[n1 - 1]
        if np.isnan(cloud_top_1h) and n1 > 2: cloud_top_1h = cloud_1h[n1 - 2]
        if not np.isnan(cloud_top_1h) and c1[n1 - 1] > cloud_top_1h:
            results["above_cloud_1h"] = True

        # Volume 1H
        if not results["volume_break"]:
            vr_1h = calc_volume_ratio(v1)
            for j in range(max(0, n1 - 4), n1):
                if vr_1h[j] >= VOLUME_BREAK_MULTIPLIER:
                    results["volume_break"] = True
                    results["volume_tf"] = "1h"; break

        # Retest: prix touche le high puis rebondit
        gb_high = box["high_4h"]
        tol = box["box_height"] * 0.15
        for j in range(max(0, n1 - 8), n1):
            if abs(l1[j] - gb_high) <= tol and c1[j] > gb_high:
                results["retest_support"] = True; break

    # ── 30M : Span B + Volume ──
    df_30m = get_klines(symbol, "30m", 200)
    if df_30m is not None:
        h30 = df_30m["high"].values; l30 = df_30m["low"].values
        c30 = df_30m["close"].values; v30 = df_30m["volume"].values
        n30 = len(c30)

        cloud_30m = calc_assyin_cloud(df_30m)
        cloud_top_30m = cloud_30m[n30 - 1]
        if np.isnan(cloud_top_30m) and n30 > 2: cloud_top_30m = cloud_30m[n30 - 2]
        if not np.isnan(cloud_top_30m) and c30[n30 - 1] > cloud_top_30m:
            results["above_cloud_30m"] = True

        if not results["volume_break"]:
            vr_30m = calc_volume_ratio(v30)
            for j in range(max(0, n30 - 8), n30):
                if vr_30m[j] >= VOLUME_BREAK_MULTIPLIER:
                    results["volume_break"] = True
                    results["volume_tf"] = "30m"; break

    # ── 15M : Volume only ──
    if not results["volume_break"]:
        df_15m = get_klines(symbol, "15m", 100)
        if df_15m is not None:
            v15 = df_15m["volume"].values
            vr_15m = calc_volume_ratio(v15)
            n15 = len(v15)
            for j in range(max(0, n15 - 16), n15):
                if vr_15m[j] >= VOLUME_BREAK_MULTIPLIER:
                    results["volume_break"] = True
                    results["volume_tf"] = "15m"; break

    return results, current_price, entry_price


def is_entry_ready(conds):
    return all([conds["dmi_cross_4h"], conds["break_high_4h"],
                conds["rsi_higher_4h"], conds["above_cloud_1h"],
                conds["above_cloud_30m"]])


# ═══════════════════════════════════════════════════════
# 📱 TELEGRAM
# ═══════════════════════════════════════════════════════
def send_telegram(text):
    try:
        _http.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                   data={"chat_id": TELEGRAM_CHAT_ID, "text": text,
                         "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print(f"  ⚠️ Telegram: {e}")

def send_entry_notification(box, conditions):
    symbol = box["symbol"]; ep = box["entry_price"]
    tp = box["tp_price"]; sl = box["sl_price"]
    rr = abs(tp - ep) / abs(ep - sl) if abs(ep - sl) > 0 else 0
    def ic(v): return "✅" if v else "❌"

    msg = (
        f"🎯🎯🎯 <b>ENTRY READY — {symbol}</b> 🎯🎯🎯\n"
        f"{'─' * 30}\n\n"
        f"💰 Entry: <b>{ep:.8g}</b>\n"
        f"🎯 TP: <b>{tp:.8g}</b> (+{abs(tp-ep)/ep*100:.2f}%)\n"
        f"🛑 SL: <b>{sl:.8g}</b> (-{abs(ep-sl)/ep*100:.2f}%)\n"
        f"📊 R:R = <b>1:{rr:.1f}</b>\n\n"
        f"<b>Conditions:</b>\n"
        f"{ic(conditions['dmi_cross_4h'])} DMI+ > DMI- (4H)\n"
        f"{ic(conditions['break_high_4h'])} Break Golden Box High\n"
        f"{ic(conditions['rsi_higher_4h'])} RSI Higher High (4H)\n"
        f"{ic(conditions['above_cloud_1h'])} Prix > Cloud Top (1H)\n"
        f"{ic(conditions['above_cloud_30m'])} Prix > Cloud Top (30M)\n"
        f"{'🟢' if conditions['volume_break'] else '⚪'} Volume Break ({conditions.get('volume_tf', '-')})\n"
        f"{'🟢' if conditions['retest_support'] else '⚪'} Retest Support\n\n"
        f"📦 Golden Box: {box['low_4h']:.8g} — {box['high_4h']:.8g}\n"
        f"📅 Signal: {box['signal_time']}"
    )
    send_telegram(msg)

def send_watching_update(boxes):
    watching = {k: v for k, v in boxes.items() if v["status"] == "WATCHING"}
    if not watching: return
    msg = f"👁️ <b>Golden Boxes: {len(watching)} actives</b>\n{'─' * 28}\n\n"
    for key, box in list(watching.items())[:20]:
        s = box["symbol"].replace("USDT", "")
        left = box["max_checks"] - box["checks_count"]
        conds = box.get("conditions_met", {})
        met = sum(1 for k in ["dmi_cross_4h", "break_high_4h", "rsi_higher_4h",
                               "above_cloud_1h", "above_cloud_30m"] if conds.get(k))
        msg += f"📦 <b>{s}</b> {met}/5 | ⏳{left} left\n"
    send_telegram(msg)


# ═══════════════════════════════════════════════════════
# 📊 GOOGLE SHEETS — Feuilles journalières
# ═══════════════════════════════════════════════════════
_gs_client = None
_gs_spreadsheet = None

def init_google_sheets():
    global _gs_client, _gs_spreadsheet
    if not GOOGLE_SHEETS_ENABLED or not GSPREAD_OK: return False
    if not os.path.exists(GOOGLE_CREDS_FILE):
        print(f"  ⚠️ {GOOGLE_CREDS_FILE} introuvable"); return False
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets",
                  "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_file(GOOGLE_CREDS_FILE, scopes=scopes)
        _gs_client = gspread.authorize(creds)
        _gs_spreadsheet = _gs_client.open(GOOGLE_SHEET_NAME)
        print(f"  ✅ Google Sheet: {GOOGLE_SHEET_NAME}")
        return True
    except Exception as e:
        print(f"  ❌ Google Sheets: {e}"); return False

def get_or_create_daily_sheet():
    """Obtient/crée la feuille 'Entry - DD/MM/YYYY'"""
    if _gs_spreadsheet is None: return None
    date_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    tab_name = f"Entry - {date_str}"
    try:
        try:
            return _gs_spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound: pass

        ws = _gs_spreadsheet.add_worksheet(title=tab_name, rows=200, cols=18)
        headers = [
            "Heure", "Paire", "Entry", "TP", "SL", "R:R",
            "DMI+>-", "Break", "RSI↑", "Cloud 1H", "Cloud 30M",
            "Volume", "Retest", "Box High", "Box Low", "RSI Sig", "Status", "Signal"
        ]
        ws.update(values=[headers], range_name='A1:R1')

        sid = ws.id
        body = {"requests": [
            {"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                           "startColumnIndex": 0, "endColumnIndex": 18},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.05, "green": 0.05, "blue": 0.12},
                    "textFormat": {"bold": True, "fontSize": 10,
                                   "foregroundColor": {"red": 1, "green": 0.85, "blue": 0.2}},
                    "horizontalAlignment": "CENTER",
                    "borders": {"bottom": {"style": "SOLID_THICK",
                                           "color": {"red": 1, "green": 0.6, "blue": 0}}}
                }}, "fields": "userEnteredFormat"
            }},
            {"updateSheetProperties": {
                "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 1}},
                "fields": "gridProperties.frozenRowCount"
            }},
            {"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 70}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 110}, "fields": "pixelSize"}},
            {"updateDimensionProperties": {
                "range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": 2, "endIndex": 6},
                "properties": {"pixelSize": 105}, "fields": "pixelSize"}},
        ]}
        _gs_spreadsheet.batch_update(body)
        print(f"  ✅ Feuille créée: {tab_name}")
        return ws
    except Exception as e:
        print(f"  ⚠️ Sheet tab: {e}"); return None

def log_entry_to_sheet(box, conditions):
    ws = get_or_create_daily_sheet()
    if ws is None: return
    try:
        ep = box["entry_price"]; tp = box["tp_price"]; sl = box["sl_price"]
        rr = abs(tp - ep) / abs(ep - sl) if abs(ep - sl) > 0 else 0
        def yn(v): return "✓" if v else "✗"

        row = [
            datetime.now(timezone.utc).strftime("%H:%M"),
            box["symbol"].replace("USDT", ""),
            round(ep, 8), round(tp, 8), round(sl, 8), f"1:{rr:.1f}",
            yn(conditions["dmi_cross_4h"]), yn(conditions["break_high_4h"]),
            yn(conditions["rsi_higher_4h"]), yn(conditions["above_cloud_1h"]),
            yn(conditions["above_cloud_30m"]),
            f"{yn(conditions['volume_break'])} {conditions.get('volume_tf', '')}",
            yn(conditions["retest_support"]),
            round(box["high_4h"], 8), round(box["low_4h"], 8),
            round(box["rsi_signal"], 1), "🎯 ENTRY", box["signal_time"]
        ]

        next_row = len(ws.get_all_values()) + 1
        ws.update(values=[row], range_name=f'A{next_row}:R{next_row}')

        sid = ws.id; ri = next_row - 1
        fmt = [
            # Fond vert foncé
            {"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": ri, "endRowIndex": ri + 1,
                          "startColumnIndex": 0, "endColumnIndex": 18},
                "cell": {"userEnteredFormat": {
                    "backgroundColor": {"red": 0.05, "green": 0.22, "blue": 0.05},
                    "textFormat": {"foregroundColor": {"red": 0.7, "green": 1, "blue": 0.7},
                                   "fontSize": 10},
                    "horizontalAlignment": "CENTER"
                }}, "fields": "userEnteredFormat"
            }},
            # Paire bold blanc
            {"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": ri, "endRowIndex": ri + 1,
                          "startColumnIndex": 1, "endColumnIndex": 2},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True, "fontSize": 12,
                                   "foregroundColor": {"red": 1, "green": 1, "blue": 1}}
                }}, "fields": "userEnteredFormat.textFormat"
            }},
            # Entry gold
            {"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": ri, "endRowIndex": ri + 1,
                          "startColumnIndex": 2, "endColumnIndex": 3},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True, "fontSize": 11,
                                   "foregroundColor": {"red": 1, "green": 0.85, "blue": 0.2}}
                }}, "fields": "userEnteredFormat.textFormat"
            }},
            # Bordure or
            {"updateBorders": {
                "range": {"sheetId": sid, "startRowIndex": ri, "endRowIndex": ri + 1,
                          "startColumnIndex": 0, "endColumnIndex": 18},
                "left": {"style": "SOLID_THICK", "color": {"red": 1, "green": 0.8, "blue": 0}},
                "right": {"style": "SOLID_THICK", "color": {"red": 1, "green": 0.8, "blue": 0}},
            }},
        ]
        # Conditions vert/rouge
        for ci in range(6, 13):
            is_ok = "✓" in str(row[ci])
            fg = ({"red": 0.2, "green": 1, "blue": 0.2} if is_ok
                  else {"red": 1, "green": 0.3, "blue": 0.3})
            fmt.append({"repeatCell": {
                "range": {"sheetId": sid, "startRowIndex": ri, "endRowIndex": ri + 1,
                          "startColumnIndex": ci, "endColumnIndex": ci + 1},
                "cell": {"userEnteredFormat": {
                    "textFormat": {"bold": True, "foregroundColor": fg}
                }}, "fields": "userEnteredFormat.textFormat"
            }})

        _gs_spreadsheet.batch_update({"requests": fmt})
        print(f"  📊 Sheet: {box['symbol']} logué")
    except Exception as e:
        print(f"  ⚠️ Sheet log: {e}")


# ═══════════════════════════════════════════════════════
# 🔄 IMPORT ALERTES
# ═══════════════════════════════════════════════════════
def import_new_alerts_from_sheet(boxes):
    """Lit les nouvelles alertes depuis la feuille 'Alerts' du Google Sheet"""
    if _gs_spreadsheet is None: return boxes
    try:
        alerts_ws = _gs_spreadsheet.get_worksheet(0)
        all_data = alerts_ws.get_all_values()
        if len(all_data) <= 1: return boxes

        added = 0
        for row in all_data[-50:]:
            if len(row) < 5: continue
            date_str = row[0]; symbol_short = row[1]
            symbol = symbol_short + "USDT" if not symbol_short.endswith("USDT") else symbol_short
            box_key = f"{symbol}_{date_str}"
            if box_key in boxes: continue

            try:
                alert_time = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                if (datetime.now() - alert_time).total_seconds() / 3600 > 72: continue
            except: continue

            print(f"  📦 Nouvelle Golden Box: {symbol} ({date_str})")
            box = create_golden_box(symbol, date_str)
            if box:
                boxes[box_key] = box; added += 1
                time.sleep(0.15)

        if added: print(f"  ✅ {added} nouvelles Golden Boxes créées")
    except Exception as e:
        print(f"  ⚠️ Import: {e}")
    return boxes


# ═══════════════════════════════════════════════════════
# 🔄 MAIN LOOP
# ═══════════════════════════════════════════════════════
def run_check(boxes):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    watching = {k: v for k, v in boxes.items() if v["status"] == "WATCHING"}

    print(f"\n{'='*60}")
    print(f"🎯 Entry Check — {now}")
    print(f"📦 {len(watching)} Golden Boxes actives")
    print(f"{'='*60}")

    if not watching:
        print("  ℹ️ Aucune Golden Box à surveiller")
        return boxes

    entries_found = 0

    for key, box in list(watching.items()):
        symbol = box["symbol"]; box["checks_count"] += 1
        print(f"\n  📦 {symbol} (check {box['checks_count']}/{box['max_checks']})")

        conditions, current_price, entry_price = check_entry_conditions(box)
        box["conditions_met"] = conditions

        met = sum(1 for k in ["dmi_cross_4h", "break_high_4h", "rsi_higher_4h",
                               "above_cloud_1h", "above_cloud_30m"] if conditions[k])
        def ic(v): return "✅" if v else "❌"
        print(f"     {ic(conditions['dmi_cross_4h'])} DMI  {ic(conditions['break_high_4h'])} Break  "
              f"{ic(conditions['rsi_higher_4h'])} RSI  {ic(conditions['above_cloud_1h'])} CL1H  "
              f"{ic(conditions['above_cloud_30m'])} CL30M  "
              f"{'🟢' if conditions['volume_break'] else '⚪'} Vol  → {met}/5")

        if is_entry_ready(conditions):
            box["status"] = "ENTRY_READY"
            if entry_price is None: entry_price = current_price
            bh = box["box_height"]
            box["entry_price"] = entry_price
            box["tp_price"] = entry_price + bh * TP_MULTIPLIER
            box["sl_price"] = box["low_4h"] - box["atr_signal"] * SL_ATR_BUFFER

            print(f"\n  🎯🎯🎯 ENTRY READY — {symbol}")
            print(f"     Entry: {entry_price:.8g} | TP: {box['tp_price']:.8g} | SL: {box['sl_price']:.8g}")

            send_entry_notification(box, conditions)
            log_entry_to_sheet(box, conditions)
            entries_found += 1

    boxes = cleanup_expired_boxes(boxes)
    save_golden_boxes(boxes)
    if entries_found: print(f"\n  🎯 {entries_found} ENTRY(s) !")
    return boxes


def main():
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║     🎯 MEGA BUY Entry Agent v1                   ║
    ║     Golden Box + Span B + DMI Cross              ║
    ║     ASSYIN-2026                                  ║
    ╚═══════════════════════════════════════════════════╝
    """)
    print(f"⚙️  Check: {CHECK_INTERVAL_MIN}min | Expiry: {GOLDEN_BOX_EXPIRY_4H}×4H")
    print(f"⚙️  TP: {TP_MULTIPLIER}× box | SL: Low - {SL_ATR_BUFFER}× ATR")
    print(f"⚙️  Volume: {VOLUME_BREAK_MULTIPLIER}× avg20 | Ichimoku: Assyin# Dynamic {ICH_SK_MIN}-{ICH_SK_MAX}\n")

    send_telegram(
        "🎯 <b>Entry Agent v1 démarré !</b>\n"
        f"📦 Expiry: {GOLDEN_BOX_EXPIRY_4H}×4H | Check: {CHECK_INTERVAL_MIN}min\n"
        "📊 DMI Cross + Break + RSI + Cloud 1H/30M"
    )
    print("✅ Telegram connecté")

    gs_ok = init_google_sheets()
    if gs_ok: print("✅ Google Sheets connecté")

    boxes = load_golden_boxes()
    w = sum(1 for b in boxes.values() if b["status"] == "WATCHING")
    print(f"📦 {w} Golden Boxes chargées\n")

    if gs_ok: boxes = import_new_alerts_from_sheet(boxes)
    save_golden_boxes(boxes)
    boxes = run_check(boxes)

    cycle = 0
    while True:
        try:
            now = datetime.now(timezone.utc)
            m = now.minute; s = now.second
            ns = ((m // CHECK_INTERVAL_MIN) + 1) * CHECK_INTERVAL_MIN
            wait = max(((ns if ns < 60 else 60) - m) * 60 - s + 5, 30)
            nt = now + timedelta(seconds=wait)
            print(f"\n⏳ Prochain: {nt.strftime('%H:%M')} UTC ({wait}s)")

            time.sleep(wait)
            cycle += 1

            if gs_ok: boxes = import_new_alerts_from_sheet(boxes)
            boxes = run_check(boxes)

            if cycle % 16 == 0: send_watching_update(boxes)

        except KeyboardInterrupt:
            print("\n🛑 Arrêt"); save_golden_boxes(boxes)
            send_telegram("🛑 Entry Agent arrêté"); break
        except Exception as e:
            print(f"❌ {e}"); time.sleep(60)


if __name__ == "__main__":
    main()
