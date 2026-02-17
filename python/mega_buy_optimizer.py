"""
🔬 MEGA BUY Optimizer — Trouve la config la plus profitable
Teste automatiquement des combinaisons de TP/SL/Score/MaxHold
Envoie le meilleur résultat sur Telegram

Auteur: ASSYIN-2026
"""

import requests
import numpy as np
import pandas as pd
import time
import json
import itertools
from collections import Counter
from datetime import datetime, timezone

# ═══════════════════════════════════════════════════════
# ⚙️ CONFIG
# ═══════════════════════════════════════════════════════
TELEGRAM_TOKEN = "COLLE_TON_TOKEN_ICI"
TELEGRAM_CHAT_ID = "COLLE_TON_CHAT_ID_ICI"

# ═══════════════════════════════════════════════════════
# 🎯 PAIRES À TESTER — Altcoins volatiles
# ═══════════════════════════════════════════════════════
SYMBOLS = [
    "DOGEUSDT",
    "SOLUSDT",
    "PEPEUSDT",
    "SUIUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "WIFUSDT",
    "BONKUSDT",
    "FETUSDT",
    "RENDERUSDT",
    "INJUSDT",
    "NEARUSDT",
    "BTCUSDT",
]

DATE_START = "2025-01-01"
DATE_END   = "2026-02-15"
TIMEFRAME  = "15m"

INITIAL_CAPITAL = 1000.0
POSITION_SIZE_PCT = 50.0   # 50% position — altcoins bougent plus

# ═══════════════════════════════════════════════════════
# 🔬 PARAMÈTRES À OPTIMISER — Plages élargies pour altcoins
# ═══════════════════════════════════════════════════════
OPTIMIZE = {
    "take_profit":  [2.0, 3.0, 4.0, 5.0, 7.0, 10.0],  # Altcoins bougent plus
    "stop_loss":    [1.0, 1.5, 2.0, 3.0],                # SL
    "max_hold":     [12, 24, 36, 48, 96],                 # Jusqu'à 24h
    "min_score":    [4, 5, 6, 7],                          # Score minimum
    "trailing_stop": [True, False],                        # Trailing
    "trailing_pct":  [1.0, 2.0, 3.0],                     # Trail distance
}

# ═══════════════════════════════════════════════════════
# ⚙️ PARAMÈTRES INDICATEURS (identiques au bot)
# ═══════════════════════════════════════════════════════
RSI_LENGTH = 14
RSI_MIN_MOVE_BUY = 12.0
DMI_LENGTH = 14
DMI_ADX_SMOOTH = 14
DMI_MIN_MOVE_PLUS = 10.0
AST_FACTOR = 3.0
AST_PERIOD = 10
ST_FACTOR = 3.0
ST_PERIOD = 10
PP_PIVOT_PERIOD = 2
PP_ATR_FACTOR = 3.0
PP_ATR_PERIOD = 10
AV_ATR_LENGTH = 14
AV_ATR_SMOOTH = 10
AV_ATR_THRESHOLD = 1.2
AV_VOL_LENGTH = 20
AV_VOL_THRESHOLD = 1.5
AV_MIN_MOVE = 250.0
LB_SPIKE_THRESH = 6.0
COMBO_WINDOW = 3
COMBO_THRESHOLD_PCT = 50

# ═══════════════════════════════════════════════════════
# 📡 BINANCE API
# ═══════════════════════════════════════════════════════
BINANCE_BASE = "https://api.binance.com"
TF_TO_MS = {
    "1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000,
    "30m": 1800000, "1h": 3600000, "2h": 7200000, "4h": 14400000,
    "1d": 86400000
}

