#!/usr/bin/env python3
"""Empirical answers to the 5 V11B recommendations + Q-A/D from second-Claude review.

Runs:
  1. Peak distribution analysis (Reco #2 — TP2 optimum)
  2. Peak timing for TIMEOUT trades (Reco #3 — timeout reduction)
  3. Per-score WR breakdown (Reco #4 — score filter)
  4. Walk-forward train/test split (Q-A — out-of-sample validation)
  5. Risk metrics : Sharpe, max DD, profit factor, consecutive losses (Q-D)
  6. WATCH vs non-WATCH WR (Reco #1)
"""

import math
import statistics
import sys
import time
import requests
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


def hold_hours(opened: str, closed: str) -> float:
    if not opened or not closed: return 0
    try:
        a = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        b = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 3600
    except Exception:
        return 0


def fetch_5m_klines(pair, start_ms, end_ms):
    out = []
    cursor = start_ms
    while cursor < end_ms:
        try:
            r = requests.get("https://api.binance.com/api/v3/klines", params={
                "symbol": pair, "interval": "5m",
                "startTime": cursor, "endTime": end_ms, "limit": 1000
            }, timeout=12)
            d = r.json()
            if not isinstance(d, list) or not d: break
        except: break
        out.extend(d)
        last = int(d[-1][0])
        if last <= cursor: break
        cursor = last + 5*60*1000
        time.sleep(0.05)
        if len(d) < 1000: break
    return out


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print("📥 Loading V11B closed trades...", flush=True)
    rows = []
    cursor = 0
    while True:
        r = sb.table("openclaw_positions_v11b").select("*").eq("status", "CLOSED").order("opened_at", desc=False).range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000
    print(f"   {len(rows)} trades")

    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    fp_map = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("agent_memory").select("alert_id,agent_decision,agent_confidence,scanner_score,features_fingerprint").in_("alert_id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            fp_map[x["alert_id"]] = x

    # Enrich
    for r in rows:
        m = fp_map.get(r.get("alert_id"), {})
        r["_decision"] = m.get("agent_decision") or "?"
        r["_score"] = m.get("scanner_score") or r.get("scanner_score") or 0
        r["_conf"] = m.get("agent_confidence")
        r["_hold_h"] = hold_hours(r.get("opened_at",""), r.get("closed_at",""))
        # Peak % vs entry
        e = r.get("entry_price", 0); h = r.get("highest_price", 0)
        r["_peak_pct"] = (h - e) / e * 100 if e else 0
        rr = (r.get("close_reason") or "").split(":",1)[1] if ":" in (r.get("close_reason") or "") else r.get("close_reason","?")
        r["_reason"] = rr
        r["_is_win"] = (r.get("pnl_usd") or 0) > 0

    # ============================================================
    # ANALYSIS #1 — Peak distribution (Reco #2)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #1 — Peak distribution (Reco #2: TP2 optimum)")
    print("═"*70)

    peaks = [r["_peak_pct"] for r in rows if r["_peak_pct"] > 0]
    tp1_peaks = [r["_peak_pct"] for r in rows if r["_peak_pct"] >= 10]  # at least touched TP1
    print(f"\nAll trades with positive peak: N={len(peaks)}")
    print(f"  Median peak: {statistics.median(peaks):.2f}%")
    print(f"  Mean peak  : {statistics.mean(peaks):.2f}%")
    print(f"\nTrades that touched TP1 (peak ≥ 10%): N={len(tp1_peaks)}")
    if tp1_peaks:
        print(f"  Median peak: {statistics.median(tp1_peaks):.2f}%")
        print(f"  Mean peak  : {statistics.mean(tp1_peaks):.2f}%")
    print(f"\n  Histogram of peaks (TP1+ trades) :")
    bins = [10, 12.5, 15, 17.5, 20, 25, 30, 40, 60, 100, 999]
    bin_labels = ["10-12.5", "12.5-15", "15-17.5", "17.5-20", "20-25", "25-30", "30-40", "40-60", "60-100", "100+"]
    bin_counts = [0] * (len(bins) - 1)
    for p in tp1_peaks:
        for i in range(len(bins) - 1):
            if bins[i] <= p < bins[i+1]:
                bin_counts[i] += 1
                break
    for label, count in zip(bin_labels, bin_counts):
        bar = "█" * int(count * 50 / max(bin_counts) if max(bin_counts) else 0)
        print(f"  {label:>10s}% : {count:>3d} {bar}")

    # Simulated PnL with different TP2 thresholds
    print(f"\n  📈 Simulated total PnL with different TP2 thresholds (TP1=10% fixed) :")
    print(f"  (Approximation: assumes peak was reached, realized = TP1 partial + TP2 partial + remaining at peak-trail8%)")
    SIZE_USD = 400
    TP1_PCT = 10; TP1_FRAC = 0.5
    TRAIL_PCT = 8
    for tp2_pct in [12, 13, 15, 17.5, 20, 22.5, 25]:
        TP2_FRAC = 0.3
        total = 0
        n_tp1 = n_tp2 = n_full_loss = 0
        for r in rows:
            peak = r["_peak_pct"]
            if peak < 10:
                # never touched TP1 — close at original close
                total += r.get("pnl_usd") or 0
                n_full_loss += 1
            elif peak < tp2_pct:
                # TP1 hit, no TP2 — assume BE-stop on remaining 50%
                total += SIZE_USD * TP1_FRAC * TP1_PCT / 100
                n_tp1 += 1
            else:
                # TP1+TP2 hit, trail on 20%
                trail_exit = peak - TRAIL_PCT
                pnl = (SIZE_USD * TP1_FRAC * TP1_PCT / 100
                       + SIZE_USD * TP2_FRAC * tp2_pct / 100
                       + SIZE_USD * (1 - TP1_FRAC - TP2_FRAC) * trail_exit / 100)
                total += pnl
                n_tp2 += 1
        print(f"  TP2={tp2_pct:>5.1f}% → total ${total:+,.2f} | {n_full_loss} no-TP1, {n_tp1} TP1-only, {n_tp2} TP2+ ")

    # ============================================================
    # ANALYSIS #2 — Peak timing for TIMEOUT_72H trades (Reco #3)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #2 — Peak timing for TIMEOUT_72H trades (Reco #3)")
    print("═"*70)

    timeouts = [r for r in rows if r["_reason"] == "TIMEOUT_72H"]
    print(f"\nTIMEOUT_72H trades: {len(timeouts)}")
    print("Fetching 5m klines to find peak timestamp...")

    bucket_counts = {"0-12h": 0, "12-24h": 0, "24-36h": 0, "36-48h": 0, "48-60h": 0, "60-72h": 0}
    timeout_with_data = 0
    skipped = 0
    avg_peak_pct_per_bucket = defaultdict(list)
    for i, r in enumerate(timeouts, 1):
        pair = r.get("pair")
        entry = r.get("entry_price", 0)
        opened = r.get("opened_at", "")
        if not pair or not entry or not opened: skipped += 1; continue
        try:
            start_dt = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        except: skipped += 1; continue
        end_dt = start_dt + timedelta(hours=72)
        klines = fetch_5m_klines(pair, int(start_dt.timestamp()*1000), int(end_dt.timestamp()*1000))
        if not klines: skipped += 1; continue

        # Find peak timestamp
        peak_h = entry; peak_t = int(start_dt.timestamp()*1000)
        for k in klines:
            h = float(k[2])
            if h > peak_h:
                peak_h = h
                peak_t = int(k[0])
        peak_pct = (peak_h - entry) / entry * 100
        peak_hours = (peak_t - int(start_dt.timestamp()*1000)) / 3600000

        # Bucket
        if peak_hours < 12: bucket = "0-12h"
        elif peak_hours < 24: bucket = "12-24h"
        elif peak_hours < 36: bucket = "24-36h"
        elif peak_hours < 48: bucket = "36-48h"
        elif peak_hours < 60: bucket = "48-60h"
        else: bucket = "60-72h"
        bucket_counts[bucket] += 1
        avg_peak_pct_per_bucket[bucket].append(peak_pct)
        timeout_with_data += 1
        if i % 20 == 0: print(f"   {i}/{len(timeouts)}", flush=True)

    print(f"\nPeak timing distribution ({timeout_with_data} TIMEOUT trades analyzed, {skipped} skipped) :")
    print(f"  Bucket  | Count | %     | Avg peak %")
    print(f"  --------|-------|-------|-----------")
    cum = 0
    for label in ["0-12h", "12-24h", "24-36h", "36-48h", "48-60h", "60-72h"]:
        n = bucket_counts[label]; cum += n
        pct = n/timeout_with_data*100 if timeout_with_data else 0
        avg_p = statistics.mean(avg_peak_pct_per_bucket[label]) if avg_peak_pct_per_bucket[label] else 0
        print(f"  {label:>7s} | {n:>5d} | {pct:>4.1f}% | {avg_p:+.2f}%")

    pct_before_48 = sum(bucket_counts[b] for b in ["0-12h","12-24h","24-36h","36-48h"]) / timeout_with_data * 100 if timeout_with_data else 0
    pct_after_48 = sum(bucket_counts[b] for b in ["48-60h","60-72h"]) / timeout_with_data * 100 if timeout_with_data else 0
    print(f"\n  PEAK avant h48 : {pct_before_48:.1f}%")
    print(f"  PEAK après h48 : {pct_after_48:.1f}%")
    if pct_after_48 < 20:
        print(f"  → ✅ Reco #3 SOLIDE : la grande majorité des peaks arrivent avant 48h")
    elif pct_after_48 < 35:
        print(f"  → 🟡 Reco #3 TRADE-OFF : on perdrait {pct_after_48:.1f}% des peaks tardifs")
    else:
        print(f"  → 🔴 Reco #3 RISQUÉE : trop de peaks après 48h ({pct_after_48:.1f}%)")

    # ============================================================
    # ANALYSIS #3 — Per-score WR (Reco #4)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #3 — Per-scanner-score WR (Reco #4)")
    print("═"*70)

    by_score = defaultdict(lambda: {"w":0, "l":0, "trades":[]})
    for r in rows:
        sc = r["_score"]
        by_score[sc]["trades"].append(r)
        if r["_is_win"]: by_score[sc]["w"] += 1
        else: by_score[sc]["l"] += 1

    print(f"\nPer-score breakdown :")
    print(f"  Score | N    | W    | L   | WR     | Avg PnL  | CI 95% Wilson")
    print(f"  ------|------|------|-----|--------|----------|---------------")
    for sc in sorted(by_score.keys()):
        d = by_score[sc]
        n = d["w"]+d["l"]
        if n == 0: continue
        wr = d["w"]/n*100
        avg_pnl = statistics.mean([t.get("pnl_pct") or 0 for t in d["trades"]]) if d["trades"] else 0
        # Wilson CI
        z = 1.96; p = wr/100
        denom = 1 + z*z/n
        center = (p + z*z/(2*n)) / denom
        margin = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denom
        ci_lo = max(0, center-margin)*100; ci_hi = min(1, center+margin)*100
        print(f"  {sc:>5} | {n:>4d} | {d['w']:>4d} | {d['l']:>3d} | {wr:>5.1f}% | {avg_pnl:+6.2f}% | [{ci_lo:>4.1f} – {ci_hi:>4.1f}%]")

    # ============================================================
    # ANALYSIS #4 — Walk-forward train/test (Q-A)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #4 — Walk-forward train/test split (Q-A)")
    print("═"*70)

    # Sort by opened_at, split 70/30
    sorted_rows = sorted(rows, key=lambda r: r.get("opened_at",""))
    split_idx = int(len(sorted_rows) * 0.7)
    train = sorted_rows[:split_idx]
    test = sorted_rows[split_idx:]

    def stats(lst):
        n = len(lst)
        w = sum(1 for r in lst if r["_is_win"])
        wr = w/n*100 if n else 0
        avg = statistics.mean([r.get("pnl_pct") or 0 for r in lst]) if lst else 0
        return n, w, n-w, wr, avg

    n1, w1, l1, wr1, avg1 = stats(train)
    n2, w2, l2, wr2, avg2 = stats(test)
    print(f"\n  Train (premiers 70%) : N={n1} | {w1}W/{l1}L | WR {wr1:.1f}% | avg PnL {avg1:+.2f}%")
    print(f"  Test  (derniers 30%) : N={n2} | {w2}W/{l2}L | WR {wr2:.1f}% | avg PnL {avg2:+.2f}%")
    print(f"  Δ WR : {wr2-wr1:+.1f}pts")
    if abs(wr2 - wr1) < 5:
        print(f"  → ✅ Stable out-of-sample : V11B tient sur les 30% les plus récents")
    elif wr2 < wr1 - 10:
        print(f"  → 🔴 Dégradation significative : suspect d'overfitting régime-dépendant")
    else:
        print(f"  → 🟡 Drift modéré : à surveiller")

    # Date range
    train_first = train[0].get("opened_at","")[:10]
    train_last = train[-1].get("opened_at","")[:10]
    test_first = test[0].get("opened_at","")[:10]
    test_last = test[-1].get("opened_at","")[:10]
    print(f"\n  Train period : {train_first} → {train_last}")
    print(f"  Test period  : {test_first} → {test_last}")

    # ============================================================
    # ANALYSIS #5 — Risk metrics (Q-D)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #5 — Risk metrics (Q-D)")
    print("═"*70)

    pnls_pct = [r.get("pnl_pct") or 0 for r in sorted_rows]
    pnls_usd = [r.get("pnl_usd") or 0 for r in sorted_rows]

    # Sharpe (per-trade, then annualize: assume avg ~6 trades/day with 199 trades / 30d)
    if pnls_pct and len(pnls_pct) > 1:
        mean_r = statistics.mean(pnls_pct)
        std_r = statistics.stdev(pnls_pct)
        sharpe_per_trade = mean_r / std_r if std_r else 0
        trades_per_year = len(pnls_pct) * (365/30)
        sharpe_annual = sharpe_per_trade * math.sqrt(trades_per_year)
        print(f"\n  Sharpe ratio (per-trade) : {sharpe_per_trade:.3f}")
        print(f"  Sharpe ratio (annualized) : {sharpe_annual:.2f}")

    # Profit factor
    sum_wins = sum(p for p in pnls_usd if p > 0)
    sum_losses = abs(sum(p for p in pnls_usd if p < 0))
    pf = sum_wins / sum_losses if sum_losses else 0
    print(f"  Profit Factor : {pf:.2f} (sum wins ${sum_wins:.0f} / |sum losses| ${sum_losses:.0f})")

    # Max consecutive losses
    cur_loss_streak = 0; max_loss_streak = 0
    cur_win_streak = 0; max_win_streak = 0
    streaks = []  # list of (type, length)
    cur_type = None; cur_len = 0
    for r in sorted_rows:
        is_w = r["_is_win"]
        if is_w:
            cur_loss_streak = 0
            cur_win_streak += 1
            max_win_streak = max(max_win_streak, cur_win_streak)
        else:
            cur_win_streak = 0
            cur_loss_streak += 1
            max_loss_streak = max(max_loss_streak, cur_loss_streak)
    print(f"  Max consecutive WINS : {max_win_streak}")
    print(f"  Max consecutive LOSSES : {max_loss_streak}")

    # Distribution of loss streaks
    streaks_lengths = []
    cur = 0
    for r in sorted_rows:
        if not r["_is_win"]:
            cur += 1
        else:
            if cur > 0: streaks_lengths.append(cur)
            cur = 0
    if cur > 0: streaks_lengths.append(cur)
    streak_dist = Counter(streaks_lengths)
    print(f"\n  Distribution des séries de pertes consécutives :")
    print(f"  Longueur | Count | Probabilité (sur tous les trades)")
    for length in sorted(streak_dist.keys()):
        c = streak_dist[length]
        prob = c / len(rows) * 100
        print(f"  {length:>8d} | {c:>5d} | {prob:.1f}%")

    # Max drawdown intra-period (cumulative balance curve)
    cum = 5000  # initial
    peak = cum
    max_dd_pct = 0
    for r in sorted_rows:
        cum += r.get("pnl_usd") or 0
        peak = max(peak, cum)
        dd = (peak - cum) / peak * 100 if peak else 0
        max_dd_pct = max(max_dd_pct, dd)
    print(f"\n  Max drawdown intra-period (en % du peak) : {max_dd_pct:.2f}%")

    # ============================================================
    # ANALYSIS #6 — WATCH vs non-WATCH (Reco #1)
    # ============================================================
    print("\n" + "═"*70)
    print("📊 ANALYSIS #6 — WATCH vs non-WATCH (Reco #1)")
    print("═"*70)

    by_decision = defaultdict(lambda: {"w":0, "l":0, "pnl":0})
    for r in rows:
        d = r["_decision"] or "?"
        if r["_is_win"]: by_decision[d]["w"] += 1
        else: by_decision[d]["l"] += 1
        by_decision[d]["pnl"] += r.get("pnl_usd") or 0

    print(f"\n  Decision | N    | WR     | Avg PnL/trade | Total PnL")
    print(f"  ---------|------|--------|---------------|-----------")
    for dec, d in sorted(by_decision.items(), key=lambda x: -(x[1]["w"]+x[1]["l"])):
        n = d["w"]+d["l"]
        if n == 0: continue
        wr = d["w"]/n*100
        avg = d["pnl"]/n if n else 0
        print(f"  {dec:>9s} | {n:>4d} | {wr:>5.1f}% | ${avg:>+7.2f}/tr | ${d['pnl']:+,.2f}")

    print("\n" + "═"*70)
    print("✅ All analyses complete")


if __name__ == "__main__":
    main()
