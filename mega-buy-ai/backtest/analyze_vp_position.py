#!/usr/bin/env python3
"""
Analyse approfondie: Position du prix par rapport à la Value Area
Hypothèse: Prix sous VA avant break = LOSS
"""

import requests
import json
from datetime import datetime
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

def analyze_trade_vp_position(alert, trade):
    """
    Analyze the price position relative to Value Area at alert time
    Returns: position type and details
    """
    result = {
        'symbol': None,
        'alert_datetime': alert['alert_datetime'],
        'timeframe': alert['timeframe'],
        'alert_price': alert['price_close'],
        'entry_price': trade['entry_price'],
        'pnl_c': trade['pnl_c'],
        'is_win': trade['pnl_c'] > 0,
        'exit_reason': trade['exit_reason_c'],
        # VP Data
        'vp_poc_1h': alert.get('vp_poc_1h'),
        'vp_vah_1h': alert.get('vp_vah_1h'),
        'vp_val_1h': alert.get('vp_val_1h'),
        'vp_poc_4h': alert.get('vp_poc_4h'),
        'vp_vah_4h': alert.get('vp_vah_4h'),
        'vp_val_4h': alert.get('vp_val_4h'),
        'vp_entry_position_1h': alert.get('vp_entry_position_1h'),
        'vp_entry_position_4h': alert.get('vp_entry_position_4h'),
        'vp_grade': alert.get('vp_grade'),
        'vp_score': alert.get('vp_score'),
        'vp_label': alert.get('vp_label'),
        # Position analysis
        'alert_vs_val_1h': None,
        'alert_vs_poc_1h': None,
        'alert_vs_vah_1h': None,
        'alert_position': None,
    }

    # Calculate position relative to VA at ALERT time (not entry time)
    alert_price = alert['price_close']
    val_1h = alert.get('vp_val_1h')
    poc_1h = alert.get('vp_poc_1h')
    vah_1h = alert.get('vp_vah_1h')

    if val_1h and poc_1h and vah_1h and alert_price:
        # Calculate percentage distances
        result['alert_vs_val_1h'] = ((alert_price - val_1h) / val_1h) * 100
        result['alert_vs_poc_1h'] = ((alert_price - poc_1h) / poc_1h) * 100
        result['alert_vs_vah_1h'] = ((alert_price - vah_1h) / vah_1h) * 100

        # Determine position
        if alert_price < val_1h:
            result['alert_position'] = 'BELOW_VA'
        elif alert_price > vah_1h:
            result['alert_position'] = 'ABOVE_VA'
        elif alert_price < poc_1h:
            result['alert_position'] = 'IN_VA_BELOW_POC'
        else:
            result['alert_position'] = 'IN_VA_ABOVE_POC'

    return result

