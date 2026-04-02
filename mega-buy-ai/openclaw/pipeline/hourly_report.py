"""Hourly Autonomous Audit — OpenClaw reviews the ENTIRE system every hour.

OpenClaw does a full round-trip on all functional interfaces:
1. Reviews all alerts received and decisions made
2. Checks backtest results and extracts learnings
3. Reviews outcomes (WIN/LOSE/MISSED_BUY) with PnL
4. Checks simulation performance
5. Reviews its own insights and identifies gaps
6. Analyzes token budget usage
7. Self-critique: mistakes made and corrections needed
8. Plans actions for next hour

All findings are compiled into a detailed report saved to Supabase + Telegram.
"""

import asyncio
import json
import traceback
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from uuid import uuid4

from openclaw.config import get_settings


class HourlyReporter:
    """Autonomous hourly audit of the entire MEGA BUY system."""

    def __init__(self, telegram_bot=None):
        self.bot = telegram_bot
        self.settings = get_settings()
        self._running = False
        self._task = None

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._report_loop())
        print("📊 HourlyReporter started (report at XX:05 every hour)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _report_loop(self):
        while self._running:
            now = datetime.now(timezone.utc)
            target = now.replace(minute=5, second=0, microsecond=0)
            if now.minute >= 5:
                target += timedelta(hours=1)
            wait_secs = (target - now).total_seconds()
            await asyncio.sleep(wait_secs)
            try:
                await self._generate_hourly_report()
            except Exception as e:
                print(f"[HourlyReport] Error: {e}")
                traceback.print_exc()

    async def _generate_hourly_report(self):
        """Full autonomous audit of the entire system."""
        try:
            from supabase import create_client
            sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        except Exception as e:
            print(f"[HourlyReport] Supabase error: {e}")
            return

        now = datetime.now(timezone.utc)
        period_end = now
        period_start = now - timedelta(hours=1)
        start_iso = period_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_iso = period_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        today_start = now.strftime("%Y-%m-%dT00:00:00Z")

        print(f"[HourlyReport] Starting audit {period_start.strftime('%H:%M')} -> {period_end.strftime('%H:%M')} UTC")

        # ══════════════════════════════════════════════════════════
        # 1. ALERTS — What signals did we receive?
        # ══════════════════════════════════════════════════════════
        alerts_hour = []
        alerts_today = []
        try:
            r = sb.table("alerts").select("pair,scanner_score,timeframes,pp,ec,alert_timestamp") \
                .gte("alert_timestamp", start_iso).lte("alert_timestamp", end_iso) \
                .order("alert_timestamp", desc=True).execute()
            alerts_hour = r.data or []
        except Exception:
            pass
        try:
            r = sb.table("alerts").select("pair,scanner_score", count="exact") \
                .gte("alert_timestamp", today_start).execute()
            alerts_today = r.data or []
        except Exception:
            pass

        score_dist = {}
        for a in alerts_hour:
            s = a.get("scanner_score", 0)
            score_dist[s] = score_dist.get(s, 0) + 1

        top_alerts = [a for a in alerts_hour if a.get("scanner_score", 0) >= 8]

        # ══════════════════════════════════════════════════════════
        # 2. DECISIONS — What did OpenClaw decide?
        # ══════════════════════════════════════════════════════════
        decisions_hour = []
        decisions_today = []
        try:
            r = sb.table("agent_memory").select("*") \
                .gte("timestamp", start_iso).lte("timestamp", end_iso) \
                .order("timestamp", desc=True).execute()
            decisions_hour = r.data or []
        except Exception:
            pass
        try:
            r = sb.table("agent_memory").select("agent_decision,agent_confidence,outcome,pnl_pct,pair") \
                .gte("timestamp", today_start).execute()
            decisions_today = r.data or []
        except Exception:
            pass

        buy_h = [d for d in decisions_hour if "BUY" in (d.get("agent_decision") or "")]
        watch_h = [d for d in decisions_hour if d.get("agent_decision") == "WATCH"]
        skip_h = [d for d in decisions_hour if d.get("agent_decision") == "SKIP"]

        # ══════════════════════════════════════════════════════════
        # 3. OUTCOMES — Separate: hour / 24h / global
        # ══════════════════════════════════════════════════════════

        # 3a. Global outcomes (all time)
        all_with_outcome = []
        try:
            r = sb.table("agent_memory").select("pair,agent_decision,outcome,pnl_pct,agent_confidence,timestamp") \
                .in_("outcome", ["WIN", "LOSE", "MISSED_BUY", "CORRECT_WATCH", "EXPIRED_WIN", "EXPIRED_LOSE"]) \
                .order("timestamp", desc=True).limit(500).execute()
            all_with_outcome = r.data or []
        except Exception:
            pass

        wins_global = [d for d in all_with_outcome if d.get("outcome") == "WIN"]
        losses_global = [d for d in all_with_outcome if d.get("outcome") == "LOSE"]
        missed = [d for d in all_with_outcome if d.get("outcome") == "MISSED_BUY"]
        total_resolved = len(wins_global) + len(losses_global)
        wr_global = (len(wins_global) / total_resolved * 100) if total_resolved else 0
        avg_win = sum(d.get("pnl_pct", 0) or 0 for d in wins_global) / len(wins_global) if wins_global else 0
        avg_loss = sum(d.get("pnl_pct", 0) or 0 for d in losses_global) / len(losses_global) if losses_global else 0

        # 3b. Last 24h outcomes
        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        outcomes_24h = [d for d in all_with_outcome if (d.get("timestamp") or "") >= cutoff_24h]
        wins_24h = [d for d in outcomes_24h if d.get("outcome") == "WIN"]
        losses_24h = [d for d in outcomes_24h if d.get("outcome") == "LOSE"]
        wr_24h = (len(wins_24h) / (len(wins_24h) + len(losses_24h)) * 100) if (wins_24h or losses_24h) else 0

        # 3c. This hour's decisions — all PENDING (too early for outcomes)
        hour_pending = [d for d in decisions_hour if not d.get("outcome") or d.get("outcome") == "PENDING"]
        hour_resolved = [d for d in decisions_hour if d.get("outcome") in ("WIN", "LOSE")]

        # Current pending decisions with live PnL
        pending = []
        try:
            r = sb.table("agent_memory").select("pair,agent_decision,pnl_pct,agent_confidence,timestamp") \
                .eq("outcome", "PENDING").order("timestamp", desc=True).limit(50).execute()
            pending = r.data or []
        except Exception:
            pass

        pending_positive = [p for p in pending if (p.get("pnl_pct") or 0) > 0]
        pending_negative = [p for p in pending if (p.get("pnl_pct") or 0) < 0]
        pending_danger = [p for p in pending if (p.get("pnl_pct") or 0) <= -4]

        # ══════════════════════════════════════════════════════════
        # 4. BACKTESTS — Detailed backtest analysis
        # ══════════════════════════════════════════════════════════
        backtest_stats = {}
        backtest_top = []
        backtest_recent = []
        try:
            r = requests.get("http://localhost:9001/api/stats", timeout=5)
            if r.ok:
                backtest_stats = r.json()
        except Exception:
            pass
        # Get backtest details — top performers + recent
        try:
            r = requests.get("http://localhost:9001/api/backtests?limit=100", timeout=10)
            if r.ok:
                all_bt = r.json() if isinstance(r.json(), list) else []
                # Top performers: sort by pnl, filter those with trades
                with_trades = [b for b in all_bt if b.get("total_trades", 0) > 0]
                backtest_top = sorted(with_trades, key=lambda x: x.get("pnl_strategy_c", 0), reverse=True)[:5]
                backtest_recent = sorted(all_bt, key=lambda x: x.get("created_at", ""), reverse=True)[:5]
        except Exception:
            pass

        # ══════════════════════════════════════════════════════════
        # 5. INSIGHTS — What knowledge do we have?
        # ══════════════════════════════════════════════════════════
        insights_data = []
        new_insights = []
        try:
            r = sb.table("agent_insights").select("insight,category,priority,created_at") \
                .eq("active", True).order("priority", desc=True).limit(50).execute()
            insights_data = r.data or []
        except Exception:
            pass
        try:
            r = sb.table("agent_insights").select("insight,category") \
                .gte("created_at", start_iso).lte("created_at", end_iso).execute()
            new_insights = r.data or []
        except Exception:
            pass

        insights_by_cat = {}
        for i in insights_data:
            cat = i.get("category", "other")
            insights_by_cat[cat] = insights_by_cat.get(cat, 0) + 1

        # ══════════════════════════════════════════════════════════
        # 6. BUDGET — How much did we spend?
        # ══════════════════════════════════════════════════════════
        budget = {}
        try:
            from openclaw.agent.token_tracker import get_token_tracker
            budget = get_token_tracker().get_summary()
        except Exception:
            pass

        # ══════════════════════════════════════════════════════════
        # 7. SIMULATION — Full simulation analysis
        # ══════════════════════════════════════════════════════════
        sim_data = {}
        sim_positions = []
        try:
            r = requests.get("http://localhost:8001/api/overview", timeout=5)
            if r.ok:
                sim_data = r.json()
        except Exception:
            pass
        try:
            r = requests.get("http://localhost:8001/api/positions", timeout=5)
            if r.ok:
                sim_positions = r.json() if isinstance(r.json(), list) else []
        except Exception:
            pass

        # Extract portfolio strategies from simulation overview
        strategies_data = []
        if sim_data and sim_data.get("live", {}).get("portfolios"):
            strategies_data = sim_data["live"]["portfolios"]

        # ══════════════════════════════════════════════════════════
        # 8. SERVICE HEALTH — Are all services running?
        # ══════════════════════════════════════════════════════════
        services = {}
        try:
            r = requests.get("http://localhost:8002/watchdog", timeout=5)
            if r.ok:
                services = r.json().get("services", {})
        except Exception:
            pass

        # ══════════════════════════════════════════════════════════
        # BUILD THE REPORT
        # ══════════════════════════════════════════════════════════
        stats = {
            "alerts_hour": len(alerts_hour), "alerts_today": len(alerts_today),
            "decisions_hour": len(decisions_hour),
            "buy_count": len(buy_h), "watch_count": len(watch_h), "skip_count": len(skip_h),
            # Hour stats
            "hour_pending": len(hour_pending), "hour_resolved": len(hour_resolved),
            # 24h stats
            "wins_24h": len(wins_24h), "losses_24h": len(losses_24h), "wr_24h": round(wr_24h, 1),
            # Global stats
            "total_wins": len(wins_global), "total_losses": len(losses_global), "wr_global": round(wr_global, 1),
            "avg_win_pnl": round(avg_win, 1), "avg_loss_pnl": round(avg_loss, 1),
            "missed_buys": len(missed), "pending_count": len(pending),
            "pending_positive": len(pending_positive), "pending_negative": len(pending_negative),
            "pending_danger": len(pending_danger),
            "total_insights": len(insights_data), "new_insights": len(new_insights),
            "backtest_total": backtest_stats.get("total_backtests", 0),
            "backtest_symbols": backtest_stats.get("total_symbols", 0),
            "bt_wr": backtest_stats.get("win_rate_c", 0),
            "bt_avg_pnl": backtest_stats.get("avg_pnl_c", 0),
            "budget_spent": budget.get("budget", {}).get("spent_usd", 0) if isinstance(budget.get("budget"), dict) else budget.get("total_cost_usd", 0),
            "budget_remaining": budget.get("budget", {}).get("remaining_usd", 0) if isinstance(budget.get("budget"), dict) else budget.get("budget_remaining_usd", 0),
        }

        # Generate detailed report with GPT-4o-mini
        report = await self._generate_smart_report(
            period_start, period_end, stats,
            alerts_hour, decisions_hour, all_with_outcome,
            pending, pending_danger, new_insights, insights_by_cat,
            backtest_stats, backtest_top, backtest_recent,
            sim_data, sim_positions,
            strategies_data, services, budget
        )

        # Save to Supabase
        report_id = str(uuid4())
        try:
            sb.table("openclaw_reports").insert({
                "id": report_id,
                "report_type": "hourly",
                "period_start": start_iso,
                "period_end": end_iso,
                "content": report,
                "stats": stats,
                "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }).execute()
            print(f"[HourlyReport] Saved to Supabase")
        except Exception as e:
            print(f"[HourlyReport] Save error: {e}")

        # Send to Telegram
        if self.bot:
            tg = self._build_telegram(period_start, period_end, stats, pending_danger)
            try:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id, text=tg[:3900], parse_mode="Markdown"
                )
            except Exception:
                try:
                    await self.bot.app.bot.send_message(chat_id=self.bot.chat_id, text=tg[:3900])
                except Exception:
                    pass

        print(f"[HourlyReport] Complete — {stats['decisions_hour']} decisions, WR {stats['wr_global']}%")

    async def _generate_smart_report(self, start, end, stats,
                                      alerts, decisions, outcomes,
                                      pending, danger, new_insights, insights_cats,
                                      bt_stats, bt_top, bt_recent,
                                      sim_data, sim_positions,
                                      strategies_data, services, budget) -> str:
        """Generate comprehensive report using GPT-4o-mini."""

        # Build rich context for GPT
        decisions_list = "\n".join([
            f"  - {d.get('pair','?')} score={d.get('scanner_score') or d.get('features_fingerprint',{}).get('scanner_score','?')}/10 → "
            f"{d.get('agent_decision','?')} ({int((d.get('agent_confidence') or 0)*100)}%) "
            f"PnL={d.get('pnl_pct','?')}%"
            for d in decisions[:15]
        ]) or "  Aucune"

        outcomes_list = "\n".join([
            f"  - {d.get('pair','?')} {d.get('outcome','?')} PnL={d.get('pnl_pct','?')}% (decision={d.get('agent_decision','?')})"
            for d in outcomes[:10]
        ]) or "  Aucun outcome"

        pending_list = "\n".join([
            f"  - {p.get('pair','?')} {p.get('agent_decision','?')} PnL={p.get('pnl_pct','?')}%"
            for p in pending[:10]
        ]) or "  Aucun pending"

        danger_list = "\n".join([
            f"  ⚠️ {p.get('pair','?')} PnL={p.get('pnl_pct','?')}% (decision={p.get('agent_decision','?')})"
            for p in danger
        ]) or "  Aucun en danger"

        services_str = "\n".join([
            f"  - {k}: {'✅ UP' if v.get('alive') else '❌ DOWN'} (restarts: {v.get('restarts',0)})"
            for k, v in services.items()
        ]) or "  Non disponible"

        insights_str = "\n".join([f"  - {cat}: {count}" for cat, count in insights_cats.items()]) or "  Aucun"
        new_ins_str = "\n".join([f"  - [{i.get('category','')}] {i.get('insight','')[:100]}" for i in new_insights[:5]]) or "  Aucun nouveau"

        # Backtest details
        bt_top_str = "\n".join([
            f"  🏆 {b.get('symbol','?')} PnL={b.get('pnl_strategy_c',0):.1f}% trades={b.get('total_trades',0)} alertes={b.get('total_alerts',0)} validees={b.get('valid_entries',0)}"
            for b in (bt_top[:5] if isinstance(bt_top, list) else [])
        ]) or "  Aucun backtest avec trades"

        bt_recent_str = "\n".join([
            f"  📋 {b.get('symbol','?')} — alertes={b.get('total_alerts',0)} validees={b.get('valid_entries',0)} PnL={b.get('pnl_strategy_c',0):.1f}%"
            for b in (bt_recent[:5] if isinstance(bt_recent, list) else [])
        ]) or "  Aucun backtest recent"

        # Simulation details from overview
        sim_str = "  Non disponible"
        if sim_data and sim_data.get("live"):
            g = sim_data["live"].get("global", {})
            sim_str = (
                f"  💰 Capital total: ${g.get('total_balance', 0):,.2f} (initial: ${g.get('total_initial', 0):,.0f})\n"
                f"  📈 PnL total: ${g.get('total_pnl', 0):,.2f} ({g.get('total_return_pct', 0):.2f}%)\n"
                f"  📊 Positions ouvertes: {g.get('total_open_positions', 0)}\n"
                f"  🔄 Trades clotures: {g.get('total_trades', 0)}\n"
                f"  🔔 Alertes capturees: {sim_data['live'].get('alerts_captured', 0)}"
            )

        # Open positions details
        sim_pos_str = ""
        if sim_positions:
            top_pos = sorted(sim_positions, key=lambda x: x.get("current_pnl_pct", 0), reverse=True)
            sim_pos_str = "\n".join([
                f"  {'📈' if p.get('current_pnl_pct',0) > 0 else '📉'} {p.get('pair','?')} PnL={p.get('current_pnl_pct',0):.1f}% (${p.get('current_pnl_usd',0):.1f}) entry={p.get('entry_price',0)} SL={p.get('current_sl',0)}"
                for p in top_pos[:8]
            ])
        if not sim_pos_str:
            sim_pos_str = "  Aucune position ouverte"

        # Strategies from simulation portfolios
        strat_str = ""
        if strategies_data and isinstance(strategies_data, list):
            strat_str = "\n".join([
                f"  {'✅' if s.get('return_pct',0) > 0 else '❌'} {s.get('name','?')} — Balance: ${s.get('balance',0):,.1f} Return: {s.get('return_pct',0):.2f}% PnL: ${s.get('pnl_usd',0):.1f} Positions: {s.get('open_positions',0)} DD: {s.get('max_drawdown_pct',0):.2f}%"
                for s in strategies_data
            ])
        if not strat_str:
            strat_str = "  Aucune strategie disponible"

        prompt = f"""Tu es OpenClaw 🐾, agent IA autonome de trading crypto. Tu viens de faire un AUDIT COMPLET de tout le systeme MEGA BUY.
Genere un rapport d'audit horaire DETAILLE en markdown avec des EMOJIS et de la COULEUR.

═══ 📅 PERIODE: {start.strftime('%H:%M')} → {end.strftime('%H:%M')} UTC ({start.strftime('%d/%m/%Y')}) ═══

📡 ALERTES CETTE HEURE: {stats['alerts_hour']} (total aujourd'hui: {stats['alerts_today']})

🤖 MES DECISIONS: {stats['decisions_hour']}
  🟢 BUY: {stats['buy_count']} | 🟡 WATCH: {stats['watch_count']} | 🔴 SKIP: {stats['skip_count']}
Detail:
{decisions_list}

📊 BILAN OUTCOMES:
  ⏰ CETTE HEURE: {stats['decisions_hour']} decisions, {stats['hour_pending']} encore PENDING (trop tot pour un WR — les trades ont besoin de temps)
  📅 DERNIERES 24H: {stats['wins_24h']}W / {stats['losses_24h']}L → WR 24h: {stats['wr_24h']}%
  🌍 GLOBAL (all-time): {stats['total_wins']}W / {stats['total_losses']}L → WR: {stats['wr_global']}%
  💰 Gain moyen WIN: +{stats['avg_win_pnl']}% | 💸 Perte moyenne LOSE: {stats['avg_loss_pnl']}%
  🚨 MISSED BUY (WATCH rates): {stats['missed_buys']}
  📈 BACKTEST WR historique: {stats['bt_wr']}% (avg PnL: {stats['bt_avg_pnl']:.1f}%)

  ⚠️ IMPORTANT: Les decisions de cette heure sont presque toutes PENDING.
  Le WR se calcule sur les trades RESOLUS (apres +10% WIN ou -5% LOSE), pas en temps reel.
Derniers outcomes:
{outcomes_list}

⏳ POSITIONS EN COURS: {stats['pending_count']}
  📈 En profit: {stats['pending_positive']} | 📉 En perte: {stats['pending_negative']} | ⚠️ Danger (<-4%): {stats['pending_danger']}
{pending_list}

🚨 POSITIONS EN DANGER:
{danger_list}

═══ 📈 BACKTESTS (historique) ═══
  📊 Total: {bt_stats.get('total_backtests', 0)} backtests | {bt_stats.get('total_symbols', 0)} symboles
  🔔 Alertes historiques: {bt_stats.get('total_alerts', 0)} | ✅ Validees V5: {bt_stats.get('total_validated', 0)}
  📈 WR global backtest: {bt_stats.get('global_win_rate', '?')}%
Top performers:
{bt_top_str}
Derniers backtests:
{bt_recent_str}

═══ 🎮 SIMULATION ═══
{sim_str}
Positions ouvertes:
{sim_pos_str}

═══ 🎯 STRATEGIES (Portfolios Simulation) ═══
{strat_str}

═══ 🎓 INSIGHTS ═══
  Total actifs: {stats['total_insights']} | Nouveaux cette heure: {stats['new_insights']}
  Par categorie: {json.dumps(insights_cats)}
Nouveaux:
{new_ins_str}

═══ 💰 BUDGET ═══
  Depense totale: ${stats['budget_spent']:.2f} | Restant: ${stats['budget_remaining']:.2f}

═══ 🏥 SERVICES ═══
{services_str}

═══════════════════════════════════

GENERE un rapport RICHE avec EMOJIS dans CHAQUE section:

# 🐾 Rapport d'Audit Horaire — OpenClaw
**📅 Periode:** HH:MM → HH:MM UTC

## 📊 1. Synthese de l'Heure
(3-4 phrases avec contexte marche, resume des actions, tendance)

## 📡 2. Alertes et Decisions
(Pour CHAQUE decision: emoji + pair + score + decision + PnL live + justification)
(⭐ Mettre en avant les scores >= 8)

## 📈 3. Performance et Outcomes
(WR avec emoji vert/rouge, tendance hausse/baisse, positions prometteuses vs dangereuses)
(🚨 Si MISSED_BUY: analyser pourquoi et comment eviter)

## 🔬 4. Backtests (Historique)
(Progres, top performers du backtest, WR historique, alertes validees)
(⚠️ Si WR backtest different de WR live → analyser l'ecart)

## 🎮 5. Simulation
(Etat du portefeuille simulation, positions, PnL)
(Si pas de donnees: noter le probleme)

## 🎯 6. Strategies
(Performance des strategies, laquelle marche le mieux)
(Si pas de donnees: recommander des actions)

## 🎓 7. Apprentissage et Insights
(Nouveaux insights, gaps identifies, recommandations)

## 💰 8. Budget et Ressources
(Consommation, projection, optimisations possibles)

## 🪞 9. Auto-Critique
(✅ Ce que j'ai bien fait | ❌ Mes erreurs | 🔧 Corrections a appliquer)
(Sois HONNETE et SPECIFIQUE)

## 🎯 10. Plan Prochaine Heure
(📋 Actions concretes | 👀 Paires a surveiller | ⚡ Ameliorations)

## 🏥 11. Sante du Systeme
(Chaque service avec ✅/❌ + details)

Sois HONNETE dans l'auto-critique. Utilise des emojis partout. Donne des chiffres precis.
"""

        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.settings.openai_api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
                temperature=0.3,
            )
            content = response.choices[0].message.content or ""

            try:
                from openclaw.agent.token_tracker import get_token_tracker
                get_token_tracker().record_openai(dict(response.usage), "gpt-4o-mini")
            except Exception:
                pass

            return content
        except Exception as e:
            print(f"[HourlyReport] GPT error: {e}")
            return self._fallback_report(start, end, stats, decisions, pending, danger, services)

    def _fallback_report(self, start, end, stats, decisions, pending, danger, services) -> str:
        """Fallback report without LLM."""
        lines = [
            f"# Rapport d'Audit Horaire — OpenClaw",
            f"**Periode:** {start.strftime('%H:%M')} → {end.strftime('%H:%M')} UTC ({start.strftime('%d/%m/%Y')})\n",
            f"## 1. Synthese",
            f"- {stats['alerts_hour']} alertes recues, {stats['decisions_hour']} decisions",
            f"- BUY: {stats['buy_count']} | WATCH: {stats['watch_count']} | SKIP: {stats['skip_count']}",
            f"- WR global: {stats['wr_global']}% ({stats['total_wins']}W / {stats['total_losses']}L)",
            f"- MISSED BUY: {stats['missed_buys']}\n",
            f"## 2. Decisions cette heure",
        ]
        for d in decisions[:15]:
            p = d.get('pair', '?')
            dec = d.get('agent_decision', '?')
            conf = int((d.get('agent_confidence') or 0) * 100)
            pnl = d.get('pnl_pct')
            lines.append(f"- {p} → {dec} ({conf}%) {'PnL: ' + str(round(pnl,1)) + '%' if pnl else ''}")

        lines.append(f"\n## 3. Positions en cours ({stats['pending_count']})")
        lines.append(f"- En profit: {stats['pending_positive']} | En perte: {stats['pending_negative']} | Danger: {stats['pending_danger']}")
        if danger:
            lines.append("### Positions en danger:")
            for p in danger:
                lines.append(f"  ⚠️ {p.get('pair','?')} PnL={p.get('pnl_pct','?')}%")

        lines.append(f"\n## 4. Backtests: {stats['backtest_total']} total, {stats['backtest_symbols']} symboles")
        lines.append(f"\n## 5. Insights: {stats['total_insights']} actifs, {stats['new_insights']} nouveaux")
        lines.append(f"\n## 6. Budget: ${stats['budget_spent']:.2f} depense, ${stats['budget_remaining']:.2f} restant")

        lines.append(f"\n## 7. Services")
        for k, v in services.items():
            status = '✅' if v.get('alive') else '❌'
            lines.append(f"- {k}: {status}")

        lines.append(f"\n---\n_Rapport genere automatiquement (fallback)_")
        return "\n".join(lines)

    def _build_telegram(self, start, end, stats, danger) -> str:
        """Telegram summary."""
        h = start.strftime("%H:%M")
        he = end.strftime("%H:%M")
        d = start.strftime("%d/%m")

        lines = [
            f"📊 *Audit Horaire OpenClaw*",
            f"📅 {d} {h} → {he} UTC\n",
            f"📡 Alertes: {stats['alerts_hour']} | Decisions: {stats['decisions_hour']}",
            f"🟢 BUY: {stats['buy_count']} | 🟡 WATCH: {stats['watch_count']} | 🔴 SKIP: {stats['skip_count']}\n",
            f"📈 *Performance:*",
            f"⏰ Cette heure: {stats['hour_pending']} PENDING (en attente de resultat)",
            f"📅 24h: WR {stats['wr_24h']}% ({stats['wins_24h']}W / {stats['losses_24h']}L)",
            f"🌍 Global: WR {stats['wr_global']}% ({stats['total_wins']}W / {stats['total_losses']}L)",
        ]

        if stats['missed_buys']:
            lines.append(f"🚨 MISSED BUY: {stats['missed_buys']}")

        lines.append(f"\n⏳ Pending: {stats['pending_count']} ({stats['pending_positive']}↑ {stats['pending_negative']}↓)")

        if danger:
            lines.append(f"\n⚠️ *EN DANGER:*")
            for p in danger[:5]:
                lines.append(f"  {p.get('pair','?')} {p.get('pnl_pct','?')}%")

        lines.append(f"\n💰 Budget: ${stats['budget_remaining']:.2f} restant")
        lines.append(f"🎓 Insights: {stats['total_insights']} (+{stats['new_insights']} nouveau)")
        lines.append(f"📈 Backtests: {stats['backtest_total']}")
        lines.append(f"\n_Audit auto — OpenClaw_")
        return "\n".join(lines)
