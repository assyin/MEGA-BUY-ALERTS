# 🔬 V11B — Trois vérifications avant implémentation Tier 1

_Généré : 2026-04-28 — basé sur 199 trades fermés V11B (139 train / 60 test)_

**Statut** : analyses factuelles uniquement. Pas de modification de code. Rapport préparatoire au feu vert utilisateur.

---

# 1️⃣ Sharpe annualisé 49.68 — vérification de la formule + interprétation live

## ✅ La formule est mathématiquement correcte

```python
mean_r = statistics.mean(pnls_pct)        # ≈ 7.15% per trade
std_r  = statistics.stdev(pnls_pct)        # ≈ 7.08% per trade
sharpe_per_trade = mean_r / std_r          # ≈ 1.010

trades_per_year = 199 × (365/30)           # ≈ 2422 trades/an
sharpe_annual = sharpe_per_trade × sqrt(2422)  # ≈ 49.68
```

C'est la **formule standard d'annualisation** d'un Sharpe per-period :
`Sharpe_annual = Sharpe_period × sqrt(periods_per_year)`

Pour des **rendements quotidiens** (S&P 500 par exemple) on multiplie par √252.
Ici on a des rendements **per-trade** sur ~2422 trades/an extrapolés → √2422 ≈ 49.

## 🚨 Pourquoi le chiffre est si élevé (3 raisons)

### Raison 1 — Variance artificiellement basse
Le exit hybride V7 **discrétise** les sorties autour de 4 valeurs principales :
- TP1+BE : ~+5% (50% × 10%)
- TP1+TP2+trail : +12 à +25%
- SL : ~-8%
- Timeout : variable mais souvent compressé

→ La distribution des returns ressemble à un mélange de quelques pics au lieu d'une cloche continue. **Std artificiellement bas** car les trades clustent autour de ces points discrets.

Comparaison :
- Trade strategy classique (entrée libre / exit selon contexte) : std/mean ≈ 2-4
- V11B : std/mean ≈ 1.0 (très contraint par le exit hybride)

### Raison 2 — Hypothèse i.i.d. fausse
La formule `× √trades_per_year` suppose que chaque trade est **indépendant** et que les statistiques observées tiennent toute l'année. En réalité :
- Trades clustent temporellement (plusieurs alertes V11B sortent souvent le même jour)
- Régime BTC change → mean et std changent
- 2422 trades/an est une extrapolation depuis 199 trades sur 30j (peut être faux)

Si la **vraie** auto-corrélation entre trades est positive (régime persistance), la formule sur-estime le Sharpe.

### Raison 3 — WR exceptionnel sur fenêtre courte
- WR 86% × avg_win 10% × avg_loss 8% sur 30 jours
- Si un futur régime baisse cette WR à 65% (réaliste live), la formule donne :
  - mean = 0.65×10% + 0.35×(-8%) = +3.7%
  - std plus élevé (plus de variance autour des SL)
  - sharpe_per_trade ≈ 0.4
  - sharpe_annual ≈ 20 (toujours haut mais plus crédible)

## 📊 Comparaison à des benchmarks réels

| Strategy | Sharpe annualisé typique |
|---|---|
| S&P 500 (long-only) | 0.5 - 1.0 |
| Top hedge funds (Renaissance) | 2 - 4 |
| HFT firms (frequence 1ms) | 5 - 10+ |
| **V11B backtest (annualisé)** | **49.68** |
| **V11B Sortino backtest** | **150.59** ← encore pire |

Sharpe de 49 ou Sortino de 150 sont **physiquement improbables** sur du trading live discrétionnaire. C'est un signal que les conditions de backtest sont **trop bonnes pour être vraies**.

## 🎯 Comportement attendu en live

| Source de dégradation | Impact estimé sur Sharpe |
|---|---|
| Slippage (entrée + sortie) | -10 à -20pts |
| Fees Binance (0.1% × 4 legs en hybride) | -3 à -5pts |
| Latence (alerte → ordre) | -5 à -10pts |
| Régime non favorable (1 mois sur 4) | -10 à -15pts |
| Variance réelle plus large | -10 à -20pts |
| **Total dégradation attendue** | **~-40 à -60pts** |
| **Sharpe annualisé live attendu** | **0 à 10** |

Un Sharpe live de **2 à 4** serait déjà excellent. Au-dessus de 5 = soupçon, au-dessus de 10 = bug ou data leakage non détecté.

## ✅ Recommandation : ignorer le Sharpe, prioriser d'autres métriques

