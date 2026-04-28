"""V11 gate functions — discovery-driven filters.

5 variants:
  V11a  Custom        — user's original continuation filter
  V11b  Compression   — Range 30m ≤1.89 + Range 4h ≤2.58 (top combo)
  V11c  Premium       — Range 1h ≤1.67 + BTC.D ≤57 (96.4% WR)
  V11d  Accum         — Accum days ≥3.7 + Range 30m ≤1.46
  V11e  BBSqueeze     — BB 4H width ≤13.56

Each gate accepts (alert, cache) where cache is built once per alert via
`build_v11_cache(pair)` and shared across all 5 gates to avoid redundant Binance calls.
"""

import math
import time
import requests
from typing import Dict, Optional, Tuple


# ─── Shared cache for BTC dominance (refreshed every 10 min globally) ───
_BTC_DOM_CACHE = {"value": None, "ts": 0}
_DOM_TTL = 600  # 10 minutes


def get_btc_dominance() -> Optional[float]:
    """BTC dominance from CoinGecko, cached 10 min."""
    now = time.time()
    if _BTC_DOM_CACHE["value"] is not None and now - _BTC_DOM_CACHE["ts"] < _DOM_TTL:
        return _BTC_DOM_CACHE["value"]
    try:
        r = requests.get("https://api.coingecko.com/api/v3/global", timeout=5)
        d = r.json().get("data", {}).get("market_cap_percentage", {})
        btc = d.get("btc")
        if btc is not None:
            _BTC_DOM_CACHE["value"] = float(btc)
            _BTC_DOM_CACHE["ts"] = now
            return float(btc)
    except Exception:
        pass
    return None


# ─── Shared cache for BTC 24h change (refreshed every 60s, Binance ticker) ───
_BTC_24H_CACHE = {"value": None, "ts": 0}
_BTC_24H_TTL = 60  # 1 minute — frequent enough to catch dumps


def get_btc_change_24h() -> Optional[float]:
    """BTC 24h price change % from Binance, cached 60s."""
    now = time.time()
    if _BTC_24H_CACHE["value"] is not None and now - _BTC_24H_CACHE["ts"] < _BTC_24H_TTL:
        return _BTC_24H_CACHE["value"]
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                         params={"symbol": "BTCUSDT"}, timeout=5)
        ch = r.json().get("priceChangePercent")
        if ch is not None:
            _BTC_24H_CACHE["value"] = float(ch)
            _BTC_24H_CACHE["ts"] = now
            return float(ch)
    except Exception:
        pass
    return None


def _candle_stats(klines: list) -> Dict:
    """From a list of klines, return body/range/direction of the LAST candle."""
    if not klines: return {}
    last = klines[-1]
    o, h, l, c = float(last[1]), float(last[2]), float(last[3]), float(last[4])
    if o <= 0 or l <= 0: return {}
    return {
        "body_pct": abs(c - o) / o * 100,
        "range_pct": (h - l) / l * 100,
        "direction": "green" if c >= o else "red",
        "open": o, "high": h, "low": l, "close": c,
    }


def _bb_width_pct(closes: list, period: int = 20, std_mult: float = 2.0) -> Optional[float]:
    """Bollinger Band width % from a list of close prices."""
    if len(closes) < period: return None
    sub = closes[-period:]
    mean = sum(sub) / period
    if mean <= 0: return None
    var = sum((x - mean) ** 2 for x in sub) / period
    std = math.sqrt(var)
    upper = mean + std_mult * std
    lower = mean - std_mult * std
    return (upper - lower) / mean * 100


