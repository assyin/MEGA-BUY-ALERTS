"""Supabase-backed memory store for OpenClaw agent."""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from openclaw.config import get_settings


class MemoryStore:
    """CRUD operations on agent_memory and agent_state tables."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self._ensure_tables()

    def _ensure_tables(self):
        """Check tables exist. If not, use local JSON fallback."""
        self._memory_ok = False
        self._state_ok = False
        self._local_patterns = []
        try:
            self.sb.table("agent_memory").select("id").limit(1).execute()
            self._memory_ok = True
        except Exception:
            print("⚠️ agent_memory table not found — using local fallback")
            print("  Create it in Supabase SQL Editor with the schema from the plan")
        try:
            self.sb.table("agent_state").select("id").limit(1).execute()
            self._state_ok = True
        except Exception:
            print("⚠️ agent_state table not found — using local fallback")
            self._local_state = {
                "daily_losses": 0, "weekly_losses": 0,
                "daily_wins": 0, "weekly_wins": 0,
                "circuit_breaker_active": False,
                "total_alerts_processed": 0,
            }
            self._local_patterns = []

    # ===== MEMORY =====

    def save_pattern(self, alert_id: str, pair: str, features: Dict,
                     decision: str, confidence: float, reasoning: str,
                     analysis_text: str = None) -> Optional[str]:
        """Save a new pattern to memory after agent makes a decision."""
        data = {
            "alert_id": alert_id,
            "pair": pair,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "features_fingerprint": features,
            "agent_decision": decision,
            "agent_confidence": confidence,
            "agent_reasoning": reasoning,
            "outcome": "PENDING",
        }
        # analysis_text column may not exist yet — add gracefully
        if analysis_text:
            data["analysis_text"] = analysis_text
        # scanner_score for quick filtering
        if features.get("scanner_score"):
            data["scanner_score"] = features["scanner_score"]
        if self._memory_ok:
            try:
                result = self.sb.table("agent_memory").insert(data).execute()
                return result.data[0]["id"] if result.data else None
            except Exception as e:
                print(f"⚠️ Memory save error: {e}")
        else:
            self._local_patterns.append(data)
        return None

    def update_outcome(self, alert_id: str, outcome: str, pnl_pct: float):
        """Update a pattern with trade outcome."""
        try:
            self.sb.table("agent_memory") \
                .update({
                    "outcome": outcome,
                    "pnl_pct": pnl_pct,
                    "outcome_at": datetime.now(timezone.utc).isoformat(),
                }) \
                .eq("alert_id", alert_id) \
                .execute()
        except Exception as e:
            print(f"⚠️ Memory update error: {e}")

    def get_recent(self, limit: int = 50) -> List[Dict]:
        """Get recent patterns."""
        if self._memory_ok:
            try:
                result = self.sb.table("agent_memory") \
                    .select("*") \
                    .order("created_at", desc=True) \
                    .limit(limit) \
                    .execute()
                return result.data or []
            except Exception:
                pass
        return getattr(self, '_local_patterns', [])[-limit:]

    def get_stats(self) -> Dict:
        """Get memory statistics."""
        patterns = self.get_recent(500)
        completed = [p for p in patterns if p.get("outcome") and p["outcome"] != "PENDING"]
        wins = [p for p in completed if p["outcome"] == "WIN"]
        losses = [p for p in completed if p["outcome"] == "LOSE"]
        return {
            "total_patterns": len(patterns),
            "completed": len(completed),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(completed) * 100, 1) if completed else 0,
            "pending": len(patterns) - len(completed),
        }

    # ===== AGENT STATE =====

    def get_state(self) -> Dict:
        """Get circuit breaker state."""
        if self._state_ok:
            try:
                result = self.sb.table("agent_state").select("*").eq("id", "singleton").single().execute()
                return result.data if result.data else self._init_state()
            except Exception:
                pass
        return getattr(self, '_local_state', self._init_state())

    def _init_state(self) -> Dict:
        """Initialize agent state."""
        state = {
            "id": "singleton",
            "daily_losses": 0,
            "weekly_losses": 0,
            "daily_wins": 0,
            "weekly_wins": 0,
            "circuit_breaker_active": False,
            "total_alerts_processed": 0,
        }
        try:
            self.sb.table("agent_state").upsert(state).execute()
        except Exception:
            pass
        return state

    def update_state(self, updates: Dict):
        """Update agent state."""
        if self._state_ok:
            try:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                self.sb.table("agent_state").update(updates).eq("id", "singleton").execute()
                return
            except Exception as e:
                print(f"⚠️ State update error: {e}")
        # Local fallback
        local = getattr(self, '_local_state', {})
        local.update(updates)
        self._local_state = local

    def increment_processed(self):
        """Increment alerts processed counter."""
        state = self.get_state()
        self.update_state({"total_alerts_processed": state.get("total_alerts_processed", 0) + 1})
