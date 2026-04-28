#!/usr/bin/env python3
"""Backfill paper_pnl_pct + paper_pnl_usd on closed V11x positions.

For each CLOSED position with paper_entry_price NOT NULL but paper_pnl_pct NULL,
compute:
    paper_pnl_pct = (exit_price - paper_entry_price) / paper_entry_price * 100
    paper_pnl_usd = size_usd * paper_pnl_pct / 100

Idempotent: re-running won't double-write because we filter on paper_pnl_pct IS NULL.
Safe: paper P&L is observational only — does not affect actual portfolio balance.

Usage: python3 scripts/backfill_paper_pnl.py [--variant v11b]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


VARIANTS = ("v11a", "v11b", "v11c", "v11d", "v11e")


def backfill_variant(sb, variant: str) -> tuple[int, int, int]:
    """Returns (scanned, eligible, updated)."""
    table = f"openclaw_positions_{variant}"
    rows = []
    cursor = 0
    while True:
        r = sb.table(table).select(
            "id,pair,exit_price,size_usd,paper_entry_price,paper_pnl_pct,status"
        ).eq("status", "CLOSED").range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000

    scanned = len(rows)
    eligible = 0
    updated = 0
    for row in rows:
        if row.get("paper_pnl_pct") is not None:
            continue  # already backfilled or computed at close
        pe = row.get("paper_entry_price")
        ex = row.get("exit_price")
        sz = row.get("size_usd")
        if pe is None or ex is None or sz is None:
            continue
        try:
            pe_f = float(pe); ex_f = float(ex); sz_f = float(sz)
        except (TypeError, ValueError):
            continue
        if pe_f <= 0 or sz_f <= 0:
            continue
        eligible += 1
        paper_pnl_pct = (ex_f - pe_f) / pe_f * 100
        paper_pnl_usd = sz_f * paper_pnl_pct / 100
        try:
            sb.table(table).update({
                "paper_pnl_pct": round(paper_pnl_pct, 2),
                "paper_pnl_usd": round(paper_pnl_usd, 2),
            }).eq("id", row["id"]).execute()
            updated += 1
        except Exception as e:
            print(f"  ⚠️ {variant.upper()} {row.get('pair')}: update failed — {e}")
    return scanned, eligible, updated


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", choices=list(VARIANTS) + ["all"], default="all")
    args = parser.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    targets = VARIANTS if args.variant == "all" else (args.variant,)
    print("Backfill paper_pnl_pct + paper_pnl_usd on closed positions")
    print("=" * 60)
    total_scanned = total_eligible = total_updated = 0
    for v in targets:
        sc, el, up = backfill_variant(sb, v)
        total_scanned += sc; total_eligible += el; total_updated += up
        print(f"  {v.upper():>5}: scanned={sc:>4}  eligible={el:>3}  updated={up:>3}")
    print("=" * 60)
    print(f"  TOTAL: scanned={total_scanned}  eligible={total_eligible}  updated={total_updated}")
    print()
    if total_eligible == 0 and total_scanned > 0:
        print("ℹ️  No eligible rows. Either:")
        print("   - paper_entry_price has not been populated yet (need new opens after T+60s)")
        print("   - or all CLOSED rows already have paper_pnl_pct (idempotent — already done)")


if __name__ == "__main__":
    main()
