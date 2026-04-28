"""Risk metrics for V11B audit reports.

compute_risk_metrics(rows) — pure function over a list of CLOSED trade dicts.
render_md / render_html — formatters with the Sharpe caveat warning.
"""

import math
from datetime import datetime
from typing import Dict, List


SHARPE_WARNING = (
    "⚠️ Sharpe annualisé théorique. Ne pas comparer aux Sharpe traditionnels "
    "(S&P 500, hedge funds). En live, un Sharpe de 2-4 serait déjà excellent. "
    "Voir Profit Factor et Calmar pour des métriques plus interprétables."
)


def _to_dt(s: str):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def compute_risk_metrics(rows: List[Dict], initial_capital: float = 5000.0) -> Dict:
    """Compute risk metrics from a list of closed trade dicts.

    Each row must have: pnl_usd, pnl_pct, opened_at, closed_at.
    Returns dict with: sharpe_annualized, profit_factor, calmar_ratio,
    max_consecutive_losses, max_consecutive_wins, streak_distribution,
    max_drawdown_pct, annualized_return_pct, n_trades_per_year, span_days.
    """
    n = len(rows)
    if n == 0:
        return {"n": 0}

    # Order chronologically by closed_at (or opened_at fallback)
    ordered = sorted(rows, key=lambda r: r.get("closed_at") or r.get("opened_at") or "")

    pnl_pcts = [(r.get("pnl_pct") or 0.0) for r in ordered]
    pnl_usds = [(r.get("pnl_usd") or 0.0) for r in ordered]

    # Time span
    first_open = _to_dt(ordered[0].get("opened_at") or "")
    last_close = _to_dt(ordered[-1].get("closed_at") or "")
    span_days = ((last_close - first_open).total_seconds() / 86400) if (first_open and last_close) else 0.0
    span_days = max(span_days, 1.0)
    trades_per_year = n / (span_days / 365.0)

    # Sharpe per-trade → annualized
    mean_ret = sum(pnl_pcts) / n
    if n >= 2:
        var = sum((x - mean_ret) ** 2 for x in pnl_pcts) / (n - 1)
        std = math.sqrt(var) if var > 0 else 0.0
    else:
        std = 0.0
    sharpe_per_trade = (mean_ret / std) if std > 0 else 0.0
    sharpe_annual = sharpe_per_trade * math.sqrt(trades_per_year) if std > 0 else 0.0

    # Profit Factor = sum(wins$) / |sum(losses$)|
    sum_wins = sum(p for p in pnl_usds if p > 0)
    sum_losses = sum(p for p in pnl_usds if p < 0)
    profit_factor = (sum_wins / abs(sum_losses)) if sum_losses < 0 else float("inf")

    # Equity curve & max drawdown (in % of initial capital)
    equity = initial_capital
    peak = initial_capital
    max_dd = 0.0
    for p in pnl_usds:
        equity += p
        peak = max(peak, equity)
        dd_pct = (peak - equity) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd_pct)

    # Annualized return (LINEAR extrapolation — avoids CAGR explosion on short windows).
    # period_return * (365 / span_days). Honest for sub-90-day samples.
    period_ret_pct = (sum(pnl_usds) / initial_capital) * 100
    ann_ret_pct = period_ret_pct * (365.0 / span_days) if span_days > 0 else 0.0

    # Calmar = annualized return / max drawdown
    calmar = (ann_ret_pct / max_dd) if max_dd > 0 else float("inf")

    # Streaks (consecutive wins / consecutive losses)
    streak_dist = {"win": {}, "loss": {}}
    cur_dir = None
    cur_len = 0
    max_w = max_l = 0
    streaks_w: List[int] = []
    streaks_l: List[int] = []

    def flush():
        nonlocal cur_len, cur_dir
        if cur_dir == "win" and cur_len:
            streaks_w.append(cur_len)
            streak_dist["win"][cur_len] = streak_dist["win"].get(cur_len, 0) + 1
        elif cur_dir == "loss" and cur_len:
            streaks_l.append(cur_len)
            streak_dist["loss"][cur_len] = streak_dist["loss"].get(cur_len, 0) + 1
        cur_len = 0
        cur_dir = None

    for p in pnl_usds:
        d = "win" if p > 0 else "loss"
        if d == cur_dir:
            cur_len += 1
        else:
            flush()
            cur_dir = d
            cur_len = 1
        if d == "win": max_w = max(max_w, cur_len)
        else:          max_l = max(max_l, cur_len)
    flush()

    return {
        "n": n,
        "span_days": span_days,
        "n_trades_per_year": trades_per_year,
        "sharpe_per_trade": sharpe_per_trade,
        "sharpe_annualized": sharpe_annual,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_dd,
        "annualized_return_pct": ann_ret_pct,
        "calmar_ratio": calmar,
        "max_consecutive_wins": max_w,
        "max_consecutive_losses": max_l,
        "streak_distribution": streak_dist,
        "sum_wins_usd": sum_wins,
        "sum_losses_usd": sum_losses,
    }


