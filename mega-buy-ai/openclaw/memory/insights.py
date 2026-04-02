"""Strategic insights extracted from conversations.

These insights are injected into the agent's system prompt
when analyzing alerts, so conversations directly improve decisions.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from openclaw.config import get_settings


class InsightsStore:
    """CRUD for agent_insights — learnings that improve decisions."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self._ok = True
        try:
            self.sb.table("agent_insights").select("id").limit(1).execute()
        except Exception:
            self._ok = False
            self._local_insights = []
            print("⚠️ agent_insights table not found — using local fallback")

    def _is_duplicate(self, insight: str, category: str) -> bool:
        """Check if a similar insight already exists (deduplication).
        Compares first 80 chars to detect near-duplicates."""
        if not self._ok:
            for ins in getattr(self, '_local_insights', []):
                if ins.get("active") and ins["insight"][:80] == insight[:80]:
                    return True
            return False

        try:
            # Check by prefix match (first 80 chars)
            prefix = insight[:80]
            result = self.sb.table("agent_insights") \
                .select("id") \
                .eq("active", True) \
                .eq("category", category) \
                .ilike("insight", f"{prefix}%") \
                .limit(1) \
                .execute()
            return bool(result.data)
        except Exception:
            return False

    def _is_noise(self, insight: str) -> bool:
        """Reject noisy insight types that degrade performance.
        These patterns were identified as harmful during insight audit."""
        import re
        text = insight

        # 1. Per-trade training: "sur XXXUSDT a produit +X%"
        if re.search(r'sur [A-Z]+USDT a produit|sur [A-Z]+USDT confirme', text):
            return True

        # 2. Pattern "identifie sur XXXUSDT" — too specific, not generalizable
        if "Pattern '" in text and 'identifie sur' in text:
            return True

        # 3. SL touche specifique: "XXXUSDT a touche SL"
        if re.search(r'[A-Z]+USDT a touche SL', text):
            return True

        # 4. Conditions specifiques: "Conditions X/5 sur XXXUSDT"
        if re.search(r'Conditions \d/5 sur [A-Z]+USDT', text):
            return True

        return False

    def add_insight(self, insight: str, category: str = "strategy",
                    conversation_id: str = None, priority: int = 5) -> Optional[str]:
        """Add a new insight learned from a conversation.
        Skips duplicates and noisy patterns automatically."""
        # Noise filter — reject patterns that degrade performance
        if self._is_noise(insight):
            print(f"  🚫 Insight noise rejected: {insight[:60]}...")
            return None

        # Deduplication check
        if self._is_duplicate(insight, category):
            print(f"  ⏭ Insight duplicate skipped: {insight[:60]}...")
            return None

        if self._ok:
            try:
                result = self.sb.table("agent_insights").insert({
                    "insight": insight,
                    "category": category,
                    "source_conversation_id": conversation_id,
                    "priority": priority,
                    "active": True,
                }).execute()
                return result.data[0]["id"] if result.data else None
            except Exception as e:
                print(f"⚠️ Insight save error: {e}")
        else:
            self._local_insights.append({
                "insight": insight, "category": category, "priority": priority, "active": True
            })
        return None

    def get_active_insights(self, limit: int = 50) -> List[Dict]:
        """Get all active insights, sorted by priority."""
        if self._ok:
            try:
                result = self.sb.table("agent_insights") \
                    .select("*") \
                    .eq("active", True) \
                    .order("priority", desc=True) \
                    .limit(limit) \
                    .execute()
                return result.data or []
            except Exception:
                pass
        return getattr(self, '_local_insights', [])[:limit]

    def deactivate_insight(self, insight_id: str):
        """Deactivate an insight (soft delete)."""
        if self._ok:
            try:
                self.sb.table("agent_insights") \
                    .update({"active": False}).eq("id", insight_id).execute()
            except Exception:
                pass

    def format_for_prompt(self) -> str:
        """Format all active insights as text to inject into Claude's system prompt."""
        insights = self.get_active_insights()
        if not insights:
            return ""

        lines = [
            "",
            "## Insights Appris (de nos conversations passees)",
            "Ces regles ont ete definies avec l'utilisateur. Applique-les dans tes analyses:",
            "",
        ]

        by_category = {}
        for ins in insights:
            cat = ins.get("category", "general")
            by_category.setdefault(cat, []).append(ins["insight"])

        for cat, items in by_category.items():
            lines.append(f"### {cat.upper()}")
            for item in items:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)
