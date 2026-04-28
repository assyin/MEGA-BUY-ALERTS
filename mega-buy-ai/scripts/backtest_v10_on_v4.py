#!/usr/bin/env python3
"""Backtest the proposed V10 strategy on V4's 69 historical trades.

Simulates:
  1. Filter calibration — for each anti-top threshold, count wins/losses
     eliminated and report net $ impact.
  2. Final V10 = optimal filters + hybrid TP/SL exits (TP1 50%@+10%,
     TP2 30%@+20%, Trail 20% at peak-5%, BE-SL after TP1, time stop 96h).
  3. Compare V4 actual vs V10 simulated.

Outputs: V10_BACKTEST_<DATE>.md
"""

import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


def hold_hours(opened: str, closed: str) -> float:
    if not opened or not closed:
        return 0.0
    try:
        a = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        b = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 3600
    except Exception:
        return 0.0


def fetch_trades_with_features(sb):
    """Return enriched closed V4 trades."""
    rows = []
    cursor = 0
    while True:
        r = sb.table("openclaw_positions_v4").select("*").range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000:
            break
        cursor += 1000
    closed = [r for r in rows if r.get("status") == "CLOSED" and r.get("pnl_pct") is not None]

    alert_ids = list({r.get("alert_id") for r in closed if r.get("alert_id")})
    mem = {}
    for i in range(0, len(alert_ids), 100):
        chunk = alert_ids[i:i+100]
        rr = sb.table("agent_memory").select(
            "alert_id, pnl_max, features_fingerprint"
        ).in_("alert_id", chunk).execute()
        for row in (rr.data or []):
            mem[row["alert_id"]] = row

    enriched = []
    for t in closed:
        m = mem.get(t.get("alert_id"), {})
        feat = m.get("features_fingerprint") or {}
        enriched.append({
            "pair": t.get("pair"),
            "pnl_pct": t.get("pnl_pct") or 0,
            "pnl_usd": t.get("pnl_usd") or 0,
            "size_usd": t.get("size_usd") or 0,
            "is_win": (t.get("pnl_pct") or 0) > 0,
            "hold_h": hold_hours(t.get("opened_at"), t.get("closed_at")),
            "close_reason": t.get("close_reason"),
            # peak reached after entry — used for hybrid TP simulation
            "pnl_max": m.get("pnl_max"),
            # features for filter simulation
            "change_24h": feat.get("change_24h_pct"),
            "vol_spike_4h": feat.get("vol_spike_vs_4h"),
            "body_4h": feat.get("candle_4h_body_pct"),
            "btc_trend": feat.get("btc_trend_1h"),
            "quality_grade": feat.get("quality_grade"),
            # confidence may live inline on the position row
            "confidence": t.get("confidence") or 0,
        })
    return enriched


# ─── Filter simulation ───────────────────────────────────────

def sim_filter(trades, predicate):
    """Apply predicate (return True=keep, False=skip) to all trades; return kept + skipped."""
    kept, skipped = [], []
    for t in trades:
        if predicate(t):
            kept.append(t)
        else:
            skipped.append(t)
    return kept, skipped


def filter_summary(skipped, label):
    n = len(skipped)
    if n == 0:
        return f"{label}: 0 trades skipped"
    w = sum(1 for t in skipped if t["is_win"])
    l = n - w
    pnl_lost = sum(t["pnl_usd"] for t in skipped if t["is_win"])
    pnl_avoided = sum(t["pnl_usd"] for t in skipped if not t["is_win"])
    net = pnl_avoided + pnl_lost  # avoided is negative number magnitude becomes negative; pnl_lost is positive
    # Re-clarify:
    # pnl_lost = sum of WINNING usd we'd skip → that's a cost (positive number we'd lose)
    # pnl_avoided = sum of LOSING usd (negative number) we'd avoid → we save its magnitude
    return (f"{label}: skipped {n} ({w}W/{l}L) | "
            f"avoided losses ${-pnl_avoided:.2f} | "
            f"forfeited wins ${pnl_lost:.2f} | "
            f"NET ${(-pnl_avoided) - pnl_lost:+.2f}")


