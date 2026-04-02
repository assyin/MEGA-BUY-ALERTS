#!/usr/bin/env python3
"""
Backfill accumulation data for recent alerts (last 2 days).
Reads alerts from agent_memory, computes accumulation via realtime_analyze,
and updates features_fingerprint in Supabase.
"""
import sys, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add paths
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from openclaw.config import get_settings
from supabase import create_client
from api.realtime_analyze import analyze_alert_realtime

def main():
    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)

    # Fetch alerts from last 2 days
    since = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    result = sb.table("agent_memory") \
        .select("id,pair,timestamp,features_fingerprint") \
        .gte("timestamp", since) \
        .order("timestamp", desc=True) \
        .limit(500) \
        .execute()

    alerts = result.data or []
    print(f"Found {len(alerts)} alerts from last 2 days")

    updated = 0
    skipped = 0
    errors = 0

    for i, alert in enumerate(alerts):
        pair = alert.get("pair", "")
        ts = alert.get("timestamp", "")
        fp = alert.get("features_fingerprint") or {}

        # Skip if already has accumulation data
        if fp.get("accumulation_days") and fp["accumulation_days"] > 0:
            skipped += 1
            continue

        print(f"[{i+1}/{len(alerts)}] {pair} @ {ts[:16]}...", end=" ", flush=True)

        try:
            price = fp.get("price", 0)
            analysis = analyze_alert_realtime(pair, ts, price)

            acc = analysis.get("accumulation", {})
            if isinstance(acc, dict) and acc.get("detected"):
                acc_data = {
                    "accumulation_days": round(acc.get("days", 0), 1),
                    "accumulation_hours": round(acc.get("hours", 0)),
                    "accumulation_range_pct": round(acc.get("range_pct", 0), 1),
                }
            else:
                acc_data = {
                    "accumulation_days": 0,
                    "accumulation_hours": 0,
                    "accumulation_range_pct": 0,
                }

            # Update features_fingerprint
            fp.update(acc_data)
            sb.table("agent_memory") \
                .update({"features_fingerprint": fp}) \
                .eq("id", alert["id"]) \
                .execute()

            days = acc_data["accumulation_days"]
            if days > 0:
                print(f"✅ {days}j (range {acc_data['accumulation_range_pct']}%)")
            else:
                print(f"— no accumulation")
            updated += 1

        except Exception as e:
            print(f"❌ {e}")
            errors += 1

        time.sleep(0.1)  # Rate limiting

    print(f"\nDone! Updated: {updated}, Skipped (already had data): {skipped}, Errors: {errors}")

if __name__ == "__main__":
    main()
