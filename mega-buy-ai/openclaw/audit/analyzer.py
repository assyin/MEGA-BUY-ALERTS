"""Audit Analyzers — separated into Portfolio (real trades) and Decisions (tracker).

PortfolioAuditor: Analyzes the $5000 virtual trading portfolio
  - Real positions with SL/TP, entry/exit prices, PnL realise
  - Position sizing effectiveness
  - Dynamic SL/TP quality
  - R:R analysis per trade
  - Drawdown patterns

DecisionsAuditor: Analyzes the alert analysis quality
  - BUY/WATCH/SKIP decision accuracy
  - Missed BUY detection
  - PnL live vs PnL max (was the trade ever winning?)
  - Decision confidence calibration
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from collections import defaultdict

from openclaw.config import get_settings


class PortfolioAuditor:
    """Deep analysis of the $5000 virtual trading portfolio."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive portfolio audit."""
        positions = self._fetch_positions()
        state = self._fetch_state()

        closed = [p for p in positions if p.get("status") == "CLOSED"]
        open_pos = [p for p in positions if p.get("status") == "OPEN"]

        stats = {
            "portfolio": self._portfolio_overview(state, open_pos, closed),
            "closed_trades": self._closed_trades_analysis(closed),
            "open_positions": self._open_positions_analysis(open_pos),
            "sl_tp_quality": self._sl_tp_quality(closed),
            "position_sizing": self._position_sizing_analysis(closed, state),
            "pair_performance": self._pair_performance(closed),
            "timing": self._timing_analysis(closed),
            "risk_metrics": self._risk_metrics(closed, state),
            "decision_effectiveness": self._decision_vs_result(closed),
        }

        points = self._generate_points(stats, closed, open_pos)
        report = self._build_report(stats, points, closed, open_pos)

        return {"report": report, "points": points, "raw_stats": stats, "audit_type": "portfolio"}

    # ─── Data Fetch ──────────────────────────────────────────

    def _fetch_positions(self) -> List[Dict]:
        try:
            r = self.sb.table("openclaw_positions").select("*").order("opened_at", desc=True).limit(500).execute()
            return r.data or []
        except Exception as e:
            print(f"  Audit: positions error: {e}")
            return []

    def _fetch_state(self) -> Dict:
        try:
            r = self.sb.table("openclaw_portfolio_state").select("*").eq("id", "main").single().execute()
            return r.data or {}
        except Exception:
            return {"balance": 5000, "initial_capital": 5000, "total_pnl": 0, "wins": 0, "losses": 0, "total_trades": 0, "peak_balance": 5000, "max_drawdown_pct": 0}

    # ─── Analysis Methods ────────────────────────────────────

    def _portfolio_overview(self, state, open_pos, closed):
        balance = state.get("balance", 5000)
        initial = state.get("initial_capital", 5000)
        in_positions = sum(p.get("size_usd", 0) or 0 for p in open_pos)
        unrealized = sum(p.get("pnl_usd", 0) or 0 for p in open_pos)
        equity = balance + in_positions + unrealized
        return {
            "balance": balance, "initial": initial, "equity": equity,
            "in_positions": in_positions, "unrealized_pnl": unrealized,
            "realized_pnl": state.get("total_pnl", 0),
            "return_pct": round((equity - initial) / initial * 100, 2) if initial else 0,
            "total_trades": state.get("total_trades", 0),
            "wins": state.get("wins", 0), "losses": state.get("losses", 0),
            "wr": round(state.get("wins", 0) / state.get("total_trades", 1) * 100, 1) if state.get("total_trades", 0) > 0 else 0,
            "open_count": len(open_pos), "closed_count": len(closed),
            "max_drawdown": state.get("max_drawdown_pct", 0),
            "drawdown_mode": state.get("drawdown_mode", False),
        }

    def _closed_trades_analysis(self, closed):
        if not closed:
            return {"count": 0}
        wins = [p for p in closed if (p.get("pnl_pct") or 0) > 0]
        losses = [p for p in closed if (p.get("pnl_pct") or 0) <= 0]
        all_pnls = [p.get("pnl_pct", 0) or 0 for p in closed]
        all_usd = [p.get("pnl_usd", 0) or 0 for p in closed]
        win_pnls = [p.get("pnl_pct", 0) or 0 for p in wins]
        loss_pnls = [p.get("pnl_pct", 0) or 0 for p in losses]

        best = max(closed, key=lambda p: p.get("pnl_pct", 0) or 0)
        worst = min(closed, key=lambda p: p.get("pnl_pct", 0) or 0)

        return {
            "count": len(closed), "wins": len(wins), "losses": len(losses),
            "wr": round(len(wins) / len(closed) * 100, 1) if closed else 0,
            "total_pnl_usd": round(sum(all_usd), 2),
            "avg_pnl_pct": round(sum(all_pnls) / len(all_pnls), 2),
            "avg_win_pct": round(sum(win_pnls) / len(win_pnls), 2) if win_pnls else 0,
            "avg_loss_pct": round(sum(loss_pnls) / len(loss_pnls), 2) if loss_pnls else 0,
            "best_trade": f"{best.get('pair', '?')} +{best.get('pnl_pct', 0):.1f}% (${best.get('pnl_usd', 0):.1f})",
            "worst_trade": f"{worst.get('pair', '?')} {worst.get('pnl_pct', 0):.1f}% (${worst.get('pnl_usd', 0):.1f})",
            "profit_factor": round(abs(sum(p.get("pnl_usd", 0) or 0 for p in wins)) / abs(sum(p.get("pnl_usd", 0) or 0 for p in losses)), 2) if losses and sum(p.get("pnl_usd", 0) or 0 for p in losses) != 0 else 999,
            "trades_detail": [
                {"pair": p.get("pair"), "pnl_pct": round(p.get("pnl_pct", 0) or 0, 2), "pnl_usd": round(p.get("pnl_usd", 0) or 0, 2),
                 "decision": p.get("decision"), "close_reason": p.get("close_reason"),
                 "sl_reason": p.get("sl_reason"), "tp_reason": p.get("tp_reason"),
                 "entry": p.get("entry_price"), "exit": p.get("exit_price"),
                 "size": p.get("size_usd"), "duration_h": self._duration_hours(p)}
                for p in sorted(closed, key=lambda x: x.get("closed_at", ""), reverse=True)
            ],
        }

    def _open_positions_analysis(self, open_pos):
        if not open_pos:
            return {"count": 0, "positions": []}
        return {
            "count": len(open_pos),
            "total_allocated": round(sum(p.get("size_usd", 0) or 0 for p in open_pos), 2),
            "total_unrealized": round(sum(p.get("pnl_usd", 0) or 0 for p in open_pos), 2),
            "in_profit": len([p for p in open_pos if (p.get("pnl_pct") or 0) > 0]),
            "in_loss": len([p for p in open_pos if (p.get("pnl_pct") or 0) < 0]),
            "danger": len([p for p in open_pos if (p.get("pnl_pct") or 0) < -5]),
            "positions": [
                {"pair": p.get("pair"), "pnl_pct": round(p.get("pnl_pct", 0) or 0, 2),
                 "pnl_usd": round(p.get("pnl_usd", 0) or 0, 2), "size": p.get("size_usd"),
                 "decision": p.get("decision"), "sl": p.get("sl_price"), "tp": p.get("tp_price"),
                 "sl_reason": p.get("sl_reason"), "tp_reason": p.get("tp_reason"),
                 "entry": p.get("entry_price"), "hours_open": self._duration_hours(p)}
                for p in sorted(open_pos, key=lambda x: x.get("pnl_pct", 0) or 0, reverse=True)
            ],
        }

    def _sl_tp_quality(self, closed):
        tp_hits = [p for p in closed if p.get("close_reason") == "TP_HIT"]
        sl_hits = [p for p in closed if p.get("close_reason") == "SL_HIT"]

        # Analyze if TP was too tight (low PnL wins)
        tight_tp = [p for p in tp_hits if (p.get("pnl_pct") or 0) < 3]
        good_tp = [p for p in tp_hits if (p.get("pnl_pct") or 0) >= 5]

        # Analyze SL reasons
        sl_reasons = defaultdict(int)
        for p in sl_hits:
            sl_reasons[p.get("sl_reason", "unknown")] += 1

        tp_reasons = defaultdict(int)
        for p in tp_hits:
            tp_reasons[p.get("tp_reason", "unknown")] += 1

        return {
            "tp_hits": len(tp_hits), "sl_hits": len(sl_hits),
            "tp_avg_pnl": round(sum(p.get("pnl_pct", 0) or 0 for p in tp_hits) / len(tp_hits), 2) if tp_hits else 0,
            "sl_avg_pnl": round(sum(p.get("pnl_pct", 0) or 0 for p in sl_hits) / len(sl_hits), 2) if sl_hits else 0,
            "tight_tp_count": len(tight_tp), "good_tp_count": len(good_tp),
            "tp_ratio": round(len(tp_hits) / len(sl_hits), 2) if sl_hits else 999,
            "sl_reasons": dict(sl_reasons), "tp_reasons": dict(tp_reasons),
            "tight_tp_examples": [f"{p.get('pair')} +{p.get('pnl_pct', 0):.1f}% TP={p.get('tp_reason')}" for p in tight_tp[:5]],
        }

    def _position_sizing_analysis(self, closed, state):
        by_decision = defaultdict(lambda: {"sizes": [], "pnls": [], "count": 0})
        for p in closed:
            dec = p.get("decision", "?")
            by_decision[dec]["sizes"].append(p.get("size_usd", 0) or 0)
            by_decision[dec]["pnls"].append(p.get("pnl_usd", 0) or 0)
            by_decision[dec]["count"] += 1

        result = {}
        for dec, data in by_decision.items():
            avg_size = sum(data["sizes"]) / len(data["sizes"]) if data["sizes"] else 0
            total_pnl = sum(data["pnls"])
            result[dec] = {"avg_size": round(avg_size, 2), "total_pnl": round(total_pnl, 2), "count": data["count"]}

        return result

    def _pair_performance(self, closed):
        by_pair = defaultdict(lambda: {"wins": 0, "losses": 0, "pnls": [], "pnl_usd": []})
        for p in closed:
            pair = p.get("pair", "?")
            pnl = p.get("pnl_pct", 0) or 0
            by_pair[pair]["pnls"].append(pnl)
            by_pair[pair]["pnl_usd"].append(p.get("pnl_usd", 0) or 0)
            if pnl > 0:
                by_pair[pair]["wins"] += 1
            else:
                by_pair[pair]["losses"] += 1

        result = {}
        for pair, data in by_pair.items():
            total = data["wins"] + data["losses"]
            result[pair] = {
                "total": total, "wins": data["wins"], "losses": data["losses"],
                "wr": round(data["wins"] / total * 100, 1) if total else 0,
                "avg_pnl": round(sum(data["pnls"]) / len(data["pnls"]), 2),
                "total_pnl_usd": round(sum(data["pnl_usd"]), 2),
            }
        return dict(sorted(result.items(), key=lambda x: x[1]["total_pnl_usd"], reverse=True))

    def _timing_analysis(self, closed):
        """When do trades perform best?"""
        by_hour = defaultdict(lambda: {"count": 0, "wins": 0, "pnl_sum": 0})
        durations = []
        for p in closed:
            hours = self._duration_hours(p)
            if hours:
                durations.append(hours)
            opened = p.get("opened_at", "")
            if opened:
                try:
                    h = datetime.fromisoformat(opened.replace("Z", "+00:00")).hour
                    by_hour[h]["count"] += 1
                    by_hour[h]["pnl_sum"] += (p.get("pnl_pct", 0) or 0)
                    if (p.get("pnl_pct", 0) or 0) > 0:
                        by_hour[h]["wins"] += 1
                except Exception:
                    pass

        return {
            "avg_duration_hours": round(sum(durations) / len(durations), 1) if durations else 0,
            "min_duration": round(min(durations), 1) if durations else 0,
            "max_duration": round(max(durations), 1) if durations else 0,
            "best_hours": sorted([(h, d) for h, d in by_hour.items() if d["count"] >= 2], key=lambda x: x[1]["wins"] / max(x[1]["count"], 1), reverse=True)[:3],
        }

    def _risk_metrics(self, closed, state):
        sorted_trades = sorted(closed, key=lambda x: x.get("closed_at", ""))
        max_consec_loss = 0
        current_streak = 0
        equity_curve = [state.get("initial_capital", 5000)]
        for p in sorted_trades:
            pnl = p.get("pnl_usd", 0) or 0
            equity_curve.append(equity_curve[-1] + pnl)
            if (p.get("pnl_pct", 0) or 0) < 0:
                current_streak += 1
                max_consec_loss = max(max_consec_loss, current_streak)
            else:
                current_streak = 0

        peak = max(equity_curve) if equity_curve else 5000
        trough = min(equity_curve) if equity_curve else 5000
        max_dd_usd = peak - trough

        return {
            "max_consecutive_losses": max_consec_loss,
            "max_drawdown_usd": round(max_dd_usd, 2),
            "max_drawdown_pct": state.get("max_drawdown_pct", 0),
            "current_equity": equity_curve[-1] if equity_curve else 5000,
            "peak_equity": round(peak, 2),
        }

    def _decision_vs_result(self, closed):
        """How does each BUY level perform in portfolio?"""
        by_dec = defaultdict(lambda: {"wins": 0, "losses": 0, "pnl_usd": 0, "count": 0})
        for p in closed:
            dec = p.get("decision", "?")
            by_dec[dec]["count"] += 1
            by_dec[dec]["pnl_usd"] += (p.get("pnl_usd", 0) or 0)
            if (p.get("pnl_pct", 0) or 0) > 0:
                by_dec[dec]["wins"] += 1
            else:
                by_dec[dec]["losses"] += 1

        for dec, data in by_dec.items():
            data["wr"] = round(data["wins"] / data["count"] * 100, 1) if data["count"] else 0
        return dict(by_dec)

    def _duration_hours(self, p):
        opened = p.get("opened_at", "")
        closed_at = p.get("closed_at", "")
        if not opened:
            return 0
        try:
            start = datetime.fromisoformat(opened.replace("Z", "+00:00"))
            end = datetime.fromisoformat(closed_at.replace("Z", "+00:00")) if closed_at else datetime.now(timezone.utc)
            return round((end - start).total_seconds() / 3600, 1)
        except Exception:
            return 0

    # ─── Points Generation ───────────────────────────────────

    def _generate_points(self, stats, closed, open_pos):
        points = []
        pid = 0

        # Check for unmet engagements from previous audits
        try:
            from openclaw.audit.engagements import EngagementTracker
            tracker = EngagementTracker()
            unmet = [e for e in tracker.get_all() if e.get("status") in ("NOT_RESPECTED", "EXPIRED")]
            if unmet:
                pid += 1
                unmet_list = "\n".join([f"  - {e['title']} (deadline: {e.get('deadline','?')}, status: {e['status']})" for e in unmet])
                points.append({
                    "id": pid,
                    "title": f"Engagements non-respectes ({len(unmet)})",
                    "evidence": f"Les engagements suivants n'ont pas ete tenus:\n{unmet_list}",
                    "recommendation": "OpenClaw doit expliquer pourquoi et proposer un nouveau plan.",
                    "priority": 10,
                })
        except Exception:
            pass

        ct = stats["closed_trades"]
        overview = stats["portfolio"]
        sl_tp = stats["sl_tp_quality"]
        risk = stats["risk_metrics"]
        sizing = stats["position_sizing"]
        dec_eff = stats["decision_effectiveness"]

        # 1. Portfolio Performance
        if ct.get("count", 0) > 0:
            pid += 1
            points.append({"id": pid, "title": "Performance Globale du Portfolio",
                "evidence": f"Capital: ${overview['initial']:.0f} → Equity: ${overview['equity']:.0f} (return {overview['return_pct']:+.1f}%). "
                    f"WR: {ct['wr']:.1f}% ({ct['wins']}W/{ct['losses']}L sur {ct['count']} trades). "
                    f"Profit Factor: {ct['profit_factor']:.2f}. PnL total: ${ct['total_pnl_usd']:+.2f}. "
                    f"Avg WIN: +{ct['avg_win_pct']:.1f}% | Avg LOSE: {ct['avg_loss_pct']:.1f}%. "
                    f"Meilleur: {ct['best_trade']}. Pire: {ct['worst_trade']}.",
                "recommendation": "Evaluer si le WR et le Profit Factor sont acceptables pour continuer avec la strategie actuelle.",
                "priority": 9})

        # 2. SL/TP Quality
        if sl_tp["tp_hits"] + sl_tp["sl_hits"] > 0:
            pid += 1
            tight = sl_tp["tight_tp_count"]
            total_tp = sl_tp["tp_hits"]
            points.append({"id": pid, "title": "Qualite des SL/TP Dynamiques",
                "evidence": f"TP touches: {sl_tp['tp_hits']} (avg +{sl_tp['tp_avg_pnl']:.1f}%). SL touches: {sl_tp['sl_hits']} (avg {sl_tp['sl_avg_pnl']:.1f}%). "
                    f"Ratio TP/SL: {sl_tp['tp_ratio']:.2f}. "
                    f"TP trop serres (<3%): {tight}/{total_tp}. TP bons (>5%): {sl_tp['good_tp_count']}/{total_tp}. "
                    f"Raisons SL: {json.dumps(sl_tp['sl_reasons'])}. Raisons TP: {json.dumps(sl_tp['tp_reasons'])}."
                    + (f"\nExemples TP serres: {', '.join(sl_tp['tight_tp_examples'])}" if sl_tp['tight_tp_examples'] else ""),
                "recommendation": "Si beaucoup de TP serres (<3%), augmenter le TP minimum. Analyser si les niveaux techniques (OB, Fib, VP) sont pertinents.",
                "priority": 8 if tight > total_tp * 0.5 else 5})

        # 3. Drawdown & Risk
        if risk["max_drawdown_pct"] > 5:
            pid += 1
            points.append({"id": pid, "title": "Gestion du Risque et Drawdown",
                "evidence": f"Max drawdown: {risk['max_drawdown_pct']:.1f}% (${risk['max_drawdown_usd']:.0f}). "
                    f"Pertes consecutives max: {risk['max_consecutive_losses']}. "
                    f"Peak equity: ${risk['peak_equity']:.0f}. Equity actuelle: ${risk['current_equity']:.0f}."
                    + (f" MODE DRAWDOWN ACTIF — tailles reduites 50%." if overview['drawdown_mode'] else ""),
                "recommendation": "Evaluer les regles de drawdown. Considerer un SL plus large ou une reduction progressive des tailles.",
                "priority": 9 if risk["max_drawdown_pct"] > 15 else 7})

        # 4. Position Sizing
        if sizing:
            pid += 1
            sizing_detail = " | ".join([f"{dec}: avg ${d['avg_size']:.0f}, PnL ${d['total_pnl']:+.1f} ({d['count']} trades)" for dec, d in sizing.items()])
            points.append({"id": pid, "title": "Efficacite du Position Sizing",
                "evidence": f"Par type de decision: {sizing_detail}.",
                "recommendation": "Verifier si BUY STRONG justifie des tailles plus grandes. Ajuster si un type de decision perd plus qu'il ne gagne.",
                "priority": 6})

        # 5. Pair performance
        pair_perf = stats["pair_performance"]
        bad_pairs = {k: v for k, v in pair_perf.items() if v["total"] >= 2 and v["wr"] < 40}
        best_pairs = {k: v for k, v in pair_perf.items() if v["total"] >= 2 and v["wr"] >= 70}
        if bad_pairs:
            pid += 1
            bad_detail = "\n".join([f"  {p}: {d['wr']:.0f}% WR ({d['wins']}W/{d['losses']}L) PnL ${d['total_pnl_usd']:+.1f}" for p, d in bad_pairs.items()])
            points.append({"id": pid, "title": "Paires a Probleme dans le Portfolio",
                "evidence": f"Paires avec WR < 40% (min 2 trades):\n{bad_detail}",
                "recommendation": f"Considerer blacklister: {', '.join(bad_pairs.keys())}.",
                "priority": 8})
        if best_pairs:
            pid += 1
            best_detail = "\n".join([f"  {p}: {d['wr']:.0f}% WR ({d['wins']}W/{d['losses']}L) PnL ${d['total_pnl_usd']:+.1f}" for p, d in best_pairs.items()])
            points.append({"id": pid, "title": "Paires Stars du Portfolio",
                "evidence": f"Paires avec WR >= 70% (min 2 trades):\n{best_detail}",
                "recommendation": "Augmenter la taille de position ou prioriser ces paires.",
                "priority": 5})

        # 6. Decision effectiveness
        if dec_eff:
            pid += 1
            dec_detail = " | ".join([f"{dec}: WR {d['wr']:.0f}% PnL ${d['pnl_usd']:+.1f} ({d['count']} trades)" for dec, d in dec_eff.items()])
            points.append({"id": pid, "title": "Efficacite BUY STRONG vs BUY vs BUY WEAK",
                "evidence": f"Performance par niveau de decision: {dec_detail}.",
                "recommendation": "Si BUY WEAK performe mieux que BUY STRONG, revoir les criteres de confiance.",
                "priority": 7})

        # 7. Open positions health
        open_stats = stats["open_positions"]
        if open_stats["count"] > 0 and open_stats.get("danger", 0) > 0:
            pid += 1
            danger_list = [p for p in open_stats["positions"] if p["pnl_pct"] < -5]
            danger_str = ", ".join([f"{p['pair']} {p['pnl_pct']:+.1f}%" for p in danger_list])
            points.append({"id": pid, "title": "Positions Ouvertes en Danger",
                "evidence": f"{open_stats['danger']} position(s) en danger (<-5%): {danger_str}. "
                    f"Total alloue: ${open_stats['total_allocated']:.0f}. PnL non-realise: ${open_stats['total_unrealized']:+.1f}.",
                "recommendation": "Evaluer si ces positions doivent etre fermees manuellement ou si le SL va les proteger.",
                "priority": 8})

        points.sort(key=lambda p: -p["priority"])
        return points

    # ─── Report Building ─────────────────────────────────────

    def _build_report(self, stats, points, closed, open_pos):
        o = stats["portfolio"]
        ct = stats["closed_trades"]
        op = stats["open_positions"]
        sl = stats["sl_tp_quality"]
        risk = stats["risk_metrics"]
        timing = stats["timing"]

        lines = [
            "# 📊 Audit Portfolio OpenClaw — Trading $5,000",
            f"*Genere le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
            "## 💰 Vue d'Ensemble",
            f"| Metrique | Valeur |",
            f"|----------|--------|",
            f"| Capital Initial | ${o['initial']:,.0f} |",
            f"| Equity Actuelle | ${o['equity']:,.2f} |",
            f"| Return | {o['return_pct']:+.2f}% |",
            f"| PnL Realise | ${o['realized_pnl']:+.2f} |",
            f"| PnL Non-Realise | ${o['unrealized_pnl']:+.2f} |",
            f"| Win Rate | {o['wr']:.1f}% ({o['wins']}W / {o['losses']}L) |",
            f"| Profit Factor | {ct.get('profit_factor', 0):.2f} |",
            f"| Max Drawdown | {o['max_drawdown']:.1f}% |",
            f"| Positions Ouvertes | {o['open_count']} (${o['in_positions']:,.0f} alloue) |",
            f"| Trades Clotures | {o['closed_count']} |\n",
        ]

        if ct.get("count", 0) > 0:
            lines.extend([
                "## 📈 Trades Clotures",
                f"- Meilleur: {ct['best_trade']}",
                f"- Pire: {ct['worst_trade']}",
                f"- Avg WIN: +{ct['avg_win_pct']:.1f}% | Avg LOSE: {ct['avg_loss_pct']:.1f}%",
                f"- Duree moyenne: {timing['avg_duration_hours']:.0f}h (min {timing['min_duration']:.0f}h, max {timing['max_duration']:.0f}h)\n",
                "| Paire | PnL% | PnL$ | Decision | Raison | Duree |",
                "|-------|------|------|----------|--------|-------|",
            ])
            for t in ct["trades_detail"][:15]:
                lines.append(f"| {t['pair']} | {t['pnl_pct']:+.1f}% | ${t['pnl_usd']:+.1f} | {t['decision']} | {t['close_reason']} | {t['duration_h']:.0f}h |")
            lines.append("")

        if sl["tp_hits"] + sl["sl_hits"] > 0:
            lines.extend([
                "## 🎯 Qualite SL/TP",
                f"- TP touches: {sl['tp_hits']} (avg +{sl['tp_avg_pnl']:.1f}%)",
                f"- SL touches: {sl['sl_hits']} (avg {sl['sl_avg_pnl']:.1f}%)",
                f"- TP trop serres (<3%): {sl['tight_tp_count']}/{sl['tp_hits']}",
                f"- Ratio TP/SL: {sl['tp_ratio']:.2f}\n",
            ])

        if op["count"] > 0:
            lines.extend(["## ⏳ Positions Ouvertes",
                f"| Paire | PnL% | PnL$ | Decision | SL | TP | Heures |",
                "|-------|------|------|----------|----|----|--------|"])
            for p in op["positions"]:
                lines.append(f"| {p['pair']} | {p['pnl_pct']:+.1f}% | ${p['pnl_usd']:+.1f} | {p['decision']} | {p.get('sl_reason','')} | {p.get('tp_reason','')} | {p['hours_open']:.0f}h |")
            lines.append("")

        lines.extend([f"\n## 📋 Points a Discuter ({len(points)})\n"])
        for pt in points:
            prio = "🔴 CRITIQUE" if pt["priority"] >= 8 else "🟡 IMPORTANT" if pt["priority"] >= 6 else "🟢 INFO"
            lines.extend([f"### Point #{pt['id']}: {pt['title']} [{prio}]",
                f"**Evidence**: {pt['evidence']}", f"**Recommandation**: {pt['recommendation']}\n"])

        return "\n".join(lines)


