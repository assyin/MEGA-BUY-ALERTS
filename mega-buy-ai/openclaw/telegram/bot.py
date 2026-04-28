"""Telegram bot for OpenClaw — async with inline buttons."""

import asyncio
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from openclaw.config import get_settings
from openclaw.telegram.formatters import (
    format_recommendation, format_portfolio, format_status, format_alert_notification
)
from openclaw.agent.tool_handlers import set_telegram_sender


class OpenClawBot:
    """Telegram bot with inline buttons and conversational mode."""

    def __init__(self, agent, circuit_breaker, memory):
        self.settings = get_settings()
        self.agent = agent
        self.circuit_breaker = circuit_breaker
        self.memory = memory
        self.app: Optional[Application] = None
        self.chat_id = self.settings.telegram_chat_id
        # Comma-separated list of destinations (DM id, group id, channel id…)
        self.chat_ids = [c.strip() for c in str(self.chat_id).split(",") if c.strip()]

    async def start(self):
        """Start the Telegram bot in polling mode."""
        token = self.settings.telegram_token
        if not token:
            print("⚠️ Telegram token not configured")
            return

        self.app = Application.builder().token(token).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("portfolio", self._cmd_portfolio))
        self.app.add_handler(CommandHandler("analyze", self._cmd_analyze))
        self.app.add_handler(CommandHandler("history", self._cmd_history))
        self.app.add_handler(CommandHandler("watchdog", self._cmd_watchdog))
        self.app.add_handler(CallbackQueryHandler(self._callback_handler))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._free_text))

        # Wire the send function for tool_handlers
        set_telegram_sender(self._send_recommendation)

        # Start polling
        # Init in background — don't block openclaw startup if Telegram is unreachable
        async def _init_with_retry():
            retry = 0
            while True:
                try:
                    await self.app.initialize()
                    await self.app.start()
                    await self.app.updater.start_polling(drop_pending_updates=True)
                    print(f"🤖 Telegram bot started (chat_id: {self.chat_id})")
                    return
                except Exception as e:
                    retry += 1
                    wait = min(120, 10 * retry)
                    print(f"⚠️ Telegram bot init failed (attempt {retry}): {type(e).__name__}. Retry in {wait}s.")
                    await asyncio.sleep(wait)
        asyncio.create_task(_init_with_retry())
        print(f"🤖 Telegram bot init scheduled in background (chat_id: {self.chat_id})")

    async def stop(self):
        """Stop the bot."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    # === SEND METHODS ===

    async def send_alert_notification(self, alert: dict):
        """Send initial alert notification (before analysis) to every configured chat_id."""
        text = format_alert_notification(alert)
        for cid in self.chat_ids:
            try:
                await self.app.bot.send_message(
                    chat_id=cid, text=text, parse_mode="Markdown"
                )
            except Exception as e:
                print(f"⚠️ Telegram alert to {cid} failed: {type(e).__name__}: {e}")

    async def _send_recommendation(self, message: str, decision: str = "WATCH", alert_id: str = ""):
        """Send recommendation to every configured chat_id. Strips inline buttons for channels/supergroups."""
        def _build_markup():
            buttons = []
            if decision == "BUY":
                buttons = [
                    [InlineKeyboardButton("✅ Confirm Trade", callback_data=f"confirm:{alert_id}"),
                     InlineKeyboardButton("👀 Watch", callback_data=f"watch:{alert_id}")],
                    [InlineKeyboardButton("❌ Skip", callback_data=f"skip:{alert_id}"),
                     InlineKeyboardButton("📊 Details", callback_data=f"details:{alert_id}")],
                ]
            elif decision == "WATCH":
                buttons = [
                    [InlineKeyboardButton("👀 Watching", callback_data=f"watch:{alert_id}"),
                     InlineKeyboardButton("❌ Skip", callback_data=f"skip:{alert_id}")],
                ]
            else:
                buttons = [
                    [InlineKeyboardButton("✅ OK", callback_data=f"skip:{alert_id}")],
                ]
            return InlineKeyboardMarkup(buttons) if buttons else None

        for cid in self.chat_ids:
            # Channels / supergroups (id starts with -100) don't support inline buttons
            is_channel = str(cid).startswith('-100')
            markup = None if is_channel else _build_markup()
            try:
                await self.app.bot.send_message(
                    chat_id=cid, text=message,
                    parse_mode="Markdown", reply_markup=markup
                )
            except Exception as e:
                # Fallback without Markdown if parsing fails
                try:
                    await self.app.bot.send_message(
                        chat_id=cid, text=message, reply_markup=markup
                    )
                except Exception as e2:
                    print(f"⚠️ Telegram rec to {cid} failed: {type(e2).__name__}: {e2}")

    # === COMMAND HANDLERS ===

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "🤖 *OpenClaw Trading Assistant*\n\n"
            "Je suis votre analyste IA pour MEGA BUY.\n"
            "Commandes: /status /portfolio /analyze /history /help",
            parse_mode="Markdown"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "📋 *Commandes OpenClaw*\n\n"
            "/status — Stats agent + circuit breaker\n"
            "/portfolio — Positions simulation\n"
            "/analyze PAIR — Analyse manuelle (ex: /analyze BTCUSDT)\n"
            "/history PAIR — Historique backtest\n"
            "/help — Cette aide\n\n"
            "💬 Ou ecrivez une question en texte libre!",
            parse_mode="Markdown"
        )

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        cb_status = self.circuit_breaker.get_status()
        mem_stats = self.memory.get_stats()
        text = format_status(cb_status, mem_stats)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        from openclaw.agent.tool_handlers import handle_get_portfolio_status
        data = await handle_get_portfolio_status()
        text = format_portfolio(data)
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /analyze BTCUSDT")
            return

        pair = args[0].upper()
        if not pair.endswith("USDT"):
            pair += "USDT"

        await update.message.reply_text(f"🔍 Analyse de {pair} en cours...")

        # Create a fake alert for analysis
        alert = {
            "id": "", "pair": pair, "price": 0, "scanner_score": 0,
            "timeframes": [], "alert_timestamp": "",
            "rsi_check": False, "dmi_check": False, "ast_check": False,
            "choch": False, "zone": False, "lazy": False,
            "vol": False, "st": False, "pp": False, "ec": False,
        }

        try:
            decision = await self.agent.analyze_alert(alert)
            await self._send_recommendation(decision.raw_response, decision.decision, "")
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {e}")

    async def _cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.message.reply_text("Usage: /history BTCUSDT")
            return

        pair = args[0].upper()
        if not pair.endswith("USDT"):
            pair += "USDT"

        from openclaw.agent.tool_handlers import handle_get_backtest_history
        data = await handle_get_backtest_history(pair)

        if data.get("total_trades", 0) == 0:
            await update.message.reply_text(f"Aucun backtest pour {pair}")
            return

        text = (
            f"📊 *Backtest {pair}*\n\n"
            f"Trades: {data['total_trades']}\n"
            f"Win Rate: {data['win_rate_pct']}%\n"
            f"Avg P&L (C): {data['avg_pnl_c']:+.1f}%\n"
            f"Best: {data['best_trade_pnl']:+.1f}%\n"
            f"Worst: {data['worst_trade_pnl']:+.1f}%"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_watchdog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            import requests as req
            r = req.get("http://localhost:8002/watchdog", timeout=5)
            data = r.json()
            services = data.get("services", {})
            events = data.get("recent_events", [])

            lines = ["🐕 *Watchdog Status*\n"]
            for svc_id, svc in services.items():
                emoji = "✅" if svc.get("alive") else "❌"
                restarts = svc.get("restarts", 0)
                name = svc.get("name", svc_id)
                port = f" :{svc['port']}" if svc.get("port") else ""
                restart_txt = f" ({restarts} restarts)" if restarts > 0 else ""
                lines.append(f"{emoji} {name}{port}{restart_txt}")

            if events:
                lines.append("\n📋 *Recent events:*")
                for e in events[-5:]:
                    lines.append(f"  {e['timestamp'][:16]} | {e['service']} {e['action']}")

            await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Watchdog error: {e}")

    # === CALLBACK HANDLER (inline buttons) ===

    async def _callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        data = query.data
        action, _, alert_id = data.partition(":")

        if action == "confirm":
            await query.edit_message_text(
                query.message.text + "\n\n✅ *Trade confirme!*", parse_mode="Markdown"
            )
        elif action == "watch":
            await query.edit_message_text(
                query.message.text + "\n\n👀 *En surveillance*", parse_mode="Markdown"
            )
        elif action == "skip":
            await query.edit_message_text(
                query.message.text + "\n\n❌ *Skippe*", parse_mode="Markdown"
            )
        elif action == "details":
            await query.message.reply_text(f"📊 Details complets sur le dashboard:\nhttp://localhost:9000/alerts")

    # === FREE TEXT (conversational) ===

    async def _free_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Ignore channel posts / edits / non-text messages — only respond to direct user messages
        if update.message is None or update.message.text is None:
            return
        question = update.message.text
        await update.message.reply_text("🤔 Reflexion en cours...")

        try:
            answer = await self.agent.answer_question(question)
            # Truncate for Telegram (4096 char limit)
            if len(answer) > 4000:
                answer = answer[:4000] + "..."
            await update.message.reply_text(answer)
        except Exception as e:
            await update.message.reply_text(f"❌ Erreur: {e}")
