#!/usr/bin/env python3
"""Hydrate V11a-V11e portfolios with historical trades that match each gate.

For each V11 variant:
  1. Find agent_memory rows in last N days that pass the gate (using stored features_fingerprint)
  2. For each match: fetch 5m klines, simulate V7-style hybrid TP/SL exit
  3. Insert as CLOSED HYDRATED_BACKTEST into openclaw_positions_v11x
  4. Update openclaw_portfolio_state_v11x with running balance, peak, drawdown

Usage:
    python3 -u scripts/hydrate_v11_portfolios.py [--days 30] [--variants v11b,v11c]
"""

import argparse
import sys
import time
import uuid
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


# ─── Hybrid TP exit constants (mirror manager_v11 / V7) ─────
INITIAL_CAPITAL = 5000.0
SIZE_PCT = 8.0
SIZE_USD = INITIAL_CAPITAL * SIZE_PCT / 100  # = 400
SL_PCT = 8.0
TP1_PCT = 10.0; TP1_FRAC = 0.50
TP2_PCT = 20.0; TP2_FRAC = 0.30
TRAIL_DIST_PCT = 8.0
TIMEOUT_H = 72


# ─── Gates working on STORED features (historical) ──────────

def hist_match_v11a(fp: dict, alert: dict) -> bool:
    """V11a Custom — historical version reading from features_fingerprint + alerts row."""
    score = (fp.get("scanner_score") or alert.get("scanner_score") or 0)
    di_p = fp.get("di_plus_4h") or alert.get("di_plus_4h")
    di_m = fp.get("di_minus_4h") or alert.get("di_minus_4h")
    adx = fp.get("adx_4h") or alert.get("adx_4h")
    if di_p is None or di_p < 37 or di_p > 50: return False
    if di_m is None or di_m < 0 or di_m > 14: return False
    if adx is None or adx < 15: return False
    if (di_p - di_m) > 45: return False
    if (adx - di_m) < 3: return False
    if (fp.get("rsi") or alert.get("rsi") or 0) > 79: return False
    if (fp.get("change_24h_pct") or 0) > 36: return False
    if (fp.get("candle_4h_body_pct") or 0) < 2.7: return False
    if (fp.get("candle_4h_range_pct") or 0) > 34: return False
    if (fp.get("stc_15m") or 0) < 0.1: return False
    if (fp.get("stc_30m") or 0) < 0.2: return False
    if (fp.get("stc_1h") or 0) < 0.1: return False
    if fp.get("candle_4h_direction") != "green": return False
    if not (fp.get("pp") or alert.get("pp")): return False
    if not (fp.get("ec") or alert.get("ec")): return False
    tfs = fp.get("timeframes") or alert.get("timeframes") or []
    if "15m" not in tfs: return False
    vp = alert.get("vol_pct") or {}
    if isinstance(vp, dict) and vp:
        if all((v is None or v <= 0) for v in vp.values()):
            return False
    return True


def hist_match_v11b(fp: dict, alert: dict) -> bool:
    r30 = fp.get("candle_30m_range_pct")
    r4 = fp.get("candle_4h_range_pct")
    return r30 is not None and r4 is not None and r30 <= 1.89 and r4 <= 2.58


def hist_match_v11c(fp: dict, alert: dict) -> bool:
    r1h = fp.get("candle_1h_range_pct")
    btc_d = fp.get("btc_dominance")
    return r1h is not None and btc_d is not None and r1h <= 1.67 and btc_d <= 56.98


def hist_match_v11d(fp: dict, alert: dict) -> bool:
    days = fp.get("accumulation_days") or 0
    r30 = fp.get("candle_30m_range_pct")
    return days >= 3.7 and r30 is not None and r30 <= 1.46


def hist_match_v11e(fp: dict, alert: dict) -> bool:
    bbw = fp.get("bb_4h_width_pct")
    return bbw is not None and bbw <= 13.56


HIST_GATES = {
    "v11a": hist_match_v11a,
    "v11b": hist_match_v11b,
    "v11c": hist_match_v11c,
    "v11d": hist_match_v11d,
    "v11e": hist_match_v11e,
}

LABELS = {
    "v11a": "Custom (continuation)",
    "v11b": "Compression (R30m+R4h)",
    "v11c": "Premium (R1h+BTC.D)",
    "v11d": "Accum Breakout",
    "v11e": "BB Squeeze 4H",
}


