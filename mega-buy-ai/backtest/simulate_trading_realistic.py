#!/usr/bin/env python3
"""
Trading Simulation RÉALISTE - V5 Backtest
Gère les trades simultanés et le capital disponible
"""

import sqlite3
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

DB_PATH = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/data/backtest.db"

@dataclass
class Trade:
    id: int
    pair: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    pnl_pct: float
    exit_reason: str

@dataclass
class Position:
    trade: Trade
    allocated_capital: float
    entry_time: datetime
    exit_time: datetime

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string"""
    if not dt_str:
        return None
    try:
        # Handle various formats
        for fmt in ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"]:
            try:
                return datetime.strptime(dt_str, fmt)
            except:
                continue
        return None
    except:
        return None

def run_realistic_simulation(
    initial_balance: float = 2000.0,
    max_concurrent_trades: int = 5,
    position_size_pct: float = 20.0  # % du solde par trade
):
    """
    Simulation réaliste avec gestion des trades simultanés

    Args:
        initial_balance: Solde initial
        max_concurrent_trades: Nombre max de trades simultanés
        position_size_pct: % du solde total alloué par trade
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Récupérer tous les trades V5 avec dates
    cursor.execute("""
        SELECT
            t.id,
            b.symbol,
            t.entry_datetime,
            t.exit_datetime_c,
            t.entry_price,
            t.exit_price_c,
            t.pnl_c,
            t.exit_reason_c
        FROM trades t
        JOIN backtest_runs b ON t.backtest_run_id = b.id
        WHERE b.strategy_version = 'v5'
        AND t.pnl_c IS NOT NULL
        AND t.entry_datetime IS NOT NULL
        AND t.exit_datetime_c IS NOT NULL
        ORDER BY t.entry_datetime ASC
    """)

    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("❌ Aucun trade V5 trouvé")
        return

    # Convertir en objets Trade
    trades = []
    for row in rows:
        entry_dt = parse_datetime(row[2])
        exit_dt = parse_datetime(row[3])
        if entry_dt and exit_dt:
            trades.append(Trade(
                id=row[0],
                pair=row[1],
                entry_time=entry_dt,
                exit_time=exit_dt,
                entry_price=row[4] or 0,
                exit_price=row[5] or 0,
                pnl_pct=row[6],
                exit_reason=row[7] or ""
            ))

    print(f"\n{'='*90}")
    print(f"📊 SIMULATION RÉALISTE V5 - Capital: ${initial_balance:,.2f}")
    print(f"   Max {max_concurrent_trades} trades simultanés | {position_size_pct}% du solde par trade")
    print(f"{'='*90}\n")

    # État du portefeuille
    total_balance = initial_balance  # Solde total (cash + positions)
    cash_balance = initial_balance   # Cash disponible
    open_positions: List[Position] = []
    closed_positions: List[Position] = []
    skipped_trades = []

    # Créer une timeline d'événements
    events = []
    for t in trades:
        events.append(('entry', t.entry_time, t))
        events.append(('exit', t.exit_time, t))

    # Trier par date
    events.sort(key=lambda x: x[1])

    # Variables de tracking
    peak_balance = initial_balance
    max_drawdown = 0
    max_drawdown_pct = 0

    print("📈 EXÉCUTION DES TRADES")
    print("-" * 90)
    print(f"{'Date':<20} {'Event':<8} {'Paire':<12} {'P&L %':>8} {'Alloué $':>12} {'P&L $':>12} {'Cash $':>12} {'Total $':>12}")
    print("-" * 90)

    processed_trade_ids = set()

    for event_type, event_time, trade in events:
        if event_type == 'entry':
            # Vérifier si on peut prendre ce trade
            if trade.id in processed_trade_ids:
                continue  # Déjà traité

            # Fermer les positions expirées
            for pos in open_positions[:]:
                if pos.exit_time <= event_time:
                    # Calculer le P&L
                    pnl_usd = pos.allocated_capital * (pos.trade.pnl_pct / 100)
                    cash_balance += pos.allocated_capital + pnl_usd
                    total_balance = cash_balance + sum(p.allocated_capital for p in open_positions if p != pos)
                    open_positions.remove(pos)
                    closed_positions.append(pos)

            # Vérifier les limites
            if len(open_positions) >= max_concurrent_trades:
                skipped_trades.append((trade, "Max positions atteint"))
                continue

            # Calculer le capital à allouer
            allocation = total_balance * (position_size_pct / 100)

            if allocation > cash_balance:
                # Pas assez de cash
                if cash_balance > 100:  # Minimum 100$ pour trader
                    allocation = cash_balance * 0.95  # Utiliser 95% du cash restant
                else:
                    skipped_trades.append((trade, f"Cash insuffisant: ${cash_balance:.2f}"))
                    continue

            # Ouvrir la position
            cash_balance -= allocation
            pos = Position(
                trade=trade,
                allocated_capital=allocation,
                entry_time=trade.entry_time,
                exit_time=trade.exit_time
            )
            open_positions.append(pos)
            processed_trade_ids.add(trade.id)

            # Calculer le total (cash + valeur des positions ouvertes)
            total_balance = cash_balance + sum(p.allocated_capital for p in open_positions)

            print(f"{event_time.strftime('%Y-%m-%d %H:%M'):<20} {'ENTRY':<8} {trade.pair:<12} {'':>8} ${allocation:>10,.2f} {'':>12} ${cash_balance:>10,.2f} ${total_balance:>10,.2f}")

        elif event_type == 'exit':
            # Trouver la position correspondante
            pos = None
            for p in open_positions:
                if p.trade.id == trade.id:
                    pos = p
                    break

            if pos is None:
                continue  # Position non trouvée (skipped ou déjà fermée)

            # Calculer le P&L
            pnl_usd = pos.allocated_capital * (trade.pnl_pct / 100)
            returned_capital = pos.allocated_capital + pnl_usd
            cash_balance += returned_capital

            open_positions.remove(pos)
            closed_positions.append(pos)

            # Calculer le total
            total_balance = cash_balance + sum(p.allocated_capital for p in open_positions)

            # Tracker le drawdown
            if total_balance > peak_balance:
                peak_balance = total_balance
            current_dd = peak_balance - total_balance
            current_dd_pct = (current_dd / peak_balance) * 100 if peak_balance > 0 else 0
            if current_dd > max_drawdown:
                max_drawdown = current_dd
                max_drawdown_pct = current_dd_pct

            # Emoji
            emoji = "🚀" if trade.pnl_pct >= 15 else ("✅" if trade.pnl_pct > 0 else "❌")

            print(f"{event_time.strftime('%Y-%m-%d %H:%M'):<20} {'EXIT':<8} {emoji} {trade.pair:<10} {trade.pnl_pct:>+7.2f}% ${pos.allocated_capital:>10,.2f} ${pnl_usd:>+10,.2f} ${cash_balance:>10,.2f} ${total_balance:>10,.2f}")

    # Fermer les positions restantes (pour le calcul final)
    for pos in open_positions:
        pnl_usd = pos.allocated_capital * (pos.trade.pnl_pct / 100)
        cash_balance += pos.allocated_capital + pnl_usd
        closed_positions.append(pos)

    total_balance = cash_balance

    # Statistiques
    winners = sum(1 for p in closed_positions if p.trade.pnl_pct > 0)
    losers = sum(1 for p in closed_positions if p.trade.pnl_pct <= 0)
    big_winners = sum(1 for p in closed_positions if p.trade.pnl_pct >= 15)
    total_trades = len(closed_positions)
    win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
    total_return = ((total_balance - initial_balance) / initial_balance) * 100

    total_profit = sum(p.allocated_capital * (p.trade.pnl_pct / 100) for p in closed_positions if p.trade.pnl_pct > 0)
    total_loss = abs(sum(p.allocated_capital * (p.trade.pnl_pct / 100) for p in closed_positions if p.trade.pnl_pct <= 0))
    profit_factor = (total_profit / total_loss) if total_loss > 0 else float('inf')

    print(f"\n{'='*90}")
    print("📊 RAPPORT FINAL")
    print(f"{'='*90}")

    print(f"""
┌──────────────────────────────────────────────────────────────────────┐
│                       RÉSUMÉ DE PERFORMANCE                          │
├──────────────────────────────────────────────────────────────────────┤
│  Solde Initial:         ${initial_balance:>12,.2f}                            │
│  Solde Final:           ${total_balance:>12,.2f}                            │
│  Profit/Perte:          ${total_balance - initial_balance:>+12,.2f} ({total_return:>+.1f}%)                     │
├──────────────────────────────────────────────────────────────────────┤
│                       STATISTIQUES TRADES                            │
├──────────────────────────────────────────────────────────────────────┤
│  Trades Exécutés:       {total_trades:>12}                                    │
│  Trades Ignorés:        {len(skipped_trades):>12}                                    │
│  Gagnants:              {winners:>12} ({win_rate:.1f}%)                           │
│  Perdants:              {losers:>12}                                    │
│  Big Winners (≥15%):    {big_winners:>12}                                    │
├──────────────────────────────────────────────────────────────────────┤
│                       MÉTRIQUES DE RISQUE                            │
├──────────────────────────────────────────────────────────────────────┤
│  Profit Factor:         {profit_factor:>12.2f}                                    │
│  Max Drawdown:          ${max_drawdown:>12,.2f} ({max_drawdown_pct:.1f}%)                  │
│  Peak Balance:          ${peak_balance:>12,.2f}                            │
│  Max Trades Simultanés: {max_concurrent_trades:>12}                                    │
│  Taille Position:       {position_size_pct:>11.0f}%                                    │
└──────────────────────────────────────────────────────────────────────┘
""")

    # Top trades
    sorted_positions = sorted(closed_positions, key=lambda p: p.trade.pnl_pct, reverse=True)

    print("\n🏆 TOP 5 MEILLEURS TRADES:")
    print("-" * 70)
    for i, pos in enumerate(sorted_positions[:5], 1):
        pnl_usd = pos.allocated_capital * (pos.trade.pnl_pct / 100)
        print(f"  {i}. {pos.trade.pair:<15} {pos.trade.pnl_pct:>+7.2f}%  (${pnl_usd:>+10,.2f}) - Capital: ${pos.allocated_capital:,.2f}")

    print("\n💀 TOP 5 PIRES TRADES:")
    print("-" * 70)
    for i, pos in enumerate(sorted_positions[-5:][::-1], 1):
        pnl_usd = pos.allocated_capital * (pos.trade.pnl_pct / 100)
        print(f"  {i}. {pos.trade.pair:<15} {pos.trade.pnl_pct:>+7.2f}%  (${pnl_usd:>+10,.2f}) - Capital: ${pos.allocated_capital:,.2f}")

    # Trades ignorés
    if skipped_trades:
        print(f"\n⚠️ TRADES IGNORÉS ({len(skipped_trades)}):")
        print("-" * 70)
        for trade, reason in skipped_trades[:10]:
            print(f"  - {trade.pair:<15} {trade.entry_time.strftime('%Y-%m-%d %H:%M')} | Raison: {reason}")
        if len(skipped_trades) > 10:
            print(f"  ... et {len(skipped_trades) - 10} autres")

    # Analyse des trades simultanés
    print("\n📊 ANALYSE DES TRADES SIMULTANÉS:")
    print("-" * 70)

    # Compter les trades par jour
    trades_per_day = {}
    for pos in closed_positions:
        day = pos.entry_time.strftime('%Y-%m-%d')
        if day not in trades_per_day:
            trades_per_day[day] = []
        trades_per_day[day].append(pos)

    max_same_day = max(len(v) for v in trades_per_day.values()) if trades_per_day else 0
    print(f"  Max trades entrés le même jour: {max_same_day}")
    print(f"  Jours de trading: {len(trades_per_day)}")
    print(f"  Moyenne trades/jour: {len(closed_positions) / len(trades_per_day):.1f}")

    return {
        'initial_balance': initial_balance,
        'final_balance': total_balance,
        'total_return_pct': total_return,
        'total_trades': total_trades,
        'skipped_trades': len(skipped_trades),
        'winners': winners,
        'losers': losers,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'max_drawdown': max_drawdown,
        'max_drawdown_pct': max_drawdown_pct,
        'big_winners': big_winners
    }


if __name__ == "__main__":
    print("\n" + "="*90)
    print("SCÉNARIO 1: 5 trades max, 20% par position")
    print("="*90)
    run_realistic_simulation(
        initial_balance=2000.0,
        max_concurrent_trades=5,
        position_size_pct=20.0
    )

    print("\n\n" + "="*90)
    print("SCÉNARIO 2: 3 trades max, 30% par position")
    print("="*90)
    run_realistic_simulation(
        initial_balance=2000.0,
        max_concurrent_trades=3,
        position_size_pct=30.0
    )

    print("\n\n" + "="*90)
    print("SCÉNARIO 3: 10 trades max, 10% par position")
    print("="*90)
    run_realistic_simulation(
        initial_balance=2000.0,
        max_concurrent_trades=10,
        position_size_pct=10.0
    )
