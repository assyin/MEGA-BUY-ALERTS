#!/usr/bin/env python3
"""Auto-discover high-performance filter hypotheses from agent_memory data.

For every numeric / categorical / boolean feature in features_fingerprint and
alert_data, test conditional WR vs baseline. Then test 2-feature combos. Output
a ranked markdown report.

Usage:
    python3 -u scripts/discover_hypotheses.py [--days 30] [--min-n 30] [--top 30]
"""

import argparse
import math
import statistics
import sys
from datetime import datetime, timezone, timedelta
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from openclaw.config import get_settings
from supabase import create_client

try:
    from scipy.stats import binomtest
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ─── Feature catalog ─────────────────────────────────────────
# (source, feature_path, type, label)
# source ∈ {'fp' (features_fingerprint), 'alert' (alert_data)}

NUMERIC_FEATURES = [
    # Score & decision quality
    ('row', 'scanner_score', 'Scanner Score'),
    ('fp', 'agent_confidence', 'Agent Confidence'),
    ('fp', 'vip_score', 'VIP Score'),
    ('fp', 'quality_axes', 'Quality Axes'),
    # 4H technical
    ('fp', 'di_plus_4h', 'DI+ 4H'),
    ('fp', 'di_minus_4h', 'DI- 4H'),
    ('fp', 'adx_4h', 'ADX 4H'),
    ('fp', 'rsi', 'RSI'),
    ('fp', 'change_24h_pct', '24h change %'),
    # Candle bodies & ranges per TF
    ('fp', 'candle_15m_body_pct', 'Body 15m %'),
    ('fp', 'candle_30m_body_pct', 'Body 30m %'),
    ('fp', 'candle_1h_body_pct', 'Body 1h %'),
    ('fp', 'candle_4h_body_pct', 'Body 4h %'),
    ('fp', 'candle_15m_range_pct', 'Range 15m %'),
    ('fp', 'candle_30m_range_pct', 'Range 30m %'),
    ('fp', 'candle_1h_range_pct', 'Range 1h %'),
    ('fp', 'candle_4h_range_pct', 'Range 4h %'),
    # Vol spikes
    ('fp', 'vol_spike_vs_1h', 'Vol spike vs 1h'),
    ('fp', 'vol_spike_vs_4h', 'Vol spike vs 4h'),
    ('fp', 'vol_spike_vs_24h', 'Vol spike vs 24h'),
    ('fp', 'vol_spike_vs_48h', 'Vol spike vs 48h'),
    ('fp', 'volume_usdt', 'Volume USDT'),
    # STC
    ('fp', 'stc_15m', 'STC 15m'),
    ('fp', 'stc_30m', 'STC 30m'),
    ('fp', 'stc_1h', 'STC 1h'),
    # Market context
    ('fp', 'btc_change_24h', 'BTC 24h %'),
    ('fp', 'eth_change_24h', 'ETH 24h %'),
    ('fp', 'btc_dominance', 'BTC dominance'),
    ('fp', 'eth_dominance', 'ETH dominance'),
    ('fp', 'others_d', 'Others.D'),
    ('fp', 'fear_greed_value', 'Fear & Greed'),
    # Accumulation
    ('fp', 'accumulation_days', 'Accum days'),
    ('fp', 'accumulation_hours', 'Accum hours'),
    ('fp', 'accumulation_range_pct', 'Accum range %'),
    # Tier 3 — analyze_alert
    ('fp', 'prog_count_effective', 'Prog cond effective'),
    ('fp', 'prog_count_hard', 'Prog cond hard'),
    ('fp', 'bonus_count', 'Bonus count'),
    ('fp', 'adx_1h', 'ADX 1H'),
    ('fp', 'adx_1h_di_plus', 'DI+ 1H'),
    ('fp', 'adx_1h_di_minus', 'DI- 1H'),
    ('fp', 'adx_1h_di_spread', 'DI spread 1H'),
    ('fp', 'rsi_mtf_aligned_count', 'RSI MTF aligned'),
    ('fp', 'ml_p_success', 'ML p_success'),
    ('fp', 'ema_stack_1h_count', 'EMA Stack 1H'),
    ('fp', 'ema_stack_4h_count', 'EMA Stack 4H'),
    ('fp', 'stochrsi_1h_k', 'StochRSI 1H k'),
    ('fp', 'stochrsi_4h_k', 'StochRSI 4H k'),
    ('fp', 'bb_1h_width_pct', 'BB 1H width %'),
    ('fp', 'bb_4h_width_pct', 'BB 4H width %'),
    ('fp', 'ob_1h_distance_pct', 'OB 1H dist %'),
    ('fp', 'ob_4h_distance_pct', 'OB 4H dist %'),
    ('fp', 'ob_1h_count', 'OB 1H count'),
    ('fp', 'ob_4h_count', 'OB 4H count'),
    # Alerts table
    ('alert', 'puissance', 'Puissance'),
    ('alert', 'nb_timeframes', 'Nb TFs'),
    ('alert', 'max_profit_pct', 'Max profit historic %'),
    # Per-TF moves (extracted from JSON dicts in alert_data)
    ('move', 'rsi_moves|15m', 'RSI move 15m'),
    ('move', 'rsi_moves|30m', 'RSI move 30m'),
    ('move', 'rsi_moves|1h', 'RSI move 1h'),
    ('move', 'rsi_moves|4h', 'RSI move 4h'),
    ('move', 'di_plus_moves|15m', 'DI+ move 15m'),
    ('move', 'di_plus_moves|30m', 'DI+ move 30m'),
    ('move', 'di_plus_moves|1h', 'DI+ move 1h'),
    ('move', 'di_plus_moves|4h', 'DI+ move 4h'),
    ('move', 'di_minus_moves|15m', 'DI- move 15m'),
    ('move', 'di_minus_moves|1h', 'DI- move 1h'),
    ('move', 'di_minus_moves|4h', 'DI- move 4h'),
    ('move', 'adx_moves|15m', 'ADX move 15m'),
    ('move', 'adx_moves|1h', 'ADX move 1h'),
    ('move', 'adx_moves|4h', 'ADX move 4h'),
    ('move', 'ec_moves|15m', 'EC move 15m'),
    ('move', 'ec_moves|30m', 'EC move 30m'),
    ('move', 'ec_moves|1h', 'EC move 1h'),
    ('move', 'ec_moves|4h', 'EC move 4h'),
    # Volume % per TF
    ('move', 'vol_pct|15m', 'Vol % 15m'),
    ('move', 'vol_pct|30m', 'Vol % 30m'),
    ('move', 'vol_pct|1h', 'Vol % 1h'),
    ('move', 'vol_pct|4h', 'Vol % 4h'),
    # LazyBar value per TF (numeric, takes vals[0] = score)
    ('lazy_val', 'lazy_values|15m', 'LazyBar val 15m'),
    ('lazy_val', 'lazy_values|30m', 'LazyBar val 30m'),
    ('lazy_val', 'lazy_values|1h', 'LazyBar val 1h'),
    ('lazy_val', 'lazy_values|4h', 'LazyBar val 4h'),
    # Score exact values
    ('score_eq', '10', 'Scanner Score = 10'),
    ('score_eq', '9', 'Scanner Score = 9'),
    ('score_eq', '8', 'Scanner Score = 8'),
]