def _fmt_inf(x: float, fmt: str = ".2f") -> str:
    if x == float("inf"): return "∞"
    return format(x, fmt)


def render_md(rm: Dict) -> List[str]:
    """Markdown lines. Returns a list ready to extend onto an existing list."""
    if rm.get("n", 0) == 0:
        return ["_Risk metrics: no trades._", ""]
    L = []
    L.append("## 📊 Risk-adjusted metrics")
    L.append("")
    L.append("| Metric | Value | Interpretation |")
    L.append("|---|---:|---|")
    L.append(f"| **Sharpe annualisé** | **{rm['sharpe_annualized']:.2f}** | per-trade Sharpe × √(trades/an) |")
    L.append(f"| Sharpe per-trade | {rm['sharpe_per_trade']:.3f} | mean(ret) / stdev(ret) |")
    L.append(f"| **Profit Factor** | **{_fmt_inf(rm['profit_factor'])}** | $wins / $losses (>1 = profitable) |")
    L.append(f"| **Calmar Ratio** | **{_fmt_inf(rm['calmar_ratio'])}** | annualized return / max DD |")
    L.append(f"| Max drawdown | {rm['max_drawdown_pct']:.2f}% | peak-to-trough on equity curve |")
    L.append(f"| Annualized return (linear) | {rm['annualized_return_pct']:+.1f}% | period return × 365/{rm['span_days']:.0f}j |")
    L.append(f"| Trades/an (extrapolated) | {rm['n_trades_per_year']:.0f} | window: {rm['span_days']:.0f}j ({rm['n']} trades) |")
    L.append(f"| Max losing streak | {rm['max_consecutive_losses']} | longest consecutive losses |")
    L.append(f"| Max winning streak | {rm['max_consecutive_wins']} | longest consecutive wins |")
    L.append(f"| Sum wins | ${rm['sum_wins_usd']:+,.2f} | |")
    L.append(f"| Sum losses | ${rm['sum_losses_usd']:+,.2f} | |")
    L.append("")
    L.append(f"> {SHARPE_WARNING}")
    L.append("")
    L.append("### Streak distribution")
    L.append("")
    L.append("| Length | Wins (count) | Losses (count) |")
    L.append("|---:|---:|---:|")
    all_lens = sorted(set(list(rm["streak_distribution"]["win"].keys()) +
                          list(rm["streak_distribution"]["loss"].keys())))
    for k in all_lens:
        w = rm["streak_distribution"]["win"].get(k, 0)
        l = rm["streak_distribution"]["loss"].get(k, 0)
        L.append(f"| {k} | {w if w else '—'} | {l if l else '—'} |")
    L.append("")
    return L


