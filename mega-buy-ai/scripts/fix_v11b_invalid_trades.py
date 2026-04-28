#!/usr/bin/env python3
"""Fix the 8 V11B trades flagged invalid by the audit.

Strategy:
  1. For each invalid trade, fetch the 30m and 4h candle that was ACTIVE at
     alert_timestamp from Binance (real ground truth).
  2. Compute correct candle_30m_range_pct and candle_4h_range_pct.
  3. Compare to V11B thresholds (≤1.89, ≤2.58):
     a. If TRUE values pass → trade is valid; update agent_memory FP.
     b. If TRUE values violate → trade is invalid; DELETE from V11B + adjust state.
  4. Recompute openclaw_portfolio_state_v11b totals.
"""

import sys
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


THR_R30M = 1.89
THR_R4H = 2.58


def fetch_candle_at(pair: str, interval: str, ts_iso: str) -> dict | None:
    """Fetch THE candle that contains ts_iso for the given pair/interval."""
    try:
        ts_dt = datetime.fromisoformat(ts_iso.replace("Z", "+00:00"))
    except Exception:
        return None
    end_ms = int(ts_dt.timestamp() * 1000) + 60 * 60 * 1000  # buffer
    start_ms = int(ts_dt.timestamp() * 1000) - 6 * 60 * 60 * 1000  # 6h before
    try:
        r = requests.get("https://api.binance.com/api/v3/klines", params={
            "symbol": pair, "interval": interval,
            "startTime": start_ms, "endTime": end_ms, "limit": 50,
        }, timeout=8)
        klines = r.json()
        if not isinstance(klines, list) or not klines:
            return None
    except Exception:
        return None

    target_ms = int(ts_dt.timestamp() * 1000)
    # Find the candle whose open_time <= target < open_time + interval_ms
    interval_ms_map = {"30m": 30*60*1000, "4h": 4*60*60*1000}
    interval_ms = interval_ms_map.get(interval, 0)
    chosen = None
    for k in klines:
        op = int(k[0])
        if op <= target_ms < op + interval_ms:
            chosen = k
            break
    if chosen is None:
        # Fallback: candle that closed JUST BEFORE the target
        for k in reversed(klines):
            if int(k[0]) + interval_ms <= target_ms:
                chosen = k
                break
    if chosen is None:
        return None

    o = float(chosen[1]); h = float(chosen[2]); l = float(chosen[3]); c = float(chosen[4])
    if o <= 0 or l <= 0:
        return None
    return {
        "body_pct": abs(c - o) / o * 100,
        "range_pct": (h - l) / l * 100,
        "direction": "green" if c >= o else "red",
    }


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print("📥 Loading invalid V11B trades…", flush=True)
    invalid_alert_ids = ["d80f9325", "1a30512d", "1f508566", "9a200aa5", "f27c2a1d", "22c1b836", "acf634df", "599397c4"]
    trades = []
    for prefix in invalid_alert_ids:
        r = sb.table("openclaw_positions_v11b").select("*").like("alert_id", f"{prefix}%").eq("status", "CLOSED").execute()
        for x in (r.data or []):
            trades.append(x)
    print(f"   {len(trades)} invalid trades to investigate")
    print()

    # Fetch alert_timestamp from alerts table
    aids = list({t["alert_id"] for t in trades})
    alert_ts = {}
    rr = sb.table("alerts").select("id,alert_timestamp,price").in_("id", aids).execute()
    for x in (rr.data or []):
        alert_ts[x["id"]] = x

    # For each trade: re-fetch real candle at alert time
    keep = []
    delete = []
    for t in trades:
        pair = t.get("pair")
        aid = t.get("alert_id")
        ts_info = alert_ts.get(aid, {})
        ts_iso = ts_info.get("alert_timestamp") or t.get("opened_at")
        print(f"🔬 {pair} (alert {aid[:12]}, {ts_iso[:16]})…", flush=True)

        c30 = fetch_candle_at(pair, "30m", ts_iso)
        c4 = fetch_candle_at(pair, "4h", ts_iso)
        time.sleep(0.1)

        true_r30 = c30.get("range_pct") if c30 else None
        true_r4 = c4.get("range_pct") if c4 else None
        print(f"    True range_30m = {true_r30}, True range_4h = {true_r4}")

        passes_30 = true_r30 is not None and true_r30 <= THR_R30M
        passes_4 = true_r4 is not None and true_r4 <= THR_R4H

        if passes_30 and passes_4:
            print(f"    ✅ TRUE values pass V11B gate → keep trade, update agent_memory FP")
            keep.append((t, c30, c4))
        else:
            r30_s = f"{true_r30:.2f}" if true_r30 is not None else "N/A"
            r4_s = f"{true_r4:.2f}" if true_r4 is not None else "N/A"
            print(f"    ❌ TRUE values violate gate (r30={r30_s}, r4={r4_s}) → DELETE trade")
            delete.append(t)
        print()

    # Apply fixes
    print("━" * 60)
    print(f"📊 Decision: {len(keep)} keep, {len(delete)} delete")
    print()

    # Update FP for keepers
    for t, c30, c4 in keep:
        aid = t["alert_id"]
        try:
            r = sb.table("agent_memory").select("features_fingerprint").eq("alert_id", aid).single().execute()
            fp = (r.data or {}).get("features_fingerprint") or {}
            if c30:
                fp["candle_30m_body_pct"] = round(c30["body_pct"], 2)
                fp["candle_30m_range_pct"] = round(c30["range_pct"], 2)
                fp["candle_30m_direction"] = c30["direction"]
            if c4:
                fp["candle_4h_body_pct"] = round(c4["body_pct"], 2)
                fp["candle_4h_range_pct"] = round(c4["range_pct"], 2)
                fp["candle_4h_direction"] = c4["direction"]
            sb.table("agent_memory").update({"features_fingerprint": fp}).eq("alert_id", aid).execute()
            print(f"   ✅ {t['pair']} FP corrected (r30={fp['candle_30m_range_pct']}, r4={fp['candle_4h_range_pct']})")
        except Exception as e:
            print(f"   ⚠️ {t['pair']} FP update error: {e}")

    # Delete invalid trades
    deleted_pnl = 0.0
    deleted_wins = 0
    deleted_losses = 0
    for t in delete:
        try:
            sb.table("openclaw_positions_v11b").delete().eq("id", t["id"]).execute()
            pnl = t.get("pnl_usd") or 0
            deleted_pnl += pnl
            if pnl > 0: deleted_wins += 1
            else: deleted_losses += 1
            print(f"   🗑 {t['pair']} deleted (pnl was ${pnl:+.2f})")
        except Exception as e:
            print(f"   ⚠️ {t['pair']} delete error: {e}")

    # Recompute portfolio_state_v11b
    print()
    print("📊 Recomputing portfolio_state_v11b…")
    INITIAL = 5000.0
    closed = sb.table("openclaw_positions_v11b").select("pnl_usd").eq("status", "CLOSED").execute().data or []
    total_pnl = sum((c.get("pnl_usd") or 0) for c in closed)
    wins = sum(1 for c in closed if (c.get("pnl_usd") or 0) > 0)
    losses = len(closed) - wins

    # Peak (cumulative)
    closed_sorted = sb.table("openclaw_positions_v11b").select("pnl_usd,closed_at").eq("status", "CLOSED").order("closed_at", desc=False).execute().data or []
    cum = 0; peak = 0; max_dd = 0
    for c in closed_sorted:
        cum += c.get("pnl_usd") or 0
        peak = max(peak, cum)
        dd = (peak - cum) / INITIAL * 100
        max_dd = max(max_dd, dd)

    sb.table("openclaw_portfolio_state_v11b").update({
        "balance": round(INITIAL + total_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_trades": len(closed),
        "wins": wins, "losses": losses,
        "max_drawdown_pct": round(max_dd, 2),
        "peak_balance": round(INITIAL + peak, 2),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", "main").execute()

    wr = wins/len(closed)*100 if closed else 0
    print(f"   Closed: {len(closed)} | WR: {wr:.1f}% | total PnL: ${total_pnl:+.2f} | DD: {max_dd:.2f}%")
    print(f"   Balance: ${INITIAL + total_pnl:.2f}")
    print()
    print(f"━" * 60)
    print(f"✅ Fix complete:")
    print(f"   {len(keep)} trades kept (FP corrected in agent_memory)")
    print(f"   {len(delete)} trades deleted (genuinely violated V11B gate)")
    print(f"   Deleted PnL impact: ${deleted_pnl:+.2f} ({deleted_wins}W/{deleted_losses}L)")


if __name__ == "__main__":
    main()