def date_to_ms(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def get_full_history(symbol, interval, start_date, end_date):
    start_ms = date_to_ms(start_date)
    end_ms = date_to_ms(end_date)
    warmup_ms = TF_TO_MS.get(interval, 900000) * 200
    fetch_start = start_ms - warmup_ms
    all_klines = []
    current_start = fetch_start
    print(f"📥 Téléchargement {symbol} {interval}...")
    while current_start < end_ms:
        url = f"{BINANCE_BASE}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "startTime": current_start, "endTime": end_ms, "limit": 1000}
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0: break
        all_klines.extend(data)
        current_start = data[-1][6] + 1
        print(f"   📊 {len(all_klines)} bougies...", end="\r")
        time.sleep(0.15)
    print(f"   ✅ {len(all_klines)} bougies chargées          ")
    if not all_klines: return None
    df = pd.DataFrame(all_klines, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"
    ])
    for col in ["open","high","low","close","volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df = df.drop_duplicates(subset="open_time").reset_index(drop=True)
    return df

# ═══════════════════════════════════════════════════════
# 📊 INDICATEURS (copiés du bot)
# ═══════════════════════════════════════════════════════
def rma(series, length):
    alpha = 1.0 / length
    result = np.zeros(len(series)); result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result

def ema(series, length):
    alpha = 2.0 / (length + 1)
    result = np.zeros(len(series)); result[0] = series[0]
    for i in range(1, len(series)):
        result[i] = alpha * series[i] + (1 - alpha) * result[i - 1]
    return result

def sma(series, length):
    result = np.full(len(series), np.nan)
    for i in range(length - 1, len(series)):
        result[i] = np.mean(series[i - length + 1:i + 1])
    return result

def true_range(high, low, close):
    tr = np.zeros(len(high)); tr[0] = high[0] - low[0]
    for i in range(1, len(high)):
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    return tr

def calc_rsi(close, length=14):
    delta = np.diff(close, prepend=close[0])
    gain = np.maximum(delta, 0); loss = -np.minimum(delta, 0)
    avg_gain = rma(gain, length); avg_loss = rma(loss, length)
    with np.errstate(divide='ignore', invalid='ignore'):
        rs = np.where(avg_loss == 0, 100, avg_gain / avg_loss)
        return np.where(avg_loss == 0, 100, 100 - (100 / (1 + rs)))

def calc_dmi(high, low, close, length=14, adx_smooth=14):
    n = len(high); plus_dm = np.zeros(n); minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i]-high[i-1]; down = low[i-1]-low[i]
        plus_dm[i] = up if (up > down and up > 0) else 0
        minus_dm[i] = down if (down > up and down > 0) else 0
    tr = true_range(high, low, close); atr_vals = rma(tr, length)
    atr_safe = np.where(atr_vals == 0, 1, atr_vals)
    plus_di = 100 * rma(plus_dm, length) / atr_safe
    minus_di = 100 * rma(minus_dm, length) / atr_safe
    di_sum = plus_di + minus_di; di_safe = np.where(di_sum == 0, 1, di_sum)
    dx = 100 * np.abs(plus_di - minus_di) / di_safe
    return plus_di, minus_di, rma(dx, adx_smooth)

def calc_supertrend_classic(high, low, close, factor=3.0, period=10):
    n = len(high); tr = true_range(high, low, close); atr_vals = rma(tr, period)
    hl2 = (high+low)/2; upper = hl2+factor*atr_vals; lower = hl2-factor*atr_vals
    direction = np.ones(n); supertrend = np.zeros(n)
    fu = np.copy(upper); fl = np.copy(lower)
    for i in range(1, n):
        if close[i-1] > fu[i-1]: direction[i] = -1
        elif close[i-1] < fl[i-1]: direction[i] = 1
        else: direction[i] = direction[i-1]
        if direction[i] == -1:
            fl[i] = max(lower[i], fl[i-1]) if close[i-1] > fl[i-1] else lower[i]
            supertrend[i] = fl[i]
        else:
            fu[i] = min(upper[i], fu[i-1]) if close[i-1] < fu[i-1] else upper[i]
            supertrend[i] = fu[i]
    return supertrend, direction

def calc_assyin_supertrend(high, low, close, factor=3.0, period=10):
    n = len(high); tr = true_range(high, low, close); atr_vals = rma(tr, period)
    hl2 = (high+low)/2
    ur = hl2+factor*atr_vals; lr = hl2-factor*atr_vals
    ub = np.copy(ur); lb = np.copy(lr); d = np.ones(n)
    for i in range(1, n):
        lb[i] = max(lr[i], lb[i-1]) if close[i-1] > lb[i-1] else lr[i]
        ub[i] = min(ur[i], ub[i-1]) if close[i-1] < ub[i-1] else ur[i]
        if d[i-1] == -1: d[i] = 1 if close[i] < lb[i] else -1
        else: d[i] = -1 if close[i] > ub[i] else 1
    return np.where(d == -1, lb, ub), d

