#!/usr/bin/env python3
"""
Script pour relancer tous les backtests pour les 58 paires uniques.
Utilise BacktestEngine avec dates par défaut (6 mois).
"""
import json
import time
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.engine import BacktestEngine
from api.models import SessionLocal, BacktestRun

def progress_callback(msg):
    """Print progress messages"""
    print(f"    {msg}")

def main():
    # Load pairs to retest
    with open('data/pairs_to_retest.json', 'r') as f:
        pairs = json.load(f)

    total = len(pairs)
    print(f"\n{'='*60}")
    print(f"  MEGA BUY AI - Batch Backtest Runner")
    print(f"  {total} pairs to process")
    print(f"{'='*60}\n")

    # Default dates: 6 months back
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
    print(f"  Date range: {start_date} to {end_date}")

    engine = BacktestEngine()
    db = SessionLocal()

    success = 0
    failed = []

    for i, symbol in enumerate(pairs, 1):
        print(f"\n[{i}/{total}] Processing {symbol}...")
        print("-" * 40)

        try:
            start_time = time.time()
            run_id = engine.run_backtest(symbol, start_date, end_date, progress_callback)
            elapsed = time.time() - start_time

            # Get results from DB
            run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()

            if run:
                print(f"  ✓ Completed in {elapsed:.1f}s")
                print(f"    Alerts: {run.total_alerts}, Entries: {run.valid_entries}")
                print(f"    Trades: {run.total_trades}")
                print(f"    P&L C: {run.pnl_strategy_c:+.2f}%, P&L D: {run.pnl_strategy_d:+.2f}%")
                success += 1
            else:
                print(f"  ✗ Failed: No run created")
                failed.append((symbol, "No run created"))

        except Exception as e:
            print(f"  ✗ Exception: {str(e)[:100]}")
            failed.append((symbol, str(e)[:100]))

        # Small delay between backtests to avoid rate limits
        if i < total:
            time.sleep(2)

    db.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH BACKTEST COMPLETE")
    print(f"{'='*60}")
    print(f"  Success: {success}/{total}")
    print(f"  Failed: {len(failed)}/{total}")

    if failed:
        print(f"\n  Failed pairs:")
        for symbol, error in failed:
            print(f"    - {symbol}: {error[:50]}")

    print(f"\n{'='*60}\n")

    return success, failed

if __name__ == '__main__':
    success, failed = main()
    sys.exit(0 if not failed else 1)
