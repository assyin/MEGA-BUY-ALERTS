"""V11 portfolio managers — discovery-driven filters with V7 hybrid TP.

Same exit logic as V7 (TP1 50%@+10% / TP2 30%@+20% / Trail 20% peak-8% / SL -8% / 72h timeout).
Only the entry gate differs. 5 variants share a base class + thin subclasses.
"""

import asyncio
import uuid
import time
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional

from openclaw.config import get_settings
from openclaw.portfolio.gates_v11 import GATES, get_btc_change_24h


# BTC dump Telegram dedup: don't spam — 60s between same (variant, trigger) messages.
# Per-event console logging is unaffected; this only gates Telegram sends.
_BTC_TG_LAST_SENT: Dict[str, float] = {}
_BTC_TG_DEDUP_S = 60.0


def _should_send_btc_tg(variant: str, trigger: str) -> bool:
    key = f"{variant}:{trigger}"
    now = time.time()
    if now - _BTC_TG_LAST_SENT.get(key, 0) >= _BTC_TG_DEDUP_S:
        _BTC_TG_LAST_SENT[key] = now
        return True
    return False


class _PortfolioV11Base:
    """Base for all V11x variants. Subclasses must set VARIANT, GATE_FUNC, TABLE, STATE_TABLE, LABEL."""

    INITIAL_CAPITAL = 5000.0
    MAX_POSITIONS = 12
    MAX_PER_PAIR = 1
    SIZE_PCT = 8.0
    SL_PCT = 8.0
    TP1_PCT = 10.0
    TP1_CLOSE_FRAC = 0.50
    TP2_PCT = 20.0
    TP2_CLOSE_FRAC = 0.30
    TRAIL_DIST_PCT = 8.0
    TIMEOUT_H = 72

    # BTC dump protection (layered) — see V11B_PRE_IMPL_CHECKS_2026-04-28.md
    BTC_HARD_STOP_PCT = -5.0   # if BTC 24h <= this → reject all opens (any state)
    BTC_SOFT_CAP_PCT = -3.0    # if BTC 24h <= this AND open >= threshold → reject
    BTC_SOFT_CAP_OPEN_THRESHOLD = 6  # # of open positions that activates soft cap

    # Paper trading slippage tracker (Reco #5 Phase 1) — observational only
    PAPER_DELAY_S = 60       # seconds after alert to fetch "realistic" entry price
    PAPER_ENABLE = True      # turn off to disable shadow logging

    # Phase 2 killswitch — auto-suspend on WR degradation (Reco #5 Phase 2)
    KILLSWITCH_ENABLE = True
    KILLSWITCH_LOOKBACK_N = 30      # last N closed trades to evaluate
    KILLSWITCH_WR_THRESHOLD = 0.70  # suspend if WR(last N) < this

    # Subclass attrs:
    VARIANT = ""        # 'v11a' .. 'v11e'
    LABEL = ""
    TABLE = ""
    STATE_TABLE = ""

    def __init__(self, telegram_bot=None):
        self.settings = get_settings()
        self.telegram_bot = telegram_bot
        self._running = False
        self._task = None
        from supabase import create_client
        self.sb = create_client(self.settings.supabase_url, self.settings.supabase_service_key)
        self._ensure_state()
        self.gate_func, self.label = GATES.get(self.VARIANT, (None, "?"))

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
            print(f"⚠️ {self.VARIANT.upper()} state init: {e}")

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
        if not self.telegram_bot:
            return
        try:
            await self.telegram_bot.app.bot.send_message(
                chat_id=self.telegram_bot.chat_id, text=text, parse_mode="Markdown"
            )
        except Exception:
            try:
                await self.telegram_bot.app.bot.send_message(chat_id=self.telegram_bot.chat_id, text=text)
            except Exception:
                pass

    # ===== OPEN =====

    async def try_open_position(self, pair: str, decision: str, confidence: float,
                                 alert: Dict, vip: Optional[Dict] = None,
                                 quality: Optional[Dict] = None,
                                 v11_cache: Optional[Dict] = None) -> Optional[Dict]:
        if "BUY" not in decision:
            return None

        # Killswitch — block if portfolio is suspended (manual resume only)
        if self._is_suspended():
            print(f"💼 {self.VARIANT.upper()} SUSPENDED — open blocked: {pair}")
            return None

        # Build cache if not provided (lazy fallback)
        if v11_cache is None:
            from openclaw.portfolio.gates_v11 import build_v11_cache
            v11_cache = await asyncio.to_thread(build_v11_cache, pair)

        if not self.gate_func:
            return None

        passed, reason = self.gate_func(alert, v11_cache)
        if not passed:
            print(f"💼 {self.VARIANT.upper()} GATE REJECT {pair}: {reason}")
            return None

        # Build gate_snapshot — immutable record of what passed the filter
        gate_snapshot = self._build_gate_snapshot(alert, v11_cache)

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
        if any(p.get("pair") == pair for p in open_positions):
            return None

        # BTC dump protection (layered: hard stop + soft cap)
        if not await self._btc_dump_check_ok(pair, len(open_positions)):
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
            "entry_price": price, "current_price": price, "size_usd": size_usd,
            "sl_price": sl, "tp1_price": tp1, "tp2_price": tp2,
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
            "partial1_done": False, "partial2_done": False,
            "trail_active": False, "trail_stop": sl,
            "realized_pnl_usd": 0.0, "remaining_size_pct": 1.0,
            "gate_snapshot": gate_snapshot,
        }

        try:
            self.sb.table(self.TABLE).insert(position).execute()
        except Exception as e:
            print(f"⚠️ {self.VARIANT.upper()} insert: {e}")
            return None

        self._update_state({"balance": round(balance - size_usd, 2)})
        print(f"💼 {self.VARIANT.upper()} OPENED: {pair} — {confidence*100:.0f}% — ${size_usd:.0f} @ {price}")

        # Schedule paper-trading slippage capture (best-effort, non-blocking)
        if self.PAPER_ENABLE:
            asyncio.create_task(self._log_paper_entry(position["id"], pair, price))

        await self._tg(
            f"🆕 *{self.VARIANT.upper()} OPEN* — `{pair}`\n"
            f"_{self.label}_\n"
            f"💰 Size: *${size_usd:.0f}* @ `{price}`\n"
            f"🎯 TP1=`{tp1}` (+10%/50%) / TP2=`{tp2}` (+20%/30%) / Trail 8%\n"
            f"🛡 SL: `{sl}` (-8%)"
        )
        return position

    # ===== CHECK / CLOSE — copied from V7 logic =====

    async def check_positions(self):
        positions = self._get_open_positions()
        if not positions:
            return

        now = datetime.now(timezone.utc)
        checked = closed = 0

        for pos in positions:
            pair = pos.get("pair", "")
            if not pair: continue
            price = await self._get_price(pair)
            if not price: continue
            entry = pos.get("entry_price", 0)
            if not entry: continue

            highest = max(pos.get("highest_price", price), price)
            size_usd = pos.get("size_usd", 0)
            partial1 = pos.get("partial1_done", False)
            partial2 = pos.get("partial2_done", False)
            trail_active = pos.get("trail_active", False)
            trail_stop = pos.get("trail_stop", pos.get("sl_price", 0))
            realized = pos.get("realized_pnl_usd", 0.0)
            remaining_pct = pos.get("remaining_size_pct", 1.0)

            updates: Dict = {}

            # Stop check
            if price <= trail_stop:
                exit_pct = (trail_stop - entry) / entry * 100
                exit_usd = size_usd * remaining_pct * exit_pct / 100
                final_realized = realized + exit_usd
                reason = "TRAIL_STOP" if trail_active else ("BREAKEVEN_STOP" if partial1 else "SL_HIT")
                await self._close_full(pos, trail_stop, reason, final_realized, remaining_pct)
                closed += 1
                continue

            # TP1
            tp1 = pos.get("tp1_price", 0)
            if not partial1 and tp1 and price >= tp1:
                profit_usd = size_usd * self.TP1_CLOSE_FRAC * self.TP1_PCT / 100
                realized += profit_usd
                remaining_pct -= self.TP1_CLOSE_FRAC
                partial1 = True
                trail_stop = entry  # SL → BE
                state = self.get_portfolio_state()
                bal = state.get("balance", 0) + (size_usd * self.TP1_CLOSE_FRAC) + profit_usd
                tp_total = state.get("total_pnl", 0) + profit_usd
                self._update_state({"balance": round(bal, 2), "total_pnl": round(tp_total, 2)})
                print(f"💼 {self.VARIANT.upper()} TP1 ✅: {pair} +{self.TP1_PCT}% (${profit_usd:+.1f}) — SL→BE")
                await self._tg(
                    f"🎯 *{self.VARIANT.upper()} TP1* — `{pair}` — sold 50% @ +{self.TP1_PCT}%\n"
                    f"💰 Profit: *${profit_usd:+.2f}* — SL→BE"
                )
                updates.update({
                    "partial1_done": True, "trail_stop": trail_stop,
                    "realized_pnl_usd": round(realized, 2),
                    "remaining_size_pct": round(remaining_pct, 4),
                })

            # TP2
            tp2 = pos.get("tp2_price", 0)
            if partial1 and not partial2 and tp2 and price >= tp2:
                profit_usd = size_usd * self.TP2_CLOSE_FRAC * self.TP2_PCT / 100
                realized += profit_usd
                remaining_pct -= self.TP2_CLOSE_FRAC
                partial2 = True
                trail_active = True
                trail_stop = round(highest * (1 - self.TRAIL_DIST_PCT / 100), 8)
                state = self.get_portfolio_state()
                bal = state.get("balance", 0) + (size_usd * self.TP2_CLOSE_FRAC) + profit_usd
                tp_total = state.get("total_pnl", 0) + profit_usd
                self._update_state({"balance": round(bal, 2), "total_pnl": round(tp_total, 2)})
                print(f"💼 {self.VARIANT.upper()} TP2 ✅✅: {pair} +{self.TP2_PCT}% — Trail active")
                await self._tg(
                    f"🎯🎯 *{self.VARIANT.upper()} TP2* — `{pair}` — sold 30% @ +{self.TP2_PCT}%\n"
                    f"💎 Realized: *${realized:.2f}* | 🔄 Trail 8% on remaining 20%"
                )
                updates.update({
                    "partial2_done": True, "trail_active": True,
                    "trail_stop": trail_stop,
                    "realized_pnl_usd": round(realized, 2),
                    "remaining_size_pct": round(remaining_pct, 4),
                })

            # Update trailing stop after TP2
            if trail_active:
                new_trail = round(highest * (1 - self.TRAIL_DIST_PCT / 100), 8)
                if new_trail > trail_stop:
                    trail_stop = new_trail
                    updates["trail_stop"] = trail_stop

            # Timeout
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
            print(f"💼 {self.VARIANT.upper()} check: {checked} updated, {closed} closed ({len(positions)} open)")

    async def _close_full(self, pos: Dict, exit_price: float, reason: str,
                          total_realized_pnl: float, remaining_pct: float):
        entry = pos.get("entry_price", 0)
        size = pos.get("size_usd", 0)
        pnl_pct = (total_realized_pnl / size * 100) if size else 0
        is_win = total_realized_pnl > 0

        # Phase 1 paper P&L (simple, no partials propagation — Phase 3 sujet).
        # Compares "if entry was at paper_entry, sell at exit_price" — used for
        # the delta WR backtest-vs-paper go/no-go criterion. Observational only.
        paper_entry = pos.get("paper_entry_price")
        paper_pnl_pct = None
        paper_pnl_usd = None
        if paper_entry and float(paper_entry) > 0 and exit_price and size:
            paper_pnl_pct = (exit_price - float(paper_entry)) / float(paper_entry) * 100
            paper_pnl_usd = size * paper_pnl_pct / 100

        update_payload = {
            "status": "CLOSED", "exit_price": exit_price, "current_price": exit_price,
            "close_reason": reason,
            "pnl_pct": round(pnl_pct, 2),
            "pnl_usd": round(total_realized_pnl, 2),
            "realized_pnl_usd": round(total_realized_pnl, 2),
            "remaining_size_pct": 0,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        if paper_pnl_pct is not None:
            update_payload["paper_pnl_pct"] = round(paper_pnl_pct, 2)
            update_payload["paper_pnl_usd"] = round(paper_pnl_usd, 2)
        try:
            self.sb.table(self.TABLE).update(update_payload).eq("id", pos["id"]).execute()
        except:
            return

        state = self.get_portfolio_state()
        prev_realized = pos.get("realized_pnl_usd", 0.0)
        last_leg_pnl = total_realized_pnl - prev_realized
        bal = state.get("balance", 0) + (size * remaining_pct) + last_leg_pnl
        tp = state.get("total_pnl", 0) + last_leg_pnl
        tt = state.get("total_trades", 0) + 1
        w = state.get("wins", 0) + (1 if is_win else 0)
        l = state.get("losses", 0) + (0 if is_win else 1)
        # Peak equity = INITIAL_CAPITAL + max running total_pnl. Compare equity-vs-equity
        # (pas peak_balance vs total_pnl — bug fixé 2026-04-29 qui produisait DD=99% sur V11B).
        equity = self.INITIAL_CAPITAL + tp
        peak_equity = max(state.get("peak_balance", self.INITIAL_CAPITAL), equity)
        dd = ((peak_equity - equity) / peak_equity * 100) if peak_equity > 0 else 0
        self._update_state({
            "balance": round(bal, 2),
            "total_pnl": round(tp, 2),
            "total_trades": tt, "wins": w, "losses": l,
            "peak_balance": round(peak_equity, 2),
            "max_drawdown_pct": round(max(state.get("max_drawdown_pct", 0), dd), 2),
        })
        print(f"💼 {self.VARIANT.upper()} {'✅' if is_win else '❌'}: {pos['pair']} {pnl_pct:+.1f}% — {reason}")
        wr = (w / tt * 100) if tt else 0
        await self._tg(
            f"{'✅' if is_win else '❌'} *{self.VARIANT.upper()} CLOSE* — `{pos['pair']}` — *{reason}*\n"
            f"💰 PnL: *{pnl_pct:+.2f}%* (*${total_realized_pnl:+.2f}*) | "
            f"Bal: *${bal:.0f}* | WR: *{wr:.1f}%*"
        )

        # Phase 2 killswitch — re-evaluate after each close (only if not already suspended)
        if self.KILLSWITCH_ENABLE and not state.get("is_suspended", False):
            await self._evaluate_killswitch()

    def _is_suspended(self) -> bool:
        """Read suspended flag from state (cheap, single SELECT)."""
        if not self.KILLSWITCH_ENABLE:
            return False
        try:
            r = self.sb.table(self.STATE_TABLE).select("is_suspended").eq("id", "main").single().execute()
            return bool((r.data or {}).get("is_suspended", False))
        except Exception:
            return False  # fail-open: prefer trading over freezing on transient DB errors

    async def _evaluate_killswitch(self):
        """Suspend portfolio if WR on last N closed trades drops below threshold.
        Called after each close. No-op if already suspended.
        """
        try:
            r = self.sb.table(self.TABLE).select("pnl_usd,closed_at").eq(
                "status", "CLOSED"
            ).order("closed_at", desc=True).limit(self.KILLSWITCH_LOOKBACK_N).execute()
            recent = r.data or []
            if len(recent) < self.KILLSWITCH_LOOKBACK_N:
                return  # not enough sample yet
            wins = sum(1 for x in recent if (x.get("pnl_usd") or 0) > 0)
            wr = wins / len(recent)
            if wr >= self.KILLSWITCH_WR_THRESHOLD:
                return  # healthy
            # Trigger suspension
            reason = f"WR {wr*100:.1f}% < {self.KILLSWITCH_WR_THRESHOLD*100:.0f}% on last {self.KILLSWITCH_LOOKBACK_N} closes"
            self._update_state({
                "is_suspended": True,
                "suspended_at": datetime.now(timezone.utc).isoformat(),
                "suspended_reason": reason,
            })
            print(f"🛑 {self.VARIANT.upper()} SUSPENDED — {reason}")
            await self._tg(
                f"🛑 *{self.VARIANT.upper()} SUSPENDED* — auto killswitch\n"
                f"WR last {self.KILLSWITCH_LOOKBACK_N}: *{wr*100:.1f}%* (seuil {self.KILLSWITCH_WR_THRESHOLD*100:.0f}%)\n"
                f"_{wins}W / {len(recent)-wins}L_\n"
                f"Aucun nouvel open jusqu'à reprise manuelle (dashboard ou SQL)."
            )
        except Exception as e:
            print(f"⚠️ {self.VARIANT.upper()} killswitch eval: {e}")

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        print(f"💼 {self.VARIANT.upper()} Portfolio started — {self.label}")

    async def _check_loop(self):
        while self._running:
            try:
                await self.check_positions()
            except Exception as e:
                print(f"⚠️ {self.VARIANT.upper()}: {e}")
            await asyncio.sleep(60)

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
        print(f"💼 {self.VARIANT.upper()} stopped")

    async def _log_paper_entry(self, position_id: str, pair: str, alert_price: float):
        """Reco #5 Phase 1 — capture realistic execution price after PAPER_DELAY_S.

        Observational only: writes paper_entry_price + paper_slippage_pct on the
        position row. Never affects exit logic. Slippage > 0 = price drifted up
        after alert (worse fill); slippage < 0 = price came back down (better fill).
        """
        try:
            await asyncio.sleep(self.PAPER_DELAY_S)
            paper_price = await self._get_price(pair)
            if not paper_price or not alert_price:
                return
            slippage_pct = (paper_price - alert_price) / alert_price * 100
            self.sb.table(self.TABLE).update({
                "paper_entry_price": paper_price,
                "paper_slippage_pct": round(slippage_pct, 4),
                "paper_logged_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", position_id).execute()
            print(f"💼 {self.VARIANT.upper()} PAPER {pair}: alert={alert_price} paper={paper_price} slip={slippage_pct:+.3f}%")
        except Exception as e:
            # Best-effort: paper logging failures must never crash the bot
            print(f"⚠️ {self.VARIANT.upper()} paper log {pair}: {e}")

    async def _btc_dump_check_ok(self, pair: str, n_open: int) -> bool:
        """Layered BTC dump protection. Returns False if open should be skipped.
        - Hard stop: BTC 24h <= -5% → block any new entry
        - Soft cap:  BTC 24h <= -3% AND n_open >= threshold → block to avoid concentration
        Logs to console always; sends one Telegram per (variant, trigger) per dedup window.
        """
        btc_24h = await asyncio.to_thread(get_btc_change_24h)
        if btc_24h is None:
            return True  # fail-open if API unavailable — better miss a guard than freeze entries

        # Hard stop
        if btc_24h <= self.BTC_HARD_STOP_PCT:
            print(f"💼 {self.VARIANT.upper()} BTC HARD STOP {pair}: btc_24h={btc_24h:+.2f}% <= {self.BTC_HARD_STOP_PCT}% (open={n_open})")
            if _should_send_btc_tg(self.VARIANT, "hard_stop"):
                await self._tg(
                    f"🛑 *{self.VARIANT.upper()} BTC HARD STOP*\n"
                    f"BTC 24h: *{btc_24h:+.2f}%* (≤ {self.BTC_HARD_STOP_PCT}%)\n"
                    f"Open positions: *{n_open}*\n"
                    f"All new entries blocked until BTC > {self.BTC_HARD_STOP_PCT}%"
                )
            return False

        # Soft cap
        if btc_24h <= self.BTC_SOFT_CAP_PCT and n_open >= self.BTC_SOFT_CAP_OPEN_THRESHOLD:
            print(f"💼 {self.VARIANT.upper()} BTC SOFT CAP {pair}: btc_24h={btc_24h:+.2f}% <= {self.BTC_SOFT_CAP_PCT}% & open={n_open} >= {self.BTC_SOFT_CAP_OPEN_THRESHOLD}")
            if _should_send_btc_tg(self.VARIANT, "soft_cap"):
                await self._tg(
                    f"⚠️ *{self.VARIANT.upper()} BTC SOFT CAP*\n"
                    f"BTC 24h: *{btc_24h:+.2f}%* (≤ {self.BTC_SOFT_CAP_PCT}%)\n"
                    f"Open positions: *{n_open}* (≥ {self.BTC_SOFT_CAP_OPEN_THRESHOLD})\n"
                    f"New entries paused — concentration risk too high"
                )
            return False

        return True

    def _build_gate_snapshot(self, alert: Dict, cache: Dict) -> Dict:
        """Capture the exact values that passed the gate (immutable audit trail)."""
        snap = {
            "variant": self.VARIANT,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "source": "live",
        }
        # Common fields useful across all variants
        for key in ("candle_15m_range_pct", "candle_30m_range_pct",
                    "candle_1h_range_pct", "candle_4h_range_pct",
                    "candle_4h_body_pct", "candle_4h_direction",
                    "bb_4h_width_pct", "btc_dominance"):
            if key in cache and cache[key] is not None:
                snap[key] = cache[key]
        # Accumulation (V11d)
        acc = cache.get("accumulation") or {}
        if acc.get("days") is not None:
            snap["accumulation_days"] = acc.get("days")
            snap["accumulation_hours"] = acc.get("hours")
        # V11A specific (DI/RSI/STC come from alert directly)
        if self.VARIANT == "v11a":
            for k in ("di_plus_4h", "di_minus_4h", "adx_4h", "rsi", "pp", "ec"):
                if alert.get(k) is not None:
                    snap[k] = alert.get(k)
            for k in ("stc_15m", "stc_30m", "stc_1h"):
                if alert.get(k) is not None:
                    snap[k] = alert.get(k)
        return snap


# ─── 5 concrete subclasses ───────────────────────────────────

class PortfolioManagerV11A(_PortfolioV11Base):
    VARIANT = "v11a"
    TABLE = "openclaw_positions_v11a"
    STATE_TABLE = "openclaw_portfolio_state_v11a"

class PortfolioManagerV11B(_PortfolioV11Base):
    VARIANT = "v11b"
    TABLE = "openclaw_positions_v11b"
    STATE_TABLE = "openclaw_portfolio_state_v11b"
    # Optimum from train/test split on 199 trades: TP2=13% (train) / 14% (test) — Δ=1pt → STABLE
    # See V11B_PRE_IMPL_CHECKS_2026-04-28.md §2. Keeps a 3pt margin above TP1=10%.
    TP2_PCT = 13.0

class PortfolioManagerV11C(_PortfolioV11Base):
    VARIANT = "v11c"
    TABLE = "openclaw_positions_v11c"
    STATE_TABLE = "openclaw_portfolio_state_v11c"

class PortfolioManagerV11D(_PortfolioV11Base):
    VARIANT = "v11d"
    TABLE = "openclaw_positions_v11d"
    STATE_TABLE = "openclaw_portfolio_state_v11d"

class PortfolioManagerV11E(_PortfolioV11Base):
    VARIANT = "v11e"
    TABLE = "openclaw_positions_v11e"
    STATE_TABLE = "openclaw_portfolio_state_v11e"
