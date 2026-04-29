#!/usr/bin/env python3
"""V11 system digest — comprehensive report covering all 5 variants.

Generates:
- Markdown text (for Telegram, condensed)
- HTML (for email, full detailed)

Sections:
1. Header: timestamp, BTC context, killswitch state summary
2. Per-variant state (WR, paper coverage, suspended status, open positions)
3. Closes in last 8h window (per-trade detail with PnL, reason, slippage if available)
4. Open positions (sorted by age, current PnL, time-to-timeout)
5. Paper P&L vs Backtest delta (when paper data available)
6. Killswitch events / BTC dump events in window
7. Risk metrics top-level summary

Usage:
    python3 scripts/digest_report.py [--window-hours N]
    Output: prints HTML to stdout, writes Markdown to /tmp/digest_md.txt
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from openclaw.config import get_settings
from openclaw.portfolio.gates_v11 import get_btc_change_24h, get_btc_dominance
from supabase import create_client
from _risk_metrics import compute_risk_metrics


VARIANTS = ("v11a", "v11b", "v11c", "v11d", "v11e")
VARIANT_LABEL = {
    "v11a": "Custom (continuation)",
    "v11b": "Compression (R30m+R4h)",
    "v11c": "Premium (R1h+BTC.D)",
    "v11d": "Accum Breakout",
    "v11e": "BB Squeeze 4H",
}


def fmt_age(hours: float) -> str:
    if hours < 1: return f"{int(hours*60)}min"
    if hours < 24: return f"{hours:.1f}h"
    days = int(hours // 24); rem = int(hours % 24)
    return f"{days}j{rem}h"


def parse_iso(s: str):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def collect_data(sb, window_h: float):
    """Collect everything needed for the digest in one pass."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=window_h)
    out = {"now": now, "cutoff": cutoff, "window_h": window_h, "variants": {}}

    for v in VARIANTS:
        st_r = sb.table(f"openclaw_portfolio_state_{v}").select("*").eq("id", "main").single().execute()
        state = st_r.data or {}

        pos_r = sb.table(f"openclaw_positions_{v}").select(
            "pair,entry_price,exit_price,size_usd,pnl_pct,pnl_usd,paper_entry_price,"
            "paper_slippage_pct,paper_pnl_pct,paper_pnl_usd,status,close_reason,opened_at,"
            "closed_at,partial1_done,partial2_done,trail_active,decision,confidence,"
            "remaining_size_pct,realized_pnl_usd"
        ).order("opened_at", desc=True).limit(2000).execute()
        rows = pos_r.data or []

        closes_window = [r for r in rows
                         if r.get("status") == "CLOSED"
                         and parse_iso(r.get("closed_at")) is not None
                         and parse_iso(r.get("closed_at")) >= cutoff]
        opens = [r for r in rows if r.get("status") == "OPEN"]
        all_closed = [r for r in rows if r.get("status") == "CLOSED"]

        # WR last 30 (killswitch criterion)
        last30 = sorted(all_closed, key=lambda x: x.get("closed_at") or "", reverse=True)[:30]
        wr_last30 = (sum(1 for r in last30 if (r.get("pnl_usd") or 0) > 0) / len(last30) * 100) if last30 else 0

        # Paper data coverage
        with_paper_pnl = [r for r in all_closed if r.get("paper_pnl_pct") is not None]

        out["variants"][v] = {
            "state": state, "rows_total": len(rows),
            "closes_window": closes_window, "opens": opens,
            "all_closed": all_closed,
            "wr_last30": wr_last30, "n_last30": len(last30),
            "with_paper_pnl": with_paper_pnl,
        }

    # BTC context
    out["btc_24h"] = get_btc_change_24h()
    out["btc_dominance"] = get_btc_dominance()

    return out