BOOLEAN_FEATURES = [
    ('fp', 'is_vip', 'Is VIP'),
    ('fp', 'is_high_ticket', 'Is High Ticket'),
    ('fp', 'pp', 'PP'),
    ('fp', 'ec', 'EC'),
    ('fp', 'btc_season', 'BTC season'),
    ('fp', 'btc_trend_bullish', 'BTC trend bullish'),
    ('fp', 'eth_trend_bullish', 'ETH trend bullish'),
    ('fp', 'alt_season', 'Alt season'),
    # Tier 3 booleans
    ('fp', 'fib_4h_bonus', 'Fib 4H bonus'),
    ('fp', 'fib_1h_bonus', 'Fib 1H bonus'),
    ('fp', 'ob_4h_bonus', 'OB 4H bonus'),
    ('fp', 'ob_1h_bonus', 'OB 1H bonus'),
    ('fp', 'fvg_4h_bonus', 'FVG 4H bonus'),
    ('fp', 'fvg_1h_bonus', 'FVG 1H bonus'),
    ('fp', 'bb_1h_squeeze', 'BB 1H squeeze'),
    ('fp', 'bb_4h_squeeze', 'BB 4H squeeze'),
    ('fp', 'macd_1h_growing', 'MACD 1H growing'),
    ('fp', 'macd_4h_growing', 'MACD 4H growing'),
    ('fp', 'ob_1h_mitigated', 'OB 1H mitigated'),
    ('fp', 'ob_4h_mitigated', 'OB 4H mitigated'),
    ('fp', 'prog_ema100_1h_valid', 'Prog ema100_1h valid'),
    ('fp', 'prog_ema20_4h_valid', 'Prog ema20_4h valid'),
    ('fp', 'prog_cloud_1h_valid', 'Prog cloud_1h valid'),
    ('fp', 'prog_cloud_30m_valid', 'Prog cloud_30m valid'),
    ('fp', 'prog_choch_bos_valid', 'Prog choch_bos valid'),
    # Alerts table
    ('alert', 'bougie_4h', 'Bougie 4H validation'),
    ('alert', 'dmi_cross_4h', 'DMI cross 4H'),
    # MEGA BUY scanner conditions (the 10 conditions)
    ('alert', 'rsi_check', 'MB cond: RSI surge'),
    ('alert', 'dmi_check', 'MB cond: DMI+ surge'),
    ('alert', 'ast_check', 'MB cond: AssyinSuperTrend'),
    ('alert', 'choch', 'MB cond: CHoCH'),
    ('alert', 'zone', 'MB cond: Green Zone'),
    ('alert', 'lazy', 'MB cond: LazyBar'),
    ('alert', 'vol', 'MB cond: Volume'),
    ('alert', 'st', 'MB cond: SuperTrend'),
]

