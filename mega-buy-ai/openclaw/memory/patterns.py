"""Pattern similarity search for agent memory."""

import math
from typing import Dict, List

from openclaw.memory.store import MemoryStore


def compute_fingerprint(alert: dict) -> Dict:
    """Extract a numerical fingerprint from an alert for similarity comparison."""
    return {
        "scanner_score": alert.get("scanner_score", 0),
        "nb_timeframes": len(alert.get("timeframes", [])),
        "has_4h": "4h" in alert.get("timeframes", []),
        "has_1h": "1h" in alert.get("timeframes", []),
        "di_plus_4h": alert.get("di_plus_4h", 0) or 0,
        "di_minus_4h": alert.get("di_minus_4h", 0) or 0,
        "adx_4h": alert.get("adx_4h", 0) or 0,
        "pp": 1 if alert.get("pp") else 0,
        "ec": 1 if alert.get("ec") else 0,
        "price": alert.get("price", 0),
    }


def cosine_similarity(a: Dict, b: Dict) -> float:
    """Compute cosine similarity between two fingerprints."""
    keys = set(a.keys()) & set(b.keys()) - {"price", "has_4h", "has_1h"}
    if not keys:
        return 0

    dot = sum(float(a.get(k, 0)) * float(b.get(k, 0)) for k in keys)
    mag_a = math.sqrt(sum(float(a.get(k, 0)) ** 2 for k in keys))
    mag_b = math.sqrt(sum(float(b.get(k, 0)) ** 2 for k in keys))

    if mag_a == 0 or mag_b == 0:
        return 0

    return dot / (mag_a * mag_b)


def find_similar_patterns(memory: MemoryStore, alert: dict, top_k: int = 5) -> List[Dict]:
    """Find the most similar past patterns in memory."""
    fingerprint = compute_fingerprint(alert)
    patterns = memory.get_recent(200)

    if not patterns:
        return []

    scored = []
    for p in patterns:
        if p.get("outcome") == "PENDING":
            continue
        stored_fp = p.get("features_fingerprint", {})
        sim = cosine_similarity(fingerprint, stored_fp)
        scored.append({
            "pair": p["pair"],
            "decision": p["agent_decision"],
            "outcome": p.get("outcome"),
            "pnl_pct": p.get("pnl_pct"),
            "confidence": p.get("agent_confidence"),
            "similarity": round(sim, 3),
        })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
