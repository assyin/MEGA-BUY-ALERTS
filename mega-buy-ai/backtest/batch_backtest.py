#!/usr/bin/env python3
"""
Batch backtest runner for all 58 unique pairs.
Uses 3-month date range for reasonable execution time.
"""
import sys
sys.stdout.reconfigure(line_buffering=True)

import json
import time
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from api.engine import BacktestEngine
from api.models import SessionLocal, BacktestRun

def main():
    # Load pairs
    with open('data/pairs_to_retest.json', 'r') as f:
        pairs = json.load(f)

    total = len(pairs)

    # 3 months date range
    end_date = '2026-02-28'
    start_date = '2025-12-01'

    print(f"\n{'='*60}")
    print(f"  MEGA BUY AI - Batch Backtest Runner")
    print(f"  {total} pairs to process")
    print(f"  Date range: {start_date} to {end_date}")
    print(f"{'='*60}\n")

    engine = BacktestEngine()

    success = 0
    failed = []
    results = []

    for i, symbol in enumerate(pairs, 1):
        print(f"\n[{i}/{total}] Processing {symbol}...")
        print("-" * 40)

        def progress(msg):
            print(f"  {msg}")

        try:
            start_time = time.time()
            run_id = engine.run_backtest(symbol, start_date, end_date, progress)
            elapsed = time.time() - start_time

            # Get results from DB
            db = SessionLocal()
            run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()

            if run:
                print(f"  ✓ Completed in {elapsed:.1f}s (Run ID: {run_id})")
                print(f"    Alerts: {run.total_alerts}, Entries: {run.valid_entries}")
                print(f"    Trades: {run.total_trades}")
                print(f"    P&L C: {run.pnl_strategy_c:+.2f}%, P&L D: {run.pnl_strategy_d:+.2f}%")

                results.append({
                    'symbol': symbol,
                    'run_id': run_id,
                    'alerts': run.total_alerts,
                    'entries': run.valid_entries,
                    'trades': run.total_trades,
                    'pnl_c': run.pnl_strategy_c,
                    'pnl_d': run.pnl_strategy_d,
                    'elapsed': elapsed
                })
                success += 1
            else:
                print(f"  ✗ Failed: No run created")
                failed.append((symbol, "No run created"))

            db.close()

        except Exception as e:
            print(f"  ✗ Exception: {str(e)[:100]}")
            failed.append((symbol, str(e)[:100]))

        # Small delay between backtests
        if i < total:
            time.sleep(2)

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

    # Top performers
    if results:
        sorted_by_pnl = sorted(results, key=lambda x: x['pnl_c'], reverse=True)
        print(f"\n  Top 5 by P&L (Strategy C):")
        for r in sorted_by_pnl[:5]:
            print(f"    {r['symbol']}: {r['pnl_c']:+.2f}% ({r['entries']} entries)")

    print(f"\n{'='*60}\n")

    # Save results
    with open('data/batch_results.json', 'w') as f:
        json.dump({
            'date_range': {'start': start_date, 'end': end_date},
            'total': total,
            'success': success,
            'failed': len(failed),
            'results': results,
            'failed_pairs': failed
        }, f, indent=2)

    print(f"Results saved to data/batch_results.json")

    return success, failed

if __name__ == '__main__':
    success, failed = main()
    sys.exit(0 if not failed else 1)
