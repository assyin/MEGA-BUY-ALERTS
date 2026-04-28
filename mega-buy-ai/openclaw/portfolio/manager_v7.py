"""Portfolio Manager V7 — OPTIMIZED FILTER + Hybrid Trailing TP.

Strategy: capture moonshots while securing profits.
- Filter: same as V6 (gate_v6.passes_optimized_gate)
- Capital: $5000 | Slots: 12 | Size: 8% per trade ($400)
- TP1 = 50% closed @ +10% (lock half profit)
- TP2 = 30% closed @ +20% (extend gains)
- 20% remaining = TRAILING infini (catch +50%/+100%/+1000% moonshots)
- After TP1 hit → SL moves to BREAKEVEN
- SL: -8% initial | TIMEOUT: 72h (longer to let runners breathe)

Position state (additional fields):
- partial1_done (bool)
- partial2_done (bool)
- trail_active (bool)
- trail_stop (float)
- realized_pnl_usd (float, partial profits already booked)
- remaining_size_pct (float, fraction of original size still open)
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from openclaw.config import get_settings
from openclaw.portfolio.gate_v6 import passes_optimized_gate


class PortfolioManagerV7:

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 12
    MAX_PER_PAIR = 1
    SIZE_PCT = 8.0

    SL_PCT = 8.0                # Initial stop loss
    TP1_PCT = 10.0              # Lock profit threshold
    TP1_CLOSE_FRAC = 0.50       # Close 50% of position
    TP2_PCT = 20.0              # Extended TP
    TP2_CLOSE_FRAC = 0.30       # Close 30% (cumulative 80%)
    TRAIL_DIST_PCT = 8.0        # Trailing stop distance after TP2
    TIMEOUT_H = 72              # Longer hold for runners

    TABLE = "openclaw_positions_v7"
    STATE_TABLE = "openclaw_portfolio_state_v7"

    def __init__(self, telegram_bot=None):
        self.settings = get_settings()
        self.telegram_bot = telegram_bot
        self._running = False
        self._task = None

        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        self._ensure_state()

    def _ensure_state(self):
        try:
            r = self.sb.table(self.STATE_TABLE).select("id").eq("id", "main").execute()
            if not r.data:
                self.sb.table(self.STATE_TABLE).insert({
                    "id": "main", "balance": self.INITIAL_CAPITAL,
                    "initial_capital": self.INITIAL_CAPITAL,
                    "total_pnl": 0, "total_trades": 0, "wins": 0, "losses": 0,
                    "max_drawdown_pct": 0, "peak_balance": self.INITIAL_CAPITAL,
                }).execute()
        except Exception as e:
            print(f"⚠️ V7 state init: {e}")

    def get_portfolio_state(self) -> Dict:
        try:
            return self.sb.table(self.STATE_TABLE).select("*").eq("id", "main").single().execute().data or {}
        except:
            return {}

    def _update_state(self, updates: Dict):
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.sb.table(self.STATE_TABLE).update(updates).eq("id", "main").execute()
        except:
            pass

    def _get_open_positions(self) -> List[Dict]:
        try:
            return self.sb.table(self.TABLE).select("*").eq("status", "OPEN").execute().data or []
        except:
            return []

    async def _get_price(self, pair: str) -> float:
        def _sync():
            try:
                return float(requests.get("https://api.binance.com/api/v3/ticker/price",
                    params={"symbol": pair}, timeout=5).json().get("price", 0))
            except:
                return 0
        return await asyncio.to_thread(_sync)

    async def _tg(self, text: str):
        """Send a Telegram notification (silent fail)."""
        if not self.telegram_bot:
            return
        try:
            await self.telegram_bot.app.bot.send_message(
                chat_id=self.telegram_bot.chat_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await self.telegram_bot.app.bot.send_message(
                    chat_id=self.telegram_bot.chat_id, text=text
                )
            except Exception:
                pass

    # ==================================================================
    # OPEN POSITION
    # ==================================================================

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 alert: Dict, vip: Optional[Dict] = None,
                                 quality: Optional[Dict] = None) -> Optional[Dict]:
        if "BUY" not in decision:
            return None

        passed, reason = passes_optimized_gate(pair, alert, label="V7", cache=alert.get("_gate_cache"))
        if not passed:
            print(f"💼 V7 GATE REJECT {pair}: {reason}")
            return None

        try:
            from openclaw.pipeline.pair_filter import is_tradable
            if not is_tradable(pair):
                return None
        except:
            pass

        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        if balance < 50:
            return None

        open_positions = self._get_open_positions()
        if len(open_positions) >= self.MAX_POSITIONS:
            print(f"💼 V7 SKIP {pair}: portfolio full ({self.MAX_POSITIONS}/{self.MAX_POSITIONS})")
            return None

        if any(p.get("pair") == pair for p in open_positions):
            return None

        size_usd = round(self.INITIAL_CAPITAL * self.SIZE_PCT / 100, 2)
        if balance < size_usd:
            return None

        price = alert.get("price", 0) or 0
        if not price:
            price = await self._get_price(pair)
        if not price:
            return None

        sl = round(price * (1 - self.SL_PCT / 100), 8)
        tp1 = round(price * (1 + self.TP1_PCT / 100), 8)
        tp2 = round(price * (1 + self.TP2_PCT / 100), 8)

        position = {
            "id": str(uuid.uuid4()), "pair": pair,
            "entry_price": price, "current_price": price,
            "size_usd": size_usd,
            "sl_price": sl,
            "tp1_price": tp1,
            "tp2_price": tp2,
            "pnl_pct": 0.0, "pnl_usd": 0.0, "highest_price": price,
            "status": "OPEN", "close_reason": None, "exit_price": None,
            "decision": decision, "confidence": confidence,
            "alert_id": alert.get("id", ""),
            "scanner_score": alert.get("scanner_score", 0),
            "is_vip": (vip or {}).get("is_vip", False),
            "is_high_ticket": (vip or {}).get("is_high_ticket", False),
            "quality_grade": (quality or {}).get("grade", ""),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,

            # Hybrid trailing state
            "partial1_done": False,
            "partial2_done": False,
            "trail_active": False,
            "trail_stop": sl,
            "realized_pnl_usd": 0.0,
            "remaining_size_pct": 1.0,
        }

        try:
            self.sb.table(self.TABLE).insert(position).execute()
        except Exception as e:
            print(f"⚠️ V7 insert: {e}")
            return None

        self._update_state({"balance": round(balance - size_usd, 2)})
        print(f"💼 V7 OPENED: {pair} — {confidence*100:.0f}% — ${size_usd:.0f} @ {price} | TP1={tp1} TP2={tp2} SL={sl}")

        # Telegram notification
        score = alert.get("scanner_score", 0)
        vip_badge = "🏆" if (vip or {}).get("is_high_ticket") else ("⭐" if (vip or {}).get("is_vip") else "")
        grade = (quality or {}).get("grade", "")
        await self._tg(
            f"🟣 *V7 OPEN* — `{pair}` {vip_badge}\n"
            f"💰 Size: *${size_usd:.0f}* (8% × $5K)\n"
            f"📍 Entry: `{price}`\n"
            f"🎯 TP1: `{tp1}` (+10% · ferme 50%)\n"
            f"🎯 TP2: `{tp2}` (+20% · ferme 30%)\n"
            f"🔄 Trail: 8% sur les 20% restants\n"
            f"🛡 SL: `{sl}` (-8%)\n"
            f"⏱ Timeout: 72h\n"
            f"📊 Score: {score}/10 | Grade: {grade or '—'} | Conf: {confidence*100:.0f}%"
        )
        return position

    # ==================================================================
    # CHECK POSITIONS — Hybrid logic
    # ==================================================================

    async def check_positions(self):
        positions = self._get_open_positions()
        if not positions:
            return

        now = datetime.now(timezone.utc)
        checked = closed = updated = 0

        for pos in positions:
            pair = pos.get("pair", "")
            if not pair:
                continue
            price = await self._get_price(pair)
            if not price:
                continue
            entry = pos.get("entry_price", 0)
            if not entry:
                continue

            highest = max(pos.get("highest_price", price), price)
            size_usd = pos.get("size_usd", 0)

            partial1 = pos.get("partial1_done", False)
            partial2 = pos.get("partial2_done", False)
            trail_active = pos.get("trail_active", False)
            trail_stop = pos.get("trail_stop", pos.get("sl_price", 0))
            realized = pos.get("realized_pnl_usd", 0.0)
            remaining_pct = pos.get("remaining_size_pct", 1.0)

            updates: Dict = {}

            # === STOP CHECK ===
            # Stop = SL initial (avant TP1) OU breakeven (après TP1) OU trailing (après TP2)
            stop_price = trail_stop
            if price <= stop_price:
                # Close remaining position
                exit_pct = (stop_price - entry) / entry * 100
                exit_usd = size_usd * remaining_pct * exit_pct / 100
                final_realized = realized + exit_usd

                reason = "TRAIL_STOP" if trail_active else ("BREAKEVEN_STOP" if partial1 else "SL_HIT")
                await self._close_full(pos, stop_price, reason, final_realized, remaining_pct)
                closed += 1
                continue

            # === TP1 = 50% @ +10% ===
            tp1 = pos.get("tp1_price", 0)
            if not partial1 and tp1 and price >= tp1:
                # Close TP1_CLOSE_FRAC of position
                profit_pct = self.TP1_PCT
                profit_usd = size_usd * self.TP1_CLOSE_FRAC * profit_pct / 100
                realized += profit_usd
                remaining_pct -= self.TP1_CLOSE_FRAC
                partial1 = True

                # Move stop to breakeven (entry price)
                trail_stop = entry

                # Refund partial capital + profit immediately + track PnL
                state = self.get_portfolio_state()
                bal = state.get("balance", 0) + (size_usd * self.TP1_CLOSE_FRAC) + profit_usd
                tp_total = state.get("total_pnl", 0) + profit_usd
                self._update_state({"balance": round(bal, 2), "total_pnl": round(tp_total, 2)})

                print(f"💼 V7 TP1 ✅: {pos['pair']} closed 50% @ +{self.TP1_PCT}% (${profit_usd:+.1f}) — SL→BE")

                await self._tg(
                    f"🎯 *V7 TP1* — `{pos['pair']}`\n"
                    f"✅ Vendu *50%* @ *+{self.TP1_PCT}%*\n"
                    f"💰 Profit locké: *+${profit_usd:.2f}*\n"
                    f"🛡 SL déplacé à BREAKEVEN (`{entry}`)\n"
                    f"📦 Reste: 50% en course"
                )

                updates.update({
                    "partial1_done": True,
                    "trail_stop": trail_stop,
                    "realized_pnl_usd": round(realized, 2),
                    "remaining_size_pct": round(remaining_pct, 4),
                })

            # === TP2 = 30% @ +20% ===
            tp2 = pos.get("tp2_price", 0)
            if partial1 and not partial2 and tp2 and price >= tp2:
                profit_pct = self.TP2_PCT
                profit_usd = size_usd * self.TP2_CLOSE_FRAC * profit_pct / 100
                realized += profit_usd
                remaining_pct -= self.TP2_CLOSE_FRAC
                partial2 = True
                trail_active = True

                # Activate trailing at distance TRAIL_DIST_PCT from current high
                trail_stop = round(highest * (1 - self.TRAIL_DIST_PCT / 100), 8)

                state = self.get_portfolio_state()
                bal = state.get("balance", 0) + (size_usd * self.TP2_CLOSE_FRAC) + profit_usd
                tp_total = state.get("total_pnl", 0) + profit_usd
                self._update_state({"balance": round(bal, 2), "total_pnl": round(tp_total, 2)})

                print(f"💼 V7 TP2 ✅✅: {pos['pair']} closed 30% @ +{self.TP2_PCT}% (${profit_usd:+.1f}) — Trailing 8% activé sur 20% restants")

                await self._tg(
                    f"🎯🎯 *V7 TP2* — `{pos['pair']}`\n"
                    f"✅ Vendu *30%* @ *+{self.TP2_PCT}%*\n"
                    f"💰 Profit additionnel: *+${profit_usd:.2f}*\n"
                    f"💎 Total réalisé: *+${realized:.2f}*\n"
                    f"🔄 *TRAILING 8%* activé sur les 20% restants\n"
                    f"🚀 Mode chasse au moonshot ON"
                )

                updates.update({
                    "partial2_done": True,
                    "trail_active": True,
                    "trail_stop": trail_stop,
                    "realized_pnl_usd": round(realized, 2),
                    "remaining_size_pct": round(remaining_pct, 4),
                })

            # === Update trailing stop (after TP2 only) ===
            if trail_active:
                new_trail = round(highest * (1 - self.TRAIL_DIST_PCT / 100), 8)
                if new_trail > trail_stop:
                    trail_stop = new_trail
                    updates["trail_stop"] = trail_stop

            # === Timeout 72h ===
            try:
                open_dt = datetime.fromisoformat(pos.get("opened_at", "").replace("Z", "+00:00"))
                age_h = (now - open_dt).total_seconds() / 3600
                if age_h >= self.TIMEOUT_H:
                    exit_pct = (price - entry) / entry * 100
                    exit_usd = size_usd * remaining_pct * exit_pct / 100
                    final_realized = realized + exit_usd
                    await self._close_full(pos, price, "TIMEOUT_72H", final_realized, remaining_pct)
                    closed += 1
                    continue
            except:
                pass

            # Live update
            pnl_pct_total = (price - entry) / entry * 100
            pnl_usd_unrealized = size_usd * remaining_pct * pnl_pct_total / 100
            pnl_usd_total = realized + pnl_usd_unrealized

            updates.update({
                "current_price": price,
                "pnl_pct": round(pnl_pct_total, 2),
                "pnl_usd": round(pnl_usd_total, 2),
                "highest_price": highest,
            })
            try:
                self.sb.table(self.TABLE).update(updates).eq("id", pos["id"]).execute()
                checked += 1
            except:
                pass
            time.sleep(0.05)

        if checked or closed:
            print(f"💼 V7 check: {checked} updated, {closed} closed ({len(positions)} open)")

    async def _close_full(self, pos: Dict, exit_price: float, reason: str,
                          total_realized_pnl: float, remaining_pct: float):
        """Close remaining portion + finalize position with cumulative PnL."""
        entry = pos.get("entry_price", 0)
        size = pos.get("size_usd", 0)
        pnl_pct_position = (total_realized_pnl / size * 100) if size else 0
        is_win = total_realized_pnl > 0

        try:
            self.sb.table(self.TABLE).update({
                "status": "CLOSED", "exit_price": exit_price, "current_price": exit_price,
                "close_reason": reason,
                "pnl_pct": round(pnl_pct_position, 2),
                "pnl_usd": round(total_realized_pnl, 2),
                "realized_pnl_usd": round(total_realized_pnl, 2),
                "remaining_size_pct": 0,
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", pos["id"]).execute()
        except:
            return

        # Refund remaining capital + last leg PnL
        state = self.get_portfolio_state()
        # Compute last leg
        prev_realized = pos.get("realized_pnl_usd", 0.0)
        last_leg_pnl = total_realized_pnl - prev_realized
        bal = state.get("balance", 0) + (size * remaining_pct) + last_leg_pnl

        tp = state.get("total_pnl", 0) + last_leg_pnl  # only delta vs already-booked
        tt = state.get("total_trades", 0) + 1
        w = state.get("wins", 0) + (1 if is_win else 0)
        l = state.get("losses", 0) + (0 if is_win else 1)
        # Drawdown based on total_pnl curve (not balance)
        peak_pnl = max(state.get("peak_balance", 0), tp)
        dd = (peak_pnl - tp) / self.INITIAL_CAPITAL * 100 if self.INITIAL_CAPITAL > 0 else 0

        self._update_state({
            "balance": round(bal, 2),
            "total_pnl": round(tp, 2),
            "total_trades": tt, "wins": w, "losses": l,
            "peak_balance": round(peak_pnl, 2),
            "max_drawdown_pct": round(max(state.get("max_drawdown_pct", 0), dd), 2),
        })
        print(f"💼 V7 {'✅' if is_win else '❌'}: {pos['pair']} {pnl_pct_position:+.1f}% (${total_realized_pnl:+.1f}) — {reason}")

        # Telegram notification — final close
        emoji_map = {
            "TRAIL_STOP": "🔄✅",
            "BREAKEVEN_STOP": "🟰",
            "SL_HIT": "❌",
            "TIMEOUT_72H": "⏰",
        }
        emoji = emoji_map.get(reason, "🔔")
        wr_pct = (w / tt * 100) if tt else 0
        await self._tg(
            f"{emoji} *V7 CLOSE FULL* — `{pos['pair']}` — *{reason}*\n"
            f"💰 PnL TOTAL: *{pnl_pct_position:+.2f}%* (*${total_realized_pnl:+.2f}*)\n"
            f"📍 Entry: `{entry}` → Exit: `{exit_price}`\n"
            f"📊 Balance V7: *${bal:.0f}* | WR: *{wr_pct:.1f}%* ({w}W/{l}L)"
        )

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print(f"💼 V7 Portfolio started — Body≥3% + Hybrid Trailing | 12 slots × 8% × $5000 | TP1=50%@+10% TP2=30%@+20% Trail=8%")

    async def _check_loop(self):
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ V7: {e}")
            await asyncio.sleep(60)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        print("💼 V7 stopped")
