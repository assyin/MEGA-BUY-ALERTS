# MEGA BUY V6 - Rapport d'Implementation

## Executive Summary

La version V6 introduit un système de filtrage intelligent basé sur l'analyse combinée de **184 trades** réels. Les améliorations ciblent les 3 problèmes majeurs identifiés:

| Problème | Impact actuel | Solution V6 |
|----------|---------------|-------------|
| Trades avec momentum insuffisant | 27% TP1 hit rate (losers) | Filtre Momentum Score |
| Timing inapproprié (15m slow) | 25-28% WR | Filtre Timing Dynamique |
| Entrées multiples sur même mouvement | -21% P&L FETUSDT | Limite entries par breakout |

**Impact attendu V6**: Win Rate +12-15%, Profit Factor x2.5

---

## 1. ARCHITECTURE V6

```
V6 = V5 + Timing Filters + Momentum Filters + Entry Limiter + Combined Scoring

┌─────────────────────────────────────────────────────────────────┐
│                         MEGA BUY SIGNAL                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PREREQUIS (existants)                        │
│  • STC Oversold on 15m/30m/1h                                   │
│  • Not 15m alone                                                │
│  • Trendline exists                                             │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                 V6 TIMING FILTER (NOUVEAU)                      │
│  • 15m: Reject if retest > 24h OR entry > 48h                   │
│  • 1h: Warn if retest 6-24h (47% WR zone)                       │
│  • All: Reject if distance > 20%                                │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                V6 MOMENTUM FILTER (NOUVEAU)                     │
│  • Min estimated potential: 10%                                 │
│  • RSI 1H > 50 at entry                                         │
│  • ADX > 20 (trend strength)                                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              V6 ENTRY LIMITER (NOUVEAU)                         │
│  • Max 2 entries per breakout zone (±2%)                        │
│  • Cooldown 6h between entries same pair                        │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│              V6 COMBINED SCORING (NOUVEAU)                      │
│  • Score 40+ = EXCELLENT (75.5% WR)                             │
│  • Score 25-39 = GOOD (67.4% WR)                                │
│  • Score 10-24 = MEDIUM (63.0% WR)                              │
│  • Score <10 = POOR → REJECT                                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
                          ENTRY V6
```

---

## 2. NOUVEAUX FILTRES V6

### 2.1 V6 Timing Filter

**Justification**: L'analyse montre que le timing est crucial, surtout pour le 15m.

```python
# Configuration V6 Timing
'V6_TIMING_FILTER_ENABLED': True,

# 15m Timing Rules (strict)
'V6_15M_MAX_RETEST_HOURS': 24,      # Retest > 24h = 41.7% WR → REJECT
'V6_15M_MAX_ENTRY_HOURS': 48,       # Entry > 48h = 28.6% WR → REJECT
'V6_15M_OPTIMAL_RETEST_HOURS': 6,   # 0-6h = 76.5% WR = FAST bonus

# 30m Timing Rules (flexible)
'V6_30M_MAX_RETEST_HOURS': 72,      # 30m robust même avec slow retest (66.7% WR)
'V6_30M_MAX_ENTRY_HOURS': 72,       # Plus flexible
'V6_30M_OPTIMAL_RETEST_HOURS': 6,   # 0-6h = 76.2% WR = FAST bonus

# 1h Timing Rules (medium)
'V6_1H_MAX_RETEST_HOURS': 72,
'V6_1H_MAX_ENTRY_HOURS': 72,
'V6_1H_WARN_RETEST_MIN': 6,         # 6-24h = 47.4% WR = WARNING zone
'V6_1H_WARN_RETEST_MAX': 24,
'V6_1H_OPTIMAL_RETEST_HOURS': 6,    # 0-6h = 72.2% WR = FAST bonus

# Distance Filter (all TFs)
'V6_MAX_DISTANCE_PCT': 20.0,        # Distance > 20% = 0% WR → REJECT
'V6_OPTIMAL_DISTANCE_MIN': 5.0,     # 5-10% = meilleur risk/reward
'V6_OPTIMAL_DISTANCE_MAX': 10.0,
```

**Règles de rejet**:
| Condition | Action | Win Rate évité |
|-----------|--------|----------------|
| 15m + Retest > 24h | REJECT | 41.7% |
| 15m + Entry > 48h | REJECT | 28.6% |
| Distance > 20% | REJECT | 0% |
| 1h + Retest 6-24h | WARNING (-10 score) | 47.4% |

