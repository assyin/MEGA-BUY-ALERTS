"""Daily report — sends a summary to Telegram at 23h UTC every day.

Also saves the report to Supabase `openclaw_reports` table with report_type='daily'.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from openclaw.config import get_settings


class DailyReporter:
    """Sends automated daily performance report to Telegram."""

    def __init__(self, telegram_bot=None, outcome_tracker=None):
        self.bot = telegram_bot
        self.tracker = outcome_tracker
        self.settings = get_settings()
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._report_loop())
        print("📊 DailyReporter started (report at 23:00 UTC)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _report_loop(self):
        """Wait until 23:00 UTC, then send report daily."""
        while self._running:
            now = datetime.now(timezone.utc)
            # Calculate seconds until next 23:00 UTC
            target = now.replace(hour=23, minute=0, second=0, microsecond=0)
            if now.hour >= 23:
                target += timedelta(days=1)
            wait_secs = (target - now).total_seconds()
            await asyncio.sleep(wait_secs)

            try:
                await self._send_daily_report()
            except Exception as e:
                print(f"⚠️ DailyReport error: {e}")

    async def _send_daily_report(self):
        """Generate and send daily report to Telegram."""
        if not self.bot:
            return

        try:
            from supabase import create_client
            sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        except Exception:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        today_start = f"{today}T00:00:00Z"
        today_end = f"{today}T23:59:59Z"

        # 1. Count alerts today
        try:
            alerts = sb.table("alerts") \
                .select("id,pair,scanner_score", count="exact") \
                .gte("alert_timestamp", today_start) \
                .lte("alert_timestamp", today_end) \
                .execute()
            total_alerts = alerts.count or 0
            alert_data = alerts.data or []
        except Exception:
            total_alerts = 0
            alert_data = []

        # Score distribution
        score_dist = {}
        for a in alert_data:
            s = a.get("scanner_score", 0)
            score_dist[s] = score_dist.get(s, 0) + 1

        # 2. Count decisions today
        try:
            decisions = sb.table("agent_memory") \
                .select("agent_decision,agent_confidence,pair,outcome,pnl_pct") \
                .gte("timestamp", today_start) \
                .lte("timestamp", today_end) \
                .execute()
            dec_data = decisions.data or []
        except Exception:
            dec_data = []

        buy_count = sum(1 for d in dec_data if "BUY" in (d.get("agent_decision") or ""))
        watch_count = sum(1 for d in dec_data if d.get("agent_decision") == "WATCH")
        skip_count = sum(1 for d in dec_data if d.get("agent_decision") == "SKIP")

        # 3. Missed buys from outcome tracker
        missed = self.tracker.get_missed_buys() if self.tracker else []

        # 4. Top alerts (score >= 8)
        top_alerts = [a for a in alert_data if a.get("scanner_score", 0) >= 8]

        # 5. Token usage
        try:
            from openclaw.agent.token_tracker import get_token_tracker
            tracker = get_token_tracker()
            usage = tracker.get_summary()
            budget_spent = usage.get("total_cost_usd", 0)
            budget_remaining = usage.get("budget_remaining_usd", 0)
        except Exception:
            budget_spent = 0
            budget_remaining = 0

        # Build report
        lines = [
            f"📊 *Rapport Journalier OpenClaw*",
            f"📅 {today} (23:00 UTC)\n",
            f"━━━━━━━━━━━━━━━━━━━━━━",
            f"📡 *Alertes detectees:* {total_alerts}",
        ]

        if score_dist:
            dist_str = " | ".join([f"S{s}={c}" for s, c in sorted(score_dist.items(), reverse=True)])
            lines.append(f"   {dist_str}")

        lines.append(f"\n🤖 *Decisions OpenClaw:*")
        lines.append(f"   🟢 BUY: {buy_count}")
        lines.append(f"   🟡 WATCH: {watch_count}")
        lines.append(f"   🔴 SKIP: {skip_count}")

        if missed:
            lines.append(f"\n🚨 *WATCH rates (MISSED BUY):* {len(missed)}")
            for mb in missed[:5]:
                lines.append(f"   • {mb['pair']} +{mb['pnl']}%")

        if top_alerts:
            lines.append(f"\n⭐ *Top Alertes (score >= 8):*")
            seen = set()
            for a in top_alerts[:5]:
                p = a.get("pair", "?")
                if p not in seen:
                    lines.append(f"   • {p} — {a.get('scanner_score')}/10")
                    seen.add(p)

        lines.append(f"\n💰 *Budget:*")
        lines.append(f"   Depense: ${budget_spent:.2f}")
        lines.append(f"   Restant: ${budget_remaining:.2f}")

        lines.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"_Rapport auto — OpenClaw 24/7_")

        msg = "\n".join(lines)

        try:
            await self.bot.app.bot.send_message(
                chat_id=self.bot.chat_id,
                text=msg, parse_mode="Markdown"
            )
            print(f"📊 Daily report sent to Telegram")
        except Exception as e:
            # Retry without Markdown
            try:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id, text=msg
                )
            except Exception:
                print(f"⚠️ Daily report send error: {e}")

        # ── Save to Supabase openclaw_reports ──
        try:
            from supabase import create_client
            sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
            now = datetime.now(timezone.utc)
            stats = {
                "alerts_count": total_alerts,
                "buy_count": buy_count,
                "watch_count": watch_count,
                "skip_count": skip_count,
                "missed_buys": len(missed),
                "budget_spent": round(budget_spent, 2),
                "budget_remaining": round(budget_remaining, 2),
                "score_distribution": score_dist,
            }
            sb.table("openclaw_reports").insert({
                "id": str(uuid4()),
                "report_type": "daily",
                "period_start": today_start,
                "period_end": today_end,
                "content": msg,
                "stats": stats,
                "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }).execute()
            print(f"📊 Daily report saved to Supabase")
        except Exception as e:
            print(f"⚠️ Daily report Supabase save error: {e}")