class DecisionsAuditor:
    """Analyzes the quality of OpenClaw's BUY/WATCH/SKIP decisions (tracker)."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive decisions audit."""
        decisions = self._fetch_decisions()

        stats = {
            "overview": self._overview(decisions),
            "wr_by_decision": self._wr_by_decision(decisions),
            "missed_buys": self._missed_buys_analysis(decisions),
            "pnl_max_analysis": self._pnl_max_analysis(decisions),
            "confidence_calibration": self._confidence_calibration(decisions),
            "pair_frequency": self._pair_frequency(decisions),
        }

        points = self._generate_points(stats, decisions)
        report = self._build_report(stats, points)
        return {"report": report, "points": points, "raw_stats": stats, "audit_type": "decisions"}

    def _fetch_decisions(self):
        try:
            r = self.sb.table("agent_memory").select("*").order("timestamp", desc=True).limit(1000).execute()
            return r.data or []
        except Exception:
            return []

    def _overview(self, decisions):
        from collections import Counter
        dec_counts = Counter(d.get("agent_decision", "?") for d in decisions)
        outcome_counts = Counter(d.get("outcome", "null") for d in decisions)
        return {"total": len(decisions), "decisions": dict(dec_counts), "outcomes": dict(outcome_counts)}

    def _wr_by_decision(self, decisions):
        by_type = defaultdict(lambda: {"wins": 0, "losses": 0, "total": 0, "pnl_sum": 0})
        for d in decisions:
            if d.get("outcome") in ("WIN", "LOSE"):
                dec = d.get("agent_decision", "?")
                by_type[dec]["total"] += 1
                by_type[dec]["pnl_sum"] += (d.get("pnl_pct") or 0)
                if d["outcome"] == "WIN":
                    by_type[dec]["wins"] += 1
                else:
                    by_type[dec]["losses"] += 1
        for data in by_type.values():
            data["wr"] = round(data["wins"] / data["total"] * 100, 1) if data["total"] else 0
            data["avg_pnl"] = round(data["pnl_sum"] / data["total"], 2) if data["total"] else 0
        return dict(by_type)

    def _missed_buys_analysis(self, decisions):
        missed = [d for d in decisions if d.get("outcome") == "MISSED_BUY"]
        from collections import Counter
        pairs = Counter(d.get("pair", "?") for d in missed)
        return {
            "count": len(missed),
            "total_missed_pnl": round(sum(d.get("pnl_pct", 0) or 0 for d in missed), 1),
            "top_pairs": dict(pairs.most_common(5)),
            "examples": [{"pair": d.get("pair"), "pnl": d.get("pnl_pct"), "was": d.get("agent_decision")} for d in missed[:10]],
        }

    def _pnl_max_analysis(self, decisions):
        """Analyze PnL Max vs PnL Live — trades that WERE winning but now losing."""
        was_winning_now_losing = []
        for d in decisions:
            pnl_max = d.get("pnl_max")
            pnl_live = d.get("pnl_pct")
            if pnl_max and pnl_live and pnl_max > 5 and pnl_live < 0:
                was_winning_now_losing.append({
                    "pair": d.get("pair"), "pnl_max": pnl_max, "pnl_live": pnl_live,
                    "decision": d.get("agent_decision"), "diff": round(pnl_max - pnl_live, 1),
                })
        return {
            "count": len(was_winning_now_losing),
            "examples": sorted(was_winning_now_losing, key=lambda x: -x["diff"])[:10],
        }

    def _confidence_calibration(self, decisions):
        """Is high confidence = high WR?"""
        buckets = {"high_conf": {"wins": 0, "total": 0}, "med_conf": {"wins": 0, "total": 0}, "low_conf": {"wins": 0, "total": 0}}
        for d in decisions:
            if d.get("outcome") not in ("WIN", "LOSE"):
                continue
            conf = d.get("agent_confidence") or 0
            if conf >= 0.7:
                bucket = "high_conf"
            elif conf >= 0.5:
                bucket = "med_conf"
            else:
                bucket = "low_conf"
            buckets[bucket]["total"] += 1
            if d["outcome"] == "WIN":
                buckets[bucket]["wins"] += 1
        for b in buckets.values():
            b["wr"] = round(b["wins"] / b["total"] * 100, 1) if b["total"] else 0
        return buckets

    def _pair_frequency(self, decisions):
        from collections import Counter
        pairs = Counter(d.get("pair", "?") for d in decisions)
        return dict(pairs.most_common(10))

    def _generate_points(self, stats, decisions):
        points = []
        pid = 0

        # Check for unmet engagements from previous audits
        try:
            from openclaw.audit.engagements import EngagementTracker
            tracker = EngagementTracker()
            unmet = [e for e in tracker.get_all() if e.get("status") in ("NOT_RESPECTED", "EXPIRED")]
            if unmet:
                pid += 1
                unmet_list = "\n".join([f"  - {e['title']} (deadline: {e.get('deadline','?')}, status: {e['status']})" for e in unmet])
                points.append({
                    "id": pid,
                    "title": f"Engagements non-respectes ({len(unmet)})",
                    "evidence": f"Les engagements suivants n'ont pas ete tenus:\n{unmet_list}",
                    "recommendation": "OpenClaw doit expliquer pourquoi et proposer un nouveau plan.",
                    "priority": 10,
                })
        except Exception:
            pass

        # 1. Missed buys
        mb = stats["missed_buys"]
        if mb["count"] > 0:
            pid += 1
            examples = ", ".join([f"{e['pair']} +{e['pnl']:.0f}% (was {e['was']})" for e in mb["examples"][:5]])
            points.append({"id": pid, "title": f"Missed BUY — {mb['count']} trades rates",
                "evidence": f"{mb['count']} WATCH/SKIP qui ont fait +10% ou plus. Total rate: +{mb['total_missed_pnl']:.0f}%. "
                    f"Paires les plus ratees: {json.dumps(mb['top_pairs'])}. Exemples: {examples}",
                "recommendation": "Baisser le seuil de confiance pour ces paires recurrentes. Ajouter comme paires prioritaires.",
                "priority": 8})

        # 2. PnL Max analysis
        pma = stats["pnl_max_analysis"]
        if pma["count"] > 0:
            pid += 1
            examples = ", ".join([f"{e['pair']} max +{e['pnl_max']:.0f}% → now {e['pnl_live']:+.0f}%" for e in pma["examples"][:5]])
            points.append({"id": pid, "title": f"Trades qui ETAIENT gagnants — {pma['count']} retournes",
                "evidence": f"{pma['count']} trades qui ont atteint +5% ou plus mais sont maintenant en perte. Exemples: {examples}",
                "recommendation": "Implementer un trailing stop ou un take-profit partiel pour securiser les gains.",
                "priority": 8})

        # 3. Confidence calibration
        cal = stats["confidence_calibration"]
        pid += 1
        points.append({"id": pid, "title": "Calibration de la Confiance",
            "evidence": f"High conf (>=70%): WR {cal['high_conf']['wr']:.0f}% ({cal['high_conf']['total']} trades). "
                f"Med conf (50-69%): WR {cal['med_conf']['wr']:.0f}% ({cal['med_conf']['total']} trades). "
                f"Low conf (<50%): WR {cal['low_conf']['wr']:.0f}% ({cal['low_conf']['total']} trades).",
            "recommendation": "Si haute confiance != haute WR, recalibrer les criteres de confiance.",
            "priority": 7})

        # 4. WR by decision
        wr = stats["wr_by_decision"]
        if wr:
            pid += 1
            detail = " | ".join([f"{d}: WR {v['wr']:.0f}% avg {v['avg_pnl']:+.1f}% ({v['total']})" for d, v in wr.items()])
            points.append({"id": pid, "title": "Performance par Type de Decision",
                "evidence": detail,
                "recommendation": "Ajuster les seuils si un type sous-performe systematiquement.",
                "priority": 6})

        points.sort(key=lambda p: -p["priority"])
        return points

    def _build_report(self, stats, points):
        o = stats["overview"]
        wr = stats["wr_by_decision"]
        mb = stats["missed_buys"]

        lines = [
            "# 🤖 Audit Decisions OpenClaw — Tracker Alertes",
            f"*Genere le {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*\n",
            "## 📊 Vue d'Ensemble",
            f"- Total decisions: {o['total']}",
            f"- Distribution: {json.dumps(o['decisions'])}",
            f"- Outcomes: {json.dumps(o['outcomes'])}\n",
            "## 📈 Win Rate par Decision",
        ]
        for dec, data in sorted(wr.items()):
            lines.append(f"- **{dec}**: WR {data['wr']:.0f}% ({data['wins']}W/{data['losses']}L, avg {data['avg_pnl']:+.1f}%)")

        lines.extend([f"\n## 🚨 Missed BUY: {mb['count']}",
            f"- Total PnL rate: +{mb['total_missed_pnl']:.0f}%",
            f"- Paires: {json.dumps(mb['top_pairs'])}\n",
            f"## 📋 Points a Discuter ({len(points)})\n"])

        for pt in points:
            prio = "🔴 CRITIQUE" if pt["priority"] >= 8 else "🟡 IMPORTANT" if pt["priority"] >= 6 else "🟢 INFO"
            lines.extend([f"### Point #{pt['id']}: {pt['title']} [{prio}]",
                f"**Evidence**: {pt['evidence']}", f"**Recommandation**: {pt['recommendation']}\n"])

        return "\n".join(lines)
