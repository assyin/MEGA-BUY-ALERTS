"""
MEGA BUY AI - Supabase Client
Client pour interagir avec la base de données Supabase
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

try:
    from supabase import create_client, Client
    SUPABASE_OK = True
except ImportError:
    SUPABASE_OK = False


class SupabaseClient:
    """Client Supabase pour MEGA BUY AI"""

    def __init__(self, url: str = None, key: str = None):
        """
        Initialise le client Supabase

        Args:
            url: URL Supabase (ou SUPABASE_URL env var)
            key: Service key (ou SUPABASE_SERVICE_KEY env var)
        """
        if not SUPABASE_OK:
            raise ImportError("supabase package not installed. Run: pip install supabase")

        self.url = url or os.getenv("SUPABASE_URL", "")
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY", "")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        self.client: Client = create_client(self.url, self.key)

    # =========================================================================
    # ALERTS
    # =========================================================================

    def insert_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Insère une nouvelle alerte"""
        result = self.client.table("alerts").insert(alert).execute()
        return result.data[0] if result.data else None

    def upsert_alert(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """Insère ou met à jour une alerte"""
        result = self.client.table("alerts").upsert(
            alert,
            on_conflict="pair,bougie_4h,timeframes"
        ).execute()
        return result.data[0] if result.data else None

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une alerte par ID"""
        result = self.client.table("alerts").select("*").eq("id", alert_id).execute()
        return result.data[0] if result.data else None

    def get_alerts(
        self,
        limit: int = 100,
        offset: int = 0,
        pair: str = None,
        status: str = None,
        min_score: int = None,
        start_date: str = None,
        end_date: str = None,
        source: str = None
    ) -> List[Dict[str, Any]]:
        """Récupère des alertes avec filtres"""

        query = self.client.table("alerts").select("*")

        if pair:
            query = query.eq("pair", pair)
        if status:
            query = query.eq("status", status)
        if min_score:
            query = query.gte("scanner_score", min_score)
        if start_date:
            query = query.gte("alert_timestamp", start_date)
        if end_date:
            query = query.lte("alert_timestamp", end_date)
        if source:
            query = query.eq("source", source)

        query = query.order("alert_timestamp", desc=True).range(offset, offset + limit - 1)

        result = query.execute()
        return result.data

    def get_alerts_complete(
        self,
        limit: int = 100,
        offset: int = 0,
        **filters
    ) -> List[Dict[str, Any]]:
        """Récupère les alertes avec décisions et rapports (vue complète)"""

        query = self.client.table("v_alerts_complete").select("*")

        for key, value in filters.items():
            if value is not None:
                query = query.eq(key, value)

        query = query.order("alert_timestamp", desc=True).range(offset, offset + limit - 1)

        result = query.execute()
        return result.data

    def update_alert_status(self, alert_id: str, status: str, validated: bool = None) -> bool:
        """Met à jour le statut d'une alerte"""
        data = {"status": status}
        if validated is not None:
            data["validated"] = validated

        result = self.client.table("alerts").update(data).eq("id", alert_id).execute()
        return len(result.data) > 0

    def update_alert_tracking(
        self,
        alert_id: str,
        max_profit_pct: float = None,
        max_profit_hours: float = None,
        max_drawdown_pct: float = None,
        max_drawdown_hours: float = None
    ) -> bool:
        """Met à jour les données de tracking d'une alerte"""
        data = {}
        if max_profit_pct is not None:
            data["max_profit_pct"] = max_profit_pct
        if max_profit_hours is not None:
            data["max_profit_hours"] = max_profit_hours
        if max_drawdown_pct is not None:
            data["max_drawdown_pct"] = max_drawdown_pct
        if max_drawdown_hours is not None:
            data["max_drawdown_hours"] = max_drawdown_hours

        if not data:
            return False

        result = self.client.table("alerts").update(data).eq("id", alert_id).execute()
        return len(result.data) > 0

    # =========================================================================
    # FEATURES
    # =========================================================================

    def insert_features(self, alert_id: str, feature_vector: Dict, version: str = "1.0") -> Dict:
        """Insère un vecteur de features pour une alerte"""
        data = {
            "alert_id": alert_id,
            "feature_vector": feature_vector,
            "feature_version": version,
            "num_features": len(feature_vector)
        }
        result = self.client.table("features").upsert(
            data,
            on_conflict="alert_id,feature_version"
        ).execute()
        return result.data[0] if result.data else None

    def get_features(self, alert_id: str, version: str = None) -> Optional[Dict]:
        """Récupère les features d'une alerte"""
        query = self.client.table("features").select("*").eq("alert_id", alert_id)
        if version:
            query = query.eq("feature_version", version)
        result = query.execute()
        return result.data[0] if result.data else None

    # =========================================================================
    # DECISIONS
    # =========================================================================

    def insert_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Insère une décision ML"""
        result = self.client.table("decisions").upsert(
            decision,
            on_conflict="alert_id"
        ).execute()
        return result.data[0] if result.data else None

    def get_decision(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Récupère la décision pour une alerte"""
        result = self.client.table("decisions").select("*").eq("alert_id", alert_id).execute()
        return result.data[0] if result.data else None

    def get_decisions_by_type(
        self,
        decision: str,
        limit: int = 100,
        min_confidence: float = None
    ) -> List[Dict[str, Any]]:
        """Récupère les décisions par type (TRADE, WATCH, SKIP)"""
        query = self.client.table("decisions").select("*").eq("decision", decision)

        if min_confidence:
            query = query.gte("confidence", min_confidence)

        query = query.order("created_at", desc=True).limit(limit)

        result = query.execute()
        return result.data

    # =========================================================================
    # LLM REPORTS
    # =========================================================================

    def insert_llm_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Insère un rapport LLM"""
        result = self.client.table("llm_reports").upsert(
            report,
            on_conflict="alert_id"
        ).execute()
        return result.data[0] if result.data else None

    def get_llm_report(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Récupère le rapport LLM pour une alerte"""
        result = self.client.table("llm_reports").select("*").eq("alert_id", alert_id).execute()
        return result.data[0] if result.data else None

    # =========================================================================
    # OUTCOMES
    # =========================================================================

    def insert_outcome(self, outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Insère un outcome (résultat réel)"""
        result = self.client.table("outcomes").upsert(
            outcome,
            on_conflict="alert_id"
        ).execute()
        return result.data[0] if result.data else None

    def get_outcome(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Récupère l'outcome pour une alerte"""
        result = self.client.table("outcomes").select("*").eq("alert_id", alert_id).execute()
        return result.data[0] if result.data else None

    def get_outcomes_stats(self) -> Dict[str, Any]:
        """Calcule les statistiques des outcomes"""

        # Total par outcome
        wins = self.client.table("outcomes").select("id", count="exact").eq("outcome", "WIN").execute()
        losses = self.client.table("outcomes").select("id", count="exact").eq("outcome", "LOSE").execute()
        neutral = self.client.table("outcomes").select("id", count="exact").eq("outcome", "NEUTRAL").execute()

        total = (wins.count or 0) + (losses.count or 0) + (neutral.count or 0)

        return {
            "total": total,
            "wins": wins.count or 0,
            "losses": losses.count or 0,
            "neutral": neutral.count or 0,
            "win_rate": (wins.count or 0) / total * 100 if total > 0 else 0
        }

    # =========================================================================
    # AUDIT LOGS
    # =========================================================================

    def log_action(
        self,
        action: str,
        entity_type: str = None,
        entity_id: str = None,
        details: Dict = None,
        source: str = "system"
    ) -> None:
        """Enregistre une action dans les logs d'audit"""
        self.client.table("audit_logs").insert({
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "source": source
        }).execute()

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_alerts_count(self, **filters) -> int:
        """Compte le nombre d'alertes avec filtres"""
        query = self.client.table("alerts").select("id", count="exact")

        for key, value in filters.items():
            if value is not None:
                query = query.eq(key, value)

        result = query.execute()
        return result.count or 0

    def get_alerts_by_pair_stats(self, limit: int = 20) -> List[Dict]:
        """Statistiques par paire"""
        # Note: Pour des stats complexes, utiliser une fonction RPC Supabase
        result = self.client.rpc("get_pair_stats", {"limit_count": limit}).execute()
        return result.data if result.data else []

    def get_recent_decisions_accuracy(self, days: int = 7) -> Dict[str, Any]:
        """Précision des décisions récentes"""
        # Requête via RPC pour performance
        result = self.client.rpc("get_decisions_accuracy", {"days_back": days}).execute()
        return result.data[0] if result.data else {}


# Singleton instance
_instance: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """Retourne l'instance singleton du client Supabase"""
    global _instance
    if _instance is None:
        _instance = SupabaseClient()
    return _instance
