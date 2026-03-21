#!/usr/bin/env python3
"""
TEST V2: Nouveau filtre VP sur ALLOUSDT
Filtre AJUSTÉ: Prend en compte la REJECTION du retest
"""

import requests
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

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
                'close': float(k[4]),
            } for k in data]
    except:
        pass
    return []

def analyze_trade_with_new_filter_v2(symbol, alert_dt_str, alert_price, entry_price, pnl,
                                      vp_val, vp_poc, vp_vah, val_retest_rejected,
                                      lookback_hours=48):
    """
    Apply V2 filter: REJECT only if bad trajectory AND no retest rejection
    """
    print(f"\n{'='*70}")
    print(f"ANALYSE: {symbol} - Alert {alert_dt_str}")
    print(f"{'='*70}")

    try:
        alert_dt = datetime.fromisoformat(alert_dt_str)
    except:
        alert_dt = datetime.strptime(alert_dt_str, '%Y-%m-%dT%H:%M:%S')

    result = "WIN" if pnl > 0 else "LOSS"

    print(f"\n📊 DONNÉES DU TRADE:")
    print(f"   Alert Price: {alert_price}")
    print(f"   Entry Price: {entry_price}")
    print(f"   PnL: {pnl:+.2f}% ({result})")
    print(f"   VP VAL: {vp_val}")
    print(f"   VAL Retest Rejected: {val_retest_rejected}")

    if not vp_val or not vp_poc or not vp_vah:
        print(f"\n⚠️  Pas de données VP - Skip")
        return None

    # Calculate alert position vs VAL
    alert_vs_val = ((alert_price - vp_val) / vp_val) * 100
    print(f"\n📍 POSITION À L'ALERTE:")
    print(f"   Alert vs VAL: {alert_vs_val:+.2f}%")

    # Get historical data
    start_dt = alert_dt - timedelta(hours=lookback_hours)
    candles = get_historical_data(symbol, start_dt, alert_dt, '1h')

    pct_below = 0
    if candles:
        below_count = sum(1 for c in candles if c['close'] < vp_val)
        total = len(candles)
        pct_below = (below_count / total * 100) if total > 0 else 0
        print(f"\n📈 TRAJECTOIRE (48h avant):")
        print(f"   % temps sous VA: {pct_below:.1f}%")

    # ═══════════════════════════════════════════════════════════════════
    # NOUVEAU FILTRE V2 - AJUSTÉ
    # ═══════════════════════════════════════════════════════════════════

    print(f"\n{'─'*70}")
    print(f"🔍 APPLICATION DU FILTRE V2 (avec rejection check):")
    print(f"{'─'*70}")

    rejection_reasons = []

    # ═══════════════════════════════════════════════════════════════════
    # RÈGLE PRINCIPALE: Prix sous VAL + pas de rejection = DANGER
    # ═══════════════════════════════════════════════════════════════════

    is_below_val = alert_price < vp_val
    is_mostly_below = pct_below > 60

    print(f"\n   Conditions:")
    print(f"   - Prix sous VAL: {is_below_val} ({alert_vs_val:+.2f}%)")
    print(f"   - >60% temps sous VA: {is_mostly_below} ({pct_below:.1f}%)")
    print(f"   - Retest rejected (rebond): {val_retest_rejected}")

    # Si le retest est REJECTED (rebond confirmé), on ACCEPTE même si prix était sous VA
    if val_retest_rejected:
        print(f"\n   ✅ Retest REJECTED (rebond confirmé) → Setup validé malgré trajectoire")
    else:
        # Pas de rejection → on vérifie les conditions de danger
        if is_below_val:
            rejection_reasons.append("BELOW_VAL_NO_BOUNCE")
            print(f"\n   ❌ Prix sous VAL ET pas de rebond → Setup faible")

        if is_mostly_below:
            rejection_reasons.append("WEAK_TRAJECTORY_NO_BOUNCE")
            print(f"\n   ❌ {pct_below:.1f}% sous VA ET pas de rebond → Trajectoire faible")

    # ═══════════════════════════════════════════════════════════════════
    # DÉCISION V2
    # ═══════════════════════════════════════════════════════════════════

    print(f"\n{'─'*70}")

    if rejection_reasons:
        print(f"🚫 DÉCISION V2: REJETÉ")
        print(f"   Raisons: {', '.join(rejection_reasons)}")
        would_reject = True
    else:
        print(f"✅ DÉCISION V2: ACCEPTÉ")
        would_reject = False

    # Compare avec le résultat réel
    print(f"\n📊 RÉSULTAT RÉEL: {pnl:+.2f}% ({result})")

    if would_reject and pnl < 0:
        print(f"✅ FILTRE CORRECT: Aurait évité cette perte de {pnl:.2f}%")
        filter_correct = True
    elif would_reject and pnl > 0:
        print(f"⚠️  FAUX POSITIF: Aurait rejeté un trade gagnant")
        filter_correct = False
    elif not would_reject and pnl > 0:
        print(f"✅ FILTRE CORRECT: A accepté un trade gagnant")
        filter_correct = True
    else:
        print(f"❌ FILTRE MANQUÉ: N'a pas détecté cette perte")
        filter_correct = False

    return {
        'symbol': symbol,
        'alert_datetime': alert_dt_str,
        'pnl': pnl,
        'result': result,
        'would_reject': would_reject,
        'rejection_reasons': rejection_reasons,
        'filter_correct': filter_correct,
        'val_retest_rejected': val_retest_rejected
    }


