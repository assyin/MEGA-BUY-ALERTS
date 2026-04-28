#!/usr/bin/env python3
"""Backfill missed alerts into agent_memory (Option B — silencieux).

For alerts that exist in `alerts` table but have NO entry in `agent_memory`
(because openclaw was down when they arrived), this script:

  1. Fetches each alert's historical 5m klines from Binance.
  2. Computes outcome using the SAME logic as OutcomeTracker live:
       WIN   → +10% hit first
       LOSE  → -8% hit first
       EXPIRED_WIN / EXPIRED_LOSE → 7 days elapsed without threshold
       PENDING → <7j and neither threshold hit
  3. Inserts an agent_memory row with:
       - All features from the alert (price, score, indicators → features_fingerprint)
       - NO Claude analysis (agent_decision=None, agent_confidence=None)
       - Computed outcome + pnl_max/pnl_min/pnl_at_close/pnl_max_at/highest_price
       - agent_reasoning prefixed with BACKFILL_7J: (marker for rollback)

Usage:
  python3 backfill_missed_alerts_to_agent_memory.py --hours 168 --dry-run
  python3 backfill_missed_alerts_to_agent_memory.py --hours 168 --limit 3 --dry-run
  python3 backfill_missed_alerts_to_agent_memory.py --hours 168               # real run

Rollback:
  python3 backfill_missed_alerts_to_agent_memory.py --rollback
"""

import argparse
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
from openclaw.config import get_settings
from supabase import create_client

BINANCE_API = "https://api.binance.com"
WIN_THRESHOLD = 10.0
LOSE_THRESHOLD = -8.0
EXPIRY_HOURS = 168  # 7 days
BACKFILL_TAG = "BACKFILL_7J"


def get_klines(symbol: str, start_ms: int, end_ms: int) -> list:
    """Fetch 5m klines from Binance. Each kline: [openTime, open, high, low, close, ...]"""
    all_klines = []
    cursor = start_ms
    while cursor < end_ms:
        data = None
        for attempt in range(3):
            try:
                r = requests.get(
                    f"{BINANCE_API}/api/v3/klines",
                    params={"symbol": symbol, "interval": "5m",
                            "startTime": cursor, "endTime": end_ms, "limit": 1000},
                    timeout=20,
                )
                if r.status_code != 200:
                    break
                data = r.json()
                break
            except Exception as e:
                if attempt == 2:
                    print(f"    ⚠ klines error {symbol} after 3 retries: {type(e).__name__}")
                    return all_klines
                time.sleep(1.0 * (attempt + 1))
        if not data:
            break
        all_klines.extend(data)
        last_open = int(data[-1][0])
        if last_open <= cursor:
            break
        cursor = last_open + 5 * 60 * 1000
        time.sleep(0.05)
        if len(data) < 1000:
            break
    return all_klines