CATEGORICAL_FEATURES = [
    ('fp', 'agent_decision', 'Agent decision'),
    ('fp', 'quality_grade', 'Quality grade'),
    ('fp', 'btc_trend_1h', 'BTC trend 1H'),
    ('fp', 'eth_trend_1h', 'ETH trend 1H'),
    ('fp', 'fear_greed_label', 'F&G label'),
    ('fp', 'candle_4h_direction', '4H direction'),
    ('fp', 'candle_1h_direction', '1H direction'),
    ('fp', 'candle_30m_direction', '30M direction'),
    ('fp', 'candle_15m_direction', '15M direction'),
    # Tier 3
    ('fp', 'macd_1h_trend', 'MACD 1H trend'),
    ('fp', 'macd_4h_trend', 'MACD 4H trend'),
    ('fp', 'stochrsi_1h_zone', 'StochRSI 1H zone'),
    ('fp', 'stochrsi_4h_zone', 'StochRSI 4H zone'),
    ('fp', 'ema_stack_1h_trend', 'EMA Stack 1H trend'),
    ('fp', 'ema_stack_4h_trend', 'EMA Stack 4H trend'),
    ('fp', 'vp_1h_position', 'VP 1H position'),
    ('fp', 'vp_4h_position', 'VP 4H position'),
    ('fp', 'ob_1h_position', 'OB 1H position'),
    ('fp', 'ob_4h_position', 'OB 4H position'),
    ('fp', 'ob_1h_strength', 'OB 1H strength'),
    ('fp', 'ob_4h_strength', 'OB 4H strength'),
    ('fp', 'fvg_1h_position', 'FVG 1H position'),
    ('fp', 'fvg_4h_position', 'FVG 4H position'),
    ('fp', 'rsi_mtf_trend', 'RSI MTF trend'),
    ('fp', 'ml_decision', 'ML decision'),
    ('alert', 'emotion', 'Emotion'),
    ('alert', 'lazy_4h', 'LazyBar 4H'),
]


# ─── Value extraction ────────────────────────────────────────