def calc_pp_supertrend(high, low, close, prd=2, factor=3.0, atr_period=10):
    n = len(high); center = np.full(n, np.nan); trend = np.ones(n, dtype=int)
    t_up = np.zeros(n); t_down = np.zeros(n)
    tr = true_range(high, low, close); atr_vals = rma(tr, atr_period)
    last_pp = np.nan
    for i in range(prd, n - prd):
        is_ph = all(i+j < n and i-j >= 0 and high[i] > high[i-j] and high[i] > high[i+j] for j in range(1, prd+1))
        is_pl = all(i+j < n and i-j >= 0 and low[i] < low[i-j] and low[i] < low[i+j] for j in range(1, prd+1))
        if is_ph: last_pp = high[i]
        if is_pl: last_pp = low[i]
        if not np.isnan(last_pp):
            center[i] = (center[i-1]*2+last_pp)/3 if not np.isnan(center[i-1]) else last_pp
    for i in range(1, n):
        if np.isnan(center[i]) and not np.isnan(center[i-1]): center[i] = center[i-1]
    for i in range(1, n):
        if np.isnan(center[i]): continue
        up_val = center[i]-factor*atr_vals[i]; dn_val = center[i]+factor*atr_vals[i]
        t_up[i] = max(up_val, t_up[i-1]) if close[i-1] > t_up[i-1] else up_val
        t_down[i] = min(dn_val, t_down[i-1]) if close[i-1] < t_down[i-1] else dn_val
        if close[i] > t_down[i-1]: trend[i] = 1
        elif close[i] < t_up[i-1]: trend[i] = -1
        else: trend[i] = trend[i-1]
    return trend

def calc_atr_vol_regime(high, low, close, volume):
    n = len(high); tr = true_range(high, low, close)
    atr_raw = rma(tr, AV_ATR_LENGTH); atr_sm = ema(atr_raw, AV_ATR_SMOOTH)
    atr_slope = np.zeros(n)
    for i in range(1, n):
        if atr_sm[i-1] != 0: atr_slope[i] = (atr_sm[i]-atr_sm[i-1])/atr_sm[i-1]*100
    atr_reg = np.zeros(n, dtype=int)
    for i in range(n):
        if atr_slope[i] > AV_ATR_THRESHOLD: atr_reg[i] = 1
        elif atr_slope[i] < -AV_ATR_THRESHOLD: atr_reg[i] = -1
    vol_ma = sma(volume, AV_VOL_LENGTH)
    vol_ratio = np.where(np.isnan(vol_ma)|(vol_ma==0), 0, volume/np.where(np.isnan(vol_ma),1,vol_ma))
    vol_change = np.zeros(n)
    for i in range(1, n):
        vm = vol_ma[i] if not np.isnan(vol_ma[i]) and vol_ma[i] != 0 else 1
        vol_change[i] = (volume[i]-volume[i-1])/vm*100
    vol_reg = np.zeros(n, dtype=int)
    for i in range(n):
        if vol_ratio[i] > AV_VOL_THRESHOLD: vol_reg[i] = 1
        elif vol_ratio[i] < 0.8: vol_reg[i] = -1
    regime = np.zeros(n, dtype=int)
    for i in range(n):
        if atr_reg[i]==1 and vol_reg[i]==1: regime[i] = 1
        elif atr_reg[i]==-1 and vol_reg[i]==-1: regime[i] = -1
    return regime, np.abs(vol_change), vol_change

def calc_lazybar(high, low, close):
    n = len(high); ht = np.zeros(n)
    for i in range(4, n):
        m = (high[i]+low[i]+high[i-1]+low[i-1]+high[i-2]+low[i-2]+high[i-3]+low[i-3]+high[i-4]+low[i-4])/10
        s = ((high[i]-low[i])+(high[i-1]-low[i-1])+(high[i-2]-low[i-2])+(high[i-3]-low[i-3])+(high[i-4]-low[i-4]))/5*0.2
        if s != 0: ht[i] = (close[i]-m)/s
    return ht

