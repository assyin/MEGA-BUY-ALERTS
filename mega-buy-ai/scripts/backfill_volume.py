"""Backfill volume spike data for existing alerts in agent_memory."""
import requests
import time
import sys
from datetime import datetime, timezone
from supabase import create_client

sb = create_client(
    'https://ejpfmquebcmwurdptqxi.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqcGZtcXVlYmNtd3VyZHB0cXhpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc2MTQ5NywiZXhwIjoyMDg3MzM3NDk3fQ.N8pck5WItWTr81UpSjJCu5wi5qd_mbPPkoJOEcuKBDM'
)

SINCE = '2026-03-31T00:00:00'
PAGE_SIZE = 500

# Paginated fetch of all alerts without volume data
offset = 0
to_fill = []
while True:
    batch = (sb.table('agent_memory')
        .select('id,pair,timestamp,features_fingerprint')
        .gte('timestamp', SINCE)
        .order('timestamp')
        .range(offset, offset + PAGE_SIZE - 1)
        .execute().data or [])
    for a in batch:
        if not (a.get('features_fingerprint') or {}).get('vol_spike_vs_1h'):
            to_fill.append(a)
    if len(batch) < PAGE_SIZE:
        break
    offset += PAGE_SIZE

print(f"Backfilling {len(to_fill)} alerts since {SINCE}...", flush=True)

updated = errors = 0
for i, a in enumerate(to_fill):
    pair = a['pair']
    ts = a['timestamp']
    fp = dict(a.get('features_fingerprint') or {})

    try:
        alert_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        end_ms = int(alert_dt.timestamp() * 1000)
        start_ms = end_ms - (48 * 3600 * 1000)

        r = requests.get("https://api.binance.com/api/v3/klines", params={
            "symbol": pair, "interval": "1h",
            "startTime": start_ms, "endTime": end_ms, "limit": 48
        }, timeout=5)
        klines = r.json()

        if not klines or not isinstance(klines, list) or len(klines) < 2:
            errors += 1
            continue

        volumes = [float(k[7]) for k in klines]
        current_vol = volumes[-1]

        def avg(vols, n):
            s = vols[-n:] if len(vols) >= n else vols
            return sum(s) / len(s) if s else 0

        prev = volumes[:-1]
        avg_1h = avg(prev, 1)
        avg_4h = avg(prev, 4)
        avg_24h = avg(prev, 24)
        avg_48h = avg(prev, len(prev))

        fp["volume_usdt"] = round(current_vol, 2)
        fp["vol_avg_1h"] = round(avg_1h, 2)
        fp["vol_avg_4h"] = round(avg_4h, 2)
        fp["vol_avg_24h"] = round(avg_24h, 2)
        fp["vol_avg_48h"] = round(avg_48h, 2)
        fp["vol_spike_vs_1h"] = round((current_vol / avg_1h - 1) * 100, 1) if avg_1h > 0 else None
        fp["vol_spike_vs_4h"] = round((current_vol / avg_4h - 1) * 100, 1) if avg_4h > 0 else None
        fp["vol_spike_vs_24h"] = round((current_vol / avg_24h - 1) * 100, 1) if avg_24h > 0 else None
        fp["vol_spike_vs_48h"] = round((current_vol / avg_48h - 1) * 100, 1) if avg_48h > 0 else None

        sb.table('agent_memory').update({"features_fingerprint": fp}).eq("id", a['id']).execute()
        updated += 1

    except Exception as e:
        errors += 1

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(to_fill)} ({(i+1)*100//len(to_fill)}%) — {updated} ok, {errors} err", flush=True)

    time.sleep(0.05)

print(f"\nDone: {updated} updated, {errors} errors out of {len(to_fill)}", flush=True)
