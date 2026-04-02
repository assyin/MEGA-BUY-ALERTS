"""Audit Negotiator v3 — point-by-point discussion with OpenClaw.

Improvements v3:
- OpenClaw MUST use ONLY pairs from our portfolio (no BTC/DOT/XRP examples)
- Claude challenges with LIVE data (calls tools during negotiation)
- No filler — every response must be data-driven with real system numbers
- 6 exchanges: 3 rounds of back-and-forth, decision in last round
- OpenClaw's decision is FINAL
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from openai import OpenAI

from openclaw.config import get_settings
from openclaw.agent.chat import ChatManager


ACCORD = "ACCORD"
DESACCORD = "DESACCORD"
COMPROMIS = "COMPROMIS"

MAX_ROUNDS = 3  # 3 rounds = 6 exchanges


class AuditNegotiator:
    """Negotiates audit points with OpenClaw, point by point."""

    def __init__(self, chat_manager: ChatManager = None):
        settings = get_settings()
        self.openai = OpenAI(api_key=settings.openai_api_key)
        self.chat = chat_manager or ChatManager()

        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)

        # Load real portfolio pairs for context
        self.real_pairs = self._load_real_pairs()
        self.portfolio_summary = self._load_portfolio_summary()

    def _load_real_pairs(self) -> list:
        """Load pairs that are ACTUALLY in our portfolio/trades."""
        pairs = set()
        try:
            r = self.sb.table("openclaw_positions").select("pair").limit(200).execute()
            pairs.update(p["pair"] for p in (r.data or []))
        except Exception:
            pass
        try:
            r = self.sb.table("agent_memory").select("pair").limit(500).execute()
            pairs.update(p["pair"] for p in (r.data or []))
        except Exception:
            pass
        return sorted(pairs)

    def _load_portfolio_summary(self) -> str:
        """Load a compact portfolio summary for context."""
        try:
            r = self.sb.table("openclaw_portfolio_state").select("*").eq("id", "main").single().execute()
            s = r.data or {}
            return (
                f"Balance: ${s.get('balance', 5000):.0f} | Initial: ${s.get('initial_capital', 5000):.0f} | "
                f"PnL: ${s.get('total_pnl', 0):.1f} | WR: {s.get('wins', 0)}W/{s.get('losses', 0)}L | "
                f"DD max: {s.get('max_drawdown_pct', 0):.1f}%"
            )
        except Exception:
            return "Portfolio data unavailable"

    async def negotiate_all(self, audit_id: str, points: List[Dict],
                            on_progress: Optional[callable] = None) -> List[Dict]:
        """Negotiate all audit points sequentially."""
        discussions = []

        for point in points:
            try:
                print(f"  🔄 Negotiating point #{point['id']}: {point['title']}")
                result = await self._negotiate_point(audit_id, point)
                discussions.append(result)
                self._save_progress(audit_id, discussions)
                print(f"  ✅ Point #{point['id']} → {result['decision']}")
            except Exception as e:
                print(f"  ❌ Point #{point['id']} error: {e}")
                discussions.append({
                    "point_id": point["id"],
                    "exchanges": [{"role": "system", "content": f"Erreur: {str(e)}"}],
                    "decision": DESACCORD,
                    "decision_reason": f"Erreur technique: {str(e)}",
                })
            await asyncio.sleep(2)

        return discussions

    async def _negotiate_point(self, audit_id: str, point: Dict) -> Dict:
        """Negotiate a single point — 3 rounds (6 exchanges).

        Round 1: Claude presents → OpenClaw diagnoses
        Round 2: Claude challenges with live data → OpenClaw defends/adjusts
        Round 3: Claude summarizes → OpenClaw gives FINAL decision + action plan
        """
        exchanges = []

        conv_id = self.chat.create_conversation(
            f"Audit #{audit_id[:8]} - Point #{point['id']}: {point['title']}"
        )
        if not conv_id:
            return {"point_id": point["id"], "exchanges": [], "decision": DESACCORD, "decision_reason": "Conv failed"}

        # ── Round 1: Presentation → Diagnosis ──
        # First, send context message to OpenClaw so it knows we're auditing portfolio $5K
        context_msg = (
            "CONTEXTE DE CET AUDIT: On audite ton PORTFOLIO VIRTUEL de $5,000 (table openclaw_positions). "
            f"Balance actuelle: {self.portfolio_summary}. "
            "NE CONFONDS PAS avec la Simulation ($14K). "
            "Tous tes chiffres doivent venir du portfolio $5K. "
            "Utilise UNIQUEMENT les paires de notre systeme.\n\n"
            "⚠️ REGLE CRITIQUE: Avant de proposer de blacklister ou eviter une paire, "
            "VERIFIE sa performance reelle dans le portfolio. "
            "NE BLACKLISTE JAMAIS une paire avec WR >= 60% ou PnL positif. "
            "Utilise tes outils pour verifier les stats avant toute recommandation."
        )
        await self.chat.send_message(conv_id, context_msg)

        claude_1 = self._build_presentation(point)
        exchanges.append({"role": "claude", "content": claude_1})
        openclaw_1 = await self.chat.send_message(conv_id, claude_1)
        exchanges.append({"role": "openclaw", "content": openclaw_1})

        # ── Round 2: Challenge with live data → Defense ──
        # Claude fetches live data to challenge OpenClaw's response
        live_data = await self._fetch_live_data_for_point(point)
        claude_2 = await self._build_challenge(point, exchanges, live_data)
        exchanges.append({"role": "claude", "content": claude_2})
        openclaw_2 = await self.chat.send_message(conv_id, claude_2)
        exchanges.append({"role": "openclaw", "content": openclaw_2})

        # ── Round 3: Summary → Final Decision ──
        claude_3 = await self._build_conclusion(point, exchanges)
        exchanges.append({"role": "claude", "content": claude_3})
        openclaw_3 = await self.chat.send_message(conv_id, claude_3)
        exchanges.append({"role": "openclaw", "content": openclaw_3})

        # ── Extract decision ──
        decision, reason = await self._extract_decision(point, exchanges)

        return {
            "point_id": point["id"],
            "conversation_id": conv_id,
            "exchanges": exchanges,
            "decision": decision,
            "decision_reason": reason,
        }

    # ─── Exchange Builders ────────────────────────────────────

    def _get_pair_stats(self, text: str) -> str:
        """Extract pair names from text and fetch their REAL performance stats.
        Prevents wrong recommendations like blacklisting winning pairs."""
        import re
        pairs_found = set(re.findall(r'[A-Z]{2,15}USDT', text))
        if not pairs_found:
            return ""

        stats_lines = []
        for pair in pairs_found:
            try:
                r = self.sb.table("openclaw_positions").select("pnl_pct,pnl_usd,close_reason") \
                    .eq("pair", pair).eq("status", "CLOSED").execute()
                trades = r.data or []
                if not trades:
                    stats_lines.append(f"  {pair}: 0 trades clotures (pas de donnees)")
                    continue
                wins = len([t for t in trades if (t.get("pnl_pct") or 0) > 0])
                losses = len(trades) - wins
                total_pnl = sum(t.get("pnl_usd", 0) or 0 for t in trades)
                wr = round(wins / len(trades) * 100, 1) if trades else 0
                status_emoji = "🟢" if wr >= 60 else "🟡" if wr >= 40 else "🔴"
                stats_lines.append(f"  {status_emoji} {pair}: WR {wr}% ({wins}W/{losses}L) PnL ${total_pnl:+.1f}")
            except Exception:
                pass

        if not stats_lines:
            return ""
        return "\n📊 STATS REELLES des paires mentionnees:\n" + "\n".join(stats_lines) + "\n⚠️ NE PROPOSE PAS de blacklister une paire avec WR >= 60% ou PnL positif!\n"

    def _build_presentation(self, point: Dict) -> str:
        """Round 1: Claude presents with portfolio context + pair stats."""
        prio = "🔴 CRITIQUE" if point["priority"] >= 8 else "🟡 IMPORTANT" if point["priority"] >= 6 else "🟢 INFO"

        # Top 10 most traded pairs for context
        top_pairs = self.real_pairs[:20]

        # Get real stats for any pairs mentioned in the point
        pair_stats = self._get_pair_stats(point.get("evidence", "") + " " + point.get("recommendation", ""))

        return (
            f"## Point d'Audit #{point['id']}: {point['title']} [{prio}]\n\n"
            f"**Priorite**: {point['priority']}/10\n"
            f"**CONTEXTE**: On audite le PORTFOLIO VIRTUEL de $5,000 (table openclaw_positions).\n"
            f"**Portfolio actuel**: {self.portfolio_summary}\n\n"
            f"⚠️ ATTENTION: NE CONFONDS PAS avec la Simulation ($14K, table simulation). "
            f"On parle UNIQUEMENT du portfolio $5,000 gere par OpenClaw.\n\n"
            f"### Evidence (donnees reelles du portfolio $5K)\n{point['evidence']}\n\n"
            f"{pair_stats}"
            f"### Ma recommandation\n{point['recommendation']}\n\n"
            f"---\n\n"
            f"OpenClaw, reponds avec:\n"
            f"1. **Ton diagnostic** base sur les chiffres du PORTFOLIO $5K ci-dessus\n"
            f"2. **D'accord ou pas ?** Si non, donne des chiffres qui contredisent\n"
            f"3. **Plan d'action concret** avec des paires, des chiffres, des delais\n\n"
            f"⚠️ REGLES STRICTES:\n"
            f"- On parle du PORTFOLIO $5,000 (openclaw_positions), PAS de la simulation\n"
            f"- Utilise UNIQUEMENT les paires de notre systeme: {', '.join(top_pairs[:15])}...\n"
            f"- NE MENTIONNE PAS de paires generiques (DOT, XRP, etc.) sauf si elles sont dans notre portfolio\n"
            f"- Chaque argument doit inclure un chiffre reel du portfolio $5K\n"
            f"- Utilise tes outils (analyze_alert, get_backtest_history) pour verifier les donnees"
        )

    async def _fetch_live_data_for_point(self, point: Dict) -> str:
        """Fetch live data relevant to the audit point for Claude's challenge."""
        title = point.get("title", "").lower()
        data_parts = []

        try:
            # Get recent trades
            r = self.sb.table("openclaw_positions").select("pair,pnl_pct,pnl_usd,decision,close_reason,status") \
                .order("opened_at", desc=True).limit(30).execute()
            positions = r.data or []

            if "sl" in title or "tp" in title or "dynamique" in title:
                tp_hits = [p for p in positions if p.get("close_reason") == "TP_HIT"]
                sl_hits = [p for p in positions if p.get("close_reason") == "SL_HIT"]
                data_parts.append(f"LIVE: {len(tp_hits)} TP hits, {len(sl_hits)} SL hits sur les 30 derniers trades")
                if tp_hits:
                    avg_tp = sum(p.get("pnl_pct", 0) or 0 for p in tp_hits) / len(tp_hits)
                    data_parts.append(f"Avg TP PnL: +{avg_tp:.1f}%")
                    tight = len([p for p in tp_hits if (p.get("pnl_pct") or 0) < 3])
                    data_parts.append(f"TP < 3%: {tight}/{len(tp_hits)}")

            if "drawdown" in title or "risque" in title:
                open_pos = [p for p in positions if p.get("status") == "OPEN"]
                danger = [p for p in open_pos if (p.get("pnl_pct") or 0) < -5]
                data_parts.append(f"LIVE: {len(open_pos)} positions ouvertes, {len(danger)} en danger (<-5%)")
                if danger:
                    data_parts.append(f"Danger: {', '.join(p.get('pair','?') + ' ' + str(round(p.get('pnl_pct',0),1)) + '%' for p in danger)}")

            if "pair" in title or "star" in title or "probleme" in title:
                from collections import Counter
                pair_results = Counter()
                for p in positions:
                    if p.get("close_reason"):
                        pair = p.get("pair", "?")
                        if (p.get("pnl_pct") or 0) > 0:
                            pair_results[pair] += 1
                        else:
                            pair_results[pair] -= 1
                if pair_results:
                    best = pair_results.most_common(3)
                    worst = pair_results.most_common()[-3:]
                    data_parts.append(f"LIVE Best pairs: {', '.join(f'{p}({c:+d})' for p,c in best)}")
                    data_parts.append(f"LIVE Worst pairs: {', '.join(f'{p}({c:+d})' for p,c in worst)}")

            if "sizing" in title or "buy strong" in title.lower():
                by_dec = {}
                for p in positions:
                    dec = p.get("decision", "?")
                    if dec not in by_dec:
                        by_dec[dec] = {"count": 0, "pnl": 0}
                    by_dec[dec]["count"] += 1
                    by_dec[dec]["pnl"] += (p.get("pnl_usd") or 0)
                summary = {k: str(v["count"]) + " trades $" + format(v["pnl"], "+.0f") for k, v in by_dec.items()}
                data_parts.append("LIVE by decision: " + json.dumps(summary))

        except Exception as e:
            data_parts.append(f"Live data fetch error: {e}")

        return "\n".join(data_parts) if data_parts else "Pas de donnees live supplementaires"

    async def _build_challenge(self, point: Dict, exchanges: List[Dict], live_data: str) -> str:
        """Round 2: Claude challenges with LIVE data from PORTFOLIO $5K only."""
        openclaw_response = exchanges[-1]["content"]

        response = await asyncio.to_thread(
            self.openai.chat.completions.create,
            model="gpt-4o",
            max_tokens=800,
            messages=[
                {"role": "system", "content": (
                    "Tu es un auditeur de trading EXIGEANT. Tu audites le PORTFOLIO VIRTUEL de $5,000 "
                    "(table openclaw_positions, balance ~$4091, initial $5000).\n\n"
                    "⚠️ IMPORTANT: Il existe aussi une SIMULATION separee ($14K, 7 portfolios). "
                    "NE CONFONDS PAS les deux. Si OpenClaw cite des chiffres de $14K ou des balances > $6000, "
                    "c'est la simulation — CORRIGE-LE.\n\n"
                    "Ton role:\n"
                    "1. COMPARE la reponse d'OpenClaw avec les donnees LIVE du PORTFOLIO $5K\n"
                    "2. Si OpenClaw confond portfolio ($5K) et simulation ($14K) → CORRIGE\n"
                    "3. Si OpenClaw mentionne des paires HORS systeme → signale\n"
                    "4. Si OpenClaw donne des generalites → exige des chiffres du portfolio $5K\n"
                    "5. Si OpenClaw propose de BLACKLISTER une paire avec WR >= 60% ou PnL positif → REFUSE et montre les stats\n"
                    "6. Si OpenClaw a raison → admets-le et propose un plan concret\n"
                    "7. NE DEMANDE PAS encore la decision finale\n\n"
                    "Sois direct. Chiffres du PORTFOLIO $5K obligatoires."
                )},
                {"role": "user", "content": (
                    f"CONTEXTE: PORTFOLIO $5,000 (PAS simulation $14K)\n\n"
                    f"Point: {point['title']} (P{point['priority']})\n"
                    f"Evidence: {point['evidence']}\n\n"
                    f"Reponse OpenClaw:\n{openclaw_response[:2000]}\n\n"
                    f"DONNEES LIVE du PORTFOLIO $5K:\n{live_data}\n\n"
                    f"Paires du portfolio: {', '.join(self.real_pairs[:30])}\n\n"
                    f"Challenge OpenClaw. Corrige si il confond portfolio et simulation."
                )},
            ],
        )
        return response.choices[0].message.content or "..."

    async def _build_conclusion(self, point: Dict, exchanges: List[Dict]) -> str:
        """Round 3: Claude summarizes and asks for FINAL decision + action."""
        history = "\n\n".join([
            f"{'[Auditeur]' if e['role'] == 'claude' else '[OpenClaw]'}: {e['content'][:500]}"
            for e in exchanges
        ])

        response = await asyncio.to_thread(
            self.openai.chat.completions.create,
            model="gpt-4o",
            max_tokens=500,
            messages=[
                {"role": "system", "content": (
                    "Tu es l'auditeur du PORTFOLIO $5,000. DERNIER echange. Tu dois:\n"
                    "1. Resume en 2-3 phrases ce qui a ete discute (chiffres du PORTFOLIO $5K uniquement)\n"
                    "2. Points d'accord vs desaccord\n"
                    "3. Demande la DECISION FINALE d'OpenClaw:\n"
                    "   ACCORD = accepte la recommandation\n"
                    "   COMPROMIS = version modifiee (preciser)\n"
                    "   DESACCORD = refuse (preciser pourquoi avec donnees du portfolio $5K)\n"
                    "4. Demande un PLAN D'ACTION concret en 1-3 etapes avec chiffres\n\n"
                    "⚠️ Rappel: PORTFOLIO $5K, PAS simulation $14K. Sois concis."
                )},
                {"role": "user", "content": (
                    f"Point: {point['title']}\n"
                    f"Recommandation: {point['recommendation']}\n\n"
                    f"Historique:\n{history}"
                )},
            ],
        )
        return response.choices[0].message.content or "..."

    # ─── Decision Extraction ──────────────────────────────────

    async def _extract_decision(self, point: Dict, exchanges: List[Dict]) -> tuple:
        """Extract decision from OpenClaw's last response."""
        last_openclaw = ""
        for e in reversed(exchanges):
            if e["role"] == "openclaw":
                last_openclaw = e["content"]
                break

        response = await asyncio.to_thread(
            self.openai.chat.completions.create,
            model="gpt-4o",
            max_tokens=200,
            messages=[
                {"role": "system", "content": (
                    "Extrais la decision finale d'OpenClaw. "
                    "Reponds UNIQUEMENT en JSON:\n"
                    '{"decision": "ACCORD|DESACCORD|COMPROMIS", "reason": "1 phrase", "action": "action concrete a implementer"}'
                )},
                {"role": "user", "content": f"Point: {point['title']}\nReponse: {last_openclaw[:2000]}"},
            ],
        )

        text = response.choices[0].message.content or ""
        try:
            j_start = text.find("{")
            j_end = text.rfind("}") + 1
            if j_start >= 0 and j_end > j_start:
                parsed = json.loads(text[j_start:j_end])
                decision = parsed.get("decision", DESACCORD)
                reason = parsed.get("reason", "")
                action = parsed.get("action", "")
                if action:
                    reason = f"{reason} | Action: {action}"
                if decision not in (ACCORD, DESACCORD, COMPROMIS):
                    decision = DESACCORD
                return decision, reason
        except (json.JSONDecodeError, KeyError):
            pass

        lower = last_openclaw.lower()
        if "accord" in lower and "desaccord" not in lower:
            return ACCORD, "OpenClaw a accepte."
        elif "compromis" in lower:
            return COMPROMIS, "Compromis trouve."
        else:
            return DESACCORD, "OpenClaw a refuse."

    # ─── Persistence ──────────────────────────────────────────

    def _save_progress(self, audit_id: str, discussions: List[Dict]):
        try:
            self.sb.table("openclaw_audits").update({
                "discussion": discussions,
                "status": "negotiating",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", audit_id).execute()
        except Exception as e:
            print(f"  Save progress error: {e}")
