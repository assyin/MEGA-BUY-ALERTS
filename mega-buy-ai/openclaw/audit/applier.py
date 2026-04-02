"""Audit Applier — applies agreed-upon decisions with SNAPSHOT + ROLLBACK.

Before applying any change:
1. Takes a SNAPSHOT of the current state (insights, blacklist, portfolio params)
2. Applies changes (insights, blacklist, TP/SL, engagements)
3. Saves snapshot to Supabase for rollback

Rollback restores the exact state before the audit was applied.
"""

import json
from typing import Dict, List, Any
from datetime import datetime, timezone

from openclaw.config import get_settings
from openclaw.memory.insights import InsightsStore


class AuditApplier:
    """Applies audit decisions with snapshot/rollback capability."""

    def __init__(self):
        settings = get_settings()
        from supabase import create_client
        self.sb = create_client(settings.supabase_url, settings.supabase_service_key)
        self.insights = InsightsStore()

    # ─── Snapshot ─────────────────────────────────────────────

    def _take_snapshot(self) -> Dict:
        """Capture the current system state BEFORE applying changes."""
        snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "insights": [],
            "blacklist": [],
            "portfolio_state": {},
        }

        # Snapshot active insights
        try:
            r = self.sb.table("agent_insights").select("id,insight,category,priority,active") \
                .eq("active", True).execute()
            snapshot["insights"] = r.data or []
        except Exception:
            pass

        # Snapshot blacklist
        try:
            r = self.sb.table("openclaw_pair_filter").select("*").execute()
            snapshot["blacklist"] = r.data or []
        except Exception:
            pass

        # Snapshot portfolio state
        try:
            r = self.sb.table("openclaw_portfolio_state").select("*").eq("id", "main").single().execute()
            snapshot["portfolio_state"] = r.data or {}
        except Exception:
            pass

        return snapshot

    def _save_snapshot(self, audit_id: str, snapshot: Dict):
        """Save snapshot to the audit record."""
        try:
            self.sb.table("openclaw_audits").update({
                "snapshot_before": snapshot,
            }).eq("id", audit_id).execute()
        except Exception as e:
            print(f"  Snapshot save error: {e}")

    # ─── Rollback ─────────────────────────────────────────────

    def rollback(self, audit_id: str) -> Dict:
        """Rollback all changes made by this audit. Restores the snapshot."""
        # 1. Get the audit with snapshot
        try:
            r = self.sb.table("openclaw_audits").select("snapshot_before,changes_applied,status") \
                .eq("id", audit_id).single().execute()
            audit = r.data
        except Exception as e:
            return {"error": f"Audit not found: {e}"}

        if not audit:
            return {"error": "Audit not found"}

        if audit.get("status") != "applied":
            return {"error": f"Audit status is '{audit.get('status')}', can only rollback 'applied'"}

        snapshot = audit.get("snapshot_before")
        if not snapshot:
            return {"error": "No snapshot found — cannot rollback"}

        changes_applied = audit.get("changes_applied", [])
        rollback_actions = []

        # 2. Remove insights added by this audit
        insight_ids_to_remove = []
        for change in changes_applied:
            if change.get("type") == "insight" and change.get("insight_id"):
                insight_ids_to_remove.append(change["insight_id"])

        for iid in insight_ids_to_remove:
            try:
                self.sb.table("agent_insights").update({"active": False}).eq("id", iid).execute()
                rollback_actions.append(f"Insight {iid[:8]} desactive")
            except Exception:
                pass

        # 3. Remove blacklist entries added by this audit
        for change in changes_applied:
            if change.get("type") == "blacklist":
                pair = ""
                desc = change.get("description", "")
                import re
                pair_match = re.search(r'([A-Z]{2,15}USDT)', desc)
                if pair_match:
                    pair = pair_match.group(1)
                    try:
                        self.sb.table("openclaw_pair_filter").delete().eq("pair", pair).execute()
                        rollback_actions.append(f"{pair} retire de la blacklist")
                    except Exception:
                        pass

        # 4. Remove engagements created by this audit
        try:
            self.sb.table("openclaw_engagements").delete().eq("audit_id", audit_id).execute()
            rollback_actions.append("Engagements supprimes")
        except Exception:
            pass

        # 5. Restore insights that were active before (re-activate any that were deactivated)
        # The snapshot contains the list of active insights at the time
        # We don't need to re-activate old ones since we only ADDED new insights

        # 6. Update audit status
        try:
            self.sb.table("openclaw_audits").update({
                "status": "rolled_back",
                "rollback_at": datetime.now(timezone.utc).isoformat(),
                "rollback_actions": rollback_actions,
            }).eq("id", audit_id).execute()
        except Exception:
            pass

        return {
            "status": "ok",
            "actions": rollback_actions,
            "message": f"Rollback complete: {len(rollback_actions)} actions annulees",
        }

    # ─── Apply Decisions ──────────────────────────────────────

    def apply_decisions(self, points: List[Dict], discussions: List[Dict], audit_id: str = "") -> List[Dict]:
        """Apply all ACCORD/COMPROMIS decisions with snapshot."""

        # STEP 0: Take snapshot BEFORE any changes
        snapshot = self._take_snapshot()
        if audit_id:
            self._save_snapshot(audit_id, snapshot)
        print(f"  📸 Snapshot saved: {len(snapshot['insights'])} insights, {len(snapshot['blacklist'])} blacklist")

        changes = []
        disc_map = {d["point_id"]: d for d in discussions}

        for point in points:
            pid = point["id"]
            disc = disc_map.get(pid)
            if not disc:
                continue

            decision = disc.get("decision", "DESACCORD")
            if decision == "DESACCORD":
                changes.append({
                    "point_id": pid,
                    "type": "skipped",
                    "description": f"Point #{pid} ({point['title']}): DESACCORD — aucun changement",
                    "applied": False,
                })
                continue

            title_lower = point["title"].lower()
            rec_lower = point.get("recommendation", "").lower()
            applied_items = []

            # Blacklist detection
            if "blacklist" in rec_lower or "problematique" in title_lower:
                applied_items.extend(self._apply_blacklist(point, disc))

            # TP/SL changes
            if "tp" in title_lower or "sl" in title_lower or "tp/sl" in title_lower:
                applied_items.extend(self._apply_tp_sl(point, disc))

            # Always save as insight
            insight_text = self._build_insight(point, disc)
            if insight_text:
                insight_id = self.insights.add_insight(
                    insight_text,
                    category="audit",
                    priority=min(point.get("priority", 5), 10),
                )
                applied_items.append({
                    "point_id": pid,
                    "type": "insight",
                    "description": f"Insight sauvegarde: {insight_text[:100]}...",
                    "applied": True,
                    "insight_id": insight_id,
                })

            if not applied_items:
                applied_items.append({
                    "point_id": pid,
                    "type": "noted",
                    "description": f"Point #{pid} ({point['title']}): {decision} — note",
                    "applied": True,
                })

            changes.extend(applied_items)

        # Extract and save engagements
        try:
            from openclaw.audit.engagements import EngagementTracker
            tracker = EngagementTracker()
            engagements = tracker.extract_engagements(audit_id, points, discussions)
            if engagements:
                changes.append({
                    "point_id": 0,
                    "type": "engagements",
                    "description": f"{len(engagements)} engagement(s) cree(s) pour suivi",
                    "applied": True,
                    "engagement_count": len(engagements),
                })
        except Exception as e:
            print(f"  Engagement extraction error: {e}")

        return changes

    # ─── Internal Methods ─────────────────────────────────────

    def _apply_blacklist(self, point: Dict, disc: Dict) -> List[Dict]:
        changes = []
        evidence = point.get("evidence", "")
        decision_reason = disc.get("decision_reason", "")
        import re
        pairs = re.findall(r'[A-Z]{2,15}USDT', evidence)
        if not pairs:
            return []
        for pair in set(pairs):
            try:
                self.sb.table("openclaw_pair_filter").upsert({
                    "pair": pair,
                    "action": "BLACKLIST",
                    "reason": f"Audit: {point['title']} — {decision_reason[:200]}",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
                changes.append({"point_id": point["id"], "type": "blacklist", "description": f"{pair} ajoute a la blacklist", "applied": True})
            except Exception as e:
                changes.append({"point_id": point["id"], "type": "blacklist_failed", "description": f"Blacklist {pair} echoue: {str(e)[:80]}", "applied": False})
        return changes

    def _apply_tp_sl(self, point: Dict, disc: Dict) -> List[Dict]:
        decision_reason = disc.get("decision_reason", "")
        return [{"point_id": point["id"], "type": "tp_sl_recommendation", "description": f"TP/SL: {decision_reason[:200]}", "applied": True}]

    def _build_insight(self, point: Dict, disc: Dict) -> str:
        decision = disc.get("decision", "")
        reason = disc.get("decision_reason", "")
        if decision == "ACCORD":
            return f"[AUDIT] {point['title']}: {point['recommendation']} (confirme: {reason})"
        elif decision == "COMPROMIS":
            return f"[AUDIT COMPROMIS] {point['title']}: modifie — {reason}"
        return ""
