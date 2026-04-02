"""Message formatting for Telegram."""

from datetime import datetime, timezone, timedelta

# GMT+1 offset
GMT_PLUS_1 = timedelta(hours=1)


def to_gmt1(ts_str: str) -> str:
    """Convert ISO timestamp string to GMT+1 formatted string."""
    try:
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_gmt1 = dt.astimezone(timezone(GMT_PLUS_1))
        return dt_gmt1.strftime('%d/%m/%Y %H:%M')
    except Exception:
        return ts_str[:16] if ts_str else '?'


def format_alert_notification(alert: dict) -> str:
    """Format a raw alert for initial notification."""
    pair = alert.get("pair", "?")
    score = alert.get("scanner_score", 0)
    tfs = ", ".join(alert.get("timeframes", []))
    price = alert.get("price", 0)
    ts = to_gmt1(alert.get("alert_timestamp", ""))

    emoji = "🟢" if score >= 9 else "🟡" if score >= 7 else "🟠"

    return (
        f"{emoji} *MEGA BUY Signal*\n"
        f"*{pair}* — Score *{score}/10*\n"
        f"💰 Prix: `{price}`\n"
        f"📊 TF: {tfs} | {ts}\n"
        f"\n_🤖 Analyse MEGA en cours..._"
    )


def format_recommendation(pair: str, decision: str, confidence: float,
                           analysis: dict, reasoning: str) -> str:
    """Format the full recommendation message."""
    # Decision emoji
    dec_emoji = {"BUY": "🟢", "WATCH": "🟡", "SKIP": "🔴"}.get(decision, "⚪")

    # Entry conditions
    ec = analysis.get("entry_conditions", {})
    ec_count = ec.get("count", 0)
    ec_total = ec.get("total", 5)

    # Bonus
    bf = analysis.get("bonus_filters", {})
    bf_count = bf.get("count", 0)
    bf_total = bf.get("total", 23)

    # Prerequisites
    prereqs = analysis.get("prerequisites", {})
    stc_valid = prereqs.get("stc_oversold")
    tl_valid = prereqs.get("trendline")

    # Indicators
    ind = analysis.get("indicators", {})
    rsi_1h = ind.get("1h", {}).get("rsi", "?")
    rsi_4h = ind.get("4h", {}).get("rsi", "?")
    adx_4h = ind.get("4h", {}).get("adx", "?")

    # Price for SL/TP
    price = analysis.get("alert_price") or ind.get("1h", {}).get("price", 0)
    sl = price * 0.95 if price else 0
    tp1 = price * 1.15 if price else 0
    rr = 3.0 if price else 0

    conf_pct = int(confidence * 100)

    lines = [
        f"🎯 *{pair}* — MEGA BUY",
        f"",
        f"{dec_emoji} *Decision: {decision}* ({conf_pct}% confiance)",
        f"",
        f"📈 *Indicateurs:*",
        f"• Conditions: {ec_count}/{ec_total}",
        f"• Bonus: {bf_count}/{bf_total}",
        f"• STC Oversold: {'✅' if stc_valid else '❌'}",
        f"• Trendline: {'✅' if tl_valid else '❌'}",
        f"• RSI 1H/4H: {_fmt(rsi_1h)}/{_fmt(rsi_4h)}",
        f"• ADX 4H: {_fmt(adx_4h)}",
    ]

    if decision == "BUY" and price:
        lines.extend([
            f"",
            f"💰 *Entry:* `{price:.6f}`",
            f"🛡️ *SL:* `{sl:.6f}` (\\-5%)",
            f"🎯 *TP1:* `{tp1:.6f}` (\\+15%)",
            f"📐 *R:R =* 1:{rr:.1f}",
        ])

    # Reasoning (truncate)
    short_reason = reasoning[:300] if len(reasoning) > 300 else reasoning
    lines.extend([
        f"",
        f"🧠 _{short_reason}_",
    ])

    return "\n".join(lines)


def format_portfolio(data: dict) -> str:
    """Format portfolio status."""
    g = data.get("global", {})
    lines = [
        "📊 *Portfolio Simulation*",
        f"💰 Balance: ${g.get('total_balance', 0):,.2f}",
        f"📈 Return: {g.get('total_return_pct', 0):+.2f}%",
        f"📦 Open: {g.get('total_open_positions', 0)} positions",
        "",
    ]
    for p in data.get("portfolios", []):
        emoji = "🟢" if p.get("return_pct", 0) > 0 else "🔴"
        lines.append(f"{emoji} {p['name']}: ${p['balance']:,.0f} ({p['return_pct']:+.1f}%) | {p['open_positions']} pos")

    return "\n".join(lines)


def format_status(cb_status: dict, memory_stats: dict) -> str:
    """Format agent status."""
    cb = cb_status
    ms = memory_stats
    active = "🔴 TRIPPED" if cb.get("active") else "🟢 OK"

    return (
        f"🤖 *OpenClaw Status*\n"
        f"\n"
        f"Circuit Breaker: {active}\n"
        f"Daily: {cb.get('daily_losses', '?')} losses | {cb.get('daily_wins', 0)} wins\n"
        f"Weekly: {cb.get('weekly_losses', '?')} losses | {cb.get('weekly_wins', 0)} wins\n"
        f"Total processed: {cb.get('total_processed', 0)}\n"
        f"\n"
        f"🧠 *Memory*\n"
        f"Patterns: {ms.get('total_patterns', 0)}\n"
        f"Win rate: {ms.get('win_rate', 0)}%\n"
        f"Pending: {ms.get('pending', 0)}"
    )


def _fmt(v) -> str:
    """Format a number for display."""
    if v is None or v == "?":
        return "?"
    try:
        return f"{float(v):.1f}"
    except (ValueError, TypeError):
        return str(v)
