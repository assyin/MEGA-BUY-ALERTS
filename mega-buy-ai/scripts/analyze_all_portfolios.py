#!/usr/bin/env python3
"""Generate a complete performance analysis of all portfolios V1-V9.

Queries Supabase for portfolio state + positions, computes metrics,
writes a markdown report.

Usage:
    python3 scripts/analyze_all_portfolios.py [--output PATH.md]
"""

import argparse
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


PORTFOLIO_VERSIONS = [
    ("v1", "", "TP +10% / SL -8% (fixed)"),
    ("v2", "_v2", "Trailing TP + partial close"),
    ("v3", "_v3", "95% conf | 3% × 25 pos | Timeout 48h"),
    ("v4", "_v4", "Gate: Score>=8 + VIP/HT + Green4H"),
    ("v5", "_v5", "Combo: 95% + Green4H + 24h>0%"),
    ("v6", "_v6", "Body 4H>=3% + Fixed TP+15% | 12 slots × 8% × $5K"),
    ("v7", "_v7", "Body 4H>=3% + Hybrid Trailing | TP1 50%@+10% + TP2 30%@+20% + 20% Trail"),
    ("v8", "_v8", "V6 + Ultra Filter (ADX 15-35 + BTC Bull + 24h>=1%) | Fixed TP+15%"),
    ("v9", "_v9", "V8 strategy + V7 trailing"),
]


def fetch_portfolio(sb, version: str, suffix: str) -> dict:
    """Fetch state + all positions for a single portfolio version."""
    state_table = f"openclaw_portfolio_state{suffix}"
    pos_table = f"openclaw_positions{suffix}"

    out = {"version": version, "state": None, "open": [], "closed": [], "errors": []}

    try:
        s = sb.table(state_table).select("*").eq("id", "main").single().execute()
        out["state"] = s.data
    except Exception as e:
        out["errors"].append(f"state: {type(e).__name__}: {str(e)[:80]}")

    try:
        # Fetch ALL positions (no limit) — chunk via range
        all_rows = []
        cursor = 0
        page = 1000
        while True:
            r = sb.table(pos_table).select("*").range(cursor, cursor + page - 1).execute()
            chunk = r.data or []
            all_rows.extend(chunk)
            if len(chunk) < page:
                break
            cursor += page
        out["open"] = [p for p in all_rows if p.get("status") == "OPEN"]
        out["closed"] = [p for p in all_rows if p.get("status") == "CLOSED"]
    except Exception as e:
        out["errors"].append(f"positions: {type(e).__name__}: {str(e)[:80]}")

    return out


