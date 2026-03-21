#!/usr/bin/env python3
"""
Analyse APPROFONDIE: Trajet du prix vs Value Area AVANT le break
Vérifie si le prix était sous la VA dans les heures/jours précédant le break
"""

import requests
import json
from datetime import datetime, timedelta
from collections import defaultdict

API_URL = "http://localhost:8000"

def get_all_backtests_with_trades():
    """Get all backtests that have trades"""
    response = requests.get(f"{API_URL}/api/backtests")
    data = response.json()
    return [b for b in data if b['total_trades'] > 0]

def get_alerts_for_backtest(backtest_id):
    """Get all alerts for a backtest"""
    response = requests.get(f"{API_URL}/api/backtests/{backtest_id}/alerts")
    return response.json()

def get_trades_for_backtest(backtest_id):
    """Get all trades for a backtest"""
    response = requests.get(f"{API_URL}/api/backtests/{backtest_id}/trades")
    return response.json()

def get_historical_data(symbol, start_time, end_time, interval='1h'):
    """Get historical price data from Binance"""
    try:
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': int(start_time.timestamp() * 1000),
            'endTime': int(end_time.timestamp() * 1000),
            'limit': 100
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [{
                'time': datetime.fromtimestamp(k[0]/1000),
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
                'volume': float(k[5])
            } for k in data]
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return []

def analyze_price_trajectory(symbol, alert, trade, lookback_hours=48):
    """
    Analyze price trajectory relative to VA in the hours before the break
    """
    result = {
        'symbol': symbol,
        'alert_datetime': alert['alert_datetime'],
        'timeframe': alert['timeframe'],
        'pnl_c': trade['pnl_c'],
        'is_win': trade['pnl_c'] > 0,
        'exit_reason': trade['exit_reason_c'],
        'vp_grade': alert.get('vp_grade'),
        'vp_val_1h': alert.get('vp_val_1h'),
        'vp_poc_1h': alert.get('vp_poc_1h'),
        'vp_vah_1h': alert.get('vp_vah_1h'),
        'vp_entry_position_1h': alert.get('vp_entry_position_1h'),
        'vp_label': alert.get('vp_label'),
        # Trajectory analysis
        'hours_below_va': 0,
        'hours_in_va': 0,
        'hours_above_va': 0,
        'pct_time_below_va': 0,
        'min_price_vs_val': None,
        'max_price_vs_val': None,
        'trajectory_pattern': None,
        'retest_detected': False,
        'retest_rejected': False,
    }

    val = alert.get('vp_val_1h')
    poc = alert.get('vp_poc_1h')
    vah = alert.get('vp_vah_1h')

    if not val or not poc or not vah:
        result['trajectory_pattern'] = 'NO_VP_DATA'
        return result

    # Get historical data before the alert
    try:
        alert_dt = datetime.fromisoformat(alert['alert_datetime'].replace('Z', '+00:00'))
    except:
        alert_dt = datetime.strptime(alert['alert_datetime'], '%Y-%m-%dT%H:%M:%S')

    start_dt = alert_dt - timedelta(hours=lookback_hours)

    candles = get_historical_data(symbol, start_dt, alert_dt, '1h')

    if not candles:
        result['trajectory_pattern'] = 'NO_HISTORICAL_DATA'
        return result

    below_va_count = 0
    in_va_count = 0
    above_va_count = 0
    min_vs_val = float('inf')
    max_vs_val = float('-inf')

    for candle in candles:
        close = candle['close']
        vs_val_pct = ((close - val) / val) * 100

        min_vs_val = min(min_vs_val, vs_val_pct)
        max_vs_val = max(max_vs_val, vs_val_pct)

        if close < val:
            below_va_count += 1
        elif close > vah:
            above_va_count += 1
        else:
            in_va_count += 1

    total_candles = len(candles)
    result['hours_below_va'] = below_va_count
    result['hours_in_va'] = in_va_count
    result['hours_above_va'] = above_va_count
    result['pct_time_below_va'] = (below_va_count / total_candles * 100) if total_candles > 0 else 0
    result['min_price_vs_val'] = min_vs_val
    result['max_price_vs_val'] = max_vs_val

    # Determine trajectory pattern
    if below_va_count > total_candles * 0.7:
        result['trajectory_pattern'] = 'MOSTLY_BELOW_VA'
    elif above_va_count > total_candles * 0.7:
        result['trajectory_pattern'] = 'MOSTLY_ABOVE_VA'
    elif below_va_count > 0 and above_va_count > 0:
        # Check the last few candles to see if price crossed from below to above
        last_candles = candles[-5:] if len(candles) >= 5 else candles
        last_positions = []
        for c in last_candles:
            if c['close'] < val:
                last_positions.append('below')
            elif c['close'] > vah:
                last_positions.append('above')
            else:
                last_positions.append('in')

        if 'below' in last_positions[:2] and ('in' in last_positions[-2:] or 'above' in last_positions[-2:]):
            result['trajectory_pattern'] = 'CROSS_UP_FROM_BELOW'
        elif 'above' in last_positions[:2] and ('in' in last_positions[-2:] or 'below' in last_positions[-2:]):
            result['trajectory_pattern'] = 'CROSS_DOWN_FROM_ABOVE'
        else:
            result['trajectory_pattern'] = 'MIXED'
    else:
        result['trajectory_pattern'] = 'MOSTLY_IN_VA'

    # Check for retest patterns
    vp_val_retested = alert.get('vp_val_retested', False)
    vp_val_retest_rejected = alert.get('vp_val_retest_rejected', False)
    vp_poc_retested = alert.get('vp_poc_retested', False)

    result['retest_detected'] = vp_val_retested or vp_poc_retested
    result['retest_rejected'] = vp_val_retest_rejected

    return result


