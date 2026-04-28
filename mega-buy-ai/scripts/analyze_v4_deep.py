#!/usr/bin/env python3
"""Deep-dive analysis of V4 portfolio.

For every closed V4 trade:
  - Joins agent_memory for entry-time features (RSI/ADX/DI+/DI-/vol_pct/fear_greed/btc_trend...)
  - Joins agent_memory.pnl_max to compute "missed upside" on winners
  - Buckets by scanner_score, confidence, hold time, BTC context

Outputs:
  - Per-trade table (every closed trade with pair, PnL, decision, conf, score, key indicators)
  - Lose pattern analysis (what's common to losses)
  - Win analysis (avg, max upside left)
  - Actionable filter proposals to add/tighten
  - Markdown report

Usage:
    python3 scripts/analyze_v4_deep.py
"""

import argparse
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


VERSION = "v4"
TABLE_POS = "openclaw_positions_v4"


def fetch_all_v4(sb) -> list:
    """Fetch every V4 position (open + closed)."""
    rows = []
    cursor = 0
    page = 1000
    while True:
        r = sb.table(TABLE_POS).select("*").range(cursor, cursor + page - 1).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < page:
            break
        cursor += page
    return rows


def fetch_agent_memory(sb, alert_ids: list) -> dict:
    """Fetch agent_memory rows for the given alert_ids; return {alert_id: row}."""
    out = {}
    if not alert_ids:
        return out
    # Supabase 'in' filter chunking — max ~200 ids per query
    chunk_size = 100
    for i in range(0, len(alert_ids), chunk_size):
        chunk = alert_ids[i:i + chunk_size]
        try:
            r = sb.table("agent_memory").select(
                "alert_id, pair, scanner_score, agent_decision, agent_confidence, "
                "outcome, pnl_pct, pnl_max, pnl_min, pnl_at_close, features_fingerprint"
            ).in_("alert_id", chunk).execute()
            for row in (r.data or []):
                aid = row.get("alert_id")
                if aid and aid not in out:
                    out[aid] = row
        except Exception as e:
            print(f"  ⚠️ fetch agent_memory chunk {i}: {type(e).__name__}: {str(e)[:80]}")
    return out


def hold_hours(opened: str, closed: str) -> float:
    if not opened or not closed:
        return 0.0
    try:
        a = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        b = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 3600
    except Exception:
        return 0.0


def fmt_pct(v):
    return f"{v:+.2f}%" if v is not None else "—"


def fmt_money(v):
    return f"${v:,.2f}" if v is not None else "—"


def fmt_dt(s):
    if not s:
        return "—"
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).strftime("%m-%d %H:%M")
    except Exception:
        return s[:16]


def get_feat(features: dict, key: str, default=None):
    if not features:
        return default
    return features.get(key, default)


