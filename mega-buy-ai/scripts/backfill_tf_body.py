"""Backfill TF body/range data for existing alerts."""
import requests
import time
from datetime import datetime, timezone
from supabase import create_client

sb = create_client(
    'https://ejpfmquebcmwurdptqxi.supabase.co',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImVqcGZtcXVlYmNtd3VyZHB0cXhpIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTc2MTQ5NywiZXhwIjoyMDg3MzM3NDk3fQ.N8pck5WItWTr81UpSjJCu5wi5qd_mbPPkoJOEcuKBDM'
)

# Fetch all alerts needing backfill
offset = 0
to_fill = []
while True:
    batch = sb.table('agent_memory').select('id,pair,timestamp,features_fingerprint').gte('timestamp','2026-03-31').order('timestamp').range(offset,offset+499).execute().data or []
    for a in batch:
        fp = a.get('features_fingerprint') or {}
        tfs = fp.get('timeframes') or []
        has_tf_body = any(fp.get(f'candle_{tf}_body_pct') is not None for tf in tfs if tf in ('15m','30m','1h'))
        if tfs and not has_tf_body:
            to_fill.append(a)
    if len(batch) < 500: break
    offset += 500

print(f"Backfilling {len(to_fill)} alerts...", flush=True)

TF_MAP = {'15m': '15m', '30m': '30m', '1h': '1h', '4h': '4h'}
updated = errors = 0

for i, a in enumerate(to_fill):
    pair = a['pair']
    ts = a['timestamp']
    fp = dict(a.get('features_fingerprint') or {})
    tfs = fp.get('timeframes') or []
    changed = False

    try:
        alert_dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        end_ms = int(alert_dt.timestamp() * 1000)

        for tf in tfs:
            interval = TF_MAP.get(tf)
            if not interval or interval == '4h':
                continue  # 4h already exists

            # Fetch the candle at alert time
            r = requests.get("https://api.binance.com/api/v3/klines", params={
                "symbol": pair, "interval": interval,
                "endTime": end_ms, "limit": 1
            }, timeout=5)
            kd = r.json()

            if kd and isinstance(kd, list) and len(kd) > 0:
                o, h, l, c = float(kd[0][1]), float(kd[0][2]), float(kd[0][3]), float(kd[0][4])
                if o > 0 and l > 0:
                    fp[f"candle_{tf}_body_pct"] = round(abs(c - o) / o * 100, 2)
                    fp[f"candle_{tf}_range_pct"] = round((h - l) / l * 100, 2)
                    fp[f"candle_{tf}_direction"] = "green" if c >= o else "red"
                    changed = True

            time.sleep(0.03)  # Rate limit

        if changed:
            sb.table('agent_memory').update({"features_fingerprint": fp}).eq("id", a['id']).execute()
            updated += 1

    except Exception:
        errors += 1

    if (i + 1) % 50 == 0:
        print(f"  {i+1}/{len(to_fill)} ({(i+1)*100//len(to_fill)}%) — {updated} ok, {errors} err", flush=True)

    time.sleep(0.02)

print(f"\nDone: {updated} updated, {errors} errors out of {len(to_fill)}", flush=True)
