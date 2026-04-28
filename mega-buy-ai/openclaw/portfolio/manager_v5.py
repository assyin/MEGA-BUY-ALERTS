"""Portfolio Manager V5 — Combo Ultime: Conf>=95% + Green 4H + 24h>0%.

Based on data: 33 trades, 81.8% WR, +28.2% edge vs baseline.
Same execution as V1 (TP +10%, SL -8%) but ultra-strict entry.

Rules:
- Confidence >= 95%
- Bougie 4H verte (green)
- 24h change > 0%
- TP: +10% | SL: -8% | Expiry: 7 days
- Size: 3% | Max 25 positions | Max 2 per pair
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

from openclaw.config import get_settings


class PortfolioManagerV5:

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 25
    MAX_PER_PAIR = 2
    SIZE_PCT = 3.0
    TP_PCT = 10.0
    SL_PCT = 8.0
    EXPIRY_DAYS = 7
    MIN_CONFIDENCE = 0.95
    TABLE = "openclaw_positions_v5"
    STATE_TABLE = "openclaw_portfolio_state_v5"

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
            print(f"⚠️ V5 state init: {e}")

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

    # ==================================================================
    # ULTRA GATE — Conf>=95% + Green 4H + 24h>0%
    # ==================================================================

    def _passes_ultra_gate(self, pair: str, confidence: float) -> bool:
        """81.8% WR combo based on 6-day analysis."""
        if confidence < self.MIN_CONFIDENCE:
            return False

        try:
            # Check 4H candle = green
            r = requests.get("https://api.binance.com/api/v3/klines",
                params={"symbol": pair, "interval": "4h", "limit": 1}, timeout=5)
            kd = r.json()
            if not kd or not isinstance(kd, list) or len(kd) == 0:
                return False
            o, c = float(kd[0][1]), float(kd[0][4])
            if c < o:  # Red = reject
                return False

            # Check 24h change > 0%
            r2 = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                params={"symbol": pair}, timeout=5)
            change = float(r2.json().get("priceChangePercent", 0))
            if change <= 0:
                return False

        except:
            return False

        return True

    # ==================================================================
    # OPEN POSITION
    # ==================================================================

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 alert: Dict, vip: Optional[Dict] = None,
                                 quality: Optional[Dict] = None) -> Optional[Dict]:
        if "BUY" not in decision:
            return None

        if not self._passes_ultra_gate(pair, confidence):
            return None

        try:
            from openclaw.pipeline.pair_filter import is_tradable
            if not is_tradable(pair): return None
        except:
            pass

        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        if balance < 50: return None

        open_positions = self._get_open_positions()
        if len(open_positions) >= self.MAX_POSITIONS: return None

        pair_count = sum(1 for p in open_positions if p.get("pair") == pair)
        if pair_count >= self.MAX_PER_PAIR: return None

        size_usd = max(balance * self.SIZE_PCT / 100, 10)

        price = alert.get("price", 0) or 0
        if not price: price = await self._get_price(pair)
        if not price: return None

        tp = round(price * (1 + self.TP_PCT / 100), 8)
        sl = round(price * (1 - self.SL_PCT / 100), 8)

        position = {
            "id": str(uuid.uuid4()), "pair": pair,
            "entry_price": price, "current_price": price,
            "size_usd": round(size_usd, 2),
            "sl_price": sl, "tp_price": tp,
            "pnl_pct": 0.0, "pnl_usd": 0.0, "highest_price": price,
            "status": "OPEN", "close_reason": None, "exit_price": None,
            "decision": decision, "confidence": confidence,
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
            print(f"⚠️ V5 insert: {e}"); return None

        self._update_state({"balance": round(balance - size_usd, 2)})
        print(f"💼 V5 OPENED: {pair} — 95%+Green+24h>0 — ${size_usd:.0f} @ {price}")
        return position

    # ==================================================================
    # CHECK POSITIONS
    # ==================================================================

    async def check_positions(self):
        positions = self._get_open_positions()
        if not positions: return

        now = datetime.now(timezone.utc)
        checked = closed = 0

        for pos in positions:
            pair = pos.get("pair", "")
            if not pair: continue
            price = await self._get_price(pair)
            if not price: continue
            entry = pos.get("entry_price", 0)
            if not entry: continue

            pnl = (price - entry) / entry * 100
            highest = max(pos.get("highest_price", price), price)

            if pos.get("sl_price") and price <= pos["sl_price"]:
                await self._close(pos, pos["sl_price"], "SL_HIT"); closed += 1; continue
            if pos.get("tp_price") and price >= pos["tp_price"]:
                await self._close(pos, pos["tp_price"], "TP_HIT"); closed += 1; continue

            try:
                open_dt = datetime.fromisoformat(pos.get("opened_at", "").replace("Z", "+00:00"))
                if (now - open_dt) > timedelta(days=self.EXPIRY_DAYS):
                    await self._close(pos, price, "EXPIRED"); closed += 1; continue
            except: pass

            try:
                self.sb.table(self.TABLE).update({
                    "current_price": price, "pnl_pct": round(pnl, 2),
                    "pnl_usd": round(pos.get("size_usd", 0) * pnl / 100, 2),
                    "highest_price": highest,
                }).eq("id", pos["id"]).execute()
                checked += 1
            except: pass
            time.sleep(0.05)

        if checked or closed:
            print(f"💼 V5 check: {checked} updated, {closed} closed ({len(positions)} open)")

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
                "pnl_usd": round(pnl_usd, 2), "closed_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", pos["id"]).execute()
        except: return

        state = self.get_portfolio_state()
        bal = state.get("balance", 0) + size + pnl_usd
        tp = state.get("total_pnl", 0) + pnl_usd
        tt = state.get("total_trades", 0) + 1
        w = state.get("wins", 0) + (1 if is_win else 0)
        l = state.get("losses", 0) + (0 if is_win else 1)
        # Drawdown based on total_pnl curve (not balance)
        peak_pnl = max(state.get("peak_balance", 0), tp)
        dd = (peak_pnl - tp) / self.INITIAL_CAPITAL * 100 if self.INITIAL_CAPITAL > 0 else 0

        self._update_state({
            "balance": round(bal, 2), "total_pnl": round(tp, 2),
            "total_trades": tt, "wins": w, "losses": l,
            "peak_balance": round(peak_pnl, 2),
            "max_drawdown_pct": round(max(state.get("max_drawdown_pct", 0), dd), 2),
        })
        print(f"💼 V5 {'✅' if is_win else '❌'}: {pos['pair']} {pnl_pct:+.1f}% (${pnl_usd:+.1f}) — {reason}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print("💼 V5 Portfolio started — Combo: 95%+Green4H+24h>0%, 81.8% WR expected")

    async def _check_loop(self):
        while self._running:
            try: await self.check_positions()
            except Exception as e: print(f"⚠️ V5: {e}")
            await asyncio.sleep(60)

    async def stop(self):
        self._running = False
        if self._task: self._task.cancel()
        print("💼 V5 stopped")
