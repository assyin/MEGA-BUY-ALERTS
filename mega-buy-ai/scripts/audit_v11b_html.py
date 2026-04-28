#!/usr/bin/env python3
"""Generate self-contained HTML version of the V11B trade audit.

Reads from openclaw_positions_v11b + agent_memory + alerts, emits a styled
.html file with dark theme, sticky header, search filter, and one collapsible
card per trade.
"""

import html
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


TABLE_POS = "openclaw_positions_v11b"
TABLE_STATE = "openclaw_portfolio_state_v11b"
THR_R30M = 1.89
THR_R4H = 2.58
SL_PCT = 8.0
TP1_PCT = 10.0; TP1_FRAC = 0.50
TP2_PCT = 20.0; TP2_FRAC = 0.30
TRAIL_DIST_PCT = 8.0
SIZE_USD = 400.0


def hold_hours(opened: str, closed: str) -> float:
    if not opened or not closed: return 0
    try:
        a = datetime.fromisoformat(opened.replace("Z", "+00:00"))
        b = datetime.fromisoformat(closed.replace("Z", "+00:00"))
        return (b - a).total_seconds() / 3600
    except Exception:
        return 0


def fmt_dur(h: float) -> str:
    if h < 1: return f"{int(h*60)}min"
    if h < 24: return f"{h:.1f}h"
    days = int(h // 24); rem = int(h % 24)
    return f"{days}j{rem}h"


def fmt_price(p) -> str:
    if p is None: return "—"
    p = float(p)
    if p >= 1: return f"${p:.4f}"
    if p >= 0.001: return f"${p:.6f}"
    return f"${p:.8f}"


def fmt_pct(p) -> str:
    if p is None: return "—"
    return f"{p:+.2f}%"


def html_entry(pair, fp, alert, valid_check):
    r30 = fp.get("candle_30m_range_pct")
    r4 = fp.get("candle_4h_range_pct")
    score = fp.get("scanner_score") or alert.get("scanner_score") or 0
    decision = fp.get("agent_decision") or "?"
    conf = fp.get("agent_confidence")
    body4 = fp.get("candle_4h_body_pct")
    direction4 = fp.get("candle_4h_direction") or "?"
    rsi = fp.get("rsi") or alert.get("rsi") or 0
    adx = fp.get("adx_4h") or alert.get("adx_4h") or 0
    di_p = fp.get("di_plus_4h") or alert.get("di_plus_4h") or 0
    di_m = fp.get("di_minus_4h") or alert.get("di_minus_4h") or 0
    btc_trend = fp.get("btc_trend_1h") or "?"
    fg = fp.get("fear_greed_value")
    chg24 = fp.get("change_24h_pct")
    valid_r30, valid_r4 = valid_check
    sym30 = "✅" if valid_r30 else "❌"
    sym4 = "✅" if valid_r4 else "❌"

    parts = []
    parts.append('<div class="section-title">Conditions du filtre V11B (gate)</div>')
    parts.append('<ul class="conditions">')
    parts.append(f'<li>{sym30} <code>range_30m = {r30 if r30 is not None else "N/A"}%</code> ≤ {THR_R30M}%</li>')
    parts.append(f'<li>{sym4} <code>range_4h = {r4 if r4 is not None else "N/A"}%</code> ≤ {THR_R4H}%</li>')
    if not (valid_r30 and valid_r4):
        parts.append('<li class="warn">🚨 <b>Trade INVALIDE</b> : ce trade n\'aurait pas dû être ouvert.</li>')
    else:
        parts.append('<li class="ok">✅ Les 2 conditions du gate V11B passent → entrée autorisée.</li>')
    parts.append('</ul>')

    parts.append('<div class="section-title">Contexte au moment de l\'alerte</div>')
    parts.append('<ul class="context">')
    parts.append(f'<li>Scanner score : <b>{score}/10</b></li>')
    if decision and decision != "?":
        conf_s = f" ({conf*100:.0f}% confiance)" if conf else ""
        parts.append(f'<li>Décision OpenClaw : <b>{html.escape(str(decision))}</b>{conf_s}</li>')
    if body4 is not None:
        parts.append(f'<li>Bougie 4H : direction <b>{direction4}</b>, body {body4:.2f}%</li>')
    if rsi: parts.append(f'<li>RSI : {rsi:.1f}</li>')
    if adx: parts.append(f'<li>ADX 4H : {adx:.1f} (DI+ {di_p:.0f} / DI- {di_m:.0f})</li>')
    if chg24 is not None: parts.append(f'<li>Change 24h : {chg24:+.2f}%</li>')
    if btc_trend != "?": parts.append(f'<li>BTC trend 1H : <code>{html.escape(str(btc_trend))}</code></li>')
    if fg is not None: parts.append(f'<li>Fear &amp; Greed : {fg}</li>')
    parts.append('</ul>')
    return "\n".join(parts)


def html_exit(t, hours):
    entry = t.get("entry_price", 0)
    exit_p = t.get("exit_price", 0)
    high = t.get("highest_price", 0)
    pnl_pct = t.get("pnl_pct", 0)
    pnl_usd = t.get("pnl_usd", 0)
    p1 = t.get("partial1_done", False)
    p2 = t.get("partial2_done", False)
    trail = t.get("trail_active", False)
    reason_raw = t.get("close_reason") or ""
    reason = reason_raw.split(":", 1)[1] if ":" in reason_raw else reason_raw
    is_hydrated = reason_raw.startswith("HYDRATED_BACKTEST:")
    peak_pct = (high - entry) / entry * 100 if entry else 0

    parts = []
    parts.append('<div class="section-title">Trajectoire</div>')
    parts.append('<ul class="trajectory">')
    parts.append(f'<li>Entry : <code>{fmt_price(entry)}</code></li>')
    parts.append(f'<li>Peak atteint : <code>{fmt_price(high)}</code> (<b>{fmt_pct(peak_pct)}</b> du peak)</li>')
    parts.append(f'<li>Exit : <code>{fmt_price(exit_p)}</code></li>')
    parts.append(f'<li>Hold : {fmt_dur(hours)}</li>')
    parts.append('</ul>')

    parts.append('<div class="section-title">Évènements (logique exit hybride V7)</div>')
    parts.append('<ul class="events">')
    if reason == "SL_HIT":
        sl_price = entry * (1 - SL_PCT/100)
        parts.append(f'<li class="bad">❌ <b>Stop Loss touché à {fmt_price(sl_price)}</b> (-{SL_PCT}% sous l\'entry)</li>')
        parts.append(f'<li>Le prix n\'a JAMAIS atteint TP1 (+{TP1_PCT}%, soit <code>{fmt_price(entry*(1+TP1_PCT/100))}</code>)</li>')
        parts.append(f'<li>Position fermée à 100% au prix du SL.</li>')
    elif reason == "BREAKEVEN_STOP":
        tp1_price = entry * (1 + TP1_PCT/100)
        parts.append(f'<li class="ok">✅ <b>TP1 hit</b> à <code>{fmt_price(tp1_price)}</code> (+{TP1_PCT}%) → 50% fermé = ${SIZE_USD * TP1_FRAC * TP1_PCT/100:.2f}</li>')
        parts.append(f'<li>🛡 Stop déplacé à BREAKEVEN (<code>{fmt_price(entry)}</code>)</li>')
        parts.append(f'<li>Le prix n\'a PAS atteint TP2 (+{TP2_PCT}%) → est redescendu à BE.</li>')
        parts.append(f'<li>Les 50% restants fermés au breakeven (0% sur cette portion).</li>')
    elif reason == "TRAIL_STOP":
        tp1_price = entry * (1 + TP1_PCT/100)
        tp2_price = entry * (1 + TP2_PCT/100)
        trail_exit_pct = (exit_p - entry) / entry * 100 if entry else 0
        parts.append(f'<li class="ok">✅ <b>TP1 hit</b> à <code>{fmt_price(tp1_price)}</code> (+{TP1_PCT}%) → 50% fermé = ${SIZE_USD * TP1_FRAC * TP1_PCT/100:.2f}</li>')
        parts.append(f'<li class="ok">✅✅ <b>TP2 hit</b> à <code>{fmt_price(tp2_price)}</code> (+{TP2_PCT}%) → 30% fermé = ${SIZE_USD * TP2_FRAC * TP2_PCT/100:.2f}</li>')
        parts.append(f'<li>🔄 <b>Trailing activé</b> sur les 20% restants (-{TRAIL_DIST_PCT}% du peak)</li>')
        parts.append(f'<li>📈 Peak final : <code>{fmt_price(high)}</code> ({fmt_pct(peak_pct)})</li>')
        parts.append(f'<li>🚪 Trail stop touché à <code>{fmt_price(exit_p)}</code> ({fmt_pct(trail_exit_pct)}) → 20% fermé.</li>')
    elif reason == "TIMEOUT_72H":
        tp1_price = entry * (1 + TP1_PCT/100)
        if p1:
            parts.append(f'<li class="ok">✅ <b>TP1 hit</b> (50% fermé à +{TP1_PCT}%)</li>')
            if p2:
                parts.append(f'<li class="ok">✅ <b>TP2 hit</b> (30% fermé à +{TP2_PCT}%)</li>')
            parts.append(f'<li>⏰ <b>Timeout 72h</b> atteint avant trail/SL → restants fermés à {fmt_pct((exit_p-entry)/entry*100 if entry else 0)}</li>')
        else:
            parts.append(f'<li>⏰ <b>Timeout 72h</b> : prix oscillé sans atteindre TP1 (<code>{fmt_price(tp1_price)}</code>) ni SL (-{SL_PCT}%)</li>')
            parts.append(f'<li>Position fermée à 100% au prix de fin de fenêtre.</li>')
    else:
        parts.append(f'<li>🔔 Close reason : <code>{html.escape(reason)}</code> (cas non standard)</li>')
    parts.append('</ul>')

    pnl_realized = t.get("realized_pnl_usd") or pnl_usd or 0
    profit_emoji = "💰" if pnl_realized > 0 else "💔"
    cls = "win" if pnl_realized > 0 else "lose"
    parts.append(f'<div class="pnl-final {cls}">{profit_emoji} <b>PnL final : {fmt_pct(pnl_pct)}</b> ({pnl_realized:+.2f}$ sur ${SIZE_USD} investis)</div>')
    if is_hydrated:
        parts.append('<div class="hydrated-tag">Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 sur klines historiques 5m.</div>')
    return "\n".join(parts)


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a0e14;color:#cdd6dc;line-height:1.5;padding:20px;max-width:1400px;margin:0 auto}
h1{color:#7dd3fc;font-size:28px;margin-bottom:6px;border-bottom:2px solid #1e3a5f;padding-bottom:10px}
h2{color:#fbbf24;font-size:20px;margin:24px 0 12px;border-left:4px solid #fbbf24;padding-left:10px}
.subtitle{color:#64748b;font-size:13px;margin-bottom:20px}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:20px 0}
.summary-card{background:#111827;border:1px solid #1f2937;border-radius:8px;padding:14px}
.summary-card .label{color:#94a3b8;font-size:11px;text-transform:uppercase;letter-spacing:1px}
.summary-card .value{color:#e2e8f0;font-size:22px;font-weight:bold;margin-top:4px}
.summary-card .value.win{color:#4ade80}.summary-card .value.lose{color:#f87171}.summary-card .value.neutral{color:#fbbf24}
table{width:100%;border-collapse:collapse;margin:12px 0;background:#111827;border:1px solid #1f2937;border-radius:8px;overflow:hidden}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid #1f2937;font-size:13px}
th{background:#1e293b;color:#94a3b8;font-weight:600;text-transform:uppercase;font-size:11px;letter-spacing:0.5px}
tr:hover{background:#1e293b}
code{background:#1e3a5f;color:#bae6fd;padding:1px 6px;border-radius:4px;font-family:'SF Mono',Monaco,monospace;font-size:12px}
.search-box{position:sticky;top:0;background:#0a0e14;padding:12px 0;z-index:100;display:flex;gap:10px;align-items:center;border-bottom:1px solid #1e3a5f;margin-bottom:16px}
.search-box input,.search-box select{padding:8px 12px;background:#111827;border:1px solid #334155;border-radius:6px;color:#e2e8f0;font-size:13px}
.search-box input{flex:1}
.search-box .count{color:#64748b;font-size:12px}
details{background:#0f172a;border:1px solid #1e293b;border-radius:8px;margin:8px 0;overflow:hidden;transition:border-color 0.2s}
details:hover{border-color:#334155}
details[open]{border-color:#475569}
summary{padding:12px 16px;cursor:pointer;display:flex;align-items:center;gap:10px;font-size:13px;list-style:none;user-select:none}
summary::-webkit-details-marker{display:none}
summary::before{content:'▶';transition:transform 0.2s;color:#64748b;font-size:10px}
details[open] summary::before{transform:rotate(90deg)}
.win-badge{color:#4ade80}.lose-badge{color:#f87171}.invalid-badge{color:#fbbf24}
.trade-content{padding:0 16px 16px;border-top:1px solid #1e293b;margin-top:0}
.section-title{color:#7dd3fc;font-size:13px;font-weight:600;margin:14px 0 6px;text-transform:uppercase;letter-spacing:0.5px}
ul{list-style:none;padding-left:0}
ul li{padding:4px 0;font-size:13px}
li.ok{color:#86efac}li.bad{color:#fca5a5}li.warn{color:#fcd34d}
.pnl-final{padding:10px 14px;border-radius:6px;margin-top:12px;font-size:14px}
.pnl-final.win{background:rgba(74,222,128,0.1);color:#86efac;border:1px solid rgba(74,222,128,0.3)}
.pnl-final.lose{background:rgba(248,113,113,0.1);color:#fca5a5;border:1px solid rgba(248,113,113,0.3)}
.hydrated-tag{font-size:11px;color:#64748b;margin-top:8px;font-style:italic;padding:6px 10px;background:#1e293b;border-radius:4px}
.top-list{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:16px 0}
.top-list-card{background:#111827;border:1px solid #1f2937;border-radius:8px;padding:14px}
.top-list-card h3{font-size:14px;margin-bottom:10px;color:#fbbf24}
.top-list-card ol{padding-left:24px;font-size:13px}
.top-list-card li{padding:3px 0}
.win-h3{color:#4ade80!important}.lose-h3{color:#f87171!important}
"""


JS = """
function filterTrades(){
  const q = document.getElementById('search').value.toLowerCase()
  const reason = document.getElementById('reasonFilter').value
  const result = document.getElementById('resultFilter').value
  let visible = 0
  document.querySelectorAll('.trade').forEach(d=>{
    const txt = d.dataset.search
    const r = d.dataset.reason || ''
    const w = d.dataset.win === 'true'
    let show = !q || txt.includes(q)
    if(show && reason && r !== reason) show = false
    if(show && result === 'wins' && !w) show = false
    if(show && result === 'losses' && w) show = false
    d.style.display = show ? '' : 'none'
    if(show) visible++
  })
  document.getElementById('counter').textContent = visible + ' trades affichés'
}
function expandAll(){document.querySelectorAll('.trade').forEach(d=>d.open=true)}
function collapseAll(){document.querySelectorAll('.trade').forEach(d=>d.open=false)}
"""


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print("📥 Loading V11B closed trades...", flush=True)
    rows = []
    cursor = 0
    while True:
        r = sb.table(TABLE_POS).select("*").eq("status", "CLOSED").order("opened_at", desc=False).range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000
    print(f"   {len(rows)} closed trades")

    state_r = sb.table(TABLE_STATE).select("*").eq("id", "main").single().execute()
    state = state_r.data or {}

    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    fp_map = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("agent_memory").select("alert_id,features_fingerprint,agent_decision,agent_confidence,scanner_score,outcome").in_("alert_id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            fp_map[x["alert_id"]] = x

    alert_map = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("alerts").select("id,alert_timestamp,price,puissance,emotion,nb_timeframes,timeframes,rsi,di_plus_4h,di_minus_4h,adx_4h,pp,ec").in_("id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            alert_map[x["id"]] = x

    n = len(rows)
    wins = sum(1 for r in rows if (r.get("pnl_usd") or 0) > 0)
    losses = n - wins
    wr = wins/n*100 if n else 0
    total_pnl = sum(r.get("pnl_usd") or 0 for r in rows)
    avg_pnl = sum(r.get("pnl_pct") or 0 for r in rows) / n if n else 0
    avg_hold = sum(hold_hours(r.get("opened_at",""), r.get("closed_at","")) for r in rows) / n if n else 0

    reasons = {}
    for r in rows:
        rr = (r.get("close_reason") or "").split(":",1)[1] if ":" in (r.get("close_reason") or "") else r.get("close_reason","?")
        reasons[rr] = reasons.get(rr, 0) + 1

    sorted_by_pnl = sorted(rows, key=lambda x: x.get("pnl_usd") or 0, reverse=True)
    top_w = sorted_by_pnl[:5]
    top_l = sorted_by_pnl[-5:]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    H = []
    H.append("<!DOCTYPE html><html lang='fr'><head><meta charset='UTF-8'>")
    H.append("<title>V11B Trade Audit</title>")
    H.append(f"<style>{CSS}</style>")
    H.append(f"<script>{JS}</script>")
    H.append("</head><body>")

    H.append("<h1>🔬 V11B Compression — Trade Audit</h1>")
    H.append(f"<div class='subtitle'>Généré : {today} • Filtre : <code>Range 30m ≤ 1.89%</code> ET <code>Range 4h ≤ 2.58%</code> • Exit hybride V7 (TP1+TP2+Trail+SL) • Capital $5,000 (8%/trade)</div>")

    # Summary cards
    balance = state.get('balance', 0)
    roi = (balance - 5000) / 5000 * 100 if balance else 0
    H.append("<div class='summary-grid'>")
    H.append(f"<div class='summary-card'><div class='label'>Trades fermés</div><div class='value'>{n}</div></div>")
    H.append(f"<div class='summary-card'><div class='label'>Win Rate</div><div class='value win'>{wr:.1f}%</div><div class='label'>{wins}W / {losses}L</div></div>")
    H.append(f"<div class='summary-card'><div class='label'>PnL total</div><div class='value {('win' if total_pnl >= 0 else 'lose')}'>${total_pnl:+,.2f}</div></div>")
    H.append(f"<div class='summary-card'><div class='label'>Avg PnL/trade</div><div class='value neutral'>{avg_pnl:+.2f}%</div></div>")
    H.append(f"<div class='summary-card'><div class='label'>Hold moyen</div><div class='value neutral'>{fmt_dur(avg_hold)}</div></div>")
    H.append(f"<div class='summary-card'><div class='label'>Balance finale</div><div class='value win'>${balance:,.0f}</div><div class='label'>ROI {roi:+.1f}%</div></div>")
    H.append("</div>")

    # Distribution close_reason
    H.append("<h2>Distribution close_reason</h2>")
    H.append("<table><tr><th>Raison</th><th>Count</th><th>%</th></tr>")
    for r, c in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        H.append(f"<tr><td><code>{html.escape(r)}</code></td><td>{c}</td><td>{c/n*100:.1f}%</td></tr>")
    H.append("</table>")

    # Risk-adjusted metrics (Sharpe with caveat, Profit Factor, Calmar, streaks)
    sys.path.insert(0, str(Path(__file__).parent))
    from _risk_metrics import compute_risk_metrics, render_html as render_risk_html, render_paper_html
    rm = compute_risk_metrics(rows, initial_capital=5000.0)
    H.extend(render_risk_html(rm))
    # Paper-trading slippage (Reco #5 Phase 1) — show even if empty
    H.extend(render_paper_html(rows))

    # BTC 24h bucket distribution — estimates layered BTC dump protection impact
    H.append("<h2>🧊 BTC dump protection — historical impact</h2>")
    H.append("<p style='color:#94a3b8;font-size:13px'>Distribution des trades par bucket "
             "<code>btc_change_24h</code> (au moment de l'alerte) + PnL réel. Donne une estimation "
             "du nombre de trades qui auraient été skippés par la protection layered "
             "(-5% hard / -3% soft avec ≥6 open).</p>")
    buckets = [
        (">= 0%",       lambda b: b >= 0,                          "ok"),
        ("[-3%, 0%)",   lambda b: -3.0 <= b < 0,                   "ok"),
        ("[-5%, -3%)",  lambda b: -5.0 <= b < -3.0,                "warn"),
        ("&lt;= -5%",   lambda b: b < -5.0,                        "bad"),
    ]
    bstats = {label: {"n": 0, "pnl": 0.0, "wins": 0} for label, _, _ in buckets}
    n_no_btc = 0
    for r in rows:
        aid = r.get("alert_id")
        fp_row = fp_map.get(aid, {})
        fp = fp_row.get("features_fingerprint") or {}
        btc = fp.get("btc_change_24h")
        if btc is None:
            n_no_btc += 1
            continue
        pnl_usd = r.get("pnl_usd") or 0
        for label, pred, _ in buckets:
            if pred(float(btc)):
                bstats[label]["n"] += 1
                bstats[label]["pnl"] += pnl_usd
                if pnl_usd > 0: bstats[label]["wins"] += 1
                break
    H.append("<table>")
    H.append("<tr><th>Bucket BTC 24h</th><th style='text-align:right'>Trades</th><th style='text-align:right'>WR</th><th style='text-align:right'>PnL réel</th><th style='text-align:right'>PnL/trade</th><th>Action future</th></tr>")
    for label, _, kind in buckets:
        bs = bstats[label]
        wr_b = (bs["wins"]/bs["n"]*100) if bs["n"] else 0
        avg = (bs["pnl"]/bs["n"]) if bs["n"] else 0
        if kind == "bad":
            action = "🛑 HARD STOP — toujours skippé"
        elif kind == "warn":
            action = "⚠️ SOFT CAP si ≥6 open"
        else:
            action = "✅ OK"
        H.append(f"<tr><td>{label}</td><td style='text-align:right'>{bs['n']}</td><td style='text-align:right'>{wr_b:.1f}%</td><td style='text-align:right'>${bs['pnl']:+,.2f}</td><td style='text-align:right'>${avg:+,.2f}</td><td>{action}</td></tr>")
    if n_no_btc:
        H.append(f"<tr><td><i>no btc_change_24h</i></td><td style='text-align:right'>{n_no_btc}</td><td colspan='4'>(FP missing field)</td></tr>")
    H.append("</table>")

    # Top 5 lists
    H.append("<div class='top-list'>")
    H.append("<div class='top-list-card'><h3 class='win-h3'>🏆 Top 5 Winners</h3><ol>")
    for r in top_w:
        rs = (r.get("close_reason") or "").split(':',1)[-1]
        H.append(f"<li><b>{html.escape(r.get('pair','?'))}</b> — {fmt_pct(r.get('pnl_pct'))} ({r.get('pnl_usd', 0):+.2f}$) — <code>{html.escape(rs)}</code></li>")
    H.append("</ol></div>")
    H.append("<div class='top-list-card'><h3 class='lose-h3'>💔 Top 5 Losers</h3><ol>")
    for r in top_l:
        rs = (r.get("close_reason") or "").split(':',1)[-1]
        H.append(f"<li><b>{html.escape(r.get('pair','?'))}</b> — {fmt_pct(r.get('pnl_pct'))} ({r.get('pnl_usd', 0):+.2f}$) — <code>{html.escape(rs)}</code></li>")
    H.append("</ol></div>")
    H.append("</div>")

    # Search bar
    H.append("<h2>Audit complet — un trade par carte</h2>")
    H.append("<div class='search-box'>")
    H.append("<input type='text' id='search' placeholder='🔍 Filtrer par paire, raison, date...' oninput='filterTrades()'>")
    H.append("<select id='reasonFilter' onchange='filterTrades()'>")
    H.append("<option value=''>Tous les exits</option>")
    for r in sorted(reasons.keys()):
        H.append(f"<option value='{html.escape(r)}'>{html.escape(r)}</option>")
    H.append("</select>")
    H.append("<select id='resultFilter' onchange='filterTrades()'>")
    H.append("<option value=''>Tous</option><option value='wins'>Wins only</option><option value='losses'>Losses only</option>")
    H.append("</select>")
    H.append("<button onclick='expandAll()' style='padding:8px 12px;background:#1e3a5f;color:#bae6fd;border:none;border-radius:6px;cursor:pointer'>Tout déplier</button>")
    H.append("<button onclick='collapseAll()' style='padding:8px 12px;background:#1e293b;color:#94a3b8;border:none;border-radius:6px;cursor:pointer'>Tout replier</button>")
    H.append(f"<span class='count' id='counter'>{n} trades affichés</span>")
    H.append("</div>")

    # Trade cards
    for i, r in enumerate(rows, 1):
        pair = r.get("pair", "?")
        pnl_pct = r.get("pnl_pct") or 0
        pnl_usd = r.get("pnl_usd") or 0
        opened = r.get("opened_at") or ""
        closed = r.get("closed_at") or ""
        hours = hold_hours(opened, closed)
        is_win = pnl_usd > 0
        emoji = "✅" if is_win else "❌"
        date_short = opened[:16].replace("T", " ")
        reason_raw = r.get("close_reason") or ""
        reason = reason_raw.split(":", 1)[1] if ":" in reason_raw else reason_raw

        aid = r.get("alert_id")
        fp_row = fp_map.get(aid, {})
        fp = fp_row.get("features_fingerprint") or {}
        alert = alert_map.get(aid, {})
        for key in ("agent_decision", "agent_confidence", "scanner_score", "outcome"):
            if key not in fp and key in fp_row:
                fp[key] = fp_row[key]

        snap = r.get("gate_snapshot") or {}
        r30v = snap.get("candle_30m_range_pct") if snap else fp.get("candle_30m_range_pct")
        r4v = snap.get("candle_4h_range_pct") if snap else fp.get("candle_4h_range_pct")
        valid = (r30v is not None and r30v <= THR_R30M and r4v is not None and r4v <= THR_R4H)
        validity_badge = "" if valid else " <span class='invalid-badge'>🚨</span>"

        win_badge = "win-badge" if is_win else "lose-badge"
        search_data = html.escape(f"{pair} {reason} {date_short} {pnl_pct:.2f}").lower()

        H.append(f"<details class='trade' data-search='{search_data}' data-reason='{html.escape(reason)}' data-win='{str(is_win).lower()}'>")
        H.append(f"<summary>")
        H.append(f"<span style='color:#64748b'>#{i}</span>")
        H.append(f"<span class='{win_badge}'>{emoji}</span>")
        H.append(f"<b>{html.escape(pair)}</b>")
        H.append(f"<span class='{win_badge}'>{fmt_pct(pnl_pct)}</span>")
        H.append(f"<span style='color:#64748b'>(${pnl_usd:+.1f})</span>")
        H.append(f"<span style='color:#64748b'>•</span>")
        H.append(f"<span style='color:#94a3b8'>{html.escape(date_short)}</span>")
        H.append(f"<span style='color:#64748b'>•</span>")
        H.append(f"<code>{html.escape(reason)}</code>")
        H.append(f"<span style='color:#64748b'>• {fmt_dur(hours)}{validity_badge}</span>")
        H.append("</summary>")
        H.append("<div class='trade-content'>")
        H.append("<h3 style='color:#7dd3fc;font-size:14px;margin-top:12px'>📥 Entry</h3>")
        H.append(html_entry(pair, fp, alert, (r30v is not None and r30v <= THR_R30M, r4v is not None and r4v <= THR_R4H)))
        H.append("<h3 style='color:#7dd3fc;font-size:14px;margin-top:16px'>📤 Exit</h3>")
        H.append(html_exit(r, hours))
        H.append("</div>")
        H.append("</details>")

    H.append("</body></html>")

    out_path = Path(__file__).parent.parent.parent / f"V11B_TRADE_AUDIT_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.html"
    out_path.write_text("\n".join(H), encoding="utf-8")
    print(f"\n✅ HTML written: {out_path}")
    print(f"   {n} trades, {len(''.join(H))//1000}KB")


if __name__ == "__main__":
    main()
