"""Alert processing pipeline — orchestrates agent + telegram + memory."""

import asyncio
from typing import Optional
from pathlib import Path

from openclaw.agent.core import ClaudeAgent, AgentDecision
from openclaw.agent.circuit_breaker import CircuitBreaker
from openclaw.memory.store import MemoryStore
from openclaw.telegram.bot import OpenClawBot
from openclaw.pipeline.chart_generator import generate_alert_chart


def _extract_analysis_features(full_analysis: dict) -> dict:
    """Flatten the analyze_alert_realtime result into structured features for filtering.

    Returns a dict that gets merged into agent_memory.features_fingerprint, giving the
    tracker UI the ability to filter on Fibonacci, Volume Profile, EMA Stack, Cloud,
    Order Blocks, StochRSI, MACD, BB Squeeze, FVG, ADX 1H, and progressive conditions.
    """
    if not isinstance(full_analysis, dict):
        return {}

    feat = {}

    # ─── Entry Conditions (5 progressive validations) ───
    ec = full_analysis.get("entry_conditions") or {}
    if isinstance(ec, dict):
        hard = 0; quasi = 0
        for k in ("ema100_1h", "ema20_4h", "cloud_1h", "cloud_30m", "choch_bos"):
            v = ec.get(k) or {}
            if not isinstance(v, dict):
                continue
            valid = bool(v.get("valid"))
            dist = v.get("distance_pct")
            feat[f"prog_{k}_valid"] = valid
            if isinstance(dist, (int, float)):
                feat[f"prog_{k}_dist_pct"] = round(dist, 2)
            if valid:
                hard += 1
            elif isinstance(dist, (int, float)) and dist >= -2.0:
                quasi += 1
        feat["prog_count_hard"] = hard
        feat["prog_count_effective"] = hard + quasi  # with -2% tolerance

    # ─── Bonus filters (Fib, OB, FVG, MACD, BB, StochRSI, EMA Stack, ADX 1H, …) ───
    bf = full_analysis.get("bonus_filters") or {}
    if isinstance(bf, dict):
        feat["bonus_count"] = bf.get("count")
        feat["bonus_total"] = bf.get("total")

        # Fibonacci
        for tf in ("1h", "4h"):
            fib = bf.get(f"fib_{tf}") or {}
            if isinstance(fib, dict):
                feat[f"fib_{tf}_bonus"] = bool(fib.get("bonus"))
                if fib.get("level") is not None:
                    feat[f"fib_{tf}_level"] = fib.get("level")

        # Order Blocks
        for tf in ("1h", "4h"):
            ob = bf.get(f"ob_{tf}") or {}
            if isinstance(ob, dict):
                feat[f"ob_{tf}_bonus"] = bool(ob.get("bonus"))
                feat[f"ob_{tf}_count"] = ob.get("count")
                blocks = ob.get("blocks") or []
                if blocks and isinstance(blocks, list) and isinstance(blocks[0], dict):
                    nb = blocks[0]
                    feat[f"ob_{tf}_position"] = nb.get("position")    # ABOVE/INSIDE/BELOW
                    feat[f"ob_{tf}_strength"] = nb.get("strength")    # STRONG/MEDIUM/WEAK
                    feat[f"ob_{tf}_mitigated"] = bool(nb.get("mitigated"))
                    if isinstance(nb.get("distance_pct"), (int, float)):
                        feat[f"ob_{tf}_distance_pct"] = round(nb["distance_pct"], 2)

        # FVG
        for tf in ("1h", "4h"):
            fvg = bf.get(f"fvg_{tf}") or {}
            if isinstance(fvg, dict):
                feat[f"fvg_{tf}_bonus"] = bool(fvg.get("bonus"))
                feat[f"fvg_{tf}_count"] = fvg.get("count")
                feat[f"fvg_{tf}_position"] = fvg.get("position")  # ABOVE/INSIDE/BELOW

        # MACD
        for tf in ("1h", "4h"):
            macd = bf.get(f"macd_{tf}") or {}
            if isinstance(macd, dict):
                feat[f"macd_{tf}_trend"] = macd.get("trend")          # BULLISH/BEARISH
                feat[f"macd_{tf}_growing"] = bool(macd.get("growing"))
                if isinstance(macd.get("histogram"), (int, float)):
                    feat[f"macd_{tf}_hist"] = round(macd["histogram"], 4)

        # Bollinger Bands / Squeeze
        for tf in ("1h", "4h"):
            bb = bf.get(f"bb_{tf}") or {}
            if isinstance(bb, dict):
                feat[f"bb_{tf}_squeeze"] = bool(bb.get("squeeze"))
                feat[f"bb_{tf}_breakout"] = bb.get("breakout")  # UP/DOWN/None
                if isinstance(bb.get("width_pct"), (int, float)):
                    feat[f"bb_{tf}_width_pct"] = round(bb["width_pct"], 2)

        # Stoch RSI
        for tf in ("1h", "4h"):
            sr = bf.get(f"stochrsi_{tf}") or {}
            if isinstance(sr, dict):
                feat[f"stochrsi_{tf}_zone"] = sr.get("zone")  # OVERSOLD/NEUTRAL/OVERBOUGHT
                feat[f"stochrsi_{tf}_cross"] = sr.get("cross")
                if isinstance(sr.get("k"), (int, float)):
                    feat[f"stochrsi_{tf}_k"] = round(sr["k"], 1)

        # EMA Stack
        for tf in ("1h", "4h"):
            es = bf.get(f"ema_stack_{tf}") or {}
            if isinstance(es, dict):
                feat[f"ema_stack_{tf}_count"] = es.get("count")  # 0..4
                feat[f"ema_stack_{tf}_trend"] = es.get("trend")  # BULLISH/MIXED/BEARISH

        # ADX 1H separately (4H is already in features)
        adx_1h = bf.get("adx_1h") or {}
        if isinstance(adx_1h, dict):
            for fld in ("adx", "di_plus", "di_minus", "di_spread", "strength"):
                v = adx_1h.get(fld)
                if v is not None:
                    feat[f"adx_1h_{fld}" if fld != "adx" else "adx_1h"] = round(v, 2) if isinstance(v, float) else v

        # RSI MTF aligned count
        rsi_mtf = bf.get("rsi_mtf") or {}
        if isinstance(rsi_mtf, dict):
            feat["rsi_mtf_aligned_count"] = rsi_mtf.get("aligned_count")
            feat["rsi_mtf_trend"] = rsi_mtf.get("trend")

    # ─── Volume Profile per TF ───
    vp = full_analysis.get("volume_profile") or {}
    for tf in ("1h", "4h"):
        v = vp.get(tf) or {}
        if isinstance(v, dict) and not v.get("error") and v.get("poc"):
            feat[f"vp_{tf}_position"] = v.get("position")  # IN_VA/ABOVE_VAH/BELOW_VAL
            if isinstance(v.get("poc_distance_pct"), (int, float)):
                feat[f"vp_{tf}_poc_dist_pct"] = round(v["poc_distance_pct"], 2)

    # ─── ML prediction (if attached upstream) ───
    ml = full_analysis.get("ml_prediction") or {}
    if isinstance(ml, dict):
        if isinstance(ml.get("p_success"), (int, float)):
            feat["ml_p_success"] = round(ml["p_success"], 3)
        if ml.get("decision"):
            feat["ml_decision"] = ml.get("decision")

    return {k: v for k, v in feat.items() if v is not None}


