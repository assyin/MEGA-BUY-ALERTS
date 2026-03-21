# Analyse d'Intégration des Filtres Empiriques dans le Système de Backtest

**Date**: 2026-03-19
**Auteur**: Claude AI
**Version**: 1.0

---

## Table des Matières

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [État Actuel du Système de Backtest](#2-état-actuel-du-système-de-backtest)
3. [Filtres Empiriques à Intégrer](#3-filtres-empiriques-à-intégrer)
4. [Analyse par Version (V1-V6)](#4-analyse-par-version-v1-v6)
5. [Plan d'Implémentation](#5-plan-dimplémentation)
6. [Impact Attendu](#6-impact-attendu)
7. [Risques et Considérations](#7-risques-et-considérations)
8. [Recommandations](#8-recommandations)

---

## 1. Résumé Exécutif

### Objectif
Intégrer les filtres empiriques validés (DI-, DI+, ADX, Vol%) dans le système de backtest pour améliorer la sélection des trades et augmenter le Win Rate global.

### Filtres Validés (sur 2076 trades)

| Filtre | Paramètres | Win Rate | Trades | Gros Gagnants |
|--------|------------|----------|--------|---------------|
| **Max Win Rate** | DI-≥22, DI+≤25, ADX≥35, Vol≥100% | **77.1%** | 105 | 4 |
| **Balanced** | DI-≥22, DI+≤20, ADX≥21, Vol≥100% | **75.0%** | 288 | 15 |
| **Big Winners** | DI-≥22, DI+≤25, ADX≥21, Vol≥100% | **73.0%** | 393 | 18 |

### Amélioration Potentielle

| Métrique | Actuel (V6) | Avec Filtres | Amélioration |
|----------|-------------|--------------|--------------|
| Win Rate | 50-55% | 73-77% | **+18-22%** |
| Sélectivité | ~40% | ~20% | Plus strict |
| Big Winners | Variable | 18/110 (16%) | Conserve 16% |

---

## 2. État Actuel du Système de Backtest

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SYSTÈME DE BACKTEST                         │
├─────────────────────────────────────────────────────────────────┤
│  api/engine.py     │ 9,340 lignes │ Logique principale         │
│  api/main.py       │ 490 lignes   │ Endpoints FastAPI          │
│  api/models.py     │ 857 lignes   │ Schéma SQLAlchemy          │
│  data/backtest.db  │ SQLite       │ Base de données            │
└─────────────────────────────────────────────────────────────────┘
```

### Versions Existantes

| Version | Description | Win Rate | Logique Principale |
|---------|-------------|----------|-------------------|
| **V1** | Baseline | ~35% | TL Break + 5 conditions progressives |
| **V2** | Optimized | ~45% | V1 + 8+ bonus indicators |
| **V3** | Golden Box | ~40% | Retest après breakout |
| **V4** | Strict | 50.7% | V3 + 5 filtres obligatoires |
| **V5** | Volume Profile | ~55% | V4 + VP trajectory |
| **V6** | Timing + Momentum | 75.5%* | V4 + timing per TF + limiter |

*Win Rate V6 avec score ≥40

### Indicateurs Actuellement Calculés

Le système calcule déjà les indicateurs DMI (DI+, DI-, ADX) dans `engine.py`:

```python
# Ligne 5915 dans engine.py
adx, plus_di, minus_di = calc_adx(high, low, close, self.config['DMI_LENGTH'])
```

**Colonnes existantes dans Alert model**:
- `adx_value` - Valeur ADX 4H
- `di_plus_4h` - Valeur DI+ 4H (à ajouter)
- `di_minus_4h` - Valeur DI- 4H (à ajouter)
- `dmi_spread` - Écart DI+ - DI- (à ajouter)
- `vol_pct_max` - Volume % max (existe partiellement)

---

## 3. Filtres Empiriques à Intégrer

### 3.1 Définition des Seuils

```python
# Configuration proposée pour DEFAULT_CONFIG
EMPIRICAL_FILTER_CONFIG = {
    # === FILTRES DI-/DI+ ===
    'DMI_FILTER_ENABLED': True,
    'MIN_DI_MINUS_4H': 22.0,      # DI- minimum (vendeurs présents)
    'MAX_DI_PLUS_4H': 25.0,       # DI+ maximum (pas de surachat)
    'MAX_DI_PLUS_STRICT': 20.0,   # DI+ strict pour Balanced

    # === FILTRE ADX ===
    'ADX_FILTER_ENABLED': True,
    'MIN_ADX_MODERATE': 21.0,     # ADX minimum modéré
    'MIN_ADX_STRONG': 35.0,       # ADX minimum fort (Max WR)

    # === FILTRE VOLUME ===
    'VOL_FILTER_ENABLED': True,
    'MIN_VOL_PCT': 100.0,         # Volume minimum (% de moyenne)

    # === CONDITIONS OBLIGATOIRES ===
    'REQUIRE_PP': True,           # PP_buy obligatoire
    'REQUIRE_EC': True,           # EC obligatoire

    # === PRESETS ===
    'FILTER_PRESET': 'big_winners',  # Options: 'max_wr', 'balanced', 'big_winners'
}
```

### 3.2 Logique de Filtrage

```python
def check_empirical_filters(alert_data: dict, config: dict) -> tuple[bool, str, int]:
    """
    Vérifie les filtres empiriques sur une alerte.

    Returns:
        (is_valid, rejection_reason, score)
    """
    di_minus = alert_data.get('di_minus_4h', 0)
    di_plus = alert_data.get('di_plus_4h', 0)
    adx = alert_data.get('adx_4h', 0)
    vol_pct = alert_data.get('vol_pct_max', 0)
    pp = alert_data.get('pp', False)
    ec = alert_data.get('ec', False)

    preset = config.get('FILTER_PRESET', 'big_winners')
    score = 0

    # === CONDITIONS OBLIGATOIRES PP/EC ===
    if config.get('REQUIRE_PP', True) and not pp:
        return False, 'NO_PP', 0
    if config.get('REQUIRE_EC', True) and not ec:
        return False, 'NO_EC', 0

    # === FILTRE DI- ===
    min_di_minus = config.get('MIN_DI_MINUS_4H', 22)
    if di_minus < min_di_minus:
        return False, f'DI_MINUS_LOW_{di_minus:.1f}', 0
    score += 10  # Bonus DI- valide

    # === FILTRE DI+ ===
    if preset == 'balanced':
        max_di_plus = config.get('MAX_DI_PLUS_STRICT', 20)
    else:
        max_di_plus = config.get('MAX_DI_PLUS_4H', 25)

    if di_plus > max_di_plus:
        return False, f'DI_PLUS_HIGH_{di_plus:.1f}', 0
    score += 10  # Bonus DI+ valide

    # === FILTRE ADX ===
    if preset == 'max_wr':
        min_adx = config.get('MIN_ADX_STRONG', 35)
    else:
        min_adx = config.get('MIN_ADX_MODERATE', 21)

    if adx < min_adx:
        return False, f'ADX_WEAK_{adx:.1f}', 0
    score += 15 if adx >= 35 else 10  # Bonus ADX

    # === FILTRE VOLUME ===
    min_vol = config.get('MIN_VOL_PCT', 100)
    if vol_pct < min_vol:
        return False, f'VOL_LOW_{vol_pct:.1f}', 0

    # Bonus volume
    if vol_pct >= 200:
        score += 20  # Volume explosif
    elif vol_pct >= 150:
        score += 15  # Volume fort
    else:
        score += 10  # Volume normal

    # === SCORE FINAL ===
    return True, 'EMPIRICAL_VALID', score
```

---

## 4. Analyse par Version (V1-V6)

### 4.1 V1 - Legacy (Baseline)

**État Actuel**:
- Aucun filtre avancé
- Entry: TL Break + 5 conditions progressives
- Win Rate: ~35%

**Intégration Proposée**:
```
V1 → V1 + Filtres Empiriques = "V1E" (Enhanced)
```

| Changement | Impact Estimé |
|------------|---------------|
| Ajouter DI-≥22 | +8% WR |
| Ajouter DI+≤25 | +5% WR |
| Ajouter ADX≥21 | +7% WR |
| Ajouter Vol≥100% | +3% WR |
| **Total** | **~55% WR** (estimation) |

**Implémentation**:
```python
# Dans run_backtest(), après les 5 conditions progressives:
if self.config.get('DMI_FILTER_ENABLED', False):
    is_valid, reason, emp_score = check_empirical_filters(alert_data, self.config)
    if not is_valid:
        alert.status = 'REJECTED_EMPIRICAL'
        alert.empirical_rejection = reason
        continue
    alert.empirical_score = emp_score
```

---

### 4.2 V2 - Optimized (Bonus Analysis)

**État Actuel**:
- 21 bonus indicators tracés
- Rejection si bonus_count < 8
- Win Rate: ~45%

**Analyse de Compatibilité**:

Les filtres empiriques complètent V2 car ils sont basés sur des indicateurs différents:

| V2 Actuel | Filtres Empiriques |
|-----------|-------------------|
| Fib 4H/1H ratio | DI- seuil |
| ETH correlation | DI+ seuil |
| StochRSI | ADX seuil |
| OB score | Vol % |
| MEGA BUY score | PP/EC |

**Intégration Proposée**:
```
V2 existant + Filtres Empiriques = "V2E"
- Conserver les 21 bonus
- Ajouter filtre DI-/DI+/ADX/Vol comme PRE-CONDITION
```

**Ordre de Filtrage**:
```
1. Filtres Empiriques (DI-/DI+/ADX/Vol) → Reject si fail
2. V2 Bonus Analysis → Score
3. Reject si bonus_count < 8
```

**Impact Estimé**:
- Win Rate: 45% → **65-70%**
- Trades: Réduction de 40-50%

---

### 4.3 V3 - Golden Box Retest

**État Actuel**:
- Entry via retest du Golden Box
- Quality Score 0-10
- Win Rate: ~40%

**Point d'Intégration**:

Les filtres empiriques doivent être appliqués **AU MOMENT DU RETEST**, pas au moment du signal initial:

```python
def validate_v3_entry_with_empirical(df, retest_idx, alert_data, config):
    """
    Valide l'entrée V3 avec filtres empiriques au moment du retest.
    """
    # 1. Calculer DI+/DI-/ADX au moment du retest
    di_plus_at_retest = df['plus_di'].iloc[retest_idx]
    di_minus_at_retest = df['minus_di'].iloc[retest_idx]
    adx_at_retest = df['adx'].iloc[retest_idx]

    # 2. Vérifier les seuils
    if di_minus_at_retest < config.get('MIN_DI_MINUS_4H', 22):
        return False, 'V3_DI_MINUS_LOW_AT_RETEST'

    if di_plus_at_retest > config.get('MAX_DI_PLUS_4H', 25):
        return False, 'V3_DI_PLUS_HIGH_AT_RETEST'

    if adx_at_retest < config.get('MIN_ADX_MODERATE', 21):
        return False, 'V3_ADX_WEAK_AT_RETEST'

    return True, 'V3_EMPIRICAL_VALID'
```

**Impact Estimé**:
- Win Rate: 40% → **68-72%**
- Trades: Réduction de 30-40%

---

### 4.4 V4 - Strict Filters

**État Actuel**:
- 5 filtres obligatoires: Quality≥6, Delay≤72h, STC combo, OB≥50, Blacklist
- Win Rate: 50.7%

**Compatibilité**:

V4 a déjà une structure de filtres obligatoires. Les filtres empiriques s'ajoutent naturellement:

```python
# Filtres V4 actuels
V4_MANDATORY_FILTERS = [
    ('v3_quality', '≥ 6'),
    ('tl_break_delay', '≤ 72h'),
    ('stc_has_1h', 'True'),
    ('ob_score', '≥ 50'),
    ('not_blacklisted', 'True'),
]

# + Filtres Empiriques
V4_EMPIRICAL_FILTERS = [
    ('di_minus_4h', '≥ 22'),
    ('di_plus_4h', '≤ 25'),
    ('adx_4h', '≥ 21'),
    ('vol_pct_max', '≥ 100'),
    ('pp', 'True'),
    ('ec', 'True'),
]
```

**Nouvelle Version: V4E (Enhanced)**

```python
def validate_v4e_filters(alert_data, config):
    """V4 + Filtres Empiriques"""

    # 1. V4 filters (existants)
    v4_valid, v4_reason = validate_v4_filters(alert_data, config)
    if not v4_valid:
        return False, v4_reason, 0

    # 2. Empirical filters (nouveaux)
    emp_valid, emp_reason, emp_score = check_empirical_filters(alert_data, config)
    if not emp_valid:
        return False, f'V4E_{emp_reason}', 0

    # 3. Combined score
    v4_score = alert_data.get('v4_score', 0)
    combined_score = v4_score + emp_score

    return True, 'V4E_VALID', combined_score
```

**Impact Estimé**:
- Win Rate: 50.7% → **73-77%** (selon preset)
- Trades: Réduction de 50-60%

---

### 4.5 V5 - Volume Profile

**État Actuel**:
- V4 + VP trajectory filter
- VAL support bounce required
- Win Rate: ~55%

**Intégration**:

V5 utilise le Volume Profile qui est **complémentaire** aux filtres DMI:

| V5 (VP) | Filtres Empiriques |
|---------|-------------------|
| Position par rapport POC/VAL/VAH | Seuils DI-/DI+ |
| Bounce sur VAL | Seuil ADX |
| HVN/LVN zones | Seuil Volume |

**Ordre de Filtrage Proposé**:
```
1. V4 filters
2. Empirical filters (DI-/DI+/ADX/Vol)  ← NOUVEAU
3. V5 VP trajectory
```

**Score Combiné V5E**:
```python
v5e_score = v4_score + empirical_score + vp_score
```

**Impact Estimé**:
- Win Rate: 55% → **75-80%**
- Préserve l'analyse VP pour confirmation

---

### 4.6 V6 - Timing + Momentum + Limiter

**État Actuel**:
- V4 + timing rules per TF
- Momentum filter (RSI≥40, ADX≥15)
- Entry limiter (2 max per zone)
- Win Rate: 75.5% (score 40+)

**Analyse de Redondance**:

V6 a déjà des filtres momentum qui **chevauchent** partiellement les filtres empiriques:

| V6 Actuel | Filtres Empiriques | Redondance |
|-----------|-------------------|------------|
| ADX ≥ 15 | ADX ≥ 21/35 | **Oui** - Empirique plus strict |
| RSI ≥ 40 | - | Non |
| DI spread ≥ 0 | DI- ≥ 22, DI+ ≤ 25 | **Partielle** |
| - | Vol ≥ 100% | Non |
| - | PP/EC required | Non |

**Proposition: V6E = V6 avec Filtres Empiriques Renforcés**

```python
def validate_v6e_filters(alert_data, timing_data, config):
    """V6 Enhanced avec filtres empiriques intégrés"""

    # 1. V6 timing filters (inchangés)
    timing_valid, timing_reason = validate_v6_timing(alert_data, timing_data, config)
    if not timing_valid:
        return False, timing_reason, 0

    # 2. Empirical filters (remplace les seuils faibles de V6)
    # ADX: utiliser empirique (21/35) au lieu de V6 (15)
    # DI: utiliser empirique (DI-≥22, DI+≤25) au lieu de spread simple

    di_minus = alert_data.get('di_minus_4h', 0)
    di_plus = alert_data.get('di_plus_4h', 0)
    adx = alert_data.get('adx_4h', 0)
    vol_pct = alert_data.get('vol_pct_max', 0)

    # Filtres empiriques stricts
    if di_minus < 22:
        return False, 'V6E_DI_MINUS_LOW', 0
    if di_plus > 25:
        return False, 'V6E_DI_PLUS_HIGH', 0
    if adx < 21:  # Plus strict que V6 (15)
        return False, 'V6E_ADX_WEAK', 0
    if vol_pct < 100:
        return False, 'V6E_VOL_LOW', 0

    # PP/EC obligatoires
    if not alert_data.get('pp'):
        return False, 'V6E_NO_PP', 0
    if not alert_data.get('ec'):
        return False, 'V6E_NO_EC', 0

    # 3. V6 entry limiter (inchangé)
    limiter_valid, limiter_reason = validate_v6_limiter(alert_data, config)
    if not limiter_valid:
        return False, limiter_reason, 0

    # 4. Scoring combiné
    v6_score = calculate_v6_score(alert_data, timing_data)
    empirical_bonus = calculate_empirical_bonus(alert_data)

    return True, 'V6E_VALID', v6_score + empirical_bonus
```

**Impact Estimé**:
- Win Rate: 75.5% → **78-82%** (potentiellement)
- Trades: Réduction de 20-30% supplémentaire
- Risque: Peut être trop restrictif

---

## 5. Plan d'Implémentation

### Phase 1: Préparation (1-2h)

```
1. Ajouter colonnes dans models.py:
   - di_plus_4h (Float)
   - di_minus_4h (Float)
   - dmi_spread (Float)
   - empirical_valid (Boolean)
   - empirical_score (Integer)
   - empirical_rejection (String)
   - empirical_preset (String)

2. Ajouter configuration dans engine.py DEFAULT_CONFIG

3. Créer fonctions helper dans engine.py:
   - check_empirical_filters()
   - calculate_empirical_bonus()
```

### Phase 2: Intégration V4E (2-3h)

```
1. Modifier validate_v4_filters() pour appeler check_empirical_filters()
2. Stocker les résultats dans Alert
3. Ajouter v4e_score, v4e_grade
4. Tester sur 10-20 symboles
```

### Phase 3: Intégration V5E & V6E (2-3h)

```
1. Modifier validate_v5_filters()
2. Modifier validate_v6_filters()
3. Ajuster les seuils pour éviter sur-filtrage
4. Tests complets
```

### Phase 4: Dashboard & API (1-2h)

```
1. Ajouter champs dans AlertResponse (main.py)
2. Créer endpoint /api/backtests/presets pour changer preset
3. Afficher filtres empiriques dans dashboard
4. Ajouter toggle pour activer/désactiver
```

### Phase 5: Validation (2-3h)

```
1. Backtester sur toutes les paires existantes
2. Comparer métriques V4 vs V4E, V5 vs V5E, V6 vs V6E
3. Ajuster seuils si nécessaire
4. Documenter les résultats
```

**Temps Total Estimé: 8-13 heures**

---

## 6. Impact Attendu

### Métriques Comparatives

| Version | Win Rate Actuel | Win Rate Estimé | Trades (%) | Big Winners |
|---------|-----------------|-----------------|------------|-------------|
| V1 | 35% | 55% | 30% | +50% |
| V2 | 45% | 65-70% | 25% | +40% |
| V3 | 40% | 68-72% | 35% | +45% |
| V4 | 50.7% | **73-77%** | 20% | +30% |
| V5 | 55% | **75-80%** | 18% | +35% |
| V6 | 75.5% | **78-82%** | 15% | +25% |

### Graphique d'Amélioration

```
Win Rate (%)
  85 │                              ┌───┐
     │                         ┌────┤V6E│
  80 │                    ┌────┤    └───┘
     │               ┌────┤V5E │
  75 │          ┌────┤V4E │    │    ┌───┐
     │          │    └────┘    │    │V6 │
  70 │     ┌────┤              │    └───┘
     │     │    │         ┌────┘
  65 │     │    │         │
     │┌────┤V2E │         │    ┌───┐
  60 ││    └────┘         │    │V5 │
     ││                   │    └───┘
  55 ││V1E           ┌────┘
     ││              │         ┌───┐
  50 │└──────────────┤         │V4 │
     │               │         └───┘
  45 │          ┌────┘    ┌───┐
     │          │         │V2 │
  40 │     ┌────┘         └───┘
     │     │         ┌───┐
  35 │┌────┤         │V3 │
     ││V1  │         └───┘
  30 │└────┘
     └────────────────────────────────────
       Avant              Après
```

---

## 7. Risques et Considérations

### 7.1 Risque de Sur-Filtrage

**Problème**: Trop de filtres = trop peu de trades = échantillon non significatif

**Mitigation**:
```python
# Ajouter un mode "flexible" qui relâche les seuils
FLEXIBLE_MODE = {
    'MIN_DI_MINUS_4H': 18,  # -4 du seuil strict
    'MAX_DI_PLUS_4H': 28,   # +3 du seuil strict
    'MIN_ADX_MODERATE': 18, # -3 du seuil strict
    'MIN_VOL_PCT': 80,      # -20% du seuil strict
}
```

### 7.2 Risque de Perte de Big Winners

**Problème**: Les filtres stricts peuvent exclure des trades +30%+

**Analyse des données**:
- Big Winners avec ADX < 21: 8/12 (67%)
- Big Winners avec DI+ > 25: 4/12 (33%)

**Mitigation**:
- Utiliser le preset `big_winners` par défaut
- Ne pas utiliser `max_wr` sauf pour trading très conservateur

### 7.3 Risque de Non-Stationnarité

**Problème**: Les seuils optimaux peuvent changer avec les conditions de marché

**Mitigation**:
```python
# Réentraînement périodique
def recalibrate_thresholds(recent_outcomes, lookback_days=30):
    """
    Recalibre les seuils basé sur les résultats récents.
    """
    # Analyser les trades des 30 derniers jours
    # Ajuster les seuils si nécessaire
    pass
```

### 7.4 Considérations de Performance

**Impact sur temps de backtest**:
- Calcul DI+/DI-/ADX: Déjà fait (pas d'impact)
- Check des seuils: ~1ms par alerte
- Impact global: **Négligeable**

---

## 8. Recommandations

### 8.1 Ordre de Priorité

1. **Implémenter V4E en premier** (meilleur ratio effort/résultat)
2. Puis V5E (si VP est utilisé)
3. Puis V6E (si timing est critique)
4. V1E/V2E/V3E en dernier (moins utilisés)

### 8.2 Configuration Recommandée par Défaut

```python
RECOMMENDED_CONFIG = {
    'DMI_FILTER_ENABLED': True,
    'VOL_FILTER_ENABLED': True,
    'ADX_FILTER_ENABLED': True,
    'REQUIRE_PP': True,
    'REQUIRE_EC': True,

    # Preset "big_winners" par défaut
    # Balance entre WR (73%) et capture des gros gains
    'FILTER_PRESET': 'big_winners',

    'MIN_DI_MINUS_4H': 22.0,
    'MAX_DI_PLUS_4H': 25.0,
    'MIN_ADX_MODERATE': 21.0,
    'MIN_VOL_PCT': 100.0,
}
```

### 8.3 Options de Presets dans le Dashboard

```
┌─────────────────────────────────────────────────┐
│ Preset de Filtres Empiriques                    │
├─────────────────────────────────────────────────┤
│ ○ Max Win Rate (77% WR, très sélectif)         │
│   DI-≥22, DI+≤25, ADX≥35, Vol≥100%             │
│                                                 │
│ ○ Balanced (75% WR, équilibré)                 │
│   DI-≥22, DI+≤20, ADX≥21, Vol≥100%             │
│                                                 │
│ ● Big Winners (73% WR, garde gros gains)       │
│   DI-≥22, DI+≤25, ADX≥21, Vol≥100%             │
│                                                 │
│ ○ Désactivé (filtres empiriques off)           │
└─────────────────────────────────────────────────┘
```

### 8.4 Monitoring Post-Implémentation

```python
# Métriques à tracker
MONITORING_METRICS = [
    'empirical_rejection_rate',   # % de rejets par filtre empirique
    'empirical_wr_impact',        # Différence WR avant/après
    'big_winners_captured_pct',   # % de gros gagnants conservés
    'false_rejection_rate',       # Trades rejetés qui auraient été gagnants
    'false_acceptance_rate',      # Trades acceptés qui ont perdu
]
```

---

## Annexes

### A. Schéma des Colonnes à Ajouter (models.py)

```python
class Alert(Base):
    __tablename__ = 'alerts'

    # ... colonnes existantes ...

    # === FILTRES EMPIRIQUES ===
    di_plus_4h = Column(Float)
    di_minus_4h = Column(Float)
    dmi_spread_4h = Column(Float)
    adx_4h_value = Column(Float)  # Renommer si conflit
    vol_pct_max = Column(Float)

    # Résultats du filtre
    empirical_valid = Column(Boolean, default=False)
    empirical_score = Column(Integer, default=0)
    empirical_rejection = Column(String(50))
    empirical_preset = Column(String(20))

    # Détails
    empirical_di_minus_pass = Column(Boolean)
    empirical_di_plus_pass = Column(Boolean)
    empirical_adx_pass = Column(Boolean)
    empirical_vol_pass = Column(Boolean)
    empirical_pp_pass = Column(Boolean)
    empirical_ec_pass = Column(Boolean)
```

### B. Code Complet de la Fonction de Filtrage

Voir section 3.2 pour l'implémentation complète.

### C. Requêtes SQL pour Analyse

```sql
-- Win Rate par preset
SELECT
    empirical_preset,
    COUNT(*) as total,
    SUM(CASE WHEN max_profit_pct >= 5 THEN 1 ELSE 0 END) as wins,
    ROUND(100.0 * SUM(CASE WHEN max_profit_pct >= 5 THEN 1 ELSE 0 END) / COUNT(*), 1) as win_rate
FROM alerts
WHERE empirical_valid = 1
GROUP BY empirical_preset;

-- Trades rejetés qui auraient été gagnants
SELECT
    empirical_rejection,
    COUNT(*) as total,
    SUM(CASE WHEN max_profit_pct >= 5 THEN 1 ELSE 0 END) as would_have_won
FROM alerts
WHERE empirical_valid = 0
GROUP BY empirical_rejection
ORDER BY would_have_won DESC;
```

---

**Fin du Document**

*Ce document sera mis à jour après l'implémentation et les tests.*
