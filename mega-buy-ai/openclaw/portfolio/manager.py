"""Autonomous paper-trading portfolio manager for OpenClaw.

Manages virtual positions with $5000 starting capital.
When OpenClaw says BUY -> opens a position with dynamic SL/TP.
Every 5 min -> checks all open positions against live Binance prices.
"""

import asyncio
import re
import uuid
import time
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple

from openclaw.config import get_settings


class PortfolioManager:
    """Paper-trading portfolio with risk management and dynamic SL/TP."""

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 10
    MAX_DAILY_LOSS_PCT = 5.0     # 5% of capital
    MAX_DRAWDOWN_PCT = 15.0      # 15% -> reduce sizes by 50%

    def __init__(self, telegram_bot=None):
        self.settings = get_settings()
        self.telegram_bot = telegram_bot
        self._running = False
        self._task = None

        # Connect to Supabase
        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)

        # Ensure portfolio state exists
        self._ensure_portfolio_state()

    # ==================================================================
    # LIFECYCLE
    # ==================================================================

    async def start(self, interval_minutes: int = 5):
        """Start the position-checking loop."""
        self._running = True
        self._task = asyncio.create_task(self._check_loop(interval_minutes))
        print(f"💼 PortfolioManager started (check every {interval_minutes}min, capital=${self.INITIAL_CAPITAL})")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    async def _check_loop(self, interval_minutes: int):
        """Check positions every N minutes."""
        await asyncio.sleep(30)  # Let other services start first
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ PortfolioManager check error: {e}")
            await asyncio.sleep(interval_minutes * 60)

    # ==================================================================
    # PORTFOLIO STATE
    # ==================================================================

    def _ensure_portfolio_state(self):
        """Load or create portfolio state in Supabase."""
        try:
            result = self.sb.table("openclaw_portfolio_state") \
                .select("*").eq("id", "main").execute()
            if not result.data:
                self._init_portfolio_state()
        except Exception as e:
            print(f"⚠️ Portfolio state table check failed: {e}")
            print("  Create openclaw_portfolio_state and openclaw_positions tables in Supabase.")

    def _init_portfolio_state(self):
        """Create initial portfolio state."""
        state = {
            "id": "main",
            "balance": self.INITIAL_CAPITAL,
            "initial_capital": self.INITIAL_CAPITAL,
            "total_pnl": 0.0,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "max_drawdown_pct": 0.0,
            "peak_balance": self.INITIAL_CAPITAL,
            "drawdown_mode": False,
            "daily_loss_today": 0.0,
            "last_daily_reset": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            self.sb.table("openclaw_portfolio_state").upsert(state).execute()
        except Exception as e:
            print(f"⚠️ Portfolio state init error: {e}")

    def get_portfolio_state(self) -> Dict:
        """Return current portfolio state."""
        try:
            result = self.sb.table("openclaw_portfolio_state") \
                .select("*").eq("id", "main").single().execute()
            state = result.data or {}
            # Reset daily loss if new day
            self._maybe_reset_daily(state)
            return state
        except Exception as e:
            return {"error": str(e)}

    def _maybe_reset_daily(self, state: Dict):
        """Reset daily loss counter if it's a new day."""
        last_reset = state.get("last_daily_reset", "")
        if not last_reset:
            return
        try:
            last_dt = datetime.fromisoformat(last_reset.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if last_dt.date() < now.date():
                self.sb.table("openclaw_portfolio_state").update({
                    "daily_loss_today": 0.0,
                    "last_daily_reset": now.isoformat(),
                }).eq("id", "main").execute()
        except Exception:
            pass

    def _update_portfolio_state(self, updates: Dict):
        """Update portfolio state fields."""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            self.sb.table("openclaw_portfolio_state") \
                .update(updates).eq("id", "main").execute()
        except Exception as e:
            print(f"⚠️ Portfolio state update error: {e}")

    # ==================================================================
    # OPEN POSITION
    # ==================================================================

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 analysis_summary: Dict, alert: Dict, vip: Optional[Dict] = None) -> Optional[Dict]:
        """Called when OpenClaw says BUY. Check risk rules and open position if OK."""
        # Check if pair is tradable (not delisted)
        try:
            from openclaw.pipeline.pair_filter import is_tradable
            if not is_tradable(pair):
                print(f"💼 Portfolio: {pair} is NOT tradable (delisted/non-trading) — skipping")
                return None
        except Exception:
            pass

        state = self.get_portfolio_state()
        if "error" in state:
            print(f"⚠️ Portfolio: cannot load state — {state['error']}")
            return None

        balance = state.get("balance", 0)
        daily_loss = state.get("daily_loss_today", 0)
        drawdown_mode = state.get("drawdown_mode", False)

        # --- Risk checks ---

        # 1. Capital available?
        if balance < 50:
            print(f"💼 Portfolio: insufficient balance (${balance:.2f})")
            return None

        # 2. Max positions reached?
        open_positions = self._get_open_positions()
        if len(open_positions) >= self.MAX_POSITIONS:
            print(f"💼 Portfolio: max positions reached ({len(open_positions)}/{self.MAX_POSITIONS})")
            return None

        # 3. Pair already in position?
        for pos in open_positions:
            if pos.get("pair") == pair:
                print(f"💼 Portfolio: {pair} already has an open position")
                return None

        # 4. Daily loss limit?
        initial_cap = state.get("initial_capital", self.INITIAL_CAPITAL)
        max_daily_loss = initial_cap * self.MAX_DAILY_LOSS_PCT / 100
        if daily_loss >= max_daily_loss:
            print(f"💼 Portfolio: daily loss limit reached (${daily_loss:.2f} >= ${max_daily_loss:.2f})")
            return None

        # --- Position sizing ---
        conf_pct = confidence * 100 if confidence <= 1 else confidence
        if conf_pct >= 75 or "STRONG" in decision.upper():
            size_pct = 5.0
        elif conf_pct >= 60:
            size_pct = 3.0
        else:
            size_pct = 2.0

        # Drawdown mode: reduce sizes by 50%
        if drawdown_mode:
            size_pct *= 0.5
            print(f"💼 Portfolio: drawdown mode active — size reduced to {size_pct}%")

        size_usd = balance * size_pct / 100
        size_usd = max(size_usd, 10)  # Minimum $10

        # --- Get price (use alert price = signal time, fallback to live) ---
        price = alert.get("price", 0) or 0
        if not price:
            price = await self._get_price(pair)
        if not price:
            print(f"💼 Portfolio: cannot get price for {pair}")
            return None

        # --- Dynamic SL/TP ---
        sl_price, sl_reason, tp_price, tp_reason = self._calculate_dynamic_sl_tp(
            pair, price, analysis_summary
        )

        # --- Calculate R:R ---
        risk = abs(price - sl_price) / price * 100 if sl_price else 8.0
        reward = abs(tp_price - price) / price * 100 if tp_price else 15.0
        rr_ratio = reward / risk if risk > 0 else 0

        # --- Open position ---
        position = {
            "id": str(uuid.uuid4()),
            "pair": pair,
            "side": "LONG",
            "entry_price": price,
            "current_price": price,
            "size_usd": round(size_usd, 2),
            "sl_price": round(sl_price, 8),
            "tp_price": round(tp_price, 8),
            "sl_reason": sl_reason,
            "tp_reason": tp_reason,
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
            "vip_score": (vip or {}).get("vip_score", 0),
            "is_high_ticket": (vip or {}).get("is_high_ticket", False),
            "accumulation_days": round((analysis_summary or {}).get("accumulation", {}).get("days", 0) if isinstance((analysis_summary or {}).get("accumulation"), dict) else 0, 1),
            "opened_at": datetime.now(timezone.utc).isoformat(),
            "closed_at": None,
        }

        try:
            self.sb.table("openclaw_positions").insert(position).execute()
        except Exception as e:
            print(f"⚠️ Portfolio: position insert error: {e}")
            return None

        # Update balance (reserve the position size)
        new_balance = balance - size_usd
        self._update_portfolio_state({"balance": round(new_balance, 2)})

        # Send Telegram notification
        await self._notify_position_opened(position, new_balance, len(open_positions) + 1, rr_ratio)

        print(f"💼 POSITION OPENED: {pair} — {decision} ({conf_pct:.0f}%) — ${size_usd:.2f} @ {price}")
        return position

    # ==================================================================
    # CHECK POSITIONS
    # ==================================================================

    async def check_positions(self):
        """Called every 5 min. Check all open positions against current prices."""
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

            entry_price = pos.get("entry_price", 0)
            if not entry_price:
                continue

            # Calculate PnL
            pnl_pct = (price - entry_price) / entry_price * 100
            pnl_usd = pos.get("size_usd", 0) * pnl_pct / 100
            highest = max(pos.get("highest_price", price), price)

            # Check SL
            sl_price = pos.get("sl_price", 0)
            if sl_price and price <= sl_price:
                await self.close_position(pos["id"], price, "SL_HIT")
                closed_count += 1
                continue

            # Check TP
            tp_price = pos.get("tp_price", 0)
            if tp_price and price >= tp_price:
                await self.close_position(pos["id"], price, "TP_HIT")
                closed_count += 1
                continue

            # Check expiry (7 days)
            opened_at = pos.get("opened_at", "")
            if opened_at:
                try:
                    open_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                    if (now - open_dt) > timedelta(days=7):
                        await self.close_position(pos["id"], price, "EXPIRED")
                        closed_count += 1
                        continue
                except Exception:
                    pass

            # Update live PnL and highest price
            try:
                self.sb.table("openclaw_positions").update({
                    "current_price": price,
                    "pnl_pct": round(pnl_pct, 2),
                    "pnl_usd": round(pnl_usd, 2),
                    "highest_price": highest,
                }).eq("id", pos["id"]).execute()
                checked += 1
            except Exception:
                pass

            time.sleep(0.05)  # Rate limiting

        if checked > 0 or closed_count > 0:
            print(f"💼 Portfolio check: {checked} updated, {closed_count} closed ({len(open_positions)} open)")

    # ==================================================================
    # CLOSE POSITION
    # ==================================================================

    async def close_position(self, position_id: str, exit_price: float, reason: str):
        """Close a position and update balance."""
        try:
            result = self.sb.table("openclaw_positions") \
                .select("*").eq("id", position_id).single().execute()
            pos = result.data
        except Exception as e:
            print(f"⚠️ Portfolio close error: {e}")
            return

        if not pos:
            return

        entry_price = pos.get("entry_price", 0)
        size_usd = pos.get("size_usd", 0)
        if not entry_price:
            return

        pnl_pct = (exit_price - entry_price) / entry_price * 100
        pnl_usd = size_usd * pnl_pct / 100
        now = datetime.now(timezone.utc)

        is_win = pnl_pct > 0

        # Update position
        try:
            self.sb.table("openclaw_positions").update({
                "status": "CLOSED",
                "exit_price": exit_price,
                "current_price": exit_price,
                "close_reason": reason,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(pnl_usd, 2),
                "closed_at": now.isoformat(),
            }).eq("id", position_id).execute()
        except Exception as e:
            print(f"⚠️ Portfolio close update error: {e}")
            return

        # Update portfolio state
        state = self.get_portfolio_state()
        balance = state.get("balance", 0)
        # Return position size + PnL to balance
        new_balance = balance + size_usd + pnl_usd
        total_pnl = state.get("total_pnl", 0) + pnl_usd
        total_trades = state.get("total_trades", 0) + 1
        wins = state.get("wins", 0) + (1 if is_win else 0)
        losses = state.get("losses", 0) + (0 if is_win else 1)
        peak_balance = max(state.get("peak_balance", self.INITIAL_CAPITAL), new_balance)
        daily_loss = state.get("daily_loss_today", 0) + (abs(pnl_usd) if not is_win else 0)

        # Calculate drawdown
        drawdown_pct = 0
        if peak_balance > 0:
            drawdown_pct = (peak_balance - new_balance) / peak_balance * 100
        max_dd = max(state.get("max_drawdown_pct", 0), drawdown_pct)
        drawdown_mode = drawdown_pct > self.MAX_DRAWDOWN_PCT

        self._update_portfolio_state({
            "balance": round(new_balance, 2),
            "total_pnl": round(total_pnl, 2),
            "total_trades": total_trades,
            "wins": wins,
            "losses": losses,
            "peak_balance": round(peak_balance, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "drawdown_mode": drawdown_mode,
            "daily_loss_today": round(daily_loss, 2),
        })

        # Log
        emoji = "WIN" if is_win else "LOSE"
        print(f"💼 POSITION CLOSED [{emoji}]: {pos['pair']} {pnl_pct:+.1f}% (${pnl_usd:+.2f}) — {reason}")

        # Telegram notification
        await self._notify_position_closed(pos, exit_price, pnl_pct, pnl_usd, reason,
                                            new_balance, wins, losses, total_pnl)

    # ==================================================================
    # DYNAMIC SL/TP CALCULATION
    # ==================================================================

    def _calculate_dynamic_sl_tp(self, pair: str, price: float,
                                  analysis_summary: Dict) -> Tuple[float, str, float, str]:
        """Calculate SL and TP from technical levels in analysis_summary.

        Returns (sl_price, sl_reason, tp_price, tp_reason).
        """
        sl_price = 0
        sl_reason = ""
        tp_price = 0
        tp_reason = ""

        if not analysis_summary:
            return self._fixed_sl_tp(price)

        # --- SL: find nearest support below price ---

        # Try OB 4H support (strongest)
        sl_price, sl_reason = self._parse_ob_support(
            analysis_summary.get("ob_4h_nearest", ""), price, "OB_4H_support"
        )

        # Try OB 1H support if 4H didn't work
        if not sl_price:
            sl_price, sl_reason = self._parse_ob_support(
                analysis_summary.get("ob_1h_nearest", ""), price, "OB_1H_support"
            )

        # Try VP VAL (Value Area Low)
        if not sl_price:
            sl_price, sl_reason = self._parse_vp_val(
                analysis_summary.get("vp_4h", ""), price
            )
            if not sl_price:
                sl_price, sl_reason = self._parse_vp_val(
                    analysis_summary.get("vp_1h", ""), price
                )

        # Try Fibonacci support
        if not sl_price:
            fib_str = ""
            filters = analysis_summary.get("filters", {})
            if isinstance(filters, dict):
                fib_str = filters.get("fib_4h", "") or filters.get("fib_1h", "")
            sl_price, sl_reason = self._parse_fib_support(fib_str, price)

        # Fallback: -8% fixed SL
        if not sl_price:
            sl_price = price * 0.92
            sl_reason = "fixed_8pct"

        # Ensure SL is below price (sanity check)
        if sl_price >= price:
            sl_price = price * 0.92
            sl_reason = "fixed_8pct"

        # --- TP: find nearest resistance above price ---

        # Try OB resistance above
        tp_price, tp_reason = self._parse_ob_resistance(
            analysis_summary.get("ob_4h_nearest", ""), price, "OB_4H_resistance"
        )
        if not tp_price:
            tp_price, tp_reason = self._parse_ob_resistance(
                analysis_summary.get("ob_1h_nearest", ""), price, "OB_1H_resistance"
            )

        # Try VP POC or VAH
        if not tp_price:
            tp_price, tp_reason = self._parse_vp_resistance(
                analysis_summary.get("vp_4h", ""), price
            )
            if not tp_price:
                tp_price, tp_reason = self._parse_vp_resistance(
                    analysis_summary.get("vp_1h", ""), price
                )

        # Try Fibonacci resistance
        if not tp_price:
            fib_str = ""
            filters = analysis_summary.get("filters", {})
            if isinstance(filters, dict):
                fib_str = filters.get("fib_4h", "") or filters.get("fib_1h", "")
            tp_price, tp_reason = self._parse_fib_resistance(fib_str, price)

        # Fallback: +15% fixed TP
        if not tp_price:
            tp_price = price * 1.15
            tp_reason = "fixed_15pct"

        # Ensure TP is above price
        if tp_price <= price:
            tp_price = price * 1.15
            tp_reason = "fixed_15pct"

        # TP MINIMUM FLOOR: 5% minimum (audit decision 25/03)
        # Dynamic TP from OB/Fib/VP can be too close (+0.2% to +1.7%)
        # This prevents involuntary scalping
        min_tp = price * 1.05
        if tp_price < min_tp:
            tp_price = min_tp
            tp_reason = f"min_5pct (was {tp_reason})"

        return sl_price, sl_reason, tp_price, tp_reason

    def _fixed_sl_tp(self, price: float) -> Tuple[float, str, float, str]:
        """Fallback fixed SL/TP."""
        return price * 0.92, "fixed_8pct", price * 1.15, "fixed_15pct"

    def _parse_ob_support(self, ob_str: str, price: float, label: str) -> Tuple[float, str]:
        """Parse OB string for support level below price.
        Format: '98.0-101.6 INSIDE 0.9% WEAK mitigated'
        """
        if not ob_str or not isinstance(ob_str, str):
            return 0, ""
        try:
            # Extract zone_low-zone_high
            match = re.match(r"([\d.]+)-([\d.]+)", ob_str)
            if match:
                zone_low = float(match.group(1))
                zone_high = float(match.group(2))
                # Use zone_low as support if it's below price
                if zone_low < price and zone_low > price * 0.85:
                    return zone_low, label
                # Also try zone_high as support if below price
                if zone_high < price and zone_high > price * 0.85:
                    return zone_high, label
        except Exception:
            pass
        return 0, ""

    def _parse_ob_resistance(self, ob_str: str, price: float, label: str) -> Tuple[float, str]:
        """Parse OB string for resistance level above price."""
        if not ob_str or not isinstance(ob_str, str):
            return 0, ""
        try:
            match = re.match(r"([\d.]+)-([\d.]+)", ob_str)
            if match:
                zone_high = float(match.group(2))
                if zone_high > price and zone_high < price * 1.30:
                    return zone_high, label
        except Exception:
            pass
        return 0, ""

    def _parse_vp_val(self, vp_str: str, price: float) -> Tuple[float, str]:
        """Parse VP string for VAL (Value Area Low) as support.
        Format: 'POC=96.374 VAH=99.806 VAL=95.438 pos=ABOVE_VAH 4.5%'
        """
        if not vp_str or not isinstance(vp_str, str):
            return 0, ""
        try:
            val_match = re.search(r"VAL=([\d.]+)", vp_str)
            if val_match:
                val = float(val_match.group(1))
                if val < price and val > price * 0.85:
                    return val, "VP_VAL"
        except Exception:
            pass
        return 0, ""

    def _parse_vp_resistance(self, vp_str: str, price: float) -> Tuple[float, str]:
        """Parse VP string for POC or VAH as resistance."""
        if not vp_str or not isinstance(vp_str, str):
            return 0, ""
        try:
            # Try VAH first (higher target)
            vah_match = re.search(r"VAH=([\d.]+)", vp_str)
            if vah_match:
                vah = float(vah_match.group(1))
                if vah > price and vah < price * 1.30:
                    return vah, "VP_VAH"

            # Try POC
            poc_match = re.search(r"POC=([\d.]+)", vp_str)
            if poc_match:
                poc = float(poc_match.group(1))
                if poc > price and poc < price * 1.30:
                    return poc, "VP_POC"
        except Exception:
            pass
        return 0, ""

    def _parse_fib_support(self, fib_str: str, price: float) -> Tuple[float, str]:
        """Parse Fib filter string for support levels.
        Looking for Fib retracement levels below price (0.382, 0.5, 0.618).
        """
        if not fib_str or not isinstance(fib_str, str):
            return 0, ""
        try:
            # Find all numeric values in the fib string
            numbers = re.findall(r"[\d]+\.[\d]+", fib_str)
            # Filter for values below price that could be support
            supports = []
            for n in numbers:
                val = float(n)
                if val < price and val > price * 0.85:
                    supports.append(val)
            if supports:
                # Use nearest support below price
                nearest = max(supports)
                return nearest, "Fib_support"
        except Exception:
            pass
        return 0, ""

    def _parse_fib_resistance(self, fib_str: str, price: float) -> Tuple[float, str]:
        """Parse Fib filter string for resistance levels above price."""
        if not fib_str or not isinstance(fib_str, str):
            return 0, ""
        try:
            numbers = re.findall(r"[\d]+\.[\d]+", fib_str)
            resistances = []
            for n in numbers:
                val = float(n)
                if val > price and val < price * 1.30:
                    resistances.append(val)
            if resistances:
                nearest = min(resistances)
                return nearest, "Fib_resistance"
        except Exception:
            pass
        return 0, ""

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _get_open_positions(self) -> List[Dict]:
        """Get all open positions from Supabase."""
        try:
            result = self.sb.table("openclaw_positions") \
                .select("*") \
                .eq("status", "OPEN") \
                .order("opened_at", desc=True) \
                .execute()
            return result.data or []
        except Exception as e:
            print(f"⚠️ Portfolio: get positions error: {e}")
            return []

    def get_closed_positions(self, limit: int = 50) -> List[Dict]:
        """Get closed positions (trade history)."""
        try:
            result = self.sb.table("openclaw_positions") \
                .select("*") \
                .eq("status", "CLOSED") \
                .order("closed_at", desc=True) \
                .limit(limit) \
                .execute()
            return result.data or []
        except Exception as e:
            return []

    async def _get_price(self, pair: str) -> Optional[float]:
        """Get current price from Binance."""
        try:
            r = await asyncio.to_thread(
                requests.get,
                f"{self.settings.binance_api_url}/api/v3/ticker/price",
                params={"symbol": pair}, timeout=5
            )
            return float(r.json().get("price", 0))
        except Exception:
            return None

    # ==================================================================
    # TELEGRAM NOTIFICATIONS
    # ==================================================================

    async def _notify_position_opened(self, pos: Dict, available_balance: float,
                                       position_count: int, rr_ratio: float):
        """Send Telegram notification for opened position."""
        if not self.telegram_bot or not self.telegram_bot.app:
            return

        entry = pos["entry_price"]
        sl = pos["sl_price"]
        tp = pos["tp_price"]
        sl_dist = (sl - entry) / entry * 100
        tp_dist = (tp - entry) / entry * 100
        conf_pct = pos["confidence"] * 100 if pos["confidence"] <= 1 else pos["confidence"]

        msg = (
            f"🟢 POSITION OUVERTE\n"
            f"📊 {pos['pair']} — {pos['decision']} ({conf_pct:.0f}%)\n\n"
            f"💰 Size: ${pos['size_usd']:.2f}\n"
            f"📈 Entry: ${entry:,.8g}\n"
            f"🛡️ SL: ${sl:,.8g} ({sl_dist:+.1f}%) [{pos['sl_reason']}]\n"
            f"🎯 TP: ${tp:,.8g} ({tp_dist:+.1f}%) [{pos['tp_reason']}]\n"
            f"📐 R:R: 1:{rr_ratio:.1f}\n\n"
            f"💼 Portfolio: ${available_balance:,.2f} dispo | {position_count}/{self.MAX_POSITIONS} positions"
        )

        try:
            await self.telegram_bot.app.bot.send_message(
                chat_id=self.telegram_bot.chat_id,
                text=msg
            )
        except Exception as e:
            print(f"⚠️ Portfolio Telegram error (open): {e}")

    async def _notify_position_closed(self, pos: Dict, exit_price: float,
                                       pnl_pct: float, pnl_usd: float,
                                       reason: str, new_balance: float,
                                       wins: int, losses: int, total_pnl: float):
        """Send Telegram notification for closed position."""
        if not self.telegram_bot or not self.telegram_bot.app:
            return

        is_win = pnl_pct > 0
        result_emoji = "✅" if is_win else "❌"
        result_label = "WIN" if is_win else "LOSE"
        wr = round(wins / (wins + losses) * 100) if (wins + losses) > 0 else 0

        # Calculate duration
        duration_str = ""
        opened_at = pos.get("opened_at", "")
        if opened_at:
            try:
                open_dt = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                delta = datetime.now(timezone.utc) - open_dt
                days = delta.days
                hours = delta.seconds // 3600
                if days > 0:
                    duration_str = f"{days}j {hours}h"
                else:
                    duration_str = f"{hours}h {(delta.seconds % 3600) // 60}m"
            except Exception:
                pass

        msg = (
            f"{result_emoji} POSITION FERMEE — {result_label}\n"
            f"📊 {pos['pair']} {pnl_pct:+.1f}% (${pnl_usd:+.2f})\n\n"
            f"💰 Entry: ${pos['entry_price']:,.8g} → Exit: ${exit_price:,.8g}\n"
        )
        if duration_str:
            msg += f"⏱️ Duree: {duration_str}\n"
        msg += (
            f"📈 Raison: {reason}\n\n"
            f"💼 Portfolio: ${new_balance:,.2f} | WR: {wr}% | PnL total: ${total_pnl:+.2f}"
        )

        try:
            await self.telegram_bot.app.bot.send_message(
                chat_id=self.telegram_bot.chat_id,
                text=msg
            )
        except Exception as e:
            print(f"⚠️ Portfolio Telegram error (close): {e}")
