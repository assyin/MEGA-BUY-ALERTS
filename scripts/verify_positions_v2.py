#!/usr/bin/env python3
"""Verify if positions meet portfolio conditions - V2"""

import sqlite3

# Portfolio conditions
PORTFOLIO_CONDITIONS = {
    "max_wr": {
        "name": "Max Win Rate",
        "type": "empirical_filter",
        "pp": True, "ec": True,
        "di_minus_min": 22.0, "di_plus_max": 25.0, "adx_min": 35.0, "vol_min": 100.0
    },
    "balanced_filter": {
        "name": "Equilibre",
        "type": "empirical_filter",
        "pp": True, "ec": True,
        "di_minus_min": 22.0, "di_plus_max": 20.0, "adx_min": 21.0, "vol_min": 100.0
    },
    "big_winners": {
        "name": "Gros Gagnants",
        "type": "empirical_filter",
        "pp": True, "ec": True,
        "di_minus_min": 22.0, "di_plus_max": 25.0, "adx_min": 21.0, "vol_min": 100.0
    },
    "aggressive": {"name": "Aggressive", "type": "p_success_threshold", "threshold": 0.3},
    "balanced_ml": {"name": "Balanced ML", "type": "p_success_threshold", "threshold": 0.5},
    "conservative": {"name": "Conservative", "type": "p_success_threshold", "threshold": 0.7}
}

def main():
    # Connect to simulation DB
    sim_db = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/data/simulation.db"
    conn = sqlite3.connect(sim_db)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get positions with alert data
    cursor.execute("""
        SELECT
            p.id as pos_id,
            p.portfolio_id,
            p.pair,
            p.entry_price,
            p.current_price,
            ((p.current_price - p.entry_price) / p.entry_price * 100) as current_pnl_pct,
            p.alert_id,
            a.p_success,
            a.pp,
            a.ec,
            a.di_plus_4h,
            a.di_minus_4h,
            a.adx_4h,
            a.vol_pct_max,
            a.filter_max_wr,
            a.filter_balanced,
            a.filter_big_winners
        FROM positions p
        LEFT JOIN alerts a ON p.alert_id = a.id
        WHERE p.status = 'OPEN'
        ORDER BY p.portfolio_id, p.pair
    """)

    positions = cursor.fetchall()

    print("=" * 70)
    print("    VERIFICATION DES CONDITIONS - POSITIONS OUVERTES")
    print("=" * 70)
    print()

    # Group by portfolio
    by_portfolio = {}
    for p in positions:
        pid = p["portfolio_id"]
        if pid not in by_portfolio:
            by_portfolio[pid] = []
        by_portfolio[pid].append(dict(p))

    total_ok = 0
    total_issues = 0

    for pid in sorted(by_portfolio.keys()):
        if pid not in PORTFOLIO_CONDITIONS:
            continue

        pconfig = PORTFOLIO_CONDITIONS[pid]
        pos_list = by_portfolio[pid]

        print("-" * 70)
        print(f"[{pconfig['name']}] ({pid}) - {len(pos_list)} positions")

        if pconfig["type"] == "empirical_filter":
            print(f"   Conditions: PP={pconfig['pp']}, EC={pconfig['ec']}")
            print(f"   DI- >= {pconfig['di_minus_min']}, DI+ <= {pconfig['di_plus_max']}, ADX >= {pconfig['adx_min']}")
        else:
            print(f"   Condition: P(Success) >= {pconfig['threshold']}")
        print()

        for p in pos_list:
            pair = p["pair"]
            pnl = p["current_pnl_pct"] or 0
            issues = []

            if p["p_success"] is None:
                print(f"   [WARN] {pair}: Pas de donnees d alerte")
                total_issues += 1
                continue

            if pconfig["type"] == "empirical_filter":
                # Check PP
                if pconfig["pp"] and not p["pp"]:
                    issues.append("PP=False (requis True)")

                # Check EC
                if pconfig["ec"] and not p["ec"]:
                    issues.append("EC=False (requis True)")

                # Check DI-
                di_minus = p["di_minus_4h"] or 0
                if di_minus < pconfig["di_minus_min"]:
                    issues.append(f"DI-={di_minus:.1f} < {pconfig['di_minus_min']}")

                # Check DI+
                di_plus = p["di_plus_4h"] or 0
                if di_plus > pconfig["di_plus_max"]:
                    issues.append(f"DI+={di_plus:.1f} > {pconfig['di_plus_max']}")

                # Check ADX
                adx = p["adx_4h"] or 0
                if adx < pconfig["adx_min"]:
                    issues.append(f"ADX={adx:.1f} < {pconfig['adx_min']}")

                # Check Volume
                vol = p["vol_pct_max"] or 0
                if vol < pconfig["vol_min"]:
                    issues.append(f"Vol={vol:.1f}% < {pconfig['vol_min']}%")

            else:  # p_success_threshold
                p_success = p["p_success"] or 0
                if p_success < pconfig["threshold"]:
                    issues.append(f"P(Success)={p_success:.2f} < {pconfig['threshold']}")

            # Print result
            if issues:
                total_issues += 1
                print(f"   [FAIL] {pair} (PnL: {pnl:+.2f}%)")
                for issue in issues:
                    print(f"          -> {issue}")
            else:
                total_ok += 1
                # Show key metrics
                if pconfig["type"] == "empirical_filter":
                    print(f"   [OK] {pair} (PnL: {pnl:+.2f}%) PP={p['pp']} EC={p['ec']} DI+={p['di_plus_4h']:.1f} DI-={p['di_minus_4h']:.1f} ADX={p['adx_4h']:.1f}")
                else:
                    print(f"   [OK] {pair} (PnL: {pnl:+.2f}%) P(Success)={p['p_success']:.2f}")
        print()

    print("=" * 70)
    print(f"RESUME: {total_ok} OK | {total_issues} avec problemes")
    print("=" * 70)

    conn.close()

if __name__ == "__main__":
    main()
