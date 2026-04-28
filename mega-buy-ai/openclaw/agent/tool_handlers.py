"""Python implementations backing each Claude tool.

Each handler is an async function that takes the tool input dict
and returns a JSON-serializable result.
"""

import sys
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

import requests

# Add project paths for imports
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_project_root / "backtest"))
sys.path.insert(0, str(_project_root.parent / "python"))

from openclaw.config import get_settings


# ============================================================
# Tool: read_alert
# ============================================================
async def handle_read_alert(alert_id: str, **kwargs) -> Dict:
    """Read full alert from Supabase."""
    settings = get_settings()
    from supabase import create_client
    sb = create_client(settings.supabase_url, settings.supabase_service_key)
    result = sb.table("alerts").select("*, decisions(*)").eq("id", alert_id).single().execute()
    return result.data if result.data else {"error": f"Alert {alert_id} not found"}


# ============================================================
# Tool: analyze_alert
# ============================================================
async def handle_analyze_alert(pair: str, timestamp: str = "", price: float = 0, **kwargs) -> Dict:
    """Compute technical indicators + ML prediction + backtest in ONE call.

    Returns a SMART summary with everything Claude needs to decide.
    """
    from api.realtime_analyze import analyze_alert_realtime
    result = await asyncio.to_thread(analyze_alert_realtime, pair, timestamp, price)
    summary = _smart_summary(result)

    # Also include ML prediction and backtest inline (saves 2 tool round-trips)
    try:
        ml = await handle_get_ml_prediction(
            pair=pair, price=price,
            scanner_score=kwargs.get("scanner_score", 0),
            pp=kwargs.get("pp", False), ec=kwargs.get("ec", False),
            di_plus_4h=kwargs.get("di_plus_4h", 0),
            di_minus_4h=kwargs.get("di_minus_4h", 0),
            adx_4h=kwargs.get("adx_4h", 0),
        )
        summary["ml_prediction"] = f"p_success={ml.get('p_success', 0):.2f} decision={ml.get('decision', 'N/A')} confidence={ml.get('confidence', 0):.2f}"
    except Exception:
        summary["ml_prediction"] = "unavailable"

    try:
        bt = await handle_get_backtest_history(pair=pair)
        if bt.get("total_trades", 0) > 0:
            summary["backtest"] = f"{bt['total_trades']} trades, WR={bt['win_rate_pct']}%, avg_pnl={bt.get('avg_pnl_c', 0):.1f}%"
        else:
            summary["backtest"] = "no data"
    except Exception:
        summary["backtest"] = "unavailable"

    return summary