def _detect_accumulation(klines_4h: list, max_range_pct: float = 10.0) -> Dict:
    """Walk backwards from the most recent 4H candle, count consecutive candles
    that stay within max_range_pct of the running mean. Returns {days, hours, range_pct}.
    """
    if not klines_4h or len(klines_4h) < 4:
        return {"days": 0, "hours": 0, "range_pct": 0}

    # Walk backwards from end
    highs = [float(k[2]) for k in klines_4h]
    lows = [float(k[3]) for k in klines_4h]
    closes = [float(k[4]) for k in klines_4h]

    # Start with last candle, expand window backwards while range stays tight
    end = len(klines_4h) - 1
    n = 1
    cum_high = highs[end]
    cum_low = lows[end]
    while n <= len(klines_4h) - 1:
        i = end - n
        if i < 0: break
        new_high = max(cum_high, highs[i])
        new_low = min(cum_low, lows[i])
        mean = sum(closes[i:end+1]) / (n + 1)
        rng_pct = (new_high - new_low) / mean * 100 if mean else 999
        if rng_pct > max_range_pct:
            break
        cum_high = new_high
        cum_low = new_low
        n += 1
    hours = n * 4  # 4H candles
    days = hours / 24
    final_range = (cum_high - cum_low) / ((cum_high + cum_low) / 2) * 100 if (cum_high + cum_low) > 0 else 0
    return {"days": round(days, 1), "hours": int(hours), "range_pct": round(final_range, 1)}


# ─── Cache builder ───────────────────────────────────────────

def build_v11_cache(pair: str) -> Dict:
    """Compute everything the V11 gates might need, in one batched Binance pass.

    Returns a dict with:
      candle_15m_range_pct, candle_15m_body_pct, candle_15m_direction
      candle_30m_range_pct, candle_30m_body_pct, candle_30m_direction
      candle_1h_range_pct,  candle_1h_body_pct,  candle_1h_direction
      candle_4h_range_pct,  candle_4h_body_pct,  candle_4h_direction
      bb_4h_width_pct
      accumulation: {days, hours, range_pct}
      btc_dominance (from CoinGecko)
    """
    cache: Dict = {"pair": pair}
    api = "https://api.binance.com/api/v3/klines"

    def _fetch(interval: str, limit: int):
        try:
            r = requests.get(api, params={"symbol": pair, "interval": interval, "limit": limit}, timeout=5)
            d = r.json()
            return d if isinstance(d, list) else None
        except Exception:
            return None

    # Per-TF candle stats — use last 50 for 4H (BB needs 20+) and small for others
    for tf, n in [("15m", 1), ("30m", 1), ("1h", 1)]:
        kls = _fetch(tf, n)
        if kls:
            s = _candle_stats(kls)
            for k, v in s.items():
                cache[f"candle_{tf}_{k}"] = v

    kls_4h = _fetch("4h", 50)
    if kls_4h:
        s = _candle_stats(kls_4h)
        for k, v in s.items():
            cache[f"candle_4h_{k}"] = v
        # BB 4H width
        closes_4h = [float(k[4]) for k in kls_4h]
        cache["bb_4h_width_pct"] = _bb_width_pct(closes_4h, 20, 2.0)
        # Accumulation
        cache["accumulation"] = _detect_accumulation(kls_4h, max_range_pct=10.0)

    # BTC dominance
    cache["btc_dominance"] = get_btc_dominance()

    return cache


# ─── Helper: read an alert field with fallback to cache ──────

