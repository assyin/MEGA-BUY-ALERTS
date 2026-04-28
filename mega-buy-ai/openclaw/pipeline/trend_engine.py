"""Multi-factor trend engine for BTC/ETH (professional-grade).

Replaces the broken "current candle red/green" heuristic used by gate_v6 and
market_sentiment. Uses:
  - Structural trend on CLOSED 1H candles (close vs EMA20/EMA50 + EMA20 slope)
  - 24h momentum from Binance ticker/24hr
  - Final score combining both, with labels compatible with the old API
    (still returns BULLISH / BEARISH for callers that only read the label).

Cached 5 min. One call per symbol: 1 klines + 1 ticker = 2 HTTP per 5 min per symbol.
"""

from __future__ import annotations

import time
import requests
from typing import Dict, Optional, Tuple, List


_TREND_CACHE: Dict[str, Dict] = {}
_TREND_TTL = 300  # 5 minutes


def _ema(values: List[float], length: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (length + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _fetch_closed_1h_closes(pair: str, count: int = 51) -> Optional[List[float]]:
    """Fetch CLOSED 1H candle closes (drops the currently-forming one)."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "1h", "limit": count + 1},
            timeout=8,
        )
        kd = r.json()
        if not kd or not isinstance(kd, list) or len(kd) < 51:
            return None
        closed = kd[:-1]
        return [float(k[4]) for k in closed]
    except Exception:
        return None


def _fetch_24h_change(pair: str) -> Optional[float]:
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": pair}, timeout=5,
        )
        return float(r.json().get("priceChangePercent", 0))
    except Exception:
        return None


def compute_trend(pair: str) -> Dict:
    """Compute a robust BTC/ETH trend verdict.

    Returns a dict with:
      score            int  (-4..+4)     — structural + momentum
      structural       int  (-2..+2)
      momentum         int  (-2..+2)
      label            str  BULLISH / BULLISH_OK / NEUTRAL / BEARISH
      bullish          bool (score >= 0)   <- gate decision
      details          dict — close, ema20, ema50, slope_pct, change_24h
    """
    now = time.time()
    cached = _TREND_CACHE.get(pair)
    if cached and (now - cached["ts"]) < _TREND_TTL:
        return cached["data"]

    closes = _fetch_closed_1h_closes(pair)
    chg_24h = _fetch_24h_change(pair)

    details = {"close": None, "ema20": None, "ema50": None, "slope_pct": None, "change_24h": chg_24h}
    structural = 0

    if closes and len(closes) >= 51:
        ema20 = _ema(closes, 20)
        ema50 = _ema(closes, 50)
        close = closes[-1]
        e20, e50 = ema20[-1], ema50[-1]
        slope_pct = (ema20[-1] - ema20[-6]) / ema20[-6] * 100 if ema20[-6] > 0 else 0
        details.update({"close": round(close, 4), "ema20": round(e20, 4),
                        "ema50": round(e50, 4), "slope_pct": round(slope_pct, 3)})

        if close > e20 > e50 and slope_pct > 0:
            structural = 2
        elif close > e50 and slope_pct >= -0.05:
            structural = 1
        elif close < e20 < e50 and slope_pct < 0:
            structural = -2
        elif close < e50:
            structural = -1
        else:
            structural = 0

    momentum = 0
    if chg_24h is not None:
        if chg_24h >= 2.0:
            momentum = 2
        elif chg_24h >= 0.5:
            momentum = 1
        elif chg_24h <= -2.0:
            momentum = -2
        elif chg_24h <= -0.5:
            momentum = -1

    score = structural + momentum
    if score >= 2:
        label = "BULLISH"
    elif score == 1:
        label = "BULLISH_OK"
    elif score == 0:
        label = "NEUTRAL"
    else:
        label = "BEARISH"

    data = {
        "score": score,
        "structural": structural,
        "momentum": momentum,
        "label": label,
        "bullish": score >= 0,
        "details": details,
    }
    _TREND_CACHE[pair] = {"data": data, "ts": now}
    return data


def is_bullish(pair: str) -> Tuple[bool, str]:
    """Backward-compatible helper. Returns (bullish_enough_for_gate, human_reason)."""
    t = compute_trend(pair)
    d = t["details"]
    reason = (f"{t['label']} score={t['score']:+d} "
              f"(struct={t['structural']:+d}, mom={t['momentum']:+d}, "
              f"24h={d.get('change_24h')}%, slope={d.get('slope_pct')}%)")
    return t["bullish"], reason