---

### 2.2 V6 Momentum Filter

**Justification**: Les trades perdants ont un potentiel max de seulement 1-5%, insuffisant pour atteindre TP1.

```python
# Configuration V6 Momentum
'V6_MOMENTUM_FILTER_ENABLED': True,

# Estimated Potential Filter
'V6_MIN_ESTIMATED_POTENTIAL_PCT': 10.0,  # Potentiel estimé min 10%
'V6_POTENTIAL_LOOKBACK_BARS': 50,        # Bars pour estimer le potentiel

# RSI Momentum
'V6_RSI_MIN_AT_ENTRY': 45,               # RSI 1H min à l'entrée
'V6_RSI_BULLISH_THRESHOLD': 50,          # RSI > 50 = bonus

# ADX Trend Strength
'V6_ADX_MIN_AT_ENTRY': 20,               # ADX min = trend présent
'V6_ADX_STRONG_THRESHOLD': 25,           # ADX > 25 = trend fort = bonus

# DMI Spread
'V6_DMI_MIN_SPREAD': 5.0,                # DI+ - DI- minimum
```

**Calcul du potentiel estimé**:
```python
def estimate_profit_potential(df_4h, entry_price, lookback=50):
    """
    Estime le potentiel de profit basé sur:
    1. Résistances proches (swing highs)
    2. ATR (volatilité moyenne)
    3. Distance au prochain niveau clé
    """
    recent_high = df_4h['high'].tail(lookback).max()
    atr = calculate_atr(df_4h, 14)

    # Potentiel = distance au high récent + 1.5 ATR
    potential = (recent_high - entry_price) / entry_price * 100
    potential += (atr * 1.5) / entry_price * 100

    return potential
```

---

### 2.3 V6 Entry Limiter

**Justification**: FETUSDT a perdu -21% avec 3 entrées au même niveau de prix.

```python
# Configuration V6 Entry Limiter
'V6_ENTRY_LIMITER_ENABLED': True,

# Max entries par zone de breakout
'V6_MAX_ENTRIES_PER_ZONE': 2,            # Max 2 trades par zone ±2%
'V6_ENTRY_ZONE_PCT': 2.0,                # Zone = entry_price ± 2%

# Cooldown entre entrées
'V6_ENTRY_COOLDOWN_HOURS': 6,            # Min 6h entre 2 entrées même paire
'V6_ENTRY_COOLDOWN_AFTER_LOSS': 24,      # 24h cooldown après un loss
```

**Logique**:
```python
def check_entry_limit(symbol, entry_price, entry_time, recent_trades):
    """
    Vérifie si une nouvelle entrée est autorisée
    """
    zone_min = entry_price * 0.98
    zone_max = entry_price * 1.02

    entries_in_zone = [t for t in recent_trades
                       if t['symbol'] == symbol
                       and zone_min <= t['entry_price'] <= zone_max]

    if len(entries_in_zone) >= config['V6_MAX_ENTRIES_PER_ZONE']:
        return False, "V6_MAX_ENTRIES_ZONE"

    # Check cooldown
    last_entry = get_last_entry(symbol, recent_trades)
    if last_entry:
        hours_since = (entry_time - last_entry['time']).total_seconds() / 3600
        cooldown = config['V6_ENTRY_COOLDOWN_AFTER_LOSS'] if last_entry['pnl'] < 0 else config['V6_ENTRY_COOLDOWN_HOURS']
        if hours_since < cooldown:
            return False, "V6_ENTRY_COOLDOWN"

    return True, None
```

---

### 2.4 V6 Combined Scoring System

**Justification**: Le score combiné 40+ a un WR de 75.5% vs 53.8% pour score <10.

