#!/usr/bin/env python3
"""Backfill Tier 3 (analyze_alert structured) features into agent_memory.

For each agent_memory row in the last N hours that doesn't yet have the new
structured fields (bonus_count, fib_*, ob_*, vp_*, macd_*, stochrsi_*, bb_*,
ema_stack_*, prog_count_*, ml_p_success, adx_1h, etc.), this script:

  1. Loads the alert from Supabase.
  2. Re-runs analyze_alert_realtime (Binance klines + indicator engine).
  3. Extracts the structured features via _extract_analysis_features.
  4. Merges them into agent_memory.features_fingerprint.

NO Telegram messages. NO Claude/OpenAI calls. Just Binance public API + Supabase.

Usage:
    python3 scripts/backfill_tier3_features.py --hours 168                  # full 7 days
    python3 scripts/backfill_tier3_features.py --hours 168 --dry-run        # show what would update, no writes
    python3 scripts/backfill_tier3_features.py --hours 168 --limit 5        # cap to 5 rows for a quick test
    python3 scripts/backfill_tier3_features.py --pair FLOKIUSDT --hours 168 # only one pair
    python3 scripts/backfill_tier3_features.py --force                      # ignore "already done" detection
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backtest"))

from openclaw.config import get_settings
from openclaw.pipeline.processor import _extract_analysis_features
from supabase import create_client


# Sentinel keys that indicate the row already got its Tier 3 backfill.
# If at least one is present, we consider the row done (unless --force).
DONE_MARKERS = ("bonus_count", "prog_count_effective", "vp_1h_position", "ema_stack_4h_count")


def already_done(features: dict) -> bool:
    if not features:
        return False
    return any(k in features for k in DONE_MARKERS)


def fetch_pending(sb, *, hours: int, pair: str | None, limit: int | None,
                  force: bool) -> list:
    """Return agent_memory rows in the last N hours that need Tier 3 features.

    Strategy: 2-pass query to avoid downloading the heavy features_fingerprint blob
    for rows we'd skip anyway.
      1. Quick lightweight scan: ids + small marker key only (server-side JSON filter
         excludes rows already done, unless --force).
      2. For each pending row, fetch its full features_fingerprint individually
         right before processing (lazy, no upfront giant payload).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    pending: list = []
    cursor = 0
    page = 200
    print(f"   Cutoff: {cutoff}", flush=True)

    while True:
        q = sb.table("agent_memory").select(
            "id, pair, alert_id, timestamp"
        ).gte("timestamp", cutoff).order("timestamp", desc=True).range(cursor, cursor + page - 1)
        if pair:
            q = q.eq("pair", pair.upper())
        if not force:
            # Server-side filter: keep only rows where bonus_count IS NULL in the JSON
            q = q.is_("features_fingerprint->>bonus_count", "null")

        try:
            r = q.execute()
        except Exception as e:
            print(f"   ⚠️ supabase query error at cursor {cursor}: {type(e).__name__}: {e}", flush=True)
            break

        chunk = r.data or []
        pending.extend(chunk)
        print(f"   page {cursor}-{cursor + len(chunk)}: +{len(chunk)} pending (total: {len(pending)})", flush=True)

        if len(chunk) < page:
            break
        cursor += page
        if limit and len(pending) >= limit:
            pending = pending[:limit]
            break

    return pending


