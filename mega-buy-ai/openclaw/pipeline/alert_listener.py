"""Polls Supabase for new MEGA BUY alerts."""

import asyncio
from typing import Set, Callable, Awaitable
from datetime import datetime, timezone, timedelta

from openclaw.config import get_settings
from openclaw.pipeline.pair_filter import is_tradable, STABLECOIN_BLACKLIST


class AlertListener:
    """Polls Supabase alerts table for new entries."""

    def __init__(self, on_new_alert: Callable[[dict], Awaitable[None]]):
        self.settings = get_settings()
        self.on_new_alert = on_new_alert
        self._seen_ids: Set[str] = set()
        self._seen_pair_bougie: Set[str] = set()  # Dedup by pair+bougie_4h
        self._pair_cooldown: dict = {}  # pair → last processed timestamp (30min cooldown)
        self._running = False
        self._task = None

        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)

    async def start(self):
        """Start polling loop."""
        self._running = True
        # Pre-load recent alert IDs to avoid re-processing
        self._preload_seen()
        self._task = asyncio.create_task(self._poll_loop())
        print(f"👂 AlertListener started (poll every {self.settings.poll_interval_sec}s, {len(self._seen_ids)} seen)")

    async def stop(self):
        """Stop polling."""
        self._running = False
        if self._task:
            self._task.cancel()

    def _preload_seen(self):
        """Mark alerts already processed by OpenClaw as 'seen'.
        Uses agent_memory table — only alerts we already analyzed are skipped."""
        try:
            # Get alert_ids from agent_memory (already processed)
            result = self.sb.table("agent_memory") \
                .select("alert_id") \
                .not_.is_("alert_id", "null") \
                .execute()
            self._seen_ids = {r["alert_id"] for r in (result.data or []) if r.get("alert_id")}
        except Exception:
            # Fallback: mark all alerts older than 2 min as seen
            try:
                cutoff = (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()
                result = self.sb.table("alerts") \
                    .select("id") \
                    .lte("alert_timestamp", cutoff) \
                    .execute()
                self._seen_ids = {r["id"] for r in (result.data or [])}
            except Exception as e:
                print(f"⚠️ Preload error: {e}")

    async def _poll_loop(self):
        """Main polling loop."""
        cycle = 0
        while self._running:
            try:
                await self._check_new_alerts()
                # Clean old dedup entries every 100 cycles (~25 min at 15s interval)
                cycle += 1
                if cycle % 100 == 0:
                    if len(self._seen_pair_bougie) > 500:
                        self._seen_pair_bougie.clear()
                    # Clean old cooldowns (> 1h)
                    now_ts = datetime.now(timezone.utc).timestamp()
                    self._pair_cooldown = {k: v for k, v in self._pair_cooldown.items() if now_ts - v < 3600}
            except Exception as e:
                print(f"⚠️ Poll error: {e}")
            await asyncio.sleep(self.settings.poll_interval_sec)

    async def _check_new_alerts(self):
        """Fetch recent alerts, dispatch new ones."""
        try:
            # Get alerts from last 60 minutes
            cutoff = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()
            result = self.sb.table("alerts") \
                .select("*, decisions(*)") \
                .gte("alert_timestamp", cutoff) \
                .order("alert_timestamp", desc=True) \
                .limit(20) \
                .execute()

            new_alerts = []
            for alert in (result.data or []):
                alert_id = alert.get("id")
                pair = alert.get("pair", "")

                if alert_id and alert_id not in self._seen_ids:
                    self._seen_ids.add(alert_id)

                    # Skip stablecoins + delisted/non-trading pairs
                    if pair in STABLECOIN_BLACKLIST or not is_tradable(pair):
                        continue

                    # Dedup: skip if same pair+bougie already analyzed (avoid double Claude calls)
                    bougie = alert.get("bougie_4h", "")
                    dedup_key = f"{pair}_{bougie}"
                    if dedup_key in self._seen_pair_bougie:
                        continue
                    self._seen_pair_bougie.add(dedup_key)

                    # Cooldown: first decision is final — no re-process within 30 min
                    now_ts = datetime.now(timezone.utc).timestamp()
                    last_processed = self._pair_cooldown.get(pair, 0)
                    if now_ts - last_processed < 1800:  # 30 min cooldown
                        continue
                    self._pair_cooldown[pair] = now_ts

                    new_alerts.append(alert)

            if new_alerts:
                # Send score >= 6 to Claude, skip score < 6
                qualified = [a for a in new_alerts if a.get("scanner_score", 0) >= 6]
                skipped_low = len(new_alerts) - len(qualified)

                # Sort by score (highest first), limit top 8 per cycle
                qualified.sort(key=lambda a: (a.get("scanner_score", 0), len(a.get("timeframes", []))), reverse=True)
                to_process = qualified[:8]
                skipped_limit = len(qualified) - len(to_process)

                if skipped_low > 0 or skipped_limit > 0:
                    print(f"🆕 {len(new_alerts)} alerts, {skipped_low} filtered (score<6), processing top {len(to_process)}" +
                          (f" (skipped {skipped_limit} overflow)" if skipped_limit else ""))
                else:
                    print(f"🆕 {len(new_alerts)} new alerts, processing {len(to_process)}")

                # Process ALL alerts in PARALLEL — multi-agent approach
                # Semaphore limits concurrent agents to avoid API overload
                sem = asyncio.Semaphore(5)  # Max 5 simultaneous agent analyses

                async def _process_one(alert):
                    async with sem:
                        pair = alert.get('pair', '?')
                        try:
                            print(f"🔍 Processing: {pair} {alert.get('scanner_score')}/10")
                            await self.on_new_alert(alert)
                        except Exception as e:
                            print(f"⚠️ Error processing {pair}: {e}")

                await asyncio.gather(*[_process_one(a) for a in to_process], return_exceptions=True)
                print(f"✅ Batch complete: {len(to_process)} alerts processed in parallel")

        except Exception as e:
            print(f"⚠️ Fetch error: {e}")