def main():
    print("=" * 90)
    print("ANALYSE APPROFONDIE: Trajet du Prix vs Value Area (48h avant break)")
    print("=" * 90)
    print()

    # Get all backtests with trades
    backtests = get_all_backtests_with_trades()
    print(f"📊 Backtests avec trades: {len(backtests)}")

    all_analyses = []
    processed = 0

    for bt in backtests:
        symbol = bt['symbol']
        bt_id = bt['id']

        alerts = get_alerts_for_backtest(bt_id)
        trades = get_trades_for_backtest(bt_id)

        if not alerts or not trades:
            continue

        # Match alerts with trades
        for trade in trades:
            trade_entry_dt = trade['entry_datetime']
            trade_alert_dt = trade['alert_datetime']

            # Find the matching alert
            matching_alert = None
            for alert in alerts:
                if alert.get('entry_datetime') == trade_entry_dt or alert['alert_datetime'] == trade_alert_dt:
                    matching_alert = alert
                    break

            if matching_alert and matching_alert.get('vp_val_1h'):
                analysis = analyze_price_trajectory(symbol, matching_alert, trade)
                all_analyses.append(analysis)
                processed += 1

                # Progress indicator
                if processed % 10 == 0:
                    print(f"⏳ Analysé {processed} trades...")

    print(f"\n📈 Total trades analysés avec VP data: {len(all_analyses)}")
    print()

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSE PAR TRAJECTORY PATTERN
    # ═══════════════════════════════════════════════════════════════════

    print("=" * 90)
    print("RÉSULTATS PAR PATTERN DE TRAJECTOIRE")
    print("=" * 90)
    print()

    by_pattern = defaultdict(list)
    for a in all_analyses:
        pattern = a['trajectory_pattern'] or 'UNKNOWN'
        by_pattern[pattern].append(a)

    pattern_stats = {}

    for pattern in sorted(by_pattern.keys()):
        trades = by_pattern[pattern]
        if not trades:
            continue

        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]

        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total > 0 else 0

        avg_pnl = sum(t['pnl_c'] for t in trades) / total if total > 0 else 0
        avg_pct_below = sum(t['pct_time_below_va'] for t in trades) / total if total > 0 else 0

        pattern_stats[pattern] = {
            'total': total,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_pct_below': avg_pct_below
        }

        print(f"┌{'─' * 88}┐")
        print(f"│ {pattern:<86} │")
        print(f"├{'─' * 88}┤")
        print(f"│ Total: {total:>3} | Wins: {win_count:>3} ({win_rate:>5.1f}%) | Losses: {loss_count:>3} ({100-win_rate:>5.1f}%) | Avg PnL: {avg_pnl:>+6.2f}% │")
        print(f"│ Avg % temps sous VA: {avg_pct_below:>5.1f}%{' ' * 57}│")
        print(f"└{'─' * 88}┘")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # DÉTAIL: MOSTLY_BELOW_VA (votre hypothèse)
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 90)
    print("DÉTAIL: Trades avec trajectoire MOSTLY_BELOW_VA (>70% du temps sous VA)")
    print("=" * 90)
    print()

    mostly_below = by_pattern.get('MOSTLY_BELOW_VA', [])

    if mostly_below:
        print(f"{'Symbol':<15} {'Alert Date':<18} {'PnL':<8} {'Result':<6} {'%Below':<8} {'MinVsVAL':<10} {'VP Grade'}")
        print("-" * 90)

        for t in sorted(mostly_below, key=lambda x: x['pnl_c']):
            result = "WIN" if t['is_win'] else "LOSS"
            min_vs_val = f"{t['min_price_vs_val']:+.2f}%" if t['min_price_vs_val'] else "N/A"
            vp_grade = t['vp_grade'] or "N/A"
            pct_below = f"{t['pct_time_below_va']:.1f}%"
            print(f"{t['symbol']:<15} {t['alert_datetime']:<18} {t['pnl_c']:>+6.2f}% {result:<6} {pct_below:<8} {min_vs_val:<10} {vp_grade}")
    else:
        print("Aucun trade avec >70% du temps sous VA trouvé.")

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSE PAR POURCENTAGE DE TEMPS SOUS VA
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 90)
    print("ANALYSE: Win Rate par % de temps sous VA")
    print("=" * 90)
    print()

    # Group by % time below VA buckets
    buckets = {
        '0-20%': [],
        '20-40%': [],
        '40-60%': [],
        '60-80%': [],
        '80-100%': []
    }

    for a in all_analyses:
        pct = a['pct_time_below_va']
        if pct < 20:
            buckets['0-20%'].append(a)
        elif pct < 40:
            buckets['20-40%'].append(a)
        elif pct < 60:
            buckets['40-60%'].append(a)
        elif pct < 80:
            buckets['60-80%'].append(a)
        else:
            buckets['80-100%'].append(a)

    print(f"{'% Temps sous VA':<15} {'Total':<8} {'Wins':<8} {'Losses':<8} {'Win Rate':<10} {'Avg PnL'}")
    print("-" * 70)

    for bucket_name, trades in buckets.items():
        if not trades:
            continue
        wins = len([t for t in trades if t['is_win']])
        losses = len([t for t in trades if not t['is_win']])
        total = len(trades)
        wr = wins / total * 100 if total > 0 else 0
        avg_pnl = sum(t['pnl_c'] for t in trades) / total if total > 0 else 0
        print(f"{bucket_name:<15} {total:<8} {wins:<8} {losses:<8} {wr:>5.1f}%{' ' * 3} {avg_pnl:>+6.2f}%")

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSE: Impact du Retest VAL
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 90)
    print("ANALYSE: Impact du Retest VAL")
    print("=" * 90)
    print()

    with_retest = [a for a in all_analyses if a['retest_detected']]
    without_retest = [a for a in all_analyses if not a['retest_detected']]

    print(f"{'Retest Status':<25} {'Total':<8} {'Wins':<8} {'Win Rate':<10} {'Avg PnL'}")
    print("-" * 60)

    for label, trades in [('Avec Retest VAL/POC', with_retest), ('Sans Retest', without_retest)]:
        if not trades:
            continue
        wins = len([t for t in trades if t['is_win']])
        total = len(trades)
        wr = wins / total * 100 if total > 0 else 0
        avg_pnl = sum(t['pnl_c'] for t in trades) / total if total > 0 else 0
        print(f"{label:<25} {total:<8} {wins:<8} {wr:>5.1f}%{' ' * 3} {avg_pnl:>+6.2f}%")

    # Retest rejected analysis
    print()
    retest_rejected = [a for a in with_retest if a['retest_rejected']]
    retest_not_rejected = [a for a in with_retest if not a['retest_rejected']]

    print(f"Parmi les trades avec Retest:")
    for label, trades in [('Retest REJECTED (rebond)', retest_rejected), ('Retest NOT rejected', retest_not_rejected)]:
        if not trades:
            continue
        wins = len([t for t in trades if t['is_win']])
        total = len(trades)
        wr = wins / total * 100 if total > 0 else 0
        avg_pnl = sum(t['pnl_c'] for t in trades) / total if total > 0 else 0
        print(f"  {label:<25} {total:<8} {wins:<8} {wr:>5.1f}%{' ' * 3} {avg_pnl:>+6.2f}%")

    # ═══════════════════════════════════════════════════════════════════
    # CONCLUSION
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 90)
    print("CONCLUSION - VALIDATION DE L'HYPOTHÈSE")
    print("=" * 90)
    print()
    print("Hypothèse: 'Prix sous VA avant le break = Setup FAIBLE = LOSS probable'")
    print()

    # Compare mostly_below vs others
    mostly_below_stats = pattern_stats.get('MOSTLY_BELOW_VA', {})
    other_patterns = ['MOSTLY_ABOVE_VA', 'MOSTLY_IN_VA', 'MIXED', 'CROSS_UP_FROM_BELOW']
    other_total = sum(pattern_stats.get(p, {}).get('total', 0) for p in other_patterns)
    other_wins = sum(pattern_stats.get(p, {}).get('wins', 0) for p in other_patterns)
    other_wr = (other_wins / other_total * 100) if other_total > 0 else 0

    mostly_below_wr = mostly_below_stats.get('win_rate', 0)
    mostly_below_total = mostly_below_stats.get('total', 0)

    print(f"📊 MOSTLY_BELOW_VA (>70% temps sous VA):")
    print(f"   - Trades: {mostly_below_total}")
    print(f"   - Win Rate: {mostly_below_wr:.1f}%")
    print()
    print(f"📊 Autres patterns:")
    print(f"   - Trades: {other_total}")
    print(f"   - Win Rate: {other_wr:.1f}%")
    print()

    if mostly_below_total >= 3:  # Minimum sample size
        if mostly_below_wr < other_wr:
            diff = other_wr - mostly_below_wr
            print(f"✅ HYPOTHÈSE CONFIRMÉE")
            print(f"   - Différence de Win Rate: {diff:.1f} points")
            print(f"   - Les trades avec prix majoritairement sous VA ont un win rate plus faible.")
        else:
            print(f"❌ HYPOTHÈSE NON CONFIRMÉE avec les données actuelles")
            print(f"   - Mais sample size peut être insuffisant ({mostly_below_total} trades)")
    else:
        print(f"⚠️  DONNÉES INSUFFISANTES")
        print(f"   - Seulement {mostly_below_total} trades avec >70% temps sous VA")
        print(f"   - Besoin de plus de données pour valider l'hypothèse")

    # Cross-up pattern analysis
    cross_up_stats = pattern_stats.get('CROSS_UP_FROM_BELOW', {})
    if cross_up_stats.get('total', 0) > 0:
        print()
        print(f"📊 Pattern CROSS_UP_FROM_BELOW (prix monte depuis sous VA):")
        print(f"   - Trades: {cross_up_stats['total']}")
        print(f"   - Win Rate: {cross_up_stats['win_rate']:.1f}%")
        print(f"   - Ce pattern correspond à votre observation sur les charts")

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()
