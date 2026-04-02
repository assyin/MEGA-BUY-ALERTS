"""Self-Training Loop — OpenClaw learns from market winners continuously.

Every 30 minutes:
1. Check Binance for pairs that gained >15% in 24h
2. Check if we had a MEGA BUY alert for those pairs
3. If YES → analyze why it worked, extract winning patterns
4. If NO → analyze why we missed it, improve detection
5. Save insights for future analyses

Cost: ~$0.02 per winning pair found (1 Claude call)
      Binance API = free
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import requests

from openclaw.config import get_settings
from openclaw.pipeline.pair_filter import STABLECOIN_BLACKLIST
from openclaw.memory.insights import InsightsStore


BINANCE_API = "https://api.binance.com"


class SelfTrainer:
    """Continuously learns from market winners."""

    def __init__(self, chat_manager, telegram_bot=None, min_gain_pct: float = 15.0,
                 interval_minutes: int = 30):
        self.chat_manager = chat_manager
        self.telegram_bot = telegram_bot
        self.min_gain = min_gain_pct
        self.interval = interval_minutes * 60
        self.insights = InsightsStore()
        self._running = False
        self._task = None
        self._analyzed_ever: set = set()  # Never re-analyze same pair

        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)

        # Preload already-trained pairs from self-training conversations
        try:
            convs = self.chat_manager.list_conversations(limit=100)
            trained_pairs = set()
            for c in convs:
                title = c.get("title", "")
                if "Self-Training" in title or "Training" in title:
                    # Get conversation messages to find analyzed pairs
                    conv = self.chat_manager.get_conversation(c["id"])
                    if conv and conv.get("messages"):
                        for msg in conv["messages"]:
                            content = msg.get("content", "")
                            # Extract pair names from training messages
                            if "TRAINING" in content and "USDT" in content:
                                import re
                                pairs_found = re.findall(r'([A-Z0-9]+USDT)', content)
                                trained_pairs.update(pairs_found)
            self._analyzed_ever = trained_pairs
            print(f"🎓 SelfTrainer: {len(self._analyzed_ever)} pairs already trained from conversations")
        except Exception as e:
            print(f"⚠️ SelfTrainer preload error: {e}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._train_loop())
        print(f"🎓 SelfTrainer started (check every {self.interval//60}min, min gain: +{self.min_gain}%)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _train_loop(self):
        """Main training loop."""
        # Wait 2 min on startup before first check
        await asyncio.sleep(120)

        while self._running:
            try:
                await self._training_cycle()
            except Exception as e:
                print(f"⚠️ SelfTrainer error: {e}")
            await asyncio.sleep(self.interval)

    async def _training_cycle(self):
        """One training cycle: find winners → check our alerts → learn."""
        # 1. Get today's big winners from Binance
        winners = await asyncio.to_thread(self._get_market_winners)
        if not winners:
            return

        print(f"🎓 SelfTrainer: {len(winners)} pairs with >{self.min_gain}% gain")

        # Send summary to Telegram
        if self.telegram_bot and winners:
            summary = f"🎓 *Self-Training*\n\n{len(winners)} paires avec >{self.min_gain}% gain 24h:\n"
            for w in winners[:8]:
                summary += f"  • *{w['symbol']}* +{w['change']:.1f}% (${w['volume_24h']:,.0f})\n"
            summary += f"\nAnalyse en cours..."
            try:
                await self.telegram_bot.app.bot.send_message(
                    chat_id=self.telegram_bot.chat_id, text=summary, parse_mode="Markdown"
                )
            except Exception:
                pass

        # 2. For each winner, check if we had an alert
        for pair_info in winners[:5]:  # Max 5 per cycle to save tokens
            pair = pair_info["symbol"]
            if pair in self._analyzed_ever:
                continue  # Already trained on this pair — skip forever
            self._analyzed_ever.add(pair)

            # Check our alerts
            alert = await asyncio.to_thread(self._find_recent_alert, pair)
            has_alert = alert is not None

            print(f"  🎓 {pair} +{pair_info['change']:.1f}% — {'✅ Alert found' if has_alert else '❌ No alert'}")

            # 3. Send to Claude for analysis via chat
            await self._analyze_and_learn(pair_info, alert)

            # Small delay between analyses
            await asyncio.sleep(10)

    def _get_market_winners(self) -> List[Dict]:
        """Get USDT pairs with >15% gain in 24h from Binance."""
        try:
            r = requests.get(f"{BINANCE_API}/api/v3/ticker/24hr", timeout=15)
            data = r.json()

            winners = []
            for t in data:
                symbol = t.get("symbol", "")
                change = float(t.get("priceChangePercent", 0))
                volume = float(t.get("quoteVolume", 0))

                if (symbol.endswith("USDT")
                    and symbol not in STABLECOIN_BLACKLIST
                    and change >= self.min_gain
                    and volume >= 500_000):
                    winners.append({
                        "symbol": symbol,
                        "change": change,
                        "price": float(t.get("lastPrice", 0)),
                        "volume_24h": volume,
                        "high": float(t.get("highPrice", 0)),
                        "low": float(t.get("lowPrice", 0)),
                    })

            # Sort by gain descending
            winners.sort(key=lambda x: x["change"], reverse=True)
            return winners

        except Exception as e:
            print(f"⚠️ SelfTrainer: Failed to get winners: {e}")
            return []

    def _find_recent_alert(self, pair: str) -> dict:
        """Find the most recent MEGA BUY alert for this pair in last 7 days."""
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            result = self.sb.table("alerts") \
                .select("*") \
                .eq("pair", pair) \
                .gte("alert_timestamp", cutoff) \
                .order("alert_timestamp", desc=True) \
                .limit(1) \
                .execute()

            return result.data[0] if result.data else None
        except Exception:
            return None

    async def _analyze_and_learn(self, pair_info: Dict, alert: dict):
        """Send to Claude for analysis and insight extraction."""
        pair = pair_info["symbol"]
        change = pair_info["change"]
        current_price = pair_info["price"]
        high_24h = pair_info["high"]
        low_24h = pair_info["low"]

        if alert:
            # We HAD an alert — full profit analysis
            score = alert.get("scanner_score", 0)
            tfs = alert.get("timeframes", [])
            pp = alert.get("pp", False)
            ec = alert.get("ec", False)
            di_plus = alert.get("di_plus_4h", "?")
            di_minus = alert.get("di_minus_4h", "?")
            adx = alert.get("adx_4h", "?")
            alert_time = alert.get("alert_timestamp", "?")[:16]
            alert_price = alert.get("price", 0)

            # Calculate profit potential
            profit_current = ((current_price - alert_price) / alert_price * 100) if alert_price else 0
            profit_max = ((high_24h - alert_price) / alert_price * 100) if alert_price else 0
            max_drawdown = ((low_24h - alert_price) / alert_price * 100) if alert_price else 0

            # Get additional alert data
            lazy_values = alert.get("lazy_values", {})
            ec_moves = alert.get("ec_moves", {})
            rsi_moves = alert.get("rsi_moves", {})
            vol_pct = alert.get("vol_pct", {})
            emotion = alert.get("emotion", "?")
            rsi = alert.get("rsi", "?")

            message = (
                f"TRAINING — ANALYSE COMPLETE d'un trade gagnant.\n\n"
                f"🎯 {pair} a fait +{change:.1f}% en 24h\n\n"
                f"📊 POTENTIEL DE PROFIT SI ON AVAIT TRADE L'ALERTE:\n"
                f"- Prix alerte: {alert_price}\n"
                f"- Prix actuel: {current_price}\n"
                f"- Profit si entree au prix alerte: {profit_current:+.1f}%\n"
                f"- Profit MAX (high 24h = {high_24h}): {profit_max:+.1f}%\n"
                f"- Drawdown MAX (low 24h = {low_24h}): {max_drawdown:+.1f}%\n"
                f"- R:R realisé: 1:{abs(profit_max/max_drawdown):.1f}\n" if max_drawdown < 0 else
                f"TRAINING — ANALYSE COMPLETE d'un trade gagnant.\n\n"
                f"🎯 {pair} a fait +{change:.1f}% en 24h\n\n"
                f"📊 POTENTIEL DE PROFIT SI ON AVAIT TRADE L'ALERTE:\n"
                f"- Prix alerte: {alert_price}\n"
                f"- Prix actuel: {current_price}\n"
                f"- Profit si entree au prix alerte: {profit_current:+.1f}%\n"
                f"- Profit MAX (high 24h = {high_24h}): {profit_max:+.1f}%\n"
                f"- Drawdown MAX (low 24h = {low_24h}): {max_drawdown:+.1f}%\n"
            )
            message += (
                f"\n📋 DONNEES DE L'ALERTE MEGA BUY:\n"
                f"- Score: {score}/10\n"
                f"- Timeframes: {', '.join(tfs)}\n"
                f"- PP={pp}, EC={ec}\n"
                f"- DI+ 4H={di_plus}, DI- 4H={di_minus}, ADX 4H={adx}\n"
                f"- RSI={rsi}\n"
                f"- Alert time: {alert_time}\n"
                f"- Emotion: {emotion}\n"
                f"- LazyBar: {lazy_values}\n"
                f"- EC moves: {ec_moves}\n"
                f"- RSI moves: {rsi_moves}\n"
                f"- Volume %: {vol_pct}\n\n"
                f"🔍 ANALYSE DEMANDEE:\n"
                f"1. Appelle analyze_alert avec pair={pair}, timestamp={alert.get('alert_timestamp','')}, price={alert_price} pour voir les 197 indicateurs AU MOMENT de l'alerte\n"
                f"2. Identifie les indicateurs CLE qui ont rendu ce trade gagnant (+{profit_max:.1f}% max)\n"
                f"3. Compare avec nos insights existants — est-ce un nouveau pattern ou un pattern deja connu?\n"
                f"4. Si nouveau pattern: sauvegarde un insight ACTIONNABLE\n"
                f"5. Si pattern connu: renforce le avec les nouvelles donnees\n"
                f"6. Identifie si le SL a 5% aurait tenu (drawdown max = {max_drawdown:+.1f}%)\n"
                f"7. Quel aurait ete le TP optimal?\n"
            )
        else:
            # We MISSED this winner — deep analysis of why
            message = (
                f"TRAINING — TRADE RATE qu'on a PAS detecte.\n\n"
                f"🎯 {pair} a fait +{change:.1f}% en 24h mais AUCUNE alerte MEGA BUY.\n\n"
                f"📊 DONNEES MARCHE:\n"
                f"- Gain 24h: +{change:.1f}%\n"
                f"- Prix actuel: {current_price}\n"
                f"- High 24h: {high_24h}\n"
                f"- Low 24h: {low_24h}\n"
                f"- Volume 24h: ${pair_info['volume_24h']:,.0f}\n"
                f"- Amplitude: {((high_24h - low_24h) / low_24h * 100):.1f}%\n\n"
                f"🔍 ANALYSE DEMANDEE:\n"
                f"1. Appelle analyze_alert avec pair={pair} (sans timestamp = donnees actuelles) pour voir l'etat technique actuel\n"
                f"2. Pourquoi notre scanner n'a PAS detecte ce mouvement? Quelles conditions manquaient?\n"
                f"3. Est-ce que les conditions MEGA BUY etaient presentes AVANT le pump?\n"
                f"4. Comment ameliorer la detection pour capter ce type de mouvement?\n"
                f"5. Sauvegarde les insights pour ne plus rater ce type de trade\n"
                f"6. Est-ce un pump artificiel (volume anormal, manipulation) ou un mouvement organique?\n"
            )

        # Step 1: Run real analysis with 197 indicators (same as alert analysis)
        analysis_data = {}
        try:
            import sys
            sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent.parent / "backtest"))
            from api.realtime_analyze import analyze_alert_realtime
            ts = alert.get("alert_timestamp", "") if alert else ""
            price = alert.get("price", 0) if alert else 0
            analysis_data = await asyncio.to_thread(analyze_alert_realtime, pair, ts, price)
        except Exception as e:
            print(f"  ⚠️ {pair} analysis failed: {e}")

        # Step 2: Extract key insights DIRECTLY (no LLM needed — save tokens)
        insights_extracted = []
        if alert and analysis_data and "error" not in analysis_data:
            # Check STC pattern
            prereqs = analysis_data.get("prerequisites", {})
            stc = prereqs.get("stc_oversold", {})
            stc_valid_tfs = stc.get("valid_tfs", [])
            ec_data = analysis_data.get("entry_conditions", {})
            cond_count = ec_data.get("count", 0)

            alert_price = alert.get("price", 0)
            profit_max = ((high_24h - alert_price) / alert_price * 100) if alert_price else 0
            max_dd = ((low_24h - alert_price) / alert_price * 100) if alert_price else 0

            # Extract GENERAL insights only (no per-pair noise)
            # These are saved only if they represent a NEW pattern not already covered
            score = alert.get("scanner_score", 0)

            # Only save if it reveals something NEW about the system
            # Don't save per-pair "XXXUSDT a produit +X%" — that's noise
            if len(stc_valid_tfs) >= 3 and profit_max > 50:
                # Only for exceptional STC triple zero trades (>50%)
                insights_extracted.append({
                    "insight": f"STC triple zero (3+ TF) confirme a nouveau avec +{profit_max:.0f}% gain. Statistique renforcee: STC multi-TF = signal le plus fiable du systeme.",
                    "category": "pattern", "priority": 9
                })

            if score >= 10 and profit_max > 20:
                # Only for perfect score with big gains
                insights_extracted.append({
                    "insight": f"Score 10/10 confirme a nouveau avec +{profit_max:.0f}% gain. Score parfait = toujours BUY STRONG.",
                    "category": "strategy", "priority": 9
                })

        # Step 3: Save insights directly (fast, no LLM cost)
        for ins in insights_extracted:
            self.insights.add_insight(ins["insight"], ins["category"], priority=ins["priority"])
            print(f"  💡 Insight saved: {ins['insight'][:80]}...")

        # Step 4: Create training conversation for full analysis
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            conv_title = f"Self-Training {today}"

            convs = self.chat_manager.list_conversations(limit=5)
            conv_id = None
            for c in convs:
                if c.get("title") == conv_title:
                    conv_id = c["id"]
                    break

            if not conv_id:
                conv_id = self.chat_manager.create_conversation(conv_title)

            if conv_id:
                response = await self.chat_manager.send_message(conv_id, message)
                print(f"  🎓 {pair}: trained ({'alert found' if alert else 'missed'})")

                # Send result to Telegram — FULL analysis, not truncated
                if self.telegram_bot and response:
                    if alert:
                        alert_price = alert.get("price", 0)
                        profit_current = ((current_price - alert_price) / alert_price * 100) if alert_price else 0
                        profit_max = ((high_24h - alert_price) / alert_price * 100) if alert_price else 0
                        max_dd = ((low_24h - alert_price) / alert_price * 100) if alert_price else 0
                        tg_msg = (
                            f"🎓 *Training: {pair}* +{change:.1f}%\n"
                            f"✅ Alert trouvee (Score {alert.get('scanner_score')}/10)\n\n"
                            f"💰 *Profit potentiel:*\n"
                            f"• Entry: {alert_price} → Now: {current_price}\n"
                            f"• Profit actuel: *{profit_current:+.1f}%*\n"
                            f"• Profit MAX: *{profit_max:+.1f}%* (high: {high_24h})\n"
                            f"• Drawdown MAX: {max_dd:+.1f}% (low: {low_24h})\n"
                            f"• SL 5%: {'TENU ✅' if max_dd > -5 else 'TOUCHE ❌'}\n"
                        )
                        if insights_extracted:
                            tg_msg += f"\n💡 *{len(insights_extracted)} insight(s) appris:*\n"
                            for ins in insights_extracted[:3]:
                                tg_msg += f"• {ins['insight'][:120]}\n"
                        tg_msg += f"\n🧠 *Analyse:*\n{response[:1500]}"
                    else:
                        tg_msg = (
                            f"🎓 *Training: {pair}* +{change:.1f}%\n"
                            f"❌ Alert MANQUEE\n\n"
                            f"📊 High: {high_24h} | Low: {low_24h}\n"
                            f"Vol: ${pair_info['volume_24h']:,.0f}\n\n"
                            f"🧠 *Pourquoi rate:*\n{response[:1500]}"
                        )
                    try:
                        await self.telegram_bot.app.bot.send_message(
                            chat_id=self.telegram_bot.chat_id, text=tg_msg[:3900], parse_mode="Markdown"
                        )
                    except Exception:
                        try:
                            await self.telegram_bot.app.bot.send_message(
                                chat_id=self.telegram_bot.chat_id, text=tg_msg[:3900]
                            )
                        except Exception:
                            pass
            else:
                print(f"  ⚠️ {pair}: could not create training conversation")

        except Exception as e:
            print(f"  ⚠️ {pair} training error: {e}")

    def get_status(self) -> dict:
        """Get self-trainer status."""
        return {
            "running": self._running,
            "interval_minutes": self.interval // 60,
            "min_gain_pct": self.min_gain,
            "total_trained": len(self._analyzed_ever),
            "recent_pairs": list(self._analyzed_ever)[-10:],
        }