def _smart_summary(data: Dict) -> Dict:
    """Smart summary — keeps ALL key indicator VALUES but in compact format.
    ~2K tokens instead of ~8K for the full dump."""
    if not data or "error" in data:
        return data

    s = {"pair": data.get("pair"), "alert_price": data.get("alert_price"), "mode": data.get("mode")}

    # Entry conditions with values + TOLERANCE -2% rule
    ec = data.get("entry_conditions", {})
    hard_valid = 0
    quasi_valid = 0
    TOLERANCE_PCT = -2.0  # Accept conditions within -2% of threshold

    for k in ["ema100_1h", "ema20_4h", "cloud_1h", "cloud_30m", "choch_bos"]:
        v = ec.get(k, {})
        if not isinstance(v, dict):
            continue

        is_valid = v.get("valid", False)
        dist = v.get("distance_pct")

        if is_valid:
            hard_valid += 1
            label = "✓"
        elif dist is not None and dist >= TOLERANCE_PCT:
            quasi_valid += 1
            label = "≈"  # quasi-validated (within -2%)
        else:
            label = "✗"

        if dist is not None:
            s[k] = f"{label} {dist:.1f}%"
        else:
            s[k] = label

    effective_count = hard_valid + quasi_valid
    s["conditions"] = f"{hard_valid}/{ec.get('total', 5)} (effective: {effective_count}/5 with -2% tolerance)"
    if quasi_valid > 0:
        s["conditions_note"] = f"{quasi_valid} condition(s) quasi-validee(s) (entre -2% et 0%)"

    # Prerequisites
    p = data.get("prerequisites", {})
    stc = p.get("stc_oversold", {})
    s["stc"] = f"{'✓' if stc.get('valid') else '✗'} tfs={stc.get('valid_tfs', [])} vals={stc.get('values', {})}"
    tl = p.get("trendline", {})
    s["trendline"] = f"{'✓' if tl.get('valid') else '✗'} price={tl.get('price')}"

    # Bonus filters — compact with key detail
    bf = data.get("bonus_filters", {})
    s["bonus"] = f"{bf.get('count', 0)}/{bf.get('total', 0)}"
    bonus_details = {}
    for k in ["fib_4h", "fib_1h", "ob_1h", "ob_4h", "fvg_1h", "fvg_4h",
              "btc_corr_1h", "btc_corr_4h", "eth_corr_1h", "eth_corr_4h",
              "vol_spike_1h", "vol_spike_4h", "rsi_mtf",
              "adx_1h", "adx_4h", "macd_1h", "macd_4h",
              "bb_1h", "bb_4h", "stochrsi_1h", "stochrsi_4h",
              "ema_stack_1h", "ema_stack_4h"]:
        v = bf.get(k, {})
        if not isinstance(v, dict):
            continue
        parts = ["✓" if v.get("bonus") else "✗"]
        for dk in ["trend", "strength", "ratio", "zone", "count", "aligned_count", "position",
                   "adx", "di_plus", "di_minus", "di_spread", "histogram", "growing", "k", "d"]:
            if dk in v and v[dk] is not None:
                val = v[dk]
                if isinstance(val, float):
                    parts.append(f"{dk}={val:.1f}")
                else:
                    parts.append(f"{dk}={val}")
        bonus_details[k] = " ".join(parts)
    s["filters"] = bonus_details

    # Indicators — compact per TF
    ind = data.get("indicators", {})
    for tf in ["1h", "4h", "1d"]:
        d = ind.get(tf, {})
        if d:
            parts = []
            for ik in ["price", "rsi", "adx", "di_plus", "di_minus", "cloud_top", "stc"]:
                if ik in d and d[ik] is not None:
                    parts.append(f"{ik}={d[ik]:.2f}" if isinstance(d[ik], float) else f"{ik}={d[ik]}")
            s[f"ind_{tf}"] = " | ".join(parts)

    # Volume Profile — compact
    vp = data.get("volume_profile", {})
    for tf in ["1h", "4h"]:
        v = vp.get(tf)
        if v and isinstance(v, dict) and not v.get("error") and v.get("poc"):
            s[f"vp_{tf}"] = f"POC={v['poc']} VAH={v.get('vah')} VAL={v.get('val')} pos={v.get('position')} dist={v.get('poc_distance_pct', 0):.1f}%"

    # OB blocks — only nearest
    for tf in ["1h", "4h"]:
        ob = bf.get(f"ob_{tf}", {})
        if ob.get("blocks"):
            top = ob["blocks"][0]
            s[f"ob_{tf}_nearest"] = f"{top.get('zone_low')}-{top.get('zone_high')} {top.get('position')} {top.get('distance_pct', 0):.1f}% str={top.get('strength')} {'mitigated' if top.get('mitigated') else 'fresh'}"

    # Futures data (funding + OI)
    futures = data.get("futures_data", {})
    if futures.get("available", False):
        s["futures"] = f"Funding={futures.get('funding_rate_pct', 0):.4f}% OI_change_24h={futures.get('oi_change_24h_pct', 0):.1f}% signal={futures.get('signal', 'N/A')}"

    # Accumulation data (for VIP check)
    acc = data.get("accumulation", {})
    if isinstance(acc, dict) and acc.get("detected"):
        s["accumulation"] = acc

    return s


