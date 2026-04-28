#!/usr/bin/env python3
"""Audit detaille trade-par-trade du portfolio V11B (Compression).

For each closed V11B trade:
  1. Re-verifies the entry filter conditions (range_30m ≤ 1.89, range_4h ≤ 2.58) were truly met
  2. Reconstructs the entry rationale (with exact values)
  3. Reconstructs the exit narrative (TP1/TP2/Trail/SL/Timeout — what fired and when)
  4. Computes hold duration
  5. Flags any inconsistency

Outputs a single markdown file with all 247+ trades, each as a collapsible card.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from openclaw.config import get_settings
from supabase import create_client


TABLE_POS = "openclaw_positions_v11b"
TABLE_STATE = "openclaw_portfolio_state_v11b"

# V11B gate thresholds (must match manager_v11)
THR_R30M = 1.89
THR_R4H = 2.58

# Hybrid TP exit constants
SL_PCT = 8.0
TP1_PCT = 10.0; TP1_FRAC = 0.50
TP2_PCT = 20.0; TP2_FRAC = 0.30
TRAIL_DIST_PCT = 8.0
SIZE_USD = 400.0  # 8% of $5K


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


def build_entry_narrative(pair: str, fp: dict, alert: dict, valid_check: tuple) -> str:
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

    lines = []
    valid_r30, valid_r4 = valid_check
    sym30 = "✅" if valid_r30 else "❌"
    sym4 = "✅" if valid_r4 else "❌"

    lines.append(f"**Conditions du filtre V11B (gate)** :")
    lines.append(f"- {sym30} `range_30m = {r30 if r30 is not None else 'N/A'}%` ≤ {THR_R30M}%")
    lines.append(f"- {sym4} `range_4h = {r4 if r4 is not None else 'N/A'}%` ≤ {THR_R4H}%")
    if not (valid_r30 and valid_r4):
        lines.append(f"- 🚨 **Trade INVALIDE** : ce trade n'aurait pas dû être ouvert (échec filtre).")
    else:
        lines.append(f"- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.")
    lines.append("")
    lines.append("**Contexte au moment de l'alerte** :")
    lines.append(f"- Scanner score : **{score}/10**")
    if decision and decision != "?":
        conf_s = f" ({conf*100:.0f}% confiance)" if conf else ""
        lines.append(f"- Décision OpenClaw : **{decision}**{conf_s}")
    if body4 is not None:
        lines.append(f"- Bougie 4H : direction **{direction4}**, body {body4:.2f}%")
    if rsi: lines.append(f"- RSI : {rsi:.1f}")
    if adx: lines.append(f"- ADX 4H : {adx:.1f} (DI+ {di_p:.0f} / DI- {di_m:.0f})")
    if chg24 is not None: lines.append(f"- Change 24h : {chg24:+.2f}%")
    if btc_trend != "?": lines.append(f"- BTC trend 1H : `{btc_trend}`")
    if fg is not None: lines.append(f"- Fear & Greed : {fg}")

    return "\n".join(lines)


def build_exit_narrative(t: dict, hours_held: float) -> str:
    entry = t.get("entry_price", 0)
    exit_p = t.get("exit_price", 0)
    high = t.get("highest_price", 0)
    pnl_pct = t.get("pnl_pct", 0)
    pnl_usd = t.get("pnl_usd", 0)
    p1 = t.get("partial1_done", False)
    p2 = t.get("partial2_done", False)
    trail = t.get("trail_active", False)
    reason_raw = t.get("close_reason") or ""
    # close_reason format: "HYDRATED_BACKTEST:<original_reason>" or just reason
    reason = reason_raw.split(":", 1)[1] if ":" in reason_raw else reason_raw
    is_hydrated = reason_raw.startswith("HYDRATED_BACKTEST:")

    peak_pct = (high - entry) / entry * 100 if entry else 0

    lines = []
    lines.append(f"**Trajectoire** :")
    lines.append(f"- Entry : `{fmt_price(entry)}`")
    lines.append(f"- Peak atteint : `{fmt_price(high)}` (**{fmt_pct(peak_pct)}** du peak)")
    lines.append(f"- Exit : `{fmt_price(exit_p)}`")
    lines.append(f"- Hold : {fmt_dur(hours_held)}")
    lines.append("")
    lines.append(f"**Évènements (logique exit hybride V7)** :")

    if reason == "SL_HIT":
        sl_price = entry * (1 - SL_PCT/100)
        lines.append(f"- ❌ **Stop Loss touché à {fmt_price(sl_price)}** (-{SL_PCT}% sous l'entry).")
        lines.append(f"- Le prix n'a JAMAIS atteint TP1 (+{TP1_PCT}%, soit `{fmt_price(entry*(1+TP1_PCT/100))}`).")
        lines.append(f"- Position fermée à 100% au prix du SL.")
    elif reason == "BREAKEVEN_STOP":
        tp1_price = entry * (1 + TP1_PCT/100)
        lines.append(f"- ✅ **TP1 hit** à `{fmt_price(tp1_price)}` (+{TP1_PCT}%) → fermeture de **50%** = profit locké de **${SIZE_USD * TP1_FRAC * TP1_PCT/100:.2f}**.")
        lines.append(f"- 🛡 Stop déplacé à BREAKEVEN (`{fmt_price(entry)}`).")
        lines.append(f"- Le prix n'a PAS atteint TP2 (+{TP2_PCT}%) → est redescendu à BE.")
        lines.append(f"- Les 50% restants fermés au breakeven (0% sur cette portion).")
    elif reason == "TRAIL_STOP":
        tp1_price = entry * (1 + TP1_PCT/100)
        tp2_price = entry * (1 + TP2_PCT/100)
        trail_exit_pct = (exit_p - entry) / entry * 100 if entry else 0
        lines.append(f"- ✅ **TP1 hit** à `{fmt_price(tp1_price)}` (+{TP1_PCT}%) → 50% fermé = ${SIZE_USD * TP1_FRAC * TP1_PCT/100:.2f}")
        lines.append(f"- ✅✅ **TP2 hit** à `{fmt_price(tp2_price)}` (+{TP2_PCT}%) → 30% fermé = ${SIZE_USD * TP2_FRAC * TP2_PCT/100:.2f}")
        lines.append(f"- 🔄 **Trailing activé** sur les 20% restants (distance -{TRAIL_DIST_PCT}% du peak)")
        lines.append(f"- 📈 Peak final : `{fmt_price(high)}` ({fmt_pct(peak_pct)})")
        lines.append(f"- 🚪 Trail stop touché à `{fmt_price(exit_p)}` ({fmt_pct(trail_exit_pct)}) → 20% fermé.")
    elif reason == "TIMEOUT_72H":
        tp1_price = entry * (1 + TP1_PCT/100)
        if p1:
            lines.append(f"- ✅ **TP1 hit** (50% fermé à +{TP1_PCT}%)")
            if p2:
                lines.append(f"- ✅ **TP2 hit** (30% fermé à +{TP2_PCT}%)")
            lines.append(f"- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel ({fmt_pct((exit_p-entry)/entry*100 if entry else 0)})")
        else:
            lines.append(f"- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`{fmt_price(tp1_price)}`) ni SL (-{SL_PCT}%)")
            lines.append(f"- Position fermée à 100% au prix de fin de fenêtre.")
    else:
        lines.append(f"- 🔔 Close reason : `{reason}` (cas non standard)")

    lines.append("")
    pnl_realized = t.get("realized_pnl_usd") or pnl_usd or 0
    profit_emoji = "💰" if pnl_realized > 0 else "💔"
    lines.append(f"**PnL final** : {profit_emoji} **{fmt_pct(pnl_pct)}** ({pnl_realized:+.2f}$ sur ${SIZE_USD} investis)")
    if is_hydrated:
        lines.append("")
        lines.append("_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._")
    return "\n".join(lines)


def main():
    s = get_settings()
    sb = create_client(s.supabase_url, s.supabase_service_key)

    print("📥 Loading V11B closed trades...", flush=True)
    rows = []
    cursor = 0
    while True:
        r = sb.table(TABLE_POS).select("*").eq("status", "CLOSED").order(
            "opened_at", desc=False
        ).range(cursor, cursor + 999).execute()
        chunk = r.data or []
        rows.extend(chunk)
        if len(chunk) < 1000: break
        cursor += 1000

    print(f"   {len(rows)} closed trades loaded")

    # Get state
    state_r = sb.table(TABLE_STATE).select("*").eq("id", "main").single().execute()
    state = state_r.data or {}

    # Fetch agent_memory features for each alert_id
    aids = list({r["alert_id"] for r in rows if r.get("alert_id")})
    print(f"📥 Fetching features_fingerprint for {len(aids)} alerts...", flush=True)
    fp_map = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("agent_memory").select(
            "alert_id,features_fingerprint,agent_decision,agent_confidence,scanner_score,outcome"
        ).in_("alert_id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            fp_map[x["alert_id"]] = x

    alert_map = {}
    for i in range(0, len(aids), 100):
        rr = sb.table("alerts").select(
            "id,alert_timestamp,price,puissance,emotion,nb_timeframes,timeframes,rsi,di_plus_4h,di_minus_4h,adx_4h,pp,ec"
        ).in_("id", aids[i:i+100]).execute()
        for x in (rr.data or []):
            alert_map[x["id"]] = x

    # Stats
    n = len(rows)
    wins = sum(1 for r in rows if (r.get("pnl_usd") or 0) > 0)
    losses = n - wins
    wr = wins/n*100 if n else 0
    total_pnl = sum(r.get("pnl_usd") or 0 for r in rows)
    avg_pnl = sum(r.get("pnl_pct") or 0 for r in rows) / n if n else 0
    avg_hold = sum(hold_hours(r.get("opened_at",""), r.get("closed_at","")) for r in rows) / n if n else 0

    # Reason breakdown
    reasons = {}
    for r in rows:
        rr = (r.get("close_reason") or "").split(":",1)[1] if ":" in (r.get("close_reason") or "") else r.get("close_reason","?")
        reasons[rr] = reasons.get(rr, 0) + 1

    # Validity check
    invalid_count = 0
    for r in rows:
        aid = r.get("alert_id")
        if not aid or aid not in fp_map:
            invalid_count += 1
            continue
        fp = (fp_map[aid].get("features_fingerprint") or {})
        r30 = fp.get("candle_30m_range_pct")
        r4 = fp.get("candle_4h_range_pct")
        if r30 is None or r30 > THR_R30M or r4 is None or r4 > THR_R4H:
            invalid_count += 1

    # Build markdown
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    L = []
    L.append("# 🔬 Audit detaille V11B Compression — chaque trade, entry & exit")
    L.append("")
    L.append(f"_Genere : {today}_")
    L.append("")
    L.append("**Filtre V11B** : `Range 30m ≤ 1.89%` ET `Range 4h ≤ 2.58%`")
    L.append("**Exit hybride V7** : TP1 50%@+10% / TP2 30%@+20% / Trail 20% à -8% du peak / SL initial -8% / Timeout 72h")
    L.append(f"**Capital initial** : $5,000 — **Size par position** : $400 (8%)")
    L.append("")

    L.append("## 📊 Résumé global")
    L.append("")
    L.append(f"- **Trades fermés** : {n}")
    L.append(f"- **WR** : {wr:.1f}% ({wins}W / {losses}L)")
    L.append(f"- **PnL total** : ${total_pnl:+.2f}")
    L.append(f"- **Avg PnL/trade** : {avg_pnl:+.2f}%")
    L.append(f"- **Hold time moyen** : {fmt_dur(avg_hold)}")
    L.append(f"- **Balance finale** : ${state.get('balance', 0):.2f} (init $5,000 → ROI {(state.get('balance',5000)-5000)/5000*100:+.1f}%)")
    L.append("")

    L.append("### Distribution close_reason")
    L.append("")
    L.append("| Raison | Count | % |")
    L.append("|---|---:|---:|")
    for r, c in sorted(reasons.items(), key=lambda x: x[1], reverse=True):
        L.append(f"| `{r}` | {c} | {c/n*100:.1f}% |")
    L.append("")

    if invalid_count > 0:
        L.append(f"### ⚠️ Validité du filtre")
        L.append("")
        L.append(f"**{invalid_count} trades** ne semblent pas correspondre au filtre V11B (données features manquantes ou seuils non respectés). Voir les badges 🚨 dans les cartes individuelles.")
        L.append("")
    else:
        L.append("### ✅ Validité du filtre")
        L.append("")
        L.append(f"**Tous les {n} trades** ont des features confirmant `range_30m ≤ {THR_R30M}` ET `range_4h ≤ {THR_R4H}` au moment de l'alerte. Filtre 100% respecté.")
        L.append("")

    L.append("---")
    L.append("")

    # Top winners and losers
    sorted_by_pnl = sorted(rows, key=lambda x: x.get("pnl_usd") or 0, reverse=True)
    top_winners = sorted_by_pnl[:5]
    top_losers = sorted_by_pnl[-5:]

    L.append("## 🏆 Top 5 winners")
    L.append("")
    for i, r in enumerate(top_winners, 1):
        L.append(f"{i}. **{r.get('pair')}** — {fmt_pct(r.get('pnl_pct'))} ({r.get('pnl_usd', 0):+.2f}$) — exit: `{(r.get('close_reason') or '').split(':',1)[-1]}`")
    L.append("")

    L.append("## 💔 Top 5 losers")
    L.append("")
    for i, r in enumerate(top_losers, 1):
        L.append(f"{i}. **{r.get('pair')}** — {fmt_pct(r.get('pnl_pct'))} ({r.get('pnl_usd', 0):+.2f}$) — exit: `{(r.get('close_reason') or '').split(':',1)[-1]}`")
    L.append("")

    L.append("---")
    L.append("")
    L.append("## 📋 Audit complet — un trade par carte")
    L.append("")
    L.append(f"_{n} trades, classés par date d'ouverture (le plus ancien en premier)._")
    L.append("")
    L.append("Chaque carte est dépliable : clique sur ▶️ pour voir le détail complet (entry rationale + exit narrative).")
    L.append("")

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

        # Get fp + alert
        aid = r.get("alert_id")
        fp_row = fp_map.get(aid, {})
        fp = fp_row.get("features_fingerprint") or {}
        alert = alert_map.get(aid, {})
        # Alert may not have features_fingerprint, but agent_memory does — and may have decision/conf at top level
        for key in ("agent_decision", "agent_confidence", "scanner_score", "outcome"):
            if key not in fp and key in fp_row:
                fp[key] = fp_row[key]

        # Validity check — prefer gate_snapshot (immutable) over current FP
        snap = r.get("gate_snapshot") or {}
        r30v = snap.get("candle_30m_range_pct") if snap else fp.get("candle_30m_range_pct")
        r4v = snap.get("candle_4h_range_pct") if snap else fp.get("candle_4h_range_pct")
        valid = (r30v is not None and r30v <= THR_R30M and r4v is not None and r4v <= THR_R4H)

        validity_badge = "" if valid else " 🚨"
        title = f"<summary>[#{i}] {emoji} <b>{pair}</b> {fmt_pct(pnl_pct)} ({pnl_usd:+.1f}$) — {date_short} — exit: <code>{reason}</code> — hold {fmt_dur(hours)}{validity_badge}</summary>"

        L.append("<details>")
        L.append(title)
        L.append("")
        L.append("### Entry")
        L.append("")
        L.append(build_entry_narrative(pair, fp, alert, (r30v is not None and r30v <= THR_R30M, r4v is not None and r4v <= THR_R4H)))
        L.append("")
        L.append("### Exit")
        L.append("")
        L.append(build_exit_narrative(r, hours))
        L.append("")
        L.append("</details>")
        L.append("")

    out_path = Path(__file__).parent.parent.parent / f"V11B_TRADE_AUDIT_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    out_path.write_text("\n".join(L), encoding="utf-8")
    print(f"\n✅ Report written: {out_path}")
    print(f"   {len(L)} lines, ~{sum(len(x) for x in L)//1000}KB")
    print(f"   {n} trades documented ({wins}W/{losses}L, WR {wr:.1f}%)")
    if invalid_count > 0:
        print(f"   ⚠️ {invalid_count} trades flagged as potentially invalid")


if __name__ == "__main__":
    main()
