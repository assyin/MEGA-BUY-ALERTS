#!/usr/bin/env python3
"""
MEGA BUY V4 - Backtest Progress Monitor
Monitors backtest progress in real-time
"""

import requests
import time
import sys
import os

API_URL = "http://localhost:8000"

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')

def get_backtests():
    """Get all backtests from API"""
    try:
        response = requests.get(f"{API_URL}/api/backtests", timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except:
        return []

def get_running_tasks():
    """Get running background tasks"""
    try:
        response = requests.get(f"{API_URL}/api/tasks", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except:
        return {}

def format_pnl(pnl):
    """Format P&L with color indicator"""
    if pnl > 0:
        return f"+{pnl:.2f}%"
    elif pnl < 0:
        return f"{pnl:.2f}%"
    return "0.00%"

def main():
    print("🔄 MEGA BUY V4 - Backtest Progress Monitor")
    print("Press Ctrl+C to exit\n")

    last_count = 0

    while True:
        try:
            backtests = get_backtests()
            tasks = get_running_tasks()

            # Count stats
            total = len(backtests)
            running = len(tasks.get('running', []))

            # Calculate aggregated stats
            total_trades = 0
            total_wins = 0
            total_pnl_c = 0
            symbols_with_trades = 0

            for bt in backtests:
                trades = bt.get('total_trades', 0)
                if trades > 0:
                    total_trades += trades
                    symbols_with_trades += 1
                    total_pnl_c += bt.get('pnl_strategy_c', 0)
                    # Estimate wins from avg_pnl
                    avg_pnl = bt.get('avg_pnl_c', 0)
                    if avg_pnl > 0:
                        total_wins += int(trades * 0.7)  # Rough estimate

            # Clear and display
            clear_screen()
            print("=" * 70)
            print("🚀 MEGA BUY V4 - BACKTEST PROGRESS MONITOR")
            print("=" * 70)
            print(f"📊 Backtests terminés: {total}")
            print(f"⏳ En cours: {running}")
            print("-" * 70)

            if total > 0:
                print(f"\n📈 STATISTIQUES GLOBALES:")
                print(f"   Symbols avec trades: {symbols_with_trades}")
                print(f"   Total trades: {total_trades}")
                print(f"   P&L Total (C): {format_pnl(total_pnl_c)}")

                # Show last 10 completed
                print(f"\n📋 DERNIERS BACKTESTS COMPLÉTÉS:")
                print("-" * 70)
                print(f"{'Symbol':<15} {'Alerts':<8} {'Trades':<8} {'P&L C':<12} {'P&L D':<12}")
                print("-" * 70)

                # Sort by id desc to get latest
                sorted_bts = sorted(backtests, key=lambda x: x.get('id', 0), reverse=True)[:15]

                for bt in sorted_bts:
                    symbol = bt.get('symbol', 'N/A')[:14]
                    alerts = bt.get('total_alerts', 0)
                    trades = bt.get('total_trades', 0)
                    pnl_c = bt.get('pnl_strategy_c', 0)
                    pnl_d = bt.get('pnl_strategy_d', 0)

                    print(f"{symbol:<15} {alerts:<8} {trades:<8} {format_pnl(pnl_c):<12} {format_pnl(pnl_d):<12}")

            # Show running tasks
            if running > 0:
                print(f"\n⏳ BACKTESTS EN COURS ({running}):")
                for task_id in list(tasks.get('running', []))[:5]:
                    print(f"   • {task_id}")
                if running > 5:
                    print(f"   ... et {running - 5} autres")

            print("\n" + "=" * 70)
            print("🔄 Actualisation toutes les 5 secondes... (Ctrl+C pour quitter)")

            # Check if new backtests completed
            if total > last_count:
                new_count = total - last_count
                print(f"✨ +{new_count} nouveau(x) backtest(s) terminé(s)!")

            last_count = total
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n👋 Monitoring arrêté.")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