# ─── Hybrid exit simulation ───────────────────────────────────

def sim_hybrid_exit(trade, tp1_pct=10.0, tp1_size=0.5, tp2_pct=20.0, tp2_size=0.3,
                    trail_back_pct=5.0, sl_pct=-8.0):
    """Estimate what the new V10 exit would have realized for this trade.

    Uses pnl_max (peak after entry) as the proxy for max favorable excursion.
    Returns simulated pnl_pct (on the full original position).
    """
    pnl_max = trade["pnl_max"]
    realized = trade["pnl_pct"]

    # No pnl_max info → fall back to original realized
    if pnl_max is None:
        return realized

    pnl_max = float(pnl_max)

    # Case 1: trade reached TP2 → both partials hit, trailing on the remainder
    if pnl_max >= tp2_pct:
        remainder = 1.0 - tp1_size - tp2_size
        # Conservative trail estimate: peak minus pullback
        trail_exit = pnl_max - trail_back_pct
        return tp1_size * tp1_pct + tp2_size * tp2_pct + remainder * trail_exit

    # Case 2: trade reached TP1 only → 50% locked at +10%, remainder hits BE-SL (= 0%)
    # since after TP1 the SL is moved to entry. If pnl_max stayed under tp2, eventually
    # the price dropped back and hit the BE stop.
    if pnl_max >= tp1_pct:
        remainder = 1.0 - tp1_size
        # If realized was actually a positive close above 0 (e.g., manual close), use it
        # Otherwise assume BE-stop = 0
        be_exit = max(0.0, realized) if realized < tp1_pct else 0.0
        return tp1_size * tp1_pct + remainder * be_exit

    # Case 3: trade never reached TP1
    # SL stays at -8%. If realized < -8%: trade hit SL. If realized > -8%: trade closed
    # for another reason (time stop, manual). For pnl_max < 10% we assume the original
    # close logic applies — return realized.
    return realized


def sim_v10_strategy(trades, *, max_24h, max_vol_spike, max_body, min_conf,
                     allow_btc_bearish=False, min_grade=None,
                     enable_hybrid_exit=True):
    """Apply V10 filters, then hybrid exit on survivors. Return stats dict."""
    def gate(t):
        if max_24h is not None and (t["change_24h"] is None or t["change_24h"] >= max_24h):
            return False
        if max_vol_spike is not None and (t["vol_spike_4h"] is None or t["vol_spike_4h"] >= max_vol_spike):
            return False
        if max_body is not None and (t["body_4h"] is None or t["body_4h"] >= max_body):
            return False
        if min_conf is not None and (t["confidence"] or 0) < min_conf:
            return False
        if not allow_btc_bearish and t["btc_trend"] in {"BEARISH", "DOWN"}:
            return False
        if min_grade is not None:
            grades_ok = {"A+", "A", "B"} if min_grade == "B" else {"A+", "A"}
            if t["quality_grade"] not in grades_ok:
                return False
        return True

    kept, skipped = sim_filter(trades, gate)

    if enable_hybrid_exit:
        sim_pnl = [(t, sim_hybrid_exit(t)) for t in kept]
    else:
        sim_pnl = [(t, t["pnl_pct"]) for t in kept]

    new_pnl_usd = []
    for t, sim_p in sim_pnl:
        # Convert simulated % back to USD using the original size_usd
        sz = t["size_usd"] or (t["pnl_usd"] / max(t["pnl_pct"], 1e-9) * 100 if t["pnl_pct"] else 0)
        new_pnl_usd.append(sim_p / 100 * sz)

    wins = [(t, p) for (t, p) in sim_pnl if p > 0]
    losses = [(t, p) for (t, p) in sim_pnl if p <= 0]

    return {
        "kept_count": len(kept),
        "skipped_count": len(skipped),
        "skipped_wins": sum(1 for t in skipped if t["is_win"]),
        "skipped_losses": sum(1 for t in skipped if not t["is_win"]),
        "wins": len(wins),
        "losses": len(losses),
        "wr": (len(wins) / len(kept) * 100) if kept else 0,
        "avg_win": statistics.mean([p for (_, p) in wins]) if wins else 0,
        "avg_loss": statistics.mean([p for (_, p) in losses]) if losses else 0,
        "total_usd": sum(new_pnl_usd),
        "avg_pnl_pct": statistics.mean([p for (_, p) in sim_pnl]) if sim_pnl else 0,
        "kept_trades": kept,
        "sim_pnl": sim_pnl,
    }