```python
# Configuration V6 Scoring
'V6_SCORING_ENABLED': True,
'V6_MIN_SCORE': 10,                      # Score < 10 = REJECT (53.8% WR)
'V6_EXCELLENT_SCORE': 40,                # Score 40+ = EXCELLENT (75.5% WR)
'V6_GOOD_SCORE': 25,                     # Score 25-39 = GOOD (67.4% WR)

# Composants du score
'V6_SCORE_WEIGHTS': {
    # Timing (max 30 points)
    'retest_fast': 15,                   # Retest 0-6h
    'retest_medium': 5,                  # Retest 6-24h
    'retest_slow': -10,                  # Retest > 24h
    'entry_fast': 10,                    # Entry 0-24h
    'entry_medium': 0,                   # Entry 24-48h
    'entry_slow': -10,                   # Entry > 48h

    # Distance (max 15 points)
    'distance_optimal': 15,              # Distance 5-10%
    'distance_short': 5,                 # Distance 0-5%
    'distance_long': -5,                 # Distance > 10%
    'distance_extreme': -20,             # Distance > 20%

    # Momentum (max 25 points)
    'rsi_bullish': 10,                   # RSI > 50
    'adx_strong': 10,                    # ADX > 25
    'dmi_positive': 5,                   # DI+ > DI-

    # CVD (max 15 points)
    'cvd_no_divergence': 10,             # Pas de divergence bearish
    'cvd_divergence_30m': 0,             # 30m tolère divergence
    'cvd_divergence_other': -10,         # 15m/1h divergence = malus

    # Timeframe (max 15 points)
    'tf_30m': 10,                        # 30m = meilleur WR
    'tf_1h': 5,                          # 1h = bon
    'tf_15m': 0,                         # 15m = plus risqué
}
```

**Calcul du score**:
```python
def calculate_v6_score(trade_data, config):
    score = 0
    weights = config['V6_SCORE_WEIGHTS']

    # 1. Timing Score
    retest_hours = trade_data['v3_hours_retest_vs_tl']
    if retest_hours <= 6:
        score += weights['retest_fast']
    elif retest_hours <= 24:
        score += weights['retest_medium']
    else:
        score += weights['retest_slow']

    entry_hours = trade_data['v3_hours_to_entry']
    if entry_hours <= 24:
        score += weights['entry_fast']
    elif entry_hours <= 48:
        score += weights['entry_medium']
    else:
        score += weights['entry_slow']

    # 2. Distance Score
    distance = trade_data['v3_distance_before_retest']
    if distance > 20:
        score += weights['distance_extreme']
    elif 5 <= distance <= 10:
        score += weights['distance_optimal']
    elif distance < 5:
        score += weights['distance_short']
    else:
        score += weights['distance_long']

    # 3. Momentum Score
    if trade_data['rsi_1h'] > 50:
        score += weights['rsi_bullish']
    if trade_data['adx'] > 25:
        score += weights['adx_strong']
    if trade_data['di_plus'] > trade_data['di_minus']:
        score += weights['dmi_positive']

    # 4. CVD Score
    tf = trade_data['timeframe']
    has_divergence = trade_data['cvd_bearish_divergence']
    if not has_divergence:
        score += weights['cvd_no_divergence']
    elif tf == '30m':
        score += weights['cvd_divergence_30m']
    else:
        score += weights['cvd_divergence_other']

    # 5. Timeframe Score
    if tf == '30m':
        score += weights['tf_30m']
    elif tf == '1h':
        score += weights['tf_1h']
    else:
        score += weights['tf_15m']

    return score
```

---

## 3. CONFIGURATIONS OPTIMALES PAR TIMEFRAME

### 3.1 Configuration 15m

```python
# 15m est le plus sensible au timing
'V6_15M_CONFIG': {
    'timing': 'STRICT',                  # Timing strict obligatoire
    'max_retest_hours': 24,              # Au-delà = 41.7% WR
    'max_entry_hours': 48,               # Au-delà = 28.6% WR
    'require_no_cvd_div': True,          # CVD divergence = malus
    'min_score': 30,                     # Score minimum plus élevé
    'expected_wr': '76-85%',             # Si config respectée
}
```

**Combinaison optimale 15m**:
- Retest FAST (0-6h) ✓
- Entry FAST (0-24h) ✓
- NO CVD Divergence ✓
- **Win Rate attendu: 85.7%**

### 3.2 Configuration 30m

```python
# 30m est le plus robuste
'V6_30M_CONFIG': {
    'timing': 'FLEXIBLE',                # Plus tolérant
    'max_retest_hours': 72,              # Tolère slow retest (66.7% WR)
    'max_entry_hours': 72,
    'require_no_cvd_div': False,         # 30m + CVD div = 71.4% WR
    'min_score': 15,                     # Score minimum plus bas
    'expected_wr': '67-85%',
}
```