def get_alert_price(sb, alert_id: str | None, fp: dict) -> float:
    """Resolve the alert price for analyze_alert_realtime."""
    if isinstance(fp, dict) and isinstance(fp.get("price"), (int, float)):
        return float(fp["price"])
    if alert_id:
        try:
            r = sb.table("alerts").select("price").eq("id", alert_id).single().execute()
            if r.data and r.data.get("price"):
                return float(r.data["price"])
        except Exception:
            pass
    return 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168, help="Lookback window in hours (default 168 = 7 days)")
    ap.add_argument("--pair", type=str, default=None, help="Limit to a single pair (e.g. FLOKIUSDT)")
    ap.add_argument("--limit", type=int, default=None, help="Cap on number of rows to process")
    ap.add_argument("--dry-run", action="store_true", help="Don't write to Supabase, just report")
    ap.add_argument("--force", action="store_true", help="Re-process rows that already have Tier 3 features")
    ap.add_argument("--sleep", type=float, default=0.3, help="Sleep between rows to be nice to Binance (default 0.3s)")
    args = ap.parse_args()

    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)

    # Lazy import — analyze_alert_realtime pulls heavy deps; only load if we run for real
    print(f"📥 Querying agent_memory (last {args.hours}h{', pair=' + args.pair if args.pair else ''})…", flush=True)
    pending = fetch_pending(sb, hours=args.hours, pair=args.pair, limit=args.limit, force=args.force)

    if not pending:
        print("✅ Nothing to backfill (all rows already have Tier 3 features). Use --force to re-process.")
        return

    print(f"   {len(pending)} rows to backfill")
    if args.dry_run:
        for r in pending[:10]:
            print(f"   - {r['pair']:14s} ts={r.get('timestamp','?')[:19]} alert_id={r.get('alert_id','?')[:12]}")
        if len(pending) > 10:
            print(f"   … (+{len(pending) - 10} more)")
        print("\n🔸 DRY RUN — no Supabase writes")
        return

    # Real run — load the heavy analyzer once
    from api.realtime_analyze import analyze_alert_realtime

    counters = {"updated": 0, "no_features": 0, "errors": 0, "skipped": 0}
    started = time.time()

    for i, row in enumerate(pending, 1):
        pair = row["pair"]
        alert_id = row.get("alert_id")
        ts = row.get("timestamp", "")
        # Lazy-load existing features_fingerprint right before update
        fp_old = {}
        try:
            r_fp = sb.table("agent_memory").select("features_fingerprint").eq("id", row["id"]).single().execute()
            fp_old = (r_fp.data or {}).get("features_fingerprint") or {}
        except Exception:
            fp_old = {}
        price = get_alert_price(sb, alert_id, fp_old)

        prefix = f"[{i:>3}/{len(pending)}] {pair:14s}"

        try:
            full_analysis = analyze_alert_realtime(pair, ts, price)
        except Exception as e:
            print(f"{prefix} ❌ analyze error: {type(e).__name__}: {str(e)[:80]}")
            counters["errors"] += 1
            time.sleep(args.sleep)
            continue

        try:
            new_features = _extract_analysis_features(full_analysis)
        except Exception as e:
            print(f"{prefix} ❌ extract error: {type(e).__name__}: {str(e)[:80]}")
            counters["errors"] += 1
            time.sleep(args.sleep)
            continue

        if not new_features:
            print(f"{prefix} ⚠️  no Tier 3 features (analysis returned empty/error)")
            counters["no_features"] += 1
            time.sleep(args.sleep)
            continue

        merged = dict(fp_old)
        merged.update(new_features)

        try:
            sb.table("agent_memory").update({"features_fingerprint": merged}).eq("id", row["id"]).execute()
            counters["updated"] += 1
            n_new = len(new_features)
            sample = list(new_features.keys())[:3]
            print(f"{prefix} ✅ +{n_new} fields ({', '.join(sample)}…)")
        except Exception as e:
            print(f"{prefix} ❌ supabase update error: {type(e).__name__}: {str(e)[:80]}")
            counters["errors"] += 1

        time.sleep(args.sleep)

    elapsed = time.time() - started
    print()
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"📊 Summary ({elapsed:.0f}s elapsed)")
    print(f"   Updated:       {counters['updated']}")
    print(f"   No features:   {counters['no_features']}")
    print(f"   Errors:        {counters['errors']}")
    print(f"   Skipped:       {counters['skipped']}")


if __name__ == "__main__":
    main()