class AlertProcessor:
    """Processes new alerts through the Claude agent pipeline."""

    def __init__(self, agent: ClaudeAgent, bot: OpenClawBot,
                 circuit_breaker: CircuitBreaker, memory: MemoryStore,
                 portfolio=None, portfolio_v2=None, portfolio_v3=None, portfolio_v4=None, portfolio_v5=None,
                 portfolio_v6=None, portfolio_v7=None, portfolio_v8=None, portfolio_v9=None,
                 portfolio_v11a=None, portfolio_v11b=None, portfolio_v11c=None,
                 portfolio_v11d=None, portfolio_v11e=None):
        self.agent = agent
        self.bot = bot
        self.circuit_breaker = circuit_breaker
        self.memory = memory
        self.portfolio = portfolio
        self.portfolio_v2 = portfolio_v2
        self.portfolio_v3 = portfolio_v3
        self.portfolio_v4 = portfolio_v4
        self.portfolio_v5 = portfolio_v5
        self.portfolio_v6 = portfolio_v6
        self.portfolio_v7 = portfolio_v7
        self.portfolio_v8 = portfolio_v8
        self.portfolio_v9 = portfolio_v9
        # V11 family — discovery-driven filters with V7 hybrid TP
        self.portfolio_v11a = portfolio_v11a
        self.portfolio_v11b = portfolio_v11b
        self.portfolio_v11c = portfolio_v11c
        self.portfolio_v11d = portfolio_v11d
        self.portfolio_v11e = portfolio_v11e

    async def process_alert(self, alert: dict):
        """Full pipeline: analyze → decide → notify → record."""
        pair = alert.get("pair", "?")
        alert_id = alert.get("id", "")
        score = alert.get("scanner_score", 0)

        print(f"\n{'='*60}")
        print(f"🔍 Processing: {pair} (Score {score}/10)")
        print(f"{'='*60}")

        # 1. Check circuit breaker
        if self.circuit_breaker.is_tripped():
            print(f"🚨 Circuit breaker active — skipping {pair}")
            await self.bot._send_recommendation(
                f"⚠️ *{pair}* Score {score}/10\n\n"
                f"🚨 Circuit breaker actif — recommandation desactivee.\n"
                f"Trop de pertes recentes.",
                "SKIP", alert_id
            )
            return

        # 2. Send initial notification
        try:
            await self.bot.send_alert_notification(alert)
        except Exception:
            pass  # Non-critical

        # 2b. FAST PATH V8/V9 — bypass agent, open positions immediately if gate passes
        # The gate V8/V9 has 11 filters that are more strict than the agent.
        # Agent adds -0.6pts WR and 30s+ latency. Direct gate → position is optimal.
        if self.portfolio_v8 or self.portfolio_v9:
            try:
                from openclaw.portfolio.gate_v6 import build_gate_cache
                _fast_cache = await asyncio.to_thread(build_gate_cache, pair)
                alert["_gate_cache"] = _fast_cache

                # Compute features needed for V8/V9 filters (STC, vol spikes) — offload to thread
                import requests as _freq
                def _fetch_vol_klines():
                    try:
                        _rv = _freq.get("https://api.binance.com/api/v3/klines",
                            params={"symbol": pair, "interval": "1h", "limit": 48}, timeout=5)
                        return _rv.json()
                    except:
                        return None
                try:
                    _kv = await asyncio.to_thread(_fetch_vol_klines)
                    if _kv and isinstance(_kv, list) and len(_kv) >= 2:
                        _vols = [float(k[7]) for k in _kv]
                        _cur = _vols[-1]
                        def _avg(v, n):
                            s = v[-n:] if len(v) >= n else v
                            return sum(s)/len(s) if s else 0
                        _prev = _vols[:-1]
                        for _vk, _vn in [("vol_spike_vs_1h",1),("vol_spike_vs_4h",4),("vol_spike_vs_24h",24),("vol_spike_vs_48h",len(_prev))]:
                            _a = _avg(_prev, _vn)
                            alert[_vk] = round((_cur/_a - 1)*100, 1) if _a > 0 else None
                except:
                    pass

                # Fast triage decision for V8/V9 (score-based, no GPT)
                _pp = alert.get("pp", False)
                _ec = alert.get("ec", False)
                if score >= 9:
                    _fb_dec, _fb_conf = "BUY STRONG", 0.75
                elif score >= 8 and _pp:
                    _fb_dec, _fb_conf = "BUY", 0.65
                elif score >= 7 and _pp and _ec:
                    _fb_dec, _fb_conf = "BUY WEAK", 0.55
                else:
                    _fb_dec, _fb_conf = "WATCH", 0.30

                if "BUY" in _fb_dec and _fb_conf >= 0.60:
                    _vip = {}
                    _quality = {}
                    _v8_opened = False
                    _v9_opened = False

                    async def _fast_v8():
                        nonlocal _v8_opened
                        if self.portfolio_v8:
                            pos = await self.portfolio_v8.try_open_position(
                                pair=pair, decision=_fb_dec, confidence=_fb_conf,
                                alert=alert, vip=_vip, quality=_quality)
                            if pos:
                                _v8_opened = True
                                print(f"⚡ V8 FAST: {pair} ${pos['size_usd']:.0f} @ {pos['entry_price']}")

                    async def _fast_v9():
                        nonlocal _v9_opened
                        if self.portfolio_v9:
                            pos = await self.portfolio_v9.try_open_position(
                                pair=pair, decision=_fb_dec, confidence=_fb_conf,
                                alert=alert, vip=_vip, quality=_quality)
                            if pos:
                                _v9_opened = True
                                print(f"⚡ V9 FAST: {pair} ${pos['size_usd']:.0f} @ {pos['entry_price']}")

                    await asyncio.gather(_fast_v8(), _fast_v9(), return_exceptions=True)

                    if _v8_opened or _v9_opened:
                        print(f"⚡ FAST PATH: {pair} V8={'✅' if _v8_opened else '❌'} V9={'✅' if _v9_opened else '❌'} — {_fb_dec} ({_fb_conf*100:.0f}%)")
            except Exception as fast_err:
                print(f"⚠️ Fast path error for {pair}: {fast_err}")

        # 3. Run agent analysis — 30s timeout then instant fast triage fallback
        try:
            decision = await asyncio.wait_for(
                self.agent.analyze_alert(alert),
                timeout=30  # 30s max — no retry, fast triage if timeout
            )
        except (asyncio.TimeoutError, Exception) as analysis_err:
            print(f"⏰ Analysis timeout/error for {pair} ({analysis_err.__class__.__name__}) — fast triage")
            # FAST TRIAGE FALLBACK — instant decision based on score (no GPT needed)
            pp = alert.get("pp", False)
            ec = alert.get("ec", False)
            if score >= 9:
                fb_decision, fb_conf = "BUY STRONG", 0.75
            elif score >= 8 and pp:
                fb_decision, fb_conf = "BUY", 0.65
            elif score >= 7 and pp and ec:
                fb_decision, fb_conf = "BUY WEAK", 0.55
            else:
                fb_decision, fb_conf = "WATCH", 0.30

            decision = AgentDecision(
                decision=fb_decision, confidence=fb_conf,
                reasoning=f"FAST TRIAGE (timeout 30s) — score {score}/10 PP={pp} EC={ec}",
                raw_response=f"Timeout fallback: {fb_decision} based on score={score} PP={pp} EC={ec}",
                tools_called=[], error="timeout_fast_triage"
            )
            print(f"⚡ {pair}: {fb_decision} ({fb_conf*100:.0f}%) — score {score} PP={pp} EC={ec}")
            try:
                await self.bot._send_recommendation(
                    f"⚡ *{pair}* Score {score}/10\n"
                    f"🤖 _FAST TRIAGE (30s timeout)_\n\n"
                    f"Decision: *{fb_decision}* ({fb_conf*100:.0f}%)\n"
                    f"Basé sur: Score {score}, PP={pp}, EC={ec}",
                    fb_decision, alert_id
                )
            except Exception:
                pass
        except Exception as e:
            err_msg = str(e)[:100]
            print(f"❌ Analysis error for {pair}: {err_msg}")
            decision = AgentDecision(
                decision="WATCH", confidence=0.3,
                reasoning=f"Error: {err_msg}",
                raw_response="", tools_called=[], error=err_msg
            )
            # Send error notification
            try:
                await self.bot._send_recommendation(
                    f"❌ *{pair}* Score {score}/10\n\nErreur d'analyse: {err_msg}\nDecision: WATCH",
                    "WATCH", alert_id
                )
            except Exception:
                pass

        # 4. Log result + send Telegram for triage-only decisions
        is_triage_only = "mega_mini_triage" in decision.tools_called and "send_recommendation" not in decision.tools_called
        is_sonnet = "send_recommendation" in decision.tools_called
        if is_triage_only:
            model_label = "🤖 MEGA 4 Mini"
        elif is_sonnet:
            model_label = "🤖 MEGA 4"
        else:
            model_label = "🤖 MEGA 4 Mini"
        print(f"📋 Decision: {decision.decision} ({int(decision.confidence*100)}%) [{model_label}]")
        print(f"🔧 Tools called: {', '.join(decision.tools_called)}")

        # ALWAYS send Telegram notification for ALL decisions
        if "send_recommendation" not in decision.tools_called:
            try:
                emoji = {"BUY STRONG": "🟢🟢", "BUY": "🟢", "BUY WEAK": "🟡🟢", "WATCH": "🟡", "SKIP": "🔴"}.get(decision.decision, "⚪")
                # Full analysis — use raw_response which contains the complete formatted analysis
                full_analysis = decision.raw_response or decision.reasoning
                # Telegram limit is 4096 chars — send full analysis
                msg = (
                    f"{emoji} *{pair}* {score}/10 — {decision.decision} ({int(decision.confidence*100)}%)\n"
                    f"{model_label}\n\n"
                    f"{full_analysis[:3900]}"
                )
                print(f"📱 Sending Telegram for {pair} ({len(msg)} chars)...")
                await self.bot._send_recommendation(msg, decision.decision, alert_id)
                print(f"📱 Telegram sent for {pair}")
            except Exception as e:
                print(f"⚠️ Telegram send error for {pair}: {e}")
                # Retry without Markdown — split if too long
                try:
                    plain_text = f"{pair} {score}/10 — {decision.decision} ({int(decision.confidence*100)}%)\n{model_label}\n\n{full_analysis[:3900]}"
                    await self.bot.app.bot.send_message(
                        chat_id=self.bot.chat_id,
                        text=plain_text
                    )
                except Exception:
                    pass

        # 5. Save to memory (with full analysis text + price + VIP + Quality for tracking)
        vip = getattr(decision, 'vip', None) or {}
        quality = getattr(decision, 'quality', None) or {}
        features = {
            "scanner_score": score,
            "timeframes": alert.get("timeframes", []),
            "di_plus_4h": alert.get("di_plus_4h"),
            "di_minus_4h": alert.get("di_minus_4h"),
            "adx_4h": alert.get("adx_4h"),
            "pp": alert.get("pp"),
            "ec": alert.get("ec"),
            "price": alert.get("price"),
            "rsi": alert.get("rsi"),
            "is_vip": vip.get("is_vip", False),
            "is_high_ticket": vip.get("is_high_ticket", False),
            "vip_score": vip.get("vip_score", 0),
            "vip_reasons": vip.get("reasons", []),
            "quality_grade": quality.get("grade", ""),
            "quality_axes": quality.get("axes", 0),
            "quality_details": quality.get("details", []),
        }
        # Fetch 24h price change + current 4H candle from Binance
        try:
            import requests as _req
            _r24 = _req.get("https://api.binance.com/api/v3/ticker/24hr", params={"symbol": pair}, timeout=5)
            _d24 = _r24.json()
            features["change_24h_pct"] = round(float(_d24.get("priceChangePercent", 0)), 2)
        except:
            features["change_24h_pct"] = None
        # Current 4H candle body + range
        try:
            _rk = _req.get("https://api.binance.com/api/v3/klines", params={"symbol": pair, "interval": "4h", "limit": 1}, timeout=5)
            _kd = _rk.json()
            if _kd and isinstance(_kd, list) and len(_kd) > 0:
                _o, _h, _l, _c = float(_kd[0][1]), float(_kd[0][2]), float(_kd[0][3]), float(_kd[0][4])
                if _l > 0:
                    features["candle_4h_body_pct"] = round(abs(_c - _o) / _o * 100, 2)
                    features["candle_4h_range_pct"] = round((_h - _l) / _l * 100, 2)
                    features["candle_4h_direction"] = "green" if _c >= _o else "red"
        except:
            pass
        # Alert TF candle body/range — the candle that triggered the signal
        try:
            import requests as _req
            tfs = alert.get("timeframes") or []
            for _tf in tfs:
                _tf_interval = {"15m": "15m", "30m": "30m", "1h": "1h", "4h": "4h"}.get(_tf)
                if not _tf_interval:
                    continue
                _rtf = _req.get("https://api.binance.com/api/v3/klines",
                    params={"symbol": pair, "interval": _tf_interval, "limit": 1}, timeout=5)
                _ktf = _rtf.json()
                if _ktf and isinstance(_ktf, list) and len(_ktf) > 0:
                    _otf, _htf, _ltf, _ctf = float(_ktf[0][1]), float(_ktf[0][2]), float(_ktf[0][3]), float(_ktf[0][4])
                    if _otf > 0 and _ltf > 0:
                        features[f"candle_{_tf}_body_pct"] = round(abs(_ctf - _otf) / _otf * 100, 2)
                        features[f"candle_{_tf}_range_pct"] = round((_htf - _ltf) / _ltf * 100, 2)
                        features[f"candle_{_tf}_direction"] = "green" if _ctf >= _otf else "red"
        except:
            pass
        # Volume spike analysis — compare current volume to historical averages
        try:
            import requests as _req
            # Fetch 1h klines for 48h (48 candles)
            _rv = _req.get("https://api.binance.com/api/v3/klines",
                params={"symbol": pair, "interval": "1h", "limit": 48}, timeout=5)
            _klines = _rv.json()
            if _klines and isinstance(_klines, list) and len(_klines) >= 2:
                # Volume = index 5 in kline data (quote asset volume = index 7)
                volumes = [float(k[7]) for k in _klines]  # quote volume in USDT
                current_vol = volumes[-1]
                features["volume_usdt"] = round(current_vol, 2)

                # Averages over different periods (from end)
                def _avg(vols, n):
                    s = vols[-n:] if len(vols) >= n else vols
                    return sum(s) / len(s) if s else 0

                avg_1h = _avg(volumes[:-1], 1)   # previous 1 candle
                avg_4h = _avg(volumes[:-1], 4)   # previous 4 candles
                avg_24h = _avg(volumes[:-1], 24)  # previous 24 candles
                avg_48h = _avg(volumes[:-1], 47)  # all previous candles

                features["vol_avg_1h"] = round(avg_1h, 2)
                features["vol_avg_4h"] = round(avg_4h, 2)
                features["vol_avg_24h"] = round(avg_24h, 2)
                features["vol_avg_48h"] = round(avg_48h, 2)
                features["vol_spike_vs_1h"] = round((current_vol / avg_1h - 1) * 100, 1) if avg_1h > 0 else None
                features["vol_spike_vs_4h"] = round((current_vol / avg_4h - 1) * 100, 1) if avg_4h > 0 else None
                features["vol_spike_vs_24h"] = round((current_vol / avg_24h - 1) * 100, 1) if avg_24h > 0 else None
                features["vol_spike_vs_48h"] = round((current_vol / avg_48h - 1) * 100, 1) if avg_48h > 0 else None
        except Exception:
            pass
        # Market sentiment (Fear&Greed, BTC dominance, BTC/ETH trends) — cached
        try:
            from openclaw.pipeline.market_sentiment import MarketSentiment
            sentiment = MarketSentiment.get_all()
            features.update(sentiment)
        except:
            pass
        # Extract STC values from analysis text
        full_analysis_text = decision.raw_response or decision.reasoning
        try:
            import re
            stc_match = re.search(r"STC.*?(\{[^}]*'15m'[^}]*\})", full_analysis_text)
            if stc_match:
                import ast
                stc_vals = ast.literal_eval(stc_match.group(1))
                features["stc_15m"] = round(float(stc_vals.get("15m", -1)), 4) if stc_vals.get("15m") is not None else None
                features["stc_30m"] = round(float(stc_vals.get("30m", -1)), 4) if stc_vals.get("30m") is not None else None
                features["stc_1h"] = round(float(stc_vals.get("1h", -1)), 4) if stc_vals.get("1h") is not None else None
        except:
            pass
        # Save full analysis text (not truncated) for the OpenClaw tracker dashboard
        self.memory.save_pattern(
            alert_id, pair, features,
            decision.decision, decision.confidence, decision.reasoning[:500],
            analysis_text=full_analysis_text[:4000]
        )

        # 6. Generate chart in BACKGROUND (non-blocking) + prepare analysis summary
        analysis_summary = None
        chart_task = None
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backtest"))
            from api.realtime_analyze import analyze_alert_realtime
            from openclaw.agent.tool_handlers import _smart_summary

            # Get FULL analysis (needed for smart_summary — chart runs in background)
            full_analysis = await asyncio.to_thread(
                analyze_alert_realtime, pair,
                alert.get("alert_timestamp", ""),
                alert.get("price", 0)
            )

            # Build smart summary for portfolio SL/TP calculation
            try:
                analysis_summary = _smart_summary(full_analysis)
            except Exception:
                analysis_summary = {}

            # Launch chart generation + telegram + DB update as background task
            async def _chart_background():
                try:
                    _chart_path = await asyncio.to_thread(
                        generate_alert_chart, pair, full_analysis,
                        alert.get("price", 0), "1h", 80
                    )
                    acc_data = {}
                    analysis_features = {}
                    if full_analysis and isinstance(full_analysis, dict):
                        acc_raw = full_analysis.get("accumulation", {})
                        if isinstance(acc_raw, dict) and acc_raw.get("detected"):
                            acc_data = {
                                "accumulation_days": round(acc_raw.get("days", 0), 1),
                                "accumulation_hours": round(acc_raw.get("hours", 0)),
                                "accumulation_range_pct": round(acc_raw.get("range_pct", 0), 1),
                            }
                        # ─── Extract structured indicators for tracker filtering ───
                        try:
                            analysis_features = _extract_analysis_features(full_analysis)
                        except Exception as _ee:
                            print(f"⚠️ extract_analysis_features error for {pair}: {_ee}")
                    if _chart_path:
                        await self.bot.app.bot.send_photo(
                            chat_id=self.bot.chat_id,
                            photo=open(_chart_path, 'rb'),
                            caption=f"📊 {pair} — {score}/10 — {decision.decision}"
                        )
                        print(f"📊 Chart sent for {pair}")
                    try:
                        from openclaw.config import get_settings
                        from supabase import create_client as _sc
                        _s = get_settings()
                        _sb = _sc(_s.supabase_url, _s.supabase_service_key)
                        update_fields = {}
                        if _chart_path:
                            update_fields["chart_path"] = str(_chart_path)
                        if acc_data or analysis_features:
                            existing = _sb.table("agent_memory").select("features_fingerprint").eq("alert_id", alert_id).single().execute()
                            fp = (existing.data or {}).get("features_fingerprint") or {}
                            if acc_data: fp.update(acc_data)
                            if analysis_features: fp.update(analysis_features)
                            update_fields["features_fingerprint"] = fp
                        if update_fields:
                            _sb.table("agent_memory").update(update_fields).eq("alert_id", alert_id).execute()
                    except Exception:
                        pass
                except Exception as e:
                    print(f"⚠️ Chart background error for {pair}: {e}")

            chart_task = asyncio.create_task(_chart_background())  # Non-blocking
        except Exception as e:
            print(f"⚠️ Chart error for {pair}: {e}")

        # Enrich alert with STC values for portfolio filters
        try:
            import re as _re, ast as _ast
            _stc_m = _re.search(r"STC.*?(\{[^}]*'15m'[^}]*\})", decision.raw_response or decision.reasoning or "")
            if _stc_m:
                _stc_v = _ast.literal_eval(_stc_m.group(1))
                alert["stc_15m"] = float(_stc_v.get("15m", -1)) if _stc_v.get("15m") is not None else None
                alert["stc_30m"] = float(_stc_v.get("30m", -1)) if _stc_v.get("30m") is not None else None
                alert["stc_1h"] = float(_stc_v.get("1h", -1)) if _stc_v.get("1h") is not None else None
        except:
            pass

        # Enrich alert with vol spikes for portfolio filters
        for _vk in ["vol_spike_vs_1h","vol_spike_vs_4h","vol_spike_vs_24h","vol_spike_vs_48h"]:
            if features.get(_vk) is not None:
                alert[_vk] = features[_vk]

        # Pre-build gate cache ONCE for all portfolio managers (saves ~80s of redundant API calls)
        gate_cache = None
        if "BUY" in decision.decision:
            try:
                from openclaw.portfolio.gate_v6 import build_gate_cache
                gate_cache = await asyncio.to_thread(build_gate_cache, pair)
            except Exception:
                pass
        # Inject cache into alert for portfolio managers
        if gate_cache:
            alert["_gate_cache"] = gate_cache

        # 6b-j. ALL Portfolios V1-V9 — PARALLEL execution via asyncio.gather
        quality = getattr(decision, 'quality', None)
        if "BUY" in decision.decision:
            async def _try_portfolio(pm, name, **kwargs):
                if not pm: return
                try:
                    pos = await pm.try_open_position(**kwargs)
                    if pos:
                        print(f"💼 {name} Position opened for {pair}: ${pos['size_usd']:.2f} @ {pos['entry_price']}")
                except Exception as e:
                    print(f"⚠️ {name} error for {pair}: {e}")

            common = dict(pair=pair, decision=decision.decision, confidence=decision.confidence, alert=alert, vip=vip)
            common_q = dict(**common, quality=quality)
            common_as = dict(**common, analysis_summary=analysis_summary or {})

            await asyncio.gather(
                _try_portfolio(self.portfolio, "V1", **common_as),
                _try_portfolio(self.portfolio_v2, "V2", **common_as, quality=quality),
                _try_portfolio(self.portfolio_v3, "V3", **common_q),
                _try_portfolio(self.portfolio_v4, "V4", **common_q),
                _try_portfolio(self.portfolio_v5, "V5", **common_q),
                _try_portfolio(self.portfolio_v6, "V6", **common_q),
                _try_portfolio(self.portfolio_v7, "V7", **common_q),
                _try_portfolio(self.portfolio_v8, "V8", **common_q),
                _try_portfolio(self.portfolio_v9, "V9", **common_q),
                return_exceptions=True,
            )

            # V11 family — build shared cache once, then dispatch all 5 in parallel
            try:
                from openclaw.portfolio.gates_v11 import build_v11_cache
                v11_cache = await asyncio.to_thread(build_v11_cache, pair)
            except Exception as _ev:
                print(f"⚠️ V11 cache build error for {pair}: {_ev}")
                v11_cache = {}
            common_v11 = dict(**common_q, v11_cache=v11_cache)
            await asyncio.gather(
                _try_portfolio(self.portfolio_v11a, "V11A", **common_v11),
                _try_portfolio(self.portfolio_v11b, "V11B", **common_v11),
                _try_portfolio(self.portfolio_v11c, "V11C", **common_v11),
                _try_portfolio(self.portfolio_v11d, "V11D", **common_v11),
                _try_portfolio(self.portfolio_v11e, "V11E", **common_v11),
                return_exceptions=True,
            )

        # 7. Wait for chart background task if still running
        if chart_task:
            try:
                await chart_task
            except Exception:
                pass

        # 8. Increment counter
        self.memory.increment_processed()

        print(f"✅ {pair} processed — {decision.decision}")