# ═══════════════════════════════════════════════════════
# 🎯 COMPUTE ALL SIGNALS (une seule fois)
# ═══════════════════════════════════════════════════════
def compute_all_signals(df):
    """Retourne la liste de TOUS les signaux avec leur score (sans filtre score min)"""
    high = df["high"].values; low = df["low"].values
    close = df["close"].values; volume = df["volume"].values
    n = len(close)
    
    print("🔧 Calcul des indicateurs...")
    rsi_vals = calc_rsi(close, RSI_LENGTH)
    plus_di, _, _ = calc_dmi(high, low, close, DMI_LENGTH, DMI_ADX_SMOOTH)
    _, st_dir = calc_supertrend_classic(high, low, close, ST_FACTOR, ST_PERIOD)
    _, ast_dir = calc_assyin_supertrend(high, low, close, AST_FACTOR, AST_PERIOD)
    pp_trend = calc_pp_supertrend(high, low, close, PP_PIVOT_PERIOD, PP_ATR_FACTOR, PP_ATR_PERIOD)
    regime, vol_move, vol_change = calc_atr_vol_regime(high, low, close, volume)
    ht = calc_lazybar(high, low, close)
    
    w = COMBO_WINDOW; window = w * 2
    signals = []
    last_bar = -999
    
    for idx in range(window + 2, n):
        # 3 obligatoires
        rsi_ok = any(rsi_vals[i]-rsi_vals[i-1] >= RSI_MIN_MOVE_BUY for i in range(max(1,idx-window), idx+1))
        if not rsi_ok: continue
        dmi_ok = any(plus_di[i]-plus_di[i-1] > 0 and abs(plus_di[i]-plus_di[i-1]) >= DMI_MIN_MOVE_PLUS for i in range(max(1,idx-window), idx+1))
        if not dmi_ok: continue
        ast_ok = any(ast_dir[i]==-1 and ast_dir[i-1]!=-1 for i in range(max(1,idx-window), idx+1))
        if not ast_ok: continue
        
        # Optionnelles
        green_ok = regime[idx] != -1
        lazy_ok = any(abs(ht[i]) >= 9.6 or abs(ht[i]-ht[i-1]) >= LB_SPIKE_THRESH for i in range(max(1,idx-window), idx+1))
        vol_ok = vol_move[idx] >= AV_MIN_MOVE and vol_change[idx] > 0
        st_ok = any(st_dir[i]==-1 and st_dir[i-1]==1 for i in range(max(1,idx-window), idx+1))
        pp_ok = any(pp_trend[i]==1 and pp_trend[i-1]==-1 for i in range(max(1,idx-window), idx+1))
        
        score = 3 + sum([green_ok, lazy_ok, vol_ok, st_ok, pp_ok])
        
        # Cooldown (min distance between signals)
        if idx - last_bar <= window: continue
        last_bar = idx
        
        signals.append({
            "bar_index": idx,
            "time": df.iloc[idx]["open_time"],
            "entry_price": close[idx],
            "score": score,
        })
    
    print(f"   ✅ {len(signals)} signaux bruts détectés")
    return signals

# ═══════════════════════════════════════════════════════
# 💰 SIMULATION AVEC TRAILING STOP
# ═══════════════════════════════════════════════════════
def simulate(df, signals, tp_pct, sl_pct, max_hold, min_score, use_trailing, trail_pct):
    """Simule les trades avec des paramètres donnés"""
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    n = len(close)
    
    trades = []
    
    for sig in signals:
        if sig["score"] < min_score:
            continue
        
        entry_idx = sig["bar_index"]
        entry_price = sig["entry_price"]
        
        tp_price = entry_price * (1 + tp_pct / 100)
        sl_price = entry_price * (1 - sl_pct / 100)
        
        # Trailing stop state
        highest_price = entry_price
        trail_sl = sl_price
        
        exit_idx = None
        exit_price = None
        exit_reason = None
        
        end_idx = min(entry_idx + max_hold + 1, n) if max_hold > 0 else n
        
        for j in range(entry_idx + 1, end_idx):
            # Update trailing stop
            if use_trailing and high[j] > highest_price:
                highest_price = high[j]
                new_trail = highest_price * (1 - trail_pct / 100)
                trail_sl = max(trail_sl, new_trail)
            
            active_sl = trail_sl if use_trailing else sl_price
            
            # Check SL
            if low[j] <= active_sl:
                exit_idx = j
                exit_price = active_sl
                exit_reason = "TRAILING SL" if use_trailing and trail_sl > sl_price else "STOP LOSS"
                break
            
            # Check TP
            if high[j] >= tp_price:
                exit_idx = j
                exit_price = tp_price
                exit_reason = "TAKE PROFIT"
                break
        
        if exit_idx is None:
            if max_hold > 0 and entry_idx + max_hold < n:
                exit_idx = entry_idx + max_hold
                exit_price = close[exit_idx]
                exit_reason = "MAX HOLD"
            else:
                continue
        
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        trades.append({
            "pnl_pct": pnl_pct,
            "exit_reason": exit_reason,
            "score": sig["score"],
            "hold_bars": exit_idx - entry_idx
        })
    
    return trades