def compute_outcome(pair: str, entry_price: float, alert_ts: str, now_utc: datetime) -> dict:
    """Compute outcome + pnl stats from historical klines."""
    try:
        start_dt = datetime.fromisoformat(alert_ts.replace("Z", "+00:00"))
    except Exception:
        return {}

    end_dt = min(start_dt + timedelta(hours=EXPIRY_HOURS), now_utc)
    start_ms = int(start_dt.timestamp() * 1000)
    end_ms = int(end_dt.timestamp() * 1000)

    klines = get_klines(pair, start_ms, end_ms)
    if not klines:
        return {}

    pnl_max = 0.0
    pnl_min = 0.0
    highest_price = entry_price
    pnl_max_at = None
    outcome = None
    pnl_at_close = None

    # Scan klines IN ORDER — detect which threshold (WIN/LOSE) hits first
    for k in klines:
        kline_open = datetime.fromtimestamp(int(k[0]) / 1000, tz=timezone.utc)
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])

        pnl_high = (high - entry_price) / entry_price * 100
        pnl_low = (low - entry_price) / entry_price * 100

        if pnl_high > pnl_max:
            pnl_max = pnl_high
            pnl_max_at = kline_open.isoformat()
            highest_price = high
        if pnl_low < pnl_min:
            pnl_min = pnl_low

        # Threshold hit (WIN/LOSE — first hit wins)
        if outcome is None:
            if pnl_high >= WIN_THRESHOLD:
                outcome = "WIN"
                pnl_at_close = round(pnl_high, 2)
                break
            if pnl_low <= LOSE_THRESHOLD:
                outcome = "LOSE"
                pnl_at_close = round(pnl_low, 2)
                break

    # If no threshold hit, determine PENDING vs EXPIRED
    if outcome is None:
        last_close = float(klines[-1][4])
        final_pnl = (last_close - entry_price) / entry_price * 100
        hours_elapsed = (now_utc - start_dt).total_seconds() / 3600
        if hours_elapsed >= EXPIRY_HOURS:
            outcome = "EXPIRED_WIN" if final_pnl > 0 else "EXPIRED_LOSE"
            pnl_at_close = round(final_pnl, 2)
        else:
            outcome = "PENDING"
            # pnl_at_close stays None for PENDING
        final_pnl_pct = round(final_pnl, 2)
    else:
        final_pnl_pct = pnl_at_close

    return {
        "outcome": outcome,
        "pnl_pct": final_pnl_pct,
        "pnl_max": round(pnl_max, 2),
        "pnl_min": round(pnl_min, 2),
        "pnl_at_close": pnl_at_close,
        "pnl_max_at": pnl_max_at,
        "highest_price": round(highest_price, 8),
        "klines_scanned": len(klines),
    }


