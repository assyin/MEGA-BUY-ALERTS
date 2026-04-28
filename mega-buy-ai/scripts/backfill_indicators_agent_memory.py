#!/usr/bin/env python3
"""Backfill missing indicators into features_fingerprint for agent_memory rows.

Fills (when missing):
  - candle_{tf}_body_pct / _range_pct / _direction  for tf in {15m, 30m, 1h, 4h}
  - vol_spike_vs_1h / _4h / _24h / _48h             (from 1h klines, 48 candles)
  - stc_15m / stc_30m / stc_1h                      (adaptive STC length=50 fast=50 slow=200)
  - btc_trend_1h / eth_trend_1h                     (compute_trend on BTC/ETH 1h closes at alert time — bucket-cached)
  - fear_greed_value / fear_greed_label             (alternative.me historical, daily bucket)

Merges into existing features_fingerprint (keeps existing keys). Only updates rows
that are actually missing at least one field.

Usage:
  python3 -u scripts/backfill_indicators_agent_memory.py --hours 168 --dry-run
  python3 -u scripts/backfill_indicators_agent_memory.py --hours 168 --limit 3 --dry-run
  python3 -u scripts/backfill_indicators_agent_memory.py --hours 168
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import requests
from openclaw.config import get_settings
from supabase import create_client

BINANCE_API = "https://api.binance.com"


# ─── STC (adaptive stochastic, copy of backtest engine) ──────────────────────
def calc_adaptive_stc(close: np.ndarray, length: int = 50, fast: int = 50, slow: int = 200):
    n = len(close)
    if n < slow + 1:
        return np.full(n, np.nan)
    src = np.full(n, np.nan)
    diff = abs(slow - fast)
    for i in range(diff, n):
        x = np.arange(diff)
        y = close[i - diff + 1:i + 1]
        if len(y) == diff:
            slope, intercept = np.polyfit(x, y, 1)
            src[i] = intercept + slope * (diff - 1)
    sc = np.full(n, np.nan)
    for i in range(length, n):
        change_sum = np.sum(np.abs(np.diff(close[i - length:i + 1])))
        sc[i] = abs(close[i] - close[i - length]) / change_sum if change_sum > 0 else 0
    stc = np.full(n, np.nan)
    for i in range(max(slow, length), n):
        if np.isnan(src[i]) or np.isnan(sc[i]):
            continue
        src_fast = src[max(0, i - fast + 1):i + 1]
        src_slow = src[max(0, i - slow + 1):i + 1]
        src_fast = src_fast[~np.isnan(src_fast)]
        src_slow = src_slow[~np.isnan(src_slow)]
        if len(src_fast) == 0 or len(src_slow) == 0:
            continue
        a = sc[i] * np.max(src_fast) + (1 - sc[i]) * np.max(src_slow)
        b = sc[i] * np.min(src_fast) + (1 - sc[i]) * np.min(src_slow)
        stc[i] = (src[i] - b) / (a - b) if a != b else 0.5
    return stc


# ─── EMA (for trend engine) ───────────────────────────────────────────────────
def ema(values: List[float], length: int) -> List[float]:
    if not values or len(values) < length:
        return []
    k = 2 / (length + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(result[-1] + k * (v - result[-1]))
    return result


def compute_trend_from_closes(closes: List[float], chg_24h: Optional[float]) -> str:
    """Simplified version of trend_engine.compute_trend. Returns BULLISH/BULLISH_OK/NEUTRAL/BEARISH."""
    if not closes or len(closes) < 51:
        return "NEUTRAL"
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    if not ema20 or not ema50 or len(ema20) < 6:
        return "NEUTRAL"
    close = closes[-1]
    e20, e50 = ema20[-1], ema50[-1]
    slope_pct = (ema20[-1] - ema20[-6]) / ema20[-6] * 100 if ema20[-6] > 0 else 0

    structural = 0
    if close > e20 > e50 and slope_pct > 0:
        structural = 2
    elif close > e50 and slope_pct >= -0.05:
        structural = 1
    elif close < e20 < e50 and slope_pct < 0:
        structural = -2
    elif close < e50 and slope_pct < 0:
        structural = -1

    momentum = 0
    if chg_24h is not None:
        if chg_24h > 2:
            momentum = 2
        elif chg_24h > 0:
            momentum = 1
        elif chg_24h > -2:
            momentum = 0
        elif chg_24h > -4:
            momentum = -1
        else:
            momentum = -2

    score = structural + momentum
    if score >= 3:
        return "BULLISH"
    if score >= 1:
        return "BULLISH_OK"
    if score >= -1:
        return "NEUTRAL"
    return "BEARISH"


# ─── Klines fetch with retry ──────────────────────────────────────────────────
def fetch_klines(symbol: str, interval: str, end_ms: int, limit: int) -> list:
    for attempt in range(3):
        try:
            r = requests.get(
                f"{BINANCE_API}/api/v3/klines",
                params={"symbol": symbol, "interval": interval, "endTime": end_ms, "limit": limit},
                timeout=15,
            )
            if r.status_code == 200:
                return r.json() or []
            return []
        except Exception:
            if attempt == 2:
                return []
            time.sleep(0.5 * (attempt + 1))
    return []


# ─── BTC/ETH trend bucket cache ───────────────────────────────────────────────
_btc_eth_cache: Dict[int, Dict[str, str]] = {}


def get_btc_eth_trend(alert_ms: int) -> Dict[str, str]:
    """Cache by hour-bucket — trend doesn't change within 1h."""
    bucket = alert_ms // (3600 * 1000)
    if bucket in _btc_eth_cache:
        return _btc_eth_cache[bucket]

    end_ms = bucket * 3600 * 1000 + 3600 * 1000  # end of that hour
    result = {}
    for symbol, prefix in [("BTCUSDT", "btc"), ("ETHUSDT", "eth")]:
        klines = fetch_klines(symbol, "1h", end_ms, 60)
        if not klines:
            result[f"{prefix}_trend_1h"] = None
            continue
        closes = [float(k[4]) for k in klines]
        chg_24h = None
        if len(klines) >= 25:
            prev = float(klines[-25][4])
            cur = float(klines[-1][4])
            chg_24h = (cur - prev) / prev * 100 if prev > 0 else 0
        result[f"{prefix}_trend_1h"] = compute_trend_from_closes(closes, chg_24h)
        time.sleep(0.05)

    _btc_eth_cache[bucket] = result
    return result


