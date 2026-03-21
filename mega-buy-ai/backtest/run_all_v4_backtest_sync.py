#!/usr/bin/env python3
"""
MEGA BUY V4 - Batch Backtest Script (SYNC VERSION)
Runs V4 backtest on ALL Binance USDT pairs - ONE AT A TIME
Period: 01/02/2026 - 13/03/2026
"""

import requests
import time
import json
from datetime import datetime
import sys

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

API_URL = "http://localhost:8000"
START_DATE = "2026-02-01"
END_DATE = "2026-03-13"
STRATEGY_VERSION = "v4"
DELAY_BETWEEN_REQUESTS = 1.0  # Seconds between each request
TIMEOUT_PER_BACKTEST = 300    # 5 minutes max per backtest
MAX_RETRIES = 2               # Retry failed backtests

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
        response = requests.get("https://api.binance.com/api/v3/exchangeInfo", timeout=30)
        response.raise_for_status()
        data = response.json()

        pairs = []
        for symbol_info in data.get('symbols', []):
            symbol = symbol_info.get('symbol', '')
            status = symbol_info.get('status', '')

            if (symbol.endswith('USDT') and
                status == 'TRADING' and
                symbol not in EXCLUDED_PAIRS):
                pairs.append(symbol)

        print(f"✅ Found {len(pairs)} USDT Spot pairs")
        return sorted(pairs)

    except Exception as e:
        print(f"❌ Error fetching pairs: {e}")
        return []


def get_existing_backtests():
    """Get symbols that already have backtests"""
    try:
        response = requests.get(f"{API_URL}/api/backtests", timeout=10)
        if response.status_code == 200:
            backtests = response.json()
            return set(bt['symbol'] for bt in backtests)
        return set()
    except:
        return set()


def wait_for_completion(task_id: str, symbol: str, timeout: int = 300):
    """Wait for a backtest to complete"""
    start = time.time()
    last_check_db = 0

    while time.time() - start < timeout:
        try:
            # Check API status
            response = requests.get(f"{API_URL}/api/backtests/status/{task_id}", timeout=5)
            if response.status_code == 200:
                status = response.json()
                if status.get('status') == 'completed':
                    return True, status.get('backtest_id')
                elif status.get('status') == 'error':
                    return False, status.get('error', 'Unknown error')
            elif response.status_code == 404:
                # Task finished and was cleaned up - check if symbol is in DB
                time.sleep(2)
                return True, None
        except:
            pass

        # Every 30 seconds, check if symbol appeared in DB
        if time.time() - last_check_db > 30:
            try:
                response = requests.get(f"{API_URL}/api/backtests", timeout=5)
                if response.status_code == 200:
                    backtests = response.json()
                    for bt in backtests:
                        if bt.get('symbol') == symbol:
                            return True, bt.get('id')
            except:
                pass
            last_check_db = time.time()

        time.sleep(2)

    return False, "Timeout"


def run_backtest_sync(symbol: str, index: int, total: int):
    """Run backtest and wait for completion"""
    try:
        payload = {
            "symbol": symbol,
            "start_date": START_DATE,
            "end_date": END_DATE,
            "strategy_version": STRATEGY_VERSION
        }

        # Start backtest
        response = requests.post(
            f"{API_URL}/api/backtests",
            json=payload,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            task_id = data.get('task_id')

            # Wait for completion
            success, result = wait_for_completion(task_id, symbol, TIMEOUT_PER_BACKTEST)

            if success:
                return {
                    'symbol': symbol,
                    'status': 'success',
                    'message': f"[{index}/{total}] ✅ {symbol} - Completed"
                }
            else:
                return {
                    'symbol': symbol,
                    'status': 'error',
                    'message': f"[{index}/{total}] ❌ {symbol} - {result}"
                }
        else:
            return {
                'symbol': symbol,
                'status': 'error',
                'message': f"[{index}/{total}] ❌ {symbol} - HTTP {response.status_code}"
            }

    except Exception as e:
        return {
            'symbol': symbol,
            'status': 'error',
            'message': f"[{index}/{total}] ❌ {symbol} - {str(e)[:50]}"
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
    print("🚀 MEGA BUY V4 - BATCH BACKTEST (SYNC)")
    print("=" * 70)
    print(f"📅 Period: {START_DATE} → {END_DATE}")
    print(f"📊 Strategy: {STRATEGY_VERSION}")
    print(f"⏱️  Mode: Sequential (one at a time)")
    print("=" * 70)

    # Check API
    if not check_api_status():
        print("❌ API not running!")
        sys.exit(1)

    print("✅ API is running")

    # Get all pairs
    pairs = get_all_usdt_pairs()
    if not pairs:
        print("❌ No pairs found!")
        sys.exit(1)

    # Get existing backtests to skip
    existing = get_existing_backtests()
    print(f"📋 Existing backtests: {len(existing)}")

    # Filter out already processed
    pairs_to_process = [p for p in pairs if p not in existing]
    print(f"📋 Pairs to process: {len(pairs_to_process)}")

    if not pairs_to_process:
        print("✅ All pairs already backtested!")
        return

    total = len(pairs_to_process)
    print(f"\n🎯 Starting backtests for {total} pairs...\n")

    # Results tracking
    results = {
        'success': [],
        'error': []
    }

    start_time = datetime.now()

    # Run backtests sequentially
    for i, symbol in enumerate(pairs_to_process, 1):
        result = run_backtest_sync(symbol, i, total)

        # Retry on timeout
        retries = 0
        while result['status'] == 'error' and 'Timeout' in result['message'] and retries < MAX_RETRIES:
            retries += 1
            print(f"   ↻ Retry {retries}/{MAX_RETRIES} for {symbol}...")
            time.sleep(5)
            result = run_backtest_sync(symbol, i, total)

        print(result['message'])
        results[result['status']].append(result['symbol'])

        # Small delay between requests
        time.sleep(DELAY_BETWEEN_REQUESTS)

        # Progress update every 25 pairs
        if i % 25 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time = elapsed / i
            remaining = (total - i) * avg_time
            print(f"\n📊 Progress: {i}/{total} ({i/total*100:.1f}%) - ETA: {remaining/60:.1f} min\n")

    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 70)
    print("📊 BATCH BACKTEST COMPLETE")
    print("=" * 70)
    print(f"⏱️  Duration: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"✅ Success: {len(results['success'])}")
    print(f"❌ Errors: {len(results['error'])}")

    if results['error']:
        print(f"\n❌ Failed pairs: {', '.join(results['error'][:10])}")

    print("\n💡 View results at: http://localhost:9000/backtest")
    print("=" * 70)


if __name__ == "__main__":
    main()
