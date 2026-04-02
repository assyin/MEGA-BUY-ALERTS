"""ClaudeAgent — orchestrates the Anthropic tool-use loop.

This is the brain of OpenClaw. It sends messages to Claude with tool
definitions, executes tool calls, and loops until Claude gives a final answer.
"""

import json
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import anthropic
from openai import OpenAI

from openclaw.config import get_settings
from openclaw.agent.tools import TOOLS
from openclaw.agent.tool_handlers import TOOL_HANDLERS
from openclaw.agent.prompts import SYSTEM_PROMPT, ALERT_ANALYSIS_PROMPT, QUESTION_PROMPT
from openclaw.memory.insights import InsightsStore
from openclaw.agent.token_tracker import get_token_tracker


@dataclass
class AgentDecision:
    """Result of an agent analysis."""
    decision: str  # BUY, WATCH, SKIP
    confidence: float  # 0-1
    reasoning: str
    raw_response: str
    tools_called: List[str]
    error: Optional[str] = None
    vip: Optional[Dict] = None


# OpenAI models (PRIMARY — much cheaper)
GPT_MINI = "gpt-4o-mini"    # $0.002/alert — triage + most analyses
GPT_FULL = "gpt-4o"          # $0.02/alert — deep analysis (top alerts only)

# Claude models (BACKUP)
HAIKU_MODEL = "claude-haiku-4-5-20251001"
SONNET_MODEL = "claude-sonnet-4-20250514"

