# MEGA BUY V4 vs V5 - Analyse Complète des Backtests

**Date**: 2026-03-14
**Données analysées**: 184 trades, 2189 alertes
**Période**: 2026-02-01 à 2026-03-14

---

## 1. Résumé Exécutif

| Métrique | Valeur |
|----------|--------|
| **Total Trades** | 184 |
| **Win Rate (Strategy C)** | 65.8% |
| **Total PnL (Strategy C)** | +991.37% |
| **Avg Win** | +10.44% |
| **Avg Loss** | -4.31% |
| **Profit Factor** | 4.65 |

### Performance V4 vs V5

| Version | Trades | Win Rate | Avg PnL |
|---------|--------|----------|---------|
| **V4** | 128 | 65.6% | +4.83% |
| **V5** | 56 | 66.1% | +6.66% |

**V5 montre une légère amélioration** avec un meilleur Win Rate et un PnL moyen supérieur.

---

## 2. Analyse des Alertes et Rejections

### Distribution des Statuts (2189 alertes)

| Statut | Count | % |
|--------|-------|---|
| REJECTED_15M_ALONE | 648 | 29.6% |
| REJECTED_STC | 476 | 21.7% |
| REJECTED_PP_BUY | 316 | 14.4% |
| V3_NO_RETEST | 242 | 11.1% |
| V3_PROG_X_5 (toutes) | 365 | 16.7% |
| VALID_V4 | 69 | 3.2% |
| V4_Rejections | 72 | 3.3% |

### Filtres V4 Spécifiques

| Rejection Reason | Count | Description |
|------------------|-------|-------------|
| V4_V3_QUALITY_5 | 18 | Quality Score < 6 |
| V4_STC_NO_1H_30M | 14 | STC non validé sur 1H/30M |
| V4_V3_QUALITY_4 | 10 | Quality Score < 5 |
| V4_STC_NO_1H_15M | 9 | STC non validé sur 1H/15M |
| V4_BLACKLIST | 7 | Paire blacklistée |
| V4_TL_DELAY_XXH | 7 | Délai TL Break trop long |
| V4_WEAK_OB_40 | 2 | Order Block trop faible |

---

## 3. Analyse des Trades par Facteur

### 3.1 Par Timeframe

| Timeframe | Win Rate | Avg PnL | Trades |
|-----------|----------|---------|--------|
| **30m** | **69.9%** | +6.33% | 93 |
| 15m | 63.9% | +2.05% | 36 |
| 1h | 60.0% | +5.97% | 55 |

**Recommandation**: Le timeframe **30m offre le meilleur Win Rate (69.9%)**. Prioriser les signaux 30m.

### 3.2 Par Score MEGA BUY

| Score | Win Rate | Avg PnL | Trades |
|-------|----------|---------|--------|
| **10** | **82.8%** | +6.47% | 29 |
| 9 | 68.8% | +10.08% | 32 |
| 8 | 63.0% | +8.85% | 27 |
| 7 | 100% | +19.64% | 3 |

**Recommandation**: Les scores **9 et 10** offrent les meilleures performances. Score 8 est acceptable mais avec un Win Rate inférieur.

### 3.3 Par VP Grade

| Grade | Win Rate | Avg PnL | Trades |
|-------|----------|---------|--------|
| **A** | **100%** | +20.70% | 12 |
| **B** | **100%** | +10.07% | 6 |
| A+ | 70.4% | +6.28% | 54 |
| B+ | 40.0% | +15.49% | 10 |
| D | 0% | -4.34% | 2 |

**Recommandation**:
- Grade **A et B = 100% Win Rate** - Trades à haute priorité
- Grade **A+** = Bon mais pas parfait
- Grade **B+ et D** = À éviter

### 3.4 Par VAL Retest

| VAL Retested | Win Rate | Avg PnL | Trades |
|--------------|----------|---------|--------|
| **True** | **75.0%** | +9.75% | 84 |
| False | 42.9% | -1.56% | 7 |

**Recommandation**: **Exiger VAL Retested = True** comme condition. Les trades sans VAL retest ont un Win Rate de seulement 42.9%.

### 3.5 Par VAL Bounce Confirmed

| Bounce Confirmé | Win Rate | Avg PnL | Trades |
|-----------------|----------|---------|--------|
| True | 75.0% | +6.08% | 72 |
| False | 63.2% | +19.49% | 19 |

**Observation**: Les trades SANS bounce confirmé ont un meilleur PnL moyen mais un Win Rate inférieur. Cela suggère des mouvements plus forts mais plus risqués.

### 3.6 Par V3 Quality Score