**Combinaison optimale 30m**:
- Retest FAST (0-6h) + Distance OPT (5-10%) + Entry FAST
- **Win Rate attendu: 75-85%**

### 3.3 Configuration 1h

```python
# 1h a une zone de warning (6-24h retest)
'V6_1H_CONFIG': {
    'timing': 'MEDIUM',
    'warn_retest_range': (6, 24),        # Zone 47.4% WR = warning
    'max_retest_hours': 72,
    'max_entry_hours': 72,
    'require_no_cvd_div': True,          # 1h + CVD div = 57.1% WR
    'min_score': 25,
    'expected_wr': '60-72%',
}
```

**Combinaison optimale 1h**:
- Retest FAST (0-6h) ✓
- Entry FAST (0-24h) ✓
- **Win Rate attendu: 72%+**

---

## 4. IMPLEMENTATION TECHNIQUE

### 4.1 Nouveaux paramètres DEFAULT_CONFIG

```python
# ═══════════════════════════════════════════════════════════════════════════════
# V6 STRATEGY - Timing + Momentum + Entry Limiter + Combined Scoring
# Based on analysis of 184 trades with detailed timing/CVD/distance data
# ═══════════════════════════════════════════════════════════════════════════════
'V6_ENABLED': True,

# V6 TIMING FILTER
'V6_TIMING_FILTER_ENABLED': True,
'V6_15M_MAX_RETEST_HOURS': 24,
'V6_15M_MAX_ENTRY_HOURS': 48,
'V6_30M_MAX_RETEST_HOURS': 72,
'V6_30M_MAX_ENTRY_HOURS': 72,
'V6_1H_MAX_RETEST_HOURS': 72,
'V6_1H_MAX_ENTRY_HOURS': 72,
'V6_1H_WARN_RETEST_MIN': 6,
'V6_1H_WARN_RETEST_MAX': 24,
'V6_OPTIMAL_RETEST_HOURS': 6,
'V6_MAX_DISTANCE_PCT': 20.0,
'V6_OPTIMAL_DISTANCE_MIN': 5.0,
'V6_OPTIMAL_DISTANCE_MAX': 10.0,

# V6 MOMENTUM FILTER
'V6_MOMENTUM_FILTER_ENABLED': True,
'V6_MIN_ESTIMATED_POTENTIAL_PCT': 10.0,
'V6_RSI_MIN_AT_ENTRY': 45,
'V6_RSI_BULLISH_THRESHOLD': 50,
'V6_ADX_MIN_AT_ENTRY': 20,
'V6_ADX_STRONG_THRESHOLD': 25,
'V6_DMI_MIN_SPREAD': 5.0,

# V6 ENTRY LIMITER
'V6_ENTRY_LIMITER_ENABLED': True,
'V6_MAX_ENTRIES_PER_ZONE': 2,
'V6_ENTRY_ZONE_PCT': 2.0,
'V6_ENTRY_COOLDOWN_HOURS': 6,
'V6_ENTRY_COOLDOWN_AFTER_LOSS': 24,

# V6 COMBINED SCORING
'V6_SCORING_ENABLED': True,
'V6_MIN_SCORE': 10,
'V6_EXCELLENT_SCORE': 40,
'V6_GOOD_SCORE': 25,

# V6 SCORING WEIGHTS
'V6_SCORE_RETEST_FAST': 15,
'V6_SCORE_RETEST_MEDIUM': 5,
'V6_SCORE_RETEST_SLOW': -10,
'V6_SCORE_ENTRY_FAST': 10,
'V6_SCORE_ENTRY_SLOW': -10,
'V6_SCORE_DISTANCE_OPTIMAL': 15,
'V6_SCORE_DISTANCE_SHORT': 5,
'V6_SCORE_DISTANCE_EXTREME': -20,
'V6_SCORE_RSI_BULLISH': 10,
'V6_SCORE_ADX_STRONG': 10,
'V6_SCORE_DMI_POSITIVE': 5,
'V6_SCORE_CVD_NO_DIV': 10,
'V6_SCORE_CVD_DIV_30M': 0,
'V6_SCORE_CVD_DIV_OTHER': -10,
'V6_SCORE_TF_30M': 10,
'V6_SCORE_TF_1H': 5,
'V6_SCORE_TF_15M': 0,
```

