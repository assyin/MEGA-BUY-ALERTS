#!/usr/bin/env python3
"""
Backtest the 4-axis Quality Filter on all alerts from the last 14 days.
For each alert: run realtime analysis, compute quality grade, simulate trade outcome.
Generate detailed .md report.
"""
import sys, time, re, json
from pathlib import Path
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backtest"))

from openclaw.config import get_settings
from supabase import create_client
from api.realtime_analyze import analyze_alert_realtime
import requests

BINANCE_URL = "https://api.binance.com/api/v3/klines"


def get_price_after(pair: str, alert_ts_iso: str, hours: int) -> float:
    """Get the price N hours after the alert timestamp."""
    try:
        ts = datetime.fromisoformat(alert_ts_iso.replace('+00:00', '+00:00'))
        target_ms = int((ts.timestamp() + hours * 3600) * 1000)
        # Get 1h candle at target time
        resp = requests.get(BINANCE_URL, params={
            'symbol': pair, 'interval': '1h', 'limit': 1, 'endTime': target_ms
        }, timeout=10)
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            return float(data[0][4])  # close price
    except:
        pass
    return 0


def get_price_range(pair: str, alert_ts_iso: str, hours: int) -> dict:
    """Get highest and lowest price within N hours after alert."""
    try:
        ts = datetime.fromisoformat(alert_ts_iso.replace('+00:00', '+00:00'))
        start_ms = int(ts.timestamp() * 1000)
        end_ms = int((ts.timestamp() + hours * 3600) * 1000)
        # Get 15m candles for precision
        resp = requests.get(BINANCE_URL, params={
            'symbol': pair, 'interval': '15m', 'limit': hours * 4,
            'startTime': start_ms, 'endTime': end_ms
        }, timeout=10)
        data = resp.json()
        if data and isinstance(data, list) and len(data) > 0:
            highs = [float(c[2]) for c in data]
            lows = [float(c[3]) for c in data]
            return {
                'highest': max(highs),
                'lowest': min(lows),
                'close': float(data[-1][4]),
                'candles': len(data)
            }
    except:
        pass
    return {'highest': 0, 'lowest': 0, 'close': 0, 'candles': 0}


def compute_quality_axes(analysis: dict, alert: dict) -> dict:
    """Compute 4-axis quality filter from realtime analysis data."""
    bf = analysis.get("bonus_filters", {})
    indicators = analysis.get("indicators", {})

    # AXE 1: TREND (ADX 4H > 40 OR DI spread 4H > 20)
    adx_4h_data = bf.get("adx_4h", {})
    adx_val = adx_4h_data.get("adx") if isinstance(adx_4h_data, dict) else None
    di_plus = adx_4h_data.get("di_plus") if isinstance(adx_4h_data, dict) else None
    di_minus = adx_4h_data.get("di_minus") if isinstance(adx_4h_data, dict) else None

    # Fallback to alert data
    if adx_val is None:
        adx_val = alert.get("adx_4h")
    if di_plus is None:
        di_plus = alert.get("di_plus_4h")
    if di_minus is None:
        di_minus = alert.get("di_minus_4h")

    di_spread = (di_plus or 0) - (di_minus or 0)
    ax1 = (adx_val is not None and adx_val > 40) or (di_spread > 20)

    # AXE 2: STRUCTURE (FVG 1H ABOVE OR OB INSIDE STRONG)
    fvg_1h = bf.get("fvg_1h", {})
    fvg_pos = fvg_1h.get("position") if isinstance(fvg_1h, dict) else None
    fvg_above = fvg_pos == "ABOVE"

    ob_1h = bf.get("ob_1h", {})
    ob_blocks = ob_1h.get("blocks", []) if isinstance(ob_1h, dict) else []
    ob_inside_strong = False
    for block in ob_blocks[:3]:
        if isinstance(block, dict):
            if block.get("position") == "INSIDE" and block.get("strength") == "STRONG":
                ob_inside_strong = True
                break

    # Also check 4H OB
    ob_4h = bf.get("ob_4h", {})
    ob_blocks_4h = ob_4h.get("blocks", []) if isinstance(ob_4h, dict) else []
    for block in ob_blocks_4h[:3]:
        if isinstance(block, dict):
            if block.get("position") == "INSIDE" and block.get("strength") == "STRONG":
                ob_inside_strong = True
                break

    ax2 = fvg_above or ob_inside_strong

    # AXE 3: MOMENTUM (MACD 4H Bullish)
    macd_4h = bf.get("macd_4h", {})
    macd_trend = macd_4h.get("trend") if isinstance(macd_4h, dict) else None
    ax3 = str(macd_trend).upper() == "BULLISH"

    # AXE 4: TIMING (Vol ratio < 0.8)
    vol_1h = bf.get("vol_spike_1h", {})
    vol_ratio = vol_1h.get("ratio") if isinstance(vol_1h, dict) else None
    ax4 = vol_ratio is not None and vol_ratio < 0.8

    axes_n = sum(1 for a in [ax1, ax2, ax3, ax4] if a)
    grade = {4: 'A+', 3: 'A', 2: 'B'}.get(axes_n, 'C')

    details = []
    if ax1: details.append(f"Trend(ADX={adx_val:.0f},DI_sp={di_spread:.0f})" if adx_val else "Trend(DI)")
    if ax2: details.append("Struct(FVG_ABOVE)" if fvg_above else "Struct(OB_INSIDE)")
    if ax3: details.append("Mom(MACD4H)")
    if ax4: details.append(f"Timing(Vol={vol_ratio:.1f}x)" if vol_ratio else "Timing")

    return {
        'grade': grade, 'axes': axes_n,
        'ax1': ax1, 'ax2': ax2, 'ax3': ax3, 'ax4': ax4,
        'adx_4h': adx_val, 'di_spread': di_spread, 'di_plus': di_plus, 'di_minus': di_minus,
        'fvg_pos': fvg_pos, 'ob_inside': ob_inside_strong, 'macd_4h': macd_trend,
        'vol_ratio': vol_ratio, 'details': details,
    }