| Quality | Win Rate | Avg PnL | Trades |
|---------|----------|---------|--------|
| **9** | **100%** | **+29.02%** | 14 |
| **11** | **100%** | +13.87% | 4 |
| **12** | **100%** | +4.14% | 1 |
| 7 | 73.3% | +5.35% | 30 |
| 6 | 62.5% | +13.96% | 8 |
| 8 | 52.4% | +2.69% | 21 |
| 10 | 50.0% | -0.07% | 6 |

**Recommandation**: **Quality Score 9 = meilleure performance** (100% WR, +29% avg). Quality 8 et 10 ont un Win Rate faible de ~50%.

### 3.7 Par Box Range

| Range | Win Rate | Avg PnL | Trades |
|-------|----------|---------|--------|
| **2-4%** | **77.4%** | +9.30% | 53 |
| 4-6% | 69.2% | +21.42% | 13 |
| <2% | 60.0% | +2.31% | 20 |
| >6% | 66.7% | -3.47% | 3 |

**Recommandation**: **Box Range entre 2-4%** offre le meilleur Win Rate. Les ranges trop petits (<2%) ou trop grands (>6%) sont moins performants.

### 3.8 Par Combo Timeframes

| Combo | Win Rate | Avg PnL | Trades |
|-------|----------|---------|--------|
| **15m,1h** | **100%** | +5.91% | 7 |
| 30m | 76.3% | +10.76% | 38 |
| 15m,30m,1h | 75.0% | +2.20% | 4 |
| 1h | 72.7% | +14.08% | 22 |
| 15m,30m | 55.0% | +1.97% | 20 |

**Recommandation**:
- **15m+1h combo = 100% Win Rate**
- **30m seul = 76.3%** (très bon)
- **Éviter 15m+30m** (55% Win Rate)

---

## 4. Analyse des Trades Perdants

### Caractéristiques des 63 Losers

| Métrique | Valeur |
|----------|--------|
| Total Losers | 63 |
| Average Loss | -4.31% |
| Trailing Activated | 0 |
| TP1 Hit | 0 |
| Max Unrealized Gain (avg) | +4.44% |

### Pattern des Pertes

**TOUS les trades perdants ont été stoppés par le SL (Box Low)** sans jamais atteindre TP1 ou activer le trailing.

### Distribution des Gains Non-Réalisés

| Max Gain Atteint | Trades |
|------------------|--------|
| >= 5% | 23 (36.5%) |
| >= 10% | 0 |
| >= 15% | 0 |
| >= 20% | 0 |

**Observation critique**: 36.5% des trades perdants ont atteint +5% avant de revenir au SL, mais aucun n'a atteint +10%.

### Top 5 Pires Pertes

| Symbol | Timeframe | PnL | Cause |
|--------|-----------|-----|-------|
| HOLOUSDT | 1h | -11.41% | SL Box Low |
| ALLOUSDT | 15m | -11.07% | SL Box Low |
| VIRTUALUSDT | 1h | -11.03% | SL Box Low |
| VIRTUALUSDT | 1h | -10.21% | SL Box Low |
| VIRTUALUSDT | 1h | -8.34% | SL Box Low |

---

## 5. Analyse des Trades Gagnants

### Caractéristiques des 121 Winners

| Métrique | Valeur |
|----------|--------|
| Total Winners | 121 |
| Average Win | +10.44% |
| Via Trailing SL | ~40% |
| Via Break-Even SL | ~35% |
| Position Ouverte | ~10% |

### Top 5 Meilleurs Trades

| Symbol | Timeframe | PnL | Exit |
|--------|-----------|-----|------|
| INITUSDT | 1h | +78.73% | Trailing SL |
| MIRAUSDT | 30m | +55.58% | Trailing SL |
| MIRAUSDT | 1h | +54.86% | Trailing SL |
| WINUSDT | 1h | +35.42% | Trailing SL |
| ORCAUSDT | 30m | +29.58% | Trailing SL |

---

## 6. Combinaisons Optimales Identifiées

### Configuration Haute Probabilité (Win Rate > 75%)

```
Score >= 9 AND
VAL_Retested = True AND
Box_Range BETWEEN 2% AND 6% AND
(Timeframe = 30m OR Combo = 15m+1h) AND
VP_Grade IN ('A', 'A+', 'B') AND
Quality_Score >= 7
```

**Résultats attendus**:
- Win Rate: ~80%
- Avg PnL: +12-15%

### Conditions à ÉVITER

| Condition | Win Rate | Action |
|-----------|----------|--------|
| VP Grade = D | 0% | **REJETER** |
| VAL Retested = False | 42.9% | **REJETER** |
| Box Range < 2% | 60% | Prudence |
| Combo 15m+30m | 55% | **REJETER** |
| Quality Score = 8 ou 10 | 50-52% | Prudence |

---

## 7. Recommandations pour Améliorer le Win Rate