# ─── Fear & Greed daily cache ─────────────────────────────────────────────────
_fg_cache: Dict[str, Dict] = {}


def init_fg_cache(days: int = 10):
    try:
        r = requests.get(f"https://api.alternative.me/fng/?limit={days}", timeout=10)
        data = r.json() or {}
        for d in data.get("data", []):
            ts = int(d["timestamp"])
            date_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            _fg_cache[date_str] = {
                "value": int(d["value"]),
                "label": d["value_classification"],
            }
        print(f"  F&G cache loaded: {len(_fg_cache)} days")
    except Exception as e:
        print(f"  ⚠ F&G fetch failed: {e}")


def get_fg(alert_dt: datetime) -> Optional[Dict]:
    key = alert_dt.strftime("%Y-%m-%d")
    return _fg_cache.get(key)


# ─── Per-TF candle + STC computation ──────────────────────────────────────────
def compute_tf_metrics(pair: str, interval: str, end_ms: int, need_stc: bool) -> Dict:
    """Fetch klines for a TF, compute candle body/range/direction + STC if needed."""
    # For STC we need 300 candles; for candle-only we need 1.
    limit = 300 if need_stc else 1
    klines = fetch_klines(pair, interval, end_ms, limit)
    if not klines:
        return {}

    out = {}
    # Last kline = candle at alert time
    last = klines[-1]
    o, h, l, c = float(last[1]), float(last[2]), float(last[3]), float(last[4])
    if o > 0 and l > 0:
        tf_key = interval  # "15m", "30m", "1h", "4h"
        out[f"candle_{tf_key}_body_pct"] = round(abs(c - o) / o * 100, 2)
        out[f"candle_{tf_key}_range_pct"] = round((h - l) / l * 100, 2)
        out[f"candle_{tf_key}_direction"] = "green" if c >= o else "red"

    if need_stc and len(klines) >= 201:
        closes = np.array([float(k[4]) for k in klines])
        stc_arr = calc_adaptive_stc(closes)
        last_stc = stc_arr[-1]
        if not np.isnan(last_stc):
            stc_key = {"15m": "stc_15m", "30m": "stc_30m", "1h": "stc_1h"}.get(interval)
            if stc_key:
                out[stc_key] = round(float(last_stc), 4)

    return out


