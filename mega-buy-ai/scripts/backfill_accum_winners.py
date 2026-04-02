#!/usr/bin/env python3
"""
Compute accumulation for ALL winning trades.
Shows results sorted by accumulation duration, including < 3 days.
"""
import sys, time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from openclaw.config import get_settings
from supabase import create_client
from api.realtime_analyze import analyze_alert_realtime

def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    # Get ALL winners
    result = sb.table("agent_memory") \
        .select("id,pair,timestamp,pnl_pct,pnl_max,agent_decision,scanner_score,features_fingerprint") \
        .eq("outcome", "WIN") \
        .order("pnl_pct", desc=True) \
        .limit(300) \
        .execute()

    wins = result.data or []
    print(f"Total winners: {len(wins)}\n")

    results = []

    for i, w in enumerate(wins):
        pair = w["pair"]
        ts = w.get("timestamp", "")
        fp = w.get("features_fingerprint") or {}
        price = fp.get("price", 0)
        pnl = w.get("pnl_pct", 0) or 0
        pnl_max = w.get("pnl_max", 0) or 0
        score = w.get("scanner_score") or 0

        print(f"[{i+1}/{len(wins)}] {pair:20s} PnL={pnl:+.1f}%...", end=" ", flush=True)

        try:
            analysis = analyze_alert_realtime(pair, ts, price)
            acc = analysis.get("accumulation", {})

            if isinstance(acc, dict):
                days = acc.get("days", 0) or 0
                hours = acc.get("hours", 0) or 0
                range_pct = acc.get("range_pct", 0) or 0
                detected = acc.get("detected", False)
                vol_trend = acc.get("volume_trend", "")
                candles = acc.get("candles_4h", 0) or 0
            else:
                days = hours = range_pct = candles = 0
                detected = False
                vol_trend = ""

            results.append({
                "pair": pair,
                "pnl": pnl,
                "pnl_max": pnl_max,
                "score": score,
                "acc_days": round(days, 1),
                "acc_hours": round(hours),
                "acc_range": round(range_pct, 1),
                "acc_candles": candles,
                "vol_trend": vol_trend,
                "detected": detected,
                "is_vip": fp.get("is_vip", False),
                "id": w["id"],
            })

            # Update Supabase features_fingerprint
            acc_data = {
                "accumulation_days": round(days, 1),
                "accumulation_hours": round(hours),
                "accumulation_range_pct": round(range_pct, 1),
            }
            fp.update(acc_data)
            sb.table("agent_memory") \
                .update({"features_fingerprint": fp}) \
                .eq("id", w["id"]) \
                .execute()

            if days > 0:
                print(f"✅ {days:.1f}j ({hours:.0f}h) range={range_pct:.1f}% vol={vol_trend}")
            else:
                print(f"— 0j")

        except Exception as e:
            print(f"❌ {e}")
            results.append({
                "pair": pair, "pnl": pnl, "pnl_max": pnl_max, "score": score,
                "acc_days": 0, "acc_hours": 0, "acc_range": 0, "acc_candles": 0,
                "vol_trend": "", "detected": False, "is_vip": fp.get("is_vip", False),
                "id": w["id"],
            })

        time.sleep(0.1)

    # ─── REPORT ───
    print("\n" + "=" * 100)
    print("ACCUMULATION REPORT — ALL WINNERS")
    print("=" * 100)

    # Sort by accumulation days desc
    results.sort(key=lambda x: (-x["acc_days"], -x["pnl"]))

    with_acc = [r for r in results if r["acc_days"] > 0]
    no_acc = [r for r in results if r["acc_days"] == 0]

    print(f"\n{'Pair':20s} {'PnL':>8s} {'PnL Max':>8s} {'Score':>6s} {'Accum':>8s} {'Hours':>6s} {'Range%':>7s} {'Volume':>10s} {'VIP':>5s}")
    print("-" * 90)

    for r in results:
        vip_icon = "🏆" if r.get("is_vip") else ""
        acc_str = f"{r['acc_days']}j" if r['acc_days'] > 0 else "—"
        hours_str = f"{r['acc_hours']}h" if r['acc_hours'] > 0 else "—"
        range_str = f"{r['acc_range']}%" if r['acc_range'] > 0 else "—"
        vol_str = r['vol_trend'] if r['vol_trend'] else "—"
        print(f"{r['pair']:20s} {r['pnl']:>+7.1f}% {r['pnl_max']:>+7.1f}% {r['score']:>5}/10 {acc_str:>7s} {hours_str:>6s} {range_str:>7s} {vol_str:>10s} {vip_icon:>5s}")

    print(f"\n─── SUMMARY ───")
    print(f"Total winners: {len(results)}")
    print(f"With accumulation (>0j): {len(with_acc)} ({len(with_acc)/len(results)*100:.0f}%)")
    print(f"  >= 5 days: {len([r for r in with_acc if r['acc_days'] >= 5])}")
    print(f"  >= 3 days: {len([r for r in with_acc if r['acc_days'] >= 3])}")
    print(f"  >= 2 days: {len([r for r in with_acc if r['acc_days'] >= 2])}")
    print(f"  >= 1 day:  {len([r for r in with_acc if r['acc_days'] >= 1])}")
    print(f"  < 1 day:   {len([r for r in with_acc if r['acc_days'] < 1])}")
    print(f"No accumulation: {len(no_acc)} ({len(no_acc)/len(results)*100:.0f}%)")

    if with_acc:
        avg_pnl_acc = sum(r["pnl"] for r in with_acc) / len(with_acc)
        avg_pnl_no = sum(r["pnl"] for r in no_acc) / len(no_acc) if no_acc else 0
        print(f"\nAvg PnL with accum:    {avg_pnl_acc:+.1f}%")
        print(f"Avg PnL without accum: {avg_pnl_no:+.1f}%")

        # By accumulation tier
        for tier_name, min_d, max_d in [("< 1j", 0, 1), ("1-2j", 1, 2), ("2-3j", 2, 3), ("3-5j", 3, 5), ("5j+", 5, 999)]:
            tier = [r for r in with_acc if min_d <= r["acc_days"] < max_d]
            if tier:
                avg = sum(r["pnl"] for r in tier) / len(tier)
                print(f"  Tier {tier_name:5s}: {len(tier):3d} trades, avg PnL {avg:+.1f}%")


if __name__ == "__main__":
    main()