### 7.1 Nouveaux Filtres V5/V6 Proposés

#### Filtre 1: VP Grade Minimum
```python
# Rejeter si VP Grade est D ou absent
if vp_grade in ['D', None]:
    reject("V6_BAD_VP_GRADE")
```
**Impact estimé**: +3-5% Win Rate

#### Filtre 2: VAL Retest Obligatoire
```python
# Exiger VAL retest pour valider
if not vp_val_retested:
    reject("V6_NO_VAL_RETEST")
```
**Impact estimé**: +5-8% Win Rate

#### Filtre 3: Box Range Optimal
```python
# Box range entre 2% et 6%
if box_range_pct < 2.0 or box_range_pct > 6.0:
    reject("V6_SUBOPTIMAL_BOX_RANGE")
```
**Impact estimé**: +3-5% Win Rate

#### Filtre 4: Éviter Combo 15m+30m
```python
# Rejeter les combos faibles
if combo_tfs == "15m,30m":
    reject("V6_WEAK_COMBO")
```
**Impact estimé**: +2-3% Win Rate

#### Filtre 5: Quality Score Optimal
```python
# Éviter quality 8 et 10 qui ont ~50% WR
if quality_score in [8, 10]:
    warn("V6_SUBOPTIMAL_QUALITY")
```
**Impact estimé**: +3-4% Win Rate

### 7.2 Optimisation du Stop Loss

#### SL basé sur VAL (Implémenté en V5)
```python
# Au lieu de Box Low, utiliser VAL - 3%
sl_price = val_1h * 0.97
```
**Résultat VIRTUALUSDT**: Trade perdant (-3.87%) → Trade gagnant (+8.44%)

#### SL avec HVN Support
```python
# Si HVN proche du SL, ajuster
if hvn_level and hvn_level > val_1h:
    sl_price = hvn_level * 0.97
```

### 7.3 Ajustements de la Stratégie de Sortie

#### Trailing Activation Plus Rapide
Actuel: +20% pour activer le trailing
Proposé: +15% pour activer le trailing

**Raison**: 36.5% des losers atteignent +5% mais aucun +10%. Un trailing plus agressif pourrait capturer plus de gains.

#### Take Profit Partiel Plus Tôt
Actuel: TP1 = +15%
Proposé: TP1 = +10%

**Raison**: Sécuriser des gains avant retournement.

---

## 8. Matrice de Décision V6 Proposée

### Prérequis (OBLIGATOIRES)

| Condition | Seuil | Si FALSE |
|-----------|-------|----------|
| STC Validated | Au moins 1 TF | REJECT |
| Not 15m Alone | 30m ou 1h requis | REJECT |
| Trendline Exists | Présente | REJECT |
| PP_buy | True | REJECT |
| VAL Retested | True | REJECT |
| VP Grade | != D | REJECT |

### Scoring V6

| Facteur | Points |
|---------|--------|
| Score 10 | +15 |
| Score 9 | +10 |
| Score 8 | +5 |
| VP Grade A | +15 |
| VP Grade A+ | +10 |
| VP Grade B | +10 |
| VP Grade B+ | +5 |
| VAL Bounce Confirmed | +10 |
| Timeframe 30m | +10 |
| Combo 15m+1h | +15 |
| Box Range 2-4% | +10 |
| Box Range 4-6% | +5 |
| Quality Score 9 | +15 |
| Quality Score 7 | +10 |
| Fib Bonus | +5 |
| OB Bonus | +5 |

**Seuil minimum V6**: 40 points

---

## 9. Conclusion

### Forces Actuelles
- Win Rate de 65.8% est solide
- Profit Factor de 4.65 est excellent
- Les filtres STC, PP_buy et 15m_alone fonctionnent

### Faiblesses Identifiées
1. **VAL Retest** non obligatoire (42.9% WR sans)
2. **VP Grade D** accepté (0% WR)
3. **Combo 15m+30m** accepté (55% WR)
4. **Box Range** non filtré (<2% = 60% WR)
5. **SL Box Low** parfois trop proche

### Amélioration Potentielle

| Métrique | Actuel | Avec V6 |
|----------|--------|---------|
| Win Rate | 65.8% | ~75-80% |
| Trades/mois | ~45 | ~25-30 |
| Avg PnL | +5.4% | +8-10% |

**Trade-off**: Moins de trades mais de meilleure qualité.

---

## 10. Prochaines Étapes

1. **Implémenter les filtres V6** dans engine.py
2. **Backtester V6** sur les mêmes données
3. **Comparer V4/V5/V6** sur période étendue
4. **Ajuster les seuils** si nécessaire
5. **Déployer en production** après validation

---

*Rapport généré automatiquement par Claude Code*