def main():
    print("=" * 80)
    print("ANALYSE APPROFONDIE: Position Prix vs Value Area")
    print("=" * 80)
    print()

    # Get all backtests with trades
    backtests = get_all_backtests_with_trades()
    print(f"📊 Backtests avec trades: {len(backtests)}")

    all_analyses = []

    for bt in backtests:
        symbol = bt['symbol']
        bt_id = bt['id']

        alerts = get_alerts_for_backtest(bt_id)
        trades = get_trades_for_backtest(bt_id)

        if not alerts or not trades:
            continue

        # Match alerts with trades by entry_datetime
        for trade in trades:
            trade_entry_dt = trade['entry_datetime']

            # Find the matching alert
            matching_alert = None
            for alert in alerts:
                if alert.get('entry_datetime') == trade_entry_dt:
                    matching_alert = alert
                    break

            if not matching_alert:
                # Try matching by alert_datetime
                for alert in alerts:
                    if alert['alert_datetime'] == trade['alert_datetime']:
                        matching_alert = alert
                        break

            if matching_alert:
                analysis = analyze_trade_vp_position(matching_alert, trade)
                analysis['symbol'] = symbol
                all_analyses.append(analysis)

    print(f"📈 Total trades analysés: {len(all_analyses)}")
    print()

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSE PAR POSITION
    # ═══════════════════════════════════════════════════════════════════

    # Group by position
    by_position = defaultdict(list)
    for a in all_analyses:
        pos = a['alert_position'] or 'NO_VP_DATA'
        by_position[pos].append(a)

    print("=" * 80)
    print("RÉSULTATS PAR POSITION DU PRIX À L'ALERTE")
    print("=" * 80)
    print()

    position_stats = {}

    for position in ['BELOW_VA', 'IN_VA_BELOW_POC', 'IN_VA_ABOVE_POC', 'ABOVE_VA', 'NO_VP_DATA']:
        trades = by_position.get(position, [])
        if not trades:
            continue

        wins = [t for t in trades if t['is_win']]
        losses = [t for t in trades if not t['is_win']]

        total = len(trades)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total * 100) if total > 0 else 0

        avg_pnl = sum(t['pnl_c'] for t in trades) / total if total > 0 else 0
        avg_win_pnl = sum(t['pnl_c'] for t in wins) / win_count if win_count > 0 else 0
        avg_loss_pnl = sum(t['pnl_c'] for t in losses) / loss_count if loss_count > 0 else 0

        position_stats[position] = {
            'total': total,
            'wins': win_count,
            'losses': loss_count,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
            'avg_win': avg_win_pnl,
            'avg_loss': avg_loss_pnl
        }

        print(f"┌{'─' * 60}┐")
        print(f"│ {position:^58} │")
        print(f"├{'─' * 60}┤")
        print(f"│ Total trades: {total:>5}                                      │")
        print(f"│ Wins:         {win_count:>5}  ({win_rate:>5.1f}%)                           │")
        print(f"│ Losses:       {loss_count:>5}  ({100-win_rate:>5.1f}%)                           │")
        print(f"│ Avg PnL:      {avg_pnl:>+6.2f}%                                   │")
        print(f"│ Avg Win:      {avg_win_pnl:>+6.2f}%                                   │")
        print(f"│ Avg Loss:     {avg_loss_pnl:>+6.2f}%                                   │")
        print(f"└{'─' * 60}┘")
        print()

    # ═══════════════════════════════════════════════════════════════════
    # DÉTAIL DES TRADES BELOW_VA (LOSSES)
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 80)
    print("DÉTAIL: Trades avec Prix SOUS la Value Area (BELOW_VA)")
    print("=" * 80)
    print()

    below_va_trades = by_position.get('BELOW_VA', [])

    if below_va_trades:
        print(f"{'Symbol':<15} {'Alert Date':<18} {'TF':<5} {'PnL':<8} {'Result':<6} {'Alert vs VAL':<12} {'VP Grade'}")
        print("-" * 90)

        for t in sorted(below_va_trades, key=lambda x: x['pnl_c']):
            result = "WIN" if t['is_win'] else "LOSS"
            alert_vs_val = f"{t['alert_vs_val_1h']:+.2f}%" if t['alert_vs_val_1h'] else "N/A"
            vp_grade = t['vp_grade'] or "N/A"
            print(f"{t['symbol']:<15} {t['alert_datetime']:<18} {t['timeframe']:<5} {t['pnl_c']:>+6.2f}% {result:<6} {alert_vs_val:<12} {vp_grade}")

    # ═══════════════════════════════════════════════════════════════════
    # COMPARAISON WINS vs LOSSES
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 80)
    print("COMPARAISON: Position VP pour les WINS vs LOSSES")
    print("=" * 80)
    print()

    wins = [a for a in all_analyses if a['is_win'] and a['alert_position']]
    losses = [a for a in all_analyses if not a['is_win'] and a['alert_position']]

    print("WINS - Distribution par position:")
    win_positions = defaultdict(int)
    for w in wins:
        win_positions[w['alert_position']] += 1
    for pos, count in sorted(win_positions.items()):
        pct = count / len(wins) * 100 if wins else 0
        print(f"  {pos:<20}: {count:>3} ({pct:>5.1f}%)")

    print()
    print("LOSSES - Distribution par position:")
    loss_positions = defaultdict(int)
    for l in losses:
        loss_positions[l['alert_position']] += 1
    for pos, count in sorted(loss_positions.items()):
        pct = count / len(losses) * 100 if losses else 0
        print(f"  {pos:<20}: {count:>3} ({pct:>5.1f}%)")

    # ═══════════════════════════════════════════════════════════════════
    # ANALYSE: Distance moyenne au VAL
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 80)
    print("ANALYSE: Distance moyenne Prix → VAL")
    print("=" * 80)
    print()

    wins_with_val = [a for a in wins if a['alert_vs_val_1h'] is not None]
    losses_with_val = [a for a in losses if a['alert_vs_val_1h'] is not None]

    if wins_with_val:
        avg_win_vs_val = sum(a['alert_vs_val_1h'] for a in wins_with_val) / len(wins_with_val)
        print(f"WINS  - Distance moyenne au VAL: {avg_win_vs_val:>+6.2f}%")
        print(f"        (positif = au-dessus du VAL)")

    if losses_with_val:
        avg_loss_vs_val = sum(a['alert_vs_val_1h'] for a in losses_with_val) / len(losses_with_val)
        print(f"LOSSES - Distance moyenne au VAL: {avg_loss_vs_val:>+6.2f}%")
        print(f"        (négatif = en-dessous du VAL)")

    # ═══════════════════════════════════════════════════════════════════
    # CONCLUSION
    # ═══════════════════════════════════════════════════════════════════

    print()
    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()

    below_va_stats = position_stats.get('BELOW_VA', {})
    in_va_stats = {
        'total': position_stats.get('IN_VA_BELOW_POC', {}).get('total', 0) +
                 position_stats.get('IN_VA_ABOVE_POC', {}).get('total', 0),
        'wins': position_stats.get('IN_VA_BELOW_POC', {}).get('wins', 0) +
                position_stats.get('IN_VA_ABOVE_POC', {}).get('wins', 0),
    }
    above_va_stats = position_stats.get('ABOVE_VA', {})

    if below_va_stats.get('total', 0) > 0:
        print(f"📉 BELOW_VA (Prix sous Value Area):")
        print(f"   Win Rate: {below_va_stats['win_rate']:.1f}%")
        print(f"   Avg PnL: {below_va_stats['avg_pnl']:+.2f}%")
        print()

    if in_va_stats.get('total', 0) > 0:
        in_va_wr = in_va_stats['wins'] / in_va_stats['total'] * 100
        print(f"📊 IN_VA (Prix dans Value Area):")
        print(f"   Win Rate: {in_va_wr:.1f}%")
        print()

    if above_va_stats.get('total', 0) > 0:
        print(f"📈 ABOVE_VA (Prix au-dessus Value Area):")
        print(f"   Win Rate: {above_va_stats['win_rate']:.1f}%")
        print(f"   Avg PnL: {above_va_stats['avg_pnl']:+.2f}%")
        print()

    # Hypothesis validation
    print()
    print("─" * 80)
    print("VALIDATION DE L'HYPOTHÈSE:")
    print("'Prix sous VA avant break = Setup FAIBLE = LOSS probable'")
    print("─" * 80)

    below_wr = below_va_stats.get('win_rate', 0)
    other_total = (in_va_stats.get('total', 0) + above_va_stats.get('total', 0))
    other_wins = (in_va_stats.get('wins', 0) + above_va_stats.get('wins', 0))
    other_wr = (other_wins / other_total * 100) if other_total > 0 else 0

    if below_wr < other_wr:
        print(f"✅ HYPOTHÈSE CONFIRMÉE")
        print(f"   - Prix BELOW_VA: {below_wr:.1f}% win rate")
        print(f"   - Prix IN/ABOVE_VA: {other_wr:.1f}% win rate")
        print(f"   - Différence: {other_wr - below_wr:.1f}% points")
    else:
        print(f"❌ HYPOTHÈSE NON CONFIRMÉE")
        print(f"   - Prix BELOW_VA: {below_wr:.1f}% win rate")
        print(f"   - Prix IN/ABOVE_VA: {other_wr:.1f}% win rate")

    print()
    print("=" * 80)

if __name__ == "__main__":
    main()