# ─── Vol spikes (from 1h klines, 48 candles) ──────────────────────────────────
def compute_vol_spikes(pair: str, end_ms: int) -> Dict:
    klines = fetch_klines(pair, "1h", end_ms, 48)
    if not klines or len(klines) < 2:
        return {}
    vols = [float(k[7]) for k in klines]  # quote volume
    cur = vols[-1]
    prev = vols[:-1]

    def avg(vv, n):
        s = vv[-n:] if len(vv) >= n else vv
        return sum(s) / len(s) if s else 0

    out = {}
    for key, n in [("vol_spike_vs_1h", 1), ("vol_spike_vs_4h", 4),
                   ("vol_spike_vs_24h", 24), ("vol_spike_vs_48h", len(prev))]:
        a = avg(prev, n)
        out[key] = round((cur / a - 1) * 100, 1) if a > 0 else None
    out["volume_usdt"] = round(cur, 2)
    return out


# ─── Main ─────────────────────────────────────────────────────────────────────
NEEDED_FIELDS = [
    "candle_4h_body_pct", "candle_4h_range_pct",
    "candle_15m_body_pct", "candle_30m_body_pct", "candle_1h_body_pct",
    "vol_spike_vs_1h", "vol_spike_vs_4h", "vol_spike_vs_24h", "vol_spike_vs_48h",
    "stc_15m", "stc_30m", "stc_1h",
    "fear_greed_value",
    "btc_trend_1h", "eth_trend_1h",
]


