#!/usr/bin/env python3
"""
MEGA BUY V4 - Batch Backtest Script
Runs V4 backtest on ALL Binance USDT pairs
Period: 01/02/2026 - 13/03/2026
"""

import requests
import time
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

API_URL = "http://localhost:8000"
START_DATE = "2026-02-01"
END_DATE = "2026-03-13"
STRATEGY_VERSION = "v4"
MAX_WORKERS = 3  # Parallel backtests (be careful with API rate limits)
DELAY_BETWEEN_BATCHES = 2  # Seconds between batches

# Exclusions (stablecoins, delisted, etc.)
EXCLUDED_PAIRS = [
    'USDCUSDT', 'BUSDUSDT', 'TUSDUSDT', 'USDPUSDT', 'FDUSDUSDT',
    'EURUSDT', 'GBPUSDT', 'AUDUSDT', 'BRLBUSD', 'PAXGUSDT'
]

# ═══════════════════════════════════════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_all_usdt_pairs():
    """Get all USDT pairs from Binance Spot"""
    print("📡 Fetching Binance Spot USDT pairs...")

    try:
        # Binance Spot exchange info
        response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=30)
        response.raise_for_status()
        data = response.json()

        pairs = []
        for symbol_info in data.get('symbols', []):
            symbol = symbol_info.get('symbol', '')
            status = symbol_info.get('status', '')

            # Filter: USDT pairs, trading, not in exclusion list
            if (symbol.endswith('USDT') and
                status == 'TRADING' and
                symbol not in EXCLUDED_PAIRS):
                pairs.append(symbol)

        print(f"✅ Found {len(pairs)} USDT Spot pairs")
        return sorted(pairs)

    except Exception as e:
        print(f"❌ Error fetching pairs: {e}")
        return []


def run_backtest(symbol: str, index: int, total: int):
    """Run backtest for a single symbol"""
    try:
        payload = {
            "symbol": symbol,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "strategy_version": STRATEGY_VERSION
        }

        response = requests.post(
            f"{API_URL}/api/backtests",
            json=payload,
            timeout=300  # 5 min timeout per backtest
        )

        if response.status_code == 200:
            data = response.json()
            backtest_id = data.get('backtest_id')
            return {
                'symbol': symbol,
                'status': 'success',
                'backtest_id': backtest_id,
                'message': f"[{index}/{total}] ✅ {symbol} - Backtest #{backtest_id} started"
            }
        else:
            return {
                'symbol': symbol,
                'status': 'error',
                'message': f"[{index}/{total}] ❌ {symbol} - HTTP {response.status_code}: {response.text[:100]}"
            }

    except requests.exceptions.Timeout:
        return {
            'symbol': symbol,
            'status': 'timeout',
            'message': f"[{index}/{total}] ⏱️ {symbol} - Timeout (still running in background)"
        }
    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'error',
            'message': f"[{index}/{total}] ❌ {symbol} - Error: {str(e)[:100]}"
        }


def check_api_status():
    """Check if API is running"""
    try:
        response = requests.get(f"{API_URL}/api/backtests", timeout=5)
        return response.status_code == 200
    except:
        return False


def main():
    print("=" * 70)
    print("🚀 MEGA BUY V4 - BATCH BACKTEST")
    print("=" * 70)
    print(f"📅 Period: {START_DATE} → {END_DATE}")
    print(f"📊 Strategy: {STRATEGY_VERSION}")
    print(f"⚡ Parallel workers: {MAX_WORKERS}")
    print("=" * 70)

    # Check API
    if not check_api_status():
        print("❌ API not running! Start it with:")
        print("   cd /home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/api")
        print("   source /home/assyin/MEGA-BUY-BOT/python/venv/bin/activate")
        print("   python main.py")
        sys.exit(1)

    print("✅ API is running")

    # Get all pairs
    pairs = get_all_usdt_pairs()
    if not pairs:
        print("❌ No pairs found!")
        sys.exit(1)

    total = len(pairs)
    print(f"\n🎯 Starting backtests for {total} pairs...\n")

    # Results tracking
    results = {
        'success': [],
        'error': [],
        'timeout': []
    }

    start_time = datetime.now()

    # Run backtests with thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}

        for i, symbol in enumerate(pairs, 1):
            future = executor.submit(run_backtest, symbol, i, total)
            futures[future] = symbol

            # Small delay to avoid overwhelming the API
            if i % MAX_WORKERS == 0:
                time.sleep(DELAY_BETWEEN_BATCHES)

        # Process results as they complete
        for future in as_completed(futures):
            result = future.result()
            print(result['message'])
            results[result['status']].append(result['symbol'])

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("📊 BATCH BACKTEST COMPLETE")
    print("=" * 70)
    print(f"⏱️  Duration: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"✅ Success: {len(results['success'])}")
    print(f"⏱️  Timeout (still running): {len(results['timeout'])}")
    print(f"❌ Errors: {len(results['error'])}")

    if results['error']:
        print(f"\n❌ Failed pairs: {', '.join(results['error'][:10])}")
        if len(results['error']) > 10:
            print(f"   ... and {len(results['error']) - 10} more")

    print("\n💡 View results at: http://localhost:9000/backtest")
    print("=" * 70)

    # Save results to file
    output_file = f"/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'start_date': START_DATE,
            'end_date': END_DATE,
            'strategy': STRATEGY_VERSION,
            'total_pairs': total,
            'results': results,
            'elapsed_seconds': elapsed
        }, f, indent=2)
    print(f"📁 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