# ─── Klines fetcher ─────────────────────────────────────────

def fetch_5m_klines(pair: str, start_ts_ms: int, end_ts_ms: int) -> List[list]:
    """Fetch 5m klines between two timestamps (inclusive). Paginated."""
    all_kls = []
    cursor = start_ts_ms
    api = "https://api.binance.com/api/v3/klines"
    while cursor < end_ts_ms:
        try:
            r = requests.get(api, params={
                "symbol": pair, "interval": "5m",
                "startTime": cursor, "endTime": end_ts_ms, "limit": 1000
            }, timeout=15)
            d = r.json()
            if not isinstance(d, list) or not d:
                break
        except Exception:
            break
        all_kls.extend(d)
        last_open = int(d[-1][0])
        if last_open <= cursor:
            break
        cursor = last_open + 5 * 60 * 1000
        time.sleep(0.05)
        if len(d) < 1000:
            break
    return all_kls


# ─── Hybrid TP simulator ─────────────────────────────────────

def simulate_exit(entry_price: float, klines: List[list]) -> Dict:
    """Walk forward through klines applying hybrid TP/SL logic.
    Returns {exit_price, close_reason, realized_pnl_usd, pnl_pct, partial1_done, partial2_done,
             trail_active, highest_price, closed_at_iso, hours}.
    """
    sl = entry_price * (1 - SL_PCT / 100)
    tp1 = entry_price * (1 + TP1_PCT / 100)
    tp2 = entry_price * (1 + TP2_PCT / 100)

    partial1 = False
    partial2 = False
    trail_active = False
    trail_stop = sl
    realized = 0.0
    remaining = 1.0
    highest = entry_price

    for kl in klines:
        ts = int(kl[0])
        h = float(kl[2]); l = float(kl[3]); c = float(kl[4])
        highest = max(highest, h)

        # Stop check first (if low touches stop before high reaches TP)
        if l <= trail_stop:
            exit_price = trail_stop
            exit_pct = (exit_price - entry_price) / entry_price * 100
            exit_usd = SIZE_USD * remaining * exit_pct / 100
            total_pnl = realized + exit_usd
            reason = "TRAIL_STOP" if trail_active else ("BREAKEVEN_STOP" if partial1 else "SL_HIT")
            return _final(exit_price, reason, total_pnl, partial1, partial2, trail_active, highest, ts)

        # TP1
        if not partial1 and h >= tp1:
            profit_usd = SIZE_USD * TP1_FRAC * TP1_PCT / 100
            realized += profit_usd
            remaining -= TP1_FRAC
            partial1 = True
            trail_stop = entry_price  # SL → BE

        # TP2
        if partial1 and not partial2 and h >= tp2:
            profit_usd = SIZE_USD * TP2_FRAC * TP2_PCT / 100
            realized += profit_usd
            remaining -= TP2_FRAC
            partial2 = True
            trail_active = True
            trail_stop = highest * (1 - TRAIL_DIST_PCT / 100)

        # Trailing update
        if trail_active:
            new_trail = highest * (1 - TRAIL_DIST_PCT / 100)
            if new_trail > trail_stop:
                trail_stop = new_trail

    # Reached end of klines without hitting SL — close at last close (TIMEOUT)
    last_close = float(klines[-1][4]) if klines else entry_price
    exit_pct = (last_close - entry_price) / entry_price * 100
    exit_usd = SIZE_USD * remaining * exit_pct / 100
    total_pnl = realized + exit_usd
    last_ts = int(klines[-1][0]) if klines else 0
    return _final(last_close, "TIMEOUT_72H", total_pnl, partial1, partial2, trail_active, highest, last_ts)


def _final(exit_price, reason, total_pnl, p1, p2, trail, highest, ts_ms) -> Dict:
    return {
        "exit_price": round(exit_price, 8),
        "close_reason": reason,
        "realized_pnl_usd": round(total_pnl, 2),
        "pnl_pct": round(total_pnl / SIZE_USD * 100, 2),
        "partial1_done": p1,
        "partial2_done": p2,
        "trail_active": trail,
        "highest_price": round(highest, 8),
        "closed_at_iso": datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat() if ts_ms else None,
    }