### 4.2 Nouvelles fonctions

```python
def check_v6_timing_filter(trade_data, config):
    """
    V6 Timing Filter - Rejette les trades avec timing inapproprié
    """
    tf = trade_data['timeframe']
    retest_hours = trade_data.get('v3_hours_retest_vs_tl', 0)
    entry_hours = trade_data.get('v3_hours_to_entry', 0)
    distance = trade_data.get('v3_distance_before_retest', 0)

    # Distance filter (all TFs)
    if distance > config.get('V6_MAX_DISTANCE_PCT', 20.0):
        return False, "V6_DISTANCE_TOO_HIGH"

    # 15m strict timing
    if tf == '15m':
        if retest_hours > config.get('V6_15M_MAX_RETEST_HOURS', 24):
            return False, "V6_15M_SLOW_RETEST"
        if entry_hours > config.get('V6_15M_MAX_ENTRY_HOURS', 48):
            return False, "V6_15M_SLOW_ENTRY"

    # 30m flexible (no rejections, only scoring)

    # 1h warning zone (score malus, not rejection)

    return True, None


def check_v6_momentum_filter(trade_data, config):
    """
    V6 Momentum Filter - Rejette les trades sans momentum suffisant
    """
    if not config.get('V6_MOMENTUM_FILTER_ENABLED', True):
        return True, None

    # Check estimated potential
    potential = trade_data.get('estimated_potential', 0)
    if potential < config.get('V6_MIN_ESTIMATED_POTENTIAL_PCT', 10.0):
        return False, "V6_LOW_POTENTIAL"

    # Check RSI
    rsi = trade_data.get('rsi_1h', 50)
    if rsi < config.get('V6_RSI_MIN_AT_ENTRY', 45):
        return False, "V6_RSI_TOO_LOW"

    # Check ADX
    adx = trade_data.get('adx', 0)
    if adx < config.get('V6_ADX_MIN_AT_ENTRY', 20):
        return False, "V6_ADX_TOO_LOW"

    return True, None


def check_v6_entry_limiter(symbol, entry_price, entry_time, recent_trades, config):
    """
    V6 Entry Limiter - Limite les entrées multiples sur même zone
    """
    if not config.get('V6_ENTRY_LIMITER_ENABLED', True):
        return True, None

    zone_pct = config.get('V6_ENTRY_ZONE_PCT', 2.0)
    zone_min = entry_price * (1 - zone_pct/100)
    zone_max = entry_price * (1 + zone_pct/100)

    # Count entries in zone
    entries_in_zone = [t for t in recent_trades
                       if t['symbol'] == symbol
                       and zone_min <= t['entry_price'] <= zone_max]

    max_entries = config.get('V6_MAX_ENTRIES_PER_ZONE', 2)
    if len(entries_in_zone) >= max_entries:
        return False, "V6_MAX_ENTRIES_ZONE"

    # Check cooldown
    symbol_trades = [t for t in recent_trades if t['symbol'] == symbol]
    if symbol_trades:
        last_trade = max(symbol_trades, key=lambda t: t['entry_time'])
        hours_since = (entry_time - last_trade['entry_time']).total_seconds() / 3600

        if last_trade.get('pnl', 0) < 0:
            cooldown = config.get('V6_ENTRY_COOLDOWN_AFTER_LOSS', 24)
        else:
            cooldown = config.get('V6_ENTRY_COOLDOWN_HOURS', 6)

        if hours_since < cooldown:
            return False, "V6_ENTRY_COOLDOWN"

    return True, None
```

---

## 5. IMPACT ATTENDU

### 5.1 Comparaison V5 vs V6

| Métrique | V5 actuel | V6 attendu | Amélioration |
|----------|-----------|------------|--------------|
| Win Rate global | 65% | 72-75% | +7-10% |
| Win Rate 15m | 64% | 80%+ | +16% |
| TP1 Hit Rate | 45% | 60%+ | +15% |
| Profit Factor | 2.1 | 3.5+ | +67% |
| Avg P&L/trade | +5.5% | +8.5% | +55% |
| Trades rejetés (bad) | 0% | 15-20% | Évite les pertes |

### 5.2 Trades évités par V6

