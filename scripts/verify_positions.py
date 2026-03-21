#!/usr/bin/env python3
"""Verify if positions meet portfolio conditions"""

import json
import requests

# Portfolio conditions
PORTFOLIO_CONDITIONS = {
    "max_wr": {
        "name": "Max Win Rate",
        "type": "empirical_filter",
        "conditions": {
            "pp": True,
            "ec": True,
            "di_minus_min": 22.0,
            "di_plus_max": 25.0,
            "adx_min": 35.0,
            "vol_min": 100.0
        }
    },
    "balanced_filter": {
        "name": "Équilibré",
        "type": "empirical_filter",
        "conditions": {
            "pp": True,
            "ec": True,
            "di_minus_min": 22.0,
            "di_plus_max": 20.0,
            "adx_min": 21.0,
            "vol_min": 100.0
        }
    },
    "big_winners": {
        "name": "Gros Gagnants",
        "type": "empirical_filter",
        "conditions": {
            "pp": True,
            "ec": True,
            "di_minus_min": 22.0,
            "di_plus_max": 25.0,
            "adx_min": 21.0,
            "vol_min": 100.0
        }
    },
    "aggressive": {
        "name": "Aggressive",
        "type": "p_success_threshold",
        "threshold": 0.3
    },
    "balanced_ml": {
        "name": "Balanced ML",
        "type": "p_success_threshold",
        "threshold": 0.5
    },
    "conservative": {
        "name": "Conservative",
        "type": "p_success_threshold",
        "threshold": 0.7
    }
}

def get_alert_details(alert_id):
    """Get alert details from dashboard API"""
    try:
        resp = requests.get(f"http://localhost:9000/api/alerts/{alert_id}", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def check_empirical_conditions(alert, conditions):
    """Check if alert meets empirical filter conditions"""
    issues = []

    # PP (Pivot Point SuperTrend Buy)
    if conditions.get("pp"):
        pp_value = alert.get("pp") or alert.get("pp_buy")
        if not pp_value:
            issues.append("PP=False (required True)")

    # EC (Entry Confirmation)
    if conditions.get("ec"):
        ec_value = alert.get("ec") or alert.get("entry_confirmation")
        if not ec_value:
            issues.append("EC=False (required True)")

    # DMI conditions
    di_minus = alert.get("di_minus") or alert.get("dmi_minus") or 0
    di_plus = alert.get("di_plus") or alert.get("dmi_plus") or 0
    adx = alert.get("adx") or 0

    if conditions.get("di_minus_min") and di_minus < conditions["di_minus_min"]:
        issues.append(f"DI-={di_minus:.1f} < {conditions['di_minus_min']}")

    if conditions.get("di_plus_max") and di_plus > conditions["di_plus_max"]:
        issues.append(f"DI+={di_plus:.1f} > {conditions['di_plus_max']}")

    if conditions.get("adx_min") and adx < conditions["adx_min"]:
        issues.append(f"ADX={adx:.1f} < {conditions['adx_min']}")

    # Volume
    vol = alert.get("volume") or alert.get("vol_ratio") or 0
    if conditions.get("vol_min") and vol < conditions["vol_min"]:
        issues.append(f"Vol={vol:.1f} < {conditions['vol_min']}")

    return issues

def check_p_success_threshold(alert, threshold):
    """Check if alert meets p_success threshold"""
    p_success = alert.get("p_success") or 0
    if p_success < threshold:
        return [f"P(Success)={p_success:.2f} < {threshold}"]
    return []

def main():
    # Get positions
    resp = requests.get("http://localhost:8001/api/positions?status=open")
    positions = resp.json()

    print("=" * 70)
    print("    VÉRIFICATION DES CONDITIONS PAR POSITION")
    print("=" * 70)
    print()

    # Group by portfolio
    by_portfolio = {}
    for p in positions:
        pid = p.get("portfolio_id")
        if pid not in by_portfolio:
            by_portfolio[pid] = []
        by_portfolio[pid].append(p)

    # Cache alerts
    alert_cache = {}

    total_ok = 0
    total_issues = 0

    for pid, pos_list in sorted(by_portfolio.items()):
        if pid not in PORTFOLIO_CONDITIONS:
            print(f"[?] Portfolio inconnu: {pid}")
            continue

        pconfig = PORTFOLIO_CONDITIONS[pid]
        print(f"{'─' * 70}")
        print(f"📁 {pconfig['name']} ({pid}) - {len(pos_list)} positions")
        print(f"   Type: {pconfig['type']}")
        if pconfig['type'] == 'empirical_filter':
            conds = pconfig.get('conditions', {})
            print(f"   Conditions: PP={conds.get('pp')}, EC={conds.get('ec')}, DI->={conds.get('di_minus_min')}, DI+<={conds.get('di_plus_max')}, ADX>={conds.get('adx_min')}")
        else:
            print(f"   Threshold: P(Success) >= {pconfig.get('threshold')}")
        print()

        for p in pos_list:
            pair = p.get("pair")
            alert_id = p.get("alert_id")
            pnl = p.get("current_pnl_pct", 0)

            # Get alert details
            if alert_id not in alert_cache:
                alert_cache[alert_id] = get_alert_details(alert_id)

            alert = alert_cache.get(alert_id)

            if not alert:
                print(f"   ⚠️  {pair}: Impossible de récupérer l'alerte {alert_id[:8]}...")
                total_issues += 1
                continue

            # Check conditions
            if pconfig['type'] == 'empirical_filter':
                issues = check_empirical_conditions(alert, pconfig.get('conditions', {}))
            else:
                issues = check_p_success_threshold(alert, pconfig.get('threshold', 0.5))

            if issues:
                total_issues += 1
                print(f"   ❌ {pair} (PnL: {pnl:+.2f}%)")
                for issue in issues:
                    print(f"      └─ {issue}")
            else:
                total_ok += 1
                print(f"   ✅ {pair} (PnL: {pnl:+.2f}%)")

        print()

    print("=" * 70)
    print(f"RÉSUMÉ: {total_ok} OK | {total_issues} avec problèmes")
    print("=" * 70)

if __name__ == "__main__":
    main()