def _h(s) -> str:
    """HTML-escape for Telegram parse_mode=HTML."""
    if s is None: return ""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_markdown(data: dict) -> str:
    """Condensed HTML for Telegram (4096 char limit). parse_mode=HTML is more
    forgiving than Markdown — only &<> need escaping.
    Function name kept for API compat (used to be Markdown)."""
    now = data["now"]; window_h = data["window_h"]
    L = []
    L.append(f"📊 <b>V11 Digest — {_h(now.strftime('%Y-%m-%d %H:%M UTC'))}</b>")
    L.append(f"<i>Window: dernières {window_h:.0f}h</i>")
    btc = data.get("btc_24h")
    btc_str = f"{btc:+.2f}%" if btc is not None else "n/a"
    L.append(f"🪙 BTC 24h: <b>{_h(btc_str)}</b> | Dominance: {(f'{d:.1f}%' if (d := data.get('btc_dominance')) is not None else 'n/a')}")
    L.append("")

    # ━━━━━━━━━━ V11B FOCUS — variant principal ━━━━━━━━━━
    b = data["variants"]["v11b"]
    bst = b["state"]
    bn = bst.get("total_trades", 0); bw = bst.get("wins", 0); bl_ = bst.get("losses", 0)
    bwr = (bw / max(bn, 1)) * 100 if bn else 0
    b_paper_n = len(b["with_paper_pnl"])
    b_closes_w = len(b["closes_window"])
    b_pnl_w = sum((r.get("pnl_usd") or 0) for r in b["closes_window"])
    b_susp = bst.get("is_suspended")
    b_susp_emoji = "🛑 SUSPENDED" if b_susp else "✅ active"
    b_initial = bst.get("initial_capital", 5000)
    b_balance = bst.get("balance", 5000)
    b_total_pnl = bst.get("total_pnl", 0)
    b_return_pct = (b_total_pnl / b_initial * 100) if b_initial else 0
    b_dd = bst.get("max_drawdown_pct", 0)
    b_in_pos = sum(float(p.get("size_usd") or 0) * float(p.get("remaining_size_pct") or 1) for p in b["opens"])
    b_unrealized = sum(float(p.get("size_usd") or 0)
                       * float(p.get("remaining_size_pct") or 1)
                       * float(p.get("pnl_pct") or 0) / 100 for p in b["opens"])
    b_equity = b_balance + b_in_pos + b_unrealized
    b_partial_wins = sum(1 for p in b["opens"]
                         if p.get("partial1_done") or p.get("partial2_done"))
    b_wr_total = ((bw + b_partial_wins) / max(bn + b_partial_wins, 1)) * 100
    b_daily_loss = bst.get("daily_loss_today", 0)

    L.append("━━━━━ ⭐ <b>V11B Focus</b> (variant principal) ━━━━━")
    L.append(f"Status: <b>{b_susp_emoji}</b>")
    L.append(f"💰 Equity: <b>${b_equity:,.2f}</b>")
    L.append(f"   Balance: <b>${b_balance:,.2f}</b> (Initial ${b_initial:,.0f})")
    L.append(f"   PnL Total: <b>${b_total_pnl:+,.2f}</b> ({b_return_pct:+.2f}%)")
    L.append(f"   Non-realisé: <b>${b_unrealized:+,.2f}</b> ({len(b['opens'])} positions)")
    L.append(f"📊 WR Total: <b>{b_wr_total:.1f}%</b> "
             f"({bw + b_partial_wins}W/{bl_}L on {bn + b_partial_wins} +{b_partial_wins} TP)")
    L.append(f"   WR Fermés: <b>{bwr:.1f}%</b> ({bw}W/{bl_}L on {bn})")
    L.append(f"   WR last 30: <b>{b['wr_last30']:.1f}%</b> (seuil killswitch 70%)")
    L.append(f"📂 Positions: <b>{len(b['opens'])}/12</b> (${b_in_pos:,.0f} alloué)")
    L.append(f"🛡 Max DD: <b>{b_dd:.2f}%</b> | Perte jour: ${b_daily_loss:,.2f}")
    L.append(f"📉 Closes {window_h:.0f}h: <b>{b_closes_w}</b> "
             f"(${b_pnl_w:+,.0f}) | Paper: <b>{b_paper_n}/{bn}</b> "
             f"({b_paper_n/max(bn,1)*100:.0f}%)")
    # Phase 1 progress bar (vers le seuil N=50)
    if b_paper_n < 50:
        bar_len = 20
        filled = int(bar_len * min(b_paper_n / 50, 1))
        bar = "█" * filled + "░" * (bar_len - filled)
        L.append(f"Phase 1: <code>{bar}</code> {b_paper_n}/50 trades paper requis")
    else:
        # Compute delta WR if we have data
        with_paper = b["with_paper_pnl"]
        bt_w = sum(1 for r in with_paper if (r.get("pnl_usd") or 0) > 0)
        pp_w = sum(1 for r in with_paper if (r.get("paper_pnl_usd") or 0) > 0)
        bt_wr = bt_w / len(with_paper) * 100
        pp_wr = pp_w / len(with_paper) * 100
        d_wr = pp_wr - bt_wr
        if abs(d_wr) <= 8: verdict = "✅ PASS (≤8pts)"
        elif abs(d_wr) <= 10: verdict = "⚠️ WATCH (8-10pts)"
        else: verdict = "🛑 FAIL (>10pts)"
        L.append(f"Phase 1: <b>Δ WR {d_wr:+.1f}pts</b> "
                 f"(BT {bt_wr:.1f}% / Paper {pp_wr:.1f}%) — {verdict}")
    # V11B closes details if any in window
    if b_closes_w > 0:
        L.append(f"Closes V11B {window_h:.0f}h:")
        for r in b["closes_window"][:6]:
            pnl = r.get("pnl_usd") or 0
            emoji = "✅" if pnl > 0 else "❌"
            reason = (r.get("close_reason") or "?").split(":", 1)[-1]
            L.append(f"  {emoji} <code>{_h(r.get('pair'))}</code> "
                     f"{r.get('pnl_pct') or 0:+.1f}% (${pnl:+.1f}) — {_h(reason)}")
    if b_susp:
        L.append(f"⚠️ Raison suspension: {_h(bst.get('suspended_reason', '?'))}")
    L.append("")

    # ━━━━━━━━━━ Vue d'ensemble 5 variants (contexte) ━━━━━━━━━━
    n_suspended = sum(1 for v in VARIANTS if data["variants"][v]["state"].get("is_suspended"))
    total_closes_window = sum(len(data["variants"][v]["closes_window"]) for v in VARIANTS)
    total_opens = sum(len(data["variants"][v]["opens"]) for v in VARIANTS)
    L.append("━━━━━ Vue d'ensemble 5 variants ━━━━━")
    L.append(f"🛑 Suspended: <b>{n_suspended}/5</b> | "
             f"📉 Closes ({window_h:.0f}h): <b>{total_closes_window}</b> | "
             f"📂 Open: <b>{total_opens}</b>")
    L.append("")

    # Per-variant compact line
    for v in VARIANTS:
        d = data["variants"][v]
        st = d["state"]
        susp_emoji = "🛑" if st.get("is_suspended") else "✅"
        wr_overall = (st.get("wins", 0) / max(st.get("total_trades", 0), 1)) * 100
        n_w = len(d["closes_window"])
        pnl_w = sum((r.get("pnl_usd") or 0) for r in d["closes_window"])
        n_paper = len(d["with_paper_pnl"])
        line = (f"{susp_emoji} <b>{v.upper()}</b> — WR all: <b>{wr_overall:.1f}%</b> "
                f"({st.get('wins', 0)}/{st.get('total_trades', 0)}) | "
                f"WR-30: <b>{d['wr_last30']:.1f}%</b> | "
                f"Δ{window_h:.0f}h: {n_w} closes ${pnl_w:+.0f} | "
                f"Open: {len(d['opens'])} | Paper: {n_paper}")
        L.append(line)
    L.append("")

    # Closes detail (if any)
    if total_closes_window:
        L.append(f"━━━ Closes dans les {window_h:.0f}h ━━━")
        for v in VARIANTS:
            for r in data["variants"][v]["closes_window"][:5]:  # cap 5/variant
                pnl = r.get("pnl_usd") or 0
                emoji = "✅" if pnl > 0 else "❌"
                reason = (r.get("close_reason") or "?").split(":", 1)[-1]
                L.append(f"{emoji} {v.upper()} <code>{_h(r.get('pair'))}</code> {r.get('pnl_pct') or 0:+.1f}% "
                         f"(${pnl:+.1f}) — {_h(reason)}")

    # Killswitch alerts
    suspended_now = [v for v in VARIANTS if data["variants"][v]["state"].get("is_suspended")]
    if suspended_now:
        L.append("")
        L.append("━━━ ⚠️ Suspensions actives ━━━")
        for v in suspended_now:
            st = data["variants"][v]["state"]
            L.append(f"🛑 <b>{v.upper()}</b>: {_h(st.get('suspended_reason', '?'))}")

    return "\n".join(L)