def calc_stats(trades):
    """Calcule les stats d'une liste de trades"""
    if not trades:
        return {"total": 0, "win_rate": 0, "pnl": 0, "pf": 0, "dd": 0, "capital": INITIAL_CAPITAL}
    
    total = len(trades)
    wins = [t for t in trades if t["pnl_pct"] > 0]
    wr = len(wins) / total * 100
    
    pnls = [t["pnl_pct"] for t in trades]
    total_pnl = sum(pnls)
    
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 99.0
    
    # Capital sim
    capital = INITIAL_CAPITAL
    max_cap = capital; max_dd = 0
    for t in trades:
        pos = capital * POSITION_SIZE_PCT / 100
        capital += pos * t["pnl_pct"] / 100
        max_cap = max(max_cap, capital)
        dd = (max_cap - capital) / max_cap * 100
        max_dd = max(max_dd, dd)
    
    tp_count = len([t for t in trades if t["exit_reason"] == "TAKE PROFIT"])
    sl_count = len([t for t in trades if "STOP" in t["exit_reason"] or "SL" in t["exit_reason"]])
    trail_count = len([t for t in trades if t["exit_reason"] == "TRAILING SL"])
    
    return {
        "total": total, "win_rate": wr, "pnl": total_pnl,
        "pf": pf, "dd": max_dd, "capital": capital,
        "tp_hits": tp_count, "sl_hits": sl_count, "trail_hits": trail_count,
        "avg_pnl": np.mean(pnls), "avg_hold": np.mean([t["hold_bars"] for t in trades])
    }

# ═══════════════════════════════════════════════════════
# 📱 TELEGRAM
# ═══════════════════════════════════════════════════════
def send_telegram(message):
    if TELEGRAM_TOKEN == "COLLE_TON_TOKEN_ICI":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    chunks = []
    while len(message) > 4000:
        cut = message[:4000].rfind("\n")
        if cut == -1: cut = 4000
        chunks.append(message[:cut]); message = message[cut:]
    chunks.append(message)
    for chunk in chunks:
        try:
            requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": chunk, "parse_mode": "HTML"}, timeout=10)
            time.sleep(0.5)
        except: pass

