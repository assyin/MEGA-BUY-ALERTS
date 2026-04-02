#!/usr/bin/env python3
"""
FAST backtest — uses alert data + 1 Binance call per alert instead of full 197-indicator analysis.
For Axes 2 (Structure) and 3 (Momentum), does a lightweight check from the bonus_filters API.
"""
import sys, time, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from openclaw.config import get_settings
from supabase import create_client
import requests

BINANCE = "https://api.binance.com/api/v3/klines"


def get_price_range_7d(pair: str, alert_ts_iso: str) -> dict:
    """Get highest/lowest price within 7 days after alert using 4H candles (1 API call)."""
    try:
        ts = datetime.fromisoformat(alert_ts_iso.replace('+00:00', '+00:00'))
        start_ms = int(ts.timestamp() * 1000)
        end_ms = min(int((ts.timestamp() + 168 * 3600) * 1000), int(datetime.now(timezone.utc).timestamp() * 1000))
        resp = requests.get(BINANCE, params={
            'symbol': pair, 'interval': '4h', 'startTime': start_ms, 'endTime': end_ms, 'limit': 42
        }, timeout=10)
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            highs = [float(c[2]) for c in data]
            lows = [float(c[3]) for c in data]
            return {'highest': max(highs), 'lowest': min(lows), 'candles': len(data)}
    except:
        pass
    return {'highest': 0, 'lowest': 0, 'candles': 0}


def compute_axes_from_alert_and_analysis(alert: dict, analysis: dict) -> dict:
    """Compute 4 quality axes from alert data + realtime analysis."""
    bf = analysis.get("bonus_filters", {}) if analysis else {}

    # AXE 1: TREND (from alert data directly)
    adx_4h = alert.get('adx_4h') or 0
    di_plus = alert.get('di_plus_4h') or 0
    di_minus = alert.get('di_minus_4h') or 0
    di_spread = di_plus - di_minus
    ax1 = adx_4h > 40 or di_spread > 20

    # AXE 2: STRUCTURE — need FVG/OB data from analysis
    ax2 = False
    fvg_pos = None
    ob_inside = False
    if bf:
        fvg_1h = bf.get("fvg_1h", {})
        fvg_pos = fvg_1h.get("position") if isinstance(fvg_1h, dict) else None
        if fvg_pos == "ABOVE":
            ax2 = True

        for tf in ["ob_1h", "ob_4h"]:
            ob = bf.get(tf, {})
            blocks = ob.get("blocks", []) if isinstance(ob, dict) else []
            for b in blocks[:3]:
                if isinstance(b, dict) and b.get("position") == "INSIDE" and b.get("strength") == "STRONG":
                    ob_inside = True
                    ax2 = True
                    break

    # AXE 3: MOMENTUM (MACD 4H from analysis)
    ax3 = False
    macd_trend = None
    if bf:
        macd_4h = bf.get("macd_4h", {})
        macd_trend = macd_4h.get("trend") if isinstance(macd_4h, dict) else None
        ax3 = str(macd_trend).upper() == "BULLISH"

    # AXE 4: TIMING (volume ratio from analysis)
    ax4 = False
    vol_ratio = None
    if bf:
        vol_1h = bf.get("vol_spike_1h", {})
        vol_ratio = vol_1h.get("ratio") if isinstance(vol_1h, dict) else None
        ax4 = vol_ratio is not None and vol_ratio < 0.8

    axes = sum(1 for a in [ax1, ax2, ax3, ax4] if a)
    grade = {4: 'A+', 3: 'A', 2: 'B'}.get(axes, 'C')

    details = []
    if ax1: details.append(f"Trend(ADX={adx_4h:.0f},DI={di_spread:.0f})")
    if ax2: details.append("Struct(FVG)" if fvg_pos == "ABOVE" else "Struct(OB)")
    if ax3: details.append("Mom(MACD)")
    if ax4: details.append(f"Time(Vol={vol_ratio:.1f}x)" if vol_ratio else "Time")

    return {
        'grade': grade, 'axes': axes,
        'ax1': ax1, 'ax2': ax2, 'ax3': ax3, 'ax4': ax4,
        'adx_4h': adx_4h, 'di_spread': di_spread, 'fvg_pos': fvg_pos,
        'ob_inside': ob_inside, 'macd': macd_trend, 'vol_ratio': vol_ratio,
        'details': details,
    }