def render_html(rm: Dict) -> List[str]:
    """HTML fragments — caller wraps in <body> already."""
    if rm.get("n", 0) == 0:
        return ["<p><i>Risk metrics: no trades.</i></p>"]
    H = []
    H.append("<h2>📊 Risk-adjusted metrics</h2>")
    H.append("<table>")
    H.append("<tr><th>Metric</th><th style='text-align:right'>Value</th><th>Interpretation</th></tr>")
    H.append(f"<tr><td><b>Sharpe annualisé</b></td><td style='text-align:right'><b>{rm['sharpe_annualized']:.2f}</b></td><td>per-trade Sharpe × √(trades/an)</td></tr>")
    H.append(f"<tr><td>Sharpe per-trade</td><td style='text-align:right'>{rm['sharpe_per_trade']:.3f}</td><td>mean(ret) / stdev(ret)</td></tr>")
    H.append(f"<tr><td><b>Profit Factor</b></td><td style='text-align:right'><b>{_fmt_inf(rm['profit_factor'])}</b></td><td>$wins / |$losses| — &gt;1 = profitable</td></tr>")
    H.append(f"<tr><td><b>Calmar Ratio</b></td><td style='text-align:right'><b>{_fmt_inf(rm['calmar_ratio'])}</b></td><td>annualized return / max drawdown</td></tr>")
    H.append(f"<tr><td>Max drawdown</td><td style='text-align:right'>{rm['max_drawdown_pct']:.2f}%</td><td>peak-to-trough on equity curve</td></tr>")
    H.append(f"<tr><td>Annualized return (linear)</td><td style='text-align:right'>{rm['annualized_return_pct']:+.1f}%</td><td>period return × 365/{rm['span_days']:.0f}j</td></tr>")
    H.append(f"<tr><td>Trades/an (extrapolated)</td><td style='text-align:right'>{rm['n_trades_per_year']:.0f}</td><td>window: {rm['span_days']:.0f}j ({rm['n']} trades)</td></tr>")
    H.append(f"<tr><td>Max losing streak</td><td style='text-align:right'>{rm['max_consecutive_losses']}</td><td>longest consecutive losses</td></tr>")
    H.append(f"<tr><td>Max winning streak</td><td style='text-align:right'>{rm['max_consecutive_wins']}</td><td>longest consecutive wins</td></tr>")
    H.append(f"<tr><td>Sum wins / losses</td><td style='text-align:right'>+${rm['sum_wins_usd']:,.2f} / ${rm['sum_losses_usd']:,.2f}</td><td></td></tr>")
    H.append("</table>")
    H.append(f"<div style='margin:14px 0;padding:12px 16px;background:#3a2d0a;border-left:4px solid #fbbf24;border-radius:4px;color:#fde68a;font-size:13px'>")
    H.append(f"{SHARPE_WARNING}")
    H.append("</div>")

    # Streak distribution
    all_lens = sorted(set(list(rm["streak_distribution"]["win"].keys()) +
                          list(rm["streak_distribution"]["loss"].keys())))
    H.append("<h3 style='color:#7dd3fc;font-size:14px;margin-top:18px'>Streak distribution</h3>")
    H.append("<table>")
    H.append("<tr><th>Length</th><th style='text-align:right'>Wins (count)</th><th style='text-align:right'>Losses (count)</th></tr>")
    for k in all_lens:
        w = rm["streak_distribution"]["win"].get(k, 0)
        l = rm["streak_distribution"]["loss"].get(k, 0)
        H.append(f"<tr><td>{k}</td><td style='text-align:right'>{w if w else '—'}</td><td style='text-align:right'>{l if l else '—'}</td></tr>")
    H.append("</table>")
    return H


