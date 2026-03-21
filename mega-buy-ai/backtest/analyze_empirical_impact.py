#!/usr/bin/env python3
"""
Analyse d'Impact des Filtres Empiriques sur le Backtest
========================================================

Ce script analyse l'impact des filtres empiriques validés sur les différentes
versions du backtest (V1-V6) AVANT implémentation.

Filtres Empiriques à tester:
- DI- >= 22 (vendeurs présents)
- DI+ <= 25 (pas de surachat) ou <= 20 (strict)
- ADX >= 21 (modéré) ou >= 35 (strict)
- Vol >= 100%
- PP = True
- EC = True

Presets:
- Max Win Rate: DI->=22, DI+<=25, ADX>=35, Vol>=100%, PP+EC
- Balanced: DI->=22, DI+<=20, ADX>=21, Vol>=100%, PP+EC
- Big Winners: DI->=22, DI+<=25, ADX>=21, Vol>=100%, PP+EC
"""

import sqlite3
import json
from datetime import datetime
from collections import defaultdict

# Database path
DB_PATH = "/home/assyin/MEGA-BUY-BOT/mega-buy-ai/backtest/data/backtest.db"

# Empirical Filter Presets
PRESETS = {
    "max_wr": {
        "name": "Max Win Rate",
        "min_di_minus": 22,
        "max_di_plus": 25,
        "min_adx": 35,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
    "balanced": {
        "name": "Balanced",
        "min_di_minus": 22,
        "max_di_plus": 20,
        "min_adx": 21,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
    "big_winners": {
        "name": "Big Winners",
        "min_di_minus": 22,
        "max_di_plus": 25,
        "min_adx": 21,
        "min_vol": 100,
        "require_pp": True,
        "require_ec": True,
    },
    "no_pp_ec": {
        "name": "No PP/EC Filter",
        "min_di_minus": 22,
        "max_di_plus": 25,
        "min_adx": 21,
        "min_vol": 100,
        "require_pp": False,
        "require_ec": False,
    },
}

def get_connection():
    return sqlite3.connect(DB_PATH)

def extract_dmi_values(row):
    """Extract DI+, DI-, ADX values from alert data."""
    di_plus = None
    di_minus = None
    adx = None
    vol_pct = 0

    # Try mega_buy_details first (most accurate for signal time)
    mega_buy_details = row.get('mega_buy_details')
    if mega_buy_details:
        try:
            details = json.loads(mega_buy_details) if isinstance(mega_buy_details, str) else mega_buy_details

            # DMI from 4H
            dmi_data = details.get('dmi', {})
            if '4h' in dmi_data:
                dmi_4h = dmi_data['4h']
                di_plus = dmi_4h.get('di_plus')
                di_minus = dmi_4h.get('di_minus')
                adx = dmi_4h.get('adx')

            # Volume (max across TFs)
            vol_data = details.get('volume', {})
            for tf in ['4h', '1h', '30m', '15m']:
                if tf in vol_data:
                    tf_vol = vol_data[tf].get('vol_pct', 0) or 0
                    vol_pct = max(vol_pct, tf_vol)
        except Exception as e:
            pass

    # Fallback to dedicated columns
    if di_plus is None:
        di_plus = row.get('adx_plus_di_4h') or row.get('di_plus_4h_at_entry')
    if di_minus is None:
        di_minus = row.get('adx_minus_di_4h') or row.get('di_minus_4h_at_entry')
    if adx is None:
        adx = row.get('adx_value_4h') or row.get('adx_4h_at_entry')

    return di_plus or 0, di_minus or 0, adx or 0, vol_pct

def extract_pp_ec(row):
    """Extract PP and EC values from conditions."""
    pp = False
    ec = False

    conditions = row.get('conditions')
    if conditions:
        try:
            conds = json.loads(conditions) if isinstance(conditions, str) else conditions

            # conditions can be a list of strings or a dict
            if isinstance(conds, list):
                pp = 'PP_buy' in conds
                ec = 'Entry_Confirm' in conds
            elif isinstance(conds, dict):
                pp = conds.get('PP_buy', False) or conds.get('pp', False)
                ec = conds.get('Entry_Confirm', False) or conds.get('ec', False)
        except Exception as e:
            pass

    return pp, ec

def check_empirical_filters(row, preset_config):
    """
    Check if a trade passes the empirical filters.

    Returns: (passed, rejection_reason, filter_values)
    """
    di_plus, di_minus, adx, vol_pct = extract_dmi_values(row)
    pp, ec = extract_pp_ec(row)

    filter_values = {
        'di_plus': di_plus,
        'di_minus': di_minus,
        'adx': adx,
        'vol_pct': vol_pct,
        'pp': pp,
        'ec': ec,
    }

    # Check filters in order
    if preset_config['require_pp'] and not pp:
        return False, 'NO_PP', filter_values

    if preset_config['require_ec'] and not ec:
        return False, 'NO_EC', filter_values

    if di_minus < preset_config['min_di_minus']:
        return False, f'DI_MINUS_LOW', filter_values

    if di_plus > preset_config['max_di_plus']:
        return False, f'DI_PLUS_HIGH', filter_values

    if adx < preset_config['min_adx']:
        return False, f'ADX_WEAK', filter_values

    if vol_pct < preset_config['min_vol']:
        return False, f'VOL_LOW', filter_values

    return True, 'PASSED', filter_values

def analyze_impact():
    """Analyze the impact of empirical filters on backtest results."""

    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("=" * 90)
    print("ANALYSE D'IMPACT DES FILTRES EMPIRIQUES SUR LE BACKTEST")
    print("=" * 90)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Get all trades with their indicators
    cursor.execute("""
        SELECT
            t.id,
            t.backtest_run_id,
            t.strategy_version,
            t.pnl_c,
            t.pnl_d,
            a.adx_value_4h,
            a.adx_plus_di_4h,
            a.adx_minus_di_4h,
            a.adx_4h_at_entry,
            a.di_plus_4h_at_entry,
            a.di_minus_4h_at_entry,
            a.mega_buy_details,
            a.conditions,
            a.timeframe,
            a.v3_quality_score,
            a.v4_score,
            a.v6_score,
            br.symbol,
            br.strategy_version as run_version
        FROM trades t
        JOIN alerts a ON t.alert_id = a.id
        JOIN backtest_runs br ON t.backtest_run_id = br.id
        WHERE t.pnl_c IS NOT NULL
    """)

    trades = [dict(row) for row in cursor.fetchall()]
    print(f"Total trades analysés: {len(trades)}")

    # Quick check on first few trades
    print("\n📊 ÉCHANTILLON DE DONNÉES (3 premiers trades):")
    print("-" * 60)
    for trade in trades[:3]:
        di_plus, di_minus, adx, vol_pct = extract_dmi_values(trade)
        pp, ec = extract_pp_ec(trade)
        print(f"  Trade {trade['id']} ({trade['symbol']}) - P&L: {trade['pnl_c']:+.2f}%")
        print(f"    DI+: {di_plus:.1f} | DI-: {di_minus:.1f} | ADX: {adx:.1f} | Vol: {vol_pct:.0f}%")
        print(f"    PP: {pp} | EC: {ec}")
        print()

    # Group trades by strategy version
    trades_by_version = defaultdict(list)
    for trade in trades:
        version = trade['run_version'] or trade['strategy_version'] or 'v1'
        trades_by_version[version].append(trade)

    # Analyze each version
    results = {}

    for version in sorted(trades_by_version.keys()):
        version_trades = trades_by_version[version]

        print(f"\n{'='*90}")
        print(f"VERSION {version.upper()} ({len(version_trades)} trades)")
        print(f"{'='*90}")

        # Current stats (without empirical filters)
        total = len(version_trades)
        wins = sum(1 for t in version_trades if (t['pnl_c'] or 0) > 0)
        losses = total - wins
        current_wr = (wins / total * 100) if total > 0 else 0
        current_pnl = sum(t['pnl_c'] or 0 for t in version_trades)
        big_winners_total = sum(1 for t in version_trades if (t['pnl_c'] or 0) >= 15)

        print(f"\n📊 STATS ACTUELLES (sans filtres empiriques):")
        print(f"   Total trades: {total}")
        print(f"   Wins: {wins} | Losses: {losses}")
        print(f"   Win Rate: {current_wr:.1f}%")
        print(f"   P&L Total: {current_pnl:+.2f}%")
        print(f"   Big Winners (≥15%): {big_winners_total}")

        # Analyze each preset
        version_results = {
            "current": {
                "total": total,
                "wins": wins,
                "wr": current_wr,
                "pnl": current_pnl,
                "big_winners": big_winners_total
            }
        }

        for preset_key, preset_config in PRESETS.items():
            print(f"\n📈 FILTRE '{preset_config['name'].upper()}':")
            filters_str = f"DI-≥{preset_config['min_di_minus']}, DI+≤{preset_config['max_di_plus']}, ADX≥{preset_config['min_adx']}, Vol≥{preset_config['min_vol']}%"
            if preset_config['require_pp'] or preset_config['require_ec']:
                filters_str += f", PP={preset_config['require_pp']}, EC={preset_config['require_ec']}"
            print(f"   ({filters_str})")

            passed_trades = []
            rejected_trades = []
            rejection_reasons = defaultdict(int)
            rejection_details = defaultdict(list)

            for trade in version_trades:
                passed, reason, values = check_empirical_filters(trade, preset_config)
                if passed:
                    passed_trades.append(trade)
                else:
                    rejected_trades.append(trade)
                    rejection_reasons[reason] += 1
                    # Store some sample values for rejected trades
                    if len(rejection_details[reason]) < 3:
                        rejection_details[reason].append({
                            'symbol': trade['symbol'],
                            'pnl': trade['pnl_c'],
                            **values
                        })

            new_total = len(passed_trades)
            new_wins = sum(1 for t in passed_trades if (t['pnl_c'] or 0) > 0)
            new_losses = new_total - new_wins
            new_wr = (new_wins / new_total * 100) if new_total > 0 else 0
            new_pnl = sum(t['pnl_c'] or 0 for t in passed_trades)

            # Rejected trades analysis
            rejected_wins = sum(1 for t in rejected_trades if (t['pnl_c'] or 0) > 0)
            rejected_losses = len(rejected_trades) - rejected_wins
            rejected_pnl = sum(t['pnl_c'] or 0 for t in rejected_trades)

            # Big winners analysis
            big_winners_kept = sum(1 for t in passed_trades if (t['pnl_c'] or 0) >= 15)
            big_winners_lost = sum(1 for t in rejected_trades if (t['pnl_c'] or 0) >= 15)

            print(f"   ─────────────────────────────────────────────────────")
            retention_pct = (new_total/total*100) if total > 0 else 0
            print(f"   Trades après filtre: {new_total}/{total} ({retention_pct:.1f}% conservés)")
            print(f"   Wins: {new_wins} | Losses: {new_losses}")
            wr_change = new_wr - current_wr
            print(f"   Win Rate: {new_wr:.1f}% ({wr_change:+.1f}% vs actuel)")
            print(f"   P&L Total: {new_pnl:+.2f}%")
            print(f"   ─────────────────────────────────────────────────────")
            print(f"   Trades rejetés: {len(rejected_trades)}")
            print(f"     → Wins perdus: {rejected_wins} ({rejected_pnl:+.2f}% P&L)")
            print(f"     → Losses évités: {rejected_losses}")
            print(f"   ─────────────────────────────────────────────────────")
            print(f"   Big Winners (≥15%):")
            print(f"     → Conservés: {big_winners_kept}/{big_winners_total}")
            print(f"     → Perdus: {big_winners_lost}")

            if rejection_reasons:
                print(f"   ─────────────────────────────────────────────────────")
                print(f"   Raisons de rejet:")
                for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
                    pct = count / len(rejected_trades) * 100 if rejected_trades else 0
                    print(f"     • {reason}: {count} ({pct:.0f}%)")
                    # Show sample rejected values
                    for detail in rejection_details[reason][:2]:
                        vals = f"DI+={detail['di_plus']:.1f}, DI-={detail['di_minus']:.1f}, ADX={detail['adx']:.1f}, Vol={detail['vol_pct']:.0f}%"
                        print(f"       Ex: {detail['symbol']} P&L={detail['pnl']:+.1f}% [{vals}]")

            version_results[preset_key] = {
                "total": new_total,
                "wins": new_wins,
                "wr": new_wr,
                "wr_change": wr_change,
                "pnl": new_pnl,
                "pnl_change": new_pnl - current_pnl,
                "rejected": len(rejected_trades),
                "rejected_wins": rejected_wins,
                "rejected_losses": rejected_losses,
                "big_winners_kept": big_winners_kept,
                "big_winners_lost": big_winners_lost,
                "retention_pct": retention_pct,
            }

        results[version] = version_results

    # Summary table
    print("\n" + "=" * 90)
    print("RÉSUMÉ COMPARATIF PAR VERSION")
    print("=" * 90)
    print()

    header = f"{'Version':<8} {'Actuel':<18} {'Max WR':<18} {'Balanced':<18} {'Big Winners':<18} {'No PP/EC':<18}"
    print(header)
    print(f"{'':8} {'WR% (trades)':<18} {'WR% (trades)':<18} {'WR% (trades)':<18} {'WR% (trades)':<18} {'WR% (trades)':<18}")
    print("-" * 98)

    for version in sorted(results.keys()):
        v = results[version]
        current = f"{v['current']['wr']:.1f}% ({v['current']['total']})"
        max_wr = f"{v['max_wr']['wr']:.1f}% ({v['max_wr']['total']})" if v['max_wr']['total'] > 0 else "N/A (0)"
        balanced = f"{v['balanced']['wr']:.1f}% ({v['balanced']['total']})" if v['balanced']['total'] > 0 else "N/A (0)"
        big_win = f"{v['big_winners']['wr']:.1f}% ({v['big_winners']['total']})" if v['big_winners']['total'] > 0 else "N/A (0)"
        no_ppec = f"{v['no_pp_ec']['wr']:.1f}% ({v['no_pp_ec']['total']})" if v['no_pp_ec']['total'] > 0 else "N/A (0)"
        print(f"{version:<8} {current:<18} {max_wr:<18} {balanced:<18} {big_win:<18} {no_ppec:<18}")

    # Win Rate Change Summary
    print("\n" + "=" * 90)
    print("CHANGEMENT DE WIN RATE PAR PRESET")
    print("=" * 90)
    print()
    print(f"{'Version':<8} {'Max WR':<15} {'Balanced':<15} {'Big Winners':<15} {'No PP/EC':<15}")
    print("-" * 68)

    for version in sorted(results.keys()):
        v = results[version]
        max_wr = f"{v['max_wr']['wr_change']:+.1f}%" if v['max_wr']['total'] > 0 else "N/A"
        balanced = f"{v['balanced']['wr_change']:+.1f}%" if v['balanced']['total'] > 0 else "N/A"
        big_win = f"{v['big_winners']['wr_change']:+.1f}%" if v['big_winners']['total'] > 0 else "N/A"
        no_ppec = f"{v['no_pp_ec']['wr_change']:+.1f}%" if v['no_pp_ec']['total'] > 0 else "N/A"
        print(f"{version:<8} {max_wr:<15} {balanced:<15} {big_win:<15} {no_ppec:<15}")

    # Recommendations
    print("\n" + "=" * 90)
    print("RECOMMANDATIONS")
    print("=" * 90)

    for version in sorted(results.keys()):
        v = results[version]

        # Find best preset (highest WR with reasonable retention)
        best_preset = None
        best_score = -float('inf')

        for preset_key in ['max_wr', 'balanced', 'big_winners', 'no_pp_ec']:
            p = v[preset_key]
            if p['total'] >= 3:  # Need at least 3 trades for meaningful stats
                # Score = WR improvement * sqrt(retention)
                score = p['wr_change'] * (p['retention_pct'] / 100) ** 0.5
                if p['wr'] > v['current']['wr']:  # Only consider if WR improved
                    if score > best_score:
                        best_score = score
                        best_preset = preset_key

        print(f"\n{version.upper()}:")
        if best_preset:
            p = v[best_preset]
            print(f"  ✅ Meilleur preset: {PRESETS[best_preset]['name']}")
            print(f"     • WR: {v['current']['wr']:.1f}% → {p['wr']:.1f}% ({p['wr_change']:+.1f}%)")
            print(f"     • Trades: {v['current']['total']} → {p['total']} ({p['retention_pct']:.0f}% conservés)")
            print(f"     • Big Winners conservés: {p['big_winners_kept']}/{v['current']['big_winners']}")
        else:
            # Check if current WR is already very high
            if v['current']['wr'] >= 75:
                print(f"  ⚠️ WR actuel déjà excellent ({v['current']['wr']:.1f}%)")
                print(f"     Les filtres empiriques réduisent trop les trades sans amélioration")
            else:
                print(f"  ⚠️ Aucun preset n'améliore significativement le WR")
                print(f"     Données insuffisantes ou filtres trop restrictifs")

    conn.close()
    return results

if __name__ == "__main__":
    analyze_impact()