def get_value(row: dict, source: str, key: str):
    """Extract feature value from the row (agent_memory + alert_data)."""
    if source == 'row':
        return row.get(key)
    if source == 'fp':
        fp = row.get('features_fingerprint') or {}
        return fp.get(key)
    if source == 'alert':
        ad = row.get('alert_data') or {}
        return ad.get(key)
    if source == 'move':
        # key format: "rsi_moves|1h" → look in alert_data['rsi_moves']['1h']
        ad = row.get('alert_data') or {}
        parts = key.split('|', 1)
        if len(parts) != 2: return None
        d = ad.get(parts[0]) or {}
        if not isinstance(d, dict): return None
        v = d.get(parts[1])
        try: return float(v) if v is not None else None
        except (ValueError, TypeError): return None
    if source == 'lazy_val':
        # key format: "lazy_values|1h" → look in alert_data['lazy_values']['1h'][0] (numeric value)
        ad = row.get('alert_data') or {}
        parts = key.split('|', 1)
        if len(parts) != 2: return None
        d = ad.get(parts[0]) or {}
        if not isinstance(d, dict): return None
        v = d.get(parts[1])
        if isinstance(v, list) and v:
            try: return float(v[0])
            except (ValueError, TypeError): return None
        return None
    if source == 'score_eq':
        # key is the exact score to match (returns the score for direct comparison)
        return row.get('scanner_score')
    return None


# ─── Stats helpers ───────────────────────────────────────────

def compute_stats(matched: list, baseline_wr: float) -> dict:
    """Compute WR, avg PnL, lift, p-value for a matched subset."""
    n = len(matched)
    if n == 0:
        return {"n": 0}
    wins = sum(1 for r in matched if r["outcome"] == "WIN")
    losses = n - wins
    wr = wins / n * 100
    pnls = [r.get("pnl_at_close") or 0 for r in matched]
    avg_pnl = sum(pnls) / n if pnls else 0
    pmax = [r.get("pnl_max") or 0 for r in matched]
    avg_pnl_max = sum(pmax) / n if pmax else 0
    lift_wr = wr - baseline_wr

    p_value = None
    if HAS_SCIPY and n > 0:
        try:
            res = binomtest(wins, n, p=baseline_wr/100, alternative='greater')
            p_value = res.pvalue
        except Exception:
            pass

    score = lift_wr * math.log(max(n, 2))  # rank metric
    return {
        "n": n, "wins": wins, "losses": losses,
        "wr": wr, "avg_pnl": avg_pnl, "avg_pnl_max": avg_pnl_max,
        "lift_wr": lift_wr, "p_value": p_value, "score": score
    }


def quantile(values: list, q: float) -> float:
    if not values:
        return 0
    s = sorted(values)
    idx = int(len(s) * q)
    return s[min(idx, len(s) - 1)]


# ─── Single-feature hypotheses ───────────────────────────────

def test_numeric_feature(rows: list, source: str, key: str, label: str,
                         baseline_wr: float, min_n: int) -> list:
    """Return list of (description, condition_lambda, stats) tuples."""
    vals = [get_value(r, source, key) for r in rows]
    valid_vals = [v for v in vals if isinstance(v, (int, float)) and v is not None]
    if len(valid_vals) < min_n * 2:  # need enough non-null data
        return []

    results = []
    # Test thresholds at quantiles
    for q in [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]:
        thr = quantile(valid_vals, q)
        # >= threshold
        matched_ge = [r for r in rows
                      if isinstance(get_value(r, source, key), (int, float))
                      and get_value(r, source, key) >= thr]
        st = compute_stats(matched_ge, baseline_wr)
        if st.get("n", 0) >= min_n:
            results.append((f"{label} >= {thr:.2f}", st, ('numeric_ge', source, key, thr)))
        # <= threshold
        matched_le = [r for r in rows
                      if isinstance(get_value(r, source, key), (int, float))
                      and get_value(r, source, key) <= thr]
        st = compute_stats(matched_le, baseline_wr)
        if st.get("n", 0) >= min_n:
            results.append((f"{label} <= {thr:.2f}", st, ('numeric_le', source, key, thr)))
    return results


