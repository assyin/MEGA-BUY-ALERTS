"""Portfolio Manager V2 — Partial TP + Trailing Stop + Break-Even.

Runs IN PARALLEL with v1. Uses separate Supabase table: openclaw_positions_v2.
Same capital ($5000), same alerts, different execution.

V2 changes vs V1:
- TP1 = +10% → close 30% of position
- TP2 = +20% → close 30% of position
- Runner = 40% with trailing stop (2.5 × ATR or higher-low structure)
- Break-even: after TP1 → SL = entry. After TP2 → SL = +10%
- Context Score integration for position sizing

All v1 code is UNTOUCHED. This is a separate class with its own table.
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from openclaw.config import get_settings


class PortfolioManagerV2:
    """V2 paper-trading with partial TP + trailing stop."""

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 10
    MAX_DAILY_LOSS_PCT = 5.0
    MAX_DRAWDOWN_PCT = 15.0
    TABLE = "openclaw_positions_v2"
    STATE_TABLE = "openclaw_portfolio_state_v2"

    def __init__(self, telegram_bot=None):
        self.settings = get_settings()
        self.telegram_bot = telegram_bot
        self._running = False

        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        self._ensure_state()

    def _ensure_state(self):
        """Create portfolio state if not exists."""
        try:
            r = self.sb.table(self.STATE_TABLE).select("id").eq("id", "main").execute()
            if not r.data:
                self.sb.table(self.STATE_TABLE).insert({
                    "id": "main",
                    "balance": self.INITIAL_CAPITAL,
                    "initial_capital": self.INITIAL_CAPITAL,
                    "total_pnl": 0, "total_trades": 0, "wins": 0, "losses": 0,
                    "max_drawdown_pct": 0, "peak_balance": self.INITIAL_CAPITAL,
                    "drawdown_mode": False, "daily_loss_today": 0,
                }).execute()
        except Exception as e:
            print(f"⚠️ V2 state init: {e}")

    def get_portfolio_state(self) -> Dict:
        try:
            r = self.sb.table(self.STATE_TABLE).select("*").eq("id", "main").single().execute()
            return r.data or {}
        except:
            return {}

    def _update_portfolio_state(self, updates: Dict):
        try:
            updates["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.sb.table(self.STATE_TABLE).update(updates).eq("id", "main").execute()
        except Exception as e:
            print(f"⚠️ V2 state update: {e}")

    def _get_open_positions(self) -> List[Dict]:
        try:
            r = self.sb.table(self.TABLE).select("*").eq("status", "OPEN").execute()
            return r.data or []
        except:
            return []

    async def _get_price(self, pair: str) -> float:
        try:
            r = requests.get(f"https://api.binance.com/api/v3/ticker/price",
                             params={"symbol": pair}, timeout=5)
            return float(r.json().get("price", 0))
        except:
            return 0

    # ==================================================================
    # OPEN POSITION (with context score sizing)
    # ==================================================================

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 analysis_summary: Dict, alert: Dict,
                                 vip: Optional[Dict] = None,
                                 quality: Optional[Dict] = None) -> Optional[Dict]:
        """Open position with V2 execution: partial TP + trailing."""
        # Check tradability
        try:
            from openclaw.pipeline.pair_filter import is_tradable
            if not is_tradable(pair):
                return None
        except:
            pass

        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        drawdown_mode = state.get("drawdown_mode", False)

        if balance < 50:
            return None

        open_positions = self._get_open_positions()
        if len(open_positions) >= self.MAX_POSITIONS:
            return None

        for pos in open_positions:
            if pos.get("pair") == pair:
                return None

        # Context Score sizing
        context_score = self._compute_context_score(quality, vip, alert)
        size_pct = self._size_from_context(context_score, decision, drawdown_mode)

        if size_pct <= 0:
            print(f"💼 V2: {pair} skipped — context_score={context_score} too low")
            return None

        size_usd = balance * size_pct / 100
        size_usd = max(size_usd, 10)

        price = await self._get_price(pair)
        if not price:
            return None

        # Dynamic SL (same as v1)
        sl_price, sl_reason = self._calculate_sl(price, analysis_summary)

        # V2 TP structure: TP1 (+10%), TP2 (+20%), runner (trailing)
        tp1_price = round(price * 1.10, 8)
        tp2_price = round(price * 1.20, 8)

        position = {
            "id": str(uuid.uuid4()),
            "pair": pair,
            "side": "LONG",
            "entry_price": price,
            "current_price": price,
            "size_usd": round(size_usd, 2),
            "size_remaining_pct": 100,  # 100% of position still open
            "sl_price": round(sl_price, 8),
            "sl_initial": round(sl_price, 8),  # original SL for reference
            "sl_reason": sl_reason,
            "tp1_price": tp1_price,
            "tp1_hit": False,
            "tp2_price": tp2_price,
            "tp2_hit": False,
            "trailing_active": False,
            "trailing_sl": 0,
            "pnl_pct": 0.0,
            "pnl_usd": 0.0,
            "pnl_realized": 0.0,  # accumulated realized PnL from partial closes
            "highest_price": price,
            "status": "OPEN",
            "close_reason": None,
            "exit_price": None,
            "decision": decision,
            "confidence": confidence,
            "alert_id": alert.get("id", ""),
            "scanner_score": alert.get("scanner_score", 0),
            "context_score": context_score,
            "is_vip": (vip or {}).get("is_vip", False),
            "is_high_ticket": (vip or {}).get("is_high_ticket", False),
            "quality_grade": (quality or {}).get("grade", ""),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,
        }

        try:
            self.sb.table(self.TABLE).insert(position).execute()
        except Exception as e:
            print(f"⚠️ V2 insert error: {e}")
            return None

        new_balance = balance - size_usd
        self._update_portfolio_state({"balance": round(new_balance, 2)})

        print(f"💼 V2 OPENED: {pair} — ctx={context_score} size=${size_usd:.2f} @ {price} | TP1={tp1_price} TP2={tp2_price} SL={sl_price}")
        return position

    # ==================================================================
    # CHECK POSITIONS (V2: partial TP + trailing + break-even)
    # ==================================================================

    async def check_positions(self):
        """Every 5 min: check partial TPs, trailing, break-even."""
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
            remaining = pos.get("size_remaining_pct", 100)
            size_usd = pos.get("size_usd", 0)
            highest = max(pos.get("highest_price", price), price)
            realized = pos.get("pnl_realized", 0)
            updates = {
                "current_price": price,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(size_usd * pnl_pct / 100, 2),
                "highest_price": highest,
            }

            # ── SL CHECK (always first) ──
            sl = pos.get("sl_price", 0)
            if sl and price <= sl:
                # Close remaining position at SL
                close_pnl = size_usd * (remaining / 100) * pnl_pct / 100
                total_pnl = realized + close_pnl
                reason = "SL_HIT" if not pos.get("tp1_hit") else "TRAILING_SL"
                await self._close_full(pos, price, reason, total_pnl)
                closed_count += 1
                continue

            # ── TP1 CHECK (+10%) — close 30% ──
            tp1 = pos.get("tp1_price", 0)
            if tp1 and not pos.get("tp1_hit") and price >= tp1:
                # Realize 30% of position
                partial_pnl = size_usd * 0.30 * ((tp1 - entry) / entry)
                new_realized = realized + partial_pnl
                new_remaining = remaining - 30

                # Break-even: move SL to entry
                updates.update({
                    "tp1_hit": True,
                    "size_remaining_pct": new_remaining,
                    "pnl_realized": round(new_realized, 2),
                    "sl_price": entry,  # BREAK-EVEN
                    "sl_reason": "break_even_tp1",
                })
                print(f"💼 V2 TP1 HIT: {pair} +10% — closed 30%, SL→entry, remaining={new_remaining}%")

            # ── TP2 CHECK (+20%) — close 30% ──
            tp2 = pos.get("tp2_price", 0)
            if tp2 and pos.get("tp1_hit") and not pos.get("tp2_hit") and price >= tp2:
                partial_pnl = size_usd * 0.30 * ((tp2 - entry) / entry)
                current_realized = updates.get("pnl_realized", pos.get("pnl_realized", 0))
                new_realized = current_realized + partial_pnl
                new_remaining = (updates.get("size_remaining_pct", remaining)) - 30

                # Move SL to +10%, activate trailing
                updates.update({
                    "tp2_hit": True,
                    "size_remaining_pct": new_remaining,
                    "pnl_realized": round(new_realized, 2),
                    "sl_price": round(tp1, 8),  # SL = +10%
                    "sl_reason": "lock_10pct_tp2",
                    "trailing_active": True,
                    "trailing_sl": round(tp1, 8),
                })
                print(f"💼 V2 TP2 HIT: {pair} +20% — closed 30%, SL→+10%, trailing ON, remaining={new_remaining}%")

            # ── TRAILING STOP (runner) ──
            if pos.get("trailing_active") or updates.get("trailing_active"):
                # Trailing = highest - 2.5× ATR proxy (use 5% of highest as fallback)
                trail_pct = 0.08  # 8% trailing from highest
                trail_sl = highest * (1 - trail_pct)

                # Only move SL up, never down
                current_trailing = updates.get("trailing_sl", pos.get("trailing_sl", 0))
                if trail_sl > current_trailing:
                    updates["trailing_sl"] = round(trail_sl, 8)
                    updates["sl_price"] = round(trail_sl, 8)
                    updates["sl_reason"] = f"trailing_8pct_from_{highest:.6f}"

            # ── EXPIRY (10 days for v2 — runners need more time) ──
            opened_at = pos.get("opened_at", "")
            if opened_at:
                try:
                    open_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                    if (now - open_dt) > timedelta(days=10):
                        close_pnl = size_usd * (remaining / 100) * pnl_pct / 100
                        total_pnl = realized + close_pnl
                        await self._close_full(pos, price, "EXPIRED", total_pnl)
                        closed_count += 1
                        continue
                except:
                    pass

            # Update position
            try:
                self.sb.table(self.TABLE).update(updates).eq("id", pos["id"]).execute()
                checked += 1
            except:
                pass

            time.sleep(0.05)

        if checked > 0 or closed_count > 0:
            print(f"💼 V2 check: {checked} updated, {closed_count} closed ({len(open_positions)} open)")

    # ==================================================================
    # CLOSE FULL POSITION
    # ==================================================================

    async def _close_full(self, pos: Dict, exit_price: float, reason: str, total_pnl_usd: float):
        """Close remaining position and update balance."""
        entry = pos.get("entry_price", 0)
        size_usd = pos.get("size_usd", 0)
        pnl_pct = (exit_price - entry) / entry * 100 if entry else 0

        # Total PnL includes realized partials
        is_win = total_pnl_usd > 0
        now = datetime.now(timezone.utc)

        try:
            self.sb.table(self.TABLE).update({
                "status": "CLOSED",
                "exit_price": exit_price,
                "current_price": exit_price,
                "close_reason": reason,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(total_pnl_usd, 2),
                "size_remaining_pct": 0,
                "closed_at": now.isoformat(),
            }).eq("id", pos["id"]).execute()
        except Exception as e:
            print(f"⚠️ V2 close error: {e}")
            return

        # Update state
        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        remaining_pct = pos.get("size_remaining_pct", 100)
        returned = size_usd * (remaining_pct / 100)  # return unrealized portion
        new_balance = balance + returned + total_pnl_usd

        total_pnl = state.get("total_pnl", 0) + total_pnl_usd
        total_trades = state.get("total_trades", 0) + 1
        wins = state.get("wins", 0) + (1 if is_win else 0)
        losses = state.get("losses", 0) + (0 if is_win else 1)
        peak = max(state.get("peak_balance", self.INITIAL_CAPITAL), new_balance)
        dd = (peak - new_balance) / peak * 100 if peak > 0 else 0
        max_dd = max(state.get("max_drawdown_pct", 0), dd)

        self._update_portfolio_state({
            "balance": round(new_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "wins": wins, "losses": losses,
            "peak_balance": round(peak, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "drawdown_mode": dd > self.MAX_DRAWDOWN_PCT,
        })

        emoji = "✅" if is_win else "❌"
        print(f"💼 V2 CLOSED {emoji}: {pos['pair']} final_pnl=${total_pnl_usd:+.2f} ({pnl_pct:+.1f}% exit) — {reason} | tp1={pos.get('tp1_hit')} tp2={pos.get('tp2_hit')}")

    # ==================================================================
    # CONTEXT SCORE
    # ==================================================================

    def _compute_context_score(self, quality: Optional[Dict], vip: Optional[Dict], alert: Dict) -> int:
        """Compute context score 0→5 from quality axes + HT + EC.

        4 axes >= 3 → +2
        HT actif    → +2
        EC actif    → +1
        """
        score = 0
        # Quality axes
        axes = (quality or {}).get("axes", 0)
        if axes >= 3:
            score += 2

        # HT
        if (vip or {}).get("is_high_ticket", False):
            score += 2
        elif (vip or {}).get("is_vip", False):
            score += 1  # VIP (non-HT) = +1 instead of +2

        # EC
        if alert.get("ec", False):
            score += 1

        return score

    def _size_from_context(self, ctx_score: int, decision: str, drawdown_mode: bool) -> float:
        """Position size % based on context score.

        5 = Elite → 5%
        4 = Strong → 3%
        3 = Medium → 2%
        ≤2 = Low → 1% (minimal exposure)
        """
        if ctx_score >= 5:
            pct = 5.0
        elif ctx_score >= 4:
            pct = 3.0
        elif ctx_score >= 3:
            pct = 2.0
        else:
            pct = 1.0

        if drawdown_mode:
            pct *= 0.5

        return pct

    # ==================================================================
    # SL CALCULATION (reuse v1 logic)
    # ==================================================================

    def _calculate_sl(self, price: float, summary: Dict) -> Tuple[float, str]:
        """Calculate SL from technical levels. Simplified from v1."""
        if not summary:
            return price * 0.92, "fixed_8pct"

        import re

        # Try OB support
        for key in ["ob_4h_nearest", "ob_1h_nearest"]:
            ob_str = str(summary.get(key, ""))
            low_match = re.search(r'([\d.]+)-([\d.]+)', ob_str)
            if low_match:
                low = float(low_match.group(1))
                if 0 < low < price and (price - low) / price * 100 < 12:
                    return round(low * 0.99, 8), f"{key}_low"

        # Try VP VAL
        for key in ["vp_4h", "vp_1h"]:
            vp_str = str(summary.get(key, ""))
            val_match = re.search(r'VAL=([\d.]+)', vp_str)
            if val_match:
                val = float(val_match.group(1))
                if 0 < val < price and (price - val) / price * 100 < 12:
                    return round(val * 0.99, 8), f"{key}_val"

        # Fallback
        return round(price * 0.92, 8), "fixed_8pct"

    # ==================================================================
    # START / STOP
    # ==================================================================

    async def start(self):
        """Start V2 position checking loop (every 5 min)."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print("💼 V2 Portfolio started — partial TP + trailing")

    async def _check_loop(self):
        """Background loop — checks positions every 5 min."""
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ V2 check error: {e}")
            await asyncio.sleep(300)

    async def stop(self):
        self._running = False
        if hasattr(self, '_task') and self._task:
            self._task.cancel()
        print("💼 V2 Portfolio stopped")