def compute_stats(data: dict) -> dict:
    """Compute performance metrics from raw portfolio data."""
    state = data["state"] or {}
    closed = data["closed"]
    open_pos = data["open"]

    closed_with_pnl = [p for p in closed if p.get("pnl_pct") is not None]
    pnls = [p["pnl_pct"] for p in closed_with_pnl]
    pnls_usd = [p.get("pnl_usd") or 0 for p in closed_with_pnl]
    wins = [p for p in closed_with_pnl if (p.get("pnl_pct") or 0) > 0]
    losses = [p for p in closed_with_pnl if (p.get("pnl_pct") or 0) < 0]
    breakeven = [p for p in closed_with_pnl if (p.get("pnl_pct") or 0) == 0]

    # Best / worst trades
    best = max(closed_with_pnl, key=lambda p: p.get("pnl_pct") or -999, default=None)
    worst = min(closed_with_pnl, key=lambda p: p.get("pnl_pct") or 999, default=None)

    # Top pairs by trade count
    pair_count = {}
    pair_pnl = {}
    for p in closed_with_pnl:
        pair = p.get("pair") or "?"
        pair_count[pair] = pair_count.get(pair, 0) + 1
        pair_pnl[pair] = pair_pnl.get(pair, 0) + (p.get("pnl_pct") or 0)
    top_pairs = sorted(pair_count.items(), key=lambda x: x[1], reverse=True)[:5]

    # Close reasons
    close_reasons = {}
    for p in closed_with_pnl:
        reason = p.get("close_reason") or "unknown"
        close_reasons[reason] = close_reasons.get(reason, 0) + 1

    # Open positions live PnL
    live_open_pnl = sum((p.get("pnl_pct") or 0) for p in open_pos)
    live_open_usd = sum((p.get("pnl_usd") or 0) for p in open_pos)

    return {
        "balance": state.get("balance"),
        "initial_capital": state.get("initial_capital"),
        "total_pnl_state": state.get("total_pnl"),
        "max_drawdown_pct": state.get("max_drawdown_pct"),
        "peak_balance": state.get("peak_balance"),
        "drawdown_mode": state.get("drawdown_mode"),
        "open_count": len(open_pos),
        "closed_count": len(closed_with_pnl),
        "wins": len(wins),
        "losses": len(losses),
        "breakeven": len(breakeven),
        "win_rate": (len(wins) / len(closed_with_pnl) * 100) if closed_with_pnl else 0.0,
        "avg_pnl_pct": statistics.mean(pnls) if pnls else 0.0,
        "median_pnl_pct": statistics.median(pnls) if pnls else 0.0,
        "total_pnl_usd_closed": sum(pnls_usd),
        "avg_win_pct": statistics.mean([p["pnl_pct"] for p in wins]) if wins else 0.0,
        "avg_loss_pct": statistics.mean([p["pnl_pct"] for p in losses]) if losses else 0.0,
        "best_trade": best,
        "worst_trade": worst,
        "top_pairs": top_pairs,
        "close_reasons": close_reasons,
        "live_open_pnl_pct_sum": live_open_pnl,
        "live_open_pnl_usd_sum": live_open_usd,
        "errors": data["errors"],
    }


def fmt_money(v):
    if v is None:
        return "—"
    return f"${v:,.2f}"


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v:+.2f}%"


def fmt_date(s):
    if not s:
        return "—"
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return d.strftime("%Y-%m-%d")
    except Exception:
        return s[:10]