def test_boolean_feature(rows: list, source: str, key: str, label: str,
                         baseline_wr: float, min_n: int) -> list:
    matched_t = [r for r in rows if get_value(r, source, key) is True]
    matched_f = [r for r in rows if get_value(r, source, key) is False]
    out = []
    for matched, op_label in [(matched_t, 'True'), (matched_f, 'False')]:
        st = compute_stats(matched, baseline_wr)
        if st.get("n", 0) >= min_n:
            op = ('bool_eq', source, key, (op_label == 'True'))
            out.append((f"{label} = {op_label}", st, op))
    return out


def test_categorical_feature(rows: list, source: str, key: str, label: str,
                              baseline_wr: float, min_n: int) -> list:
    vals = [get_value(r, source, key) for r in rows]
    unique = set(v for v in vals if v not in (None, ''))
    out = []
    for v in unique:
        matched = [r for r in rows if get_value(r, source, key) == v]
        st = compute_stats(matched, baseline_wr)
        if st.get("n", 0) >= min_n:
            op = ('cat_eq', source, key, v)
            out.append((f"{label} = '{v}'", st, op))
    return out


# ─── Combo testing ───────────────────────────────────────────

def matches_op(row: dict, op: tuple) -> bool:
    op_type = op[0]
    if op_type == 'numeric_ge':
        _, source, key, thr = op
        v = get_value(row, source, key)
        return isinstance(v, (int, float)) and v >= thr
    if op_type == 'numeric_le':
        _, source, key, thr = op
        v = get_value(row, source, key)
        return isinstance(v, (int, float)) and v <= thr
    if op_type == 'bool_eq':
        _, source, key, target = op
        v = get_value(row, source, key)
        return v is target
    if op_type == 'cat_eq':
        _, source, key, target = op
        return get_value(row, source, key) == target
    return False


def test_combo(rows: list, op_a: tuple, op_b: tuple, label_a: str, label_b: str,
               baseline_wr: float, min_n: int):
    matched = [r for r in rows if matches_op(r, op_a) and matches_op(r, op_b)]
    st = compute_stats(matched, baseline_wr)
    if st.get("n", 0) >= min_n:
        return (f"{label_a} AND {label_b}", st, (op_a, op_b))
    return None


# ─── Custom filter (user's reference) ────────────────────────

def matches_custom(r: dict) -> bool:
    fp = r.get("features_fingerprint") or {}
    a = r.get("alert_data") or {}
    score = r.get("scanner_score") or 0
    di_p = fp.get("di_plus_4h"); di_m = fp.get("di_minus_4h"); adx = fp.get("adx_4h")
    if di_p is None or di_p < 37 or di_p > 50: return False
    if di_m is None or di_m < 0 or di_m > 14: return False
    if adx is None or adx < 15: return False
    if (di_p - di_m) > 45: return False
    if (adx - di_m) < 3: return False
    if (fp.get("rsi") or 0) > 79: return False
    if (fp.get("change_24h_pct") or 0) > 36: return False
    if (fp.get("candle_4h_body_pct") or 0) < 2.7: return False
    if (fp.get("candle_4h_range_pct") or 0) > 34: return False
    if (fp.get("stc_15m") or 0) < 0.1: return False
    if (fp.get("stc_30m") or 0) < 0.2: return False
    if (fp.get("stc_1h") or 0) < 0.1: return False
    if fp.get("candle_4h_direction") != "green": return False
    if not fp.get("pp"): return False
    if not fp.get("ec"): return False
    tfs = fp.get("timeframes") or []
    if "15m" not in tfs: return False
    vp = a.get("vol_pct") or {}
    if isinstance(vp, dict) and vp:
        if all((v is None or v <= 0) for v in vp.values()): return False
    return True


# ─── Markdown rendering ──────────────────────────────────────

def fmt_pval(p):
    if p is None: return "—"
    if p < 0.001: return "<0.001 ★★★"
    if p < 0.01: return f"{p:.4f} ★★"
    if p < 0.05: return f"{p:.3f} ★"
    return f"{p:.3f}"


def render_table_row(rank: int, label: str, st: dict) -> str:
    return (f"| {rank} | {label} | {st['n']} | {st['wins']}W/{st['losses']}L | "
            f"{st['wr']:.1f}% | {st['avg_pnl']:+.2f}% | {st['lift_wr']:+.1f}pts | {fmt_pval(st['p_value'])} |")