def baseline_stats(trades):
    wins = [t for t in trades if t["is_win"]]
    losses = [t for t in trades if not t["is_win"]]
    return {
        "n": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "wr": len(wins) / len(trades) * 100 if trades else 0,
        "avg_win": statistics.mean([t["pnl_pct"] for t in wins]) if wins else 0,
        "avg_loss": statistics.mean([t["pnl_pct"] for t in losses]) if losses else 0,
        "total_usd": sum(t["pnl_usd"] for t in trades),
    }


# ─── Threshold calibration ───────────────────────────────────

def calibrate_threshold(trades, feature_key, candidate_thresholds, direction="max"):
    """Find the threshold value that maximizes net $ saved (avoided losses - lost wins).

    direction='max' means filter is `feature < T` (kept if below).
    """
    results = []
    for t in candidate_thresholds:
        if direction == "max":
            keep_pred = lambda tr: (tr[feature_key] is not None and tr[feature_key] < t)
        else:
            keep_pred = lambda tr: (tr[feature_key] is not None and tr[feature_key] > t)
        kept, skipped = sim_filter(trades, keep_pred)
        sw = sum(1 for x in skipped if x["is_win"])
        sl = sum(1 for x in skipped if not x["is_win"])
        avoided_loss_usd = sum(x["pnl_usd"] for x in skipped if not x["is_win"])  # negative
        forfeit_win_usd = sum(x["pnl_usd"] for x in skipped if x["is_win"])         # positive
        net_usd = (-avoided_loss_usd) - forfeit_win_usd
        results.append({
            "threshold": t,
            "skipped": len(skipped),
            "skipped_w": sw,
            "skipped_l": sl,
            "kept_count": len(kept),
            "avoided_loss_usd": -avoided_loss_usd,
            "forfeit_win_usd": forfeit_win_usd,
            "net_usd": net_usd,
        })
    return results


# ─── Markdown report ─────────────────────────────────────────

def fmt(v, pct=False, money=False):
    if v is None: return "—"
    if money: return f"${v:+,.2f}"
    if pct: return f"{v:+.2f}%"
    return f"{v:.2f}"