| Filtre | Trades rejetés | WR évité | P&L évité |
|--------|----------------|----------|-----------|
| 15m Slow Timing | ~12 | 25-42% | -8% à -15% |
| Distance > 20% | ~5 | 0% | -25% |
| Low Momentum | ~10 | 35% | -10% |
| Multiple Entries | ~8 | 40% | -12% |
| Score < 10 | ~15 | 53.8% | -5% |
| **TOTAL** | **~50** | **35%** | **-60%** |

### 5.3 Scoring Attendu par Catégorie

| Score | Trades | Win Rate V6 | Avg P&L |
|-------|--------|-------------|---------|
| 40+ (Excellent) | 30% | 78%+ | +12% |
| 25-39 (Good) | 35% | 70% | +8% |
| 10-24 (Medium) | 25% | 65% | +5% |
| <10 (Rejected) | 10% | N/A | Évité |

---

## 6. PLAN D'IMPLEMENTATION

### Phase 1: Core Filters (Priorité haute)

1. **V6_TIMING_FILTER** - 15m strict timing
   - Implémentation: 2h
   - Impact: +10% WR sur 15m

2. **V6_MAX_DISTANCE** - Reject distance > 20%
   - Implémentation: 30min
   - Impact: Évite 0% WR trades

### Phase 2: Momentum Filters (Priorité moyenne)

3. **V6_MOMENTUM_FILTER** - RSI/ADX checks
   - Implémentation: 2h
   - Impact: +5% WR global

4. **V6_ENTRY_LIMITER** - Limite entries par zone
   - Implémentation: 1h
   - Impact: Évite trades FETUSDT

### Phase 3: Scoring System (Priorité moyenne)

5. **V6_COMBINED_SCORING** - Score calculation
   - Implémentation: 3h
   - Impact: Meilleure sélection

6. **V6_MIN_SCORE** - Reject score < 10
   - Implémentation: 30min
   - Impact: Évite 53.8% WR trades

### Phase 4: Testing & Validation

7. **Backtest V6** sur 184 trades historiques
8. **Comparaison** V5 vs V6
9. **Fine-tuning** des seuils

---

## 7. CHECKLIST IMPLEMENTATION

```
[ ] Ajouter paramètres V6 dans DEFAULT_CONFIG
[ ] Implémenter check_v6_timing_filter()
[ ] Implémenter check_v6_momentum_filter()
[ ] Implémenter check_v6_entry_limiter()
[ ] Implémenter calculate_v6_score()
[ ] Intégrer dans run_backtest() flow
[ ] Ajouter colonnes V6 dans database (v6_score, v6_rejection_reason)
[ ] Mettre à jour API endpoints pour V6 data
[ ] Backtest validation sur historical data
[ ] Documentation mise à jour
```

---

## 8. RESUME DES REGLES V6

### Rejections obligatoires (HARD REJECT)

| Condition | Raison |
|-----------|--------|
| 15m + Retest > 24h | V6_15M_SLOW_RETEST |
| 15m + Entry > 48h | V6_15M_SLOW_ENTRY |
| Distance > 20% | V6_DISTANCE_TOO_HIGH |
| Potentiel < 10% | V6_LOW_POTENTIAL |
| RSI 1H < 45 | V6_RSI_TOO_LOW |
| ADX < 20 | V6_ADX_TOO_LOW |
| Score < 10 | V6_SCORE_TOO_LOW |
| Entries zone >= 2 | V6_MAX_ENTRIES_ZONE |
| Cooldown non respecté | V6_ENTRY_COOLDOWN |

### Warnings (Score malus, pas de rejet)

| Condition | Malus |
|-----------|-------|
| 1H + Retest 6-24h | -10 |
| CVD Divergence (15m/1h) | -10 |
| Distance > 10% | -5 |
| Retest > 24h (30m/1h) | -10 |
| Entry > 48h | -10 |

### Bonus (Score positif)

| Condition | Bonus |
|-----------|-------|
| Retest 0-6h | +15 |
| Entry 0-24h | +10 |
| Distance 5-10% | +15 |
| RSI > 50 | +10 |
| ADX > 25 | +10 |
| DI+ > DI- | +5 |
| No CVD Divergence | +10 |
| Timeframe 30m | +10 |
| Timeframe 1h | +5 |

---

*Document généré le 2026-03-15*
*Version: V6 Draft 1.0*
