#!/usr/bin/env python3
"""Test the Custom filter performance on agent_memory data."""

import sys
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from openclaw.config import get_settings
from supabase import create_client


def matches_custom(d: dict, alert_data: dict) -> bool:
    fp = d.get("features_fingerprint") or {}
    a = alert_data or {}
    score = d.get("scanner_score") or 0
    # DI+ 4H 37-50
    di_p = fp.get("di_plus_4h")
    if di_p is None or di_p < 37 or di_p > 50: return False
    # DI- 4H 0-14
    di_m = fp.get("di_minus_4h")
    if di_m is None or di_m < 0 or di_m > 14: return False
    # ADX 4H >= 15
    adx = fp.get("adx_4h")
    if adx is None or adx < 15: return False
    # DI spread 0-45
    spread = (di_p or 0) - (di_m or 0)
    if spread < 0 or spread > 45: return False
    # ADX - DI- >= 3
    if (adx - di_m) < 3: return False
    # RSI <= 79
    rsi = fp.get("rsi")
    if rsi is None or rsi > 79: return False
    # 24h change <= 36
    c24 = fp.get("change_24h_pct")
    if c24 is None or c24 > 36: return False
    # Body 4H >= 2.7
    body = fp.get("candle_4h_body_pct")
    if body is None or body < 2.7: return False
    # Range 4H 0-34
    rng = fp.get("candle_4h_range_pct")
    if rng is None or rng < 0 or rng > 34: return False
    # STC 15m>=0.1, 30m>=0.2, 1h>=0.1
    if (fp.get("stc_15m") or 0) < 0.1: return False
    if (fp.get("stc_30m") or 0) < 0.2: return False
    if (fp.get("stc_1h") or 0) < 0.1: return False
    # Direction 4H green
    if fp.get("candle_4h_direction") != "green": return False
    # PP and EC
    if not fp.get("pp"): return False
    if not fp.get("ec"): return False
    # 15m timeframe present (we don't restrict to ONLY 15m here — UI uses tfFilter=['15m'] which means "alert has 15m TF")
    tfs = fp.get("timeframes") or []
    if "15m" not in tfs: return False
    # Exclude all red vol — at least ONE vol_pct positive (>0)
    vp = a.get("vol_pct") or {}
    if isinstance(vp, dict):
        all_neg = all((v is None or v <= 0) for v in vp.values())
        if all_neg and vp: return False
    return True


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    print(f"📥 Loading agent_memory (last 30 days, resolved only)...")
    rows = []
    cursor = 0
    while True:
        r = sb.table("agent_memory").select(
            "id, pair, scanner_score, outcome, pnl_pct, pnl_max, pnl_at_close, "
            "timestamp, alert_id, features_fingerprint"
        ).gte("timestamp", cutoff).in_("outcome", ["WIN", "LOSE"]).order(
            "timestamp", desc=True
        ).range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000

    # Fetch alert_data
    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    amap = {}
    for i in range(0, len(aids), 100):
        chunk = aids[i:i+100]
        rr = sb.table("alerts").select("id,vol_pct").in_("id", chunk).execute()
        for x in (rr.data or []):
            amap[x["id"]] = x

    n = len(rows)
    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    losses = n - wins
    base_wr = wins / n * 100 if n else 0
    avg_pnl_base = sum(r.get("pnl_at_close") or 0 for r in rows) / n if n else 0

    matched = [r for r in rows if matches_custom(r, amap.get(r.get("alert_id") or ""))]
    nm = len(matched)
    wm = sum(1 for r in matched if r["outcome"] == "WIN")
    lm = nm - wm
    cust_wr = wm / nm * 100 if nm else 0
    avg_pnl_cust = sum(r.get("pnl_at_close") or 0 for r in matched) / nm if nm else 0
    avg_pnl_max_cust = sum(r.get("pnl_max") or 0 for r in matched) / nm if nm else 0

    print()
    print("━" * 60)
    print(f"📊 BASELINE (toutes alertes resolues sur 30j)")
    print(f"   Total: {n}  |  {wins}W / {losses}L  |  WR={base_wr:.1f}%")
    print(f"   Avg PnL@close: {avg_pnl_base:+.2f}%")
    print()
    print(f"🎯 FILTRE CUSTOM")
    print(f"   Matched: {nm} ({nm/n*100:.1f}% des alertes resolues)")
    print(f"   Resultat: {wm}W / {lm}L  |  WR={cust_wr:.1f}%")
    print(f"   Avg PnL@close: {avg_pnl_cust:+.2f}%")
    print(f"   Avg PnL_max:   {avg_pnl_max_cust:+.2f}%")
    print(f"   Lift WR vs baseline: {cust_wr - base_wr:+.1f} pts")
    print(f"   Lift PnL vs baseline: {avg_pnl_cust - avg_pnl_base:+.2f}%")
    print()

    # Statistical significance — binomial test
    try:
        from scipy.stats import binomtest
        if nm > 0:
            res = binomtest(wm, nm, p=base_wr/100, alternative='greater')
            print(f"   p-value (WR > baseline by chance): {res.pvalue:.4f}")
            if res.pvalue < 0.01:
                print(f"   → Statistiquement TRES significatif (p<1%)")
            elif res.pvalue < 0.05:
                print(f"   → Statistiquement significatif (p<5%)")
            else:
                print(f"   → Pas significatif statistiquement (peut etre du au hasard)")
    except ImportError:
        print("   (scipy non disponible — pas de test significatif)")

    print("━" * 60)

    # Top 10 best/worst trades from custom filter
    if matched:
        print("\n🏆 Top 5 trades GAGNANTS du filtre Custom:")
        for r in sorted([m for m in matched if m["outcome"] == "WIN"],
                        key=lambda x: x.get("pnl_max") or 0, reverse=True)[:5]:
            print(f"   {r['pair']:14s} score={r['scanner_score']} pnl_close={r.get('pnl_at_close',0):+.2f}% pnl_max={r.get('pnl_max',0):+.2f}%")
        print("\n💔 Top 5 trades PERDANTS du filtre Custom:")
        for r in sorted([m for m in matched if m["outcome"] == "LOSE"],
                        key=lambda x: x.get("pnl_at_close") or 0)[:5]:
            print(f"   {r['pair']:14s} score={r['scanner_score']} pnl_close={r.get('pnl_at_close',0):+.2f}%")


if __name__ == "__main__":
    main()