def render_paper_md(rows: List[Dict]) -> List[str]:
    """Render paper-trading slippage stats. Returns MD lines."""
    paper_rows = [r for r in rows if r.get("paper_slippage_pct") is not None]
    L = []
    L.append("## 🧪 Paper-trading slippage tracker (Reco #5 Phase 1)")
    L.append("")
    L.append("Capture du prix Binance ~60s après l'alerte = exécution réaliste. "
             "`slip > 0` = prix monté après alerte (fill défavorable). "
             "`slip < 0` = prix redescendu (fill favorable).")
    L.append("")
    if not paper_rows:
        L.append("_Pas encore de données paper. Appliquer `sql/v11_paper_tracker.sql` puis attendre quelques nouveaux trades._")
        L.append("")
        return L
    slips = [r["paper_slippage_pct"] for r in paper_rows]
    n = len(slips)
    avg = sum(slips) / n
    pos = sum(1 for s in slips if s > 0)
    neg = sum(1 for s in slips if s < 0)
    over_03 = sum(1 for s in slips if abs(s) > 0.3)
    over_05 = sum(1 for s in slips if abs(s) > 0.5)
    sorted_s = sorted(slips)
    median = sorted_s[n // 2]
    p95 = sorted_s[int(n * 0.95)] if n >= 20 else sorted_s[-1]
    L.append("| Metric | Value |")
    L.append("|---|---:|")
    L.append(f"| Trades with paper data | **{n}** / {len(rows)} |")
    L.append(f"| Avg slippage | **{avg:+.3f}%** |")
    L.append(f"| Median slippage | {median:+.3f}% |")
    L.append(f"| P95 |slippage| | {p95:+.3f}% |")
    L.append(f"| Slippage > +0.3% | {over_03} ({over_03/n*100:.1f}%) |")
    L.append(f"| Slippage > +0.5% | {over_05} ({over_05/n*100:.1f}%) |")
    L.append(f"| Up after alert (slip>0) | {pos} ({pos/n*100:.1f}%) |")
    L.append(f"| Down after alert (slip<0) | {neg} ({neg/n*100:.1f}%) |")
    L.append("")
    L.append("> Cible Phase 1 (50 trades paper): slippage moyen ≤ 0.3%. Si > 0.5% systématique → délai de réaction trop long ou alertes trop avancées.")
    L.append("")
    return L


def render_paper_pnl_md(rows: List[Dict]) -> List[str]:
    """Phase 1 go/no-go criterion: delta WR backtest (alert_entry, partials)
    vs paper (paper_entry, simple no-partials). Header shows coverage ratio
    upfront so report fidelity is visible at a glance."""
    n_total = len(rows)
    paper_rows = [r for r in rows if r.get("paper_pnl_pct") is not None]
    n_paper = len(paper_rows)
    coverage_pct = (n_paper / n_total * 100) if n_total else 0
    L = []
    L.append("## 📊 Paper P&L vs Backtest — Phase 1 critère go/no-go")
    L.append("")
    if n_total == 0:
        L.append("_Pas de trades._")
        L.append("")
        return L
    n_missing = n_total - n_paper
    L.append(f"**Couverture : {n_paper}/{n_total} trades ({coverage_pct:.0f}%)** — "
             f"{n_missing} trades sans paper data (bot restart, Binance error à T+60s, "
             f"ou close avant T+60s).")
    L.append("")
    if n_paper == 0:
        L.append("_Pas encore de paper P&L. Lancer `scripts/backfill_paper_pnl.py` ou "
                 "attendre les nouveaux closes après l'application du SQL._")
        L.append("")
        return L

    # Backtest stats: existing pnl_pct (with partials)
    bt_wins = sum(1 for r in paper_rows if (r.get("pnl_usd") or 0) > 0)
    bt_losses = n_paper - bt_wins
    bt_wr = bt_wins / n_paper * 100
    bt_avg_pct = sum((r.get("pnl_pct") or 0) for r in paper_rows) / n_paper
    bt_sum_usd = sum((r.get("pnl_usd") or 0) for r in paper_rows)

    # Paper stats: simple paper_pnl_pct
    pp_wins = sum(1 for r in paper_rows if (r.get("paper_pnl_usd") or 0) > 0)
    pp_losses = n_paper - pp_wins
    pp_wr = pp_wins / n_paper * 100
    pp_avg_pct = sum((r.get("paper_pnl_pct") or 0) for r in paper_rows) / n_paper
    pp_sum_usd = sum((r.get("paper_pnl_usd") or 0) for r in paper_rows)

    delta_wins = pp_wins - bt_wins
    delta_wr = pp_wr - bt_wr
    delta_avg_pct = pp_avg_pct - bt_avg_pct
    delta_sum_usd = pp_sum_usd - bt_sum_usd

    L.append("| Metric              | Backtest    | Paper       | Δ        |")
    L.append("|---------------------|------------:|------------:|---------:|")
    L.append(f"| Trades comparés     | {n_paper}        | {n_paper}        |          |")
    L.append(f"| Wins                | {bt_wins}        | {pp_wins}        | {delta_wins:+d}       |")
    L.append(f"| Losses              | {bt_losses}        | {pp_losses}        | {-delta_wins:+d}       |")
    L.append(f"| WR                  | {bt_wr:.1f}%       | {pp_wr:.1f}%       | {delta_wr:+.1f}pts |")
    L.append(f"| Avg PnL/trade       | {bt_avg_pct:+.2f}%      | {pp_avg_pct:+.2f}%      | {delta_avg_pct:+.2f}pt  |")
    L.append(f"| Sum P&L $           | ${bt_sum_usd:+,.2f}     | ${pp_sum_usd:+,.2f}     | ${delta_sum_usd:+,.2f}    |")
    L.append("")

    # Go/no-go check
    abs_delta_wr = abs(delta_wr)
    if abs_delta_wr <= 8:
        verdict = f"✅ **PASS** — |Δ WR| = {abs_delta_wr:.1f}pts ≤ 8pts"
    elif abs_delta_wr <= 10:
        verdict = f"⚠️ **WATCH** — |Δ WR| = {abs_delta_wr:.1f}pts (entre 8 et 10)"
    else:
        verdict = f"🛑 **FAIL** — |Δ WR| = {abs_delta_wr:.1f}pts > 10 — investiguer"

    L.append(f"> **Critère go/no-go Phase 1 : Δ WR ≤ 8pts → {verdict}**")
    L.append("")
    if n_paper < 50:
        L.append(f"> ⏳ N={n_paper} trades paper — minimum 50 requis pour validation finale.")
    else:
        L.append(f"> ✅ N={n_paper} ≥ 50 trades paper — échantillon suffisant.")
    L.append("")
    L.append("> **Note méthodo** : `paper_pnl` est calculé en mode simple "
             "(`(exit − paper_entry) / paper_entry`), sans propager les partials. "
             "`pnl` backtest utilise les partials TP1/TP2. Asymétrie acceptée pour Phase 1 — "
             "la mécanique exacte des partials avec slippage différentiel est sujet Phase 3.")
    L.append("")
    return L


def render_paper_pnl_html(rows: List[Dict]) -> List[str]:
    """HTML version of render_paper_pnl_md — coverage in big banner upfront."""
    n_total = len(rows)
    paper_rows = [r for r in rows if r.get("paper_pnl_pct") is not None]
    n_paper = len(paper_rows)
    coverage_pct = (n_paper / n_total * 100) if n_total else 0
    H = []
    H.append("<h2>📊 Paper P&L vs Backtest — Phase 1 critère go/no-go</h2>")
    if n_total == 0:
        H.append("<p><i>Pas de trades.</i></p>")
        return H
    n_missing = n_total - n_paper
    # Coverage banner — color-coded
    if coverage_pct >= 90:
        banner_color = "rgba(74,222,128,0.15);border-left:4px solid #4ade80;color:#86efac"
    elif coverage_pct >= 60:
        banner_color = "rgba(251,191,36,0.15);border-left:4px solid #fbbf24;color:#fde68a"
    else:
        banner_color = "rgba(248,113,113,0.15);border-left:4px solid #f87171;color:#fca5a5"
    H.append(f"<div style='margin:14px 0;padding:14px 18px;background:{banner_color};border-radius:4px;font-size:14px'>")
    H.append(f"<b>Couverture : {n_paper}/{n_total} trades ({coverage_pct:.0f}%)</b> — "
             f"{n_missing} trades sans paper data (bot restart, Binance error à T+60s, ou close avant T+60s).")
    H.append("</div>")

    if n_paper == 0:
        H.append("<p style='color:#fcd34d'><i>Pas encore de paper P&L. Lancer "
                 "<code>scripts/backfill_paper_pnl.py</code> ou attendre les nouveaux closes "
                 "après application du SQL.</i></p>")
        return H

    # Stats
    bt_wins = sum(1 for r in paper_rows if (r.get("pnl_usd") or 0) > 0)
    bt_losses = n_paper - bt_wins
    bt_wr = bt_wins / n_paper * 100
    bt_avg_pct = sum((r.get("pnl_pct") or 0) for r in paper_rows) / n_paper
    bt_sum_usd = sum((r.get("pnl_usd") or 0) for r in paper_rows)
    pp_wins = sum(1 for r in paper_rows if (r.get("paper_pnl_usd") or 0) > 0)
    pp_losses = n_paper - pp_wins
    pp_wr = pp_wins / n_paper * 100
    pp_avg_pct = sum((r.get("paper_pnl_pct") or 0) for r in paper_rows) / n_paper
    pp_sum_usd = sum((r.get("paper_pnl_usd") or 0) for r in paper_rows)

    delta_wins = pp_wins - bt_wins
    delta_wr = pp_wr - bt_wr
    delta_avg_pct = pp_avg_pct - bt_avg_pct
    delta_sum_usd = pp_sum_usd - bt_sum_usd

    H.append("<table>")
    H.append("<tr><th>Metric</th><th style='text-align:right'>Backtest</th><th style='text-align:right'>Paper</th><th style='text-align:right'>Δ</th></tr>")
    H.append(f"<tr><td>Trades comparés</td><td style='text-align:right'>{n_paper}</td><td style='text-align:right'>{n_paper}</td><td></td></tr>")
    H.append(f"<tr><td>Wins</td><td style='text-align:right'>{bt_wins}</td><td style='text-align:right'>{pp_wins}</td><td style='text-align:right'>{delta_wins:+d}</td></tr>")
    H.append(f"<tr><td>Losses</td><td style='text-align:right'>{bt_losses}</td><td style='text-align:right'>{pp_losses}</td><td style='text-align:right'>{-delta_wins:+d}</td></tr>")
    H.append(f"<tr><td><b>WR</b></td><td style='text-align:right'><b>{bt_wr:.1f}%</b></td><td style='text-align:right'><b>{pp_wr:.1f}%</b></td><td style='text-align:right'><b>{delta_wr:+.1f}pts</b></td></tr>")
    H.append(f"<tr><td>Avg PnL/trade</td><td style='text-align:right'>{bt_avg_pct:+.2f}%</td><td style='text-align:right'>{pp_avg_pct:+.2f}%</td><td style='text-align:right'>{delta_avg_pct:+.2f}pt</td></tr>")
    H.append(f"<tr><td>Sum P&L $</td><td style='text-align:right'>${bt_sum_usd:+,.2f}</td><td style='text-align:right'>${pp_sum_usd:+,.2f}</td><td style='text-align:right'>${delta_sum_usd:+,.2f}</td></tr>")
    H.append("</table>")

    # Go/no-go verdict
    abs_delta_wr = abs(delta_wr)
    if abs_delta_wr <= 8:
        verdict_html = f"<span style='color:#4ade80'>✅ <b>PASS</b> — |Δ WR| = {abs_delta_wr:.1f}pts ≤ 8pts</span>"
    elif abs_delta_wr <= 10:
        verdict_html = f"<span style='color:#fbbf24'>⚠️ <b>WATCH</b> — |Δ WR| = {abs_delta_wr:.1f}pts (entre 8 et 10)</span>"
    else:
        verdict_html = f"<span style='color:#f87171'>🛑 <b>FAIL</b> — |Δ WR| = {abs_delta_wr:.1f}pts &gt; 10 — investiguer</span>"
    H.append(f"<p style='font-size:14px;margin-top:12px'><b>Critère go/no-go Phase 1 (Δ WR ≤ 8pts)</b> → {verdict_html}</p>")

    if n_paper < 50:
        H.append(f"<p style='color:#fcd34d;font-size:13px'>⏳ N={n_paper} trades paper — minimum 50 requis pour validation finale.</p>")
    else:
        H.append(f"<p style='color:#86efac;font-size:13px'>✅ N={n_paper} ≥ 50 trades paper — échantillon suffisant.</p>")

    H.append("<p style='color:#94a3b8;font-size:12px;font-style:italic;margin-top:10px'>"
             "<b>Note méthodo</b> : <code>paper_pnl</code> est calculé en mode simple "
             "(<code>(exit − paper_entry) / paper_entry</code>), sans propager les partials. "
             "<code>pnl</code> backtest utilise les partials TP1/TP2. Asymétrie acceptée pour Phase 1 — "
             "la mécanique exacte des partials avec slippage différentiel est sujet Phase 3.</p>")
    return H


def render_paper_html(rows: List[Dict]) -> List[str]:
    """Render paper-trading slippage stats as HTML."""
    paper_rows = [r for r in rows if r.get("paper_slippage_pct") is not None]
    H = []
    H.append("<h2>🧪 Paper-trading slippage tracker (Reco #5 Phase 1)</h2>")
    H.append("<p style='color:#94a3b8;font-size:13px'>Capture du prix Binance ~60s après l'alerte = exécution réaliste. "
             "<code>slip &gt; 0</code> = prix monté (fill défavorable). "
             "<code>slip &lt; 0</code> = prix redescendu (fill favorable).</p>")
    if not paper_rows:
        H.append("<p style='color:#fcd34d'><i>Pas encore de données paper. Appliquer "
                 "<code>sql/v11_paper_tracker.sql</code> puis attendre quelques nouveaux trades.</i></p>")
        return H
    slips = [r["paper_slippage_pct"] for r in paper_rows]
    n = len(slips)
    avg = sum(slips) / n
    pos = sum(1 for s in slips if s > 0)
    neg = sum(1 for s in slips if s < 0)
    over_03 = sum(1 for s in slips if abs(s) > 0.3)
    over_05 = sum(1 for s in slips if abs(s) > 0.5)
    sorted_s = sorted(slips)
    median = sorted_s[n // 2]
    p95 = sorted_s[int(n * 0.95)] if n >= 20 else sorted_s[-1]
    H.append("<table>")
    H.append("<tr><th>Metric</th><th style='text-align:right'>Value</th></tr>")
    H.append(f"<tr><td>Trades with paper data</td><td style='text-align:right'><b>{n}</b> / {len(rows)}</td></tr>")
    H.append(f"<tr><td>Avg slippage</td><td style='text-align:right'><b>{avg:+.3f}%</b></td></tr>")
    H.append(f"<tr><td>Median slippage</td><td style='text-align:right'>{median:+.3f}%</td></tr>")
    H.append(f"<tr><td>P95 |slippage|</td><td style='text-align:right'>{p95:+.3f}%</td></tr>")
    H.append(f"<tr><td>Slippage &gt; +0.3%</td><td style='text-align:right'>{over_03} ({over_03/n*100:.1f}%)</td></tr>")
    H.append(f"<tr><td>Slippage &gt; +0.5%</td><td style='text-align:right'>{over_05} ({over_05/n*100:.1f}%)</td></tr>")
    H.append(f"<tr><td>Up after alert (slip&gt;0)</td><td style='text-align:right'>{pos} ({pos/n*100:.1f}%)</td></tr>")
    H.append(f"<tr><td>Down after alert (slip&lt;0)</td><td style='text-align:right'>{neg} ({neg/n*100:.1f}%)</td></tr>")
    H.append("</table>")
    H.append("<p style='color:#94a3b8;font-size:12px;font-style:italic'>"
             "Cible Phase 1 (50 trades paper): slippage moyen ≤ 0.3%. Si &gt; 0.5% systématique → "
             "délai de réaction trop long ou alertes trop avancées.</p>")
    return H
