"""OpenClaw — Main entry point.

Starts the FastAPI server with:
- Alert listener (polls Supabase every 15s)
- Telegram bot (commands + inline buttons)
- Claude agent (tool-use analysis)
- Outcome tracker (learning from results)
"""

import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from openclaw.config import get_settings
from openclaw.agent.core import ClaudeAgent
from openclaw.agent.circuit_breaker import CircuitBreaker
from openclaw.memory.store import MemoryStore
from openclaw.telegram.bot import OpenClawBot
from openclaw.pipeline.alert_listener import AlertListener
from openclaw.pipeline.processor import AlertProcessor
from openclaw.pipeline.outcome_tracker import OutcomeTracker
from openclaw.pipeline.auto_backtest import AutoBacktester
from openclaw.pipeline.watchdog import Watchdog
from openclaw.pipeline.self_trainer import SelfTrainer
from openclaw.pipeline.daily_report import DailyReporter
from openclaw.pipeline.hourly_report import HourlyReporter
from openclaw.pipeline.v6v7_reporter import V6V7Reporter
from openclaw.pipeline.timing_analyzer import TimingAnalyzer
from openclaw.agent.chat import ChatManager
from openclaw.portfolio.manager import PortfolioManager
from openclaw.portfolio.manager_v2 import PortfolioManagerV2
from openclaw.portfolio.manager_v3 import PortfolioManagerV3
from openclaw.portfolio.manager_v4 import PortfolioManagerV4
from openclaw.portfolio.manager_v5 import PortfolioManagerV5
from openclaw.portfolio.manager_v6 import PortfolioManagerV6
from openclaw.portfolio.manager_v7 import PortfolioManagerV7
from openclaw.portfolio.manager_v8 import PortfolioManagerV8
from openclaw.portfolio.manager_v9 import PortfolioManagerV9
from openclaw.portfolio.manager_v11 import (
    PortfolioManagerV11A, PortfolioManagerV11B, PortfolioManagerV11C,
    PortfolioManagerV11D, PortfolioManagerV11E,
)
from openclaw.audit.engagements import EngagementTracker