def _v11b_focus_html(data: dict) -> list:
    """V11B-specific focus block — front-and-center since c'est le variant suivi.
    Stats alignés sur le dashboard /portfolio (Equity, Balance/Initial, PnL%,
    Non-realise, WR Total/Fermes, Positions, Max DD, Perte Jour)."""
    b = data["variants"]["v11b"]
    bst = b["state"]
    window_h = data["window_h"]
    bn = bst.get("total_trades", 0); bw = bst.get("wins", 0); bl_ = bst.get("losses", 0)
    bwr = (bw / max(bn, 1)) * 100 if bn else 0
    paper_rows = b["with_paper_pnl"]
    n_paper = len(paper_rows)
    n_window = len(b["closes_window"])
    pnl_window = sum((r.get("pnl_usd") or 0) for r in b["closes_window"])
    susp = bst.get("is_suspended")

    # Compute dashboard-equivalent stats
    initial = bst.get("initial_capital", 5000)
    balance = bst.get("balance", 5000)
    total_pnl = bst.get("total_pnl", 0)
    return_pct = (total_pnl / initial * 100) if initial else 0
    in_positions = sum(float(p.get("size_usd") or 0) * float(p.get("remaining_size_pct") or 1)
                       for p in b["opens"])
    unrealized = sum(float(p.get("size_usd") or 0)
                     * float(p.get("remaining_size_pct") or 1)
                     * float(p.get("pnl_pct") or 0) / 100 for p in b["opens"])
    equity = balance + in_positions + unrealized
    partial_wins = sum(1 for p in b["opens"]
                       if p.get("partial1_done") or p.get("partial2_done"))
    total_wins_with_partials = bw + partial_wins
    total_trades_with_partials = bn + partial_wins
    wr_total = (total_wins_with_partials / max(total_trades_with_partials, 1)) * 100
    max_pos = 12  # V11 base MAX_POSITIONS
    daily_loss = bst.get("daily_loss_today", 0)
    max_dd = bst.get("max_drawdown_pct", 0)
    drawdown_mode = bst.get("drawdown_mode", False)

    H = []
    # Big highlighted box
    bg_color = "#fef2f2" if susp else "#eff6ff"
    border_color = "#dc2626" if susp else "#0369a1"
    H.append(f"<div style='background:{bg_color};border:2px solid {border_color};border-radius:8px;padding:16px 20px;margin:20px 0'>")
    status_icon = "🛑" if susp else "⭐"
    status_label = "SUSPENDED" if susp else "ACTIVE"
    status_color = "#dc2626" if susp else "#15803d"
    H.append(f"<div style='display:flex;align-items:baseline;justify-content:space-between;flex-wrap:wrap;gap:8px'>")
    H.append(f"<h2 style='margin:0;color:{border_color};border:none;font-size:18px'>{status_icon} V11B Focus — variant principal</h2>")
    H.append(f"<span style='font-weight:700;color:{status_color}'>{status_label}</span>")
    H.append(f"</div>")

    if susp:
        H.append(f"<div style='margin-top:8px;padding:8px 12px;background:#ffffff;border-left:3px solid #dc2626;border-radius:3px;color:#991b1b'>")
        H.append(f"<b>Raison :</b> <code>{bst.get('suspended_reason', '?')}</code>")
        H.append(f"</div>")

    # Stats — match dashboard /portfolio exactly (4 rows × 3 cols)
    # Use <table> for reliable horizontal layout across ALL email clients
    cards = [
        ("Equity", f"${equity:,.2f}", None,
         "#15803d" if equity >= initial else "#b91c1c"),
        ("Balance", f"${balance:,.2f}", f"Initial: ${initial:,.2f}",
         "#0369a1"),
        ("PnL Total", f"${total_pnl:+,.2f}", f"{return_pct:+.2f}%",
         "#15803d" if total_pnl >= 0 else "#b91c1c"),
        ("Non-realisé", f"${unrealized:+,.2f}", f"{len(b['opens'])} positions",
         "#15803d" if unrealized >= 0 else "#b91c1c"),
        ("WR Total", f"{wr_total:.1f}%",
         f"{total_wins_with_partials}W/{bl_}L ({total_trades_with_partials}) +{partial_wins} TP",
         "#15803d" if wr_total >= 75 else "#a16207"),
        ("WR Fermés", f"{bwr:.1f}%", f"{bw}W/{bl_}L ({bn})",
         "#15803d" if bwr >= 75 else "#a16207"),
        ("Positions", f"{len(b['opens'])}/{max_pos}", f"${in_positions:,.0f} alloc",
         "#0369a1"),
        ("Max DD", f"{max_dd:.2f}%", "⚠️ ACTIF" if drawdown_mode else "OK",
         "#b91c1c" if max_dd > 10 else "#15803d"),
        ("Perte Jour", f"${daily_loss:,.2f}", "max 5%",
         "#b91c1c" if daily_loss > initial * 0.03 else "#6b7280"),
        (f"Closes {window_h:.0f}h", f"{n_window} (${pnl_window:+,.0f})", "réalisés window",
         "#15803d" if pnl_window >= 0 else "#b91c1c"),
        ("WR last 30", f"{b['wr_last30']:.1f}%", f"({b['n_last30']} trades) — seuil 70%",
         "#15803d" if b['wr_last30'] >= 75 else "#a16207" if b['wr_last30'] >= 70 else "#b91c1c"),
        ("Paper data", f"{n_paper}/{bn}", f"{n_paper/max(bn,1)*100:.0f}% couverture",
         "#15803d" if n_paper >= 50 else "#6b7280"),
    ]

    # Table layout — 3 columns × 4 rows. Tables = universal email compat.
    H.append("<table style='border-collapse:separate;border-spacing:8px;width:100%;margin-top:14px;border:none' cellpadding='0' cellspacing='0'>")
    for i in range(0, len(cards), 3):
        H.append("<tr>")
        for j in range(3):
            if i + j >= len(cards):
                H.append("<td style='width:33.33%;border:none'></td>")
                continue
            label, value, sub, color = cards[i + j]
            H.append(
                "<td style='width:33.33%;background:#f9fafb;border:1px solid #e5e7eb;"
                "border-radius:6px;padding:10px 12px;vertical-align:top'>"
            )
            H.append(
                f"<div style='font-size:10px;color:#6b7280;text-transform:uppercase;"
                f"letter-spacing:0.5px;font-weight:600'>{label}</div>"
            )
            H.append(
                f"<div style='font-size:18px;font-weight:bold;margin-top:3px;"
                f"color:{color}'>{value}</div>"
            )
            if sub:
                H.append(
                    f"<div style='font-size:11px;color:#6b7280;margin-top:3px'>{sub}</div>"
                )
            H.append("</td>")
        H.append("</tr>")
    H.append("</table>")

    # Phase 1 progress
    H.append("<h3 style='margin-top:14px;margin-bottom:6px'>Phase 1 — Critère go/no-go (Δ WR ≤ 8 pts)</h3>")
    if n_paper == 0:
        H.append("<p class='muted'><i>Pas encore de paper data accumulée. Le système attend les premiers nouveaux opens (les positions OPEN actuelles doivent d'abord se fermer).</i></p>")
    elif n_paper < 50:
        pct = n_paper / 50 * 100
        H.append(f"<div style='background:#f3f4f6;border-radius:6px;overflow:hidden;height:20px;position:relative'>")
        H.append(f"<div style='background:#0369a1;height:100%;width:{pct:.0f}%;transition:width 0.3s'></div>")
        H.append(f"</div>")
        H.append(f"<p class='muted' style='margin-top:6px;font-size:12px'>{n_paper} / 50 trades paper requis "
                 f"({pct:.0f}%) — collecte en cours</p>")
    else:
        bt_w = sum(1 for r in paper_rows if (r.get("pnl_usd") or 0) > 0)
        pp_w = sum(1 for r in paper_rows if (r.get("paper_pnl_usd") or 0) > 0)
        bt_wr = bt_w / n_paper * 100
        pp_wr = pp_w / n_paper * 100
        delta = pp_wr - bt_wr
        abs_d = abs(delta)
        if abs_d <= 8: verdict = ("✅ PASS", "#15803d", "#f0fdf4")
        elif abs_d <= 10: verdict = ("⚠️ WATCH", "#a16207", "#fef3c7")
        else: verdict = ("🛑 FAIL", "#b91c1c", "#fef2f2")
        H.append(f"<div style='background:{verdict[2]};padding:10px 14px;border-radius:6px;border-left:4px solid {verdict[1]}'>")
        H.append(f"<b style='color:{verdict[1]};font-size:15px'>{verdict[0]}</b> — Δ WR <b>{delta:+.1f} pts</b> "
                 f"(Backtest {bt_wr:.1f}% / Paper {pp_wr:.1f}%) sur {n_paper} trades")
        H.append("</div>")

    # Closes V11B in window — detailed
    if n_window > 0:
        H.append(f"<h3 style='margin-top:14px;margin-bottom:6px'>Closes V11B — dernières {window_h:.0f}h ({n_window} trades)</h3>")
        H.append("<table>")
        H.append("<tr><th>Pair</th><th>PnL %</th><th>PnL $</th><th>Reason</th><th>Hold</th><th>Slippage</th><th>Paper PnL</th></tr>")
        for r in b["closes_window"]:
            pnl = r.get("pnl_usd") or 0
            cls = "win" if pnl > 0 else "lose"
            reason = (r.get("close_reason") or "?").split(":", 1)[-1]
            opened = parse_iso(r.get("opened_at")); closed = parse_iso(r.get("closed_at"))
            hold = fmt_age((closed - opened).total_seconds() / 3600) if opened and closed else "—"
            slip = r.get("paper_slippage_pct")
            slip_str = f"{slip:+.3f}%" if slip is not None else "—"
            ppnl = r.get("paper_pnl_pct")
            ppnl_str = f"{ppnl:+.2f}%" if ppnl is not None else "<span class='muted'>—</span>"
            H.append(f"<tr><td><b>{r.get('pair')}</b></td>"
                     f"<td class='{cls}'>{r.get('pnl_pct') or 0:+.2f}%</td>"
                     f"<td class='{cls}'>${pnl:+,.2f}</td>"
                     f"<td><code>{reason}</code></td>"
                     f"<td>{hold}</td>"
                     f"<td>{slip_str}</td>"
                     f"<td>{ppnl_str}</td></tr>")
        H.append("</table>")

    # Open positions V11B summary
    if b["opens"]:
        H.append(f"<h3 style='margin-top:14px;margin-bottom:6px'>Positions ouvertes V11B ({len(b['opens'])})</h3>")
        H.append("<table>")
        H.append("<tr><th>Pair</th><th>Entry</th><th>PnL %</th><th>Hold</th><th>Time-to-timeout</th><th>TP1?</th><th>TP2?</th></tr>")
        for r in sorted(b["opens"], key=lambda x: x.get("opened_at", ""), reverse=False):
            pnl = r.get("pnl_pct") or 0
            cls = "win" if pnl > 0 else "lose"
            o = parse_iso(r.get("opened_at"))
            age_h = (data["now"] - o).total_seconds() / 3600 if o else 0
            ttt_h = max(0, 72 - age_h)
            ttt = fmt_age(ttt_h) if ttt_h > 0 else "TIMEOUT NOW"
            ttt_color = "lose" if ttt_h < 12 else "warn" if ttt_h < 24 else "muted"
            H.append(f"<tr><td><b>{r.get('pair')}</b></td>"
                     f"<td>${r.get('entry_price', 0):.6f}</td>"
                     f"<td class='{cls}'>{pnl:+.2f}%</td>"
                     f"<td>{fmt_age(age_h)}</td>"
                     f"<td class='{ttt_color}'>{ttt}</td>"
                     f"<td>{'✅' if r.get('partial1_done') else '—'}</td>"
                     f"<td>{'✅' if r.get('partial2_done') else '—'}</td></tr>")
        H.append("</table>")

    H.append("</div>")  # close focus box
    return H