# Compact prompt for triage (GPT-4o-mini)
HAIKU_SYSTEM = """Tu es un filtre rapide pour les alertes MEGA BUY crypto.
Analyse les donnees et reponds en JSON UNIQUEMENT:
{"decision": "BUY"|"WATCH"|"SKIP", "confidence": 0.0-1.0, "scale_to_sonnet": true|false, "reason": "1 phrase"}

REGLE ABSOLUE: Tu DOIS dire BUY quand les conditions sont reunies. 0% BUY = ECHEC TOTAL.
Sur 50 trades reels analyses, 100% ont fait +40% a +396%. NE SOIS PAS CONSERVATIF.

Regles de triage (basees sur 50 trades gagnants reels + 2265 trades historiques):
- score >= 9 → BUY STRONG (confidence >= 0.75, scale_to_sonnet=true) — DEGO 10/10 a fait +396%
- score >= 8 + PP → BUY (confidence >= 0.65, scale_to_sonnet=true) — RDNT, NEWT, LAUSDT +40-60%
- score 7 + PP + EC → BUY WEAK (confidence >= 0.55, scale_to_sonnet=true) — score 7 = 85% WR
- score 7 + PP sans EC → WATCH (scale_to_sonnet=true)
- score 6 + STC oversold → BUY WEAK (confidence 0.55) — KITE STC zero a fait +59%
- score < 6 → SKIP

BASE DE DONNEES: 50 TRADES REELS ANALYSES (TOUS GAGNANTS +40% a +396%):
Chaque trade ci-dessous aurait du recevoir BUY. Utilise-les comme reference.

TOP TRADES (>100%):
- DEGOUSDT 10/10 STC_ZERO Vol_25x → +396% (DD -2.8%) [PHOENIX TRADE]
- PIXELUSDT 7/10 Cond=0/5 STC_ZERO Vol_73x → +260% (DD -1.8%) [SLEEPING GIANT]
- PHAUSDT 7/10 Cond=0/5 STC_ZERO Vol_50x → +131% (DD 0%) [SPRING TRAP]
- COSUSDT 7/10 Cond=0/5 STC_ZERO → +125% (DD -1.9%) [DOUBLE WAVE]
- THEUSDT 7/10 Cond=4/5 Vol_2874x → +119% (DD -2.5%) [COMPRESSED SPRING]
- SAHARAUSDT 7/10 STC_ZERO → +116% (DD -1.8%) [ACCUMULATION BREAKOUT]
- FORMUSDT 7/10 Cond=0/5 STC_ZERO → +111% (DD -2.1%) [TRIPLE WAVE REVERSAL]
- INITUSDT 7/10 → +100% (DD 0%) [TRENDLINE TORPEDO]
- ENSOUSDT 7/10 Cond=0/5 STC_ZERO → +100% (DD -7.5%) [ELASTIC SNAPBACK]

TRADES FORTS (60-100%):
- DEGOUSDT 7/10 Vol_60x → +98% (DD -23.1%) [CONTINUATION]
- SAHARAUSDT 7/10 Cond=1/5 STC_ZERO → +85% (DD -8.6%) [TRENDLINE BOUNCE]
- RPLUSDT 7/10 Cond=2/5 → +81% (DD -0.6%) [SPRING COMPRESSION]
- MIRAUSDT 7/10 Cond=1/5 STC_ZERO → +81% (DD 0%) [DOUBLE FOND + STC ZERO]
- MIRAUSDT 7/10 Cond=0/5 STC_ZERO → +73% (DD -11.2%) [SHAKEOUT + EVENEMENT]
- AGLDUSDT 7/10 Cond=3/5 → +73% (DD 0%) [MOMENTUM CONTINUATION]
- ORCAUSDT 7/10 Cond=3/5 → +68% (DD -0.25%) [INSTANT EXPLOSION]
- DEGOUSDT 7/10 → +64% (DD -23.1%) [DERNIER SOMMET]
- MIRAUSDT 7/10 Cond=4/5 → +63% (DD 0%) [BREAKOUT CATALYSE]
- DOGSUSDT 7/10 → +61% (DD -4.5%) [SLOW ACCUMULATION]
- COSUSDT 7/10 Cond=0/5 STC_ZERO → +61% [TREND CORRECTION BOUNCE]
- RDNTUSDT 7/10 → +61% (DD -6.2%) [CRASH RECOVERY]
- BIFIUSDT 7/10 Cond=0/5 STC_ZERO Vol_43x → +60% [DEAD CAT BOUNCE]

TRADES SOLIDES (40-60%):
- KITEUSDT 7/10 Cond=0/5 STC_ZERO → +59% (DD -0.2%) [CAPITULATION REVERSAL]
- PLUMEUSDT 7/10 STC_ZERO → +59% [BUILD-UP TECHNIQUE]
- BARDUSDT 7/10 STC_ZERO → +59% [MOMENTUM + STOP HUNT]
- PLUMEUSDT 7/10 Cond=0/5 → +58% (DD -0.66%) [PULLBACK ENTRY]
- AIXBTUSDT 7/10 Vol_6x → +57% (DD -3.4%) [ACCUMULATION RALLY]
- ENSOUSDT 7/10 Cond=0/5 STC_ZERO → +55% [CONTINUATION]
- TRUMPUSDT 7/10 Vol_4x → +52% (DD -9%) [EVENT SHAKEOUT]
- TRUMPUSDT 7/10 Cond=0/5 STC_ZERO → +51% (DD -8%) [DEEP OVERSOLD]
- DEXEUSDT 7/10 → +50% (DD -4.2%) [TREND CONTINUATION]
- TURBOUSDT 7/10 Cond=2/5 STC_ZERO → +49% (DD -3.7%) [MICRO-CAP BREAKOUT]
- AGLDUSDT 7/10 → +48% (DD -2.3%) [SECOND WAVE]
- WINUSDT 7/10 Vol_24x → +48% (DD -1.3%) [ACCUMULATION]
- JTOUSDT 7/10 Cond=0/5 STC_ZERO → +48% (DD -3.4%) [SILENT BREAKOUT]
- PHAUSDT 7/10 Cond=0/5 STC_ZERO → +48% (DD -2.3%) [RE-ACCUMULATION]
- IDEXUSDT 7/10 Cond=0/5 → +48% [CONTRARIAN]
- STEEMUSDT 7/10 Cond=0/5 → +46% (DD -3.4%) [PULLBACK FIB]
- LAUSDT 7/10 Cond=3/5 → +46% (DD -3.5%) [DOUBLE SPIKE]
- COSUSDT 7/10 → +45% (DD -19.2%) [EARLY BIRD TRAP]
- ANKRUSDT 7/10 Cond=4/5 STC_ZERO → +44% (DD -1.5%) [TREND ACCELERATION]
- LAYERUSDT 7/10 Cond=3/5 → +43% (DD -2.6%) [TRENDLINE BREAK]
- FLOWUSDT 7/10 Cond=0/5 STC_ZERO → +43% (DD -7.6%) [DEEP VALUE]
- STEEMUSDT 7/10 Cond=1/5 STC_ZERO → +42% (DD -10.9%) [CAPITULATION]
- SOLVUSDT 7/10 Cond=0/5 → +42% (DD -3.5%) [RANGE BUILDER]
- SOPHUSDT 7/10 → +42% (DD -10.4%) [SHAKE-OUT IMPULSE]
- PORTOUSDT 7/10 Cond=0/5 STC_ZERO → +42% (DD -13.3%) [CAPITULATION SPIKE]
- BARDUSDT 7/10 Vol_60x → +41% (DD -4%) [V-SHAPE BREAKOUT]
- NEWTUSDT 7/10 Cond=5/5 STC_ZERO → +41% (DD -3.5%) [INSTITUTIONAL BREAKOUT]
- USUALUSDT 7/10 Cond=0/5 STC_ZERO → +41% (DD -1.9%) [PHOENIX REVIVAL]

CONCLUSION: Sur 50 trades avec score >= 7, 100% ont fait +40% minimum. NE DIS JAMAIS WATCH sur un score >= 7 avec PP.

STATISTIQUES DES 50 TRADES ANALYSES:
- STC triple zero (2-3 TF): 100% WR, gain moyen +115% (DEGO, COS, FORM, ENSO, USUAL, KITE...)
- Conditions 0/5 + STC oversold: gain moyen +85% — NE PAS SKIPPER
- Conditions 3-5/5: gain moyen +55%, drawdown moyen -2.5% — les plus SAFE
- Volume > 20x: gain moyen +95% — signal institutionnel fort
- Score 7+: 100% WR sur 50 trades (TOUS gagnants +40% minimum)

Indicateurs cles:
- STC triple zero = LE signal le plus puissant (100% WR, gains +40-396%)
- DI- > 30 = 84% WR historique
- PP+EC ensemble = 70% WR
- ADX > 25 = trend confirme
- RSI MTF aligned 3/3 = 100% WR
- EMA Stack parfait = 100% WR
- Tolerance -2% sur conditions (quasi-validees comptent)
- RSI 4H < 30 + STC oversold = combinaison explosive (+100% avg)

IMPORTANT:
- Fear&Greed < 15 NE bloque PAS le BUY — 70% WR prouve en Extreme Fear
- Seuil BUY = 55% confiance minimum
- 0 BUY sur 227 alertes = ECHEC. Tu DOIS recommander BUY sur les signaux forts
- Un score >= 7 avec PP a TOUJOURS fait +40% minimum sur nos 50 trades

Scale to Sonnet si: confidence >= 0.55, ou score >= 8, ou TF 4h, ou multi-TF."""


