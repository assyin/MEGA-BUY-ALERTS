"""Alert processing pipeline — orchestrates agent + telegram + memory."""

import asyncio
from typing import Optional
from pathlib import Path

from openclaw.agent.core import ClaudeAgent, AgentDecision
from openclaw.agent.circuit_breaker import CircuitBreaker
from openclaw.memory.store import MemoryStore
from openclaw.telegram.bot import OpenClawBot
from openclaw.pipeline.chart_generator import generate_alert_chart


class AlertProcessor:
    """Processes new alerts through the Claude agent pipeline."""

    def __init__(self, agent: ClaudeAgent, bot: OpenClawBot,
                 circuit_breaker: CircuitBreaker, memory: MemoryStore,
                 portfolio=None, portfolio_v2=None):
        self.agent = agent
        self.bot = bot
        self.circuit_breaker = circuit_breaker
        self.memory = memory
        self.portfolio = portfolio
        self.portfolio_v2 = portfolio_v2

    async def process_alert(self, alert: dict):
        """Full pipeline: analyze → decide → notify → record."""
        pair = alert.get("pair", "?")
        alert_id = alert.get("id", "")
        score = alert.get("scanner_score", 0)

        print(f"\n{'='*60}")
        print(f"🔍 Processing: {pair} (Score {score}/10)")
        print(f"{'='*60}")

        # 1. Check circuit breaker
        if self.circuit_breaker.is_tripped():
            print(f"🚨 Circuit breaker active — skipping {pair}")
            await self.bot._send_recommendation(
                f"⚠️ *{pair}* Score {score}/10\n\n"
                f"🚨 Circuit breaker actif — recommandation desactivee.\n"
                f"Trop de pertes recentes.",
                "SKIP", alert_id
            )
            return

        # 2. Send initial notification
        try:
            await self.bot.send_alert_notification(alert)
        except Exception:
            pass  # Non-critical

        # 3. Run Claude agent analysis
        try:
            decision = await asyncio.wait_for(
                self.agent.analyze_alert(alert),
                timeout=90  # 90s max
            )
        except asyncio.TimeoutError:
            print(f"⏰ Analysis timeout for {pair} — retry in 30s...")
            try:
                await self.bot.app.bot.send_message(
                    chat_id=self.bot.chat_id,
                    text=f"⏰ *{pair}* {score}/10 — Timeout 90s, retry dans 30s...",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            # RETRY after 30 seconds
            await asyncio.sleep(30)
            try:
                print(f"🔄 Retrying analysis for {pair}...")
                decision = await asyncio.wait_for(
                    self.agent.analyze_alert(alert),
                    timeout=120  # 120s for retry
                )
                print(f"✅ Retry succeeded for {pair}: {decision.decision}")
            except (asyncio.TimeoutError, Exception) as retry_err:
                print(f"❌ Retry also failed for {pair}: {retry_err}")
                decision = AgentDecision(
                    decision="WATCH", confidence=0.3,
                    reasoning="Analysis timed out twice (90s + 120s retry)",
                    raw_response="", tools_called=[], error="double_timeout"
                )
                try:
                    await self.bot._send_recommendation(
                        f"⏰ *{pair}* Score {score}/10\n"
                        f"🤖 _MEGA 4_\n\n"
                        f"Analyse timeout x2 (90s + 120s retry).\n"
                        f"Decision par defaut: WATCH",
                        "WATCH", alert_id
                    )
                except Exception:
                    pass
        except Exception as e:
            err_msg = str(e)[:100]
            print(f"❌ Analysis error for {pair}: {err_msg}")
            decision = AgentDecision(
                decision="WATCH", confidence=0.3,
                reasoning=f"Error: {err_msg}",
                raw_response="", tools_called=[], error=err_msg
            )
            # Send error notification
            try:
                await self.bot._send_recommendation(
                    f"❌ *{pair}* Score {score}/10\n\nErreur d'analyse: {err_msg}\nDecision: WATCH",
                    "WATCH", alert_id
                )
            except Exception:
                pass

        # 4. Log result + send Telegram for triage-only decisions
        is_triage_only = "mega_mini_triage" in decision.tools_called and "send_recommendation" not in decision.tools_called
        is_sonnet = "send_recommendation" in decision.tools_called
        if is_triage_only:
            model_label = "🤖 MEGA 4 Mini"
        elif is_sonnet:
            model_label = "🤖 MEGA 4"
        else:
            model_label = "🤖 MEGA 4 Mini"
        print(f"📋 Decision: {decision.decision} ({int(decision.confidence*100)}%) [{model_label}]")
        print(f"🔧 Tools called: {', '.join(decision.tools_called)}")

        # ALWAYS send Telegram notification for ALL decisions
        if "send_recommendation" not in decision.tools_called:
            try:
                emoji = {"BUY STRONG": "🟢🟢", "BUY": "🟢", "BUY WEAK": "🟡🟢", "WATCH": "🟡", "SKIP": "🔴"}.get(decision.decision, "⚪")
                # Full analysis — use raw_response which contains the complete formatted analysis
                full_analysis = decision.raw_response or decision.reasoning
                # Telegram limit is 4096 chars — send full analysis
                msg = (
                    f"{emoji} *{pair}* {score}/10 — {decision.decision} ({int(decision.confidence*100)}%)\n"
                    f"{model_label}\n\n"
                    f"{full_analysis[:3900]}"
                )
                print(f"📱 Sending Telegram for {pair} ({len(msg)} chars)...")
                await self.bot._send_recommendation(msg, decision.decision, alert_id)
                print(f"📱 Telegram sent for {pair}")
            except Exception as e:
                print(f"⚠️ Telegram send error for {pair}: {e}")
                # Retry without Markdown — split if too long
                try:
                    plain_text = f"{pair} {score}/10 — {decision.decision} ({int(decision.confidence*100)}%)\n{model_label}\n\n{full_analysis[:3900]}"
                    await self.bot.app.bot.send_message(
                        chat_id=self.bot.chat_id,
                        text=plain_text
                    )
                except Exception:
                    pass

        # 5. Save to memory (with full analysis text + price + VIP + Quality for tracking)
        vip = getattr(decision, 'vip', None) or {}
        quality = getattr(decision, 'quality', None) or {}
        features = {
            "scanner_score": score,
            "timeframes": alert.get("timeframes", []),
            "di_plus_4h": alert.get("di_plus_4h"),
            "di_minus_4h": alert.get("di_minus_4h"),
            "adx_4h": alert.get("adx_4h"),
            "pp": alert.get("pp"),
            "ec": alert.get("ec"),
            "price": alert.get("price"),
            "rsi": alert.get("rsi"),
            "is_vip": vip.get("is_vip", False),
            "is_high_ticket": vip.get("is_high_ticket", False),
            "vip_score": vip.get("vip_score", 0),
            "vip_reasons": vip.get("reasons", []),
            "quality_grade": quality.get("grade", ""),
            "quality_axes": quality.get("axes", 0),
            "quality_details": quality.get("details", []),
        }
        # Save full analysis text (not truncated) for the OpenClaw tracker dashboard
        full_analysis_text = decision.raw_response or decision.reasoning
        self.memory.save_pattern(
            alert_id, pair, features,
            decision.decision, decision.confidence, decision.reasoning[:500],
            analysis_text=full_analysis_text[:4000]
        )

        # 6. Generate chart + portfolio position (reuse analysis data)
        analysis_summary = None
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backtest"))
            from api.realtime_analyze import analyze_alert_realtime
            from openclaw.agent.tool_handlers import _smart_summary

            # Get FULL analysis (not the smart_summary — we need raw data for chart)
            full_analysis = await asyncio.to_thread(
                analyze_alert_realtime, pair,
                alert.get("alert_timestamp", ""),
                alert.get("price", 0)
            )

            # Build smart summary for portfolio SL/TP calculation
            try:
                analysis_summary = _smart_summary(full_analysis)
            except Exception:
                analysis_summary = {}

            chart_path = await asyncio.to_thread(
                generate_alert_chart, pair, full_analysis,
                alert.get("price", 0), "1h", 80
            )
            # Update features_fingerprint with accumulation data from realtime analysis
            acc_data = {}
            if full_analysis and isinstance(full_analysis, dict):
                acc_raw = full_analysis.get("accumulation", {})
                if isinstance(acc_raw, dict) and acc_raw.get("detected"):
                    acc_data = {
                        "accumulation_days": round(acc_raw.get("days", 0), 1),
                        "accumulation_hours": round(acc_raw.get("hours", 0)),
                        "accumulation_range_pct": round(acc_raw.get("range_pct", 0), 1),
                    }

            if chart_path:
                await self.bot.app.bot.send_photo(
                    chat_id=self.bot.chat_id,
                    photo=open(chart_path, 'rb'),
                    caption=f"📊 {pair} — {score}/10 — {decision.decision}"
                )
                print(f"📊 Chart sent for {pair}")

            # Save chart path + accumulation to agent_memory
            try:
                from openclaw.config import get_settings
                from supabase import create_client as _sc
                _s = get_settings()
                _sb = _sc(_s.supabase_url, _s.supabase_service_key)
                update_fields = {}
                if chart_path:
                    update_fields["chart_path"] = str(chart_path)
                if acc_data:
                    # Merge accumulation into existing features_fingerprint
                    existing = _sb.table("agent_memory").select("features_fingerprint").eq("alert_id", alert_id).single().execute()
                    fp = (existing.data or {}).get("features_fingerprint") or {}
                    fp.update(acc_data)
                    update_fields["features_fingerprint"] = fp
                if update_fields:
                    _sb.table("agent_memory") \
                        .update(update_fields) \
                        .eq("alert_id", alert_id) \
                        .execute()
            except Exception:
                pass
        except Exception as e:
            print(f"⚠️ Chart error for {pair}: {e}")

        # 6b. Portfolio V1 — open position if BUY decision
        if self.portfolio and "BUY" in decision.decision:
            try:
                pos = await self.portfolio.try_open_position(
                    pair=pair,
                    decision=decision.decision,
                    confidence=decision.confidence,
                    analysis_summary=analysis_summary or {},
                    alert=alert,
                    vip=vip,
                )
                if pos:
                    print(f"💼 V1 Position opened for {pair}: ${pos['size_usd']:.2f} @ {pos['entry_price']}")
            except Exception as e:
                print(f"⚠️ Portfolio V1 error for {pair}: {e}")

        # 6c. Portfolio V2 — parallel execution with partial TP + trailing
        quality = getattr(decision, 'quality', None)
        if self.portfolio_v2 and "BUY" in decision.decision:
            try:
                pos2 = await self.portfolio_v2.try_open_position(
                    pair=pair,
                    decision=decision.decision,
                    confidence=decision.confidence,
                    analysis_summary=analysis_summary or {},
                    alert=alert,
                    vip=vip,
                    quality=quality,
                )
                if pos2:
                    print(f"💼 V2 Position opened for {pair}: ctx={pos2.get('context_score',0)} ${pos2['size_usd']:.2f} @ {pos2['entry_price']}")
            except Exception as e:
                print(f"⚠️ Portfolio V2 error for {pair}: {e}")

        # 7. Increment counter
        self.memory.increment_processed()

        print(f"✅ {pair} processed — {decision.decision}")