def _summarize_analysis(data: Dict) -> Dict:
    """Keep key fields, drop raw arrays to save tokens."""
    if not data or "error" in data:
        return data

    summary = {
        "pair": data.get("pair"),
        "mode": data.get("mode"),
        "alert_price": data.get("alert_price"),
        "timing_seconds": data.get("timing", {}).get("total_seconds"),
    }

    # Entry conditions (compact)
    ec = data.get("entry_conditions", {})
    summary["entry_conditions"] = {
        "count": ec.get("count", 0),
        "total": ec.get("total", 5),
    }
    for key in ["ema100_1h", "ema20_4h", "cloud_1h", "cloud_30m", "choch_bos"]:
        if key in ec:
            summary["entry_conditions"][key] = {
                "valid": ec[key].get("valid"),
                "distance_pct": ec[key].get("distance_pct"),
            }

    # Prerequisites
    prereqs = data.get("prerequisites", {})
    summary["prerequisites"] = {
        "stc_oversold": prereqs.get("stc_oversold", {}).get("valid"),
        "stc_tfs": prereqs.get("stc_oversold", {}).get("valid_tfs", []),
        "trendline": prereqs.get("trendline", {}).get("valid"),
        "tl_price": prereqs.get("trendline", {}).get("price"),
    }

    # Bonus filters (compact: just bonus true/false + key detail)
    bf = data.get("bonus_filters", {})
    summary["bonus_filters"] = {
        "count": bf.get("count", 0),
        "total": bf.get("total", 0),
    }
    for key in ["fib_4h", "fib_1h", "ob_1h", "ob_4h", "fvg_1h", "fvg_4h",
                "btc_corr_1h", "btc_corr_4h", "eth_corr_1h", "eth_corr_4h",
                "vol_spike_1h", "vol_spike_4h", "rsi_mtf",
                "adx_1h", "adx_4h", "macd_1h", "macd_4h",
                "bb_1h", "bb_4h", "stochrsi_1h", "stochrsi_4h",
                "ema_stack_1h", "ema_stack_4h"]:
        val = bf.get(key, {})
        if isinstance(val, dict):
            compact = {"bonus": val.get("bonus", False)}
            for detail_key in ["trend", "strength", "ratio", "zone", "count", "aligned_count", "position"]:
                if detail_key in val:
                    compact[detail_key] = val[detail_key]
            summary["bonus_filters"][key] = compact

    # Key indicators (price, RSI, ADX per TF)
    ind = data.get("indicators", {})
    summary["indicators"] = {}
    for tf in ["1h", "4h", "1d"]:
        if tf in ind:
            summary["indicators"][tf] = {
                k: ind[tf][k] for k in ["price", "rsi", "adx", "di_plus", "di_minus", "cloud_top"]
                if k in ind[tf]
            }

    # Volume Profile (compact)
    vp = data.get("volume_profile", {})
    for tf in ["1h", "4h"]:
        v = vp.get(tf)
        if v and not isinstance(v, dict) or (isinstance(v, dict) and not v.get("error")):
            summary[f"vp_{tf}"] = {
                k: v.get(k) for k in ["poc", "vah", "val", "position", "poc_distance_pct"]
                if v and k in v
            }

    return summary


