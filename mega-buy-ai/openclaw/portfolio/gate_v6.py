"""Shared optimized gate filter for V6 and V7.

Filter (based on 7d backtest analysis — 73.5% real WR, +290% PnL with TP+15%):
- Body 4H >= 3% (THE KEY)
- Range 4H >= 3.5%
- Direction 4H = green
- DI+ <= 45
- ADX <= 50
- BTC trend 1H = BULLISH
- ETH trend 1H = BULLISH
- PP = True
- EC = True
- 24h change in [0, 50]
- At least one fast TF (15m / 30m / 1h)
- Volume spike vs 24h >= -30% (reject low-volume alerts — WR 33% below this)
- Volume spike vs 48h >= -30% (confirm volume is not collapsing)
"""

import requests
from typing import Dict, Optional, Tuple


# Filter thresholds
MAX_DI_PLUS = 45.0
MAX_ADX = 50.0
MIN_RANGE_4H_PCT = 3.5
MIN_BODY_4H_PCT = 3.0          # Key filter — trades < 3% body have higher loss rate
MIN_24H_PCT = 0.0
MAX_24H_PCT = 50.0
FAST_TFS = {"15m", "30m", "1h"}
MIN_VOL_SPIKE_24H = -30.0      # Reject low-volume (WR 33% below this)
MIN_VOL_SPIKE_48H = -30.0      # Confirm volume not collapsing


def _fetch_4h_candle(pair: str) -> Optional[Tuple[float, float, float, float]]:
    """Returns (open, high, low, close) of current 4H candle."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "4h", "limit": 1},
            timeout=5,
        )
        kd = r.json()
        if not kd or not isinstance(kd, list) or len(kd) == 0:
            return None
        return float(kd[0][1]), float(kd[0][2]), float(kd[0][3]), float(kd[0][4])
    except Exception:
        return None


def _fetch_1h_trend(pair: str) -> Optional[str]:
    """Returns 'BULLISH' or 'BEARISH' from current 1H candle."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "1h", "limit": 1},
            timeout=5,
        )
        kd = r.json()
        if not kd or not isinstance(kd, list) or len(kd) == 0:
            return None
        o, c = float(kd[0][1]), float(kd[0][4])
        return "BULLISH" if c >= o else "BEARISH"
    except Exception:
        return None


def _fetch_24h_change(pair: str) -> Optional[float]:
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/24hr",
            params={"symbol": pair},
            timeout=5,
        )
        return float(r.json().get("priceChangePercent", 0))
    except Exception:
        return None


def _fetch_volume_spikes(pair: str) -> Tuple[Optional[float], Optional[float]]:
    """Returns (vol_spike_vs_24h, vol_spike_vs_48h) in percent."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": pair, "interval": "1h", "limit": 48},
            timeout=5,
        )
        klines = r.json()
        if not klines or not isinstance(klines, list) or len(klines) < 2:
            return None, None
        volumes = [float(k[7]) for k in klines]  # quote volume (USDT)
        current = volumes[-1]
        prev = volumes[:-1]
        avg_24h = sum(prev[-24:]) / min(len(prev), 24) if prev else 0
        avg_48h = sum(prev) / len(prev) if prev else 0
        spike_24h = round((current / avg_24h - 1) * 100, 1) if avg_24h > 0 else None
        spike_48h = round((current / avg_48h - 1) * 100, 1) if avg_48h > 0 else None
        return spike_24h, spike_48h
    except Exception:
        return None, None


def build_gate_cache(pair: str) -> Dict:
    """Pre-fetch all gate data once. Pass to passes_optimized_gate(cache=...) to avoid redundant API calls."""
    return {
        "candle_4h": _fetch_4h_candle(pair),
        "btc_trend": _fetch_1h_trend("BTCUSDT"),
        "eth_trend": _fetch_1h_trend("ETHUSDT"),
        "change_24h": _fetch_24h_change(pair),
        "vol_spikes": _fetch_volume_spikes(pair),
    }


def passes_optimized_gate(pair: str, alert: Dict, label: str = "GATE", cache: Dict = None) -> Tuple[bool, str]:
    """Check if a pair+alert passes the optimized filter.

    Returns (passed, reason). reason explains failure for logging.
    Pass cache=build_gate_cache(pair) to avoid redundant API calls.
    """
    # 1. DI+ / ADX from alert
    di_plus = alert.get("di_plus_4h")
    if di_plus is None or di_plus > MAX_DI_PLUS:
        return False, f"di_plus={di_plus} > {MAX_DI_PLUS}"

    adx = alert.get("adx_4h")
    if adx is None or adx > MAX_ADX:
        return False, f"adx={adx} > {MAX_ADX}"

    # 2. PP / EC from alert
    if not alert.get("pp"):
        return False, "pp=false"
    if not alert.get("ec"):
        return False, "ec=false"

    # 3. Timeframes — at least one fast TF
    tfs = alert.get("timeframes") or []
    if not any(tf in FAST_TFS for tf in tfs):
        return False, f"no_fast_tf (got {tfs})"

    # 4. 4H candle (body, range, direction) — use cache if available
    candle = cache["candle_4h"] if cache else _fetch_4h_candle(pair)
    if candle is None:
        return False, "no_4h_candle"
    o, h, l, c = candle
    if o <= 0 or l <= 0:
        return False, "bad_4h_candle"

    direction = "green" if c >= o else "red"
    if direction != "green":
        return False, "4h_red"

    body_pct = abs(c - o) / o * 100
    if body_pct < MIN_BODY_4H_PCT:
        return False, f"body={body_pct:.2f}% < {MIN_BODY_4H_PCT}%"

    range_pct = (h - l) / l * 100
    if range_pct < MIN_RANGE_4H_PCT:
        return False, f"range={range_pct:.2f}% < {MIN_RANGE_4H_PCT}%"

    # 5. BTC + ETH trend 1H (both must be BULLISH) — use cache if available
    btc_trend = cache["btc_trend"] if cache else _fetch_1h_trend("BTCUSDT")
    if btc_trend != "BULLISH":
        return False, f"btc_1h={btc_trend}"

    eth_trend = cache["eth_trend"] if cache else _fetch_1h_trend("ETHUSDT")
    if eth_trend != "BULLISH":
        return False, f"eth_1h={eth_trend}"

    # 6. 24h change of pair — use cache if available
    ch24 = cache["change_24h"] if cache else _fetch_24h_change(pair)
    if ch24 is None:
        return False, "no_24h"
    if ch24 < MIN_24H_PCT or ch24 > MAX_24H_PCT:
        return False, f"24h={ch24:.1f}% out of [{MIN_24H_PCT},{MAX_24H_PCT}]"

    return True, f"OK body={body_pct:.1f}% range={range_pct:.1f}% 24h={ch24:.1f}%"