def render_report(trades, baseline, calib, scenarios) -> str:
    L = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L.append("# 🧪 V10 Backtest on V4 Historical Trades")
    L.append("")
    L.append(f"_Generated: {today}_")
    L.append("")
    L.append(f"Backtest base: **{len(trades)} closed V4 trades**. Goal: validate that V10's anti-top filters and hybrid TP exits would have improved net P&L without sacrificing too many wins.")
    L.append("")

    # Baseline
    L.append("## 📊 V4 actual (baseline)")
    L.append("")
    L.append(f"- {baseline['n']} trades — {baseline['wins']}W / {baseline['losses']}L → **WR {baseline['wr']:.1f}%**")
    L.append(f"- Avg win {fmt(baseline['avg_win'], pct=True)} | avg loss {fmt(baseline['avg_loss'], pct=True)}")
    L.append(f"- **Total realized: {fmt(baseline['total_usd'], money=True)}**")
    L.append("")

    # Calibration tables
    L.append("---")
    L.append("")
    L.append("## 🎯 Filter threshold calibration")
    L.append("")
    L.append("For each candidate threshold: how many trades skipped? How many of those were losses (good) vs wins (bad)? Net $ impact.")
    L.append("")
    for label, results in calib.items():
        L.append(f"### {label}")
        L.append("")
        L.append("| Threshold | Skipped | Wins lost | Losses avoided | $ wins lost | $ losses avoided | NET $ |")
        L.append("|---:|---:|---:|---:|---:|---:|---:|")
        for r in results:
            L.append(f"| {r['threshold']} | {r['skipped']} | {r['skipped_w']} | {r['skipped_l']} | "
                     f"${r['forfeit_win_usd']:.2f} | ${r['avoided_loss_usd']:.2f} | **${r['net_usd']:+.2f}** |")
        L.append("")
        # best NET
        best = max(results, key=lambda x: x["net_usd"])
        L.append(f"→ **Optimal threshold: {best['threshold']}** (skips {best['skipped_l']} losses for {best['skipped_w']} wins, NET **+${best['net_usd']:.2f}**)")
        L.append("")

    # Scenario comparison
    L.append("---")
    L.append("")
    L.append("## 🔬 Strategy scenarios vs V4")
    L.append("")
    L.append("| Scenario | Kept | Wins | Losses | WR | Avg PnL | Total $ | Δ vs V4 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|---:|")
    L.append(f"| **V4 actual** | {baseline['n']} | {baseline['wins']} | {baseline['losses']} | "
             f"{baseline['wr']:.1f}% | — | {fmt(baseline['total_usd'], money=True)} | — |")
    for name, s in scenarios.items():
        delta = s["total_usd"] - baseline["total_usd"]
        L.append(f"| {name} | {s['kept_count']} | {s['wins']} | {s['losses']} | "
                 f"{s['wr']:.1f}% | {fmt(s['avg_pnl_pct'], pct=True)} | "
                 f"{fmt(s['total_usd'], money=True)} | **{fmt(delta, money=True)}** |")
    L.append("")

    # Detail of best scenario
    best_name, best_scen = max(scenarios.items(), key=lambda kv: kv[1]["total_usd"])
    L.append("---")
    L.append("")
    L.append(f"## 🏆 Best scenario detail — {best_name}")
    L.append("")
    L.append(f"**Total realized**: {fmt(best_scen['total_usd'], money=True)} (vs V4 actual {fmt(baseline['total_usd'], money=True)} → "
             f"**{fmt(best_scen['total_usd'] - baseline['total_usd'], money=True)}**)")
    L.append("")

    # Trades that benefited most from new exits (winners with hybrid exit > realized)
    boosted = []
    for t, sim_p in best_scen["sim_pnl"]:
        if t["is_win"] and sim_p > t["pnl_pct"]:
            boosted.append((t, sim_p, sim_p - t["pnl_pct"]))
    boosted.sort(key=lambda x: x[2], reverse=True)
    if boosted:
        L.append("### Top 10 winners boosted by hybrid TP")
        L.append("")
        L.append("| Pair | V4 realized | V10 simulated | Δ |")
        L.append("|---|---:|---:|---:|")
        for t, sim_p, diff in boosted[:10]:
            L.append(f"| `{t['pair']}` | {fmt(t['pnl_pct'], pct=True)} | {fmt(sim_p, pct=True)} | **+{diff:.2f}%** |")
        L.append("")

    # Note
    L.append("---")
    L.append("")
    L.append("### ⚠️ Caveats")
    L.append("")
    L.append("- Hybrid TP simulation uses `pnl_max` (peak after entry) as the proxy for the highest price reached during the watch window. The actual trail exit could have differed by a few %.")
    L.append("- Filter calibration is purely historical — past patterns may not repeat exactly. Results show the *theoretical max gain* if the filters had been perfectly applied to this 69-trade dataset.")
    L.append("- Wins lost to filtering are forfeited completely (we assume V10 would never enter them).")
    L.append("")

    return "\n".join(L)


