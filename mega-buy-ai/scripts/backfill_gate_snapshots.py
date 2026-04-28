#!/usr/bin/env python3
"""Backfill gate_snapshot for existing V11 trades that don't have one yet.

For each V11 trade without gate_snapshot, fetches the current
agent_memory.features_fingerprint and snapshots the relevant fields.
This creates an immutable audit trail post-hoc.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


SNAPSHOT_KEYS = (
    "candle_15m_range_pct", "candle_30m_range_pct",
    "candle_1h_range_pct", "candle_4h_range_pct",
    "candle_4h_body_pct", "candle_4h_direction",
    "bb_4h_width_pct", "btc_dominance",
    "accumulation_days", "accumulation_hours",
    "di_plus_4h", "di_minus_4h", "adx_4h", "rsi",
    "stc_15m", "stc_30m", "stc_1h", "pp", "ec",
)


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    for variant in ("v11a", "v11b", "v11c", "v11d", "v11e"):
        table = f"openclaw_positions_{variant}"
        print(f"\n━━━ {variant.upper()} ━━━", flush=True)

        # Fetch trades missing gate_snapshot
        rows = []
        cursor = 0
        while True:
            try:
                r = sb.table(table).select("id,alert_id,gate_snapshot").is_("gate_snapshot", "null").range(cursor, cursor + 999).execute()
            except Exception as e:
                print(f"  ⚠️ skip {variant}: {e}")
                break
            chunk = r.data or []
            rows.extend(chunk)
            if len(chunk) < 1000: break
            cursor += 1000
        if not rows:
            print(f"  ✅ All trades already have gate_snapshot")
            continue
        print(f"  📥 {len(rows)} trades to backfill")

        # Fetch FP for all alert_ids
        aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
        fp_map = {}
        for i in range(0, len(aids), 100):
            rr = sb.table("agent_memory").select("alert_id,features_fingerprint").in_("alert_id", aids[i:i+100]).execute()
            for x in (rr.data or []):
                fp_map[x["alert_id"]] = x.get("features_fingerprint") or {}

        updated = 0
        for r in rows:
            aid = r.get("alert_id")
            fp = fp_map.get(aid, {})
            snap = {
                "variant": variant,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "source": "post_hoc_backfill",
            }
            for k in SNAPSHOT_KEYS:
                if fp.get(k) is not None:
                    snap[k] = fp[k]
            try:
                sb.table(table).update({"gate_snapshot": snap}).eq("id", r["id"]).execute()
                updated += 1
            except Exception as e:
                print(f"    ⚠️ {r['id']}: {e}")
        print(f"  ✅ {updated} trades backfilled with gate_snapshot")


if __name__ == "__main__":
    main()