def _f(d: dict, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


# ─── 5 gate functions ────────────────────────────────────────

def gate_v11a(alert: Dict, cache: Dict) -> Tuple[bool, str]:
    """V11a Custom — user's original continuation filter."""
    # Most fields available directly from alerts table (di_plus_4h, etc.)
    di_p = _f(alert, "di_plus_4h"); di_m = _f(alert, "di_minus_4h"); adx = _f(alert, "adx_4h")
    if di_p is None or di_p < 37 or di_p > 50: return False, "DI+ 4H OOR"
    if di_m is None or di_m < 0 or di_m > 14: return False, "DI- 4H OOR"
    if adx is None or adx < 15: return False, "ADX 4H <15"
    if (di_p - di_m) > 45: return False, "DI spread >45"
    if (adx - di_m) < 3: return False, "ADX-DI- <3"
    if (alert.get("rsi") or 0) > 79: return False, "RSI >79"

    # 4H candle from cache
    body4 = cache.get("candle_4h_body_pct")
    range4 = cache.get("candle_4h_range_pct")
    dir4 = cache.get("candle_4h_direction")
    if body4 is None or body4 < 2.7: return False, "body4h <2.7"
    if range4 is None or range4 > 34: return False, "range4h >34"
    if dir4 != "green": return False, "4H not green"

    # 24h change — try alert first (some alerts have it)
    c24 = _f(alert, "change_24h_pct")
    if c24 is not None and c24 > 36: return False, "24h >36"

    # STC (stored on alert by processor.py earlier)
    if (alert.get("stc_15m") or 0) < 0.1: return False, "stc_15m <0.1"
    if (alert.get("stc_30m") or 0) < 0.2: return False, "stc_30m <0.2"
    if (alert.get("stc_1h") or 0) < 0.1: return False, "stc_1h <0.1"

    # PP & EC
    if not alert.get("pp"): return False, "no PP"
    if not alert.get("ec"): return False, "no EC"

    # 15m TF present
    tfs = alert.get("timeframes") or []
    if "15m" not in tfs: return False, "no 15m TF"

    # Exclude all red vol
    vp = alert.get("vol_pct") or {}
    if isinstance(vp, dict) and vp:
        if all((v is None or v <= 0) for v in vp.values()):
            return False, "all-red volume"

    return True, "OK"


def gate_v11b(alert: Dict, cache: Dict) -> Tuple[bool, str]:
    """V11b Compression — Range 30m ≤1.89 + Range 4h ≤2.58."""
    r30 = cache.get("candle_30m_range_pct")
    r4 = cache.get("candle_4h_range_pct")
    if r30 is None: return False, "no 30m data"
    if r4 is None: return False, "no 4h data"
    if r30 > 1.89: return False, f"range_30m {r30:.2f} > 1.89"
    if r4 > 2.58: return False, f"range_4h {r4:.2f} > 2.58"
    return True, "OK"


def gate_v11c(alert: Dict, cache: Dict) -> Tuple[bool, str]:
    """V11c Premium — Range 1h ≤1.67 + BTC.D ≤57."""
    r1h = cache.get("candle_1h_range_pct")
    btc_d = cache.get("btc_dominance")
    if r1h is None: return False, "no 1h data"
    if btc_d is None: return False, "no btc dominance"
    if r1h > 1.67: return False, f"range_1h {r1h:.2f} > 1.67"
    if btc_d > 56.98: return False, f"btc.d {btc_d:.2f} > 56.98"
    return True, "OK"


def gate_v11d(alert: Dict, cache: Dict) -> Tuple[bool, str]:
    """V11d Accum — Accum days ≥3.7 + Range 30m ≤1.46."""
    acc = cache.get("accumulation") or {}
    days = acc.get("days", 0)
    r30 = cache.get("candle_30m_range_pct")
    if days < 3.7: return False, f"accum_days {days} <3.7"
    if r30 is None: return False, "no 30m data"
    if r30 > 1.46: return False, f"range_30m {r30:.2f} > 1.46"
    return True, "OK"


def gate_v11e(alert: Dict, cache: Dict) -> Tuple[bool, str]:
    """V11e BBSqueeze — BB 4H width ≤13.56."""
    bbw = cache.get("bb_4h_width_pct")
    if bbw is None: return False, "no BB data"
    if bbw > 13.56: return False, f"bb_4h_width {bbw:.2f} > 13.56"
    return True, "OK"


# ─── Registry ────────────────────────────────────────────────

GATES = {
    "v11a": (gate_v11a, "Custom (continuation)"),
    "v11b": (gate_v11b, "Compression (R30m+R4h)"),
    "v11c": (gate_v11c, "Premium (R1h+BTC.D)"),
    "v11d": (gate_v11d, "Accum Breakout"),
    "v11e": (gate_v11e, "BB Squeeze 4H"),
}
