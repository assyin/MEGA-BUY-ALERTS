"""Portfolio Manager V4 — Gate Filter: Score >= 8 + VIP/HT obligatoire.

Same execution as V1 (TP +10%, SL -8%, expiry 7d) but strict entry filter.
This tests whether better filtering alone makes the system profitable.

Rules:
- ONLY Score >= 8
- ONLY VIP or HT (no plain trades)
- TP: +10% | SL: -8% | Expiry: 7 days
- Size: 3% of capital
- Max 15 positions
- Max 2 per pair
- Uses alert price (not live price) for entry
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from openclaw.config import get_settings


class PortfolioManagerV4:

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 15
    MAX_PER_PAIR = 2
    SIZE_PCT = 3.0
    TP_PCT = 10.0
    SL_PCT = 8.0
    EXPIRY_DAYS = 7
    TABLE = "openclaw_positions_v4"
    STATE_TABLE = "openclaw_portfolio_state_v4"

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
                    "drawdown_mode": False, "daily_loss_today": 0,
                }).execute()
        except Exception as e:
            print(f"⚠️ V4 state init: {e}")

    def get_portfolio_state(self) -> Dict:
        try:
            r = self.sb.table(self.STATE_TABLE).select("*").eq("id", "main").single().execute()
            return r.data or {}
        except:
            return {}

    def _update_state(self, updates: Dict):
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.sb.table(self.STATE_TABLE).update(updates).eq("id", "main").execute()
        except Exception as e:
            print(f"⚠️ V4 state update: {e}")

    def _get_open_positions(self) -> List[Dict]:
        try:
            r = self.sb.table(self.TABLE).select("*").eq("status", "OPEN").execute()
            return r.data or []
        except:
            return []

    async def _get_price(self, pair: str) -> float:
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/price",
                             params={"symbol": pair}, timeout=5)
            return float(r.json().get("price", 0))
        except:
            return 0

    # ==================================================================
    # GATE FILTER — the key difference from V1
    # ==================================================================

    def _passes_gate(self, alert: Dict, vip: Optional[Dict], pair: str = "") -> bool:
        """Strict entry filter based on data analysis:
        - Score >= 8 (Score 7 = -374% PnL, 17% WR)
        - VIP or HT obligatoire (No VIP = -1211% PnL)
        - Bougie 4H verte (Green=70% WR vs Red=31% WR, +38% edge)
        """
        score = alert.get("scanner_score", 0) or 0
        if score < 8:
            return False

        is_vip = (vip or {}).get("is_vip", False)
        is_ht = (vip or {}).get("is_high_ticket", False)
        if not is_vip and not is_ht:
            return False

        # Check 4H candle direction (green = 70% WR, red = 31% WR)
        if pair:
            try:
                r = requests.get("https://api.binance.com/api/v3/klines",
                    params={"symbol": pair, "interval": "4h", "limit": 1}, timeout=5)
                kd = r.json()
                if kd and isinstance(kd, list) and len(kd) > 0:
                    o, c = float(kd[0][1]), float(kd[0][4])
                    if c < o:  # Red candle
                        return False
            except:
                pass

        return True

    # ==================================================================
    # OPEN POSITION
    # ==================================================================

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 alert: Dict, vip: Optional[Dict] = None,
                                 quality: Optional[Dict] = None) -> Optional[Dict]:
        """Open position ONLY if passes gate filter."""
        if "BUY" not in decision:
            return None

        if not self._passes_gate(alert, vip, pair):
            return None

        # Check tradability
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
            return None

        # Max 2 per pair
        pair_count = sum(1 for p in open_positions if p.get("pair") == pair)
        if pair_count >= self.MAX_PER_PAIR:
            return None

        size_usd = balance * self.SIZE_PCT / 100
        size_usd = max(size_usd, 10)

        # Use alert price
        price = alert.get("price", 0) or 0
        if not price:
            price = await self._get_price(pair)
        if not price:
            return None

        tp_price = round(price * (1 + self.TP_PCT / 100), 8)
        sl_price = round(price * (1 - self.SL_PCT / 100), 8)

        position = {
            "id": str(uuid.uuid4()),
            "pair": pair,
            "entry_price": price,
            "current_price": price,
            "size_usd": round(size_usd, 2),
            "sl_price": sl_price,
            "tp_price": tp_price,
            "pnl_pct": 0.0,
            "pnl_usd": 0.0,
            "highest_price": price,
            "status": "OPEN",
            "close_reason": None,
            "exit_price": None,
            "decision": decision,
            "confidence": confidence,
            "alert_id": alert.get("id", ""),
            "scanner_score": alert.get("scanner_score", 0),
            "is_vip": (vip or {}).get("is_vip", False),
            "is_high_ticket": (vip or {}).get("is_high_ticket", False),
            "quality_grade": (quality or {}).get("grade", ""),
            "pair_position_nr": pair_count + 1,
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,
        }

        try:
            self.sb.table(self.TABLE).insert(position).execute()
        except Exception as e:
            print(f"⚠️ V4 insert: {e}")
            return None

        new_balance = balance - size_usd
        self._update_state({"balance": round(new_balance, 2)})

        vip_label = "🏆" if (vip or {}).get("is_high_ticket") else "⭐"
        print(f"💼 V4 OPENED: {pair} {vip_label} — {decision} Sc{alert.get('scanner_score',0)} — ${size_usd:.0f} @ {price}")
        return position

    # ==================================================================
    # CHECK POSITIONS (same as V1: TP +10%, SL -8%, expiry 7d)
    # ==================================================================

    async def check_positions(self):
        open_positions = self._get_open_positions()
        if not open_positions:
            return

        now = datetime.now(timezone.utc)
        checked = 0
        closed_count = 0

        for pos in open_positions:
            pair = pos.get("pair", "")
            if not pair:
                continue

            price = await self._get_price(pair)
            if not price:
                continue

            entry = pos.get("entry_price", 0)
            if not entry:
                continue

            pnl_pct = (price - entry) / entry * 100
            highest = max(pos.get("highest_price", price), price)

            # SL
            if pos.get("sl_price") and price <= pos["sl_price"]:
                await self._close(pos, price, "SL_HIT")
                closed_count += 1
                continue

            # TP
            if pos.get("tp_price") and price >= pos["tp_price"]:
                await self._close(pos, price, "TP_HIT")
                closed_count += 1
                continue

            # Expiry
            opened_at = pos.get("opened_at", "")
            if opened_at:
                try:
                    open_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                    if (now - open_dt) > timedelta(days=self.EXPIRY_DAYS):
                        await self._close(pos, price, "EXPIRED")
                        closed_count += 1
                        continue
                except:
                    pass

            # Update
            try:
                self.sb.table(self.TABLE).update({
                    "current_price": price,
                    "pnl_pct": round(pnl_pct, 2),
                    "pnl_usd": round(pos.get("size_usd", 0) * pnl_pct / 100, 2),
                    "highest_price": highest,
                }).eq("id", pos["id"]).execute()
                checked += 1
            except:
                pass

            time.sleep(0.05)

        if checked > 0 or closed_count > 0:
            print(f"💼 V4 check: {checked} updated, {closed_count} closed ({len(open_positions)} open)")

    # ==================================================================
    # CLOSE
    # ==================================================================

    async def _close(self, pos: Dict, exit_price: float, reason: str):
        entry = pos.get("entry_price", 0)
        size_usd = pos.get("size_usd", 0)
        pnl_pct = (exit_price - entry) / entry * 100 if entry else 0
        pnl_usd = size_usd * pnl_pct / 100
        is_win = pnl_usd > 0
        now = datetime.now(timezone.utc)

        try:
            self.sb.table(self.TABLE).update({
                "status": "CLOSED", "exit_price": exit_price, "current_price": exit_price,
                "close_reason": reason, "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(pnl_usd, 2), "closed_at": now.isoformat(),
            }).eq("id", pos["id"]).execute()
        except Exception as e:
            print(f"⚠️ V4 close: {e}")
            return

        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        new_balance = balance + size_usd + pnl_usd
        total_pnl = state.get("total_pnl", 0) + pnl_usd
        total_trades = state.get("total_trades", 0) + 1
        wins = state.get("wins", 0) + (1 if is_win else 0)
        losses = state.get("losses", 0) + (0 if is_win else 1)
        peak = max(state.get("peak_balance", self.INITIAL_CAPITAL), new_balance)
        dd = (peak - new_balance) / peak * 100 if peak > 0 else 0
        max_dd = max(state.get("max_drawdown_pct", 0), dd)

        self._update_state({
            "balance": round(new_balance, 2), "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades, "wins": wins, "losses": losses,
            "peak_balance": round(peak, 2), "max_drawdown_pct": round(max_dd, 2),
        })

        emoji = "✅" if is_win else "❌"
        print(f"💼 V4 CLOSED {emoji}: {pos['pair']} {pnl_pct:+.1f}% (${pnl_usd:+.1f}) — {reason}")

    # ==================================================================
    # START / STOP
    # ==================================================================

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print(f"💼 V4 Portfolio started — Gate: Score>=8 + VIP/HT, 3%×15pos, TP+10%/SL-8%")

    async def _check_loop(self):
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ V4 check error: {e}")
            await asyncio.sleep(300)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        print("💼 V4 Portfolio stopped")