def render_md(closed: list, mem_by_alert: dict) -> str:
    """Build the markdown report."""
    lines = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ─── Enrich each trade with mem features ───
    enriched = []
    for t in closed:
        aid = t.get("alert_id")
        mem = mem_by_alert.get(aid, {})
        feat = mem.get("features_fingerprint") or {}
        e = dict(t)
        e["_score_actual"] = mem.get("scanner_score") or t.get("scanner_score") or 0
        e["_decision"] = mem.get("agent_decision") or t.get("decision") or "?"
        e["_confidence"] = mem.get("agent_confidence") or t.get("confidence") or 0
        e["_pnl_max_alert"] = mem.get("pnl_max")  # peak reached after the alert
        e["_pnl_pct"] = t.get("pnl_pct") or 0
        e["_pnl_usd"] = t.get("pnl_usd") or 0
        e["_hold_h"] = hold_hours(t.get("opened_at"), t.get("closed_at"))
        e["_close_reason"] = t.get("close_reason") or "—"
        e["_di_plus"] = get_feat(feat, "di_plus_4h")
        e["_di_minus"] = get_feat(feat, "di_minus_4h")
        e["_adx"] = get_feat(feat, "adx_4h")
        e["_rsi"] = get_feat(feat, "rsi")
        e["_btc_trend"] = get_feat(feat, "btc_trend_1h", "?")
        e["_eth_trend"] = get_feat(feat, "eth_trend_1h", "?")
        e["_fg"] = get_feat(feat, "fear_greed_value")
        e["_change_24h"] = get_feat(feat, "change_24h_pct")
        e["_body_4h"] = get_feat(feat, "candle_4h_body_pct")
        e["_quality_grade"] = get_feat(feat, "quality_grade", "?")
        e["_vol_spike_4h"] = get_feat(feat, "vol_spike_vs_4h")
        e["_is_win"] = (e["_pnl_pct"] or 0) > 0
        # Missed upside = pnl_max alert - realized close (only meaningful if win)
        if e["_pnl_max_alert"] is not None and e["_pnl_pct"] is not None:
            e["_missed_pct"] = max(0, e["_pnl_max_alert"] - e["_pnl_pct"])
        else:
            e["_missed_pct"] = None
        enriched.append(e)

    wins = [e for e in enriched if e["_is_win"]]
    losses = [e for e in enriched if not e["_is_win"] and e["_pnl_pct"] is not None]

    # ─── Header ───
    lines.append("# 🔬 V4 Portfolio Deep Dive")
    lines.append("")
    lines.append(f"_Generated: {today}_")
    lines.append("")
    lines.append("**Strategy V4**: Gate Score≥8 + VIP/HT + Green4H | Champion portfolio (highest WR + highest realized PnL).")
    lines.append("")
    lines.append("Goal of this report: identify why losses happen, measure profit left on the table on winners, "
                 "and propose concrete filter/exit changes.")
    lines.append("")

    # ─── Summary ───
    lines.append("## 📊 Summary")
    lines.append("")
    total = len(enriched)
    n_w = len(wins)
    n_l = len(losses)
    wr = (n_w / total * 100) if total else 0
    avg_w = statistics.mean([w["_pnl_pct"] for w in wins]) if wins else 0
    avg_l = statistics.mean([l["_pnl_pct"] for l in losses]) if losses else 0
    sum_w_usd = sum(w["_pnl_usd"] for w in wins)
    sum_l_usd = sum(l["_pnl_usd"] for l in losses)
    avg_hold_w = statistics.mean([w["_hold_h"] for w in wins]) if wins else 0
    avg_hold_l = statistics.mean([l["_hold_h"] for l in losses]) if losses else 0
    expectancy = ((wr / 100) * avg_w) + ((1 - wr / 100) * avg_l)

    lines.append(f"- **Closed trades**: {total} ({n_w} wins, {n_l} losses, WR {wr:.1f}%)")
    lines.append(f"- **Avg win**: {fmt_pct(avg_w)} | **Avg loss**: {fmt_pct(avg_l)}")
    lines.append(f"- **Total realized**: wins {fmt_money(sum_w_usd)} / losses {fmt_money(sum_l_usd)} → net **{fmt_money(sum_w_usd + sum_l_usd)}**")
    lines.append(f"- **Avg hold time**: wins {avg_hold_w:.1f}h / losses {avg_hold_l:.1f}h")
    lines.append(f"- **Expectancy per trade**: {fmt_pct(expectancy)}")
    lines.append("")

    # ─── Missed upside on winners ───
    winners_with_max = [w for w in wins if w["_missed_pct"] is not None]
    if winners_with_max:
        avg_missed = statistics.mean([w["_missed_pct"] for w in winners_with_max])
        median_missed = statistics.median([w["_missed_pct"] for w in winners_with_max])
        winners_left_a_lot = [w for w in winners_with_max if w["_missed_pct"] >= 5]
        lines.append("### 💸 Profit left on the table (winners only)")
        lines.append("")
        lines.append(f"- Comparing **realized PnL%** vs **pnl_max** (peak the price hit during the watch window):")
        lines.append(f"- Avg missed upside: **{avg_missed:+.2f}%** (median {median_missed:+.2f}%)")
        lines.append(f"- Trades where ≥5% was left on the table: **{len(winners_left_a_lot)} / {len(winners_with_max)}**")
        if winners_left_a_lot:
            top_missed = sorted(winners_left_a_lot, key=lambda x: x["_missed_pct"], reverse=True)[:5]
            lines.append("")
            lines.append("Top 5 trades where TP exited too early:")
            lines.append("")
            for w in top_missed:
                lines.append(f"- `{w.get('pair')}` realized {fmt_pct(w['_pnl_pct'])} but peak was **{fmt_pct(w['_pnl_max_alert'])}** → missed **{w['_missed_pct']:+.2f}%** ({w['_close_reason']})")
            lines.append("")
        lines.append("> **Implication**: V4's fixed-TP exit might be leaving a chunk of the move uncaptured. "
                     "Consider a hybrid model (V7-style: TP1 partial @ +10%, TP2 partial @ +20%, trail the remainder).")
        lines.append("")

    # ─── Loss pattern analysis ───
    lines.append("## 🚨 Loss Pattern Analysis")
    lines.append("")
    if not losses:
        lines.append("No losing trades — analysis skipped.")
        lines.append("")
    else:
        # Distributions
        loss_close_reasons = Counter(l["_close_reason"] for l in losses)
        loss_btc = Counter(l["_btc_trend"] for l in losses)
        loss_pairs = Counter(l.get("pair") for l in losses)
        loss_grades = Counter(l["_quality_grade"] for l in losses)

        lines.append(f"**{n_l} losing trades** — what they have in common:")
        lines.append("")

        lines.append("**Close reasons (losses):**")
        for r, n in loss_close_reasons.most_common():
            lines.append(f"- `{r}`: {n} ({n/n_l*100:.0f}%)")
        lines.append("")

        lines.append("**BTC trend at entry (losses):**")
        for t, n in loss_btc.most_common():
            lines.append(f"- `{t}`: {n} ({n/n_l*100:.0f}%)")
        lines.append("")

        lines.append("**Quality grade distribution (losses):**")
        for g, n in loss_grades.most_common():
            lines.append(f"- Grade `{g}`: {n} ({n/n_l*100:.0f}%)")
        lines.append("")

        # Loss vs Win comparison on key features
        def avg_feature(rows, key):
            vals = [r[key] for r in rows if r.get(key) is not None]
            return statistics.mean(vals) if vals else None

        comparisons = [
            ("Scanner score", "_score_actual"),
            ("Confidence", "_confidence"),
            ("DI+ (4h)", "_di_plus"),
            ("DI- (4h)", "_di_minus"),
            ("ADX (4h)", "_adx"),
            ("RSI", "_rsi"),
            ("Body 4h %", "_body_4h"),
            ("24h change %", "_change_24h"),
            ("Vol spike vs 4h", "_vol_spike_4h"),
            ("Fear & Greed", "_fg"),
            ("Hold hours", "_hold_h"),
        ]
        lines.append("**Avg indicator at entry — Wins vs Losses:**")
        lines.append("")
        lines.append("| Feature | Avg WIN | Avg LOSS | Δ |")
        lines.append("|---|---:|---:|---:|")
        for label, key in comparisons:
            aw = avg_feature(wins, key)
            al = avg_feature(losses, key)
            if aw is None and al is None:
                continue
            delta = (aw - al) if (aw is not None and al is not None) else None
            lines.append(f"| {label} | {aw:.2f} | {al:.2f} | {delta:+.2f} |" if delta is not None
                         else f"| {label} | {aw if aw is not None else '—'} | {al if al is not None else '—'} | — |")
        lines.append("")

        # Top losing pairs
        top_loss_pairs = loss_pairs.most_common(5)
        if top_loss_pairs:
            lines.append("**Top losing pairs (recurrent losers):**")
            for p, n in top_loss_pairs:
                if n >= 2:
                    lines.append(f"- `{p}`: {n} losses")
            lines.append("")

        # Worst single losses
        worst5 = sorted(losses, key=lambda x: x["_pnl_pct"])[:5]
        lines.append("**Top 5 worst losses (deep dive):**")
        lines.append("")
        for l in worst5:
            di_p = f"{l['_di_plus']:.0f}" if l['_di_plus'] is not None else "—"
            di_m = f"{l['_di_minus']:.0f}" if l['_di_minus'] is not None else "—"
            lines.append(
                f"- `{l.get('pair')}` {fmt_pct(l['_pnl_pct'])} | score {l['_score_actual']}/10 | "
                f"conf {l['_confidence']*100:.0f}% | grade {l['_quality_grade']} | "
                f"BTC {l['_btc_trend']} | 24h {fmt_pct(l['_change_24h'])} | "
                f"DI±{di_p}/{di_m} | "
                f"hold {l['_hold_h']:.1f}h → `{l['_close_reason']}`"
            )
        lines.append("")

    # ─── Per-trade table (compact) ───
    lines.append("## 📋 Every Closed Trade")
    lines.append("")
    lines.append("Sorted by date (newest first). `Δmax` = peak after entry vs realized close.")
    lines.append("")
    lines.append("| # | Date | Pair | PnL% | PnL$ | Score | Conf | Grade | BTC | DI± | ADX | 24h% | Hold | Close | Δmax |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---|---:|")
    sorted_trades = sorted(enriched, key=lambda t: t.get("closed_at") or "", reverse=True)
    for i, t in enumerate(sorted_trades, 1):
        di_str = f"{t['_di_plus']:.0f}/{t['_di_minus']:.0f}" if t['_di_plus'] is not None and t['_di_minus'] is not None else "—"
        adx_str = f"{t['_adx']:.0f}" if t['_adx'] is not None else "—"
        miss = f"+{t['_missed_pct']:.1f}%" if t['_missed_pct'] is not None and t['_missed_pct'] > 0 else "—"
        lines.append(
            f"| {i} | {fmt_dt(t.get('closed_at'))} | `{t.get('pair')}` | "
            f"{'✅' if t['_is_win'] else '❌'} {fmt_pct(t['_pnl_pct'])} | "
            f"{fmt_money(t['_pnl_usd'])} | {t['_score_actual']} | "
            f"{t['_confidence']*100:.0f}% | {t['_quality_grade']} | "
            f"{t['_btc_trend']} | {di_str} | "
            f"{adx_str} | "
            f"{fmt_pct(t['_change_24h'])} | {t['_hold_h']:.0f}h | "
            f"{t['_close_reason']} | {miss} |"
        )
    lines.append("")

    # ─── Improvement proposals ───
    lines.append("---")
    lines.append("")
    lines.append("## 💡 Improvement Proposals")
    lines.append("")

    # Build evidence-based proposals
    proposals = []

    if losses:
        # 1. BTC bearish filter
        loss_btc_bearish = sum(1 for l in losses if l["_btc_trend"] in {"BEARISH", "DOWN"})
        win_btc_bearish = sum(1 for w in wins if w["_btc_trend"] in {"BEARISH", "DOWN"})
        if loss_btc_bearish + win_btc_bearish > 0:
            wr_in_bearish = win_btc_bearish / (loss_btc_bearish + win_btc_bearish) * 100
            if wr_in_bearish < wr - 10:
                proposals.append(
                    f"🔻 **Block trades when BTC trend = BEARISH** — current WR in BTC BEARISH context is "
                    f"{wr_in_bearish:.1f}% vs overall {wr:.1f}% (gap of {wr - wr_in_bearish:.1f} pts). "
                    f"Adding `if features.btc_trend_1h == 'BEARISH': skip` would have avoided "
                    f"{loss_btc_bearish} losses at the cost of {win_btc_bearish} wins."
                )

        # 2. Quality grade C
        loss_grade_c = sum(1 for l in losses if l["_quality_grade"] in {"C", ""})
        win_grade_c = sum(1 for w in wins if w["_quality_grade"] in {"C", ""})
        total_grade_c = loss_grade_c + win_grade_c
        if total_grade_c >= 5:
            wr_grade_c = win_grade_c / total_grade_c * 100
            if wr_grade_c < wr - 15:
                proposals.append(
                    f"🔻 **Block grade C / no-grade trades** — WR on grade C/blank is {wr_grade_c:.1f}% on {total_grade_c} trades "
                    f"vs overall {wr:.1f}%. Tightening to grade ≥ B would prune {loss_grade_c} losses for {win_grade_c} foregone wins."
                )

        # 3. Confidence threshold
        low_conf_losses = [l for l in losses if (l["_confidence"] or 0) < 0.7]
        low_conf_wins = [w for w in wins if (w["_confidence"] or 0) < 0.7]
        if len(low_conf_losses) + len(low_conf_wins) >= 5:
            wr_low = len(low_conf_wins) / (len(low_conf_losses) + len(low_conf_wins)) * 100
            if wr_low < wr - 10:
                proposals.append(
                    f"🔻 **Raise min confidence to 70%** — current WR for confidence <70% is {wr_low:.1f}% "
                    f"(vs {wr:.1f}% overall). Cutting these would remove {len(low_conf_losses)} losses for {len(low_conf_wins)} foregone wins."
                )

        # 4. ADX too weak
        weak_adx_losses = [l for l in losses if (l["_adx"] or 0) < 20]
        weak_adx_wins = [w for w in wins if (w["_adx"] or 0) < 20]
        if len(weak_adx_losses) + len(weak_adx_wins) >= 5:
            wr_weak = len(weak_adx_wins) / (len(weak_adx_losses) + len(weak_adx_wins)) * 100
            if wr_weak < wr - 10:
                proposals.append(
                    f"🔻 **Add ADX 4H ≥ 20 filter** — when ADX < 20 (no clear trend), WR drops to {wr_weak:.1f}%. "
                    f"This filter would skip {len(weak_adx_losses)} losses but also {len(weak_adx_wins)} wins."
                )

        # 5. 24h change negative
        bad_24h_losses = [l for l in losses if (l["_change_24h"] or 0) < 0]
        bad_24h_wins = [w for w in wins if (w["_change_24h"] or 0) < 0]
        if len(bad_24h_losses) + len(bad_24h_wins) >= 5:
            wr_bad24 = len(bad_24h_wins) / (len(bad_24h_losses) + len(bad_24h_wins)) * 100
            if wr_bad24 < wr - 10:
                proposals.append(
                    f"🔻 **Require 24h change ≥ 0%** — entries on red 24h candles win only {wr_bad24:.1f}% of the time. "
                    f"Currently V4 already requires 24h>0% per its strategy comment — verify the filter is actually applied "
                    f"(seeing {len(bad_24h_losses)} losses with red 24h suggests a bug or override)."
                )

    # Profit improvements
    if winners_with_max:
        avg_missed = statistics.mean([w["_missed_pct"] for w in winners_with_max])
        if avg_missed >= 3:
            proposals.append(
                f"🎯 **Migrate to V7-style hybrid TP** — winners leave {avg_missed:.1f}% on the table on average. "
                f"V7 captures more by: TP1 partial @ +10% (locks profit), TP2 partial @ +20%, trail the remainder. "
                f"Apply the same exit logic to V4's entry filter to potentially boost avg win from "
                f"{avg_w:+.2f}% toward {avg_w + avg_missed * 0.5:+.2f}%."
            )

    # Hold time disparity
    if avg_hold_l > avg_hold_w * 1.5 and n_l >= 5:
        proposals.append(
            f"⏰ **Add a time-based stop** — losses are held {avg_hold_l:.1f}h on average vs {avg_hold_w:.1f}h for wins. "
            f"Trades that stagnate beyond {avg_hold_w * 1.5:.0f}h have low win probability. "
            f"Consider auto-close at -2% if hold > {avg_hold_w * 1.5:.0f}h."
        )

    if not proposals:
        proposals.append("Nothing actionable jumped out from this dataset — V4 is performing close to its theoretical limit. "
                         "Consider scaling capital or testing the strategy on different timeframes.")

    for i, p in enumerate(proposals, 1):
        lines.append(f"{i}. {p}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## ⚙️ How to apply these")
    lines.append("")
    lines.append("V4's gate is implemented in `mega-buy-ai/openclaw/portfolio/manager_v4.py` — the entry logic checks "
                 "`scanner_score ≥ 8`, `is_vip OR is_high_ticket`, and `green_4h`. To apply a new filter:")
    lines.append("")
    lines.append("```python")
    lines.append("# In manager_v4.py, in the gate check:")
    lines.append("if features.get('btc_trend_1h') == 'BEARISH':")
    lines.append("    return None, 'BTC bearish — skip'")
    lines.append("if features.get('quality_grade') in {'C', ''}:")
    lines.append("    return None, 'Grade C — skip'")
    lines.append("```")
    lines.append("")
    lines.append("Backtest each proposed filter individually before stacking them — combining too many filters can starve the portfolio of trades.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)

    print(f"📥 Fetching all V4 positions...", flush=True)
    rows = fetch_all_v4(sb)
    closed = [r for r in rows if r.get("status") == "CLOSED"]
    print(f"   {len(rows)} total ({len(closed)} closed)")

    alert_ids = list({r.get("alert_id") for r in closed if r.get("alert_id")})
    print(f"📥 Joining agent_memory ({len(alert_ids)} alert_ids)...", flush=True)
    mem_by_alert = fetch_agent_memory(sb, alert_ids)
    print(f"   matched {len(mem_by_alert)} / {len(alert_ids)}")

    md = render_md(closed, mem_by_alert)

    if args.output:
        path = Path(args.output)
    else:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = Path(__file__).parent.parent.parent / f"V4_DEEP_ANALYSIS_{today}.md"
    path.write_text(md, encoding="utf-8")
    print(f"\n✅ Report written: {path}")
    print(f"   Size: {len(md)} chars, {len(md.splitlines())} lines")


if __name__ == "__main__":
    main()