# ============================================================
# Tool: get_ml_prediction
# ============================================================
async def handle_get_ml_prediction(pair: str, price: float = 0, scanner_score: int = 0,
                                    timeframes: list = None, **kwargs) -> Dict:
    """Get ML prediction from DecisionCore."""
    try:
        from services.decision_core.ml_model import get_decision_core
        dc = get_decision_core()

        # Build alert data matching what DecisionCore expects
        alert_data = {
            "pair": pair,
            "price": price,
            "scanner_score": scanner_score,
            "timeframes": timeframes or [],
            "pp": kwargs.get("pp", False),
            "ec": kwargs.get("ec", False),
            "di_plus_4h": kwargs.get("di_plus_4h", 0),
            "di_minus_4h": kwargs.get("di_minus_4h", 0),
            "adx_4h": kwargs.get("adx_4h", 0),
        }

        result = await asyncio.to_thread(dc.decide, alert_data)

        if isinstance(result, dict):
            return {
                "p_success": result.get("p_success", 0),
                "decision": result.get("decision", "SKIP"),
                "confidence": result.get("confidence", 0),
                "rules_applied": result.get("rules_applied", []),
                "entry_zone_low": result.get("entry_zone_low"),
                "entry_zone_high": result.get("entry_zone_high"),
                "stop_loss": result.get("stop_loss"),
            }
        return {"p_success": 0, "decision": "SKIP", "error": "No result from model"}

    except ImportError as e:
        # If ML model can't load, provide a rule-based fallback
        return _rules_based_prediction(scanner_score, kwargs)
    except Exception as e:
        return _rules_based_prediction(scanner_score, kwargs, error=str(e))


def _rules_based_prediction(score: int, kwargs: dict, error: str = None) -> Dict:
    """Simple rules-based fallback when ML model is unavailable."""
    pp = kwargs.get("pp", False)
    ec = kwargs.get("ec", False)
    di_minus = kwargs.get("di_minus_4h", 0) or 0
    di_plus = kwargs.get("di_plus_4h", 0) or 0
    adx = kwargs.get("adx_4h", 0) or 0

    # Simple scoring
    p = 0.3  # Base
    if score >= 9: p += 0.15
    elif score >= 7: p += 0.05
    if pp: p += 0.1
    if ec: p += 0.05
    if di_minus >= 22 and di_plus <= 25: p += 0.1  # Max WR filter
    if adx >= 25: p += 0.05

    p = min(p, 0.95)
    decision = "TRADE" if p >= 0.5 else "WATCH" if p >= 0.35 else "SKIP"

    result = {
        "p_success": round(p, 3),
        "decision": decision,
        "confidence": round(p, 2),
        "method": "rules_fallback",
        "rules_applied": [],
    }
    if error:
        result["ml_error"] = error
    return result