def main():
    settings = get_settings()
    sb = create_client(settings.supabase_url, settings.supabase_service_key)

    print("📥 Loading V4 trades + agent_memory features...")
    trades = fetch_trades_with_features(sb)
    baseline = baseline_stats(trades)
    print(f"   {baseline['n']} trades — {baseline['wins']}W / {baseline['losses']}L — WR {baseline['wr']:.1f}% — total ${baseline['total_usd']:.2f}")

    # ─── Calibrate each filter individually ───
    print("\n🔬 Calibrating filter thresholds...")
    calib = {
        "Filter A — 24h change < T": calibrate_threshold(
            trades, "change_24h", [3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0]
        ),
        "Filter B — vol_spike_vs_4h < T": calibrate_threshold(
            trades, "vol_spike_4h", [150, 175, 200, 225, 250, 300]
        ),
        "Filter C — candle_4h_body_pct < T": calibrate_threshold(
            trades, "body_4h", [2.5, 3.0, 3.5, 4.0, 5.0, 6.0]
        ),
    }
    for label, results in calib.items():
        best = max(results, key=lambda r: r["net_usd"])
        print(f"   {label}: best @ T={best['threshold']} → +${best['net_usd']:.2f} (skip {best['skipped_l']}L for {best['skipped_w']}W)")

    # Pick optimal thresholds
    best_24h = max(calib["Filter A — 24h change < T"], key=lambda r: r["net_usd"])["threshold"]
    best_vol = max(calib["Filter B — vol_spike_vs_4h < T"], key=lambda r: r["net_usd"])["threshold"]
    best_body = max(calib["Filter C — candle_4h_body_pct < T"], key=lambda r: r["net_usd"])["threshold"]

    # ─── Scenarios ───
    print("\n🔬 Running scenarios...")
    scenarios = {
        "S1: hybrid exit only (no filters)": sim_v10_strategy(
            trades, max_24h=None, max_vol_spike=None, max_body=None,
            min_conf=None, allow_btc_bearish=True, min_grade=None,
            enable_hybrid_exit=True
        ),
        f"S2: filter A only (24h<{best_24h})": sim_v10_strategy(
            trades, max_24h=best_24h, max_vol_spike=None, max_body=None,
            min_conf=None, allow_btc_bearish=True, min_grade=None,
            enable_hybrid_exit=False
        ),
        f"S3: filter B only (vol<{best_vol})": sim_v10_strategy(
            trades, max_24h=None, max_vol_spike=best_vol, max_body=None,
            min_conf=None, allow_btc_bearish=True, min_grade=None,
            enable_hybrid_exit=False
        ),
        f"S4: filter C only (body<{best_body})": sim_v10_strategy(
            trades, max_24h=None, max_vol_spike=None, max_body=best_body,
            min_conf=None, allow_btc_bearish=True, min_grade=None,
            enable_hybrid_exit=False
        ),
        f"S5: V10 full (filters {best_24h}/{best_vol}/{best_body} + hybrid exit)": sim_v10_strategy(
            trades, max_24h=best_24h, max_vol_spike=best_vol, max_body=best_body,
            min_conf=None, allow_btc_bearish=True, min_grade=None,
            enable_hybrid_exit=True
        ),
        f"S6: V10 + conf>=0.70 + grade>=B": sim_v10_strategy(
            trades, max_24h=best_24h, max_vol_spike=best_vol, max_body=best_body,
            min_conf=0.70, allow_btc_bearish=True, min_grade="B",
            enable_hybrid_exit=True
        ),
    }

    for name, s in scenarios.items():
        delta = s["total_usd"] - baseline["total_usd"]
        print(f"   {name}: kept {s['kept_count']}, WR {s['wr']:.1f}%, total ${s['total_usd']:.2f} (Δ ${delta:+.2f})")

    md = render_report(trades, baseline, calib, scenarios)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = Path(__file__).parent.parent.parent / f"V10_BACKTEST_{today}.md"
    path.write_text(md, encoding="utf-8")
    print(f"\n✅ Report written: {path}")


if __name__ == "__main__":
    main()