def build_features_fingerprint(alert: dict) -> dict:
    """Extract indicators from alert row into features_fingerprint (same shape as live)."""
    return {
        "price": alert.get("price"),
        "scanner_score": alert.get("scanner_score"),
        "timeframes": alert.get("timeframes"),
        "nb_timeframes": alert.get("nb_timeframes"),
        "emotion": alert.get("emotion"),
        "puissance": alert.get("puissance"),
        "rsi": alert.get("rsi"),
        "di_plus_4h": alert.get("di_plus_4h"),
        "di_minus_4h": alert.get("di_minus_4h"),
        "adx_4h": alert.get("adx_4h"),
        "pp": alert.get("pp"),
        "ec": alert.get("ec"),
        "choch": alert.get("choch"),
        "zone": alert.get("zone"),
        "lazy": alert.get("lazy"),
        "vol": alert.get("vol"),
        "st": alert.get("st"),
        "vol_pct": alert.get("vol_pct"),
        "body_4h": alert.get("body_4h"),
        "range_4h": alert.get("range_4h"),
        "dmi_cross_4h": alert.get("dmi_cross_4h"),
        "lazy_4h": alert.get("lazy_4h"),
        "alert_timestamp": alert.get("alert_timestamp"),
        "bougie_4h": alert.get("bougie_4h"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=168, help="Lookback hours (default 168 = 7d)")
    ap.add_argument("--limit", type=int, default=None, help="Limit how many to process")
    ap.add_argument("--dry-run", action="store_true", help="Preview only, no insert")
    ap.add_argument("--rollback", action="store_true", help="Delete all BACKFILL_7J entries")
    args = ap.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    if args.rollback:
        print(f"🔄 Rollback — deleting agent_memory rows tagged '{BACKFILL_TAG}'...")
        r = sb.table("agent_memory").delete().like("agent_reasoning", f"{BACKFILL_TAG}%").execute()
        print(f"✅ Deleted {len(r.data or [])} rows")
        return

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat()
    now_utc = datetime.now(timezone.utc)

    print(f"🔍 Fetching alerts since {cutoff}...")
    alerts_res = sb.table("alerts").select("*").gte("alert_timestamp", cutoff).limit(2000).execute()
    alerts = alerts_res.data or []
    print(f"   Found {len(alerts)} alerts in last {args.hours}h")

    mem_res = sb.table("agent_memory").select("alert_id").gte("timestamp", cutoff).limit(5000).execute()
    processed = {r["alert_id"] for r in (mem_res.data or []) if r.get("alert_id")}
    print(f"   {len(processed)} alerts already have agent_memory")

    missed = [a for a in alerts if a["id"] not in processed and a.get("price")]
    print(f"   → {len(missed)} missed alerts to backfill")

    if args.limit:
        missed = missed[:args.limit]
        print(f"   Limiting to first {len(missed)}")

    if not missed:
        print("✅ Nothing to backfill")
        return

    print()
    stats = {"WIN": 0, "LOSE": 0, "EXPIRED_WIN": 0, "EXPIRED_LOSE": 0, "PENDING": 0,
             "ERROR": 0, "INSERTED": 0, "SKIPPED": 0}
    rows_to_insert = []

    for i, alert in enumerate(missed, 1):
        pair = alert["pair"]
        entry = float(alert["price"])
        alert_ts = alert["alert_timestamp"]
        score = alert.get("scanner_score")

        print(f"[{i}/{len(missed)}] {pair:14s} score={score} price={entry:<10} ts={alert_ts[:19]}", end=" ")

        oc = compute_outcome(pair, entry, alert_ts, now_utc)
        if not oc:
            print("→ ⚠ no klines")
            stats["ERROR"] += 1
            continue

        tag = oc["outcome"]
        stats[tag] = stats.get(tag, 0) + 1

        pnl_str = f"{oc['pnl_pct']:+.1f}%" if oc["pnl_pct"] is not None else "—"
        max_str = f"max={oc['pnl_max']:+.1f}%" if oc["pnl_max"] else ""
        print(f"→ {tag:13s} {pnl_str:8s} {max_str}  ({oc['klines_scanned']} klines)")

        row = {
            "alert_id": alert["id"],
            "pair": pair,
            "timestamp": alert_ts,
            "scanner_score": score,
            "features_fingerprint": build_features_fingerprint(alert),
            "agent_decision": "BACKFILL",
            "agent_confidence": 0.0,
            "agent_reasoning": f"{BACKFILL_TAG}: openclaw down at signal time. Outcome computed from Binance klines @ {now_utc.strftime('%Y-%m-%d %H:%M')}.",
            "analysis_text": None,
            "chart_path": None,
            "outcome": oc["outcome"],
            "pnl_pct": oc["pnl_pct"],
            "pnl_max": oc["pnl_max"],
            "pnl_min": oc["pnl_min"],
            "pnl_at_close": oc["pnl_at_close"],
            "pnl_max_at": oc["pnl_max_at"],
            "highest_price": oc["highest_price"],
            "outcome_at": now_utc.isoformat() if oc["outcome"] != "PENDING" else None,
        }
        rows_to_insert.append(row)

    print()
    print("━" * 70)
    print(f"📊 Summary: {dict((k, v) for k, v in stats.items() if v > 0)}")

    resolved = stats["WIN"] + stats["LOSE"] + stats["EXPIRED_WIN"] + stats["EXPIRED_LOSE"]
    wins = stats["WIN"] + stats["EXPIRED_WIN"]
    if resolved > 0:
        wr = wins / resolved * 100
        print(f"   WR = {wins}/{resolved} = {wr:.1f}%")

    if args.dry_run:
        print(f"\n🔸 DRY RUN — {len(rows_to_insert)} rows would be inserted (not executed)")
        return

    if not rows_to_insert:
        print("Nothing to insert")
        return

    print(f"\n💾 Inserting {len(rows_to_insert)} rows in batches of 50...")
    BATCH = 50
    for i in range(0, len(rows_to_insert), BATCH):
        chunk = rows_to_insert[i:i + BATCH]
        try:
            sb.table("agent_memory").insert(chunk).execute()
            stats["INSERTED"] += len(chunk)
            print(f"   [{stats['INSERTED']}/{len(rows_to_insert)}] inserted")
        except Exception as e:
            print(f"   ⚠ batch error: {e}")
            stats["SKIPPED"] += len(chunk)

    print(f"\n✅ Done — {stats['INSERTED']} inserted, {stats['SKIPPED']} skipped")
    print(f"   Rollback: python3 {Path(__file__).name} --rollback")


if __name__ == "__main__":
    main()
