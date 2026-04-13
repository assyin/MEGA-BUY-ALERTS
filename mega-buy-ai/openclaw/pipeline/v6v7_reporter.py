"""V6/V7 Reporter — sends daily and weekly performance reports to Telegram.

- Daily: every day at 22:30 UTC (after main daily reporter at 23:00)
  → Performance V6 + V7 du jour, top winners, ratio TP1/TP2/Trail (V7)

- Weekly: every Sunday at 22:00 UTC
  → Comparaison complète V6 vs V7 sur les 7 derniers jours
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List

from openclaw.config import get_settings


class V6V7Reporter:

    def __init__(self, telegram_bot=None):
        self.bot = telegram_bot
        self.settings = get_settings()
        self._running = False
        self._task_daily = None
        self._task_weekly = None

        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)

    async def start(self):
        self._running = True
        self._task_daily = asyncio.create_task(self._daily_loop())
        self._task_weekly = asyncio.create_task(self._weekly_loop())
        print("📊 V6V7Reporter started — daily 22:30 UTC, weekly Sunday 22:00 UTC")

    async def stop(self):
        self._running = False
        for t in (self._task_daily, self._task_weekly):
            if t:
                t.cancel()

    # ==================================================================
    # SCHEDULING
    # ==================================================================

    async def _daily_loop(self):
        while self._running:
            now = datetime.now(timezone.utc)
            target = now.replace(hour=22, minute=30, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=1)
            wait = (target - now).total_seconds()
            await asyncio.sleep(wait)
            try:
                await self._send_daily_report()
            except Exception as e:
                print(f"⚠️ V6V7 daily report error: {e}")

    async def _weekly_loop(self):
        while self._running:
            now = datetime.now(timezone.utc)
            # Next Sunday at 22:00 UTC
            days_until_sunday = (6 - now.weekday()) % 7
            target = (now + timedelta(days=days_until_sunday)).replace(hour=22, minute=0, second=0, microsecond=0)
            if now >= target:
                target += timedelta(days=7)
            wait = (target - now).total_seconds()
            await asyncio.sleep(wait)
            try:
                await self._send_weekly_comparison()
            except Exception as e:
                print(f"⚠️ V6V7 weekly report error: {e}")

    # ==================================================================
    # DATA FETCH
    # ==================================================================

    def _fetch_state(self, table: str) -> Dict:
        try:
            return self.sb.table(table).select("*").eq("id", "main").single().execute().data or {}
        except Exception:
            return {}

    def _fetch_positions_period(self, table: str, since_iso: str, status: str = None) -> List[Dict]:
        try:
            q = self.sb.table(table).select("*").gte("opened_at", since_iso).order("opened_at", desc=True)
            if status:
                q = q.eq("status", status)
            return q.execute().data or []
        except Exception:
            return []

    # ==================================================================
    # DAILY REPORT
    # ==================================================================

    async def _send_daily_report(self):
        if not self.bot:
            return

        now = datetime.now(timezone.utc)
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

        # ===== V6 =====
        v6_state = self._fetch_state("openclaw_portfolio_state_v6")
        v6_open_today = self._fetch_positions_period("openclaw_positions_v6", day_start, "OPEN")
        v6_closed_today = [p for p in self._fetch_positions_period("openclaw_positions_v6", day_start)
                           if p.get("status") == "CLOSED" and p.get("closed_at", "") >= day_start]

        v6_wins = [p for p in v6_closed_today if (p.get("pnl_usd") or 0) > 0]
        v6_losses = [p for p in v6_closed_today if (p.get("pnl_usd") or 0) <= 0]
        v6_pnl_day = sum(p.get("pnl_usd", 0) or 0 for p in v6_closed_today)
        v6_wr_day = (len(v6_wins) / len(v6_closed_today) * 100) if v6_closed_today else 0
        v6_top = sorted(v6_closed_today, key=lambda x: -(x.get("pnl_pct") or 0))[:3]

        # ===== V7 =====
        v7_state = self._fetch_state("openclaw_portfolio_state_v7")
        v7_open_today = self._fetch_positions_period("openclaw_positions_v7", day_start, "OPEN")
        v7_all_today = self._fetch_positions_period("openclaw_positions_v7", day_start)
        v7_closed_today = [p for p in v7_all_today if p.get("status") == "CLOSED" and p.get("closed_at", "") >= day_start]

        v7_wins = [p for p in v7_closed_today if (p.get("pnl_usd") or 0) > 0]
        v7_losses = [p for p in v7_closed_today if (p.get("pnl_usd") or 0) <= 0]
        v7_pnl_day = sum(p.get("pnl_usd", 0) or 0 for p in v7_closed_today)
        v7_wr_day = (len(v7_wins) / len(v7_closed_today) * 100) if v7_closed_today else 0
        v7_top = sorted(v7_closed_today, key=lambda x: -(x.get("pnl_pct") or 0))[:3]

        # V7 partial stats — count TP1/TP2/Trail across ALL today positions (open + closed)
        v7_tp1_count = sum(1 for p in v7_all_today if p.get("partial1_done"))
        v7_tp2_count = sum(1 for p in v7_all_today if p.get("partial2_done"))
        v7_trail_count = sum(1 for p in v7_all_today if p.get("trail_active"))
        v7_trail_stops = sum(1 for p in v7_closed_today if p.get("close_reason") == "TRAIL_STOP")
        v7_be_stops = sum(1 for p in v7_closed_today if p.get("close_reason") == "BREAKEVEN_STOP")

        # ===== Build message =====
        msg = f"📊 *RAPPORT JOURNALIER V6/V7* — {now.strftime('%d/%m/%Y')}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # V6 Block
        msg += "🟢 *V6 — Fixed TP +15%*\n"
        msg += f"💰 Balance: *${v6_state.get('balance', 5000):.0f}* / $5000 init\n"
        msg += f"📈 PnL Total: *${v6_state.get('total_pnl', 0):+.0f}* ({v6_state.get('total_pnl', 0)/50:+.1f}%)\n"
        msg += f"📊 PnL Jour: *${v6_pnl_day:+.0f}*\n"
        msg += f"🔄 Trades jour: {len(v6_closed_today)} ({len(v6_wins)}W/{len(v6_losses)}L) WR {v6_wr_day:.0f}%\n"
        msg += f"📦 Positions ouvertes: {len(v6_open_today)}/12\n"
        msg += f"🏆 WR global: {self._calc_wr(v6_state)}% ({v6_state.get('wins', 0)}W/{v6_state.get('losses', 0)}L)\n"

        if v6_top:
            msg += "\n🥇 *Top winners V6 jour*:\n"
            for p in v6_top[:3]:
                pnl_pct = p.get("pnl_pct") or 0
                pnl_usd = p.get("pnl_usd") or 0
                emoji = "🟢" if pnl_pct > 0 else "🔴"
                msg += f"  {emoji} `{p['pair']}` *{pnl_pct:+.1f}%* (${pnl_usd:+.0f})\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # V7 Block
        msg += "🟣 *V7 — Hybrid Trailing*\n"
        msg += f"💰 Balance: *${v7_state.get('balance', 5000):.0f}* / $5000 init\n"
        msg += f"📈 PnL Total: *${v7_state.get('total_pnl', 0):+.0f}* ({v7_state.get('total_pnl', 0)/50:+.1f}%)\n"
        msg += f"📊 PnL Jour: *${v7_pnl_day:+.0f}*\n"
        msg += f"🔄 Trades jour: {len(v7_closed_today)} ({len(v7_wins)}W/{len(v7_losses)}L) WR {v7_wr_day:.0f}%\n"
        msg += f"📦 Positions ouvertes: {len(v7_open_today)}/12\n"
        msg += f"🏆 WR global: {self._calc_wr(v7_state)}% ({v7_state.get('wins', 0)}W/{v7_state.get('losses', 0)}L)\n"

        msg += f"\n🎯 *Stats partials V7 jour*:\n"
        msg += f"  TP1 hit (50%): *{v7_tp1_count}*\n"
        msg += f"  TP2 hit (30%): *{v7_tp2_count}*\n"
        msg += f"  Trailing actif: *{v7_trail_count}*\n"
        msg += f"  Trail stops (close): {v7_trail_stops}\n"
        msg += f"  Breakeven stops: {v7_be_stops}\n"

        if v7_top:
            msg += "\n🥇 *Top winners V7 jour*:\n"
            for p in v7_top[:3]:
                pnl_pct = p.get("pnl_pct") or 0
                pnl_usd = p.get("pnl_usd") or 0
                emoji = "🟢" if pnl_pct > 0 else "🔴"
                msg += f"  {emoji} `{p['pair']}` *{pnl_pct:+.1f}%* (${pnl_usd:+.0f})\n"

        msg += "\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Comparison snapshot
        winner = "🟢 V6" if v6_pnl_day > v7_pnl_day else ("🟣 V7" if v7_pnl_day > v6_pnl_day else "🟰 Égalité")
        msg += f"\n🏁 *Gagnant du jour: {winner}*\n"
        msg += f"   V6: ${v6_pnl_day:+.0f}  vs  V7: ${v7_pnl_day:+.0f}"

        await self._send(msg)

    # ==================================================================
    # WEEKLY COMPARISON
    # ==================================================================

    async def _send_weekly_comparison(self):
        if not self.bot:
            return

        now = datetime.now(timezone.utc)
        week_start = (now - timedelta(days=7)).isoformat()

        # ===== V6 =====
        v6_state = self._fetch_state("openclaw_portfolio_state_v6")
        v6_all = self._fetch_positions_period("openclaw_positions_v6", week_start)
        v6_closed = [p for p in v6_all if p.get("status") == "CLOSED"]
        v6_wins = [p for p in v6_closed if (p.get("pnl_usd") or 0) > 0]
        v6_losses = [p for p in v6_closed if (p.get("pnl_usd") or 0) <= 0]
        v6_pnl_week = sum(p.get("pnl_usd", 0) or 0 for p in v6_closed)
        v6_wr_week = (len(v6_wins) / len(v6_closed) * 100) if v6_closed else 0
        v6_avg_win = (sum(p.get("pnl_pct", 0) or 0 for p in v6_wins) / len(v6_wins)) if v6_wins else 0
        v6_avg_loss = (sum(p.get("pnl_pct", 0) or 0 for p in v6_losses) / len(v6_losses)) if v6_losses else 0
        v6_tp_hits = sum(1 for p in v6_closed if p.get("close_reason") == "TP_HIT")
        v6_sl_hits = sum(1 for p in v6_closed if p.get("close_reason") == "SL_HIT")
        v6_timeouts = sum(1 for p in v6_closed if p.get("close_reason") == "TIMEOUT_48H")
        v6_best = max(v6_closed, key=lambda x: x.get("pnl_pct", 0) or 0) if v6_closed else None
        v6_worst = min(v6_closed, key=lambda x: x.get("pnl_pct", 0) or 0) if v6_closed else None

        # ===== V7 =====
        v7_state = self._fetch_state("openclaw_portfolio_state_v7")
        v7_all = self._fetch_positions_period("openclaw_positions_v7", week_start)
        v7_closed = [p for p in v7_all if p.get("status") == "CLOSED"]
        v7_wins = [p for p in v7_closed if (p.get("pnl_usd") or 0) > 0]
        v7_losses = [p for p in v7_closed if (p.get("pnl_usd") or 0) <= 0]
        v7_pnl_week = sum(p.get("pnl_usd", 0) or 0 for p in v7_closed)
        v7_wr_week = (len(v7_wins) / len(v7_closed) * 100) if v7_closed else 0
        v7_avg_win = (sum(p.get("pnl_pct", 0) or 0 for p in v7_wins) / len(v7_wins)) if v7_wins else 0
        v7_avg_loss = (sum(p.get("pnl_pct", 0) or 0 for p in v7_losses) / len(v7_losses)) if v7_losses else 0
        v7_tp1_total = sum(1 for p in v7_all if p.get("partial1_done"))
        v7_tp2_total = sum(1 for p in v7_all if p.get("partial2_done"))
        v7_trail_stops = sum(1 for p in v7_closed if p.get("close_reason") == "TRAIL_STOP")
        v7_be_stops = sum(1 for p in v7_closed if p.get("close_reason") == "BREAKEVEN_STOP")
        v7_sl_hits = sum(1 for p in v7_closed if p.get("close_reason") == "SL_HIT")
        v7_timeouts = sum(1 for p in v7_closed if p.get("close_reason") == "TIMEOUT_72H")
        v7_best = max(v7_closed, key=lambda x: x.get("pnl_pct", 0) or 0) if v7_closed else None
        v7_worst = min(v7_closed, key=lambda x: x.get("pnl_pct", 0) or 0) if v7_closed else None

        # ===== Build message =====
        msg = f"🏆 *COMPARAISON HEBDO V6 vs V7*\n"
        msg += f"📅 {(now - timedelta(days=7)).strftime('%d/%m')} → {now.strftime('%d/%m/%Y')}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        # Side-by-side table
        msg += "*Métrique*           │ *V6* │ *V7*\n"
        msg += "─────────────────────┼──────┼──────\n"
        msg += f"Trades clôturés       │ {len(v6_closed):>4} │ {len(v7_closed):>4}\n"
        msg += f"Wins                  │ {len(v6_wins):>4} │ {len(v7_wins):>4}\n"
        msg += f"Losses                │ {len(v6_losses):>4} │ {len(v7_losses):>4}\n"
        msg += f"Win Rate              │ {v6_wr_week:>3.0f}% │ {v7_wr_week:>3.0f}%\n"
        msg += f"PnL semaine ($)       │ {v6_pnl_week:>+4.0f} │ {v7_pnl_week:>+4.0f}\n"
        msg += f"PnL semaine (%)       │ {v6_pnl_week/50:>+3.1f}% │ {v7_pnl_week/50:>+3.1f}%\n"
        msg += f"Avg WIN %             │ {v6_avg_win:>+3.1f}% │ {v7_avg_win:>+3.1f}%\n"
        msg += f"Avg LOSS %            │ {v6_avg_loss:>+3.1f}% │ {v7_avg_loss:>+3.1f}%\n"
        msg += f"Balance actuelle      │ ${v6_state.get('balance', 5000):.0f} │ ${v7_state.get('balance', 5000):.0f}\n"

        msg += "\n*🔍 Raisons de fermeture*\n"
        msg += f"  V6 — TP: {v6_tp_hits} | SL: {v6_sl_hits} | Timeout: {v6_timeouts}\n"
        msg += f"  V7 — TP1: {v7_tp1_total} | TP2: {v7_tp2_total} | Trail: {v7_trail_stops} | BE: {v7_be_stops} | SL: {v7_sl_hits} | Timeout: {v7_timeouts}\n"

        if v6_best:
            msg += f"\n🥇 *Best V6*: `{v6_best['pair']}` {v6_best.get('pnl_pct', 0):+.1f}%"
        if v7_best:
            msg += f"\n🥇 *Best V7*: `{v7_best['pair']}` {v7_best.get('pnl_pct', 0):+.1f}%"
        if v6_worst:
            msg += f"\n💀 *Worst V6*: `{v6_worst['pair']}` {v6_worst.get('pnl_pct', 0):+.1f}%"
        if v7_worst:
            msg += f"\n💀 *Worst V7*: `{v7_worst['pair']}` {v7_worst.get('pnl_pct', 0):+.1f}%"

        msg += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"

        # Verdict
        if v6_pnl_week > v7_pnl_week:
            diff = v6_pnl_week - v7_pnl_week
            msg += f"\n🏆 *GAGNANT DE LA SEMAINE: 🟢 V6*\n"
            msg += f"📈 V6 surperforme V7 de *${diff:+.0f}* ({diff/50:+.1f}%)"
        elif v7_pnl_week > v6_pnl_week:
            diff = v7_pnl_week - v6_pnl_week
            msg += f"\n🏆 *GAGNANT DE LA SEMAINE: 🟣 V7*\n"
            msg += f"📈 V7 surperforme V6 de *${diff:+.0f}* ({diff/50:+.1f}%)"
        else:
            msg += "\n🟰 *Égalité parfaite*"

        # Insights
        msg += "\n\n💡 *Insights*:\n"
        if v6_wr_week > v7_wr_week + 5:
            msg += f"  • V6 a un meilleur WR (+{v6_wr_week-v7_wr_week:.0f}pts) — TP+15% fixe est plus régulier\n"
        elif v7_wr_week > v6_wr_week + 5:
            msg += f"  • V7 a un meilleur WR (+{v7_wr_week-v6_wr_week:.0f}pts) — TP1 partiel sécurise tôt\n"
        if v7_avg_win > v6_avg_win + 2:
            msg += f"  • V7 capture mieux les moonshots (avg win +{v7_avg_win-v6_avg_win:.1f}pts)\n"
        if v6_avg_win > v7_avg_win + 2:
            msg += f"  • V6 maximise les wins propres (avg win +{v6_avg_win-v7_avg_win:.1f}pts)\n"

        await self._send(msg)

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _calc_wr(self, state: Dict) -> int:
        tt = state.get("total_trades", 0) or 0
        w = state.get("wins", 0) or 0
        return int(w / tt * 100) if tt else 0

    async def _send(self, text: str):
        try:
            await self.bot.app.bot.send_message(
                chat_id=self.bot.chat_id, text=text, parse_mode="Markdown"
            )
        except Exception as e:
            print(f"⚠️ V6V7 send failed: {e}")
            try:
                # Fallback without markdown
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id, text=text
                )
            except Exception:
                pass
