#!/usr/bin/env python3
"""Fix V1h/V4h/V24h/V48h for BACKFILL_7J rows.

The original backfill used full-hour volume as `_cur` (since klines were already
completed at backfill time). Live uses PARTIAL-minute volume at alert time.
This script reconstructs the partial-minute volume via 1m klines, then recomputes
vol_spike_vs_* with the same formula as live — matching LIVE behaviour exactly.

Only touches rows tagged BACKFILL_7J.

Usage:
  python3 -u scripts/fix_vol_spikes_backfill.py --dry-run
  python3 -u scripts/fix_vol_spikes_backfill.py --limit 3 --dry-run
  python3 -u scripts/fix_vol_spikes_backfill.py
"""

import argparse
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from openclaw.config import get_settings
from supabase import create_client

BINANCE_API = "https://api.binance.com"


def fetch_klines(params, retries=3):
    for i in range(retries):
        try:
            r = requests.get(f"{BINANCE_API}/api/v3/klines", params=params, timeout=20)
            if r.status_code == 200:
                return r.json() or []
            return []
        except Exception:
            if i == retries - 1:
                return None
            time.sleep(1.0 * (i + 1))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print("🔍 Fetching BACKFILL_7J rows...")
    rows = []
    page = 0
    while True:
        batch = sb.table("agent_memory").select(
            "id,pair,timestamp,features_fingerprint"
        ).like("agent_reasoning", "BACKFILL_7J%").range(page * 500, (page + 1) * 500 - 1).execute().data or []
        rows.extend(batch)
        if len(batch) < 500:
            break
        page += 1
    print(f"   Found {len(rows)} BACKFILL_7J rows")

    if args.limit:
        rows = rows[:args.limit]
        print(f"   Limiting to first {len(rows)}")

    stats = {"updated": 0, "skipped": 0, "errors": 0}

    for i, row in enumerate(rows, 1):
        pair = row["pair"]
        ts = row["timestamp"]
        fp = dict(row.get("features_fingerprint") or {})

        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            alert_ms = int(dt.timestamp() * 1000)
            hour_start = (alert_ms // 3600000) * 3600000
            mins_elapsed = int((alert_ms - hour_start) / 60000)
        except Exception:
            stats["errors"] += 1
            continue

        # 1m klines for partial current hour (0 → mins_elapsed)
        if mins_elapsed > 0:
            m_klines = fetch_klines({
                "symbol": pair, "interval": "1m",
                "startTime": hour_start, "endTime": alert_ms, "limit": 60
            })
            if m_klines is None:
                stats["errors"] += 1
                print(f"[{i}/{len(rows)}] {pair:14s} → network error")
                continue
            partial_vol = sum(float(k[7]) for k in m_klines) if m_klines else 0
        else:
            partial_vol = 0
        time.sleep(0.08)

        # 48 full previous hours (strictly before current hour)
        h_klines = fetch_klines({
            "symbol": pair, "interval": "1h",
            "endTime": hour_start - 1, "limit": 48
        })
        if h_klines is None:
            stats["errors"] += 1
            print(f"[{i}/{len(rows)}] {pair:14s} → network error")
            continue
        if not h_klines or len(h_klines) < 2:
            stats["skipped"] += 1
            print(f"[{i}/{len(rows)}] {pair:14s} → no prev klines (delisted?)")
            continue
        time.sleep(0.08)

        prev_vols = [float(k[7]) for k in h_klines]

        def avg(vv, n):
            s = vv[-n:] if len(vv) >= n else vv
            return sum(s) / len(s) if s else 0

        avg_1h = avg(prev_vols, 1)
        avg_4h = avg(prev_vols, 4)
        avg_24h = avg(prev_vols, 24)
        avg_48h = avg(prev_vols, len(prev_vols))

        new_vals = {
            "volume_usdt": round(partial_vol, 2),
            "vol_avg_1h": round(avg_1h, 2),
            "vol_avg_4h": round(avg_4h, 2),
            "vol_avg_24h": round(avg_24h, 2),
            "vol_avg_48h": round(avg_48h, 2),
            "vol_spike_vs_1h": round((partial_vol / avg_1h - 1) * 100, 1) if avg_1h > 0 else None,
            "vol_spike_vs_4h": round((partial_vol / avg_4h - 1) * 100, 1) if avg_4h > 0 else None,
            "vol_spike_vs_24h": round((partial_vol / avg_24h - 1) * 100, 1) if avg_24h > 0 else None,
            "vol_spike_vs_48h": round((partial_vol / avg_48h - 1) * 100, 1) if avg_48h > 0 else None,
        }

        old_v1h = fp.get("vol_spike_vs_1h")
        for k, v in new_vals.items():
            fp[k] = v

        print(f"[{i}/{len(rows)}] {pair:14s} ts={ts[:19]}  V1h: {old_v1h}% → {new_vals['vol_spike_vs_1h']}%  (partial {mins_elapsed}min)")

        if not args.dry_run:
            try:
                sb.table("agent_memory").update({"features_fingerprint": fp}).eq("id", row["id"]).execute()
                stats["updated"] += 1
            except Exception as e:
                print(f"    ⚠ DB error: {e}")
                stats["errors"] += 1

    print()
    print("━" * 70)
    print(f"📊 {stats}")
    if args.dry_run:
        print("🔸 DRY RUN — nothing written")


if __name__ == "__main__":
    main()