# ============================================================
# Tool: get_backtest_history
# ============================================================
async def handle_get_backtest_history(pair: str, **kwargs) -> Dict:
    """Query backtest SQLite DB for historical trades."""
    settings = get_settings()
    db_path = settings.backtest_db_path

    def _query():
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Trades are linked to backtest_runs via backtest_run_id
            # The symbol/pair is in backtest_runs, not in trades
            cur.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN t.pnl_c > 0 THEN 1 ELSE 0 END) as wins,
                       AVG(t.pnl_c) as avg_pnl_c,
                       AVG(t.pnl_d) as avg_pnl_d,
                       MAX(t.pnl_c) as best_pnl,
                       MIN(t.pnl_c) as worst_pnl,
                       AVG(t.v3_quality_score) as avg_quality
                FROM trades t
                JOIN backtest_runs br ON t.backtest_run_id = br.id
                WHERE br.symbol = ? AND t.entry_price IS NOT NULL
            """, (pair,))
            row = cur.fetchone()
            conn.close()

            if not row or row["total"] == 0:
                return {"pair": pair, "total_trades": 0, "message": "No backtest data for this pair"}

            total = row["total"]
            wins = row["wins"] or 0
            return {
                "pair": pair,
                "total_trades": total,
                "wins": wins,
                "win_rate_pct": round(wins / total * 100, 1) if total > 0 else 0,
                "avg_pnl_c": round(row["avg_pnl_c"], 2) if row["avg_pnl_c"] else 0,
                "avg_pnl_d": round(row["avg_pnl_d"], 2) if row["avg_pnl_d"] else 0,
                "best_trade_pnl": round(row["best_pnl"], 2) if row["best_pnl"] else 0,
                "worst_trade_pnl": round(row["worst_pnl"], 2) if row["worst_pnl"] else 0,
                "avg_quality_score": round(row["avg_quality"], 1) if row["avg_quality"] else None,
            }
        except Exception as e:
            return {"pair": pair, "error": str(e)}

    return await asyncio.to_thread(_query)


# ============================================================
# Tool: get_market_context
# ============================================================
async def handle_get_market_context(**kwargs) -> Dict:
    """Fetch BTC trend + Fear & Greed Index."""
    def _fetch():
        result = {}
        # BTC price & trend
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                           params={"symbol": "BTCUSDT"}, timeout=10)
            data = r.json()
            result["btc"] = {
                "price": float(data.get("lastPrice", 0)),
                "change_24h_pct": float(data.get("priceChangePercent", 0)),
                "volume_24h": float(data.get("quoteVolume", 0)),
            }
        except Exception:
            result["btc"] = {"error": "Failed to fetch"}

        # Fear & Greed Index
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=10)
            data = r.json()
            fng = data.get("data", [{}])[0]
            result["fear_greed"] = {
                "value": int(fng.get("value", 0)),
                "label": fng.get("value_classification", "Unknown"),
            }
        except Exception:
            result["fear_greed"] = {"value": 50, "label": "Unknown"}

        # ETH
        try:
            r = requests.get("https://api.binance.com/api/v3/ticker/24hr",
                           params={"symbol": "ETHUSDT"}, timeout=10)
            data = r.json()
            result["eth"] = {
                "price": float(data.get("lastPrice", 0)),
                "change_24h_pct": float(data.get("priceChangePercent", 0)),
            }
        except Exception:
            pass

        return result

    return await asyncio.to_thread(_fetch)


# ============================================================
# Tool: get_similar_patterns
# ============================================================
async def handle_get_similar_patterns(scanner_score: int = 0, **kwargs) -> Dict:
    """Search agent memory for similar patterns."""
    settings = get_settings()
    try:
        from supabase import create_client
        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        result = sb.table("agent_memory") \
            .select("*") \
            .not_.is_("outcome", "null") \
            .order("created_at", desc=True) \
            .limit(50) \
            .execute()

        patterns = result.data or []
        if not patterns:
            return {"matches": [], "message": "No patterns in memory yet"}

        # Simple matching by score proximity and pair
        matches = []
        for p in patterns:
            fp = p.get("features_fingerprint", {})
            score_diff = abs(fp.get("scanner_score", 0) - scanner_score)
            if score_diff <= 2:
                matches.append({
                    "pair": p["pair"],
                    "decision": p["agent_decision"],
                    "outcome": p.get("outcome"),
                    "pnl_pct": p.get("pnl_pct"),
                    "confidence": p.get("agent_confidence"),
                    "score_diff": score_diff,
                })

        # Sort by relevance
        matches.sort(key=lambda x: x["score_diff"])
        return {"matches": matches[:10], "total_in_memory": len(patterns)}

    except Exception as e:
        return {"matches": [], "error": str(e)}


# ============================================================
# Tool: get_portfolio_status
# ============================================================
async def handle_get_portfolio_status(**kwargs) -> Dict:
    """Get simulation portfolio overview."""
    settings = get_settings()
    try:
        r = await asyncio.to_thread(
            requests.get, f"{settings.simulation_api_url}/api/overview", timeout=10
        )
        data = r.json()
        # Compact the response
        live = data.get("live", {})
        return {
            "running": data.get("running"),
            "global": live.get("global", {}),
            "portfolios": [
                {
                    "name": p["name"],
                    "balance": p["balance"],
                    "return_pct": p["return_pct"],
                    "open_positions": p["open_positions"],
                    "win_rate": p["win_rate"],
                }
                for p in live.get("portfolios", [])
            ]
        }
    except Exception as e:
        return {"error": str(e)}


# ============================================================
# Tool: send_recommendation (stub — wired by bot.py)
# ============================================================
_telegram_send_fn = None

def set_telegram_sender(fn):
    """Set the Telegram send function (called by bot.py on init)."""
    global _telegram_send_fn
    _telegram_send_fn = fn


async def handle_send_recommendation(message: str, decision: str = "WATCH",
                                      alert_id: str = "", **kwargs) -> Dict:
    """Send recommendation via Telegram."""
    if _telegram_send_fn:
        await _telegram_send_fn(message, decision, alert_id)
        return {"sent": True}
    return {"sent": False, "error": "Telegram bot not connected"}


# ============================================================
# Tool: record_decision
# ============================================================
async def handle_record_decision(alert_id: str, decision: str, confidence: float = 0,
                                  reasoning: str = "", **kwargs) -> Dict:
    """Record agent decision to Supabase."""
    settings = get_settings()
    try:
        from supabase import create_client
        sb = create_client(settings.supabase_url, settings.supabase_service_key)
        data = {
            "alert_id": alert_id,
            "decision": decision,
            "p_success": confidence,
            "confidence": confidence,
        }
        result = sb.table("decisions").insert(data).execute()
        return {"recorded": True, "id": result.data[0]["id"] if result.data else None}
    except Exception as e:
        return {"recorded": False, "error": str(e)}


# ============================================================
# Tool: record_outcome
# ============================================================
async def handle_record_outcome(alert_id: str, result: str, pnl_pct: float = 0,
                                 exit_reason: str = "", **kwargs) -> Dict:
    """Record trade outcome for learning."""
    settings = get_settings()
    try:
        from supabase import create_client
        sb = create_client(settings.supabase_url, settings.supabase_service_key)

        # Update agent_memory if exists
        sb.table("agent_memory") \
            .update({"outcome": result, "pnl_pct": pnl_pct}) \
            .eq("alert_id", alert_id) \
            .execute()

        return {"recorded": True}
    except Exception as e:
        return {"recorded": False, "error": str(e)}


# ============================================================
# Conversational query helpers — read-only Supabase queries for free-text Q&A
# ============================================================

def _portfolio_versions(version: str):
    """Return list of (version_label, table_suffix) tuples to query."""
    if version == "all":
        return [(v, "" if v == "v1" else f"_{v}") for v in
                ["v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"]]
    if version in {"v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8", "v9"}:
        return [(version, "" if version == "v1" else f"_{version}")]
    return [("v1", "")]


async def handle_get_recent_trades(days: int = 7, version: str = "all",
                                    status: str = "all", limit: int = 20, **kwargs) -> Dict:
    """Recent trades from openclaw_positions tables, optionally filtered by version/status."""
    from datetime import datetime, timezone, timedelta
    settings = get_settings()
    from supabase import create_client
    sb = create_client(settings.supabase_url, settings.supabase_service_key)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    rows: list = []
    for ver, suffix in _portfolio_versions(version):
        table = f"openclaw_positions{suffix}"
        try:
            q = sb.table(table).select("*").gte("opened_at", cutoff).order("opened_at", desc=True).limit(limit)
            if status.upper() in {"OPEN", "CLOSED"}:
                q = q.eq("status", status.upper())
            r = q.execute()
            for row in (r.data or []):
                rows.append({**row, "_version": ver})
        except Exception as e:
            rows.append({"_error": f"{table}: {type(e).__name__}: {str(e)[:80]}"})

    rows.sort(key=lambda r: r.get("opened_at") or "", reverse=True)
    rows = [r for r in rows if "_error" not in r][:limit]

    return {
        "count": len(rows),
        "days": days,
        "version_filter": version,
        "status_filter": status,
        "trades": [{
            "version": r.get("_version"),
            "pair": r.get("pair"),
            "status": r.get("status"),
            "decision": r.get("decision"),
            "confidence": r.get("confidence"),
            "scanner_score": r.get("scanner_score"),
            "entry_price": r.get("entry_price"),
            "current_price": r.get("current_price"),
            "exit_price": r.get("exit_price"),
            "pnl_pct": r.get("pnl_pct"),
            "pnl_usd": r.get("pnl_usd"),
            "size_usd": r.get("size_usd"),
            "sl_price": r.get("sl_price"),
            "tp_price": r.get("tp_price"),
            "close_reason": r.get("close_reason"),
            "opened_at": r.get("opened_at"),
            "closed_at": r.get("closed_at"),
        } for r in rows],
    }


async def handle_get_top_trades(metric: str = "pnl_pct", days: int = 7,
                                 version: str = "all", direction: str = "best",
                                 limit: int = 5, **kwargs) -> Dict:
    """Top winners or losers across portfolios. metric ∈ {pnl_pct, pnl_usd}, direction ∈ {best, worst}."""
    full = await handle_get_recent_trades(days=days, version=version, status="all", limit=500)
    trades = full.get("trades", [])
    metric_key = metric if metric in {"pnl_pct", "pnl_usd"} else "pnl_pct"
    valid = [t for t in trades if t.get(metric_key) is not None]
    reverse = (direction == "best")
    valid.sort(key=lambda t: t.get(metric_key) or 0, reverse=reverse)
    return {
        "count": len(valid[:limit]),
        "metric": metric_key,
        "direction": direction,
        "days": days,
        "version_filter": version,
        "trades": valid[:limit],
    }


async def handle_get_recent_alerts(days: int = 7, decision: str = "all",
                                    outcome: str = "all", pair: str = "",
                                    sort_by: str = "timestamp", direction: str = "desc",
                                    limit: int = 20, **kwargs) -> Dict:
    """Recent OpenClaw decisions from agent_memory (the tracker view).
    sort_by ∈ {timestamp, pnl_max, pnl_min, pnl_at_close, pnl_pct, scanner_score, agent_confidence}.
    direction ∈ {desc, asc}. Default: most recent first."""
    from datetime import datetime, timezone, timedelta
    settings = get_settings()
    from supabase import create_client
    sb = create_client(settings.supabase_url, settings.supabase_service_key)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    sortable = {"timestamp", "pnl_max", "pnl_min", "pnl_at_close", "pnl_pct", "scanner_score", "agent_confidence"}
    sort_col = sort_by if sort_by in sortable else "timestamp"
    desc = (direction.lower() != "asc")

    q = sb.table("agent_memory").select(
        "id, pair, agent_decision, agent_confidence, outcome, pnl_pct, pnl_max, pnl_min, "
        "pnl_at_close, scanner_score, timestamp, alert_id"
    ).gte("timestamp", cutoff).order(sort_col, desc=desc).limit(limit)
    if decision.upper() not in {"ALL", ""}:
        q = q.eq("agent_decision", decision.upper())
    if outcome.upper() not in {"ALL", ""}:
        q = q.eq("outcome", outcome.upper())
    if pair:
        q = q.eq("pair", pair.upper())

    try:
        r = q.execute()
        return {
            "count": len(r.data or []),
            "days": days,
            "decision_filter": decision,
            "outcome_filter": outcome,
            "pair_filter": pair or "all",
            "sort_by": sort_col,
            "direction": "desc" if desc else "asc",
            "alerts": r.data or [],
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:120]}"}


# ============================================================
# Handler registry
# ============================================================
TOOL_HANDLERS = {
    "read_alert": handle_read_alert,
    "analyze_alert": handle_analyze_alert,
    "get_ml_prediction": handle_get_ml_prediction,
    "get_backtest_history": handle_get_backtest_history,
    "get_market_context": handle_get_market_context,
    "get_similar_patterns": handle_get_similar_patterns,
    "get_portfolio_status": handle_get_portfolio_status,
    "get_recent_trades": handle_get_recent_trades,
    "get_top_trades": handle_get_top_trades,
    "get_recent_alerts": handle_get_recent_alerts,
    "send_recommendation": handle_send_recommendation,
    "record_decision": handle_record_decision,
    "record_outcome": handle_record_outcome,
}