def main():
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

    # Deduplicate: keep first alert per pair per 4H candle
    seen = set()
    unique = []
    for a in all_alerts:
        key = f"{a['pair']}_{a.get('bougie_4h', '')}"
        if key not in seen:
            seen.add(key)
            unique.append(a)

    print(f"Unique (per pair per 4H candle): {len(unique)}")

    # Filter: score >= 7 and not 15m-only
    filtered = []
    for a in unique:
        score = a.get('scanner_score', 0) or 0
        tfs = a.get('timeframes', [])
        if score < 7:
            continue
        if tfs == ['15m']:
            continue
        filtered.append(a)

    print(f"After score>=7 and not 15m-only: {len(filtered)}")
    print(f"Processing...\n")

    results = []
    for i, alert in enumerate(filtered):
        pair = alert['pair']
        ts = alert.get('alert_timestamp', '')
        price = alert.get('price', 0) or 0
        score = alert.get('scanner_score', 0)

        if i % 50 == 0:
            print(f"[{i}/{len(filtered)}] Processing...")

        try:
            # Run realtime analysis
            analysis = analyze_alert_realtime(pair, ts, price)

            # Compute quality grade
            quality = compute_quality_axes(analysis, alert)

            # Get price after 24h, 48h, 72h, 7days
            range_48h = get_price_range(pair, ts, 48)
            range_7d = get_price_range(pair, ts, 168)

            highest_48h = range_48h['highest']
            lowest_48h = range_48h['lowest']
            close_48h = range_48h['close']
            highest_7d = range_7d['highest']
            lowest_7d = range_7d['lowest']

            # PnL calculations
            if price > 0:
                pnl_max_48h = (highest_48h / price - 1) * 100 if highest_48h else 0
                pnl_min_48h = (lowest_48h / price - 1) * 100 if lowest_48h else 0
                pnl_48h = (close_48h / price - 1) * 100 if close_48h else 0
                pnl_max_7d = (highest_7d / price - 1) * 100 if highest_7d else 0
                pnl_min_7d = (lowest_7d / price - 1) * 100 if lowest_7d else 0
            else:
                pnl_max_48h = pnl_min_48h = pnl_48h = pnl_max_7d = pnl_min_7d = 0

            # WIN/LOSE outcome (TP=+10%, SL=-8%)
            if pnl_max_7d >= 10:
                outcome = 'WIN'
                pnl_result = 10.0
            elif pnl_min_7d <= -8:
                outcome = 'LOSE'
                pnl_result = -8.0
            else:
                outcome = 'PENDING'
                pnl_result = pnl_48h

            results.append({
                'pair': pair, 'ts': ts[:16], 'price': price, 'score': score,
                'tfs': alert.get('timeframes', []),
                'pp': alert.get('pp', False), 'ec': alert.get('ec', False),
                'di_plus': alert.get('di_plus_4h'), 'di_minus': alert.get('di_minus_4h'),
                'adx_4h': alert.get('adx_4h'),
                'grade': quality['grade'], 'axes': quality['axes'],
                'ax1': quality['ax1'], 'ax2': quality['ax2'], 'ax3': quality['ax3'], 'ax4': quality['ax4'],
                'q_adx': quality['adx_4h'], 'q_di_spread': quality['di_spread'],
                'q_fvg': quality['fvg_pos'], 'q_ob': quality['ob_inside'],
                'q_macd': quality['macd_4h'], 'q_vol': quality['vol_ratio'],
                'q_details': quality['details'],
                'pnl_max_48h': round(pnl_max_48h, 2),
                'pnl_min_48h': round(pnl_min_48h, 2),
                'pnl_max_7d': round(pnl_max_7d, 2),
                'pnl_min_7d': round(pnl_min_7d, 2),
                'outcome': outcome, 'pnl_result': round(pnl_result, 2),
            })
        except Exception as e:
            print(f"  ERROR {pair}: {e}")
            continue

        time.sleep(0.05)

    print(f"\nProcessed {len(results)} alerts. Generating report...\n")

    # ═══════════════════════════════════════════════════════
    # GENERATE REPORT
    # ═══════════════════════════════════════════════════════
    lines = []
    lines.append("# Backtest Quality Filter 4 Axes — 14 Derniers Jours\n")
    lines.append(f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"**Periode:** {filtered[0]['alert_timestamp'][:10]} → {filtered[-1]['alert_timestamp'][:10]}")
    lines.append(f"**Alertes scannees:** {len(all_alerts)}")
    lines.append(f"**Apres dedup (pair/4H):** {len(unique)}")
    lines.append(f"**Apres filtre score>=7:** {len(filtered)}")
    lines.append(f"**Analysees avec succes:** {len(results)}\n")

    lines.append("## Methode\n")
    lines.append("Chaque alerte est analysee avec `analyze_alert_realtime()` pour obtenir les 197 indicateurs,")
    lines.append("puis classee par le filtre 4 axes :\n")
    lines.append("| Axe | Critere | Edge vs Losers |")
    lines.append("|-----|---------|----------------|")
    lines.append("| 1. Trend | ADX 4H > 40 OU DI spread > 20 | +43% |")
    lines.append("| 2. Structure | FVG 1H ABOVE OU OB INSIDE STRONG | +38% |")
    lines.append("| 3. Momentum | MACD 4H Bullish | +26% |")
    lines.append("| 4. Timing | Volume ratio < 0.8x | +38% |")
    lines.append("")
    lines.append("**TP = +10% | SL = -8% | Horizon = 7 jours**\n")

    # ── EXPECTANCY PAR GRADE ──
    lines.append("## 1. Expectancy par Grade\n")
    lines.append("| Grade | Trades | WIN | LOSE | PENDING | WR% | Avg Win | Avg Loss | Expectancy | PnL Total |")
    lines.append("|-------|--------|-----|------|---------|-----|---------|----------|------------|-----------|")

    for grade in ['A+', 'A', 'B', 'C', 'ALL']:
        grp = results if grade == 'ALL' else [r for r in results if r['grade'] == grade]
        resolved = [r for r in grp if r['outcome'] in ('WIN', 'LOSE')]
        wins = [r for r in resolved if r['outcome'] == 'WIN']
        losses = [r for r in resolved if r['outcome'] == 'LOSE']
        pending = [r for r in grp if r['outcome'] == 'PENDING']
        wr = len(wins) / len(resolved) * 100 if resolved else 0
        aw = sum(r['pnl_result'] for r in wins) / len(wins) if wins else 0
        al = sum(r['pnl_result'] for r in losses) / len(losses) if losses else 0
        exp = (wr / 100 * aw) + ((1 - wr / 100) * al) if resolved else 0
        tp = sum(r['pnl_result'] for r in resolved)
        name = f"**{grade}**" if grade in ('A+', 'A', 'ALL') else grade
        lines.append(f"| {name} | {len(grp)} | {len(wins)} | {len(losses)} | {len(pending)} | {wr:.1f}% | {aw:+.1f}% | {al:+.1f}% | {exp:+.2f}% | {tp:+.1f}% |")

    # ── SIMULATION FILTRE ──
    lines.append("\n## 2. Simulation — Impact du filtre\n")
    lines.append("| Filtre | Trades | WIN | LOSE | WR% | PnL | Avg/trade | BigW (>=+14%) |")
    lines.append("|--------|--------|-----|------|-----|-----|-----------|---------------|")

    for label, valid_grades in [("Aucun (baseline)", ['A+','A','B','C']), (">= A (recommande)", ['A+','A']), (">= B", ['A+','A','B']), ("A+ seulement", ['A+'])]:
        kept = [r for r in results if r['grade'] in valid_grades]
        res = [r for r in kept if r['outcome'] in ('WIN','LOSE')]
        w = len([r for r in res if r['outcome'] == 'WIN'])
        l = len([r for r in res if r['outcome'] == 'LOSE'])
        wr = w / len(res) * 100 if res else 0
        pnl = sum(r['pnl_result'] for r in res)
        avg_t = pnl / len(res) if res else 0
        bw = len([r for r in kept if r['pnl_max_7d'] >= 14])
        lines.append(f"| {label} | {len(kept)} | {w} | {l} | {wr:.1f}% | {pnl:+.1f}% | {avg_t:+.2f}% | {bw} |")

    # ── PNL MAX DISTRIBUTION ──
    lines.append("\n## 3. Distribution PnL Max (7j)\n")
    lines.append("| Grade | Trades | PnL Max Avg | >=+5% | >=+10% | >=+20% | >=+30% |")
    lines.append("|-------|--------|-------------|-------|--------|--------|--------|")

    for grade in ['A+', 'A', 'B', 'C']:
        grp = [r for r in results if r['grade'] == grade]
        if not grp: continue
        avg_mx = sum(r['pnl_max_7d'] for r in grp) / len(grp)
        h5 = len([r for r in grp if r['pnl_max_7d'] >= 5])
        h10 = len([r for r in grp if r['pnl_max_7d'] >= 10])
        h20 = len([r for r in grp if r['pnl_max_7d'] >= 20])
        h30 = len([r for r in grp if r['pnl_max_7d'] >= 30])
        lines.append(f"| {grade} | {len(grp)} | {avg_mx:+.1f}% | {h5} ({h5/len(grp)*100:.0f}%) | {h10} ({h10/len(grp)*100:.0f}%) | {h20} ({h20/len(grp)*100:.0f}%) | {h30} ({h30/len(grp)*100:.0f}%) |")

    # ── DETAIL GRADE A+ AND A ──
    lines.append("\n## 4. Detail des alertes Grade A+ et A\n")
    a_trades = sorted([r for r in results if r['grade'] in ('A+', 'A')], key=lambda x: -x['pnl_max_7d'])

    lines.append(f"| # | Pair | Date | Score | Grade | Axes | Trend | Struct | Mom | Time | PnL Max 48h | PnL Max 7d | Outcome | Details |")
    lines.append(f"|---|------|------|-------|-------|------|-------|--------|-----|------|-------------|------------|---------|---------|")

    for idx, r in enumerate(a_trades, 1):
        t = '✅' if r['ax1'] else '❌'
        s = '✅' if r['ax2'] else '❌'
        m = '✅' if r['ax3'] else '❌'
        ti = '✅' if r['ax4'] else '❌'
        det = ', '.join(r['q_details'])
        lines.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {r['axes']}/4 | {t} | {s} | {m} | {ti} | {r['pnl_max_48h']:+.1f}% | {r['pnl_max_7d']:+.1f}% | {r['outcome']} | {det} |")

    # ── DETAIL GRADE B BIG WINNERS ──
    b_big = [r for r in results if r['grade'] in ('B', 'C') and r['pnl_max_7d'] >= 14]
    if b_big:
        lines.append(f"\n## 5. Grade B/C avec PnL Max >= +14% (opportunites manquees)\n")
        lines.append(f"| Pair | Date | Score | Grade | PnL Max 7d | Axes | Details |")
        lines.append(f"|------|------|-------|-------|------------|------|---------|")
        for r in sorted(b_big, key=lambda x: -x['pnl_max_7d']):
            det = ', '.join(r['q_details'])
            lines.append(f"| {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {r['pnl_max_7d']:+.1f}% | {r['axes']}/4 | {det} |")

    # ── TOP PERFORMERS ──
    lines.append(f"\n## 6. Top 20 Performers (PnL Max 7d)\n")
    top = sorted(results, key=lambda x: -x['pnl_max_7d'])[:20]
    lines.append(f"| # | Pair | Date | Score | Grade | PnL Max 7d | PnL Min 7d | Outcome |")
    lines.append(f"|---|------|------|-------|-------|------------|------------|---------|")
    for idx, r in enumerate(top, 1):
        lines.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {r['pnl_max_7d']:+.1f}% | {r['pnl_min_7d']:+.1f}% | {r['outcome']} |")

    # ── WORST PERFORMERS ──
    lines.append(f"\n## 7. Top 20 Worst (PnL Min 7d)\n")
    worst = sorted(results, key=lambda x: x['pnl_min_7d'])[:20]
    lines.append(f"| # | Pair | Date | Score | Grade | PnL Max 7d | PnL Min 7d | Outcome |")
    lines.append(f"|---|------|------|-------|-------|------------|------------|---------|")
    for idx, r in enumerate(worst, 1):
        lines.append(f"| {idx} | {r['pair']} | {r['ts'][5:]} | {r['score']}/10 | {r['grade']} | {r['pnl_max_7d']:+.1f}% | {r['pnl_min_7d']:+.1f}% | {r['outcome']} |")

    # ── SUMMARY ──
    res_all = [r for r in results if r['outcome'] in ('WIN','LOSE')]
    res_a = [r for r in results if r['grade'] in ('A+','A') and r['outcome'] in ('WIN','LOSE')]

    lines.append(f"\n## 8. Resume\n")
    lines.append(f"### Sans filtre (baseline)")
    if res_all:
        w = len([r for r in res_all if r['outcome']=='WIN'])
        l = len([r for r in res_all if r['outcome']=='LOSE'])
        wr = w/len(res_all)*100
        pnl = sum(r['pnl_result'] for r in res_all)
        lines.append(f"- Trades resolus: {len(res_all)} ({w}W / {l}L)")
        lines.append(f"- Win Rate: {wr:.1f}%")
        lines.append(f"- PnL Total: {pnl:+.1f}%")
        lines.append(f"- Avg/trade: {pnl/len(res_all):+.2f}%")

    lines.append(f"\n### Avec filtre >= A")
    if res_a:
        w = len([r for r in res_a if r['outcome']=='WIN'])
        l = len([r for r in res_a if r['outcome']=='LOSE'])
        wr = w/len(res_a)*100
        pnl = sum(r['pnl_result'] for r in res_a)
        lines.append(f"- Trades resolus: {len(res_a)} ({w}W / {l}L)")
        lines.append(f"- Win Rate: {wr:.1f}%")
        lines.append(f"- PnL Total: {pnl:+.1f}%")
        lines.append(f"- Avg/trade: {pnl/len(res_a):+.2f}%")

        avoided = len(res_all) - len(res_a)
        avoided_losses = len([r for r in res_all if r['outcome']=='LOSE' and r['grade'] not in ('A+','A')])
        lines.append(f"- Trades evites: {avoided} (dont {avoided_losses} pertes)")

    lines.append(f"\n---\n*Genere automatiquement par backtest_quality_filter.py*")

    # Write report
    report_path = ROOT / "docs" / "BACKTEST_QUALITY_FILTER_14J.md"
    report_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"\nReport saved to: {report_path}")

    # Print summary
    print(f"\n{'='*60}")
    print(f"RESUME RAPIDE")
    print(f"{'='*60}")
    for grade in ['A+', 'A', 'B', 'C']:
        grp = [r for r in results if r['grade'] == grade]
        res = [r for r in grp if r['outcome'] in ('WIN','LOSE')]
        w = len([r for r in res if r['outcome']=='WIN'])
        l = len([r for r in res if r['outcome']=='LOSE'])
        wr = w/len(res)*100 if res else 0
        pnl = sum(r['pnl_result'] for r in res)
        print(f"  {grade}: {len(grp)} trades | {w}W/{l}L WR={wr:.1f}% | PnL={pnl:+.1f}%")


if __name__ == "__main__":
    main()
