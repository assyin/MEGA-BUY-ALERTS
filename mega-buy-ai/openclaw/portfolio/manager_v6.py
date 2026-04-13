"""Portfolio Manager V6 — OPTIMIZED FILTER + Fixed TP +15%.

Strategy based on 7d backtest analysis:
- Filter: Body 4H >= 3% + baseline (gate_v6.passes_optimized_gate)
- Capital: $5000 | Slots: 12 | Size: 8% per trade ($400)
- TP: +15% (FIXED) | SL: -8% | TIMEOUT: 48h

Backtest expectation:
- ~5 alerts/day matching, ~34 trades/week
- WR ~71-74%, PnL +290%/week (raw) → +22% portfolio/week ($1107)
- Hold avg ~24h
- Concurrence max observée ~10-12 positions
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from openclaw.config import get_settings
from openclaw.portfolio.gate_v6 import passes_optimized_gate


class PortfolioManagerV6:

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 12
    MAX_PER_PAIR = 1
    SIZE_PCT = 8.0
    TP_PCT = 15.0          # ⬆️ Optimal vs +10%: +38% PnL avec -3pts WR
    SL_PCT = 8.0
    TIMEOUT_H = 48

    TABLE = "openclaw_positions_v6"
    STATE_TABLE = "openclaw_portfolio_state_v6"

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
            print(f"⚠️ V6 state init: {e}")

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
        try:
            return float(requests.get("https://api.binance.com/api/v3/ticker/price",
                params={"symbol": pair}, timeout=5).json().get("price", 0))
        except:
            return 0

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
                # Fallback without markdown
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

        # ULTRA GATE
        passed, reason = passes_optimized_gate(pair, alert, label="V6", cache=alert.get("_gate_cache"))
        if not passed:
            print(f"💼 V6 GATE REJECT {pair}: {reason}")
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

        # Max positions (FIFO rotation could be added later)
        if len(open_positions) >= self.MAX_POSITIONS:
            print(f"💼 V6 SKIP {pair}: portfolio full ({self.MAX_POSITIONS}/{self.MAX_POSITIONS})")
            return None

        # 1 per pair
        if any(p.get("pair") == pair for p in open_positions):
            return None

        # Position size: 8% of INITIAL capital (fixed, not compound)
        size_usd = round(self.INITIAL_CAPITAL * self.SIZE_PCT / 100, 2)
        if balance < size_usd:
            print(f"💼 V6 SKIP {pair}: insufficient cash (${balance:.0f} < ${size_usd:.0f})")
            return None

        price = alert.get("price", 0) or 0
        if not price:
            price = await self._get_price(pair)
        if not price:
            return None

        tp = round(price * (1 + self.TP_PCT / 100), 8)
        sl = round(price * (1 - self.SL_PCT / 100), 8)

        position = {
            "id": str(uuid.uuid4()), "pair": pair,
            "entry_price": price, "current_price": price,
            "size_usd": size_usd,
            "sl_price": sl, "tp_price": tp,
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
        }

        try:
            self.sb.table(self.TABLE).insert(position).execute()
        except Exception as e:
            print(f"⚠️ V6 insert: {e}")
            return None

        self._update_state({"balance": round(balance - size_usd, 2)})
        print(f"💼 V6 OPENED: {pair} — {confidence*100:.0f}% — ${size_usd:.0f} @ {price} | TP={tp} SL={sl}")

        # Telegram notification
        score = alert.get("scanner_score", 0)
        vip_badge = "🏆" if (vip or {}).get("is_high_ticket") else ("⭐" if (vip or {}).get("is_vip") else "")
        grade = (quality or {}).get("grade", "")
        await self._tg(
            f"🟢 *V6 OPEN* — `{pair}` {vip_badge}\n"
            f"💰 Size: *${size_usd:.0f}* (8% × $5K)\n"
            f"📍 Entry: `{price}`\n"
            f"🎯 TP: `{tp}` (+15%)\n"
            f"🛡 SL: `{sl}` (-8%)\n"
            f"⏱ Timeout: 48h\n"
            f"📊 Score: {score}/10 | Grade: {grade or '—'} | Conf: {confidence*100:.0f}%"
        )
        return position

    # ==================================================================
    # CHECK POSITIONS
    # ==================================================================

    async def check_positions(self):
        positions = self._get_open_positions()
        if not positions:
            return

        now = datetime.now(timezone.utc)
        checked = closed = 0

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

            pnl = (price - entry) / entry * 100
            highest = max(pos.get("highest_price", price), price)

            # SL — use SL price (not market price) to avoid slippage in PnL
            if pos.get("sl_price") and price <= pos["sl_price"]:
                await self._close(pos, pos["sl_price"], "SL_HIT")
                closed += 1
                continue

            # TP +15% — use TP price for clean exit
            if pos.get("tp_price") and price >= pos["tp_price"]:
                await self._close(pos, pos["tp_price"], "TP_HIT")
                closed += 1
                continue

            # Timeout 48h
            try:
                open_dt = datetime.fromisoformat(pos.get("opened_at", "").replace("Z", "+00:00"))
                age_h = (now - open_dt).total_seconds() / 3600
                if age_h >= self.TIMEOUT_H:
                    await self._close(pos, price, "TIMEOUT_48H")
                    closed += 1
                    continue
            except:
                pass

            try:
                self.sb.table(self.TABLE).update({
                    "current_price": price, "pnl_pct": round(pnl, 2),
                    "pnl_usd": round(pos.get("size_usd", 0) * pnl / 100, 2),
                    "highest_price": highest,
                }).eq("id", pos["id"]).execute()
                checked += 1
            except:
                pass
            time.sleep(0.05)

        if checked or closed:
            print(f"💼 V6 check: {checked} updated, {closed} closed ({len(positions)} open)")

    async def _close(self, pos: Dict, exit_price: float, reason: str):
        entry = pos.get("entry_price", 0)
        size = pos.get("size_usd", 0)
        pnl_pct = (exit_price - entry) / entry * 100 if entry else 0
        pnl_usd = size * pnl_pct / 100
        is_win = pnl_usd > 0

        try:
            self.sb.table(self.TABLE).update({
                "status": "CLOSED", "exit_price": exit_price, "current_price": exit_price,
                "close_reason": reason, "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(pnl_usd, 2),
                "closed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", pos["id"]).execute()
        except:
            return

        state = self.get_portfolio_state()
        bal = state.get("balance", 0) + size + pnl_usd
        tp = state.get("total_pnl", 0) + pnl_usd
        tt = state.get("total_trades", 0) + 1
        w = state.get("wins", 0) + (1 if is_win else 0)
        l = state.get("losses", 0) + (0 if is_win else 1)
        # Drawdown based on total_pnl curve (not balance)
        peak_pnl = max(state.get("peak_balance", 0), tp)  # reuse peak_balance to store peak PnL
        dd = (peak_pnl - tp) / self.INITIAL_CAPITAL * 100 if self.INITIAL_CAPITAL > 0 else 0

        self._update_state({
            "balance": round(bal, 2), "total_pnl": round(tp, 2),
            "total_trades": tt, "wins": w, "losses": l,
            "peak_balance": round(peak_pnl, 2),
            "max_drawdown_pct": round(max(state.get("max_drawdown_pct", 0), dd), 2),
        })
        print(f"💼 V6 {'✅' if is_win else '❌'}: {pos['pair']} {pnl_pct:+.1f}% (${pnl_usd:+.1f}) — {reason}")

        # Telegram notification
        emoji = {"TP_HIT": "✅✅", "SL_HIT": "❌", "TIMEOUT_48H": "⏰"}.get(reason, "🔔")
        wr_pct = (w / tt * 100) if tt else 0
        await self._tg(
            f"{emoji} *V6 CLOSE* — `{pos['pair']}` — *{reason}*\n"
            f"💰 PnL: *{pnl_pct:+.2f}%* (${pnl_usd:+.2f})\n"
            f"📍 Entry: `{entry}` → Exit: `{exit_price}`\n"
            f"📊 Balance V6: *${bal:.0f}* | WR: *{wr_pct:.1f}%* ({w}W/{l}L)"
        )

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print(f"💼 V6 Portfolio started — Body≥3% + Fixed TP+15% | 12 slots × 8% × $5000")

    async def _check_loop(self):
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ V6: {e}")
            await asyncio.sleep(60)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        print("💼 V6 stopped")