# ─── Hydration runner ────────────────────────────────────────

def hydrate(sb, variant: str, days: int) -> Dict:
    """Hydrate a single V11x with historical matches."""
    print(f"\n━━━ Hydrating {variant.upper()} ({LABELS[variant]}) ━━━", flush=True)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    table_pos = f"openclaw_positions_{variant}"
    table_state = f"openclaw_portfolio_state_{variant}"
    gate = HIST_GATES[variant]

    # Wipe existing hydrated rows (so re-runs are idempotent)
    try:
        sb.table(table_pos).delete().eq("close_reason", "HYDRATED_BACKTEST").execute()
        # Also wipe TRAIL_STOP / SL_HIT / BREAKEVEN_STOP / TIMEOUT_72H if they came from past hydration
        # (We flag hydrated rows by writing close_reason='HYDRATED_BACKTEST:<original_reason>')
        sb.table(table_pos).delete().like("close_reason", "HYDRATED_BACKTEST:%").execute()
    except Exception as e:
        print(f"  ⚠️ wipe error: {e}")

    # Load resolved agent_memory rows + alert_data
    print(f"  📥 Loading agent_memory (last {days}d, resolved)...", flush=True)
    rows = []
    cursor = 0
    while True:
        r = sb.table("agent_memory").select(
            "id,pair,scanner_score,outcome,timestamp,alert_id,features_fingerprint"
        ).gte("timestamp", cutoff).in_("outcome", ["WIN", "LOSE"]).order(
            "timestamp", desc=False  # ascending so balance updates chronologically
        ).range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000

    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    amap = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("alerts").select(
            "id,alert_timestamp,price,puissance,emotion,nb_timeframes,bougie_4h,dmi_cross_4h,"
            "lazy_4h,vol_pct,timeframes,rsi_check,dmi_check,ast_check,choch,zone,lazy,vol,st,"
            "rsi,di_plus_4h,di_minus_4h,adx_4h,pp,ec"
        ).in_("id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            amap[x["id"]] = x

    matched = []
    for r in rows:
        fp = r.get("features_fingerprint") or {}
        a = amap.get(r.get("alert_id"), {})
        if gate(fp, a):
            matched.append((r, a))

    print(f"  ✅ {len(matched)} alerts match {variant.upper()} gate")
    if not matched:
        return {"variant": variant, "matched": 0, "wins": 0, "losses": 0, "total_pnl": 0}

    # Reset state
    try:
        sb.table(table_state).update({
            "balance": INITIAL_CAPITAL, "total_pnl": 0,
            "total_trades": 0, "wins": 0, "losses": 0,
            "max_drawdown_pct": 0, "peak_balance": INITIAL_CAPITAL,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", "main").execute()
    except Exception as e:
        print(f"  ⚠️ state reset: {e}")

    # Simulate each
    wins = losses = 0
    total_pnl = 0.0
    peak_pnl = 0.0
    max_dd = 0.0

    for i, (r, a) in enumerate(matched, 1):
        pair = r.get("pair", "")
        alert_ts_iso = a.get("alert_timestamp") or r.get("timestamp")
        entry_price = a.get("price") or 0
        if not pair or not alert_ts_iso or not entry_price:
            continue
        try:
            start_dt = datetime.fromisoformat(alert_ts_iso.replace("Z", "+00:00"))
        except Exception:
            continue
        end_dt = start_dt + timedelta(hours=TIMEOUT_H)
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)

        klines = fetch_5m_klines(pair, start_ms, end_ms)
        if not klines:
            print(f"    [{i:>3}/{len(matched)}] {pair:14s} ⚠️ no klines")
            continue

        sim = simulate_exit(entry_price, klines)
        is_win = sim["realized_pnl_usd"] > 0
        wins += int(is_win); losses += int(not is_win)
        total_pnl += sim["realized_pnl_usd"]
        peak_pnl = max(peak_pnl, total_pnl)
        dd = (peak_pnl - total_pnl) / INITIAL_CAPITAL * 100
        max_dd = max(max_dd, dd)

        # Build gate_snapshot from FP values that triggered the match (immutable audit trail)
        fp = r.get("features_fingerprint") or {}
        gate_snap = {
            "variant": variant,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "hydration_backfill",
        }
        for key in ("candle_15m_range_pct", "candle_30m_range_pct",
                    "candle_1h_range_pct", "candle_4h_range_pct",
                    "candle_4h_body_pct", "candle_4h_direction",
                    "bb_4h_width_pct", "btc_dominance",
                    "accumulation_days", "accumulation_hours",
                    "di_plus_4h", "di_minus_4h", "adx_4h", "rsi",
                    "stc_15m", "stc_30m", "stc_1h", "pp", "ec"):
            if fp.get(key) is not None:
                gate_snap[key] = fp[key]

        # Insert CLOSED position
        position = {
            "id": str(uuid.uuid4()), "pair": pair,
            "entry_price": entry_price, "current_price": sim["exit_price"],
            "size_usd": SIZE_USD,
            "sl_price": entry_price * (1 - SL_PCT / 100),
            "tp1_price": entry_price * (1 + TP1_PCT / 100),
            "tp2_price": entry_price * (1 + TP2_PCT / 100),
            "pnl_pct": sim["pnl_pct"], "pnl_usd": sim["realized_pnl_usd"],
            "highest_price": sim["highest_price"],
            "status": "CLOSED",
            "close_reason": f"HYDRATED_BACKTEST:{sim['close_reason']}",
            "exit_price": sim["exit_price"],
            "decision": "BUY", "confidence": 0.7,
            "alert_id": r.get("alert_id"),
            "scanner_score": r.get("scanner_score") or a.get("scanner_score") or 0,
            "is_vip": False, "is_high_ticket": False, "quality_grade": "",
            "opened_at": alert_ts_iso,
            "closed_at": sim["closed_at_iso"],
            "partial1_done": sim["partial1_done"],
            "partial2_done": sim["partial2_done"],
            "trail_active": sim["trail_active"],
            "trail_stop": entry_price * (1 - SL_PCT / 100),
            "realized_pnl_usd": sim["realized_pnl_usd"],
            "remaining_size_pct": 0,
            "gate_snapshot": gate_snap,
        }
        try:
            sb.table(table_pos).insert(position).execute()
        except Exception as e:
            print(f"    [{i:>3}/{len(matched)}] {pair:14s} ❌ insert: {e}")
            continue

        sign = '✅' if is_win else '❌'
        if i % 25 == 0 or i == len(matched):
            print(f"    [{i:>3}/{len(matched)}] {pair:14s} {sign} {sim['pnl_pct']:+.2f}% ({sim['close_reason']}) | balance ${INITIAL_CAPITAL + total_pnl:.0f}", flush=True)
        time.sleep(0.05)

    # Update state
    try:
        sb.table(table_state).update({
            "balance": round(INITIAL_CAPITAL + total_pnl, 2),
            "total_pnl": round(total_pnl, 2),
            "total_trades": wins + losses,
            "wins": wins, "losses": losses,
            "max_drawdown_pct": round(max_dd, 2),
            "peak_balance": round(INITIAL_CAPITAL + peak_pnl, 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", "main").execute()
    except Exception as e:
        print(f"  ⚠️ final state update: {e}")

    wr = (wins / (wins + losses) * 100) if (wins + losses) else 0
    print(f"  📊 {variant.upper()} hydrated: {wins}W/{losses}L | WR {wr:.1f}% | total PnL ${total_pnl:+.2f} | DD {max_dd:.2f}%")
    return {"variant": variant, "matched": wins + losses, "wins": wins, "losses": losses, "total_pnl": total_pnl, "wr": wr, "dd": max_dd}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--variants", type=str, default="v11a,v11b,v11c,v11d,v11e")
    args = ap.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    variants = [v.strip().lower() for v in args.variants.split(",") if v.strip()]
    summaries = []
    for v in variants:
        if v not in HIST_GATES:
            print(f"⚠️ unknown variant {v}, skipped")
            continue
        summaries.append(hydrate(sb, v, args.days))

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("📊 HYDRATION SUMMARY")
    for s in summaries:
        if not s: continue
        print(f"   {s['variant'].upper()}: {s.get('wins',0)}W/{s.get('losses',0)}L ({s.get('matched',0)} trades) | WR {s.get('wr',0):.1f}% | PnL ${s.get('total_pnl',0):+.2f} | DD {s.get('dd',0):.2f}%")


if __name__ == "__main__":
    main()