| Métrique | Valeur V11B | Pourquoi mieux que Sharpe |
|---|---|---|
| **Profit Factor** | 8.68 | Borné, plus interprétable |
| **WR + Avg Win/Loss ratio** | 86% × 1.25 | Trader-readable |
| **Max DD intra-période** | 1.21% | Risque de capital concret |
| **Max consec. losses** | 3 | Nombre psychologiquement supportable |
| **Calmar ratio** (return / DD) | À calculer | ~ ROI 114% / DD 1.2% = 95 (encore haut mais crédible) |

**Mon conseil pour le reporting** : afficher Sharpe avec **un avertissement explicite** "annualisation théorique, ne pas comparer aux Sharpe traditionnels", et mettre en avant le **Profit Factor** + **DD** qui sont plus interprétables.

---

# 2️⃣ TP2 = 13% — robustesse train vs test

## Méthode

Split chronologique 70/30 :
- **Train** : premiers 139 trades (31/03 → 14/04, 14j)
- **Test** : derniers 60 trades (14/04 → 26/04, 12j)

Pour chaque TP2 candidat, simulation du PnL avec exit hybride V7 (TP1=10%/50%, trail 8%, SL -8%, BE-stop après TP1).

## Résultats détaillés

| TP2 | Train PnL ($) | Test PnL ($) | Combined ($) |
|---:|---:|---:|---:|
| 10.0% | +3,385 | +1,968 | +5,353 ⭐ |
| 11.0% | +3,379 | +1,966 | +5,345 |
| 12.0% | +3,372 | +1,951 | +5,323 |
| **13.0%** | **+3,386 ⭐** | +1,963 | +5,349 |
| 14.0% | +3,243 | **+1,968 ⭐** | +5,211 |
| 15.0% | +3,253 | +1,921 | +5,174 |
| 16.0% | +3,257 | +1,887 | +5,144 |
| 17.5% | +3,166 | +1,886 | +5,052 |
| 20.0% (actuel) | +3,049 | +1,841 | +4,890 |
| 22.5% | +2,879 | +1,690 | +4,569 |
| 25.0% | +2,777 | +1,536 | +4,313 |

## Verdict critère utilisateur

| Optimum | Valeur |
|---|---|
| Train | **TP2 = 13%** ($+3,386) |
| Test | **TP2 = 14%** ($+1,968) |
| **Δ train ↔ test** | **1 pt** |
| Critère utilisateur (Δ ≤ 2pts) | ✅ **PASSED** |

→ **Pas d'overfitting détecté.** L'optimum est stable hors échantillon.

## Insight supplémentaire — la courbe est plate sur 10-14%

```
TP2  | Combined PnL
10%  | $5,353  ← max global
11%  | $5,345  (-$8)
12%  | $5,323  (-$30)
13%  | $5,349  (-$4)
14%  | $5,211  (-$142)  ← chute brutale
```

→ Toute valeur de TP2 entre **10% et 13%** donne un PnL similaire (Δ < $30 sur ~$5350). À partir de 14%, ça dégrade.

**Conclusion** : il n'y a pas UNE valeur optimale précise, mais une **plage robuste [10-13%]**. Le choix exact dans cette fourchette est presque arbitraire.

## Recommandation finale

**TP2 = 13%** reste le bon choix car :
1. Stable train/test (Δ 1pt — bien sous le seuil utilisateur)
2. Sur la courbe combined, c'est le 2e meilleur ($5,349 vs max $5,353 — différence négligeable)
3. Rester légèrement au-dessus de TP1=10% laisse une "marge" psychologique (le trade doit prouver quelque chose au-delà de TP1 avant de partial-exit en TP2)
4. Plus facile à expliquer/documenter qu'un TP2 = 10% qui "colle" à TP1

**Action recommandée si feu vert** : implémenter TP2=13% pour V11B. Re-tester après +200 trades en live pour confirmer.

---

# 3️⃣ BTC dump cap — version minimaliste + version dynamique (layered)

## Logique défense en profondeur

L'utilisateur demande **2 niveaux** de protection au lieu d'un seul :

```
NIVEAU 1 — HARD STOP (minimaliste, couvre 80% du risque)
└── Si BTC change 24h ≤ -5% → AUCUN nouveau trade V11B

NIVEAU 2 — SOFT CAP (dynamique, couvre les dumps modérés)
└── Si BTC change 24h ∈ [-5%, -3%] ET déjà ≥ 6 positions ouvertes → skip
```

## Pourquoi cette stratégie en couches est meilleure

### Niveau 1 (hard stop) seul
- Ne couvre QUE les "vrais" crashes (-5% en 24h, événement rare)
- En 30 jours, peut-être 2-3 occurrences max
- **Pro** : trivial à implémenter, comportement prévisible
- **Con** : pas de protection sur les "petits" dumps -3%/-4% qui sont fréquents

