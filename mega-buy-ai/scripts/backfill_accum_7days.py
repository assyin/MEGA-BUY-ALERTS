#!/usr/bin/env python3
"""Backfill accumulation for ALL alerts in last 7 days that don't have it yet."""
import sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from openclaw.config import get_settings
from supabase import create_client
from api.realtime_analyze import analyze_alert_realtime

def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    # Fetch all alerts last 7 days (paginated)
    all_alerts = []
    for offset in range(0, 2000, 500):
        res = sb.table("agent_memory") \
            .select("id,pair,timestamp,features_fingerprint") \
            .gte("timestamp", since) \
            .order("timestamp", desc=True) \
            .range(offset, offset + 499) \
            .execute()
        batch = res.data or []
        all_alerts.extend(batch)
        if len(batch) < 500:
            break

    # Filter those without accumulation
    to_process = [a for a in all_alerts if not (a.get("features_fingerprint") or {}).get("accumulation_days")]
    print(f"Total alerts 7 days: {len(all_alerts)}")
    print(f"Already computed: {len(all_alerts) - len(to_process)}")
    print(f"To process: {len(to_process)}\n")

    updated = 0
    with_acc = 0
    errors = 0

    for i, alert in enumerate(to_process):
        pair = alert["pair"]
        ts = alert.get("timestamp", "")
        fp = alert.get("features_fingerprint") or {}
        price = fp.get("price", 0)

        print(f"[{i+1}/{len(to_process)}] {pair:20s} @ {ts[:16]}...", end=" ", flush=True)

        try:
            analysis = analyze_alert_realtime(pair, ts, price)
            acc = analysis.get("accumulation", {})

            if isinstance(acc, dict):
                days = acc.get("days", 0) or 0
                hours = acc.get("hours", 0) or 0
                range_pct = acc.get("range_pct", 0) or 0
            else:
                days = hours = range_pct = 0

            acc_data = {
                "accumulation_days": round(days, 1),
                "accumulation_hours": round(hours),
                "accumulation_range_pct": round(range_pct, 1),
            }
            fp.update(acc_data)
            sb.table("agent_memory").update({"features_fingerprint": fp}).eq("id", alert["id"]).execute()

            updated += 1
            if days >= 1:
                with_acc += 1
                print(f"✅ {days:.1f}j ({hours:.0f}h) range={range_pct:.1f}%")
            else:
                print(f"— {days:.1f}j")

        except Exception as e:
            errors += 1
            print(f"❌ {e}")

        time.sleep(0.05)

    print(f"\n{'='*60}")
    print(f"Done! Processed: {updated}, With accum >=1j: {with_acc}, Errors: {errors}")

if __name__ == "__main__":
    main()