def render_markdown(all_stats: list) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = []
    lines.append("# 📊 OpenClaw Portfolio Performance Report")
    lines.append("")
    lines.append(f"_Generated: {today}_")
    lines.append("")
    lines.append("Cumulative analysis of all 9 virtual portfolios (V1 → V9) — open positions, "
                 "closed history, win rates, drawdown, and live P&L. Capital initial: $5,000 per portfolio.")
    lines.append("")

    # ─────────────── Executive summary table ───────────────
    lines.append("## 🎯 Executive Summary")
    lines.append("")
    lines.append("| V | Strategy | Closed | WR | Avg PnL | Total PnL$ | Open | Live PnL$ | Balance | DD% |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for v, _, desc in PORTFOLIO_VERSIONS:
        s = next((x for x in all_stats if x["version"] == v), None)
        if not s:
            lines.append(f"| {v.upper()} | {desc} | — | — | — | — | — | — | — | — |")
            continue
        stats = s["stats"]
        lines.append(
            f"| **{v.upper()}** | {desc} | {stats['closed_count']} | "
            f"{stats['win_rate']:.1f}% | {fmt_pct(stats['avg_pnl_pct'])} | "
            f"{fmt_money(stats['total_pnl_usd_closed'])} | "
            f"{stats['open_count']} | {fmt_money(stats['live_open_pnl_usd_sum'])} | "
            f"{fmt_money(stats['balance'])} | {stats['max_drawdown_pct']:.2f}% |"
        )
    lines.append("")

    # ─────────────── Aggregate totals ───────────────
    total_closed = sum(s["stats"]["closed_count"] for s in all_stats)
    total_wins = sum(s["stats"]["wins"] for s in all_stats)
    total_losses = sum(s["stats"]["losses"] for s in all_stats)
    total_pnl_usd = sum(s["stats"]["total_pnl_usd_closed"] for s in all_stats)
    total_balance = sum(s["stats"]["balance"] or 0 for s in all_stats)
    total_initial = sum(s["stats"]["initial_capital"] or 5000 for s in all_stats)
    total_open = sum(s["stats"]["open_count"] for s in all_stats)
    total_live_pnl = sum(s["stats"]["live_open_pnl_usd_sum"] for s in all_stats)
    overall_wr = (total_wins / total_closed * 100) if total_closed else 0

    lines.append("### Totals across all portfolios")
    lines.append("")
    lines.append(f"- **Initial capital combined**: {fmt_money(total_initial)}")
    lines.append(f"- **Current balance combined**: {fmt_money(total_balance)} ({fmt_pct((total_balance - total_initial) / total_initial * 100 if total_initial else 0)})")
    lines.append(f"- **Closed trades total**: {total_closed} ({total_wins} wins / {total_losses} losses → WR {overall_wr:.1f}%)")
    lines.append(f"- **Realized P&L closed**: {fmt_money(total_pnl_usd)}")
    lines.append(f"- **Open positions**: {total_open} (live unrealized: {fmt_money(total_live_pnl)})")
    lines.append("")

    # ─────────────── Per-portfolio deep dive ───────────────
    lines.append("---")
    lines.append("")
    lines.append("## 📈 Per-Portfolio Deep Dive")
    lines.append("")

    for v, suffix, desc in PORTFOLIO_VERSIONS:
        s = next((x for x in all_stats if x["version"] == v), None)
        if not s:
            continue
        stats = s["stats"]
        lines.append(f"### {v.upper()} — {desc}")
        lines.append("")
        if stats["errors"]:
            lines.append(f"⚠️ Errors: {' | '.join(stats['errors'])}")
            lines.append("")

        lines.append("**State**")
        lines.append("")
        lines.append(f"- Balance: **{fmt_money(stats['balance'])}** (init: {fmt_money(stats['initial_capital'])}, peak: {fmt_money(stats['peak_balance'])})")
        lines.append(f"- Cumulative PnL (state): {fmt_money(stats['total_pnl_state'])}")
        lines.append(f"- Max drawdown: **{stats['max_drawdown_pct']:.2f}%** {'🚨 in DD mode' if stats['drawdown_mode'] else ''}")
        lines.append("")

        lines.append("**Trades stats**")
        lines.append("")
        lines.append(f"- Closed: **{stats['closed_count']}** | Open: {stats['open_count']} | Breakeven: {stats['breakeven']}")
        lines.append(f"- Wins: **{stats['wins']}** | Losses: **{stats['losses']}** → WR **{stats['win_rate']:.1f}%**")
        lines.append(f"- Avg win: **{fmt_pct(stats['avg_win_pct'])}** | Avg loss: **{fmt_pct(stats['avg_loss_pct'])}**")
        lines.append(f"- Avg PnL closed: {fmt_pct(stats['avg_pnl_pct'])} (median: {fmt_pct(stats['median_pnl_pct'])})")
        lines.append(f"- Realized PnL closed: **{fmt_money(stats['total_pnl_usd_closed'])}**")
        lines.append(f"- Live open PnL sum: {fmt_money(stats['live_open_pnl_usd_sum'])} ({fmt_pct(stats['live_open_pnl_pct_sum'])})")
        lines.append("")

        if stats["best_trade"]:
            b = stats["best_trade"]
            lines.append(f"**Best trade**: `{b.get('pair')}` {fmt_pct(b.get('pnl_pct'))} ({fmt_money(b.get('pnl_usd'))}) — {b.get('close_reason') or 'closed'} on {fmt_date(b.get('closed_at'))}")
        if stats["worst_trade"]:
            w = stats["worst_trade"]
            lines.append(f"**Worst trade**: `{w.get('pair')}` {fmt_pct(w.get('pnl_pct'))} ({fmt_money(w.get('pnl_usd'))}) — {w.get('close_reason') or 'closed'} on {fmt_date(w.get('closed_at'))}")
        lines.append("")

        if stats["top_pairs"]:
            lines.append("**Top pairs by trade count**: " + ", ".join(f"`{p}` ({n}x)" for p, n in stats["top_pairs"]))
            lines.append("")

        if stats["close_reasons"]:
            sorted_reasons = sorted(stats["close_reasons"].items(), key=lambda x: x[1], reverse=True)
            lines.append("**Close reasons**: " + ", ".join(f"{r}={n}" for r, n in sorted_reasons))
            lines.append("")

        lines.append("---")
        lines.append("")

    # ─────────────── Verdict / synthesis ───────────────
    lines.append("## 🏆 Verdict & Synthesis")
    lines.append("")

    sorted_by_pnl = sorted(all_stats, key=lambda x: x["stats"]["total_pnl_usd_closed"], reverse=True)
    sorted_by_wr = sorted([s for s in all_stats if s["stats"]["closed_count"] >= 5],
                          key=lambda x: x["stats"]["win_rate"], reverse=True)

    lines.append("### Most profitable (realized USD)")
    lines.append("")
    for i, s in enumerate(sorted_by_pnl[:3], 1):
        st = s["stats"]
        lines.append(f"{i}. **{s['version'].upper()}** — {fmt_money(st['total_pnl_usd_closed'])} on {st['closed_count']} trades (WR {st['win_rate']:.1f}%)")
    lines.append("")

    if sorted_by_wr:
        lines.append("### Highest win rate (min 5 trades)")
        lines.append("")
        for i, s in enumerate(sorted_by_wr[:3], 1):
            st = s["stats"]
            lines.append(f"{i}. **{s['version'].upper()}** — WR {st['win_rate']:.1f}% on {st['closed_count']} trades, avg {fmt_pct(st['avg_pnl_pct'])}")
        lines.append("")

    sorted_by_dd = sorted(all_stats, key=lambda x: x["stats"]["max_drawdown_pct"])
    lines.append("### Lowest drawdown (most defensive)")
    lines.append("")
    for i, s in enumerate(sorted_by_dd[:3], 1):
        st = s["stats"]
        lines.append(f"{i}. **{s['version'].upper()}** — DD {st['max_drawdown_pct']:.2f}%, balance {fmt_money(st['balance'])}")
    lines.append("")

    # Best risk-adjusted (PnL/DD ratio)
    risk_adj = []
    for s in all_stats:
        st = s["stats"]
        dd = st["max_drawdown_pct"] or 0.001
        ratio = (st["total_pnl_usd_closed"] or 0) / max(abs(dd), 0.001)
        risk_adj.append((s["version"], ratio, st))
    risk_adj.sort(key=lambda x: x[1], reverse=True)

    lines.append("### Best risk-adjusted (PnL$ / DD%)")
    lines.append("")
    for i, (v, r, st) in enumerate(risk_adj[:3], 1):
        lines.append(f"{i}. **{v.upper()}** — ratio {r:.1f} ({fmt_money(st['total_pnl_usd_closed'])} ÷ {st['max_drawdown_pct']:.2f}% DD)")
    lines.append("")

    # Final note
    lines.append("### Notes & caveats")
    lines.append("")
    lines.append("- All PnL values are computed from positions stored in Supabase tables `openclaw_positions[_v*]`.")
    lines.append("- `Live PnL$` represents unrealized P&L on currently open positions (snapshot at report time).")
    lines.append("- Win rate is calculated over closed trades only; PENDING/OPEN trades excluded.")
    lines.append("- Capital is virtual ($5,000 per portfolio) — these portfolios run in parallel for strategy comparison.")
    lines.append("- Some portfolios may have very few trades — interpret WR/avg figures with caution if `closed < 10`.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None, help="Output markdown path")
    args = parser.parse_args()

    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)

    all_stats = []
    for v, suffix, desc in PORTFOLIO_VERSIONS:
        print(f"  → Fetching {v} (openclaw_positions{suffix})...", flush=True)
        data = fetch_portfolio(sb, v, suffix)
        stats = compute_stats(data)
        all_stats.append({"version": v, "stats": stats})
        print(f"     {stats['closed_count']} closed, {stats['open_count']} open, WR {stats['win_rate']:.1f}%")

    md = render_markdown(all_stats)

    if args.output:
        path = Path(args.output)
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Path(__file__).parent.parent.parent / f"PORTFOLIO_ANALYSIS_{today}.md"

    path.write_text(md, encoding="utf-8")
    print()
    print(f"✅ Report written: {path}")
    print(f"   Size: {len(md)} chars, {len(md.splitlines())} lines")


if __name__ == "__main__":
    main()
