#!/usr/bin/env python3
"""Detect drift between gate_snapshot (immutable) and current features_fingerprint.

For each V11 trade, compare each snapshotted field against its current value
in agent_memory.features_fingerprint. Flag any drift to investigate root cause
of post-insertion modifications.

Output: markdown report listing all drifted alerts with the diff.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


# Numeric tolerance — small float diffs are not drift
TOLERANCE = 0.01  # 1% relative tolerance for floats

# Fields to monitor for drift (must be in snapshot)
MONITORED_FIELDS = (
    "candle_15m_range_pct", "candle_30m_range_pct",
    "candle_1h_range_pct", "candle_4h_range_pct",
    "candle_4h_body_pct", "candle_4h_direction",
    "bb_4h_width_pct", "btc_dominance",
    "accumulation_days", "accumulation_hours",
    "di_plus_4h", "di_minus_4h", "adx_4h", "rsi",
    "stc_15m", "stc_30m", "stc_1h",
)


def values_differ(a, b) -> bool:
    if a is None and b is None: return False
    if a is None or b is None: return True
    if isinstance(a, str) or isinstance(b, str):
        return str(a) != str(b)
    try:
        a = float(a); b = float(b)
        if a == b: return False
        denom = max(abs(a), abs(b), 1e-9)
        return abs(a - b) / denom > TOLERANCE
    except (ValueError, TypeError):
        return a != b


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    all_drifts = []  # (variant, pair, alert_id, field, snapshot_val, current_val, opened_at)
    total_trades = 0
    trades_with_snap = 0
    trades_with_drift = 0

    for variant in ("v11a", "v11b", "v11c", "v11d", "v11e"):
        table = f"openclaw_positions_{variant}"
        # Load all trades with gate_snapshot
        rows = []
        cursor = 0
        while True:
            r = sb.table(table).select("id,pair,alert_id,opened_at,gate_snapshot").range(cursor, cursor + 999).execute()
            chunk = r.data or []
            rows.extend(chunk)
            if len(chunk) < 1000: break
            cursor += 1000

        total_trades += len(rows)
        rows_with_snap = [r for r in rows if r.get("gate_snapshot")]
        trades_with_snap += len(rows_with_snap)
        if not rows_with_snap:
            continue

        aids = list({r["alert_id"] for r in rows_with_snap if r.get("alert_id")})
        fp_map = {}
        for i in range(0, len(aids), 100):
            rr = sb.table("agent_memory").select("alert_id,features_fingerprint").in_("alert_id", aids[i:i+100]).execute()
            for x in (rr.data or []):
                fp_map[x["alert_id"]] = x.get("features_fingerprint") or {}

        for r in rows_with_snap:
            aid = r.get("alert_id")
            snap = r.get("gate_snapshot") or {}
            fp = fp_map.get(aid, {})
            row_drifts = []
            for field in MONITORED_FIELDS:
                if field not in snap:
                    continue
                snap_val = snap.get(field)
                fp_val = fp.get(field)
                if values_differ(snap_val, fp_val):
                    row_drifts.append((field, snap_val, fp_val))
            if row_drifts:
                trades_with_drift += 1
                for field, sv, fv in row_drifts:
                    all_drifts.append({
                        "variant": variant, "pair": r.get("pair"),
                        "alert_id": aid, "opened_at": r.get("opened_at"),
                        "field": field, "snapshot": sv, "current": fv,
                    })

    # Build report
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append(f"# 🔍 FP Drift Detection — {today}")
    L.append("")
    L.append(f"Comparing `gate_snapshot` (immutable, captured at insert) vs current `features_fingerprint` for all V11 trades.")
    L.append("")
    L.append(f"- **Total V11 trades**: {total_trades}")
    L.append(f"- **Trades with snapshot**: {trades_with_snap}")
    L.append(f"- **Trades with FP drift**: **{trades_with_drift}** ({trades_with_drift/max(trades_with_snap,1)*100:.1f}%)")
    L.append(f"- **Total drift events**: {len(all_drifts)}")
    L.append("")

    if not all_drifts:
        L.append("## ✅ No drift detected")
        L.append("")
        L.append("All snapshotted fields match the current features_fingerprint values. Pipeline is stable.")
    else:
        # Group by field
        by_field = {}
        for d in all_drifts:
            by_field.setdefault(d["field"], []).append(d)

        L.append("## 📊 Drift by field")
        L.append("")
        L.append("| Field | Drift count | % of monitored |")
        L.append("|---|---:|---:|")
        for field, lst in sorted(by_field.items(), key=lambda x: len(x[1]), reverse=True):
            L.append(f"| `{field}` | {len(lst)} | {len(lst)/trades_with_snap*100:.1f}% |")
        L.append("")

        # Group by variant
        by_var = {}
        for d in all_drifts:
            by_var.setdefault(d["variant"], 0)
            by_var[d["variant"]] += 1

        L.append("## 📊 Drift by variant")
        L.append("")
        L.append("| Variant | Drift events |")
        L.append("|---|---:|")
        for v in ("v11a", "v11b", "v11c", "v11d", "v11e"):
            L.append(f"| {v.upper()} | {by_var.get(v, 0)} |")
        L.append("")

        L.append("## 📋 All drift events")
        L.append("")
        L.append("| Variant | Pair | Field | Snapshot | Current | Δ |")
        L.append("|---|---|---|---:|---:|---:|")
        for d in sorted(all_drifts, key=lambda x: (x["variant"], x["pair"])):
            sv = d["snapshot"]; cv = d["current"]
            try:
                delta = float(cv) - float(sv)
                delta_str = f"{delta:+.2f}"
            except (ValueError, TypeError):
                delta_str = "—"
            sv_s = f"{sv:.2f}" if isinstance(sv, (int, float)) else str(sv)
            cv_s = f"{cv:.2f}" if isinstance(cv, (int, float)) else (str(cv) if cv is not None else "null")
            L.append(f"| {d['variant'].upper()} | `{d['pair']}` | `{d['field']}` | {sv_s} | {cv_s} | {delta_str} |")
        L.append("")

        L.append("## 💡 Interpretation")
        L.append("")
        L.append("Drift in `features_fingerprint` AFTER trade insertion suggests one of:")
        L.append("- The `_chart_background` task in `processor.py` overwrote fields")
        L.append("- A re-run of `backfill_indicators_agent_memory.py` updated old rows")
        L.append("- Manual edits or another pipeline step")
        L.append("")
        L.append("The snapshot is the source of truth for entry conditions. The drift is informational only — the trade's entry decision was made on the snapshot, not the current FP.")

    out_path = Path(__file__).parent.parent.parent / f"FP_DRIFT_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"\n✅ Report written: {out_path}")
    print(f"   Trades scanned: {trades_with_snap}, drifted: {trades_with_drift}, drift events: {len(all_drifts)}")


if __name__ == "__main__":
    main()