def main():
    print("=" * 70)
    print("TEST V2: FILTRE VP AJUSTÉ (avec check rebond)")
    print("=" * 70)
    print()
    print("RÈGLE V2:")
    print("  - Si retest REJECTED (rebond) → ACCEPTÉ (même si prix sous VA)")
    print("  - Si prix sous VAL ET pas de rebond → REJETÉ")
    print("  - Si >60% sous VA ET pas de rebond → REJETÉ")

    # Les 5 trades ALLOUSDT
    trades = [
        {
            'alert_dt': '2026-02-08T14:30:00',
            'alert_price': 0.0579,
            'entry_price': 0.0589,
            'pnl': 8.59,
            'vp_val': 0.056513,
            'vp_poc': 0.057885,
            'vp_vah': 0.058865,
            'val_retest_rejected': True  # ← REBOND!
        },
        {
            'alert_dt': '2026-02-08T17:30:00',
            'alert_price': 0.0583,
            'entry_price': 0.0582,
            'pnl': 6.21,
            'vp_val': 0.057912,
            'vp_poc': 0.058488,
            'vp_vah': 0.060024,
            'val_retest_rejected': True  # ← REBOND!
        },
        {
            'alert_dt': '2026-02-25T02:15:00',
            'alert_price': 0.1071,
            'entry_price': 0.1107,
            'pnl': -11.07,
            'vp_val': 0.108117,
            'vp_poc': 0.114093,
            'vp_vah': 0.119571,
            'val_retest_rejected': False  # ← PAS DE REBOND!
        },
        {
            'alert_dt': '2026-03-03T15:00:00',
            'alert_price': 0.1085,
            'entry_price': 0.1117,
            'pnl': 11.62,
            'vp_val': 0.104318,
            'vp_poc': 0.108862,
            'vp_vah': 0.110282,
            'val_retest_rejected': True  # ← REBOND!
        },
        {
            'alert_dt': '2026-03-04T08:30:00',
            'alert_price': 0.1115,
            'entry_price': 0.1117,
            'pnl': 0.50,
            'vp_val': 0.104478,
            'vp_poc': 0.108942,
            'vp_vah': 0.114894,
            'val_retest_rejected': False  # Pas de rebond mais prix +6.72% au-dessus VAL
        },
    ]

    results = []
    for t in trades:
        result = analyze_trade_with_new_filter_v2(
            'ALLOUSDT',
            t['alert_dt'],
            t['alert_price'],
            t['entry_price'],
            t['pnl'],
            t['vp_val'],
            t['vp_poc'],
            t['vp_vah'],
            t['val_retest_rejected']
        )
        if result:
            results.append(result)

    # ═══════════════════════════════════════════════════════════════════
    # RÉSUMÉ V2
    # ═══════════════════════════════════════════════════════════════════

    print("\n")
    print("=" * 70)
    print("RÉSUMÉ V2 - IMPACT DU FILTRE AJUSTÉ SUR ALLOUSDT")
    print("=" * 70)

    rejected = [r for r in results if r['would_reject']]
    accepted = [r for r in results if not r['would_reject']]

    print(f"\n📊 SANS LE FILTRE (actuel):")
    total_pnl_before = sum(r['pnl'] for r in results)
    wins_before = len([r for r in results if r['pnl'] > 0])
    losses_before = len([r for r in results if r['pnl'] <= 0])
    print(f"   Trades: {len(results)}")
    print(f"   Wins: {wins_before}, Losses: {losses_before}")
    print(f"   PnL Total: {total_pnl_before:+.2f}%")

    print(f"\n📊 AVEC LE FILTRE V2:")
    total_pnl_after = sum(r['pnl'] for r in accepted)
    wins_after = len([r for r in accepted if r['pnl'] > 0])
    losses_after = len([r for r in accepted if r['pnl'] <= 0])
    print(f"   Trades acceptés: {len(accepted)}")
    print(f"   Trades rejetés: {len(rejected)}")
    print(f"   Wins: {wins_after}, Losses: {losses_after}")
    print(f"   PnL Total: {total_pnl_after:+.2f}%")

    print(f"\n📈 AMÉLIORATION:")
    improvement = total_pnl_after - total_pnl_before
    avoided_losses = sum(r['pnl'] for r in rejected if r['pnl'] < 0)
    missed_wins = sum(r['pnl'] for r in rejected if r['pnl'] > 0)
    print(f"   Différence PnL: {improvement:+.2f}%")
    print(f"   Pertes évitées: {abs(avoided_losses):.2f}%")
    print(f"   Gains manqués: {missed_wins:.2f}%")

    if losses_after == 0 and losses_before > 0:
        print(f"\n🎯 100% WIN RATE avec le filtre V2!")

    print(f"\n📋 DÉTAIL DES REJETS:")
    if rejected:
        for r in rejected:
            print(f"   - {r['alert_datetime']}: {r['pnl']:+.2f}% ({r['result']}) - {', '.join(r['rejection_reasons'])}")
    else:
        print(f"   Aucun trade rejeté")

    print(f"\n📋 TRADES ACCEPTÉS:")
    for r in accepted:
        bounce = "✓ rebond" if r['val_retest_rejected'] else "○ pas rebond"
        print(f"   - {r['alert_datetime']}: {r['pnl']:+.2f}% ({r['result']}) - {bounce}")

    # Validation de la règle
    print(f"\n{'─'*70}")
    print("VALIDATION DE LA RÈGLE:")
    print(f"{'─'*70}")

    correct_count = len([r for r in results if r['filter_correct']])
    accuracy = correct_count / len(results) * 100
    print(f"   Précision du filtre: {accuracy:.1f}% ({correct_count}/{len(results)})")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
