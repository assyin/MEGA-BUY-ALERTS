"""Recompute BTC/ETH trend for agent_memory rows in the last N hours.

Uses the new multi-factor trend_engine with HISTORICAL klines (endTime=alert_hour)
so each alert gets the trend label that should have been assigned at its time.
"""

import os
import sys
import time
import argparse
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "/home/assyin/MEGA-BUY-BOT/mega-buy-ai")

from dotenv import load_dotenv
load_dotenv("/home/assyin/MEGA-BUY-BOT/python/.env")

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
assert SUPABASE_URL and SUPABASE_KEY, "Supabase creds missing"

sb = create_client(SUPABASE_URL, SUPABASE_KEY)


def _ema(values: List[float], length: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (length + 1)
    out = [values[0]]
    for v in values[1:]:
        out.append(alpha * v + (1 - alpha) * out[-1])
    return out


def _get_with_retry(url: str, params: Dict, attempts: int = 4) -> Optional[Dict]:
    last = None
    for i in range(attempts):
        try:
            r = requests.get(url, params=params, timeout=15)
            return r.json()
        except Exception as e:
            last = e
            if i < attempts - 1:
                time.sleep(1.5 * (2 ** i))
    print(f"  ⚠️ GET fail after {attempts}: {last}")
    return None


def _fetch_hist_klines(pair: str, end_ms: int, count: int = 52) -> Optional[List[float]]:
    """Fetch `count` 1H klines ending at end_ms. Returns list of closes of CLOSED candles only."""
    kd = _get_with_retry(
        "https://api.binance.com/api/v3/klines",
        {"symbol": pair, "interval": "1h", "endTime": end_ms, "limit": count},
    )
    if not isinstance(kd, list) or len(kd) < 51:
        return None
    closed = [k for k in kd if int(k[6]) <= end_ms]
    if len(closed) < 51:
        return None
    return [float(k[4]) for k in closed[-51:]]


def _fetch_hist_24h_change(pair: str, end_ms: int) -> Optional[float]:
    """24h change at end_ms: close vs close 24 candles ago on the closed stream."""
    kd = _get_with_retry(
        "https://api.binance.com/api/v3/klines",
        {"symbol": pair, "interval": "1h", "endTime": end_ms, "limit": 26},
    )
    if not isinstance(kd, list) or len(kd) < 25:
        return None
    closed = [k for k in kd if int(k[6]) <= end_ms][-25:]
    if len(closed) < 25:
        return None
    c_now = float(closed[-1][4])
    c_24h_ago = float(closed[0][4])
    if c_24h_ago <= 0:
        return None
    return round((c_now / c_24h_ago - 1) * 100, 2)


def compute_hist_trend(pair: str, at_ms: int) -> Dict:
    closes = _fetch_hist_klines(pair, at_ms)
    chg = _fetch_hist_24h_change(pair, at_ms)

    structural = 0
    close = ema20 = ema50 = slope_pct = None
    if closes and len(closes) >= 51:
        e20 = _ema(closes, 20)
        e50 = _ema(closes, 50)
        close, ema20, ema50 = closes[-1], e20[-1], e50[-1]
        slope_pct = (e20[-1] - e20[-6]) / e20[-6] * 100 if e20[-6] > 0 else 0
        if close > ema20 > ema50 and slope_pct > 0:
            structural = 2
        elif close > ema50 and slope_pct >= -0.05:
            structural = 1
        elif close < ema20 < ema50 and slope_pct < 0:
            structural = -2
        elif close < ema50:
            structural = -1

    momentum = 0
    if chg is not None:
        if chg >= 2.0: momentum = 2
        elif chg >= 0.5: momentum = 1
        elif chg <= -2.0: momentum = -2
        elif chg <= -0.5: momentum = -1

    score = structural + momentum
    label = "BULLISH" if score >= 2 else "BULLISH_OK" if score == 1 else "NEUTRAL" if score == 0 else "BEARISH"
    return {
        "score": score, "structural": structural, "momentum": momentum,
        "label": label, "bullish": score >= 0,
        "close": round(close, 4) if close else None,
        "ema20": round(ema20, 4) if ema20 else None,
        "ema50": round(ema50, 4) if ema50 else None,
        "slope_pct": round(slope_pct, 3) if slope_pct is not None else None,
        "change_24h": chg,
    }


def hour_bucket_ms(iso: str) -> int:
    """Round timestamp down to hour bucket (ms) + 1h to get "endTime = start of alert hour"."""
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    dt = dt.replace(minute=0, second=0, microsecond=0)
    return int(dt.timestamp() * 1000)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--hours", type=int, default=78)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=10000)
    args = p.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat()
    print(f"🔎 Fetching agent_memory rows since {since[:19]}Z …")

    rows: List[Dict] = []
    page_size = 1000
    start = 0
    while start < args.limit:
        r = sb.table("agent_memory") \
            .select("id,pair,timestamp,features_fingerprint") \
            .gte("timestamp", since) \
            .order("timestamp", desc=False) \
            .range(start, start + page_size - 1).execute()
        batch = r.data or []
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    print(f"📦 Loaded {len(rows)} rows")

    # Group by hour bucket — one trend computation per bucket
    buckets: Dict[int, List[Dict]] = {}
    for row in rows:
        ts = row.get("timestamp")
        if not ts: continue
        b = hour_bucket_ms(ts)
        buckets.setdefault(b, []).append(row)
    print(f"🧮 {len(buckets)} unique hour buckets")

    # Compute trend per bucket, for BTC and ETH
    trend_by_bucket: Dict[int, Dict] = {}
    for i, bucket_ms in enumerate(sorted(buckets.keys())):
        btc = compute_hist_trend("BTCUSDT", bucket_ms)
        eth = compute_hist_trend("ETHUSDT", bucket_ms)
        trend_by_bucket[bucket_ms] = {"btc": btc, "eth": eth}
        h_iso = datetime.fromtimestamp(bucket_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        print(f"  [{i+1}/{len(buckets)}] {h_iso}  BTC={btc['label']}({btc['score']:+d})  ETH={eth['label']}({eth['score']:+d})  rows={len(buckets[bucket_ms])}")
        time.sleep(0.15)  # be gentle on Binance

    # Patch rows
    updated = 0
    skipped = 0
    for bucket_ms, rs in buckets.items():
        tr = trend_by_bucket[bucket_ms]
        btc, eth = tr["btc"], tr["eth"]
        for row in rs:
            fp = dict(row.get("features_fingerprint") or {})
            old_btc = fp.get("btc_trend_1h")
            old_eth = fp.get("eth_trend_1h")
            fp["btc_trend_1h"] = btc["label"]
            fp["btc_trend_score"] = btc["score"]
            fp["btc_trend_bullish"] = btc["bullish"]
            fp["btc_change_24h"] = btc["change_24h"]
            fp["eth_trend_1h"] = eth["label"]
            fp["eth_trend_score"] = eth["score"]
            fp["eth_trend_bullish"] = eth["bullish"]
            fp["eth_change_24h"] = eth["change_24h"]
            fp["trend_backfill_v1"] = True

            if old_btc == fp["btc_trend_1h"] and old_eth == fp["eth_trend_1h"]:
                skipped += 1
                continue

            if args.dry_run:
                print(f"  [DRY] {row['pair']} {row['timestamp'][:16]} btc:{old_btc}→{fp['btc_trend_1h']} eth:{old_eth}→{fp['eth_trend_1h']}")
            else:
                try:
                    sb.table("agent_memory").update({"features_fingerprint": fp}).eq("id", row["id"]).execute()
                except Exception as e:
                    print(f"  ❌ update fail {row['id']}: {e}")
                    continue
            updated += 1

    print()
    print(f"✅ Done. Updated={updated}  Unchanged={skipped}  Total={len(rows)}")


if __name__ == "__main__":
    main()