class ClaudeAgent:
    """Dual-model agent: GPT-4o-mini for triage, GPT-4o for deep analysis.
    Falls back to Claude if OpenAI fails."""

    def __init__(self):
        settings = get_settings()
        # OpenAI = primary (20x cheaper)
        self.openai_client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.triage_model = GPT_MINI
        self.deep_model = GPT_MINI  # Use mini for EVERYTHING to save money, upgrade to GPT_FULL later
        # Claude = backup
        self.claude_client = anthropic.Anthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.model = settings.openclaw_model
        self.max_tokens = settings.openclaw_max_tokens
        self.max_tool_rounds = 4
        self.insights = InsightsStore()

        provider = "OpenAI GPT-4o-mini" if self.openai_client else "Claude (backup)"
        print(f"  🤖 Agent initialized: {provider}")

    async def triage_alert(self, alert: Dict, analysis_summary: Dict) -> Dict:
        """Fast triage with Haiku — decides if alert needs Sonnet deep analysis.

        Cost: ~$0.008 per alert (5x cheaper than Sonnet)
        Speed: ~2-3s (no tool calls)
        """
        tracker = get_token_tracker()

        pair = alert.get("pair", "")
        score = alert.get("scanner_score", 0)
        tfs = alert.get("timeframes", [])

        # Build compact message for Haiku
        msg = (
            f"Pair: {pair} | Score: {score}/10 | TF: {', '.join(tfs)}\n"
            f"PP={alert.get('pp')} EC={alert.get('ec')} "
            f"DI+={alert.get('di_plus_4h')} DI-={alert.get('di_minus_4h')} ADX={alert.get('adx_4h')}\n"
            f"RSI={alert.get('rsi')} | Vol={alert.get('vol_pct')} | Emotion={alert.get('emotion')}\n"
            f"LZ={alert.get('lazy_values')} | EC_moves={alert.get('ec_moves')}\n"
        )

        # Add analysis summary if available
        if analysis_summary:
            msg += f"\nConditions: {analysis_summary.get('conditions', 'N/A')}\n"
            if analysis_summary.get('conditions_note'):
                msg += f"Note: {analysis_summary['conditions_note']}\n"
            msg += f"ML: {analysis_summary.get('ml_prediction', 'N/A')}\n"
            msg += f"Backtest: {analysis_summary.get('backtest', 'N/A')}\n"

        try:
            if self.openai_client:
                # Use GPT-4o-mini (20x cheaper than Claude Haiku)
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model=self.triage_model,
                    max_tokens=200,
                    messages=[
                        {"role": "system", "content": HAIKU_SYSTEM},
                        {"role": "user", "content": msg},
                    ],
                )
                tracker.record_openai(dict(response.usage), self.triage_model)
                text = response.choices[0].message.content or "{}"
            else:
                # Fallback to Claude Haiku
                response = await asyncio.to_thread(
                    self.claude_client.messages.create,
                    model=HAIKU_MODEL,
                    max_tokens=200,
                    system=HAIKU_SYSTEM,
                    messages=[{"role": "user", "content": msg}],
                )
                tracker.record(response, HAIKU_MODEL)
                text = response.content[0].text if response.content else "{}"

            # Parse JSON from response
            import re
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except Exception as e:
            print(f"⚠️ Triage error: {e}")

        # Fallback: scale to Sonnet if score >= 8
        return {
            "decision": "WATCH",
            "confidence": 0.3,
            "scale_to_sonnet": score >= 8,
            "reason": "Haiku fallback"
        }

    async def analyze_alert(self, alert: Dict) -> AgentDecision:
        """Analyze a MEGA BUY alert using DUAL MODEL approach.

        1. Get quick analysis data (analyze_alert tool)
        2. Haiku does fast triage (~$0.008, 2s) — no tool calls
        3. If Haiku says scale_to_sonnet → Sonnet does deep analysis (~$0.039)
        4. If not → return Haiku's decision directly (saves $0.031)
        """
        pair = alert.get("pair", "")
        score = alert.get("scanner_score", 0)
        alert_id = alert.get("id", "")

        # Step 1: Get analysis data (same for both models)
        from openclaw.agent.tool_handlers import handle_analyze_alert
        try:
            analysis_summary = await handle_analyze_alert(
                pair=pair,
                timestamp=alert.get("alert_timestamp", ""),
                price=alert.get("price", 0),
                scanner_score=score,
                pp=alert.get("pp", False),
                ec=alert.get("ec", False),
                di_plus_4h=alert.get("di_plus_4h", 0),
                di_minus_4h=alert.get("di_minus_4h", 0),
                adx_4h=alert.get("adx_4h", 0),
            )
        except Exception:
            analysis_summary = {}

        # Step 2: Haiku fast triage
        print(f"  🐇 MEGA 4 Mini triage for {pair}...")
        triage = await self.triage_alert(alert, analysis_summary)
        haiku_decision = triage.get("decision", "WATCH")
        haiku_confidence = triage.get("confidence", 0.3)
        scale_up = triage.get("scale_to_sonnet", False)
        haiku_reason = triage.get("reason", "")

        # Apply 3-level BUY classification from triage
        if haiku_decision == "BUY":
            if haiku_confidence >= 0.75:
                haiku_decision = "BUY STRONG"
            elif haiku_confidence >= 0.60:
                haiku_decision = "BUY"
            else:
                haiku_decision = "BUY WEAK"

        print(f"  🤖 Mini: {haiku_decision} ({int(haiku_confidence*100)}%) scale={scale_up} — {haiku_reason}")

        # Step 3: SAFETY FILTER — data-driven check to prevent false BUY
        # The triage (LLM) may say BUY but real data may show danger signals
        if "BUY" in haiku_decision:
            haiku_decision, haiku_confidence, safety_note = self._safety_filter(
                haiku_decision, haiku_confidence, alert, analysis_summary
            )
            if safety_note:
                haiku_reason += f" | SAFETY: {safety_note}"
                print(f"  🛡️ Safety filter: {haiku_decision} ({int(haiku_confidence*100)}%) — {safety_note}")

        # Step 3b: QUALITY FILTER — 4-axis structural check
        # Based on analysis of 89 winners vs 227 losers:
        # Trades with 3+ axes = expectancy +1.74%, PnL +66%
        # Trades with <3 axes = expectancy -2.8%, PnL -744%
        quality_result = None
        if "BUY" in haiku_decision and analysis_summary:
            quality_result = self._quality_filter(haiku_decision, haiku_confidence, analysis_summary, pair=pair)
            haiku_decision = quality_result["decision"]
            haiku_confidence = quality_result["confidence"]
            if quality_result.get("note"):
                haiku_reason += f" | QUALITY: {quality_result['note']}"
                print(f"  📐 Quality filter: Grade {quality_result['grade']} ({quality_result['axes']}/5) — {quality_result['note']}")

        if haiku_decision.startswith("BUY"):
            print(f"  📊 Generating detailed analysis with MEGA 4 Mini...")

        # Step 4: VIP Check
        vip_result = self._vip_check(alert, analysis_summary)

        # Step 5: GPT-4o-mini generates FULL analysis message (no tool calls needed)
        full_msg = await self._format_full_analysis(alert, analysis_summary, haiku_decision, haiku_confidence, haiku_reason)

        # Prepend quality grade + VIP badge
        if quality_result and quality_result.get("grade"):
            grade = quality_result["grade"]
            axes = quality_result["axes"]
            details = quality_result.get("details", [])
            grade_line = f"📐 Quality: Grade {grade} ({axes}/5) — {', '.join(details)}\n"
            full_msg = grade_line + full_msg

        if vip_result.get("is_high_ticket"):
            full_msg = f"🏆 HIGH TICKET — Potentiel exceptionnel ({vip_result['vip_score']}/5: {', '.join(vip_result['reasons'])})\n\n{full_msg}"
        elif vip_result.get("is_vip"):
            full_msg = f"⭐ VIP — Potentiel eleve ({vip_result['vip_score']}/5: {', '.join(vip_result['reasons'])})\n\n{full_msg}"

        decision = AgentDecision(
            decision=haiku_decision,
            confidence=haiku_confidence,
            reasoning=full_msg,
            raw_response=full_msg,
            tools_called=["analyze_alert", "mega_mini_triage"],
        )
        # Attach VIP + quality data for processor to save
        decision.vip = vip_result
        decision.quality = quality_result
        return decision

    def _safety_filter(self, decision: str, confidence: float,
                       alert: Dict, summary: Dict) -> tuple:
        """Data-driven safety filter to prevent false BUY signals.

        Checks REAL technical data (not LLM opinion) for danger patterns.
        Returns (decision, confidence, safety_note) — may downgrade BUY to WATCH.

        Red flags that downgrade BUY → WATCH:
        1. EMA Stack 4H INVERSE (bearish structure)
        2. StochRSI 4H > 90 (overbought, correction imminent)
        3. ADX 4H < 15 (no trend at all)
        4. DI- > DI+ on 4H (sellers dominate)
        5. Conditions 0/5 AND no STC oversold (no edge)
        6. ML prediction = SKIP with low p_success
        """
        # HARD BLACKLIST — never trade these pairs
        BLACKLISTED_PAIRS = {"HOOKUSDT", "MBOXUSDT", "DCRUSDT"}  # Delisted or 100% lose
        pair = alert.get("pair", "")
        if pair in BLACKLISTED_PAIRS:
            return "SKIP", 0.0, f"BLACKLISTED: {pair} (delisted or 100% lose history)"

        # Check if pair is tradable on Binance (not delisted)
        try:
            from openclaw.pipeline.pair_filter import is_tradable
            if not is_tradable(pair):
                return "SKIP", 0.0, f"NOT_TRADABLE: {pair} (delisted or non-trading on Binance)"
        except Exception:
            pass

        red_flags = []
        score = alert.get("scanner_score", 0)

        # Check from analysis summary (real computed data)
        filters = summary.get("filters", {})

        # 1. EMA Stack 4H INVERSE = bearish structure
        ema_4h = filters.get("ema_stack_4h", "")
        if isinstance(ema_4h, str) and "INVERSE" in ema_4h.upper():
            red_flags.append("EMA_4H_INVERSE")

        # 2. StochRSI 4H overbought (> 90)
        stochrsi_4h = filters.get("stochrsi_4h", "")
        if isinstance(stochrsi_4h, str):
            import re
            k_match = re.search(r'k=(\d+\.?\d*)', stochrsi_4h)
            if k_match and float(k_match.group(1)) > 90:
                red_flags.append("StochRSI_4H_OVERBOUGHT")

        # 3. ADX too low = no trend
        adx_4h = alert.get("adx_4h", 0) or 0
        if adx_4h > 0 and adx_4h < 15:
            red_flags.append("ADX_4H_TOO_LOW")

        # 4. DI- > DI+ on 4H = sellers dominate
        di_plus = alert.get("di_plus_4h", 0) or 0
        di_minus = alert.get("di_minus_4h", 0) or 0
        if di_plus > 0 and di_minus > 0 and di_minus > di_plus:
            red_flags.append("DI_MINUS_DOMINANT")

        # 5. Conditions 0/5 AND STC NOT oversold = no edge
        conditions_str = summary.get("conditions", "")
        stc_str = summary.get("stc", "")
        if "0/" in str(conditions_str) and "✗" in str(stc_str):
            red_flags.append("NO_CONDITIONS_NO_STC")

        # 6. ML prediction SKIP with very low confidence
        ml_str = summary.get("ml_prediction", "")
        if "SKIP" in str(ml_str).upper():
            import re
            p_match = re.search(r'p_success=(\d+\.?\d*)', str(ml_str))
            if p_match and float(p_match.group(1)) < 0.25:
                red_flags.append("ML_STRONG_SKIP")

        # 7. Futures data: funding rate very positive + OI dropping = bearish
        futures_str = summary.get("futures", "")
        if isinstance(futures_str, str) and "BEARISH" in futures_str.upper():
            red_flags.append("FUTURES_BEARISH")

        # Decision logic based on red flags
        if len(red_flags) >= 3:
            # 3+ red flags → downgrade to WATCH
            return "WATCH", min(confidence, 0.50), f"Downgraded: {', '.join(red_flags)}"
        elif len(red_flags) >= 2:
            # 2 red flags → downgrade confidence, keep BUY WEAK
            new_conf = max(confidence - 0.15, 0.50)
            new_dec = "BUY WEAK" if new_conf >= 0.55 else "WATCH"
            return new_dec, new_conf, f"Reduced: {', '.join(red_flags)}"
        elif len(red_flags) == 1:
            # 1 red flag → small confidence reduction, keep original level
            new_conf = max(confidence - 0.05, 0.55)
            # Re-classify
            if decision == "BUY STRONG" and new_conf < 0.75:
                decision = "BUY"
            return decision, new_conf, f"Warning: {red_flags[0]}"
        else:
            # No red flags → pass through
            return decision, confidence, None

    def _quality_filter(self, decision: str, confidence: float, summary: Dict, pair: str = "") -> Dict:
        """5-axis structural quality filter.

        Based on empirical analysis of 4849 alerts + 89 winners vs 227 losers:
        - Axis 1 (Trend): ADX 4H > 40 OR DI spread 4H > 20  (+43% edge)
        - Axis 2 (Structure): FVG 1H ABOVE OR OB INSIDE STRONG (+38% edge)
        - Axis 3 (Momentum): MACD 4H Bullish (+26% edge)
        - Axis 4 (Timing): Vol ratio < 0.8x (+38% edge)
        - Axis 5 (Confirmation): 2nd alert on same pair today (+13% WR edge, 59% WR)

        Grade A+ (5/5): best setup
        Grade A  (3-4/5): tradable with boost
        Grade B  (2/5): no boost
        Grade C  (0-1/5): weak

        Returns dict with grade, axes, decision, confidence, details.
        """
        filters = summary.get("filters", {})
        details = []

        # ── AXE 1: TREND (ADX 4H > 40 OR DI spread 4H > 20) ──
        ax1 = False
        adx_4h_str = filters.get("adx_4h", "")
        macd_4h_str = filters.get("macd_4h", "")
        import re

        # Extract ADX value from filters
        adx_m = re.search(r'adx=([\d.]+)', str(adx_4h_str))
        adx_val = float(adx_m.group(1)) if adx_m else None

        # Extract DI spread from filters
        di_sp_m = re.search(r'di_spread=([\d.-]+)', str(adx_4h_str))
        di_spread = float(di_sp_m.group(1)) if di_sp_m else None

        if (adx_val and adx_val > 40) or (di_spread and di_spread > 20):
            ax1 = True
            val_str = f"ADX={adx_val:.0f}" if adx_val and adx_val > 40 else f"DI_sp={di_spread:.0f}"
            details.append(f"Trend({val_str})")

        # ── AXE 2: STRUCTURE (FVG 1H ABOVE OR OB INSIDE STRONG) ──
        ax2 = False
        # Check FVG position
        fvg_1h_str = filters.get("fvg_1h", "")
        fvg_above = "position=ABOVE" in str(fvg_1h_str)

        # Check OB INSIDE + STRONG
        ob_1h_str = str(summary.get("ob_1h_nearest", ""))
        ob_4h_str = str(summary.get("ob_4h_nearest", ""))
        ob_inside_strong = ("INSIDE" in ob_1h_str and "STRONG" in ob_1h_str) or \
                           ("INSIDE" in ob_4h_str and "STRONG" in ob_4h_str)

        if fvg_above or ob_inside_strong:
            ax2 = True
            val_str = "FVG_ABOVE" if fvg_above else "OB_INSIDE"
            details.append(f"Struct({val_str})")

        # ── AXE 3: MOMENTUM (MACD 4H Bullish) ──
        ax3 = False
        macd_trend = re.search(r'trend=(\w+)', str(macd_4h_str))
        if macd_trend and macd_trend.group(1).upper() == "BULLISH":
            ax3 = True
            details.append("Mom(MACD4H)")

        # ── AXE 4: TIMING (Vol 15m negative) ──
        ax4 = False
        # Get volume 15m from indicators
        ind_15m = summary.get("ind_15m", "")
        # Try to find vol_pct from the 15m indicator string or from filters
        vol_str = str(summary.get("filters", {}).get("vol_spike_1h", ""))
        # Check 15m volume from indicator data
        for tf_key in ["ind_15m"]:
            tf_data = str(summary.get(tf_key, ""))
            # Volume data not directly available in summary, check via stc/vol
            pass

        # Alternative: check if vol ratio < 1 from filters
        vol_1h_str = str(filters.get("vol_spike_1h", ""))
        vol_ratio_m = re.search(r'ratio=([\d.]+)', vol_1h_str)
        if vol_ratio_m:
            ratio = float(vol_ratio_m.group(1))
            if ratio < 0.8:  # Low volume = compression
                ax4 = True
                details.append(f"Timing(Vol={ratio:.1f}x)")

        # ── AXE 5: CONFIRMATION (2nd alert on same pair today → 59% WR) ──
        ax5 = False
        if pair:
            try:
                from datetime import datetime, timezone, timedelta
                today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0).isoformat()
                from openclaw.config import get_settings as _gs
                from supabase import create_client as _sc2
                _s2 = _gs()
                _sb2 = _sc2(_s2.supabase_url, _s2.supabase_service_key)
                r = _sb2.table("agent_memory") \
                    .select("id", count="exact") \
                    .eq("pair", pair) \
                    .gte("timestamp", today_start) \
                    .execute()
                prior_alerts = r.count or 0
                if prior_alerts >= 1:  # This is the 2nd+ alert today
                    ax5 = True
                    details.append(f"Confirm({prior_alerts+1}x today)")
            except Exception:
                pass

        # ── GRADE ──
        axes_count = sum(1 for a in [ax1, ax2, ax3, ax4, ax5] if a)
        if axes_count >= 5:
            grade = "A+"
        elif axes_count >= 3:
            grade = "A"
        elif axes_count >= 2:
            grade = "B"
        else:
            grade = "C"

        # ── CONFIDENCE ADJUSTMENT (multiplicative) ──
        new_conf = confidence
        new_dec = decision
        note = None

        if axes_count >= 3:
            # Grade A/A+: multiplicative boost
            if ax1: new_conf *= 1.10
            if ax2: new_conf *= 1.15
            if ax3: new_conf *= 1.10
            if ax4: new_conf *= 1.10
            if ax5: new_conf *= 1.05  # Confirmation = smaller boost
            new_conf = min(round(new_conf, 4), 0.95)

            # Re-classify based on boosted confidence
            if new_conf >= 0.75:
                new_dec = "BUY STRONG"
            elif new_conf >= 0.60:
                new_dec = "BUY"
            else:
                new_dec = "BUY WEAK"

            if new_dec != decision:
                note = f"Grade {grade} ({axes_count}/5) → {decision} upgraded to {new_dec} ({confidence*100:.0f}%→{new_conf*100:.0f}%)"
            else:
                note = f"Grade {grade} ({axes_count}/5) — conf {confidence*100:.0f}%→{new_conf*100:.0f}%"
        else:
            # Grade B/C: no boost, just log
            note = f"Grade {grade} ({axes_count}/5) — no boost"

        return {
            "decision": new_dec,
            "confidence": new_conf,
            "grade": grade,
            "axes": axes_count,
            "ax1_trend": ax1,
            "ax2_structure": ax2,
            "ax3_momentum": ax3,
            "ax4_timing": ax4,
            "ax5_confirmation": ax5,
            "details": details,
            "note": note,
        }

    def _vip_check(self, alert: Dict, summary: Dict) -> Dict:
        """Check if this trade qualifies as VIP / HIGH TICKET.

        Does NOT change the decision — just adds a label.
        Based on analysis of 70 winners +10%.

        Criteria (5 points):
        1. DI+ spread 4H >= 15 (buyers dominant)
        2. Score >= 8
        3. PP + EC both active
        4. Price INSIDE or < 3% of OB STRONG (from analysis_summary)
        5. Accumulation >= 3 days (from analysis_summary.accumulation)

        3+ criteria → VIP, 4+ → HIGH TICKET
        """
        reasons = []
        score_count = 0

        # 1. DI+ spread
        di_plus = alert.get("di_plus_4h") or 0
        di_minus = alert.get("di_minus_4h") or 0
        di_spread = di_plus - di_minus
        if di_spread >= 15:
            score_count += 1
            reasons.append(f"DI+ spread +{di_spread:.0f}")

        # 2. Score >= 8
        scanner_score = alert.get("scanner_score") or 0
        if scanner_score >= 8:
            score_count += 1
            reasons.append(f"Score {scanner_score}/10")

        # 3. PP + EC
        pp = alert.get("pp", False)
        ec = alert.get("ec", False)
        if pp and ec:
            score_count += 1
            reasons.append("PP+EC")

        # 4. OB proximity — check from summary
        ob_inside = False
        for ob_key in ["ob_1h_nearest", "ob_4h_nearest"]:
            ob_str = str(summary.get(ob_key, ""))
            if "INSIDE" in ob_str and "STRONG" in ob_str:
                ob_inside = True
                break
            elif "BELOW" in ob_str:
                import re
                dist_match = re.search(r'(-?\d+\.?\d*)%', ob_str)
                if dist_match and abs(float(dist_match.group(1))) <= 3 and "STRONG" in ob_str:
                    ob_inside = True
                    break
        if ob_inside:
            score_count += 1
            reasons.append("OB STRONG proche")

        # 5. Accumulation >= 3 days (from realtime analysis)
        acc = summary.get("accumulation", {})
        if isinstance(acc, str):
            # May be in compact summary format
            acc = {}
        acc_days = 0
        if isinstance(acc, dict):
            acc_days = acc.get("days", 0) or 0
        if acc_days >= 3:
            score_count += 1
            vol_trend = acc.get("volume_trend", "")
            reasons.append(f"Accum {acc_days:.0f}j" + (f" vol↓" if vol_trend == "decreasing" else ""))
            # Bonus: >= 5 days counts extra
            if acc_days >= 5:
                score_count += 1
                reasons[-1] = f"Accum {acc_days:.0f}j (long)" + (f" vol↓" if vol_trend == "decreasing" else "")

        is_vip = score_count >= 3
        is_high_ticket = score_count >= 4

        if is_vip:
            print(f"  {'🏆' if is_high_ticket else '⭐'} VIP Check: {score_count}/5 — {', '.join(reasons)}")

        return {
            "is_vip": is_vip,
            "is_high_ticket": is_high_ticket,
            "vip_score": score_count,
            "reasons": reasons,
        }

    async def _format_full_analysis(self, alert: Dict, summary: Dict,
                                      decision: str, confidence: float, reason: str) -> str:
        """Generate FULL detailed analysis message from summary data.
        Uses GPT-4o-mini with ONE call — just formatting, no tool calls.
        Cost: ~$0.002 (very cheap)"""
        tracker = get_token_tracker()
        pair = alert.get("pair", "?")
        score = alert.get("scanner_score", 0)
        price = alert.get("price", 0)

        # Get insights for context-aware analysis
        insights_block = self.insights.format_for_prompt()

        # Full summary dump — NO truncation
        summary_json = json.dumps(summary, indent=2, default=str)

        # Build comprehensive data dump for GPT to format
        data_msg = f"""Formate une analyse COMPLETE et DETAILLEE pour Telegram avec TOUTES ces donnees.
Tu dois utiliser CHAQUE indicateur fourni — ne rien omettre.

Pair: {pair} | Score: {score}/10 | Prix: {price}
TF: {alert.get('timeframes', [])} | PP={alert.get('pp')} EC={alert.get('ec')}
DI+ 4H={alert.get('di_plus_4h')} DI- 4H={alert.get('di_minus_4h')} ADX 4H={alert.get('adx_4h')}
LazyBar: {alert.get('lazy_values')} | EC moves: {alert.get('ec_moves')}
RSI moves: {alert.get('rsi_moves')} | Vol%: {alert.get('vol_pct')}
RSI: {alert.get('rsi')} | DI+ moves: {alert.get('di_plus_moves')} | DI- moves: {alert.get('di_minus_moves')}

Analyse technique COMPLETE:
{summary_json}

Decision du triage: {decision} ({int(confidence*100)}%) — {reason}

{insights_block}

FORMATE EXACTEMENT comme ceci (COMPLET, ne rien omettre):

🎯 PAIR — MEGA BUY SCORE/10

📊 Decision: DECISION (XX% confiance)
🤖 ML Score: X.XX | Backtest: données

⚠️ Conditions Progressives (X/5 → Y/5 avec tolerance -2%):
• ema100_1h: ✓/✗/≈ (distance%) → VALIDEE/QUASI-VALIDEE/ECHOUEE
• ema20_4h: ...
• cloud_1h: ...
• cloud_30m: ...
• choch_bos: ✓/✗

📈 Indicateurs Techniques:
• RSI: 1h=XX / 4h=XX / 1d=XX (RSI MTF aligne X/3)
• ADX 1H: XX MODERATE/STRONG (DI+ XX vs DI- XX) = ±XX spread
• ADX 4H: XX MODERATE/STRONG (DI+ XX vs DI- XX) = ±XX spread
• MACD 1H: BULLISH/BEARISH (hist: X, growing: ✓/✗)
• MACD 4H: BULLISH/BEARISH (hist: X, growing: ✓/✗)
• LazyBar: 1h=XX 🟢/🟡/🔴 / 15m=XX 🟢/🟡/🔴
• EC RSI: 1h=±XX / 15m=±XX
• EMA Stack: 1H=PERFECT/MIXED/INVERSE (X/4) / 4H=PERFECT/MIXED/INVERSE (X/4)
• StochRSI: 1H=OVERBOUGHT/NEUTRAL/OVERSOLD (k=XX) / 4H=...
• STC: TFs oversold avec valeurs
• Vol%: 1h=XX% / 15m=XX%

🏦 Volume Profile:
• 1H: POC=XX, VAH=XX, VAL=XX → Position: INVA/ABOVEVAH/BELOWVAL (XX%)
• 4H: POC=XX → Position: ...

🧱 Order Blocks:
• 1H: X OB (nearest: XX-XX, ABOVE/BELOW XX%, STRONG/MODERATE/WEAK, fresh/mitigated)
• 4H: X OB (nearest: XX-XX, ABOVE/BELOW XX%, ...)

🎯 Fibonacci & FVG:
• Fib 4H: ✓/✗ | Fib 1H: ✓/✗
• FVG 1H: ✓/✗ (X count, position) | FVG 4H: ✓/✗

🌍 Contexte Marche:
• BTC: $XX (trend) correlation
• ETH: $XX (trend) correlation
• Fear&Greed: XX (label)

✅ Points Positifs:
- Liste 3-5 points forts avec donnees chiffrees
- Utilise les insights appris (STC triple zero, volume, etc.)

❌ Signaux d'Alerte:
- Liste 2-4 risques avec donnees chiffrees

🧠 Raisonnement:
3-4 phrases data-driven expliquant la decision. Mentionne les patterns connus (Phoenix, Sleeping Giant, etc.) si applicable. Compare avec les insights appris.

💰 Si entry: $XX
🛡️ SL suggere: $XX (-X%) avec justification
🎯 TP1: $XX (+X%)
📐 R:R potentiel: 1:X"""

        system_prompt = """Tu es OpenClaw, un analyste trading expert crypto. Tu formates les donnees techniques en analyses detaillees pour Telegram.

REGLES STRICTES:
1. Utilise TOUS les chiffres fournis dans les donnees — ne rien omettre
2. N'invente AUCUN chiffre — si une donnee manque, ecris "N/A"
3. Applique les insights appris (STC triple zero = signal fort, etc.)
4. Sois precis et data-driven dans le raisonnement
5. Calcule le Entry/SL/TP basé sur les niveaux techniques (VP, OB, Fib)
6. Classifie le trade: DEPARTURE (STC oversold, fond) ou CONTINUATION (tendance active)
7. Si STC triple zero → mentionne que c'est le signal le plus fiable (100% WR)
8. Si conditions 0/5 mais STC oversold → mentionne le paradoxe conditions faibles / signal fort"""

        try:
            if self.openai_client:
                response = await asyncio.to_thread(
                    self.openai_client.chat.completions.create,
                    model=self.triage_model,
                    max_tokens=3000,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": data_msg},
                    ],
                )
                tracker.record_openai(dict(response.usage), self.triage_model)
                return response.choices[0].message.content or reason
        except Exception as e:
            print(f"⚠️ Format error: {e}")

        # Fallback: return basic message
        return (
            f"🎯 *{pair}* — MEGA BUY {score}/10\n"
            f"🤖 MEGA 4 Mini\n\n"
            f"📊 Decision: {decision} ({int(confidence*100)}%)\n\n"
            f"Conditions: {summary.get('conditions', 'N/A')}\n"
            f"ML: {summary.get('ml_prediction', 'N/A')}\n"
            f"Backtest: {summary.get('backtest', 'N/A')}\n\n"
            f"🧠 {reason}"
        )

    async def _sonnet_deep_analysis(self, alert: Dict, analysis_summary: Dict = None) -> AgentDecision:
        """Full Sonnet analysis with tools — only called for promising alerts."""
        conditions_str = ", ".join(
            f"{k}={'YES' if v else 'no'}"
            for k, v in {
                "RSI": alert.get("rsi_check"), "DMI": alert.get("dmi_check"),
                "AST": alert.get("ast_check"), "CHoCH": alert.get("choch"),
                "Zone": alert.get("zone"), "Lazy": alert.get("lazy"),
                "Vol": alert.get("vol"), "ST": alert.get("st"),
                "PP": alert.get("pp"), "EC": alert.get("ec"),
            }.items()
        )

        def _fmt_dict(d):
            if not d or not isinstance(d, dict):
                return "N/A"
            return " | ".join(f"{k}={v}" for k, v in d.items())

        user_message = ALERT_ANALYSIS_PROMPT.format(
            pair=alert.get("pair", ""),
            price=alert.get("price", 0),
            score=alert.get("scanner_score", 0),
            timeframes=", ".join(alert.get("timeframes", [])),
            timestamp=alert.get("alert_timestamp", ""),
            alert_id=alert.get("id", ""),
            conditions=conditions_str,
            di_plus_4h=alert.get("di_plus_4h", "N/A"),
            di_minus_4h=alert.get("di_minus_4h", "N/A"),
            adx_4h=alert.get("adx_4h", "N/A"),
            rsi=alert.get("rsi", "N/A"),
            lazy_values=_fmt_dict(alert.get("lazy_values")),
            lazy_moves=_fmt_dict(alert.get("lazy_moves")),
            ec_moves=_fmt_dict(alert.get("ec_moves")),
            rsi_moves=_fmt_dict(alert.get("rsi_moves")),
            vol_pct=_fmt_dict(alert.get("vol_pct")),
            di_plus_moves=_fmt_dict(alert.get("di_plus_moves")),
            di_minus_moves=_fmt_dict(alert.get("di_minus_moves")),
            adx_moves=_fmt_dict(alert.get("adx_moves")),
            puissance=alert.get("puissance", "N/A"),
            emotion=alert.get("emotion", "N/A"),
        )

        return await self._run_tool_loop(user_message)

    async def answer_question(self, question: str) -> str:
        """Answer a user question (conversational mode)."""
        user_message = QUESTION_PROMPT.format(question=question)
        result = await self._run_tool_loop(user_message)
        return result.raw_response

    async def _run_tool_loop(self, user_message: str) -> AgentDecision:
        """Core tool-use loop using OpenAI GPT-4o-mini (primary) or Claude (backup).
        OpenAI function calling is used instead of Anthropic tool-use."""
        tracker = get_token_tracker()
        insights_block = self.insights.format_for_prompt()
        system_with_insights = SYSTEM_PROMPT + insights_block

        if self.openai_client:
            return await self._openai_tool_loop(user_message, system_with_insights, tracker)
        elif self.claude_client:
            return await self._claude_tool_loop(user_message, system_with_insights, tracker)
        else:
            return AgentDecision(decision="WATCH", confidence=0.3, reasoning="No AI provider", raw_response="", tools_called=[], error="No API key")

    async def _openai_tool_loop(self, user_message: str, system: str, tracker) -> AgentDecision:
        """Tool loop using OpenAI function calling."""
        # Convert Anthropic tools to OpenAI function format
        openai_tools = []
        for tool in TOOLS:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                }
            })

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ]
        tools_called = []

        for round_num in range(self.max_tool_rounds):
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model=self.deep_model,
                max_tokens=self.max_tokens,
                messages=messages,
                tools=openai_tools if round_num == 0 else openai_tools,  # Always provide tools
                tool_choice="auto",
            )
            tracker.record_openai(dict(response.usage), self.deep_model)

            choice = response.choices[0]

            # Check for tool calls
            if choice.message.tool_calls:
                messages.append(choice.message)

                for tc in choice.message.tool_calls:
                    tool_name = tc.function.name
                    try:
                        tool_input = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}
                    tools_called.append(tool_name)

                    print(f"  🔧 Tool: {tool_name}({json.dumps(tool_input)[:80]}...)")

                    handler = TOOL_HANDLERS.get(tool_name)
                    if handler:
                        try:
                            result = await handler(**tool_input)
                        except Exception as e:
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result, default=str),
                    })
            else:
                # Final answer
                text = choice.message.content or ""
                decision = self._parse_decision(text)
                decision.tools_called = tools_called
                decision.raw_response = text
                return decision

        return AgentDecision(
            decision="WATCH", confidence=0.3,
            reasoning="Max tool rounds exceeded",
            raw_response="", tools_called=tools_called,
            error="Max tool rounds exceeded"
        )

    async def _claude_tool_loop(self, user_message: str, system: str, tracker) -> AgentDecision:
        """Fallback tool loop using Claude API."""
        messages = [{"role": "user", "content": user_message}]
        tools_called = []

        for round_num in range(self.max_tool_rounds):
            response = await asyncio.to_thread(
                self.claude_client.messages.create,
                model=self.model,
                max_tokens=self.max_tokens,
                system=system,
                tools=TOOLS,
                messages=messages,
            )
            tracker.record(response, self.model)

            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tools_called.append(tool_name)
                        print(f"  🔧 Tool: {tool_name}({json.dumps(tool_input)[:80]}...)")
                        handler = TOOL_HANDLERS.get(tool_name)
                        if handler:
                            try:
                                result = await handler(**tool_input)
                            except Exception as e:
                                result = {"error": str(e)}
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}
                        tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps(result, default=str)})
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
            else:
                text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        text += block.text
                decision = self._parse_decision(text)
                decision.tools_called = tools_called
                decision.raw_response = text
                return decision

        return AgentDecision(decision="WATCH", confidence=0.3, reasoning="Max rounds", raw_response="", tools_called=tools_called)

    def _parse_decision(self, text: str) -> AgentDecision:
        """Extract decision, confidence, reasoning from Claude's response.

        Supports 3-level BUY system:
        - BUY STRONG (confidence >= 75%) — STC zero + volume + score >= 9
        - BUY (confidence 60-74%) — conditions fortes
        - BUY WEAK (confidence 55-59%) — signal partiel
        """
        text_upper = text.upper()

        # Detect decision
        if "DECISION: BUY" in text_upper or "RECOMMANDATION: BUY" in text_upper:
            decision = "BUY"
        elif "DECISION: SKIP" in text_upper or "RECOMMANDATION: SKIP" in text_upper or "AVOID" in text_upper:
            decision = "SKIP"
        else:
            decision = "WATCH"

        # Extract confidence (look for "XX% confiance" or "confidence: XX%")
        confidence = 0.5
        import re
        conf_match = re.search(r'(\d{1,3})%\s*(?:confiance|confidence)', text, re.IGNORECASE)
        if conf_match:
            confidence = int(conf_match.group(1)) / 100

        # Apply 3-level BUY classification
        if decision == "BUY":
            if confidence >= 0.75:
                decision = "BUY STRONG"
            elif confidence >= 0.60:
                decision = "BUY"
            else:
                decision = "BUY WEAK"

        # Extract reasoning (first 2-3 sentences after "Raisonnement" or just the last paragraph)
        reasoning = text[-500:] if len(text) > 500 else text

        return AgentDecision(
            decision=decision,
            confidence=confidence,
            reasoning=reasoning,
            raw_response=text,
            tools_called=[],
        )
