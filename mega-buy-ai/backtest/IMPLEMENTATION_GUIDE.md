# GUIDE D'IMPLÉMENTATION - OPTIMISATION MEGA BUY AI

**Date**: 2026-03-01
**Basé sur**: 249 trades analysés sur 75 paires
**Objectif**: Augmenter le Win Rate de 47% vers 65-75%

---

## TABLE DES MATIÈRES

1. [Résumé Exécutif](#1-résumé-exécutif)
2. [Filtres CRITIQUES (Priorité 1)](#2-filtres-critiques-priorité-1)
3. [Filtres IMPORTANTS (Priorité 2)](#3-filtres-importants-priorité-2)
4. [Système de Scoring Bonus](#4-système-de-scoring-bonus)
5. [Modifications du Code](#5-modifications-du-code)
6. [Impact Estimé](#6-impact-estimé)
7. [Checklist d'Implémentation](#7-checklist-dimplémentation)

---

## 1. RÉSUMÉ EXÉCUTIF

### Performance Actuelle (Sans Filtres)
| Métrique | Valeur |
|----------|--------|
| Total Trades | 249 |
| Win Rate | **47.0%** |
| Profit Factor | 1.87 |
| Avg Win | +15.31% |
| Avg Loss | -7.26% |

### Performance Estimée (Avec Filtres)
| Métrique | Valeur |
|----------|--------|
| Trades Estimés | ~80-100 |
| Win Rate | **65-75%** |
| Profit Factor | 3.0-4.0 |
| Amélioration | +40% WR |

### Principe Clé
> **QUALITÉ > QUANTITÉ**
> Mieux vaut 80 trades à 70% WR que 249 trades à 47% WR

---

## 2. FILTRES CRITIQUES (Priorité 1)

Ces filtres DOIVENT être implémentés en priorité car ils ont le plus grand impact.

### 2.1 FILTRE: Fibonacci 4H > 1H + ETH BOTH

| Statistique | Valeur |
|-------------|--------|
| Win Rate | **0%** |
| Trades affectés | 11 |
| Impact | Évite 11 LOSSES certaines |

**Règle**: REJETER si `fib_4h_count > fib_1h_count` ET `eth_corr_1h = TRUE` ET `eth_corr_4h = TRUE`

```python
# FILTRE COMBO MORTEL
def check_combo_mortel(fib_levels_1h, fib_levels_4h, eth_1h, eth_4h):
    count_1h = sum(1 for lvl in fib_levels_1h.values() if lvl.get('break'))
    count_4h = sum(1 for lvl in fib_levels_4h.values() if lvl.get('break'))

    if count_4h > count_1h and eth_1h and eth_4h:
        return False, "REJECTED_COMBO_MORTEL"
    return True, "OK"
```

---

### 2.2 FILTRE: RSI Multi-Timeframe (MTF)

| Statistique | Valeur |
|-------------|--------|
| Win Rate avec RSI MTF | **83.3%** |
| Win Rate sans RSI MTF | ~40% |
| Impact | +40% WR |

**Règle**: PRÉFÉRER les trades où `rsi_mtf_bonus = TRUE`

```python
# FILTRE RSI MTF - CRITIQUE
def check_rsi_mtf(rsi_mtf_bonus):
    if not rsi_mtf_bonus:
        return False, "REJECTED_RSI_MTF_FALSE"
    return True, "OK"
```

**Note**: Ce filtre est le PLUS IMPORTANT. 83.3% WR est exceptionnel.

---

### 2.3 FILTRE: ADX WEAK

| Statistique | Valeur |
|-------------|--------|
| Win Rate ADX WEAK | **32.6%** |
| Win Rate ADX STRONG | **57.0%** |
| Trades affectés | 86 |

**Règle**: REJETER si `adx_strength_1h = "WEAK"`

```python
# FILTRE ADX - REJETER WEAK
def check_adx_strength(adx_strength_1h):
    if adx_strength_1h == "WEAK":
        return False, "REJECTED_ADX_WEAK"
    return True, "OK"
```

---

### 2.4 FILTRE: Timeframe 1H Seul

| Statistique | Valeur |
|-------------|--------|
| Win Rate 1H seul | **38.9%** |
| Win Rate 30m | **52.7%** |
| P&L moyen 1H seul | **-0.41%** |

**Règle**: REJETER si le combo timeframe est uniquement "1h"

```python
# FILTRE TIMEFRAME - REJETER 1H SEUL
def check_timeframe_combo(combo_tfs):
    if combo_tfs == "1h" or combo_tfs == "1h seul":
        return False, "REJECTED_1H_ALONE"
    return True, "OK"
```

---

### 2.5 FILTRE: Fibonacci 4H > 1H (Sans ETH)

| Statistique | Valeur |
|-------------|--------|
| Win Rate Fib 4H > 1H | **5.9%** |
| Win Rate Fib 1H > 4H | **93.3%** |
| Trades affectés | 17 |

**Règle**: REJETER si `fib_4h_count > fib_1h_count`

```python
# FILTRE FIBONACCI RELATION
def check_fib_relation(fib_levels_1h, fib_levels_4h):
    count_1h = sum(1 for lvl in fib_levels_1h.values() if lvl.get('break'))
    count_4h = sum(1 for lvl in fib_levels_4h.values() if lvl.get('break'))

    if count_4h > count_1h:
        return False, "REJECTED_FIB_4H_HIGHER"
    return True, "OK"
```

---

### 2.6 FILTRE: Bonus Count Minimum

| Bonus Count | Win Rate | Action |
|-------------|----------|--------|
| 6 | 28.6% | REJETER |
| 7 | 25.0% | REJETER |
| 8+ | 50%+ | ACCEPTER |

**Règle**: REJETER si `bonus_count < 8`

```python
# FILTRE BONUS COUNT
def check_bonus_count(bonus_count):
    if bonus_count < 8:
        return False, "REJECTED_LOW_BONUS"
    return True, "OK"
```

---

### 2.7 FILTRE: StochRSI 1H

| Statistique | Valeur |
|-------------|--------|
| Win Rate StochRSI 1H TRUE | **34.4%** |
| Win Rate StochRSI 1H FALSE | ~50% |

**Règle**: REJETER si `stoch_rsi_bonus_1h = TRUE`

```python
# FILTRE STOCHRSI 1H - CONTRE-INTUITIF!
def check_stoch_rsi_1h(stoch_rsi_bonus_1h):
    if stoch_rsi_bonus_1h:
        return False, "REJECTED_STOCHRSI_1H"
    return True, "OK"
```

---

## 3. FILTRES IMPORTANTS (Priorité 2)

Ces filtres améliorent les performances mais sont moins critiques.

### 3.1 FILTRE: Fib 5 niveaux 4H

| Statistique | Valeur |
|-------------|--------|
| Win Rate 5 niveaux 4H | **10%** |
| Trades affectés | 10 |

**Règle**: REJETER si 5 niveaux Fib 4H sont cassés

```python
# FILTRE FIB 4H SATURÉ
def check_fib_4h_saturation(fib_levels_4h):
    count_4h = sum(1 for lvl in fib_levels_4h.values() if lvl.get('break'))
    if count_4h >= 5:
        return False, "REJECTED_FIB_4H_SATURATED"
    return True, "OK"
```

---

### 3.2 FILTRE: Fib 0 niveau 1H

| Statistique | Valeur |
|-------------|--------|
| Win Rate 0 niveau 1H | **0%** |
| Trades affectés | 7 |

**Règle**: REJETER si aucun niveau Fib 1H n'est cassé

```python
# FILTRE FIB 1H VIDE
def check_fib_1h_empty(fib_levels_1h):
    count_1h = sum(1 for lvl in fib_levels_1h.values() if lvl.get('break'))
    if count_1h == 0:
        return False, "REJECTED_FIB_1H_EMPTY"
    return True, "OK"
```

---

### 3.3 FILTRE: BTC Correlation 4H Seul

| Statistique | Valeur |
|-------------|--------|
| Win Rate BTC 4H seul | **35.6%** |

**Règle**: ATTENTION si `btc_corr_4h = TRUE` et `btc_corr_1h = FALSE`

```python
# FILTRE BTC CORRELATION (optionnel)
def check_btc_correlation(btc_1h, btc_4h):
    if btc_4h and not btc_1h:
        return "WARNING", "BTC_4H_ONLY_RISK"
    return True, "OK"
```

---

## 4. SYSTÈME DE SCORING BONUS

### 4.1 Bonus Positifs (Ajouter des points)

| Condition | Points | Win Rate | Justification |
|-----------|--------|----------|---------------|
| Fib 1H > Fib 4H | **+5** | 93.3% | Meilleur indicateur Fib |
| RSI MTF = TRUE | **+5** | 83.3% | Indicateur le plus fiable |
| EMA Stack 4H = TRUE | **+4** | 81.2% | Très fort |
| ETH 4H ONLY (sans 1H) | **+3** | 66.7% | Excellent signal |
| ETH Trend 1H = NEUTRAL | **+3** | 58.3% | Bon contexte |
| BTC Trend 1H = BEARISH | **+3** | 59.6% | Recovery play |
| ADX 1H = STRONG | **+2** | 57.0% | Force confirmée |
| Vol Spike 4H = TRUE | **+2** | 53.8% | Volume confirmé |
| Fib aligné 2=2 | **+2** | 59.6% | Sweet spot |
| Score MEGA BUY = 10/10 | **+2** | 56.9% | Fiable |

### 4.2 Malus (Retirer des points)

| Condition | Points | Win Rate | Justification |
|-----------|--------|----------|---------------|
| Fib 4H > Fib 1H | **-10** | 5.9% | Quasi certain de perdre |
| StochRSI 1H = TRUE | **-5** | 34.4% | Pire filtre |
| ADX 1H = WEAK | **-5** | 32.6% | Tendance faible |
| ETH BOTH TRUE | **-3** | 41.2% | Mauvais signal |
| ETH Trend 1H = BULLISH | **-2** | 42.4% | Moins performant |
| Bonus Count 6-7 | **-5** | 25-28% | Danger |
| Timeframe 1H seul | **-8** | 38.9% | À éviter |
| Score 9/10 | **-2** | 39.3% | Instable |

### 4.3 Implémentation du Scoring

```python
def calculate_trade_score(trade_data):
    score = 0

    # === BONUS POSITIFS ===

    # Fibonacci relation (TRÈS IMPORTANT)
    fib_1h = count_fib_levels(trade_data['fib_levels_1h'])
    fib_4h = count_fib_levels(trade_data['fib_levels_4h'])
    if fib_1h > fib_4h:
        score += 5  # 93.3% WR

    # RSI MTF (CRITIQUE)
    if trade_data.get('rsi_mtf_bonus'):
        score += 5  # 83.3% WR

    # EMA Stack 4H
    if trade_data.get('ema_stack_bonus_4h'):
        score += 4  # 81.2% WR

    # ETH Correlation
    eth_1h = trade_data.get('eth_corr_bonus_1h')
    eth_4h = trade_data.get('eth_corr_bonus_4h')
    if eth_4h and not eth_1h:
        score += 3  # 66.7% WR (ETH 4H ONLY)

    # ETH Trend 1H
    if trade_data.get('eth_trend_1h') == "NEUTRAL":
        score += 3  # 58.3% WR

    # BTC Trend 1H
    if trade_data.get('btc_trend_1h') == "BEARISH":
        score += 3  # 59.6% WR

    # ADX Strength
    if trade_data.get('adx_strength_1h') == "STRONG":
        score += 2  # 57% WR

    # Vol Spike 4H
    if trade_data.get('vol_spike_bonus_4h'):
        score += 2  # 53.8% WR

    # Fib aligné 2=2
    if fib_1h == fib_4h == 2:
        score += 2  # 59.6% WR

    # Score MEGA BUY
    if trade_data.get('mega_buy_score') == 10:
        score += 2  # 56.9% WR

    # === MALUS ===

    # Fibonacci relation inverse (CRITIQUE)
    if fib_4h > fib_1h:
        score -= 10  # 5.9% WR

    # StochRSI 1H (PIRE FILTRE)
    if trade_data.get('stoch_rsi_bonus_1h'):
        score -= 5  # 34.4% WR

    # ADX WEAK
    if trade_data.get('adx_strength_1h') == "WEAK":
        score -= 5  # 32.6% WR

    # ETH BOTH TRUE
    if eth_1h and eth_4h:
        score -= 3  # 41.2% WR

    # ETH Trend 1H BULLISH
    if trade_data.get('eth_trend_1h') == "BULLISH":
        score -= 2  # 42.4% WR

    # Bonus Count faible
    bonus_count = trade_data.get('bonus_count', 0)
    if bonus_count in [6, 7]:
        score -= 5  # 25-28% WR

    # Timeframe 1H seul
    if trade_data.get('combo_tfs') == "1h":
        score -= 8  # 38.9% WR

    # Score 9/10
    if trade_data.get('mega_buy_score') == 9:
        score -= 2  # 39.3% WR

    return score

def get_trade_recommendation(score):
    if score >= 10:
        return "STRONG_BUY", "Excellente configuration"
    elif score >= 5:
        return "BUY", "Bonne configuration"
    elif score >= 0:
        return "NEUTRAL", "Configuration moyenne"
    elif score >= -5:
        return "AVOID", "Configuration risquée"
    else:
        return "REJECT", "Configuration dangereuse"
```

---

## 5. MODIFICATIONS DU CODE

### 5.1 Fichier: `engine.py`

#### A. Ajouter la fonction de validation globale

```python
def validate_trade_entry(alert_data):
    """
    Valide un trade avant entrée avec tous les filtres critiques.
    Retourne (is_valid, rejection_reason, score)
    """

    # Extraire les données Fibonacci
    fib_1h = json.loads(alert_data.get('fib_levels_1h', '{}'))
    fib_4h = json.loads(alert_data.get('fib_levels', '{}'))
    count_1h = sum(1 for lvl in fib_1h.values() if lvl.get('break'))
    count_4h = sum(1 for lvl in fib_4h.values() if lvl.get('break'))

    # ETH Correlation
    eth_1h = alert_data.get('eth_corr_bonus_1h', False)
    eth_4h = alert_data.get('eth_corr_bonus_4h', False)

    # === FILTRES CRITIQUES (REJETS) ===

    # 1. Combo Mortel: Fib 4H > 1H + ETH BOTH (0% WR)
    if count_4h > count_1h and eth_1h and eth_4h:
        return False, "REJECTED_COMBO_MORTEL", -999

    # 2. Fib 4H > 1H (5.9% WR)
    if count_4h > count_1h:
        return False, "REJECTED_FIB_4H_HIGHER", -100

    # 3. ADX WEAK (32.6% WR)
    if alert_data.get('adx_strength_1h') == "WEAK":
        return False, "REJECTED_ADX_WEAK", -50

    # 4. StochRSI 1H TRUE (34.4% WR)
    if alert_data.get('stoch_rsi_bonus_1h'):
        return False, "REJECTED_STOCHRSI_1H", -50

    # 5. Timeframe 1H seul (38.9% WR)
    combo_tfs = alert_data.get('combo_tfs', '')
    if combo_tfs == "1h" or combo_tfs.strip() == "1h":
        return False, "REJECTED_1H_ALONE", -80

    # 6. Bonus Count < 8 (25-28% WR)
    bonus_count = count_bonus_filters(alert_data)
    if bonus_count < 8:
        return False, "REJECTED_LOW_BONUS", -50

    # 7. Fib 4H saturé (10% WR)
    if count_4h >= 5:
        return False, "REJECTED_FIB_4H_SATURATED", -100

    # 8. Fib 1H vide (0% WR)
    if count_1h == 0:
        return False, "REJECTED_FIB_1H_EMPTY", -100

    # === CALCUL DU SCORE ===
    score = calculate_trade_score(alert_data)

    # Rejet si score trop négatif
    if score < -5:
        return False, "REJECTED_LOW_SCORE", score

    return True, "VALIDATED", score
```

#### B. Modifier la fonction `run_backtest`

Ajouter la validation avant chaque entrée:

```python
# Dans run_backtest(), après avoir trouvé une entrée potentielle:

# Valider le trade avec les nouveaux filtres
is_valid, rejection_reason, trade_score = validate_trade_entry(alert_data)

if not is_valid:
    # Enregistrer le rejet
    alert_data['status'] = rejection_reason
    alert_data['trade_score'] = trade_score
    stats['rejected_by_filters'] += 1
    stats[f'rejected_{rejection_reason.lower()}'] = stats.get(f'rejected_{rejection_reason.lower()}', 0) + 1
    continue  # Passer au prochain signal

# Enregistrer le score pour les trades validés
alert_data['trade_score'] = trade_score
```

---

### 5.2 Fichier: `page.tsx` (Dashboard)

#### A. Ajouter l'affichage du score de trade

```typescript
// Dans la section des résultats de trade
{trade.trade_score !== undefined && (
  <div className={`px-2 py-1 rounded text-sm ${
    trade.trade_score >= 10 ? 'bg-green-500/20 text-green-400' :
    trade.trade_score >= 5 ? 'bg-blue-500/20 text-blue-400' :
    trade.trade_score >= 0 ? 'bg-yellow-500/20 text-yellow-400' :
    'bg-red-500/20 text-red-400'
  }`}>
    Score: {trade.trade_score}
  </div>
)}
```

#### B. Ajouter les statistiques de rejet

```typescript
// Dans le résumé du backtest
<div className="grid grid-cols-2 gap-4">
  <div>
    <h4>Rejets par Filtre:</h4>
    {backtest.rejected_combo_mortel > 0 && (
      <p>Combo Mortel: {backtest.rejected_combo_mortel}</p>
    )}
    {backtest.rejected_fib_4h_higher > 0 && (
      <p>Fib 4H > 1H: {backtest.rejected_fib_4h_higher}</p>
    )}
    {backtest.rejected_adx_weak > 0 && (
      <p>ADX Weak: {backtest.rejected_adx_weak}</p>
    )}
    {/* ... autres rejets ... */}
  </div>
</div>
```

---

### 5.3 Fichier: `config.py`

Ajouter les constantes de configuration:

```python
# === FILTRES DE VALIDATION ===

# Fibonacci
FIB_REJECT_4H_HIGHER = True  # Rejeter si Fib 4H > 1H
FIB_REJECT_4H_SATURATED = True  # Rejeter si 5 niveaux 4H
FIB_REJECT_1H_EMPTY = True  # Rejeter si 0 niveau 1H

# ADX
ADX_REJECT_WEAK = True  # Rejeter ADX WEAK

# StochRSI
STOCHRSI_REJECT_1H_TRUE = True  # Rejeter StochRSI 1H TRUE

# Bonus
MIN_BONUS_COUNT = 8  # Minimum de bonus requis

# Timeframe
REJECT_1H_ALONE = True  # Rejeter 1H seul

# ETH Correlation
REJECT_COMBO_MORTEL = True  # Rejeter Fib 4H>1H + ETH BOTH

# RSI MTF
PREFER_RSI_MTF = True  # Préférer RSI MTF TRUE

# Scoring
MIN_TRADE_SCORE = -5  # Score minimum pour valider un trade

# === POIDS DU SCORING ===
SCORE_WEIGHTS = {
    'fib_1h_higher': 5,
    'rsi_mtf': 5,
    'ema_stack_4h': 4,
    'eth_4h_only': 3,
    'eth_trend_neutral': 3,
    'btc_trend_bearish': 3,
    'adx_strong': 2,
    'vol_spike_4h': 2,
    'fib_aligned_2': 2,
    'score_10': 2,
    # Malus
    'fib_4h_higher': -10,
    'stochrsi_1h': -5,
    'adx_weak': -5,
    'eth_both': -3,
    'eth_bullish': -2,
    'low_bonus': -5,
    '1h_alone': -8,
    'score_9': -2,
}
```

---

## 6. IMPACT ESTIMÉ

### 6.1 Trades Éliminés par Filtre

| Filtre | Trades Rejetés | WR Évité | Impact |
|--------|----------------|----------|--------|
| Combo Mortel | 11 | 0% | +11 losses évitées |
| Fib 4H > 1H | 17 | 5.9% | +16 losses évitées |
| ADX WEAK | 86 | 32.6% | +58 losses évitées |
| StochRSI 1H | 32 | 34.4% | +21 losses évitées |
| 1H seul | 95 | 38.9% | +58 losses évitées |
| Bonus < 8 | ~25 | 25-28% | +18 losses évitées |

**Note**: Certains filtres se chevauchent, donc le total n'est pas additif.

### 6.2 Estimation Finale

| Métrique | Avant | Après | Amélioration |
|----------|-------|-------|--------------|
| Trades | 249 | **~80-100** | -60% |
| Win Rate | 47% | **65-75%** | +20-28% |
| Profit Factor | 1.87 | **3.0-4.5** | +60-140% |
| Avg Trade PnL | +3.34% | **+10-15%** | +200-350% |
| Losses Évitées | 0 | **~100-120** | - |

### 6.3 Comparaison Profit

**Avant (249 trades à 47% WR):**
- Wins: 117 × +15.31% = +1,791%
- Losses: 132 × -7.26% = -958%
- **Net: +833%**

**Après (90 trades à 70% WR estimé):**
- Wins: 63 × +15.31% = +965%
- Losses: 27 × -7.26% = -196%
- **Net: +769%**

> Moins de profit total MAIS avec beaucoup moins de risque et un capital mieux préservé.

---

## 7. CHECKLIST D'IMPLÉMENTATION

### Phase 1: Filtres Critiques (Priorité HAUTE)

- [ ] Implémenter filtre Combo Mortel (Fib 4H>1H + ETH BOTH)
- [ ] Implémenter filtre Fib 4H > 1H
- [ ] Implémenter filtre ADX WEAK
- [ ] Implémenter filtre StochRSI 1H TRUE
- [ ] Implémenter filtre 1H seul
- [ ] Implémenter filtre Bonus Count < 8
- [ ] Tester chaque filtre individuellement

### Phase 2: Filtres Secondaires (Priorité MOYENNE)

- [ ] Implémenter filtre Fib 4H saturé (5 niveaux)
- [ ] Implémenter filtre Fib 1H vide
- [ ] Implémenter filtre BTC 4H seul (warning)
- [ ] Ajouter les compteurs de rejet dans les stats

### Phase 3: Système de Scoring (Priorité MOYENNE)

- [ ] Implémenter la fonction `calculate_trade_score()`
- [ ] Ajouter tous les bonus positifs
- [ ] Ajouter tous les malus
- [ ] Afficher le score dans le dashboard
- [ ] Ajouter le seuil minimum de score

### Phase 4: Dashboard Updates (Priorité BASSE)

- [ ] Afficher les rejets par type
- [ ] Afficher le score de chaque trade
- [ ] Ajouter des graphiques de distribution des scores
- [ ] Ajouter un filtre pour voir les trades par score

### Phase 5: Validation (CRITIQUE)

- [ ] Re-run tous les backtests avec les nouveaux filtres
- [ ] Comparer les résultats avec les estimations
- [ ] Ajuster les seuils si nécessaire
- [ ] Documenter les changements de performance

---

## ANNEXE A: RÉSUMÉ DES RÈGLES

### REJETS AUTOMATIQUES (Ne jamais entrer)

| # | Condition | Win Rate |
|---|-----------|----------|
| 1 | Fib 4H > Fib 1H + ETH BOTH TRUE | 0% |
| 2 | Fib 4H > Fib 1H | 5.9% |
| 3 | 5 niveaux Fib 4H | 10% |
| 4 | 0 niveau Fib 1H | 0% |
| 5 | ADX 1H = WEAK | 32.6% |
| 6 | StochRSI 1H = TRUE | 34.4% |
| 7 | Timeframe = 1H seul | 38.9% |
| 8 | Bonus Count < 8 | 25-28% |

### SIGNAUX FORTS (Privilégier)

| # | Condition | Win Rate |
|---|-----------|----------|
| 1 | Fib 1H > Fib 4H | 93.3% |
| 2 | RSI MTF = TRUE | 83.3% |
| 3 | EMA Stack 4H = TRUE | 81.2% |
| 4 | ETH 4H ONLY | 66.7% |
| 5 | BTC Trend 1H = BEARISH | 59.6% |
| 6 | ETH Trend 1H = NEUTRAL | 58.3% |
| 7 | ADX 1H = STRONG | 57.0% |

---

## ANNEXE B: FORMULE DE SCORE FINALE

```
SCORE = (
    + 5 × (fib_1h > fib_4h)
    + 5 × rsi_mtf
    + 4 × ema_stack_4h
    + 3 × eth_4h_only
    + 3 × (eth_trend_1h == "NEUTRAL")
    + 3 × (btc_trend_1h == "BEARISH")
    + 2 × (adx_1h == "STRONG")
    + 2 × vol_spike_4h
    + 2 × (fib_1h == fib_4h == 2)
    + 2 × (score == 10)
    - 10 × (fib_4h > fib_1h)
    - 5 × stochrsi_1h
    - 5 × (adx_1h == "WEAK")
    - 3 × (eth_1h AND eth_4h)
    - 2 × (eth_trend_1h == "BULLISH")
    - 5 × (bonus_count in [6, 7])
    - 8 × (combo_tfs == "1h")
    - 2 × (score == 9)
)

DECISION:
- SCORE >= 10: STRONG BUY
- SCORE >= 5: BUY
- SCORE >= 0: NEUTRAL
- SCORE >= -5: AVOID
- SCORE < -5: REJECT
```

---

*Document généré le 2026-03-01*
*Basé sur l'analyse de 249 trades sur 75 paires*
*MEGA BUY AI - Guide d'Optimisation v1.0*