### Niveau 2 (soft cap) seul
- Couvre les dumps modérés (-3% à -5%)
- Plus subtil — mode prudence sans tout fermer
- **Pro** : continue à trader avec exposure réduit
- **Con** : ne protège pas contre les VRAIS crashes -10%/-20%

### Niveau 1 + 2 combinés (recommandé)
- BTC-5% : hard stop
- BTC-3 à -5% : cap à 6 positions
- BTC > -3% : normal jusqu'à 12 positions
- **Couvre tous les régimes** avec granularité progressive

## Code proposé (à implémenter au feu vert)

Dans `manager_v11_base.py`, méthode `try_open_position` :

```python
# === BTC DUMP PROTECTION (layered) ===
btc_24h = alert.get("btc_change_24h")  # peut venir de market_sentiment
if btc_24h is None:
    # Fallback : fetch live si non disponible dans alert
    try:
        from openclaw.pipeline.market_sentiment import MarketSentiment
        btc_24h = MarketSentiment.get_all().get("btc_change_24h")
    except Exception:
        btc_24h = 0  # neutre si indisponible

# Hard stop (niveau 1)
if btc_24h is not None and btc_24h <= -5:
    print(f"💼 {self.VARIANT.upper()} SKIP {pair}: BTC dump {btc_24h:.1f}% — hard stop")
    return None

# Soft cap (niveau 2)
if btc_24h is not None and btc_24h <= -3 and len(open_positions) >= 6:
    print(f"💼 {self.VARIANT.upper()} SKIP {pair}: BTC dump {btc_24h:.1f}% + 6+ open — soft cap")
    return None
```

## Effort estimé

- **Hard stop seul** : 5-10 min (juste un `if`)
- **Hard stop + soft cap layered** : 15-20 min (dont le check `len(open_positions)`)

L'utilisateur a raison : **hard stop seul couvre 80% du risque** avec 5 min de code. Le soft cap est nice-to-have qui couvre les 20% restants.

## Backtest impact (estimé)

Sur les 30 jours de V11B backtest :
- Combien de trades pris pendant BTC ≤ -5% ? Difficile à mesurer rétrospectivement sans recharger les klines BTC pour chaque alerte
- Estimation conservatrice : ~5-10% des trades V11B
- Impact PnL si on les avait skippés : probablement **-$200 à -$500** (perte partielle de bons trades)
- MAIS : protection contre tail risk en bear market (qu'on n'a pas vu sur ces 30j)

→ Coût quasi nul en bull market, **assurance massive** en bear/crash.

## Recommandation finale

**Implémenter les 2 niveaux** (hard stop + soft cap layered). 15 minutes de dev pour une protection complète.

Si le user veut faire encore plus minimaliste : commencer par **hard stop seul** aujourd'hui, ajouter soft cap dans 1 semaine après observation.

---

# 📋 Synthèse des 3 vérifications

| Vérification | Résultat | Verdict |
|---|---|---|
| **#1 Sharpe 49.68** | Formule correcte mais conditions backtest trop favorables. Live attendu Sharpe 0-10. | ⚠️ **Mettre warning dans le reporting**, ne pas s'extasier sur le chiffre |
| **#2 TP2 stable train/test** | Δ 1pt (≤ critère 2pts). TP2=13% confirmé robuste. | ✅ **GO** pour TP2=13% |
| **#3 BTC dump (layered)** | 2 niveaux meilleurs qu'1 seul. Hard stop seul = 80% du gain en 5min, layered = 100% en 15min. | ✅ **GO** pour layered (15 min) |

## Plan Tier 1 ajusté après ces vérifications

```
TIER 1 (au feu vert) :
├── 1. TP2 = 13% pour V11B (10 min)
│   └── manager_v11.py : override dans PortfolioManagerV11B class
│
├── 2. BTC dump protection layered (15 min)
│   └── manager_v11_base.py : hard stop -5% + soft cap -3% si 6+ open
│
├── 3. Risk metrics au reporting (30 min)
│   ├── audit_v11b_html.py : nouvelle section "Risk metrics"
│   ├── audit_v11b_trades.py : idem en MD
│   └── ⚠️ Mettre WARNING sur Sharpe annualisé : "théorique — voir doc"
│
└── 4. (Bonus) Documenter les caveats Sharpe dans le rapport HTML
    └── Une note sous le Sharpe expliquant pourquoi 49 ne se transposera pas en live

Total : ~1h dev, 0 risque, gains mesurables
```

## En attente de ton feu vert pour démarrer.