def main():
    from api.realtime_analyze import analyze_alert_realtime

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)
    since = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()

    # Load all alerts
    all_alerts = []
    for offset in range(0, 5000, 1000):
        r = sb.table('alerts').select('*').gte('alert_timestamp', since) \
            .order('alert_timestamp', desc=False).range(offset, offset + 999).execute()
        all_alerts.extend(r.data or [])
        if len(r.data or []) < 1000: break

    print(f"Total alerts: {len(all_alerts)}")

    # Deduplicate
    seen = set()
    unique = []
    for a in all_alerts:
        key = f"{a['pair']}_{a.get('bougie_4h', '')}"
        if key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"Unique (pair/4H): {len(unique)}")

    # Filter
    filtered = [a for a in unique if (a.get('scanner_score', 0) or 0) >= 7 and a.get('timeframes', []) != ['15m']]
    print(f"After score>=7, not 15m-only: {len(filtered)}")

    results = []
    errors = 0
    t_start = time.time()

    for i, alert in enumerate(filtered):
        pair = alert['pair']
        ts = alert.get('alert_timestamp', '')
        price = alert.get('price', 0) or 0
        score = alert.get('scanner_score', 0) or 0

        if i % 25 == 0:
            elapsed = time.time() - t_start
            rate = i / elapsed if elapsed > 0 else 0
            eta = (len(filtered) - i) / rate / 60 if rate > 0 else 0
            print(f"[{i}/{len(filtered)}] {pair:15s} | {elapsed:.0f}s elapsed | ETA {eta:.0f}min")

        try:
            # Full analysis for quality axes
            analysis = analyze_alert_realtime(pair, ts, price)
            quality = compute_axes_from_alert_and_analysis(alert, analysis)

            # Price range 7d (1 API call)
            pr = get_price_range_7d(pair, ts)
            highest = pr['highest']
            lowest = pr['lowest']

            pnl_max = (highest / price - 1) * 100 if price and highest else 0
            pnl_min = (lowest / price - 1) * 100 if price and lowest else 0

            # Outcome
            if pnl_max >= 10:
                outcome = 'WIN'
                pnl_result = 10.0
            elif pnl_min <= -8:
                outcome = 'LOSE'
                pnl_result = -8.0
            else:
                outcome = 'OPEN'
                pnl_result = 0

            results.append({
                'pair': pair, 'ts': ts[:16], 'price': price, 'score': score,
                'tfs': ','.join(alert.get('timeframes', [])),
                'pp': alert.get('pp', False), 'ec': alert.get('ec', False),
                'grade': quality['grade'], 'axes': quality['axes'],
                'ax1': quality['ax1'], 'ax2': quality['ax2'],
                'ax3': quality['ax3'], 'ax4': quality['ax4'],
                'q_details': quality['details'],
                'adx_4h': quality['adx_4h'], 'di_spread': quality['di_spread'],
                'fvg_pos': quality['fvg_pos'], 'ob_inside': quality['ob_inside'],
                'macd': quality['macd'], 'vol_ratio': quality['vol_ratio'],
                'pnl_max': round(pnl_max, 2), 'pnl_min': round(pnl_min, 2),
                'outcome': outcome, 'pnl_result': round(pnl_result, 2),
            })
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  ERROR {pair}: {e}")

        time.sleep(0.05)

    elapsed = time.time() - t_start
    print(f"\nDone! {len(results)} alerts in {elapsed:.0f}s ({elapsed/60:.1f}min) | {errors} errors\n")

    # ═══════════════════════════════════════
    # GENERATE REPORT
    # ═══════════════════════════════════════
    L = []
    L.append("# Backtest Quality Filter 4 Axes — 14 Derniers Jours\n")
    L.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L.append(f"**Periode:** {filtered[0]['alert_timestamp'][:10]} → {filtered[-1]['alert_timestamp'][:10]}")
    L.append(f"**Alertes totales:** {len(all_alerts)} | Uniques: {len(unique)} | Filtrees: {len(filtered)} | Analysees: {len(results)}")
    L.append(f"**TP:** +10% | **SL:** -8% | **Horizon:** 7 jours\n")

    # ── 1. EXPECTANCY ──
    L.append("## 1. Expectancy par Grade\n")
    L.append("| Grade | Trades | WIN | LOSE | OPEN | WR% | Avg Win | Avg Loss | Expectancy | PnL Total |")
    L.append("|-------|--------|-----|------|------|-----|---------|----------|------------|-----------|")

    for grade in ['A+', 'A', 'B', 'C', '---', 'ALL']:
        if grade == '---':
            L.append("|-------|--------|-----|------|------|-----|---------|----------|------------|-----------|")
            continue
        grp = results if grade == 'ALL' else [r for r in results if r['grade'] == grade]
        res = [r for r in grp if r['outcome'] in ('WIN', 'LOSE')]
        w = [r for r in res if r['outcome'] == 'WIN']
        lo = [r for r in res if r['outcome'] == 'LOSE']
        op = [r for r in grp if r['outcome'] == 'OPEN']
        wr = len(w) / len(res) * 100 if res else 0
        aw = sum(r['pnl_result'] for r in w) / len(w) if w else 0
        al = sum(r['pnl_result'] for r in lo) / len(lo) if lo else 0
        exp = (wr / 100 * aw) + ((1 - wr / 100) * al) if res else 0
        tp = sum(r['pnl_result'] for r in res)
        nm = f"**{grade}**" if grade in ('A+', 'A', 'ALL') else grade
        L.append(f"| {nm} | {len(grp)} | {len(w)} | {len(lo)} | {len(op)} | {wr:.1f}% | {aw:+.1f}% | {al:+.1f}% | **{exp:+.2f}%** | {tp:+.1f}% |")

    # ── 2. SIMULATION ──
    L.append("\n## 2. Simulation — Impact du filtre\n")
    L.append("| Filtre | Trades | WIN | LOSE | WR% | PnL Total | Avg/trade | Big Winners (>=+20%) |")
    L.append("|--------|--------|-----|------|-----|-----------|-----------|----------------------|")

    for label, vg in [("Aucun filtre", ['A+','A','B','C']), ("**>= Grade A**", ['A+','A']), (">= Grade B", ['A+','A','B']), ("Grade A+ seul", ['A+'])]:
        kept = [r for r in results if r['grade'] in vg]
        res = [r for r in kept if r['outcome'] in ('WIN','LOSE')]
        w = len([r for r in res if r['outcome']=='WIN']); lo = len([r for r in res if r['outcome']=='LOSE'])
        wr = w/len(res)*100 if res else 0; pnl = sum(r['pnl_result'] for r in res)
        avg_t = pnl/len(res) if res else 0
        bw = len([r for r in kept if r['pnl_max'] >= 20])
        L.append(f"| {label} | {len(kept)} | {w} | {lo} | {wr:.1f}% | {pnl:+.1f}% | {avg_t:+.2f}% | {bw} |")

    # ── 3. PNL MAX DISTRIBUTION ──
    L.append("\n## 3. Distribution PnL Max par Grade\n")
    L.append("| Grade | N | PnL Max Avg | >=+5% | >=+10% | >=+20% | >=+30% | >=+50% |")
    L.append("|-------|---|-------------|-------|--------|--------|--------|--------|")
    for grade in ['A+', 'A', 'B', 'C']:
        grp = [r for r in results if r['grade'] == grade]
        if not grp: continue
        am = sum(r['pnl_max'] for r in grp)/len(grp)
        L.append(f"| {grade} | {len(grp)} | {am:+.1f}% | {len([r for r in grp if r['pnl_max']>=5])} ({len([r for r in grp if r['pnl_max']>=5])/len(grp)*100:.0f}%) | {len([r for r in grp if r['pnl_max']>=10])} ({len([r for r in grp if r['pnl_max']>=10])/len(grp)*100:.0f}%) | {len([r for r in grp if r['pnl_max']>=20])} ({len([r for r in grp if r['pnl_max']>=20])/len(grp)*100:.0f}%) | {len([r for r in grp if r['pnl_max']>=30])} ({len([r for r in grp if r['pnl_max']>=30])/len(grp)*100:.0f}%) | {len([r for r in grp if r['pnl_max']>=50])} ({len([r for r in grp if r['pnl_max']>=50])/len(grp)*100:.0f}%) |")

    # ── 4. DETAIL GRADE A+ et A ──
    a_trades = sorted([r for r in results if r['grade'] in ('A+', 'A')], key=lambda x: -x['pnl_max'])
    L.append(f"\n## 4. Detail des {len(a_trades)} alertes Grade A+ et A\n")
    L.append("| # | Pair | Date | Score | Grade | T | S | M | Ti | PnL Max | PnL Min | Outcome | Details |")
    L.append("|---|------|------|-------|-------|---|---|---|-----|---------|---------|---------|---------|")
    for idx, r in enumerate(a_trades, 1):
        t='✅' if r['ax1'] else '❌'; ss='✅' if r['ax2'] else '❌'; m='✅' if r['ax3'] else '❌'; ti='✅' if r['ax4'] else '❌'
        det = ', '.join(r['q_details'])
        L.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {t} | {ss} | {m} | {ti} | {r['pnl_max']:+.1f}% | {r['pnl_min']:+.1f}% | {r['outcome']} | {det} |")

    # ── 5. GRADE B/C BIG WINNERS (missed) ──
    bc_big = sorted([r for r in results if r['grade'] in ('B','C') and r['pnl_max'] >= 14], key=lambda x: -x['pnl_max'])
    if bc_big:
        L.append(f"\n## 5. Opportunites manquees — Grade B/C avec PnL Max >= +14%\n")
        L.append("| # | Pair | Date | Score | Grade | Axes | PnL Max | Details |")
        L.append("|---|------|------|-------|-------|------|---------|---------|")
        for idx, r in enumerate(bc_big, 1):
            det = ', '.join(r['q_details'])
            L.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {r['axes']}/4 | {r['pnl_max']:+.1f}% | {det} |")

    # ── 6. TOP 30 ──
    L.append(f"\n## 6. Top 30 Performers\n")
    top = sorted(results, key=lambda x: -x['pnl_max'])[:30]
    L.append("| # | Pair | Date | Score | Grade | PnL Max | PnL Min | Outcome |")
    L.append("|---|------|------|-------|-------|---------|---------|---------|")
    for idx, r in enumerate(top, 1):
        L.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | **{r['grade']}** | **{r['pnl_max']:+.1f}%** | {r['pnl_min']:+.1f}% | {r['outcome']} |")

    # ── 7. RESUME ──
    L.append(f"\n## 7. Resume et Conclusion\n")
    res_all = [r for r in results if r['outcome'] in ('WIN','LOSE')]
    res_a = [r for r in results if r['grade'] in ('A+','A') and r['outcome'] in ('WIN','LOSE')]

    if res_all:
        w = len([r for r in res_all if r['outcome']=='WIN']); lo = len(res_all)-w
        wr = w/len(res_all)*100; pnl = sum(r['pnl_result'] for r in res_all)
        L.append(f"### Sans filtre")
        L.append(f"- **{len(res_all)}** trades resolus ({w}W / {lo}L)")
        L.append(f"- Win Rate: **{wr:.1f}%**")
        L.append(f"- PnL Total: **{pnl:+.1f}%**")
        L.append(f"- Avg/trade: **{pnl/len(res_all):+.2f}%**\n")

    if res_a:
        w = len([r for r in res_a if r['outcome']=='WIN']); lo = len(res_a)-w
        wr = w/len(res_a)*100; pnl = sum(r['pnl_result'] for r in res_a)
        avoided = len(res_all) - len(res_a)
        avoided_l = len([r for r in res_all if r['outcome']=='LOSE' and r['grade'] not in ('A+','A')])
        L.append(f"### Avec filtre >= Grade A")
        L.append(f"- **{len(res_a)}** trades resolus ({w}W / {lo}L)")
        L.append(f"- Win Rate: **{wr:.1f}%**")
        L.append(f"- PnL Total: **{pnl:+.1f}%**")
        L.append(f"- Avg/trade: **{pnl/len(res_a):+.2f}%**")
        L.append(f"- Trades evites: **{avoided}** (dont **{avoided_l}** pertes)\n")

    L.append("---\n*Genere par backtest_quality_fast.py*\n")

    # Write
    report_path = ROOT / "docs" / "BACKTEST_QUALITY_FILTER_14J.md"
    report_path.write_text('\n'.join(L), encoding='utf-8')
    print(f"Report: {report_path}")

    # Summary
    print(f"\n{'='*60}")
    for grade in ['A+', 'A', 'B', 'C']:
        grp = [r for r in results if r['grade'] == grade]
        res = [r for r in grp if r['outcome'] in ('WIN','LOSE')]
        w = len([r for r in res if r['outcome']=='WIN'])
        lo = len(res) - w
        wr = w/len(res)*100 if res else 0
        pnl = sum(r['pnl_result'] for r in res)
        bw = len([r for r in grp if r['pnl_max'] >= 14])
        print(f"  {grade:3s}: {len(grp):4d} trades | {w}W/{lo}L WR={wr:.1f}% | PnL={pnl:+.1f}% | BigW={bw}")


if __name__ == "__main__":
    main()