def build_html(data: dict) -> str:
    """Full HTML for email — detailed, same depth as audit reports."""
    now = data["now"]; window_h = data["window_h"]
    H = []
    H.append("<!DOCTYPE html><html><head><meta charset='UTF-8'>")
    H.append("<style>")
    # Light theme for max email-client compatibility (Gmail/Outlook/mobile, light+dark mode)
    H.append("body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;background:#ffffff;color:#1f2937;padding:20px;max-width:1100px;margin:auto;font-size:14px;line-height:1.5}")
    H.append("h1{color:#0369a1;border-bottom:2px solid #bae6fd;padding-bottom:8px;margin-bottom:16px}")
    H.append("h2{color:#0c4a6e;margin-top:28px;border-bottom:1px solid #e5e7eb;padding-bottom:6px}")
    H.append("h3{color:#0369a1;font-size:14px;margin-top:18px}")
    H.append("table{border-collapse:collapse;width:100%;background:#ffffff;border:1px solid #e5e7eb;border-radius:6px;overflow:hidden;margin:8px 0}")
    H.append("th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #e5e7eb;font-size:13px}")
    H.append("th{background:#f3f4f6;color:#0369a1;font-weight:600}")
    H.append("tr:last-child td{border-bottom:none}")
    H.append("tr:hover{background:#f9fafb}")
    # Status colors — strong contrast on white
    H.append(".win{color:#15803d;font-weight:600}")
    H.append(".lose{color:#b91c1c;font-weight:600}")
    H.append(".warn{color:#a16207;font-weight:600}")
    H.append(".muted{color:#6b7280}")
    H.append(".banner-suspended{background:#fef2f2;border-left:4px solid #dc2626;padding:12px 16px;margin:12px 0;border-radius:4px;color:#991b1b}")
    H.append(".banner-ok{background:#f0fdf4;border-left:4px solid #16a34a;padding:12px 16px;margin:12px 0;border-radius:4px;color:#166534}")
    H.append("code{background:#f3f4f6;color:#1f2937;padding:1px 5px;border-radius:3px;font-size:12px;font-family:Menlo,Monaco,monospace}")
    H.append(".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin:8px 0}")
    H.append(".card{background:#f9fafb;border:1px solid #e5e7eb;border-radius:6px;padding:10px}")
    H.append(".card .label{font-size:10px;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;font-weight:600}")
    H.append(".card .value{font-size:18px;font-weight:bold;margin-top:2px;color:#1f2937}")
    H.append("</style></head><body>")

    H.append(f"<h1>📊 V11 System Digest — {now.strftime('%Y-%m-%d %H:%M UTC')}</h1>")
    H.append(f"<p class='muted'>Fenêtre: dernières {window_h:.0f}h • Couvre les 5 variants V11</p>")

    # Top banner — system health
    n_suspended = sum(1 for v in VARIANTS if data["variants"][v]["state"].get("is_suspended"))
    btc = data.get("btc_24h")
    btc_str = f"{btc:+.2f}%" if btc is not None else "n/a"
    if n_suspended > 0:
        suspended_list = [v.upper() for v in VARIANTS if data["variants"][v]["state"].get("is_suspended")]
        H.append(f"<div class='banner-suspended'><b>⚠️ {n_suspended}/5 variants suspendus :</b> {', '.join(suspended_list)}</div>")
    else:
        H.append("<div class='banner-ok'><b>✅ Tous les 5 variants opérationnels</b> — aucun killswitch déclenché</div>")

    dom_val = data.get('btc_dominance')
    dom_str = f"{dom_val:.1f}%" if dom_val is not None else "n/a"
    H.append(f"<p>🪙 BTC 24h: <b>{btc_str}</b> | Dominance: <b>{dom_str}</b></p>")

    # === V11B FOCUS — variant principal (avant la vue d'ensemble) ===
    H.extend(_v11b_focus_html(data))

    # === Section 1: Per-variant summary ===
    H.append("<h2>1. Vue d'ensemble — état des 5 variants</h2>")
    H.append("<table>")
    H.append("<tr><th>Variant</th><th>Filtre</th><th>Total trades</th><th>WR all-time</th>"
             "<th>WR last 30</th><th>Open</th><th>Closes (window)</th><th>PnL window</th>"
             "<th>Paper pnl rows</th><th>Status</th></tr>")
    for v in VARIANTS:
        d = data["variants"][v]; st = d["state"]
        total = st.get("total_trades", 0); w = st.get("wins", 0)
        wr_overall = (w / max(total, 1)) * 100 if total else 0
        wr_30 = d["wr_last30"]
        susp = st.get("is_suspended")
        n_w = len(d["closes_window"])
        pnl_w = sum((r.get("pnl_usd") or 0) for r in d["closes_window"])
        wr_color = "win" if wr_overall >= 75 else "warn" if wr_overall >= 60 else "lose"
        wr30_color = "win" if wr_30 >= 75 else "warn" if wr_30 >= 70 else "lose"
        status_html = "<span class='lose'>🛑 SUSPENDED</span>" if susp else "<span class='win'>✅ active</span>"
        pnl_color = "win" if pnl_w >= 0 else "lose"
        H.append(f"<tr><td><b>{v.upper()}</b></td><td>{VARIANT_LABEL[v]}</td>"
                 f"<td>{total}</td>"
                 f"<td class='{wr_color}'>{wr_overall:.1f}%</td>"
                 f"<td class='{wr30_color}'>{wr_30:.1f}%</td>"
                 f"<td>{len(d['opens'])}</td>"
                 f"<td>{n_w}</td>"
                 f"<td class='{pnl_color}'>${pnl_w:+,.2f}</td>"
                 f"<td>{len(d['with_paper_pnl'])}</td>"
                 f"<td>{status_html}</td></tr>")
    H.append("</table>")

    # === Section 2: Closes detailed in window ===
    total_closes = sum(len(data["variants"][v]["closes_window"]) for v in VARIANTS)
    H.append(f"<h2>2. Closes des {window_h:.0f}h dernières heures ({total_closes} trades)</h2>")
    if total_closes == 0:
        H.append("<p class='muted'><i>Aucune fermeture dans la fenêtre.</i></p>")
    else:
        H.append("<table>")
        H.append("<tr><th>Variant</th><th>Pair</th><th>Decision</th><th>PnL %</th><th>PnL $</th>"
                 "<th>Reason</th><th>Hold</th><th>Slippage</th><th>Paper PnL %</th><th>Closed at</th></tr>")
        all_closes = []
        for v in VARIANTS:
            for r in data["variants"][v]["closes_window"]:
                r["_variant"] = v
                all_closes.append(r)
        all_closes.sort(key=lambda r: r.get("closed_at") or "", reverse=True)
        for r in all_closes:
            pnl_pct = r.get("pnl_pct") or 0
            pnl_usd = r.get("pnl_usd") or 0
            cls = "win" if pnl_usd > 0 else "lose"
            opened = parse_iso(r.get("opened_at"))
            closed = parse_iso(r.get("closed_at"))
            hold = fmt_age((closed - opened).total_seconds() / 3600) if opened and closed else "—"
            reason = (r.get("close_reason") or "?").split(":", 1)[-1]
            slip = r.get("paper_slippage_pct")
            slip_str = f"{slip:+.3f}%" if slip is not None else "—"
            ppnl = r.get("paper_pnl_pct")
            ppnl_str = f"{ppnl:+.2f}%" if ppnl is not None else "<span class='muted'>—</span>"
            cl_short = (r.get("closed_at") or "")[:16].replace("T", " ")
            H.append(f"<tr><td><b>{r['_variant'].upper()}</b></td><td>{r.get('pair')}</td>"
                     f"<td>{r.get('decision', '')}</td>"
                     f"<td class='{cls}'>{pnl_pct:+.2f}%</td>"
                     f"<td class='{cls}'>${pnl_usd:+,.2f}</td>"
                     f"<td><code>{reason}</code></td>"
                     f"<td>{hold}</td>"
                     f"<td>{slip_str}</td>"
                     f"<td>{ppnl_str}</td>"
                     f"<td class='muted'>{cl_short}</td></tr>")
        H.append("</table>")

    # === Section 3: Open positions ===
    total_open = sum(len(data["variants"][v]["opens"]) for v in VARIANTS)
    H.append(f"<h2>3. Positions ouvertes ({total_open} actives)</h2>")
    if total_open == 0:
        H.append("<p class='muted'><i>Aucune position ouverte.</i></p>")
    else:
        H.append("<table>")
        H.append("<tr><th>Variant</th><th>Pair</th><th>Entry</th><th>PnL %</th>"
                 "<th>Hold</th><th>Time-to-timeout</th><th>TP1?</th><th>TP2?</th><th>Trail?</th></tr>")
        all_opens = []
        for v in VARIANTS:
            for r in data["variants"][v]["opens"]:
                r["_variant"] = v
                all_opens.append(r)
        # Sort by hold age desc (oldest first → most urgent for timeout)
        now_dt = data["now"]
        for r in all_opens:
            o = parse_iso(r.get("opened_at"))
            r["_age_h"] = (now_dt - o).total_seconds() / 3600 if o else 0
        all_opens.sort(key=lambda r: -r["_age_h"])
        for r in all_opens:
            pnl_pct = r.get("pnl_pct") or 0
            cls = "win" if pnl_pct > 0 else "lose"
            age = fmt_age(r["_age_h"])
            ttt = max(0, 72 - r["_age_h"])
            ttt_str = fmt_age(ttt) if ttt > 0 else "TIMEOUT NOW"
            ttt_color = "lose" if ttt < 12 else "warn" if ttt < 24 else "muted"
            H.append(f"<tr><td><b>{r['_variant'].upper()}</b></td><td>{r.get('pair')}</td>"
                     f"<td>${r.get('entry_price', 0):.6f}</td>"
                     f"<td class='{cls}'>{pnl_pct:+.2f}%</td>"
                     f"<td>{age}</td>"
                     f"<td class='{ttt_color}'>{ttt_str}</td>"
                     f"<td>{'✅' if r.get('partial1_done') else '—'}</td>"
                     f"<td>{'✅' if r.get('partial2_done') else '—'}</td>"
                     f"<td>{'✅' if r.get('trail_active') else '—'}</td></tr>")
        H.append("</table>")

    # === Section 4: Paper data status (per variant) ===
    H.append("<h2>4. Phase 1 — Paper trading instrumentation</h2>")
    has_any_paper = any(len(data["variants"][v]["with_paper_pnl"]) > 0 for v in VARIANTS)
    if not has_any_paper:
        H.append("<p class='muted'><i>Aucune paper data accumulée encore. Les positions doivent se fermer "
                 "puis de nouveaux opens doivent se produire pour générer la première mesure.</i></p>")
    else:
        H.append("<table>")
        H.append("<tr><th>Variant</th><th>Paper rows</th><th>Avg slippage</th><th>WR backtest</th>"
                 "<th>WR paper</th><th>Δ WR</th><th>Verdict</th></tr>")
        for v in VARIANTS:
            d = data["variants"][v]
            paper = d["with_paper_pnl"]
            if not paper:
                H.append(f"<tr><td><b>{v.upper()}</b></td><td>0</td><td colspan='5' class='muted'>Pas de data</td></tr>")
                continue
            slips = [r.get("paper_slippage_pct") for r in paper if r.get("paper_slippage_pct") is not None]
            avg_slip = sum(slips)/len(slips) if slips else 0
            bt_wins = sum(1 for r in paper if (r.get("pnl_usd") or 0) > 0)
            pp_wins = sum(1 for r in paper if (r.get("paper_pnl_usd") or 0) > 0)
            bt_wr = bt_wins/len(paper)*100
            pp_wr = pp_wins/len(paper)*100
            delta = pp_wr - bt_wr
            abs_delta = abs(delta)
            if abs_delta <= 8: verdict = "<span class='win'>✅ PASS</span>"
            elif abs_delta <= 10: verdict = "<span class='warn'>⚠️ WATCH</span>"
            else: verdict = "<span class='lose'>🛑 FAIL</span>"
            H.append(f"<tr><td><b>{v.upper()}</b></td><td>{len(paper)}</td>"
                     f"<td>{avg_slip:+.3f}%</td>"
                     f"<td>{bt_wr:.1f}%</td><td>{pp_wr:.1f}%</td>"
                     f"<td>{delta:+.1f}pts</td><td>{verdict}</td></tr>")
        H.append("</table>")

    # === Section 5: Risk metrics (V11B detail since it's the lead variant) ===
    v11b = data["variants"]["v11b"]
    if v11b["all_closed"]:
        rm = compute_risk_metrics(v11b["all_closed"], initial_capital=5000.0)
        H.append("<h2>5. Risk metrics — V11B (variant principal)</h2>")
        H.append("<div class='grid'>")
        for label, value, color in [
            ("Sharpe annualisé", f"{rm['sharpe_annualized']:.2f}", "win"),
            ("Profit Factor", f"{rm['profit_factor']:.2f}" if rm['profit_factor'] != float('inf') else "∞", "win"),
            ("Max DD", f"{rm['max_drawdown_pct']:.2f}%", "win" if rm['max_drawdown_pct'] < 5 else "warn"),
            ("Calmar", f"{rm['calmar_ratio']:.1f}" if rm['calmar_ratio'] != float('inf') else "∞", "win"),
            ("Max losing streak", f"{rm['max_consecutive_losses']}", "muted"),
            ("Max winning streak", f"{rm['max_consecutive_wins']}", "win"),
        ]:
            H.append(f"<div class='card'><div class='label'>{label}</div>"
                     f"<div class='value {color}'>{value}</div></div>")
        H.append("</div>")
        H.append("<p class='muted' style='font-size:11px;font-style:italic'>"
                 "⚠️ Sharpe annualisé théorique. En live un Sharpe 2-4 serait excellent. "
                 "Voir Profit Factor et Calmar pour des métriques plus interprétables.</p>")

    # === Section 6: Suspensions actives détail ===
    suspended_now = [v for v in VARIANTS if data["variants"][v]["state"].get("is_suspended")]
    if suspended_now:
        H.append("<h2>6. Suspensions actives — action requise</h2>")
        for v in suspended_now:
            st = data["variants"][v]["state"]
            H.append(f"<div class='banner-suspended'>")
            H.append(f"<b>🛑 {v.upper()} SUSPENDED</b><br>")
            H.append(f"Raison : <code>{st.get('suspended_reason', '?')}</code><br>")
            H.append(f"Depuis : <code>{st.get('suspended_at', '?')}</code><br>")
            H.append("Pour reprendre : bouton dans le dashboard /portfolio (V11x → bandeau rouge → ▶️ Reprendre)")
            H.append("</div>")

    H.append("<hr style='border:none;border-top:1px solid #e5e7eb;margin-top:30px'>")
    H.append(f"<p class='muted' style='font-size:11px'>Digest généré par <code>scripts/digest_report.py</code> "
             f"• Window {window_h:.0f}h • {now.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>")
    H.append("</body></html>")
    return "\n".join(H)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-hours", type=float, default=8.0,
                        help="Hours of activity to cover (default 8h, matches 3x/day cadence)")
    parser.add_argument("--out-md", default="/tmp/digest.md")
    parser.add_argument("--out-html", default="/tmp/digest.html")
    args = parser.parse_args()

    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print(f"📥 Collecting V11 data (window={args.window_hours}h)...", file=sys.stderr)
    data = collect_data(sb, args.window_hours)

    md = build_markdown(data)
    html = build_html(data)

    Path(args.out_md).write_text(md, encoding="utf-8")
    Path(args.out_html).write_text(html, encoding="utf-8")

    print(f"✅ Markdown: {args.out_md} ({len(md)} chars)", file=sys.stderr)
    print(f"✅ HTML: {args.out_html} ({len(html)} chars)", file=sys.stderr)

    # Stats summary
    n_closes = sum(len(data["variants"][v]["closes_window"]) for v in VARIANTS)
    n_open = sum(len(data["variants"][v]["opens"]) for v in VARIANTS)
    n_susp = sum(1 for v in VARIANTS if data["variants"][v]["state"].get("is_suspended"))
    print(f"📊 Closes ({args.window_hours}h): {n_closes} | Open: {n_open} | Suspended: {n_susp}/5",
          file=sys.stderr)


if __name__ == "__main__":
    main()