# ═══════════════════════════════════════════════════════
# 🔬 OPTIMISATION PAR PAIRE
# ═══════════════════════════════════════════════════════
def optimize_single(symbol, df):
    """Optimise une seule paire, retourne (best_config, top5, all_results)"""
    signals = compute_all_signals(df)
    if not signals:
        print(f"   ❌ {symbol}: aucun signal"); return None
    
    tp_vals = OPTIMIZE["take_profit"]
    sl_vals = OPTIMIZE["stop_loss"]
    mh_vals = OPTIMIZE["max_hold"]
    ms_vals = OPTIMIZE["min_score"]
    tr_vals = OPTIMIZE["trailing_stop"]
    trp_vals = OPTIMIZE["trailing_pct"]
    
    combos = []
    for tp, sl, mh, ms, tr, trp in itertools.product(tp_vals, sl_vals, mh_vals, ms_vals, tr_vals, trp_vals):
        if not tr and trp != trp_vals[0]: continue
        if tp <= sl: continue
        combos.append((tp, sl, mh, ms, tr, trp))
    
    results = []
    for tp, sl, mh, ms, tr, trp in combos:
        trades = simulate(df, signals, tp, sl, mh, ms, tr, trp)
        stats = calc_stats(trades)
        if stats["total"] >= 5:
            results.append({
                "symbol": symbol, "tp": tp, "sl": sl, "max_hold": mh,
                "min_score": ms, "trailing": tr, "trail_pct": trp,
                **stats
            })
    
    if not results:
        print(f"   ❌ {symbol}: aucune combinaison valide"); return None
    
    for r in results:
        r["score_composite"] = r["pf"] * (r["win_rate"] / 100) * (1 if r["pnl"] > 0 else 0.3) * (1 - r["dd"] / 100)
    results.sort(key=lambda x: x["score_composite"], reverse=True)
    
    best = results[0]
    trail_str = f"T{best['trail_pct']}%" if best["trailing"] else "OFF"
    icon = "🟢" if best["pnl"] > 20 else "🟡" if best["pnl"] > 0 else "🔴"
    
    print(f"   {icon} {symbol:>12}: P&L {best['pnl']:>+7.1f}% | WR {best['win_rate']:.0f}% | "
          f"PF {best['pf']:.2f} | TP{best['tp']}% SL{best['sl']}% {trail_str} | "
          f"{best['total']} trades | ${best['capital']:,.0f}")
    
    return {"best": best, "top5": results[:5], "all": results, "signals_count": len(signals)}