def needs_backfill(fp: dict) -> Dict[str, bool]:
    need = {}
    need["candles_4h"] = fp.get("candle_4h_body_pct") is None
    need["candles_15m"] = fp.get("candle_15m_body_pct") is None
    need["candles_30m"] = fp.get("candle_30m_body_pct") is None
    need["candles_1h"] = fp.get("candle_1h_body_pct") is None
    need["vol"] = fp.get("vol_spike_vs_1h") is None
    need["stc_15m"] = fp.get("stc_15m") is None
    need["stc_30m"] = fp.get("stc_30m") is None
    need["stc_1h"] = fp.get("stc_1h") is None
    need["fg"] = fp.get("fear_greed_value") is None
    need["btc_eth"] = fp.get("btc_trend_1h") is None or fp.get("eth_trend_1h") is None
    return need


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print(f"🔄 Loading Fear & Greed history...")
    init_fg_cache(days=min(args.hours // 24 + 3, 30))

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat()
    print(f"🔍 Fetching agent_memory rows since {cutoff}...")

    # Paginated fetch
    rows = []
    page = 0
    while True:
        batch = sb.table("agent_memory").select(
            "id,pair,timestamp,features_fingerprint"
        ).gte("timestamp", cutoff).order("timestamp").range(page * 500, (page + 1) * 500 - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < 500:
            break
        page += 1
    print(f"   Loaded {len(rows)} rows")

    # Filter to rows needing backfill
    to_process = []
    for r in rows:
        fp = r.get("features_fingerprint") or {}
        flags = needs_backfill(fp)
        if any(flags.values()):
            to_process.append((r, flags))
    print(f"   → {len(to_process)} rows need backfill")

    if args.limit:
        to_process = to_process[:args.limit]
        print(f"   Limiting to first {len(to_process)}")

    if not to_process:
        print("✅ Nothing to backfill")
        return

    stats = {"updated": 0, "skipped": 0, "errors": 0}
    updates_by_field = {f: 0 for f in NEEDED_FIELDS}

    for i, (row, flags) in enumerate(to_process, 1):
        pair = row["pair"]
        ts = row["timestamp"]
        fp = dict(row.get("features_fingerprint") or {})

        try:
            alert_dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            end_ms = int(alert_dt.timestamp() * 1000)
        except Exception:
            stats["errors"] += 1
            continue

        summary = []
        changed = {}

        # Per-TF metrics (15m, 30m, 1h): may need candles AND/OR STC
        for tf, need_c, need_s in [
            ("15m", flags["candles_15m"], flags["stc_15m"]),
            ("30m", flags["candles_30m"], flags["stc_30m"]),
            ("1h", flags["candles_1h"], flags["stc_1h"]),
        ]:
            if need_c or need_s:
                metrics = compute_tf_metrics(pair, tf, end_ms, need_s)
                for k, v in metrics.items():
                    if v is not None and fp.get(k) is None:
                        fp[k] = v
                        changed[k] = v
                time.sleep(0.05)

        # 4h candle
        if flags["candles_4h"]:
            metrics = compute_tf_metrics(pair, "4h", end_ms, False)
            for k, v in metrics.items():
                if v is not None and fp.get(k) is None:
                    fp[k] = v
                    changed[k] = v
            time.sleep(0.05)

        # Vol spikes
        if flags["vol"]:
            metrics = compute_vol_spikes(pair, end_ms)
            for k, v in metrics.items():
                if v is not None and fp.get(k) is None:
                    fp[k] = v
                    changed[k] = v
            time.sleep(0.05)

        # BTC/ETH trend
        if flags["btc_eth"]:
            t = get_btc_eth_trend(end_ms)
            for k, v in t.items():
                if v is not None and fp.get(k) is None:
                    fp[k] = v
                    changed[k] = v

        # F&G
        if flags["fg"]:
            fg = get_fg(alert_dt)
            if fg:
                if fp.get("fear_greed_value") is None:
                    fp["fear_greed_value"] = fg["value"]
                    changed["fear_greed_value"] = fg["value"]
                if fp.get("fear_greed_label") is None:
                    fp["fear_greed_label"] = fg["label"]
                    changed["fear_greed_label"] = fg["label"]

        # Count per-field stats
        for k in changed:
            if k in updates_by_field:
                updates_by_field[k] = updates_by_field.get(k, 0) + 1

        if not changed:
            stats["skipped"] += 1
            print(f"[{i}/{len(to_process)}] {pair:14s} → no data fetched (pair delisted?)")
            continue

        summary_str = f"{len(changed)} fields"
        print(f"[{i}/{len(to_process)}] {pair:14s} ts={ts[:19]} → +{summary_str}")

        if not args.dry_run:
            try:
                sb.table("agent_memory").update({"features_fingerprint": fp}).eq("id", row["id"]).execute()
                stats["updated"] += 1
            except Exception as e:
                print(f"    ⚠ DB error: {e}")
                stats["errors"] += 1

    print()
    print("━" * 70)
    print(f"📊 Summary: {stats}")
    print("📊 Per-field updates:")
    for f, c in sorted(updates_by_field.items(), key=lambda x: -x[1]):
        if c > 0:
            print(f"   {f:30s}: {c} rows")

    if args.dry_run:
        print(f"\n🔸 DRY RUN — nothing written")


if __name__ == "__main__":
    main()
