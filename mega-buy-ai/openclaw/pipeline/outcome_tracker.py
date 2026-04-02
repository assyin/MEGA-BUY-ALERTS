"""Tracks trade outcomes LIVE — updates PnL every 30min for all PENDING decisions.

Outcomes:
- WIN: PnL >= +10% at any point
- LOSE: PnL <= -5% at any point
- EXPIRED_WIN/EXPIRED_LOSE: After 7 days, force-close based on current PnL
- MISSED_BUY: WATCH decision where price went +10%
- CORRECT_WATCH: WATCH decision where price went -5%
"""

import asyncio
import requests
import time
from datetime import datetime, timezone, timedelta

from openclaw.config import get_settings
from openclaw.memory.store import MemoryStore
from openclaw.agent.circuit_breaker import CircuitBreaker


class OutcomeTracker:
    """Live PnL tracker — updates every 30min for dashboard display."""

    def __init__(self, memory: MemoryStore, circuit_breaker: CircuitBreaker,
                 telegram_bot=None):
        self.memory = memory
        self.circuit_breaker = circuit_breaker
        self.telegram_bot = telegram_bot
        self.settings = get_settings()
        self._running = False
        self._task = None
        self._watch_task = None
        self._missed_buys_today = []

    async def start(self, interval_minutes: int = 5):
        """Start outcome tracking loop."""
        self._running = True
        self._task = asyncio.create_task(self._track_loop(interval_minutes))
        self._watch_task = asyncio.create_task(self._watch_feedback_loop())
        print(f"📈 OutcomeTracker started (LIVE PnL every {interval_minutes}min, WATCH feedback every 2h)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        if self._watch_task:
            self._watch_task.cancel()

    async def _track_loop(self, interval_minutes: int):
        """Check outcomes every 30 min — update PnL for ALL pending."""
        # First run after 60 seconds (let alerts get processed first)
        await asyncio.sleep(60)
        while self._running:
            try:
                await self._check_all_pending()
            except Exception as e:
                print(f"⚠️ OutcomeTracker error: {e}")
            await asyncio.sleep(interval_minutes * 60)

    async def _check_all_pending(self):
        """Check ALL pending decisions — update PnL live, close outcomes."""
        try:
            from supabase import create_client
            sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        except Exception:
            return

        # Get ALL pending decisions (not just from memory — from Supabase directly)
        try:
            result = sb.table("agent_memory") \
                .select("*") \
                .in_("outcome", ["PENDING", None]) \
                .order("timestamp", desc=True) \
                .limit(200) \
                .execute()
            pending = result.data or []
        except Exception:
            # Fallback
            pending = [p for p in self.memory.get_recent(200)
                       if not p.get("outcome") or p.get("outcome") == "PENDING"]

        if not pending:
            return

        # Batch fetch all unique pair prices
        pairs = list(set(p.get("pair", "") for p in pending if p.get("pair")))
        prices = {}
        for pair in pairs:
            try:
                r = requests.get(
                    f"{self.settings.binance_api_url}/api/v3/ticker/price",
                    params={"symbol": pair}, timeout=5
                )
                prices[pair] = float(r.json().get("price", 0))
                time.sleep(0.05)  # Rate limiting
            except Exception:
                pass

        updated = 0
        wins = 0
        losses = 0
        now = datetime.now(timezone.utc)

        for pattern in pending:
            pair = pattern.get("pair", "")
            if not pair or pair not in prices:
                continue

            current_price = prices[pair]
            if current_price <= 0:
                continue

            # Get entry price from features
            features = pattern.get("features_fingerprint", {}) or {}
            entry_price = features.get("price", 0) or features.get("alert_price", 0)
            if not entry_price:
                continue

            pnl = (current_price - entry_price) / entry_price * 100
            record_id = pattern.get("id", "")
            alert_id = pattern.get("alert_id", "")
            decision = pattern.get("agent_decision", "")

            # Track PnL MAX and MIN (highest/lowest ever reached)
            prev_pnl_max = pattern.get("pnl_max") or pnl
            prev_pnl_min = pattern.get("pnl_min") or pnl
            prev_highest = pattern.get("highest_price") or current_price
            pnl_max = max(pnl, prev_pnl_max)
            pnl_min = min(pnl, prev_pnl_min)
            highest_price = max(current_price, prev_highest)

            # Calculate time since alert
            ts = pattern.get("timestamp", "")
            hours_since = 999
            if ts:
                try:
                    alert_time = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    hours_since = (now - alert_time).total_seconds() / 3600
                except Exception:
                    pass

            # Determine outcome
            outcome = None
            if pnl >= 10:
                outcome = "WIN"
                wins += 1
                self.circuit_breaker.record_win()
            elif pnl <= -8:
                outcome = "LOSE"
                losses += 1
                self.circuit_breaker.record_loss()
            elif hours_since >= 168:  # 7 days = force close
                outcome = "EXPIRED_WIN" if pnl > 0 else "EXPIRED_LOSE"

            # Update in Supabase
            # - pnl_pct: LIVE price (changes every 5min)
            # - pnl_max/pnl_min: historical high/low PnL (never decrease/increase)
            # - highest_price: ATH price since alert
            # - When outcome decided: pnl_at_close = FROZEN PnL at decision time
            try:
                update_data = {"pnl_pct": round(pnl, 2)}
                # Try to add tracking columns (may not exist yet)
                extra = {
                    "pnl_max": round(pnl_max, 2),
                    "pnl_min": round(pnl_min, 2),
                    "highest_price": round(highest_price, 8),
                }
                if outcome:
                    update_data["outcome"] = outcome
                    update_data["outcome_at"] = now.isoformat()
                    extra["pnl_at_close"] = round(pnl, 2)  # FROZEN at decision time

                target = record_id or alert_id
                key = "id" if record_id else "alert_id"
                if target:
                    # Try full update with tracking columns
                    try:
                        sb.table("agent_memory").update({**update_data, **extra}).eq(key, target).execute()
                    except Exception:
                        # Fallback: just update basic fields
                        sb.table("agent_memory").update(update_data).eq(key, target).execute()

                updated += 1
            except Exception:
                pass

            # Log significant outcomes
            if outcome == "WIN":
                print(f"  ✅ {pair}: WIN +{pnl:.1f}%")
            elif outcome == "LOSE":
                print(f"  ❌ {pair}: LOSE {pnl:.1f}%")
            elif outcome and "EXPIRED" in outcome:
                print(f"  ⏰ {pair}: {outcome} {pnl:+.1f}% (7d expired)")

        if updated > 0:
            print(f"📊 OutcomeTracker: {updated} PnL updated, {wins} WIN, {losses} LOSE ({len(pending)} total pending)")

        # Daily/weekly resets
        if now.hour == 0 and now.minute < 35:
            self.circuit_breaker.reset_daily()
        if now.weekday() == 0 and now.hour == 0 and now.minute < 35:
            self.circuit_breaker.reset_weekly()

    # ================================================================
    # WATCH FEEDBACK LOOP — Detect MISSED_BUY
    # ================================================================

    async def _watch_feedback_loop(self):
        """Every 2h, check WATCH decisions: if price moved +10% → MISSED_BUY."""
        await asyncio.sleep(300)  # Wait 5min after startup
        while self._running:
            try:
                await self._check_watch_outcomes()
            except Exception as e:
                print(f"⚠️ WATCH feedback error: {e}")
            await asyncio.sleep(2 * 3600)  # Every 2 hours

    async def _check_watch_outcomes(self):
        """Check all recent WATCH decisions against current prices."""
        try:
            from supabase import create_client
            sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        except Exception:
            return

        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        try:
            result = sb.table("agent_memory") \
                .select("*") \
                .eq("agent_decision", "WATCH") \
                .gte("timestamp", cutoff) \
                .in_("outcome", ["PENDING", None]) \
                .limit(50) \
                .execute()
            watch_patterns = result.data or []
        except Exception:
            watch_patterns = []

        if not watch_patterns:
            return

        missed = 0
        correct = 0

        for pattern in watch_patterns:
            pair = pattern.get("pair", "")
            if not pair:
                continue

            try:
                r = requests.get(
                    f"{self.settings.binance_api_url}/api/v3/ticker/price",
                    params={"symbol": pair}, timeout=5
                )
                current_price = float(r.json().get("price", 0))
                if current_price <= 0:
                    continue

                features = pattern.get("features_fingerprint", {}) or {}
                alert_price = features.get("price", 0) or features.get("alert_price", 0)
                if not alert_price:
                    continue

                pnl = (current_price - alert_price) / alert_price * 100

                if pnl >= 10:
                    missed += 1
                    self._missed_buys_today.append({
                        "pair": pair, "pnl": round(pnl, 1),
                        "alert_price": alert_price, "current_price": current_price,
                        "timestamp": pattern.get("timestamp", ""),
                    })
                    try:
                        sb.table("agent_memory") \
                            .update({"outcome": "MISSED_BUY", "pnl_pct": round(pnl, 2)}) \
                            .eq("id", pattern["id"]).execute()
                    except Exception:
                        pass
                    print(f"  🚨 MISSED_BUY: {pair} +{pnl:.1f}%")

                elif pnl <= -5:
                    correct += 1
                    try:
                        sb.table("agent_memory") \
                            .update({"outcome": "CORRECT_WATCH", "pnl_pct": round(pnl, 2)}) \
                            .eq("id", pattern["id"]).execute()
                    except Exception:
                        pass

            except Exception:
                pass

        if missed > 0 or correct > 0:
            print(f"📊 WATCH Feedback: {missed} MISSED_BUY, {correct} CORRECT_WATCH")

        if missed > 0 and self.telegram_bot:
            try:
                lines = ["🚨 *WATCH Feedback Loop*\n"]
                lines.append(f"*{missed} MISSED BUY* detectes :\n")
                for mb in self._missed_buys_today[-10:]:
                    lines.append(f"• *{mb['pair']}* +{mb['pnl']}%")
                lines.append(f"\n✅ {correct} CORRECT WATCH")
                msg = "\n".join(lines)
                await self.telegram_bot.app.bot.send_message(
                    chat_id=self.telegram_bot.chat_id,
                    text=msg, parse_mode="Markdown"
                )
            except Exception:
                pass

    def get_missed_buys(self) -> list:
        return self._missed_buys_today
