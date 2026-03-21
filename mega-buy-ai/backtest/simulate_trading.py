#!/usr/bin/env python3
"""
Trading Simulation - V5 Backtest
Simule le trading avec un solde initial et les trades du backtest V5
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/data/backtest.db"

def run_simulation(initial_balance: float = 2000.0, position_size_pct: float = 100.0, strategy: str = 'C'):
    """
    Simule le trading avec les trades V5

    Args:
        initial_balance: Solde initial en USD
        position_size_pct: % du solde utilisé par trade (100 = all-in)
        strategy: 'C' pour trailing stop, 'D' pour fixed TP
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Récupérer tous les trades V5 triés par date d'entrée
    # On joint alerts pour avoir le symbol (pair)
    pnl_col = 'pnl_c' if strategy == 'C' else 'pnl_d'
    exit_reason_col = 'exit_reason_c' if strategy == 'C' else 'exit_reason_d'

    cursor.execute(f"""
        SELECT
            t.id,
            b.symbol,
            t.entry_datetime,
            t.exit_datetime_c,
            t.entry_price,
            t.exit_price_c,
            t.{pnl_col},
            t.{exit_reason_col},
            b.strategy_version
        FROM trades t
        JOIN backtest_runs b ON t.backtest_run_id = b.id
        WHERE b.strategy_version = 'v5'
        AND t.{pnl_col} IS NOT NULL
        ORDER BY t.entry_datetime ASC
    """)

    trades = cursor.fetchall()
    conn.close()

    if not trades:
        print("❌ Aucun trade V5 trouvé")
        return

    # Simulation
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    max_drawdown_pct = 0

    winners = 0
    losers = 0
    big_winners = 0  # >= 15%
    total_profit = 0
    total_loss = 0

    trade_history = []

    print(f"\n{'='*80}")
    print(f"📊 SIMULATION DE TRADING V5 - Solde Initial: ${initial_balance:,.2f}")
    print(f"   Stratégie: {'Trailing Stop (C)' if strategy == 'C' else 'Fixed TP (D)'}")
    print(f"{'='*80}\n")

    for trade in trades:
        trade_id, pair, entry_time, exit_time, entry_price, exit_price, pnl_pct, exit_reason, version = trade

        if pnl_pct is None:
            continue

        # Calculer le P&L en USD
        position_value = balance * (position_size_pct / 100)
        pnl_usd = position_value * (pnl_pct / 100)

        # Mettre à jour le solde
        old_balance = balance
        balance += pnl_usd

        # Tracker le drawdown
        if balance > peak_balance:
            peak_balance = balance
        current_drawdown = peak_balance - balance
        current_drawdown_pct = (current_drawdown / peak_balance) * 100 if peak_balance > 0 else 0
        if current_drawdown > max_drawdown:
            max_drawdown = current_drawdown
            max_drawdown_pct = current_drawdown_pct

        # Stats
        if pnl_pct > 0:
            winners += 1
            total_profit += pnl_usd
            if pnl_pct >= 15:
                big_winners += 1
        else:
            losers += 1
            total_loss += abs(pnl_usd)

        # Format date
        entry_dt = entry_time[:10] if entry_time else "N/A"

        # Emoji pour le résultat
        if pnl_pct >= 15:
            emoji = "🚀"
        elif pnl_pct > 0:
            emoji = "✅"
        else:
            emoji = "❌"

        trade_history.append({
            'num': len(trade_history) + 1,
            'date': entry_dt,
            'pair': pair,
            'pnl_pct': pnl_pct,
            'pnl_usd': pnl_usd,
            'balance': balance,
            'emoji': emoji,
            'exit_reason': exit_reason
        })

    # Afficher l'historique des trades
    print("📈 HISTORIQUE DES TRADES")
    print("-" * 100)
    print(f"{'#':>3} {'Date':<12} {'Paire':<18} {'P&L %':>10} {'P&L $':>12} {'Solde $':>14} {'Raison':<15}")
    print("-" * 100)

    for t in trade_history:
        reason = t['exit_reason'][:15] if t['exit_reason'] else "N/A"
        print(f"{t['num']:>3} {t['date']:<12} {t['emoji']} {t['pair']:<15} {t['pnl_pct']:>+8.2f}% ${t['pnl_usd']:>+10.2f} ${t['balance']:>12,.2f} {reason:<15}")

    # Résumé final
    total_trades = winners + losers
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
    total_return = ((balance - initial_balance) / initial_balance) * 100
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')
    avg_win = (total_profit / winners) if winners > 0 else 0
    avg_loss = (total_loss / losers) if losers > 0 else 0

    print(f"\n{'='*80}")
    print("📊 RAPPORT FINAL")
    print(f"{'='*80}")

    print(f"""
┌─────────────────────────────────────────────────────────────┐
│                    RÉSUMÉ DE PERFORMANCE                     │
├─────────────────────────────────────────────────────────────┤
│  Solde Initial:      ${initial_balance:>12,.2f}                       │
│  Solde Final:        ${balance:>12,.2f}                       │
│  Profit/Perte:       ${balance - initial_balance:>+12,.2f} ({total_return:+.1f}%)               │
├─────────────────────────────────────────────────────────────┤
│                    STATISTIQUES TRADES                       │
├─────────────────────────────────────────────────────────────┤
│  Total Trades:       {total_trades:>12}                               │
│  Gagnants:           {winners:>12} ({win_rate:.1f}%)                      │
│  Perdants:           {losers:>12}                               │
│  Big Winners (≥15%): {big_winners:>12}                               │
├─────────────────────────────────────────────────────────────┤
│                    MÉTRIQUES DE RISQUE                       │
├─────────────────────────────────────────────────────────────┤
│  Profit Factor:      {profit_factor:>12.2f}                               │
│  Gain Moyen:         ${avg_win:>12,.2f}                       │
│  Perte Moyenne:      ${avg_loss:>12,.2f}                       │
│  Max Drawdown:       ${max_drawdown:>12,.2f} ({max_drawdown_pct:.1f}%)            │
│  Peak Balance:       ${peak_balance:>12,.2f}                       │
└─────────────────────────────────────────────────────────────┘
""")

    # Top 5 meilleurs trades
    sorted_by_pnl = sorted(trade_history, key=lambda x: x['pnl_pct'], reverse=True)
    print("\n🏆 TOP 5 MEILLEURS TRADES:")
    print("-" * 60)
    for i, t in enumerate(sorted_by_pnl[:5], 1):
        print(f"  {i}. {t['pair']:<15} {t['pnl_pct']:>+7.2f}%  (${t['pnl_usd']:>+10,.2f})")

    # Top 5 pires trades
    print("\n💀 TOP 5 PIRES TRADES:")
    print("-" * 60)
    for i, t in enumerate(sorted_by_pnl[-5:][::-1], 1):
        print(f"  {i}. {t['pair']:<15} {t['pnl_pct']:>+7.2f}%  (${t['pnl_usd']:>+10,.2f})")

    # Évolution du solde par tranches
    print("\n📈 ÉVOLUTION DU SOLDE:")
    print("-" * 60)
    checkpoints = [0, len(trade_history)//4, len(trade_history)//2, 3*len(trade_history)//4, len(trade_history)-1]
    for cp in checkpoints:
        if cp < len(trade_history):
            t = trade_history[cp]
            pct_change = ((t['balance'] - initial_balance) / initial_balance) * 100
            bar_len = int(abs(pct_change) / 5)
            bar = "█" * min(bar_len, 30)
            if pct_change >= 0:
                print(f"  Trade #{t['num']:>2}: ${t['balance']:>10,.2f}  {pct_change:>+7.1f}% |{bar}")
            else:
                print(f"  Trade #{t['num']:>2}: ${t['balance']:>10,.2f}  {pct_change:>+7.1f}% |{bar}")

    return {
        'initial_balance': initial_balance,
        'final_balance': balance,
        'total_return_pct': total_return,
        'total_trades': total_trades,
        'winners': winners,
        'losers': losers,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'big_winners': big_winners
    }


if __name__ == "__main__":
    # Simulation avec $2000 et 100% du solde par trade (all-in)
    result = run_simulation(initial_balance=2000.0, position_size_pct=100.0, strategy='C')