# ─── Main ────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--min-n", type=int, default=30, help="Min samples to be considered")
    ap.add_argument("--top", type=int, default=30, help="Top N hypotheses to output")
    ap.add_argument("--combo-from-top", type=int, default=25, help="Combos from top N singles")
    args = ap.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    print(f"📥 Loading agent_memory (last {args.days}d, resolved only)...", flush=True)
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
    print(f"   {len(rows)} resolved alerts loaded")

    # Enrich with alert_data
    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    amap = {}
    print(f"📥 Joining alerts table ({len(aids)} alert_ids)...", flush=True)
    for i in range(0, len(aids), 100):
        rr = sb.table("alerts").select(
            "id,alert_timestamp,puissance,emotion,nb_timeframes,bougie_4h,dmi_cross_4h,"
            "lazy_4h,max_profit_pct,vol_pct,lazy_values,lazy_moves,"
            "rsi_check,dmi_check,ast_check,choch,zone,lazy,vol,st,"
            "rsi_moves,di_plus_moves,di_minus_moves,adx_moves,ec_moves"
        ).in_("id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            amap[x["id"]] = x
    for r in rows:
        r["alert_data"] = amap.get(r.get("alert_id") or "", {})

    # Baseline
    n = len(rows)
    wins = sum(1 for r in rows if r["outcome"] == "WIN")
    losses = n - wins
    baseline_wr = wins / n * 100 if n else 0
    base_pnl = sum(r.get("pnl_at_close") or 0 for r in rows) / n if n else 0
    print(f"\n📊 Baseline: N={n}, WR={baseline_wr:.1f}%, avg PnL={base_pnl:+.2f}%")

    # ─── Test all single features ───
    print(f"\n🔬 Testing single-feature hypotheses (min_n={args.min_n})...")
    all_singles = []
    for source, key, label in NUMERIC_FEATURES:
        if source == 'score_eq':
            # special case: test exact score equality
            score_target = int(key)
            matched = [r for r in rows if (r.get('scanner_score') or 0) == score_target]
            st = compute_stats(matched, baseline_wr)
            if st.get("n", 0) >= args.min_n:
                all_singles.append((label, st, ('cat_eq', 'row', 'scanner_score', score_target)))
        else:
            all_singles.extend(test_numeric_feature(rows, source, key, label, baseline_wr, args.min_n))
    for source, key, label in BOOLEAN_FEATURES:
        all_singles.extend(test_boolean_feature(rows, source, key, label, baseline_wr, args.min_n))
    for source, key, label in CATEGORICAL_FEATURES:
        all_singles.extend(test_categorical_feature(rows, source, key, label, baseline_wr, args.min_n))

    # Filter: only positive lift, sort by score
    all_singles = [s for s in all_singles if s[1]['lift_wr'] > 0]
    all_singles.sort(key=lambda x: x[1]['score'], reverse=True)
    print(f"   {len(all_singles)} hypotheses with positive lift")

    # ─── Test 2-feature combos from top singles ───
    print(f"\n🔬 Testing 2-feature combos (top {args.combo_from_top} singles, min_n={args.min_n})...")
    top_for_combo = all_singles[:args.combo_from_top]
    all_combos = []
    total_pairs = len(top_for_combo) * (len(top_for_combo) - 1) // 2
    done = 0
    for (la, sta, opa), (lb, stb, opb) in combinations(top_for_combo, 2):
        # Skip if same key (e.g., DI+ >= 35 AND DI+ >= 40 is degenerate)
        key_a = opa[2] if len(opa) > 2 else None
        key_b = opb[2] if len(opb) > 2 else None
        if key_a == key_b: continue
        c = test_combo(rows, opa, opb, la, lb, baseline_wr, args.min_n)
        if c and c[1]['lift_wr'] > 0:
            all_combos.append(c)
        done += 1
        if done % 100 == 0:
            print(f"   {done}/{total_pairs} pairs tested...", flush=True)
    all_combos.sort(key=lambda x: x[1]['score'], reverse=True)
    print(f"   {len(all_combos)} positive-lift combos")

    # ─── Custom filter reference ───
    custom_matched = [r for r in rows if matches_custom(r)]
    custom_st = compute_stats(custom_matched, baseline_wr)

    # ─── Build markdown report ───
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    L = []
    L.append(f"# 🔬 Hypothesis Discovery Report")
    L.append("")
    L.append(f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_")
    L.append("")
    L.append(f"**Dataset**: agent_memory rows resolved (WIN/LOSE) over last {args.days} days, joined with alerts table.")
    L.append("")
    L.append("## 📊 Baseline")
    L.append("")
    L.append(f"- **N**: {n} resolved alerts")
    L.append(f"- **WR**: {baseline_wr:.1f}% ({wins}W / {losses}L)")
    L.append(f"- **Avg PnL @ close**: {base_pnl:+.2f}%")
    L.append("")
    L.append(f"_Min N filter_: hypotheses must match ≥{args.min_n} alerts to be included. p-value via one-sided binomial test (greater than baseline).")
    L.append("")

    # Custom filter
    L.append("## 🎯 User's Custom filter (reference)")
    L.append("")
    if custom_st.get("n", 0) > 0:
        L.append(f"- N={custom_st['n']}, **WR={custom_st['wr']:.1f}%**, lift {custom_st['lift_wr']:+.1f}pts, "
                 f"avg PnL {custom_st['avg_pnl']:+.2f}%, p-value {fmt_pval(custom_st['p_value'])}")
    else:
        L.append("- N=0 — Custom filter matched zero rows in this dataset")
    L.append("")

    # Top single
    L.append(f"## 🏆 Top {args.top} single-feature hypotheses (sorted by lift × log(N))")
    L.append("")
    L.append("| Rank | Condition | N | W/L | WR | Avg PnL | Lift | p-value |")
    L.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for i, (label, st, _) in enumerate(all_singles[:args.top], 1):
        L.append(render_table_row(i, label, st))
    L.append("")

    # Top combos
    L.append(f"## 🤝 Top {args.top} 2-feature combos")
    L.append("")
    L.append("| Rank | Condition | N | W/L | WR | Avg PnL | Lift | p-value |")
    L.append("|---:|---|---:|---:|---:|---:|---:|---:|")
    for i, (label, st, _) in enumerate(all_combos[:args.top], 1):
        L.append(render_table_row(i, label, st))
    L.append("")

    # Position of Custom in combo ranking (informally compare)
    L.append("## 📍 Where does Custom rank?")
    L.append("")
    if custom_st.get("n", 0) > 0:
        better_singles = sum(1 for _, st, _ in all_singles if st['score'] > custom_st['score'])
        better_combos = sum(1 for _, st, _ in all_combos if st['score'] > custom_st['score'])
        L.append(f"- {better_singles} single-feature hypotheses score higher than Custom on the rank metric")
        L.append(f"- {better_combos} combo hypotheses score higher")
        if better_singles == 0 and better_combos == 0:
            L.append("- ✅ **Custom is the best ranked hypothesis** in this dataset")
        elif better_combos < 5:
            L.append(f"- 🟡 **Custom is competitive** (only {better_combos} combos rank higher)")
        else:
            L.append(f"- 🔴 **Several hypotheses outperform Custom** — see top {min(5, better_combos)} above")
    L.append("")

    # Recommendations
    L.append("## 💡 Recommendations")
    L.append("")
    L.append("1. **Prioritize hypotheses with low p-value (★, ★★, ★★★)** — they are statistically significant.")
    L.append("2. **Avoid combos with N < 50** unless the lift is dramatic (>15pts) — small samples are noise-prone.")
    L.append("3. **Run a second pass** in 1-2 weeks to verify top hypotheses still hold (regime stability check).")
    L.append("4. **Combos that look like extensions of Custom** (e.g. score>=8 + body 4h>=3) confirm your trader intuition is on track.")
    L.append("")

    out_path = Path(__file__).parent.parent.parent / f"HYPOTHESES_{today}.md"
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"\n✅ Report: {out_path}")
    print(f"   {len(all_singles)} singles | {len(all_combos)} combos | "
          f"Custom: N={custom_st.get('n',0)}, WR={custom_st.get('wr',0):.1f}%")


if __name__ == "__main__":
    main()