# Global references
_agent: Optional[ClaudeAgent] = None
_bot: Optional[OpenClawBot] = None
_listener: Optional[AlertListener] = None
_processor: Optional[AlertProcessor] = None
_tracker: Optional[OutcomeTracker] = None
_memory: Optional[MemoryStore] = None
_chat: Optional[ChatManager] = None
_auto_bt: Optional[AutoBacktester] = None
_watchdog: Optional[Watchdog] = None
_self_trainer: Optional[SelfTrainer] = None
_daily_reporter: Optional[DailyReporter] = None
_hourly_reporter: Optional[HourlyReporter] = None
_timing: Optional[TimingAnalyzer] = None
_portfolio: Optional[PortfolioManager] = None
_portfolio_v2: Optional[PortfolioManagerV2] = None
_portfolio_v3: Optional[PortfolioManagerV3] = None
_portfolio_v4: Optional[PortfolioManagerV4] = None
_portfolio_v5: Optional[PortfolioManagerV5] = None
_portfolio_v6: Optional[PortfolioManagerV6] = None
_portfolio_v7: Optional[PortfolioManagerV7] = None
_portfolio_v8: Optional[PortfolioManagerV8] = None
_portfolio_v9: Optional[PortfolioManagerV9] = None
_portfolio_v11a: Optional[PortfolioManagerV11A] = None
_portfolio_v11b: Optional[PortfolioManagerV11B] = None
_portfolio_v11c: Optional[PortfolioManagerV11C] = None
_portfolio_v11d: Optional[PortfolioManagerV11D] = None
_portfolio_v11e: Optional[PortfolioManagerV11E] = None
_v6v7_reporter: Optional[V6V7Reporter] = None
_engagements: Optional[EngagementTracker] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    global _agent, _bot, _listener, _processor, _tracker, _memory, _chat, _auto_bt, _watchdog, _self_trainer, _daily_reporter, _hourly_reporter, _timing, _portfolio, _portfolio_v2, _portfolio_v3, _portfolio_v4, _portfolio_v5, _portfolio_v6, _portfolio_v7, _portfolio_v8, _portfolio_v9, _portfolio_v11a, _portfolio_v11b, _portfolio_v11c, _portfolio_v11d, _portfolio_v11e, _v6v7_reporter, _engagements

    settings = get_settings()
    print("=" * 60)
    print("  🐾 OpenClaw — AI Trading Assistant for MEGA BUY")
    print("=" * 60)
    print(f"  Model: {settings.openclaw_model}")
    print(f"  Telegram: {'configured' if settings.telegram_token else 'NOT configured'}")
    print(f"  Supabase: {'connected' if settings.supabase_url else 'NOT configured'}")
    print(f"  Poll interval: {settings.poll_interval_sec}s")
    print("=" * 60)

    # Initialize components
    _memory = MemoryStore()
    _chat = ChatManager()
    _agent = ClaudeAgent()
    cb = CircuitBreaker(_memory, settings.max_daily_losses, settings.max_weekly_losses)
    _bot = OpenClawBot(_agent, cb, _memory)
    _portfolio = PortfolioManager(telegram_bot=_bot)
    _portfolio_v2 = PortfolioManagerV2(telegram_bot=_bot)
    _portfolio_v3 = PortfolioManagerV3(telegram_bot=_bot)
    _portfolio_v4 = PortfolioManagerV4(telegram_bot=_bot)
    _portfolio_v5 = PortfolioManagerV5(telegram_bot=_bot)
    _portfolio_v6 = PortfolioManagerV6(telegram_bot=_bot)
    _portfolio_v7 = PortfolioManagerV7(telegram_bot=_bot)
    _portfolio_v8 = PortfolioManagerV8(telegram_bot=_bot)
    _portfolio_v9 = PortfolioManagerV9(telegram_bot=_bot)
    _portfolio_v11a = PortfolioManagerV11A(telegram_bot=_bot)
    _portfolio_v11b = PortfolioManagerV11B(telegram_bot=_bot)
    _portfolio_v11c = PortfolioManagerV11C(telegram_bot=_bot)
    _portfolio_v11d = PortfolioManagerV11D(telegram_bot=_bot)
    _portfolio_v11e = PortfolioManagerV11E(telegram_bot=_bot)
    _processor = AlertProcessor(
        _agent, _bot, cb, _memory,
        portfolio=_portfolio, portfolio_v2=_portfolio_v2, portfolio_v3=_portfolio_v3,
        portfolio_v4=_portfolio_v4, portfolio_v5=_portfolio_v5, portfolio_v6=_portfolio_v6,
        portfolio_v7=_portfolio_v7, portfolio_v8=_portfolio_v8, portfolio_v9=_portfolio_v9,
        portfolio_v11a=_portfolio_v11a, portfolio_v11b=_portfolio_v11b,
        portfolio_v11c=_portfolio_v11c, portfolio_v11d=_portfolio_v11d,
        portfolio_v11e=_portfolio_v11e,
    )
    _tracker = OutcomeTracker(_memory, cb, telegram_bot=_bot)
    _listener = AlertListener(on_new_alert=_processor.process_alert)

    # Auto-backtester — V5 strategy on ~50 days (01/02 → 23/03)
    _auto_bt = AutoBacktester(
        min_volume_usd=500_000,
        backtest_days=50,        # ~50 days (01/02 → 23/03)
        delay_between_sec=60,    # 1 min between backtests (avoid overload)
        max_concurrent=1,
    )

    # Watchdog — monitors all services, auto-restarts if down
    _watchdog = Watchdog(check_interval=60)

    # Self-trainer — learns from market winners every 30 min
    _self_trainer = SelfTrainer(
        chat_manager=_chat,
        telegram_bot=_bot,
        min_gain_pct=10.0,       # Analyze pairs with >10% gain (lowered from 15% per AVIS recommendation)
        interval_minutes=30,      # Every 30 min
    )

    # Daily reporter — sends performance summary at 23:00 UTC
    _daily_reporter = DailyReporter(telegram_bot=_bot, outcome_tracker=_tracker)

    # Hourly reporter — detailed activity report every hour at XX:05
    _hourly_reporter = HourlyReporter(telegram_bot=_bot)

    # Timing analyzer — P4 pattern timing (golden hours + best days)
    _timing = TimingAnalyzer()

    # V6/V7 Reporter — daily 22:30 UTC + weekly Sunday 22:00 UTC
    _v6v7_reporter = V6V7Reporter(telegram_bot=_bot)

    # Engagement tracker — daily check of audit commitments at 22:00 UTC
    _engagements = EngagementTracker()

    # Start all components
    await _bot.start()
    await _listener.start()
    await _tracker.start()
    await _auto_bt.start()
    await _watchdog.start()
    await _self_trainer.start()
    await _daily_reporter.start()
    await _hourly_reporter.start()
    await _timing.start()
    await _portfolio.start()
    await _portfolio_v2.start()
    await _portfolio_v3.start()
    await _portfolio_v4.start()
    await _portfolio_v5.start()
    await _portfolio_v6.start()
    await _portfolio_v7.start()
    await _portfolio_v8.start()
    await _portfolio_v9.start()
    await _portfolio_v11a.start()
    await _portfolio_v11b.start()
    await _portfolio_v11c.start()
    await _portfolio_v11d.start()
    await _portfolio_v11e.start()
    await _v6v7_reporter.start()
    await _engagements.start()

    print("\n🟢 OpenClaw is LIVE — V1+V2 portfolios + alerts + backtesting + watchdog + self-training + timing + engagements + hourly/daily reports 24/7\n")

    yield

    # Shutdown
    print("\n🔴 Shutting down OpenClaw...")
    await _listener.stop()
    await _tracker.stop()
    if _auto_bt:
        await _auto_bt.stop()
    if _watchdog:
        await _watchdog.stop()
    if _self_trainer:
        await _self_trainer.stop()
    if _daily_reporter:
        await _daily_reporter.stop()
    if _hourly_reporter:
        await _hourly_reporter.stop()
    if _timing:
        await _timing.stop()
    if _portfolio:
        await _portfolio.stop()
    if _portfolio_v2:
        await _portfolio_v2.stop()
    if _portfolio_v3:
        await _portfolio_v3.stop()
    if _portfolio_v4:
        await _portfolio_v4.stop()
    if _portfolio_v5:
        await _portfolio_v5.stop()
    if _portfolio_v6:
        await _portfolio_v6.stop()
    if _portfolio_v7:
        await _portfolio_v7.stop()
    if _portfolio_v11a: await _portfolio_v11a.stop()
    if _portfolio_v11b: await _portfolio_v11b.stop()
    if _portfolio_v11c: await _portfolio_v11c.stop()
    if _portfolio_v11d: await _portfolio_v11d.stop()
    if _portfolio_v11e: await _portfolio_v11e.stop()
    if _v6v7_reporter:
        await _v6v7_reporter.stop()
    if _engagements:
        await _engagements.stop()
    await _bot.stop()


