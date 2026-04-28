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
