"""Auto-Backtester — continuously backtests all active Binance pairs.

Runs in background, picks pairs that haven't been backtested recently,
and launches V5 backtests via the backtest API (port 9001).
"""

import asyncio
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Set

from openclaw.config import get_settings
from openclaw.pipeline.pair_filter import get_trading_pairs


BACKTEST_API = "http://localhost:9001"
BINANCE_API = "https://api.binance.com"


class AutoBacktester:
    """Continuously backtests pairs in background."""

    def __init__(self, min_volume_usd: float = 500_000,
                 backtest_days: int = 21,
                 delay_between_sec: int = 30,
                 max_concurrent: int = 2):
        """
        Args:
            min_volume_usd: Minimum 24h volume to consider a pair
            backtest_days: Number of days to backtest (default 21 = 3 weeks)
            delay_between_sec: Seconds between launching backtests
            max_concurrent: Max concurrent backtests
        """
        self.min_volume = min_volume_usd
        self.backtest_days = backtest_days
        self.delay = delay_between_sec
        self.max_concurrent = max_concurrent
        self._running = False
        self._task = None
        self._active_tasks: Set[str] = set()

    async def start(self):
        """Start the auto-backtester."""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        print(f"🔄 AutoBacktester started (volume>${self.min_volume/1000:.0f}K, {self.backtest_days}d, delay={self.delay}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _run_loop(self):
        """Main loop — get pairs, filter, backtest."""
        while self._running:
            try:
                # 1. Get all active USDT pairs
                pairs = await asyncio.to_thread(self._get_active_pairs)
                print(f"🔄 AutoBacktest: {len(pairs)} pairs with volume > ${self.min_volume/1000:.0f}K")

                # 2. Get already backtested symbols
                already = await asyncio.to_thread(self._get_backtested_symbols)
                print(f"   Already backtested: {len(already)} symbols")

                # 3. Get pairs that need backtesting (new or stale > 7 days)
                to_backtest = self._prioritize_pairs(pairs, already)
                print(f"   To backtest: {len(to_backtest)} pairs")

                # 4. Run backtests one by one
                end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                default_start = (datetime.now(timezone.utc) - timedelta(days=self.backtest_days)).strftime("%Y-%m-%d")

                for pair in to_backtest:
                    if not self._running:
                        break

                    # Check if backtest API is available
                    if not self._is_api_available():
                        print("   ⚠️ Backtest API not responding, waiting 60s...")
                        await asyncio.sleep(60)
                        continue

                    # Determine start_date: after last backtested date for this pair
                    pair_info = already.get(pair, {})
                    last_end = pair_info.get("end_date", "")[:10] if pair_info else ""
                    if last_end and last_end >= default_start:
                        # Start from day AFTER last backtested date
                        try:
                            next_day = datetime.strptime(last_end, "%Y-%m-%d") + timedelta(days=1)
                            start_date = next_day.strftime("%Y-%m-%d")
                            if start_date >= end_date:
                                # Already up to date — skip
                                continue
                        except Exception:
                            start_date = default_start
                    else:
                        start_date = default_start

                    # Launch backtest and wait for completion (async)
                    success = await self._launch_and_wait(pair, start_date, end_date)

                    if success:
                        # Delete old backtest for this pair (keep only the latest)
                        await asyncio.to_thread(self._cleanup_old_backtests, pair)
                        print(f"   ✅ {pair} backtest completed")
                    else:
                        print(f"   ❌ {pair} backtest failed")

                    await asyncio.sleep(5)

                # All done for this cycle, wait 1 hour before next round
                print(f"🔄 AutoBacktest cycle complete. Next in 1h.")
                await asyncio.sleep(3600)

            except Exception as e:
                print(f"⚠️ AutoBacktest error: {e}")
                await asyncio.sleep(300)

    def _get_active_pairs(self) -> List[str]:
        """Get USDT pairs that are TRADING with sufficient volume.

        Uses the centralized pair_filter which checks Binance exchangeInfo
        to exclude delisted pairs (BREAK status) and stablecoins.
        """
        try:
            # Get tradable pairs (excludes delisted + stablecoins)
            trading = get_trading_pairs()

            # Filter by volume
            r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=15)
            data = r.json()
            vol_map = {t["symbol"]: float(t.get("quoteVolume", 0)) for t in data}

            pairs = [p for p in trading if vol_map.get(p, 0) >= self.min_volume]
            pairs.sort(key=lambda p: vol_map.get(p, 0), reverse=True)
            return pairs
        except Exception as e:
            print(f"⚠️ Failed to get pairs: {e}")
            return []

    def _get_backtested_symbols(self) -> dict:
        """Get already backtested symbols with their last backtest end_date.
        Returns {symbol: {"created_at": ..., "end_date": ..., "start_date": ...}}"""
        try:
            r = requests.get(f"{BACKTEST_API}/api/backtests?limit=500", timeout=15)
            data = r.json()
            if not isinstance(data, list):
                return {}
            result = {}
            for bt in data:
                sym = bt.get("symbol", "")
                end_date = bt.get("end_date", "")
                created = bt.get("created_at", "")
                if sym:
                    existing = result.get(sym)
                    if not existing or (end_date and end_date > existing.get("end_date", "")):
                        result[sym] = {
                            "created_at": created,
                            "end_date": end_date,
                            "start_date": bt.get("start_date", ""),
                        }
            return result
        except Exception:
            return {}

    def _prioritize_pairs(self, pairs: List[str], already: dict) -> List[str]:
        """Prioritize: new pairs first, then pairs with stale backtests.
        A pair is stale if its last backtest end_date is > 1 day old."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        new_pairs = []
        stale_pairs = []

        for pair in pairs:
            if pair not in already:
                new_pairs.append(pair)
            else:
                last_end = already[pair].get("end_date", "")
                if last_end:
                    # Extract just the date part
                    last_end_date = last_end[:10]
                    if last_end_date < today:
                        stale_pairs.append(pair)
                    # else: already backtested up to today — skip
                # No end_date = re-backtest
                else:
                    stale_pairs.append(pair)

        return new_pairs + stale_pairs

    def _is_api_available(self) -> bool:
        """Check if backtest API is responding."""
        try:
            r = requests.get(f"{BACKTEST_API}/api/stats", timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    async def _launch_and_wait(self, symbol: str, start_date: str, end_date: str) -> bool:
        """Launch a backtest and wait for completion using async sleep."""
        try:
            # Launch
            r = await asyncio.to_thread(
                requests.post,
                f"{BACKTEST_API}/api/backtests",
                json={"symbol": symbol, "start_date": start_date, "end_date": end_date, "strategy_version": "v5"},
                timeout=15
            )
            if r.status_code != 200:
                return False

            task_id = r.json().get("task_id")
            if not task_id:
                return False

            # Wait for completion with async sleep (non-blocking)
            for _ in range(180):  # 180 × 10s = 30 min max per backtest
                await asyncio.sleep(10)
                if not self._running:
                    return False
                try:
                    sr = await asyncio.to_thread(
                        requests.get, f"{BACKTEST_API}/api/backtests/status/{task_id}", timeout=5
                    )
                    status = sr.json().get("status", "")
                    if status == "completed":
                        return True
                    elif status == "error":
                        print(f"   ❌ {symbol} error: {sr.json().get('progress', '?')[:60]}")
                        return False
                except Exception:
                    pass

            print(f"   ⏰ {symbol} timeout (30min)")
            return False
        except Exception as e:
            print(f"   ❌ {symbol}: {e}")
            return False

    def _launch_backtest(self, symbol: str, start_date: str, end_date: str) -> bool:
        """Launch a backtest via API and WAIT for it to complete."""
        try:
            # Launch
            r = requests.post(
                f"{BACKTEST_API}/api/backtests",
                json={
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "strategy_version": "v5",
                },
                timeout=15
            )
            if r.status_code != 200:
                return False

            task_id = r.json().get("task_id")
            if not task_id:
                return False

            # Wait for completion (max 10 minutes per backtest)
            for _ in range(60):  # 60 × 10s = 10 min max
                time.sleep(10)
                try:
                    sr = requests.get(f"{BACKTEST_API}/api/backtests/status/{task_id}", timeout=5)
                    status = sr.json().get("status", "")
                    if status == "completed":
                        return True
                    elif status == "error":
                        print(f"   ❌ {symbol} backtest error: {sr.json().get('progress', '?')}")
                        return False
                except Exception:
                    pass

            print(f"   ⏰ {symbol} backtest timeout (10min)")
            return False

        except Exception as e:
            print(f"   ❌ {symbol} error: {e}")
            return False

    def _cleanup_old_backtests(self, symbol: str):
        """Delete old backtests for a symbol, keep only the latest."""
        try:
            r = requests.get(f"{BACKTEST_API}/api/backtests?limit=500", timeout=10)
            data = r.json() if isinstance(r.json(), list) else []
            symbol_bts = [bt for bt in data if bt.get("symbol") == symbol]
            if len(symbol_bts) <= 1:
                return
            # Sort by end_date desc — keep latest
            sorted_bts = sorted(symbol_bts, key=lambda x: x.get("end_date", "") or "", reverse=True)
            for old in sorted_bts[1:]:
                try:
                    requests.delete(f"{BACKTEST_API}/api/backtests/{old['id']}", timeout=5)
                except Exception:
                    pass
        except Exception:
            pass

    def get_status(self) -> dict:
        """Get auto-backtester status."""
        return {
            "running": self._running,
            "min_volume": self.min_volume,
            "backtest_days": self.backtest_days,
            "delay_sec": self.delay,
        }