app = FastAPI(
    title="OpenClaw — AI Trading Assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    # Sync endpoint — runs in threadpool, not blocked by event loop sync-I/O
    return {"status": "ok", "service": "openclaw"}


@app.post("/outcomes/refresh")
async def refresh_outcomes():
    """Force an immediate PnL update for all pending decisions."""
    if not _tracker:
        return {"error": "Tracker not initialized"}
    try:
        await _tracker._check_all_pending()
        return {"status": "ok", "message": "PnL refreshed"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/status")
async def status():
    if not _memory:
        return {"status": "not initialized"}
    settings = get_settings()
    cb = CircuitBreaker(_memory, settings.max_daily_losses, settings.max_weekly_losses)
    return {
        "status": "running",
        "circuit_breaker": cb.get_status(),
        "memory": _memory.get_stats(),
    }


@app.post("/backfill")
async def backfill_alerts(hours: int = 24, min_score: int = 6, limit: int = 50, dry_run: bool = False):
    """Replay missed alerts from the last N hours that were never processed by OpenClaw.

    Fetches alerts newer than `hours` ago from Supabase, skips those whose id is already in
    agent_memory.alert_id, filters by score and tradability, then dispatches them through the
    normal AlertProcessor (same path as AlertListener). Use dry_run=true to preview only.
    """
    if not _processor or not _listener:
        return {"error": "Processor/listener not initialized"}

    from datetime import timedelta
    from openclaw.pipeline.pair_filter import is_tradable, STABLECOIN_BLACKLIST

    sb = _listener.sb
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    try:
        processed_res = sb.table("agent_memory").select("alert_id").not_.is_("alert_id", "null").execute()
        already_processed = {r["alert_id"] for r in (processed_res.data or []) if r.get("alert_id")}

        res = sb.table("alerts").select("*, decisions(*)") \
            .gte("alert_timestamp", cutoff) \
            .order("alert_timestamp", desc=True) \
            .limit(500).execute()

        candidates = []
        seen_pair_bougie = set()
        for alert in (res.data or []):
            aid = alert.get("id")
            pair = alert.get("pair", "")
            score = alert.get("scanner_score", 0) or 0
            if not aid or aid in already_processed:
                continue
            if pair in STABLECOIN_BLACKLIST or not is_tradable(pair):
                continue
            if score < min_score:
                continue
            dedup_key = f"{pair}_{alert.get('bougie_4h','')}"
            if dedup_key in seen_pair_bougie:
                continue
            seen_pair_bougie.add(dedup_key)
            candidates.append(alert)

        candidates.sort(key=lambda a: (a.get("scanner_score", 0), len(a.get("timeframes", []) or [])), reverse=True)
        to_process = candidates[:limit]

        preview = [{"pair": a.get("pair"), "score": a.get("scanner_score"),
                    "tfs": a.get("timeframes"), "ts": a.get("alert_timestamp")} for a in to_process]

        if dry_run:
            return {"hours": hours, "min_score": min_score, "found": len(candidates),
                    "would_process": len(to_process), "preview": preview}

        async def _run():
            sem = asyncio.Semaphore(3)
            async def _one(a):
                async with sem:
                    try:
                        print(f"🔁 Backfill: {a.get('pair')} {a.get('scanner_score')}/10")
                        _listener._seen_ids.add(a.get("id"))
                        await _processor.process_alert(a)
                    except Exception as e:
                        print(f"⚠️ Backfill error {a.get('pair')}: {e}")
            await asyncio.gather(*[_one(a) for a in to_process], return_exceptions=True)
            print(f"✅ Backfill done: {len(to_process)} alerts replayed")

        asyncio.create_task(_run())
        return {"status": "started", "hours": hours, "min_score": min_score,
                "found": len(candidates), "processing": len(to_process), "preview": preview}
    except Exception as e:
        return {"error": str(e)}


@app.post("/analyze/{pair}")
async def manual_analyze(pair: str):
    """Trigger manual analysis for a pair."""
    if not _agent:
        return {"error": "Agent not initialized"}

    pair = pair.upper()
    if not pair.endswith("USDT"):
        pair += "USDT"

    alert = {
        "id": "", "pair": pair, "price": 0, "scanner_score": 0,
        "timeframes": [], "alert_timestamp": "",
    }
    decision = await _agent.analyze_alert(alert)
    return {
        "pair": pair,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "reasoning": decision.reasoning[:500],
        "tools_called": decision.tools_called,
    }


@app.post("/reanalyze/{memory_id}")
async def reanalyze_decision(memory_id: str):
    """Regenerate analysis for an existing decision and resend to Telegram."""
    if not _agent or not _bot:
        return {"error": "Agent or bot not initialized"}

    from supabase import create_client as _sc
    settings = get_settings()
    sb = _sc(settings.supabase_url, settings.supabase_service_key)

    # 1. Get the decision from agent_memory
    try:
        result = sb.table("agent_memory").select("*").eq("id", memory_id).single().execute()
        mem = result.data
    except Exception:
        return {"error": f"Decision {memory_id} not found"}

    if not mem:
        return {"error": "Decision not found"}

    pair = mem.get("pair", "")
    features = mem.get("features_fingerprint", {}) or {}
    alert_id = mem.get("alert_id", "")

    # 2. Get original alert data from alerts table
    alert_data = {}
    if alert_id:
        try:
            ar = sb.table("alerts").select("*").eq("id", alert_id).single().execute()
            alert_data = ar.data or {}
        except Exception:
            pass

    # 3. Build alert dict for re-analysis
    alert = {
        "id": alert_id,
        "pair": pair,
        "price": features.get("price", alert_data.get("price", 0)),
        "scanner_score": features.get("scanner_score", alert_data.get("scanner_score", 0)),
        "timeframes": features.get("timeframes", alert_data.get("timeframes", [])),
        "alert_timestamp": alert_data.get("alert_timestamp", mem.get("timestamp", "")),
        "pp": features.get("pp", alert_data.get("pp", False)),
        "ec": features.get("ec", alert_data.get("ec", False)),
        "di_plus_4h": features.get("di_plus_4h", alert_data.get("di_plus_4h", 0)),
        "di_minus_4h": features.get("di_minus_4h", alert_data.get("di_minus_4h", 0)),
        "adx_4h": features.get("adx_4h", alert_data.get("adx_4h", 0)),
        "rsi": features.get("rsi", alert_data.get("rsi")),
        "lazy_values": alert_data.get("lazy_values"),
        "ec_moves": alert_data.get("ec_moves"),
        "vol_pct": alert_data.get("vol_pct"),
        "rsi_moves": alert_data.get("rsi_moves"),
        "di_plus_moves": alert_data.get("di_plus_moves"),
        "di_minus_moves": alert_data.get("di_minus_moves"),
    }

    score = alert["scanner_score"]

    # 4. Re-run analysis
    try:
        decision = await _agent.analyze_alert(alert)
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

    # 5. Update agent_memory with new analysis
    full_analysis = decision.raw_response or decision.reasoning
    try:
        update_data = {
            "agent_decision": decision.decision,
            "agent_confidence": decision.confidence,
            "agent_reasoning": decision.reasoning[:500],
        }
        # Try to add analysis_text (column may not exist)
        try:
            sb.table("agent_memory").update({**update_data, "analysis_text": full_analysis[:4000]}).eq("id", memory_id).execute()
        except Exception:
            sb.table("agent_memory").update(update_data).eq("id", memory_id).execute()
    except Exception as e:
        print(f"⚠️ Reanalyze update error: {e}")

    # 6. Send to Telegram
    try:
        emoji = {"BUY STRONG": "🟢🟢", "BUY": "🟢", "BUY WEAK": "🟡🟢", "WATCH": "🟡", "SKIP": "🔴"}.get(decision.decision, "⚪")
        msg = (
            f"🔄 *Re-analyse: {pair}* {score}/10 — {decision.decision} ({int(decision.confidence*100)}%)\n"
            f"🤖 MEGA 4 Mini\n\n"
            f"{full_analysis[:3900]}"
        )
        await _bot.app.bot.send_message(
            chat_id=_bot.chat_id, text=msg, parse_mode="Markdown"
        )
    except Exception:
        try:
            await _bot.app.bot.send_message(
                chat_id=_bot.chat_id, text=msg[:3900]
            )
        except Exception:
            pass

    return {
        "status": "ok",
        "pair": pair,
        "decision": decision.decision,
        "confidence": decision.confidence,
        "analysis_length": len(full_analysis),
        "telegram_sent": True,
    }


# ===== CHAT ENDPOINTS =====

@app.get("/chat/conversations")
async def list_conversations():
    if not _chat:
        return {"conversations": []}
    return {"conversations": _chat.list_conversations()}


@app.post("/chat/conversations")
async def create_conversation(body: dict = None):
    if not _chat:
        return {"error": "Chat not initialized"}
    title = (body or {}).get("title", "Nouvelle conversation")
    conv_id = _chat.create_conversation(title)
    return {"id": conv_id, "title": title}


@app.get("/chat/conversations/{conv_id}")
async def get_conversation(conv_id: str):
    if not _chat:
        return {"error": "Chat not initialized"}
    conv = _chat.get_conversation(conv_id)
    if not conv:
        return {"error": "Not found"}
    return conv


@app.post("/chat/conversations/{conv_id}/messages")
async def send_message(conv_id: str, body: dict):
    if not _chat:
        return {"error": "Chat not initialized"}
    message = body.get("message", "")
    if not message:
        return {"error": "Empty message"}
    response = await _chat.send_message(conv_id, message)
    return {"response": response}


@app.delete("/chat/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    if not _chat:
        return {"error": "Chat not initialized"}
    _chat.delete_conversation(conv_id)
    return {"deleted": True}


# ===== INSIGHTS ENDPOINTS =====

@app.get("/insights")
async def get_insights():
    """Get all active insights learned from conversations."""
    if not _chat:
        return {"insights": []}
    return {"insights": _chat.insights.get_active_insights()}


@app.delete("/insights/{insight_id}")
async def deactivate_insight(insight_id: str):
    """Deactivate an insight."""
    if not _chat:
        return {"error": "Chat not initialized"}
    _chat.insights.deactivate_insight(insight_id)
    return {"deactivated": True}


# ===== TOKEN USAGE ENDPOINT =====

# ===== AUTO-BACKTEST ENDPOINT =====

@app.get("/backtest/auto/status")
async def auto_backtest_status():
    """Get auto-backtester status."""
    if not _auto_bt:
        return {"running": False}
    status = _auto_bt.get_status()
    # Add backtest DB stats
    try:
        import requests as req
        r = req.get("http://localhost:9001/api/stats", timeout=5)
        status["db_stats"] = r.json()
    except Exception:
        pass
    return status


@app.get("/training/status")
async def training_status():
    """Get self-trainer status."""
    if not _self_trainer:
        return {"running": False}
    return _self_trainer.get_status()


@app.get("/timing")
async def timing_results():
    """Get latest pattern timing analysis (golden hours, best/worst days)."""
    if not _timing:
        return {"error": "TimingAnalyzer not initialized"}
    results = _timing.get_results()
    if not results:
        return {"status": "pending", "message": "Analysis not yet completed"}
    return results


@app.get("/chart/{alert_id}")
async def get_chart(alert_id: str):
    """Serve chart image for a given alert."""
    import os, glob
    from fastapi.responses import FileResponse
    from pathlib import Path as _P

    # Method 1: Try chart_path from agent_memory
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("agent_memory") \
            .select("chart_path,pair") \
            .eq("alert_id", alert_id) \
            .limit(1) \
            .execute()
        if result.data:
            row = result.data[0]
            # Try chart_path directly
            path = row.get("chart_path", "")
            if path and os.path.exists(path):
                return FileResponse(path, media_type="image/png")
            # Method 2: Search by pair name in charts dir
            pair = row.get("pair", "")
            if pair:
                charts_dir = _P(__file__).parent / "data" / "charts"
                matches = sorted(glob.glob(str(charts_dir / f"{pair}_*.png")), reverse=True)
                if matches:
                    return FileResponse(matches[0], media_type="image/png")
    except Exception:
        pass

    # Method 3: Try alert_id-based search in charts dir
    charts_dir = _P(__file__).parent / "data" / "charts"
    if charts_dir.exists():
        matches = sorted(glob.glob(str(charts_dir / f"*{alert_id[:8]}*.png")), reverse=True)
        if matches:
            return FileResponse(matches[0], media_type="image/png")

    return {"error": "Chart not found"}


@app.get("/charts/{pair}")
async def get_chart_by_pair(pair: str):
    """Serve latest chart for a pair."""
    import glob
    from fastapi.responses import FileResponse
    from pathlib import Path as _P

    pair = pair.upper()
    charts_dir = _P(__file__).parent / "data" / "charts"
    matches = sorted(glob.glob(str(charts_dir / f"{pair}_*.png")), reverse=True)
    if matches:
        return FileResponse(matches[0], media_type="image/png")
    return {"error": f"No chart for {pair}"}


# ===== REPORTS ENDPOINTS =====

@app.post("/reports/generate")
async def generate_report_now(body: dict = None):
    """Manually trigger report generation. Body: {"type": "hourly"} or {"type": "daily"}."""
    report_type = (body or {}).get("type", "hourly")
    if report_type == "hourly" and _hourly_reporter:
        try:
            await _hourly_reporter._generate_hourly_report()
            return {"status": "ok", "type": "hourly", "message": "Rapport horaire genere et envoye sur Telegram"}
        except Exception as e:
            return {"error": str(e)}
    elif report_type == "daily" and _daily_reporter:
        try:
            await _daily_reporter._send_daily_report()
            return {"status": "ok", "type": "daily", "message": "Rapport journalier genere et envoye sur Telegram"}
        except Exception as e:
            return {"error": str(e)}
    return {"error": f"Reporter '{report_type}' not available"}


@app.get("/reports")
async def list_reports(type: str = None, limit: int = 20, offset: int = 0):
    """List all reports, paginated, most recent first. Optional filter by type (hourly/daily)."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        query = sb.table("openclaw_reports").select("*", count="exact").order("created_at", desc=True)
        if type in ("hourly", "daily"):
            query = query.eq("report_type", type)
        result = query.range(offset, offset + limit - 1).execute()
        return {
            "reports": result.data or [],
            "total": result.count or 0,
            "limit": limit,
            "offset": offset,
        }
    except Exception as e:
        return {"reports": [], "total": 0, "error": str(e)}


@app.get("/reports/latest/hourly")
async def latest_hourly_report():
    """Get the most recent hourly report."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_reports") \
            .select("*") \
            .eq("report_type", "hourly") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        if result.data:
            return result.data[0]
        return {"error": "No hourly report found"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/reports/latest/daily")
async def latest_daily_report():
    """Get the most recent daily report."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_reports") \
            .select("*") \
            .eq("report_type", "daily") \
            .order("created_at", desc=True) \
            .limit(1) \
            .execute()
        if result.data:
            return result.data[0]
        return {"error": "No daily report found"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a single report by ID."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_reports") \
            .select("*") \
            .eq("id", report_id) \
            .single() \
            .execute()
        return result.data
    except Exception as e:
        return {"error": str(e)}


@app.get("/watchdog")
def watchdog_status():
    """Get watchdog status — all services health. Sync = runs in threadpool."""
    if not _watchdog:
        return {"watchdog_active": False}
    return _watchdog.get_status()


@app.get("/usage")
async def get_usage():
    """Get Claude API token usage and costs."""
    from openclaw.agent.token_tracker import get_token_tracker
    return get_token_tracker().get_summary()


# ===== PORTFOLIO ENDPOINTS =====

@app.get("/portfolio")
async def portfolio_overview():
    """Get full portfolio state: balance, open positions, stats."""
    if not _portfolio:
        return {"error": "Portfolio not initialized"}
    state = _portfolio.get_portfolio_state()
    positions = _portfolio._get_open_positions()
    return {
        "state": state,
        "open_positions": positions,
        "open_count": len(positions),
    }


@app.get("/portfolio/positions")
async def portfolio_positions():
    """Get all open positions."""
    if not _portfolio:
        return {"positions": [], "error": "Portfolio not initialized"}
    return {"positions": _portfolio._get_open_positions()}


@app.get("/portfolio/history")
async def portfolio_history(limit: int = 50):
    """Get closed trades history."""
    if not _portfolio:
        return {"trades": [], "error": "Portfolio not initialized"}
    return {"trades": _portfolio.get_closed_positions(limit)}


@app.post("/portfolio/close/{position_id}")
async def portfolio_close_position(position_id: str):
    """Manually close a position at current market price."""
    if not _portfolio:
        return {"error": "Portfolio not initialized"}

    # Get position to find pair
    try:
        result = _portfolio.sb.table("openclaw_positions") \
            .select("*").eq("id", position_id).eq("status", "OPEN").single().execute()
        pos = result.data
    except Exception as e:
        return {"error": f"Position not found: {e}"}

    if not pos:
        return {"error": "Position not found or already closed"}

    # Get current price
    price = await _portfolio._get_price(pos["pair"])
    if not price:
        return {"error": f"Cannot get price for {pos['pair']}"}

    await _portfolio.close_position(position_id, price, "MANUAL")
    return {"status": "ok", "pair": pos["pair"], "exit_price": price, "reason": "MANUAL"}


@app.post("/portfolio/check")
async def portfolio_force_check():
    """Force an immediate position check."""
    if not _portfolio:
        return {"error": "Portfolio not initialized"}
    try:
        await _portfolio.check_positions()
        return {"status": "ok", "message": "Positions checked"}
    except Exception as e:
        return {"error": str(e)}


# ===== AUDIT ENDPOINTS =====

@app.post("/audit/start")
async def start_audit(body: dict = None):
    """Phase 1: Generate audit report. Body: {"type": "portfolio"} or {"type": "decisions"}."""
    audit_type = (body or {}).get("type", "portfolio")
    from openclaw.audit.analyzer import PortfolioAuditor, DecisionsAuditor
    try:
        analyzer = PortfolioAuditor() if audit_type != "decisions" else DecisionsAuditor()
        result = await analyzer.generate_report()

        # Save to Supabase
        audit_record = {
            "status": "pending_user",
            "name": f"Audit {'Portfolio' if audit_type != 'decisions' else 'Decisions'} — {datetime.now(timezone.utc).strftime('%d/%m %H:%M')}",
            "audit_type": result.get("audit_type", audit_type),
            "report": result["report"],
            "points": result["points"],
            "discussion": [],
            "decisions_summary": None,
            "changes_applied": [],
        }
        try:
            from supabase import create_client as _sc
            settings = get_settings()
            sb = _sc(settings.supabase_url, settings.supabase_service_key)
            insert_result = sb.table("openclaw_audits").insert(audit_record).execute()
            audit_id = insert_result.data[0]["id"] if insert_result.data else None
        except Exception as e:
            # Table might not exist
            print(f"⚠️ openclaw_audits table error: {e}")
            audit_id = None

        return {
            "status": "ok",
            "audit_id": audit_id,
            "report": result["report"],
            "points": result["points"],
            "raw_stats": result.get("raw_stats"),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/audit/{audit_id}/confirm")
async def confirm_audit(audit_id: str, body: dict = None):
    """Phase 2: User confirms (optionally with modified points), start negotiation."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)

        # Get audit record
        result = sb.table("openclaw_audits").select("*").eq("id", audit_id).single().execute()
        audit = result.data
        if not audit:
            return {"error": "Audit not found"}

        if audit["status"] not in ("pending_user", "confirmed"):
            return {"error": f"Audit status is '{audit['status']}', cannot confirm"}

        # If user sent modified points, update them
        user_points = (body or {}).get("points")
        if user_points:
            audit["points"] = user_points

        # Update status + potentially updated points
        update_data = {"status": "negotiating"}
        if user_points:
            update_data["points"] = user_points
        sb.table("openclaw_audits").update(update_data).eq("id", audit_id).execute()

        # Run negotiation in background
        async def _run_negotiation():
            from openclaw.audit.negotiator import AuditNegotiator
            try:
                negotiator = AuditNegotiator(_chat)
                discussions = await negotiator.negotiate_all(audit_id, audit["points"])

                # Build summary
                summary_lines = ["# Resume des Decisions\n"]
                for disc in discussions:
                    pid = disc["point_id"]
                    pt = next((p for p in audit["points"] if p["id"] == pid), {})
                    emoji = {"ACCORD": "✅", "COMPROMIS": "🤝", "DESACCORD": "❌"}.get(disc["decision"], "❓")
                    summary_lines.append(
                        f"{emoji} **Point #{pid}** ({pt.get('title', '?')}): "
                        f"**{disc['decision']}** — {disc.get('decision_reason', '')}"
                    )
                summary = "\n".join(summary_lines)

                sb.table("openclaw_audits").update({
                    "status": "pending_final",
                    "discussion": discussions,
                    "decisions_summary": summary,
                }).eq("id", audit_id).execute()

            except Exception as e:
                print(f"⚠️ Negotiation error: {e}")
                sb.table("openclaw_audits").update({
                    "status": "pending_user",
                    "decisions_summary": f"Erreur negotiation: {str(e)}",
                }).eq("id", audit_id).execute()

        asyncio.create_task(_run_negotiation())

        return {"status": "ok", "message": "Negotiation started in background"}

    except Exception as e:
        return {"error": str(e)}


@app.get("/audit/list")
async def list_audits():
    """List all audits, most recent first."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_audits") \
            .select("id, status, created_at, updated_at") \
            .order("created_at", desc=True) \
            .limit(20) \
            .execute()
        return {"audits": result.data or []}
    except Exception as e:
        return {"audits": [], "error": str(e)}


@app.get("/audit/{audit_id}")
async def get_audit(audit_id: str):
    """Get audit status, report, discussion, decisions."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_audits").select("*").eq("id", audit_id).single().execute()
        return result.data or {"error": "Not found"}
    except Exception as e:
        return {"error": str(e)}


@app.delete("/audit/{audit_id}")
async def delete_audit(audit_id: str):
    """Delete an audit (only if pending_user)."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("openclaw_audits").select("status").eq("id", audit_id).single().execute()
        if not result.data:
            return {"error": "Audit not found"}
        if result.data["status"] == "applied":
            return {"error": "Cannot delete applied audit"}
        sb.table("openclaw_audits").delete().eq("id", audit_id).execute()
        return {"status": "ok", "deleted": True}
    except Exception as e:
        return {"error": str(e)}


@app.patch("/audit/{audit_id}")
async def update_audit(audit_id: str, body: dict = None):
    """Rename an audit or update metadata."""
    try:
        from supabase import create_client as _sc
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)
        updates = {}
        if (body or {}).get("name"):
            updates["name"] = body["name"]
        if not updates:
            return {"error": "Nothing to update"}
        sb.table("openclaw_audits").update(updates).eq("id", audit_id).execute()
        return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/audit/{audit_id}/apply")
async def apply_audit(audit_id: str):
    """Phase 4: Apply agreed decisions."""
    try:
        from supabase import create_client as _sc
        from openclaw.audit.applier import AuditApplier
        settings = get_settings()
        sb = _sc(settings.supabase_url, settings.supabase_service_key)

        # Get audit
        result = sb.table("openclaw_audits").select("*").eq("id", audit_id).single().execute()
        audit = result.data
        if not audit:
            return {"error": "Audit not found"}

        if audit["status"] != "pending_final":
            return {"error": f"Audit status is '{audit['status']}', expected 'pending_final'"}

        # Apply decisions
        applier = AuditApplier()
        changes = applier.apply_decisions(audit["points"], audit["discussion"], audit_id=audit_id)

        # Update audit
        sb.table("openclaw_audits").update({
            "status": "applied",
            "changes_applied": changes,
        }).eq("id", audit_id).execute()

        return {"status": "ok", "changes": changes}

    except Exception as e:
        return {"error": str(e)}


@app.post("/audit/{audit_id}/rollback")
async def rollback_audit(audit_id: str):
    """Rollback all changes made by this audit — restore previous state."""
    try:
        from openclaw.audit.applier import AuditApplier
        applier = AuditApplier()
        result = applier.rollback(audit_id)
        return result
    except Exception as e:
        return {"error": str(e)}


# ===== ENGAGEMENT ENDPOINTS =====

@app.get("/engagements")
async def list_engagements():
    """List all engagements."""
    if not _engagements:
        return {"engagements": [], "error": "Engagement tracker not initialized"}
    return {"engagements": _engagements.get_all()}


@app.get("/engagements/pending")
async def pending_engagements():
    """List pending engagements only."""
    if not _engagements:
        return {"engagements": [], "error": "Engagement tracker not initialized"}
    return {"engagements": _engagements.get_pending()}


@app.post("/engagements/check")
async def force_check_engagements():
    """Force an immediate check of all pending engagements."""
    if not _engagements:
        return {"error": "Engagement tracker not initialized"}
    try:
        results = await _engagements.check_all()
        return {"status": "ok", "results": results}
    except Exception as e:
        return {"error": str(e)}


def main():
    """Run OpenClaw as a standalone service."""
    import uvicorn
    uvicorn.run(
        "openclaw.main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
    )


if __name__ == "__main__":
    main()