def run_optimization():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║     🔬 MEGA BUY Multi-Coin Optimizer          ║
    ║     Altcoins + BTC — Config Optimale           ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    print(f"📅 Période   : {DATE_START} → {DATE_END}")
    print(f"⏱️  Timeframe : {TIMEFRAME}")
    print(f"💰 Capital   : ${INITIAL_CAPITAL:,.0f} (Position {POSITION_SIZE_PCT}%)")
    print(f"📊 Paires    : {len(SYMBOLS)}")
    print(f"🔬 Combos/paire: ~{len(OPTIMIZE['take_profit'])*len(OPTIMIZE['stop_loss'])*len(OPTIMIZE['max_hold'])*len(OPTIMIZE['min_score'])*3}")
    
    # ═══════════════════════════════════════════
    # Phase 1 : Télécharger toutes les données
    # ═══════════════════════════════════════════
    print(f"\n{'═' * 60}")
    print(f"  📥 PHASE 1 — Téléchargement des données")
    print(f"{'═' * 60}")
    
    data = {}
    for sym in SYMBOLS:
        df = get_full_history(sym, TIMEFRAME, DATE_START, DATE_END)
        if df is not None and len(df) > 100:
            data[sym] = df
            print(f"   ✅ {sym}: {len(df)} bougies")
        else:
            print(f"   ❌ {sym}: données insuffisantes")
    
    if not data:
        print("❌ Aucune donnée chargée"); return
    
    # ═══════════════════════════════════════════
    # Phase 2 : Optimiser chaque paire
    # ═══════════════════════════════════════════
    print(f"\n{'═' * 60}")
    print(f"  🔬 PHASE 2 — Optimisation ({len(data)} paires)")
    print(f"{'═' * 60}\n")
    
    all_best = {}
    for sym, df in data.items():
        result = optimize_single(sym, df)
        if result:
            all_best[sym] = result
    
    if not all_best:
        print("❌ Aucun résultat"); return
    
    # ═══════════════════════════════════════════
    # Phase 3 : Classement final
    # ═══════════════════════════════════════════
    separator = "═" * 70
    print(f"\n{separator}")
    print(f"  🏆 CLASSEMENT FINAL — MEILLEURES PAIRES")
    print(f"{separator}\n")
    
    ranked = sorted(all_best.items(), key=lambda x: x[1]["best"]["pnl"], reverse=True)
    
    print(f"{'#':>3} {'Paire':>12} {'P&L':>9} {'WR':>6} {'PF':>6} {'Trades':>7} {'TP':>5} {'SL':>5} {'Hold':>5} {'Trail':>6} {'Capital':>10}")
    print(f"{'─'*3} {'─'*12} {'─'*9} {'─'*6} {'─'*6} {'─'*7} {'─'*5} {'─'*5} {'─'*5} {'─'*6} {'─'*10}")
    
    for i, (sym, res) in enumerate(ranked):
        b = res["best"]
        trail_s = f"{b['trail_pct']}%" if b["trailing"] else "OFF"
        icon = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
        pnl_s = f"{'+' if b['pnl']>0 else ''}{b['pnl']:.1f}%"
        print(f"{icon}{i+1:>2} {sym:>12} {pnl_s:>9} {b['win_rate']:>5.0f}% {b['pf']:>5.2f} {b['total']:>7} "
              f"{b['tp']:>4.0f}% {b['sl']:>4.1f}% {b['max_hold']:>5} {trail_s:>6} ${b['capital']:>9,.0f}")
    
    # Stats globales
    profitable = [s for s, r in ranked if r["best"]["pnl"] > 0]
    losing = [s for s, r in ranked if r["best"]["pnl"] <= 0]
    avg_pnl = np.mean([r["best"]["pnl"] for _, r in ranked])
    total_capital = sum(r["best"]["capital"] for _, r in ranked)
    invested = INITIAL_CAPITAL * len(ranked)
    
    print(f"\n{'─' * 70}")
    print(f"  📊 RÉSUMÉ GLOBAL")
    print(f"{'─' * 70}")
    print(f"  Paires profitables : {len(profitable)}/{len(ranked)}")
    print(f"  P&L moyen          : {avg_pnl:+.1f}%")
    print(f"  Si ${INITIAL_CAPITAL:,.0f} sur chaque : ${invested:,.0f} → ${total_capital:,.0f} ({(total_capital-invested)/invested*100:+.1f}%)")
    
    # ═══════════════════════════════════════════
    # Phase 4 : Telegram — Résultats
    # ═══════════════════════════════════════════
    
    # Message 1 : Classement
    tg = (
        f"🔬 <b>MEGA BUY OPTIMIZER — {len(data)} PAIRES</b>\n"
        f"📅 {DATE_START} → {DATE_END} | ⏱️ {TIMEFRAME}\n"
        f"💰 ${INITIAL_CAPITAL:,.0f}/paire ({POSITION_SIZE_PCT:.0f}% position)\n"
        f"{'─' * 30}\n\n"
        f"🏆 <b>CLASSEMENT :</b>\n\n"
    )
    
    for i, (sym, res) in enumerate(ranked):
        b = res["best"]
        if i < 3:
            medal = ["🥇", "🥈", "🥉"][i]
        elif b["pnl"] > 0:
            medal = "🟢"
        else:
            medal = "🔴"
        
        trail_s = f" T{b['trail_pct']}%" if b["trailing"] else ""
        tg += (
            f"{medal} <b>{sym}</b>\n"
            f"   P&L <b>{'+' if b['pnl']>0 else ''}{b['pnl']:.1f}%</b> | "
            f"WR {b['win_rate']:.0f}% | PF {b['pf']:.2f} | {b['total']}t\n"
            f"   TP{b['tp']}% SL{b['sl']}% H{b['max_hold']}{trail_s}\n"
            f"   ${INITIAL_CAPITAL:,.0f} → <b>${b['capital']:,.0f}</b>\n\n"
        )
    
    tg += (
        f"{'─' * 30}\n"
        f"📊 <b>GLOBAL</b>\n"
        f"  ✅ Profitables : {len(profitable)}/{len(ranked)}\n"
        f"  📈 P&L moyen : {avg_pnl:+.1f}%\n"
        f"  💰 ${invested:,.0f} → <b>${total_capital:,.0f}</b> ({(total_capital-invested)/invested*100:+.1f}%)\n"
    )
    
    send_telegram(tg)
    
    # Message 2 : Config détaillée TOP 3
    if len(ranked) >= 1:
        tg2 = f"📋 <b>CONFIG DÉTAILLÉE — TOP 3</b>\n\n"
        
        for sym, res in ranked[:3]:
            b = res["best"]
            tg2 += (
                f"━━━ <b>{sym}</b> ━━━\n"
                f"<code>"
                f"# {sym}\n"
                f"TAKE_PROFIT_PCT = {b['tp']}\n"
                f"STOP_LOSS_PCT = {b['sl']}\n"
                f"MAX_HOLD_BARS = {b['max_hold']}\n"
                f"COMBO_THRESHOLD_PCT = {int(b['min_score']/8*100)}\n"
                f"TRAILING_STOP = {b['trailing']}\n"
                f"TRAILING_PCT = {b['trail_pct']}\n"
                f"POSITION_SIZE_PCT = {POSITION_SIZE_PCT}"
                f"</code>\n"
                f"→ {b['total']}t | WR{b['win_rate']:.0f}% | PF{b['pf']:.2f}\n"
                f"→ ${INITIAL_CAPITAL:,.0f} → ${b['capital']:,.0f}\n\n"
            )
        
        # Meilleure config "universelle" (qui marche sur le plus de paires)
        tg2 += f"{'─' * 30}\n"
        tg2 += f"🌍 <b>CONFIG UNIVERSELLE :</b>\n"
        tg2 += f"(la plus fréquente dans les top configs)\n\n"
        
        # Trouver les params les plus communs
        top_tps = [r["best"]["tp"] for _, r in ranked if r["best"]["pnl"] > 0]
        top_sls = [r["best"]["sl"] for _, r in ranked if r["best"]["pnl"] > 0]
        top_trails = [r["best"]["trailing"] for _, r in ranked if r["best"]["pnl"] > 0]
        top_trail_pcts = [r["best"]["trail_pct"] for _, r in ranked if r["best"]["pnl"] > 0 and r["best"]["trailing"]]
        top_holds = [r["best"]["max_hold"] for _, r in ranked if r["best"]["pnl"] > 0]
        top_scores = [r["best"]["min_score"] for _, r in ranked if r["best"]["pnl"] > 0]
        
        if top_tps:
            best_tp = Counter(top_tps).most_common(1)[0][0]
            best_sl = Counter(top_sls).most_common(1)[0][0]
            best_trail = Counter(top_trails).most_common(1)[0][0]
            best_trail_pct = Counter(top_trail_pcts).most_common(1)[0][0] if top_trail_pcts else 2.0
            best_hold = Counter(top_holds).most_common(1)[0][0]
            best_score = Counter(top_scores).most_common(1)[0][0]
            
            tg2 += (
                f"<code>"
                f"TAKE_PROFIT_PCT = {best_tp}\n"
                f"STOP_LOSS_PCT = {best_sl}\n"
                f"MAX_HOLD_BARS = {best_hold}\n"
                f"COMBO_THRESHOLD_PCT = {int(best_score/8*100)}\n"
                f"TRAILING_STOP = {best_trail}\n"
                f"TRAILING_PCT = {best_trail_pct}\n"
                f"POSITION_SIZE_PCT = {POSITION_SIZE_PCT}"
                f"</code>"
            )
        
        send_telegram(tg2)
    
    # Message 3 : Meilleures paires à trader
    top_coins = [(s, r["best"]) for s, r in ranked if r["best"]["pnl"] > 20 and r["best"]["pf"] > 1.3]
    if top_coins:
        tg3 = (
            f"🔥 <b>PAIRES RECOMMANDÉES POUR LE BOT</b>\n"
            f"(P&L > 20% ET PF > 1.3)\n\n"
        )
        for sym, b in top_coins:
            stars = "⭐" * min(5, int(b["pnl"] / 20))
            tg3 += f"{stars} <b>{sym}</b> → +{b['pnl']:.0f}% | PF {b['pf']:.2f}\n"
        
        tg3 += f"\n💡 Ajoute ces paires en priorité dans le scanner !"
        send_telegram(tg3)
    
    print(f"\n📱 Résultats envoyés sur Telegram !")
    
    # Sauvegarder
    all_results = []
    for sym, res in all_best.items():
        for r in res["all"][:10]:
            all_results.append(r)
    results_df = pd.DataFrame(all_results)
    csv_file = f"optimizer_multi_{TIMEFRAME}_{DATE_START}_{DATE_END}.csv"
    results_df.to_csv(csv_file, index=False)
    print(f"💾 Top configs sauvegardées dans : {csv_file}")

if __name__ == "__main__":
    run_optimization()
