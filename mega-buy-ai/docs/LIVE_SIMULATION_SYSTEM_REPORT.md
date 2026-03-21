# SYSTÈME DE SIMULATION LIVE MEGA BUY
## Rapport Technique Complet v1.0

**Date**: 2026-03-19
**Version**: 1.0
**Auteur**: MEGA BUY AI Team

---

## TABLE DES MATIÈRES

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Architecture du Système](#2-architecture-du-système)
3. [Les 7 Portefeuilles](#3-les-7-portefeuilles)
4. [Logique Live (6 Portefeuilles)](#4-logique-live-6-portefeuilles)
5. [Logique Backtest V5 (1 Portefeuille)](#5-logique-backtest-v5-1-portefeuille)
6. [Exit Strategy Unifiée](#6-exit-strategy-unifiée)
7. [Sources de Données](#7-sources-de-données)
8. [Configuration du Système](#8-configuration-du-système)
9. [Dashboard et Visualisation](#9-dashboard-et-visualisation)
10. [Composants Techniques](#10-composants-techniques)
11. [Base de Données](#11-base-de-données)
12. [API Endpoints](#12-api-endpoints)
13. [Métriques et KPIs](#13-métriques-et-kpis)
14. [Gestion des Erreurs](#14-gestion-des-erreurs)
15. [Déploiement](#15-déploiement)

---

## 1. VUE D'ENSEMBLE

### 1.1 Objectif du Système

Le système de simulation live MEGA BUY est conçu pour:

- **Capturer** les alertes MEGA BUY en temps réel depuis l'API `/alerts`
- **Appliquer** 7 stratégies de trading indépendantes en parallèle
- **Simuler** des portefeuilles virtuels avec gestion réaliste du capital
- **Comparer** les performances de chaque stratégie en temps réel
- **Visualiser** toutes les données via un dashboard interactif

### 1.2 Philosophie

| Concept | Description |
|---------|-------------|
| **Multi-Stratégie** | 7 portefeuilles indépendants avec des critères de sélection différents |
| **Réalisme** | Gestion du capital, positions simultanées, capital limité |
| **Comparabilité** | Exit strategy identique pour isoler l'impact des filtres |
| **Configurabilité** | Tous les paramètres modifiables via interface |
| **Transparence** | Dashboard complet avec toutes les métriques |

### 1.3 Les Deux Logiques de Trading

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│   LOGIQUE LIVE (6 Portefeuilles)        LOGIQUE V5 (1 Portefeuille)    │
│   ─────────────────────────────         ───────────────────────────     │
│                                                                         │
│   • Filtres de sélection                • Système de surveillance       │
│   • Entry IMMÉDIATE si filtre OK        • Watchlist des alertes         │
│   • Pas de conditions techniques        • 6 conditions techniques       │
│     supplémentaires                     • Entry quand 6/6 validées      │
│   • Simple et rapide                    • Complexe mais précis          │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. ARCHITECTURE DU SYSTÈME

### 2.1 Architecture Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MEGA BUY SCANNER                               │
│                     (Détection des alertes MEGA BUY)                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         API ALERTS ENDPOINT                              │
│                     http://localhost:9000/alerts                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ALERT CAPTURE SERVICE                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Polling configurable (défaut: 30 secondes)                    │    │
│  │ • Déduplication par alert_id (évite les doublons)               │    │
│  │ • Enrichissement avec données ML (p_success, confidence)        │    │
│  │ • Calcul des filtres empiriques (max_wr, balanced, big_winners) │    │
│  │ • Distribution aux 7 gestionnaires de portefeuille              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
        ▼                           ▼                           ▼
┌───────────────────┐    ┌───────────────────┐    ┌───────────────────────┐
│  FILTRES          │    │  SEUILS           │    │  BACKTEST V5          │
│  EMPIRIQUES       │    │  P_SUCCESS        │    │  SURVEILLANCE         │
│  (3 Portefeuilles)│    │  (3 Portefeuilles)│    │  (1 Portefeuille)     │
├───────────────────┤    ├───────────────────┤    ├───────────────────────┤
│ 1. Max WR         │    │ 4. Aggressive     │    │ 7. V5 Logic           │
│ 2. Équilibré      │    │ 5. Balanced       │    │    • Watchlist        │
│ 3. Gros Gagnants  │    │ 6. Conservative   │    │    • Monitor Loop     │
└───────────────────┘    └───────────────────┘    │    • 6 Conditions     │
        │                           │             └───────────────────────┘
        │                           │                           │
        └───────────────────────────┼───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         POSITION MANAGER                                 │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Gestion des positions ouvertes par portefeuille               │    │
│  │ • Allocation du capital (% configurable)                        │    │
│  │ • Limite des trades simultanés (configurable)                   │    │
│  │ • Tracking des P&L en temps réel                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          PRICE MONITOR                                   │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Polling Binance API (défaut: 15 secondes)                     │    │
│  │ • Cache des prix par paire                                      │    │
│  │ • Détection des exits (SL, BE, Trailing)                        │    │
│  │ • Mise à jour des trailing stops                                │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       EXIT STRATEGY ENGINE                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Stop Loss: -5% du prix d'entrée                               │    │
│  │ • Break-Even: activé à +4%, SL déplacé à +0.5%                  │    │
│  │ • Trailing Stop: activé à +15%, trail à -10% du plus haut      │    │
│  │ • Identique pour les 7 portefeuilles                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATABASE (SQLite)                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Historique des alertes capturées                              │    │
│  │ • Positions ouvertes et fermées                                 │    │
│  │ • Watchlist V5                                                  │    │
│  │ • Snapshots des portefeuilles                                   │    │
│  │ • Configuration persistante                                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           DASHBOARD                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │ • Vue temps réel des 7 portefeuilles                            │    │
│  │ • Comparatif des performances                                   │    │
│  │ • Détail des positions ouvertes                                 │    │
│  │ • Historique des trades                                         │    │
│  │ • Watchlist V5 avec état des conditions                         │    │
│  │ • Configuration interactive                                     │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flux de Données

```
[ALERTE] → [CAPTURE] → [ENRICHISSEMENT] → [DISTRIBUTION] → [FILTRAGE]
                                                               │
    ┌──────────────────────────────────────────────────────────┘
    │
    ├── [LIVE: Entry Immédiate] ──────────────────┐
    │                                              │
    └── [V5: Ajout Watchlist] → [Monitoring] ─────┤
                                                   │
                                                   ▼
                                          [POSITION OUVERTE]
                                                   │
                                                   ▼
                                          [PRICE MONITORING]
                                                   │
                                                   ▼
                                          [EXIT DETECTION]
                                                   │
                                                   ▼
                                          [POSITION FERMÉE]
                                                   │
                                                   ▼
                                          [MISE À JOUR STATS]
                                                   │
                                                   ▼
                                          [DASHBOARD UPDATE]
```

---

## 3. LES 7 PORTEFEUILLES

### 3.1 Vue d'Ensemble

| # | Nom | Type | Critère de Sélection | Caractéristique |
|---|-----|------|---------------------|-----------------|
| 1 | **Max Win Rate** | Filtre Empirique | Conditions techniques strictes | 82% Win Rate, perd gros gagnants |
| 2 | **Équilibré** | Filtre Empirique | Conditions techniques modérées | 73% Win Rate, garde 67% gros gains |
| 3 | **Gros Gagnants** | Filtre Empirique | Conditions techniques souples | 71% Win Rate, garde 92% gros gains |
| 4 | **Aggressive** | Seuil p_success | p_success ≥ 0.30 | ~90% des alertes, risque élevé |
| 5 | **Balanced** | Seuil p_success | p_success ≥ 0.50 | ~55% des alertes, équilibré |
| 6 | **Conservative** | Seuil p_success | p_success ≥ 0.70 | ~10% des alertes, haute précision |
| 7 | **Backtest V5** | Surveillance | 6 conditions techniques | Entry différée, plus précis |

### 3.2 Indépendance des Portefeuilles

Chaque portefeuille est **totalement indépendant**:

- **Capital propre**: Chaque portefeuille a son propre solde initial
- **Positions propres**: Les positions d'un portefeuille n'affectent pas les autres
- **Statistiques propres**: Win rate, profit factor, drawdown calculés séparément
- **Configuration propre**: Position size et max trades configurables par portefeuille

### 3.3 Chevauchement des Trades

Un même trade peut être pris par **plusieurs portefeuilles** simultanément:

```
Exemple: Alerte BTCUSDT avec:
- filter_max_wr = True
- filter_big_winners = True
- p_success = 0.65

Résultat:
✓ Portefeuille 1 (Max WR) → ENTRY
✗ Portefeuille 2 (Équilibré) → SKIP (filter_balanced = False)
✓ Portefeuille 3 (Gros Gagnants) → ENTRY
✓ Portefeuille 4 (Aggressive) → ENTRY (0.65 ≥ 0.30)
✓ Portefeuille 5 (Balanced) → ENTRY (0.65 ≥ 0.50)
✗ Portefeuille 6 (Conservative) → SKIP (0.65 < 0.70)
? Portefeuille 7 (V5) → WATCHLIST (attente conditions)

= 4 entries immédiates + 1 en surveillance
```

---

## 4. LOGIQUE LIVE (6 PORTEFEUILLES)

### 4.1 Filtres Empiriques (Portefeuilles 1-3)

Ces filtres sont calculés à partir des indicateurs techniques de l'alerte.

#### 4.1.1 Filtre Max Win Rate (Portefeuille 1)

**Objectif**: Maximiser le taux de réussite (82% Win Rate)
**Compromis**: Perd les gros gagnants (trades avec >15% profit)

**Conditions (toutes requises)**:
```python
filter_max_wr = (
    pp == True AND           # PP SuperTrend Buy actif
    ec == True AND           # Entry Confirmation actif
    di_minus_4h >= 22 AND    # DI- 4H élevé (pression vendeuse forte)
    di_plus_4h <= 25 AND     # DI+ 4H modéré
    adx_4h >= 35 AND         # ADX 4H très fort (tendance marquée)
    vol_pct_max >= 100       # Volume >= 100% de la moyenne
)
```

**Interprétation**: Ce filtre sélectionne les trades avec une tendance très forte (ADX ≥ 35) et une pression vendeuse significative qui se retourne. La combinaison PP + EC confirme le signal.

#### 4.1.2 Filtre Équilibré (Portefeuille 2)

**Objectif**: Équilibre entre win rate et capture des gros gains
**Performance**: 73% Win Rate, garde 67% des gros gagnants

**Conditions (toutes requises)**:
```python
filter_balanced = (
    pp == True AND           # PP SuperTrend Buy actif
    ec == True AND           # Entry Confirmation actif
    di_minus_4h >= 22 AND    # DI- 4H élevé
    di_plus_4h <= 20 AND     # DI+ 4H plus bas (critère plus strict)
    adx_4h >= 21 AND         # ADX 4H modéré
    vol_pct_max >= 100       # Volume >= 100%
)
```

**Interprétation**: Critère DI+ plus strict (≤20 vs ≤25) mais ADX plus souple (≥21 vs ≥35). Cible les retournements plus précoces.

#### 4.1.3 Filtre Gros Gagnants (Portefeuille 3)

**Objectif**: Maximiser la capture des trades à fort potentiel
**Performance**: 71% Win Rate, garde 92% des gros gagnants

**Conditions (toutes requises)**:
```python
filter_big_winners = (
    pp == True AND           # PP SuperTrend Buy actif
    ec == True AND           # Entry Confirmation actif
    di_minus_4h >= 22 AND    # DI- 4H élevé
    di_plus_4h <= 25 AND     # DI+ 4H modéré (même que Max WR)
    adx_4h >= 21 AND         # ADX 4H modéré (plus souple)
    vol_pct_max >= 100       # Volume >= 100%
)
```

**Interprétation**: Même conditions que Max WR mais ADX plus souple (≥21 vs ≥35). Accepte des tendances moins marquées qui peuvent devenir de gros mouvements.

### 4.2 Seuils p_success (Portefeuilles 4-6)

Ces filtres utilisent la probabilité de succès calculée par le modèle ML.

#### 4.2.1 Aggressive (Portefeuille 4)

**Seuil**: `p_success ≥ 0.30`
**Trades attendus**: ~90% des alertes
**Risque**: Élevé - accepte des trades à faible probabilité

```python
if p_success >= 0.30:
    decision = "ENTRY"
```

#### 4.2.2 Balanced (Portefeuille 5)

**Seuil**: `p_success ≥ 0.50`
**Trades attendus**: ~55% des alertes
**Risque**: Modéré - équilibre quantité/qualité

```python
if p_success >= 0.50:
    decision = "ENTRY"
```

#### 4.2.3 Conservative (Portefeuille 6)

**Seuil**: `p_success ≥ 0.70`
**Trades attendus**: ~10% des alertes
**Risque**: Faible - seulement les meilleures opportunités

```python
if p_success >= 0.70:
    decision = "ENTRY"
```

### 4.3 Processus d'Entry Live

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        NOUVELLE ALERTE REÇUE                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1: EXTRACTION DES DONNÉES                                         │
│  ───────────────────────────────                                         │
│  • pair: "BTCUSDT"                                                       │
│  • price: 65000.00                                                       │
│  • alert_timestamp: "2026-03-19T10:30:00Z"                               │
│  • pp: true, ec: true                                                    │
│  • di_plus_4h: 22.5, di_minus_4h: 28.3, adx_4h: 38.2                    │
│  • vol_pct_max: 145.0                                                    │
│  • p_success: 0.58                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 2: CALCUL DES FILTRES EMPIRIQUES                                  │
│  ──────────────────────────────────────                                  │
│  • filter_max_wr: True (22.5≤25, 28.3≥22, 38.2≥35, 145≥100, pp, ec)    │
│  • filter_balanced: False (22.5 > 20, condition DI+ non respectée)      │
│  • filter_big_winners: True (22.5≤25, 28.3≥22, 38.2≥21, 145≥100)       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 3: ÉVALUATION PAR PORTEFEUILLE                                    │
│  ────────────────────────────────────                                    │
│                                                                          │
│  Pour chaque portefeuille Live (1-6):                                    │
│                                                                          │
│    1. Vérifier si le filtre/seuil est satisfait                          │
│    2. Vérifier si max_concurrent_trades non atteint                      │
│    3. Vérifier si capital disponible suffisant                           │
│    4. Si OK → OUVRIR POSITION                                            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 4: OUVERTURE DES POSITIONS                                        │
│  ────────────────────────────────                                        │
│                                                                          │
│  Portefeuille 1 (Max WR):                                                │
│    • allocation = balance × 12% = $2000 × 0.12 = $240                   │
│    • entry_price = 65000.00                                              │
│    • sl_price = 65000 × 0.95 = 61750.00                                 │
│    • be_trigger = 65000 × 1.04 = 67600.00                               │
│    • trail_trigger = 65000 × 1.15 = 74750.00                            │
│    • status = OPEN                                                       │
│                                                                          │
│  (Répéter pour chaque portefeuille qui accepte le trade)                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. LOGIQUE BACKTEST V5 (1 PORTEFEUILLE)

### 5.1 Différence Fondamentale

| Aspect | Logique Live | Logique V5 |
|--------|--------------|------------|
| **Entry** | Immédiate si filtre OK | Différée (surveillance) |
| **Conditions** | 1 condition (filtre/seuil) | 6 conditions techniques |
| **Durée** | Instantané | Jusqu'à 72 heures |
| **Complexité** | Simple | Élevée |
| **Données requises** | Alert data seulement | OHLCV multi-timeframe |

### 5.2 Prérequis (Phase 1)

Avant d'ajouter une alerte à la watchlist, vérifier 3 prérequis:

```python
# Prérequis 1: STC Oversold
stc_oversold = (
    stc_15m < 0.2 OR
    stc_30m < 0.2 OR
    stc_1h < 0.2
)
# Au moins un timeframe doit avoir STC < 0.2

# Prérequis 2: Pas 15m seul
not_15m_alone = (
    "30m" in timeframes OR
    "1h" in timeframes
)
# Le signal doit inclure 30m ou 1h

# Prérequis 3: Trendline existe
trendline_exists = (
    trendline_price is not None AND
    trendline_price > 0
)
# Une trendline doit être détectée au moment de l'alerte
```

**Si un prérequis échoue:**
```
REJECTED_STC        → STC pas en oversold sur aucun TF
REJECTED_15M_ALONE  → Signal uniquement sur 15m
REJECTED_NO_TL      → Pas de trendline détectée
```

### 5.3 Watchlist (Phase 2)

Si tous les prérequis sont validés, l'alerte est ajoutée à la watchlist:

```python
watchlist_entry = {
    "alert_id": "uuid-xxx",
    "pair": "BTCUSDT",
    "alert_timestamp": "2026-03-19T10:30:00Z",
    "deadline": "2026-03-22T10:30:00Z",  # +72 heures
    "trendline_price": 64500.00,
    "status": "WATCHING",
    "conditions_met": {
        "tl_break": False,
        "ema100_1h": False,
        "ema20_4h": False,
        "cloud_1h": False,
        "cloud_30m": False,
        "choch_bos": False
    },
    "last_check": None,
    "check_count": 0
}
```

### 5.4 Les 6 Conditions d'Entrée (Phase 3)

#### Condition 1: TL Break (Trendline Break)

```python
tl_break = close_1h > trendline_price

# Paramètres:
# - trendline_price: calculé au moment de l'alerte
# - close_1h: prix de clôture actuel sur 1H
# - délai max: 72 heures après l'alerte
```

**Calcul de la Trendline:**
- Détection des swing highs sur 4H (left=5, right=3)
- Connexion des 2 derniers swing highs majeurs
- Extension de la ligne vers le futur
- Sélection: la trendline la plus proche du prix

#### Condition 2: EMA100 sur 1H

```python
ema100_1h = close_1h > ema100_1h

# Paramètres:
# - EMA période: 100
# - Timeframe: 1H
# - Données requises: 100+ bougies 1H
```

#### Condition 3: EMA20 sur 4H

```python
ema20_4h = close_4h > ema20_4h

# Paramètres:
# - EMA période: 20
# - Timeframe: 4H
# - Données requises: 20+ bougies 4H
```

#### Condition 4: Cloud Top sur 1H

```python
cloud_top_1h = close_1h > max(senkou_a_1h, senkou_b_1h)

# Paramètres Ichimoku (STANDARD, non dynamique):
# - Tenkan-Sen: 9
# - Kijun-Sen: 26
# - Senkou-Span B: 52
# - Displacement: 26

# Calcul:
# senkou_a = (tenkan + kijun) / 2
# senkou_b = (highest_high_52 + lowest_low_52) / 2
# cloud_top = max(senkou_a, senkou_b)
```

#### Condition 5: Cloud Top sur 30M

```python
cloud_top_30m = close_30m > max(senkou_a_30m, senkou_b_30m)

# Mêmes paramètres Ichimoku que 1H
# Timeframe: 30M
```

#### Condition 6: CHoCH/BOS Confirmé

```python
choch_bos = close_1h > swing_high_price * 1.005

# Paramètres:
# - Swing High: left=5, right=3
# - Marge de confirmation: 0.5%

# Détection Swing High:
# Un swing high à l'index i est valide si:
# high[i] > all highs in [i-5, i-1] AND [i+1, i+3]
```

### 5.5 Monitoring Loop (Phase 3 - Suite)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      MONITORING LOOP V5                                  │
│                    (Exécuté toutes les 15 minutes)                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  POUR CHAQUE ALERTE DANS LA WATCHLIST:                                   │
│                                                                          │
│  1. Vérifier si deadline dépassée                                        │
│     └── Si OUI → status = "EXPIRED", retirer de watchlist               │
│                                                                          │
│  2. Récupérer les données OHLCV                                          │
│     • 30m: 52 dernières bougies                                          │
│     • 1h: 100 dernières bougies                                          │
│     • 4h: 50 dernières bougies                                           │
│                                                                          │
│  3. Calculer les indicateurs                                             │
│     • EMA100 (1H), EMA20 (4H)                                           │
│     • Ichimoku Cloud Top (30m, 1H)                                       │
│     • Swing Highs (1H) pour CHoCH/BOS                                    │
│                                                                          │
│  4. Évaluer les 6 conditions                                             │
│     • Mettre à jour conditions_met                                       │
│                                                                          │
│  5. Si toutes les conditions sont TRUE:                                  │
│     └── ENTRY! Ouvrir position, retirer de watchlist                    │
│                                                                          │
│  6. Sinon:                                                               │
│     └── Continuer surveillance, incrémenter check_count                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.6 Schéma Temporel V5

```
                    Alert                                     Deadline
                      │                                          │
                      ▼                                          ▼
Timeline: ────────────┼────────────────────────────────────────┼────────
                      │                                          │
                      │◄──────────── 72 heures max ────────────►│
                      │                                          │
                     T0          T1          T2          T3
                      │           │           │           │
                      ▼           ▼           ▼           ▼
                   Check 1    Check 2    Check 3    Check N
                   (0/6)      (2/6)      (4/6)      (6/6) ← ENTRY!
                      │           │           │           │
                      │           │           │           │
Conditions:        ──□──       ──▣──       ──▣──       ──▣──
TL Break           [  ]       [✓ ]       [✓ ]       [✓ ]
EMA100 1H          [  ]       [  ]       [✓ ]       [✓ ]
EMA20 4H           [  ]       [✓ ]       [✓ ]       [✓ ]
Cloud 1H           [  ]       [  ]       [  ]       [✓ ]
Cloud 30m          [  ]       [  ]       [✓ ]       [✓ ]
CHoCH/BOS          [  ]       [  ]       [  ]       [✓ ]
```

---

## 6. EXIT STRATEGY UNIFIÉE

### 6.1 Paramètres

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `SL_PCT` | -5.0% | Stop Loss initial |
| `BE_ACTIVATION_PCT` | +4.0% | Niveau d'activation du Break-Even |
| `BE_SL_PCT` | +0.5% | Nouveau SL après activation BE |
| `TRAILING_ACTIVATION_PCT` | +15.0% | Niveau d'activation du Trailing |
| `TRAILING_DISTANCE_PCT` | -10.0% | Distance du Trailing SL |

### 6.2 Logique Complète

```python
def check_exit(position, current_price, current_high):
    """
    Vérifie si une position doit être fermée.

    Args:
        position: Position ouverte
        current_price: Prix actuel
        current_high: Plus haut depuis l'entrée

    Returns:
        (should_exit, exit_reason, exit_price)
    """
    entry_price = position.entry_price

    # Calculer les niveaux
    sl_price = entry_price * 0.95                    # -5%
    be_trigger = entry_price * 1.04                  # +4%
    be_sl = entry_price * 1.005                      # +0.5%
    trail_trigger = entry_price * 1.15               # +15%

    # État actuel
    highest_since_entry = max(current_high, position.highest_price)
    trailing_sl = highest_since_entry * 0.90         # -10% du plus haut

    # PHASE 1: Vérifier Stop Loss initial
    if not position.be_activated:
        if current_price <= sl_price:
            return (True, "STOP_LOSS", sl_price)

    # PHASE 2: Vérifier activation Break-Even
    if not position.be_activated and current_price >= be_trigger:
        position.be_activated = True
        position.current_sl = be_sl
        # Log: "BE activé à +4%, SL déplacé à +0.5%"

    # PHASE 3: Vérifier SL Break-Even
    if position.be_activated and not position.trailing_activated:
        if current_price <= position.current_sl:
            return (True, "BREAK_EVEN", position.current_sl)

    # PHASE 4: Vérifier activation Trailing
    if not position.trailing_activated and current_price >= trail_trigger:
        position.trailing_activated = True
        position.trailing_sl = trailing_sl
        # Log: "Trailing activé à +15%"

    # PHASE 5: Mettre à jour et vérifier Trailing SL
    if position.trailing_activated:
        # Mettre à jour le trailing SL si nouveau plus haut
        new_trailing_sl = highest_since_entry * 0.90
        if new_trailing_sl > position.trailing_sl:
            position.trailing_sl = new_trailing_sl

        # Vérifier si trailing SL touché
        if current_price <= position.trailing_sl:
            return (True, "TRAILING_STOP", position.trailing_sl)

    # Mettre à jour le plus haut
    position.highest_price = highest_since_entry

    return (False, None, None)
```

### 6.3 Diagramme d'États

```
                              ┌─────────────────────┐
                              │   POSITION OUVERTE  │
                              │   SL = Entry × 0.95 │
                              └──────────┬──────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         Prix ≤ SL (-5%)      Prix ≥ +4%              Prix monte
                    │                    │                    │
                    ▼                    ▼                    │
            ┌───────────┐       ┌────────────────┐            │
            │ EXIT: SL  │       │ BE ACTIVÉ      │            │
            │ P&L: -5%  │       │ SL = +0.5%     │            │
            └───────────┘       └───────┬────────┘            │
                                        │                     │
                    ┌───────────────────┼─────────────────────┘
                    │                   │
                    ▼                   ▼
         Prix ≤ +0.5%          Prix ≥ +15%
                    │                   │
                    ▼                   ▼
            ┌───────────┐       ┌─────────────────┐
            │ EXIT: BE  │       │ TRAILING ACTIVÉ │
            │ P&L: +0.5%│       │ TSL = High×0.90 │
            └───────────┘       └───────┬─────────┘
                                        │
                                        ▼
                                Prix ≤ TSL
                                        │
                                        ▼
                               ┌──────────────────┐
                               │ EXIT: TRAILING   │
                               │ P&L: Variable    │
                               │ (min +5%, max ∞) │
                               └──────────────────┘
```

### 6.4 Exemples de Scénarios

#### Scénario A: Stop Loss Direct

```
Entry: $100
Prix tombe à $95 (-5%)
→ EXIT: STOP_LOSS
→ P&L: -5% = -$5
```

#### Scénario B: Break-Even

```
Entry: $100
Prix monte à $104 (+4%) → BE activé, SL = $100.50
Prix retombe à $100.50
→ EXIT: BREAK_EVEN
→ P&L: +0.5% = +$0.50
```

#### Scénario C: Trailing Stop

```
Entry: $100
Prix monte à $104 → BE activé, SL = $100.50
Prix monte à $115 (+15%) → Trailing activé, TSL = $103.50
Prix monte à $130 → TSL = $117.00 (130 × 0.90)
Prix monte à $140 → TSL = $126.00 (140 × 0.90)
Prix retombe à $126
→ EXIT: TRAILING_STOP
→ P&L: +26% = +$26
```

---

## 7. SOURCES DE DONNÉES

### 7.1 API Alerts

**Endpoint**: `http://localhost:9000/api/alerts`
**Méthode**: GET
**Polling**: Configurable (défaut: 30 secondes)

**Réponse attendue**:
```json
{
  "alerts": [
    {
      "id": "uuid-123",
      "pair": "BTCUSDT",
      "timeframes": ["1h", "4h"],
      "scanner_score": 8,
      "price": 65000.00,
      "alert_timestamp": "2026-03-19T10:30:00Z",
      "rsi": 45.2,
      "di_plus_4h": 22.5,
      "di_minus_4h": 28.3,
      "adx_4h": 38.2,
      "puissance": 7.5,
      "choch": true,
      "zone": true,
      "lazy": true,
      "vol": false,
      "st": true,
      "pp": true,
      "ec": true,
      "vol_pct": {"1h": 145.0, "4h": 120.0},
      "p_success": 0.58,
      "confidence": 0.72
    }
  ],
  "total": 1
}
```

### 7.2 API Binance (Prix)

**Endpoint**: `https://api.binance.com/api/v3/ticker/price`
**Méthode**: GET
**Polling**: Configurable (défaut: 15 secondes)

**Requête unique**:
```
GET /api/v3/ticker/price?symbol=BTCUSDT
```

**Requête multiple**:
```
GET /api/v3/ticker/price?symbols=["BTCUSDT","ETHUSDT","SOLUSDT"]
```

**Réponse**:
```json
{
  "symbol": "BTCUSDT",
  "price": "65123.45"
}
```

### 7.3 API Binance (OHLCV pour V5)

**Endpoint**: `https://api.binance.com/api/v3/klines`
**Méthode**: GET
**Usage**: Pour le calcul des indicateurs techniques V5

**Requête**:
```
GET /api/v3/klines?symbol=BTCUSDT&interval=1h&limit=100
```

**Intervalles requis**:
- `30m` : 52 bougies minimum (Cloud)
- `1h` : 100 bougies minimum (EMA100, Cloud, CHoCH)
- `4h` : 50 bougies minimum (EMA20, Trendline)

**Réponse**:
```json
[
  [
    1679234400000,    // Open time
    "65000.00",       // Open
    "65500.00",       // High
    "64800.00",       // Low
    "65200.00",       // Close
    "1234.56",        // Volume
    1679238000000,    // Close time
    "80345678.90",    // Quote volume
    1234,             // Number of trades
    "617.28",         // Taker buy volume
    "40172839.45",    // Taker buy quote volume
    "0"               // Ignore
  ]
]
```

### 7.4 Rate Limiting

| API | Limite | Notre usage | Marge |
|-----|--------|-------------|-------|
| Binance Ticker | 1200/min | ~4/min (15s polling × pairs) | Large |
| Binance Klines | 1200/min | ~12/min (V5 watchlist) | Large |
| Dashboard Alerts | Variable | 2/min (30s polling) | OK |

---

## 8. CONFIGURATION DU SYSTÈME

### 8.1 Fichier de Configuration

**Emplacement**: `config/simulation_config.json`

```json
{
  "version": "1.0",
  "last_updated": "2026-03-19T12:00:00Z",

  "global": {
    "alert_polling_interval_sec": 30,
    "price_polling_interval_sec": 15,
    "v5_monitoring_interval_sec": 900,
    "database_path": "data/simulation.db",
    "log_level": "INFO"
  },

  "exit_strategy": {
    "sl_pct": 5.0,
    "be_activation_pct": 4.0,
    "be_sl_pct": 0.5,
    "trailing_activation_pct": 15.0,
    "trailing_distance_pct": 10.0
  },

  "portfolios": {
    "max_wr": {
      "enabled": true,
      "name": "Max Win Rate",
      "type": "empirical_filter",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "filter_conditions": {
        "pp": true,
        "ec": true,
        "di_minus_min": 22,
        "di_plus_max": 25,
        "adx_min": 35,
        "vol_min": 100
      }
    },
    "balanced_filter": {
      "enabled": true,
      "name": "Équilibré",
      "type": "empirical_filter",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "filter_conditions": {
        "pp": true,
        "ec": true,
        "di_minus_min": 22,
        "di_plus_max": 20,
        "adx_min": 21,
        "vol_min": 100
      }
    },
    "big_winners": {
      "enabled": true,
      "name": "Gros Gagnants",
      "type": "empirical_filter",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "filter_conditions": {
        "pp": true,
        "ec": true,
        "di_minus_min": 22,
        "di_plus_max": 25,
        "adx_min": 21,
        "vol_min": 100
      }
    },
    "aggressive": {
      "enabled": true,
      "name": "Aggressive",
      "type": "p_success_threshold",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "threshold": 0.30
    },
    "balanced_ml": {
      "enabled": true,
      "name": "Balanced",
      "type": "p_success_threshold",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "threshold": 0.50
    },
    "conservative": {
      "enabled": true,
      "name": "Conservative",
      "type": "p_success_threshold",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "threshold": 0.70
    },
    "backtest_v5": {
      "enabled": true,
      "name": "Backtest V5",
      "type": "v5_surveillance",
      "initial_balance": 2000.0,
      "position_size_pct": 12.0,
      "max_concurrent_trades": 8,
      "v5_config": {
        "max_surveillance_hours": 72,
        "stc_oversold_threshold": 0.2,
        "choch_margin_pct": 0.5,
        "swing_left": 5,
        "swing_right": 3
      }
    }
  }
}
```

### 8.2 Variables d'Environnement

```bash
# .env
SIMULATION_DB_PATH=/home/assyin/MEGA-BUY-BOT/mega-buy-ai/simulation/data/simulation.db
ALERTS_API_URL=http://localhost:9000/api/alerts
BINANCE_API_URL=https://api.binance.com
LOG_LEVEL=INFO
```

---

## 9. DASHBOARD ET VISUALISATION

### 9.1 Structure des Pages

```
┌─────────────────────────────────────────────────────────────────────────┐
│  MEGA BUY SIMULATION DASHBOARD                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  [Overview] [Portfolios] [Positions] [Watchlist V5] [History] [Config]  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.2 Page Overview (Accueil)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 OVERVIEW - Simulation Live                          🟢 RUNNING      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📈 PERFORMANCE GLOBALE                                              │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Capital Total Initial: $14,000    Capital Total Actuel: $16,450    │ │
│  │  P&L Global: +$2,450 (+17.5%)      Positions Ouvertes: 12          │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📊 COMPARATIF DES 7 PORTEFEUILLES                                   │ │
│  ├──────────────────┬─────────┬──────────┬────────┬────────┬──────────┤ │
│  │ Portefeuille     │ Balance │ P&L %    │ WR %   │ Trades │ Open     │ │
│  ├──────────────────┼─────────┼──────────┼────────┼────────┼──────────┤ │
│  │ 1. Max WR        │ $2,340  │ +17.0%   │ 85%    │ 20     │ 2        │ │
│  │ 2. Équilibré     │ $2,180  │ +9.0%    │ 78%    │ 15     │ 1        │ │
│  │ 3. Gros Gagnants │ $2,520  │ +26.0%   │ 72%    │ 22     │ 3        │ │
│  │ 4. Aggressive    │ $2,150  │ +7.5%    │ 55%    │ 45     │ 4        │ │
│  │ 5. Balanced      │ $2,280  │ +14.0%   │ 68%    │ 28     │ 1        │ │
│  │ 6. Conservative  │ $2,450  │ +22.5%   │ 82%    │ 8      │ 0        │ │
│  │ 7. Backtest V5   │ $2,530  │ +26.5%   │ 88%    │ 18     │ 1        │ │
│  └──────────────────┴─────────┴──────────┴────────┴────────┴──────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📉 GRAPHIQUE D'ÉVOLUTION DES BALANCES                               │ │
│  │                                                                      │ │
│  │  $2,600 ─┬───────────────────────────────────────────────────────┐  │ │
│  │          │                                          ╱──── V5     │  │ │
│  │  $2,400 ─┤                                    ╱────╱             │  │ │
│  │          │                              ╱────╱                   │  │ │
│  │  $2,200 ─┤                        ╱────╱                         │  │ │
│  │          │                  ╱────╱                               │  │ │
│  │  $2,000 ─┼────────────────╱──────────────────────────────────────┤  │ │
│  │          │ Start                                           Now   │  │ │
│  │          └───────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 🔔 DERNIÈRES ALERTES (5 dernières)                                  │ │
│  ├──────────────────┬──────────┬────────────────────────────┬─────────┤ │
│  │ Timestamp        │ Pair     │ Portefeuilles              │ Status  │ │
│  ├──────────────────┼──────────┼────────────────────────────┼─────────┤ │
│  │ 10:45:23         │ BTCUSDT  │ MaxWR, BigWin, Agg, Bal    │ 4 Entry │ │
│  │ 10:32:15         │ ETHUSDT  │ V5 Watchlist               │ Watch   │ │
│  │ 10:28:44         │ SOLUSDT  │ Tous (7/7)                 │ 7 Entry │ │
│  │ 10:15:02         │ BNBUSDT  │ Agg, Bal                   │ 2 Entry │ │
│  │ 10:02:38         │ XRPUSDT  │ Aucun                      │ Skipped │ │
│  └──────────────────┴──────────┴────────────────────────────┴─────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.3 Page Portfolios (Détail par Portefeuille)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  💼 PORTEFEUILLE: Max Win Rate                         [Éditer Config]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📊 RÉSUMÉ                                                           │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │ │
│  │  │   $2,340     │  │   +17.0%     │  │    85%       │  │   1.8    │ │ │
│  │  │   Balance    │  │   Return     │  │   Win Rate   │  │   P.F.   │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │ │
│  │                                                                      │ │
│  │  Cash Disponible: $1,860    En Position: $480 (2 trades)           │ │
│  │  Max Drawdown: -$180 (-8.2%)    Peak Balance: $2,380               │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ ⚙️ CONFIGURATION                                                    │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Type: Filtre Empirique          Initial Balance: $2,000            │ │
│  │  Position Size: 12%              Max Concurrent: 8                  │ │
│  │                                                                      │ │
│  │  Conditions du Filtre:                                              │ │
│  │  • PP = True ✓    • EC = True ✓                                    │ │
│  │  • DI- ≥ 22       • DI+ ≤ 25                                       │ │
│  │  • ADX ≥ 35       • Vol ≥ 100%                                     │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📈 POSITIONS OUVERTES (2)                                           │ │
│  ├──────────┬────────┬──────────┬──────────┬──────────┬───────────────┤ │
│  │ Pair     │ Entry  │ Current  │ P&L %    │ Alloc    │ Status        │ │
│  ├──────────┼────────┼──────────┼──────────┼──────────┼───────────────┤ │
│  │ BTCUSDT  │ $65000 │ $66300   │ +2.0%    │ $240     │ 🔵 Open       │ │
│  │ ETHUSDT  │ $3200  │ $3350    │ +4.7%    │ $240     │ 🟢 BE Active  │ │
│  └──────────┴────────┴──────────┴──────────┴──────────┴───────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📜 HISTORIQUE DES TRADES (10 derniers)                              │ │
│  ├──────────┬────────┬──────────┬──────────┬──────────┬───────────────┤ │
│  │ Date     │ Pair   │ Entry    │ Exit     │ P&L      │ Reason        │ │
│  ├──────────┼────────┼──────────┼──────────┼──────────┼───────────────┤ │
│  │ 03-19    │ SOLUSDT│ $142.50  │ $163.87  │ +15.0%   │ Trailing      │ │
│  │ 03-19    │ BNBUSDT│ $580.00  │ $582.90  │ +0.5%    │ Break-Even    │ │
│  │ 03-18    │ XRPUSDT│ $0.62    │ $0.59    │ -5.0%    │ Stop Loss     │ │
│  │ ...      │ ...    │ ...      │ ...      │ ...      │ ...           │ │
│  └──────────┴────────┴──────────┴──────────┴──────────┴───────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.4 Page Positions (Toutes les Positions Ouvertes)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 POSITIONS OUVERTES - Tous Portefeuilles (12 positions)              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filtrer par: [Tous ▼]  Trier par: [P&L % ▼]  🔄 Refresh                │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ POSITIONS EN TEMPS RÉEL                                             │ │
│  ├────────┬───────────┬────────┬─────────┬────────┬────────┬──────────┤ │
│  │ Portf  │ Pair      │ Entry  │ Current │ P&L %  │ Status │ SL Level │ │
│  ├────────┼───────────┼────────┼─────────┼────────┼────────┼──────────┤ │
│  │ MaxWR  │ BTCUSDT   │ $65000 │ $66300  │ +2.0%  │ Open   │ $61750   │ │
│  │ MaxWR  │ ETHUSDT   │ $3200  │ $3350   │ +4.7%  │ BE     │ $3216    │ │
│  │ BigWin │ BTCUSDT   │ $65000 │ $66300  │ +2.0%  │ Open   │ $61750   │ │
│  │ BigWin │ SOLUSDT   │ $145   │ $168    │ +15.9% │ Trail  │ $151.2   │ │
│  │ BigWin │ AVAXUSDT  │ $38.50 │ $39.20  │ +1.8%  │ Open   │ $36.58   │ │
│  │ Aggr   │ BTCUSDT   │ $65000 │ $66300  │ +2.0%  │ Open   │ $61750   │ │
│  │ Aggr   │ LINKUSDT  │ $18.20 │ $17.80  │ -2.2%  │ Open   │ $17.29   │ │
│  │ Aggr   │ DOTUSDT   │ $7.85  │ $8.10   │ +3.2%  │ Open   │ $7.46    │ │
│  │ Aggr   │ MATICUSDT │ $0.92  │ $0.89   │ -3.3%  │ Open   │ $0.87    │ │
│  │ Bal    │ BTCUSDT   │ $65000 │ $66300  │ +2.0%  │ Open   │ $61750   │ │
│  │ V5     │ BTCUSDT   │ $64800 │ $66300  │ +2.3%  │ Open   │ $61560   │ │
│  │ V5     │ NEARUSDT  │ $5.20  │ $5.45   │ +4.8%  │ BE     │ $5.23    │ │
│  └────────┴───────────┴────────┴─────────┴────────┴────────┴──────────┘ │
│                                                                          │
│  Légende Status: 🔵 Open | 🟢 BE Active | 🟡 Trailing Active            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.5 Page Watchlist V5

```
┌─────────────────────────────────────────────────────────────────────────┐
│  👁️ WATCHLIST V5 - Alertes en Surveillance (5 alertes)                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ STATISTIQUES WATCHLIST                                              │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  En surveillance: 5     Entries réussies: 18    Expirées: 12        │ │
│  │  Taux de conversion: 60%    Temps moyen avant entry: 8.5h           │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ ALERTES EN SURVEILLANCE                                             │ │
│  ├──────────┬──────────────────┬───────────────────┬───────────────────┤ │
│  │ Pair     │ Depuis           │ Deadline          │ Conditions        │ │
│  ├──────────┼──────────────────┼───────────────────┼───────────────────┤ │
│  │ BTCUSDT  │ 2h 30m           │ 69h 30m restant   │ ████░░ 4/6        │ │
│  │ ETHUSDT  │ 5h 15m           │ 66h 45m restant   │ ███░░░ 3/6        │ │
│  │ SOLUSDT  │ 12h 00m          │ 60h 00m restant   │ █████░ 5/6        │ │
│  │ AVAXUSDT │ 48h 30m          │ 23h 30m restant   │ ██░░░░ 2/6        │ │
│  │ DOTUSDT  │ 68h 00m          │ 4h 00m restant    │ ████░░ 4/6        │ │
│  └──────────┴──────────────────┴───────────────────┴───────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 🔍 DÉTAIL: BTCUSDT                                     [Réduire ▲]  │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Alert ID: uuid-abc-123                                             │ │
│  │  Alert Time: 2026-03-19 08:15:00                                    │ │
│  │  Trendline Price: $64,500                                           │ │
│  │  Current Price: $66,300                                             │ │
│  │  Checks effectués: 10                                               │ │
│  │                                                                      │ │
│  │  CONDITIONS D'ENTRÉE:                                               │ │
│  │  ┌────────────────────────────────────────────────────────────────┐ │ │
│  │  │                                                                 │ │ │
│  │  │  [✓] 1. TL Break      Close $66,300 > TL $64,500               │ │ │
│  │  │  [✓] 2. EMA100 1H     Close > EMA100 ($65,800)                 │ │ │
│  │  │  [✓] 3. EMA20 4H      Close > EMA20 ($65,200)                  │ │ │
│  │  │  [✓] 4. Cloud 1H      Close > Cloud Top ($65,100)              │ │ │
│  │  │  [ ] 5. Cloud 30m     Close < Cloud Top ($66,500)  ⚠️          │ │ │
│  │  │  [ ] 6. CHoCH/BOS     Swing High $67,200 non cassé ⚠️          │ │ │
│  │  │                                                                 │ │ │
│  │  └────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                      │ │
│  │  Prochain check dans: 12 minutes                                    │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.6 Page History (Historique Complet)

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📜 HISTORIQUE DES TRADES                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filtrer: [Tous Portf ▼] [Toutes Pairs ▼] [7 derniers jours ▼]         │
│  Export: [CSV] [JSON]                                                   │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ TRADES FERMÉS (156 trades)                                          │ │
│  ├───────┬────────┬──────────┬────────┬─────────┬────────┬────────────┤ │
│  │ Date  │ Portf  │ Pair     │ Entry  │ Exit    │ P&L    │ Reason     │ │
│  ├───────┼────────┼──────────┼────────┼─────────┼────────┼────────────┤ │
│  │ 03-19 │ BigWin │ SOLUSDT  │ $142.5 │ $163.87 │ +15.0% │ Trailing   │ │
│  │ 03-19 │ V5     │ LINKUSDT │ $17.80 │ $20.47  │ +15.0% │ Trailing   │ │
│  │ 03-19 │ MaxWR  │ BNBUSDT  │ $580   │ $582.90 │ +0.5%  │ Break-Even │ │
│  │ 03-18 │ Aggr   │ XRPUSDT  │ $0.62  │ $0.59   │ -5.0%  │ Stop Loss  │ │
│  │ 03-18 │ Bal    │ BTCUSDT  │ $63500 │ $73025  │ +15.0% │ Trailing   │ │
│  │ ...   │ ...    │ ...      │ ...    │ ...     │ ...    │ ...        │ │
│  └───────┴────────┴──────────┴────────┴─────────┴────────┴────────────┘ │
│                                                                          │
│  [1] [2] [3] ... [16]  Affichage: 10 par page ▼                         │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 9.7 Page Configuration

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ⚙️ CONFIGURATION DU SYSTÈME                           [💾 Sauvegarder] │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 🌐 PARAMÈTRES GLOBAUX                                               │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Polling Alertes (sec):        [30     ]                            │ │
│  │  Polling Prix (sec):           [15     ]                            │ │
│  │  Monitoring V5 (sec):          [900    ]                            │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 📈 EXIT STRATEGY (tous portefeuilles)                               │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Stop Loss (%):                [-5.0   ]                            │ │
│  │  Break-Even Activation (%):    [+4.0   ]                            │ │
│  │  Break-Even SL (%):            [+0.5   ]                            │ │
│  │  Trailing Activation (%):      [+15.0  ]                            │ │
│  │  Trailing Distance (%):        [-10.0  ]                            │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 💼 PORTEFEUILLES                                                    │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  ┌───────────────┬─────────┬──────────┬───────────┬────────┐        │ │
│  │  │ Portefeuille  │ Enabled │ Balance  │ Pos Size  │ Max Tr │        │ │
│  │  ├───────────────┼─────────┼──────────┼───────────┼────────┤        │ │
│  │  │ 1. Max WR     │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 2. Équilibré  │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 3. Gros Gains │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 4. Aggressive │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 5. Balanced   │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 6. Conserv    │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  │ 7. V5         │   [✓]   │ [$2000 ] │   [12%]   │  [8 ]  │        │ │
│  │  └───────────────┴─────────┴──────────┴───────────┴────────┘        │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 🎯 SEUILS P_SUCCESS                                                 │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  Aggressive:    [0.30]                                              │ │
│  │  Balanced:      [0.50]                                              │ │
│  │  Conservative:  [0.70]                                              │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │ 🔧 CONDITIONS FILTRES EMPIRIQUES                                    │ │
│  ├─────────────────────────────────────────────────────────────────────┤ │
│  │                                                                      │ │
│  │  MAX WIN RATE:                                                      │ │
│  │  PP [✓]  EC [✓]  DI- ≥ [22]  DI+ ≤ [25]  ADX ≥ [35]  Vol ≥ [100%]  │ │
│  │                                                                      │ │
│  │  ÉQUILIBRÉ:                                                         │ │
│  │  PP [✓]  EC [✓]  DI- ≥ [22]  DI+ ≤ [20]  ADX ≥ [21]  Vol ≥ [100%]  │ │
│  │                                                                      │ │
│  │  GROS GAGNANTS:                                                     │ │
│  │  PP [✓]  EC [✓]  DI- ≥ [22]  DI+ ≤ [25]  ADX ≥ [21]  Vol ≥ [100%]  │ │
│  │                                                                      │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
│                    [🔄 Reset Défaut]  [💾 Sauvegarder Config]            │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 10. COMPOSANTS TECHNIQUES

### 10.1 Structure des Fichiers

```
mega-buy-ai/
└── simulation/
    ├── __init__.py
    ├── main.py                      # Point d'entrée principal
    ├── config/
    │   ├── __init__.py
    │   ├── settings.py              # Gestion de la configuration
    │   └── simulation_config.json   # Fichier de config
    ├── core/
    │   ├── __init__.py
    │   ├── alert_capture.py         # Capture des alertes
    │   ├── portfolio.py             # Classe Portfolio
    │   ├── position.py              # Classe Position
    │   ├── position_manager.py      # Gestion des positions
    │   ├── price_monitor.py         # Surveillance des prix
    │   └── exit_strategy.py         # Logique d'exit
    ├── filters/
    │   ├── __init__.py
    │   ├── base_filter.py           # Classe de base
    │   ├── empirical_filters.py     # Filtres Max WR, Équilibré, Big Winners
    │   └── ml_filters.py            # Filtres p_success
    ├── v5/
    │   ├── __init__.py
    │   ├── watchlist.py             # Gestion watchlist V5
    │   ├── condition_checker.py     # Vérification des 6 conditions
    │   ├── indicators.py            # EMA, Ichimoku, CHoCH
    │   └── trendline.py             # Détection trendlines
    ├── data/
    │   ├── __init__.py
    │   ├── binance_client.py        # Client API Binance
    │   ├── alerts_client.py         # Client API Alerts
    │   └── database.py              # Gestion SQLite
    ├── api/
    │   ├── __init__.py
    │   ├── routes.py                # Endpoints API dashboard
    │   └── websocket.py             # WebSocket temps réel
    └── utils/
        ├── __init__.py
        ├── logger.py                # Logging
        └── helpers.py               # Fonctions utilitaires
```

### 10.2 Classes Principales

#### Portfolio

```python
@dataclass
class Portfolio:
    id: str                          # "max_wr", "balanced_ml", etc.
    name: str                        # "Max Win Rate"
    type: str                        # "empirical_filter" | "p_success_threshold" | "v5_surveillance"
    enabled: bool
    initial_balance: float
    current_balance: float
    cash_available: float
    position_size_pct: float
    max_concurrent_trades: int

    # Statistiques
    total_trades: int
    winners: int
    losers: int
    total_profit: float
    total_loss: float
    peak_balance: float
    max_drawdown: float

    # Positions
    open_positions: List[Position]
    closed_positions: List[Position]

    # Config spécifique
    filter_config: Optional[Dict]     # Pour filtres empiriques
    threshold: Optional[float]        # Pour seuils p_success
    v5_config: Optional[Dict]         # Pour V5
```

#### Position

```python
@dataclass
class Position:
    id: str
    portfolio_id: str
    alert_id: str
    pair: str

    # Entry
    entry_price: float
    entry_timestamp: datetime
    allocated_capital: float

    # Current state
    current_price: float
    highest_price: float
    current_pnl_pct: float
    current_pnl_usd: float

    # SL Management
    initial_sl: float
    current_sl: float
    be_activated: bool
    trailing_activated: bool
    trailing_sl: Optional[float]

    # Exit
    exit_price: Optional[float]
    exit_timestamp: Optional[datetime]
    exit_reason: Optional[str]        # "STOP_LOSS" | "BREAK_EVEN" | "TRAILING_STOP"
    final_pnl_pct: Optional[float]
    final_pnl_usd: Optional[float]

    status: str                       # "OPEN" | "CLOSED"
```

#### WatchlistEntry (V5)

```python
@dataclass
class WatchlistEntry:
    id: str
    alert_id: str
    pair: str
    alert_timestamp: datetime
    deadline: datetime
    trendline_price: float

    # État des conditions
    conditions: Dict[str, bool]       # 6 conditions
    conditions_values: Dict[str, Any] # Valeurs actuelles

    # Monitoring
    last_check: Optional[datetime]
    check_count: int
    status: str                       # "WATCHING" | "ENTRY" | "EXPIRED"

    # Résultat
    entry_timestamp: Optional[datetime]
    entry_price: Optional[float]
```

---

## 11. BASE DE DONNÉES

### 11.1 Schéma SQLite

```sql
-- Table des alertes capturées
CREATE TABLE alerts (
    id TEXT PRIMARY KEY,
    pair TEXT NOT NULL,
    price REAL NOT NULL,
    alert_timestamp DATETIME NOT NULL,
    timeframes TEXT,                  -- JSON array
    scanner_score INTEGER,
    p_success REAL,
    confidence REAL,
    -- Indicateurs
    pp INTEGER,
    ec INTEGER,
    di_plus_4h REAL,
    di_minus_4h REAL,
    adx_4h REAL,
    vol_pct_max REAL,
    -- Filtres calculés
    filter_max_wr INTEGER,
    filter_balanced INTEGER,
    filter_big_winners INTEGER,
    -- Métadonnées
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table des portefeuilles
CREATE TABLE portfolios (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    initial_balance REAL NOT NULL,
    current_balance REAL NOT NULL,
    cash_available REAL NOT NULL,
    position_size_pct REAL NOT NULL,
    max_concurrent_trades INTEGER NOT NULL,
    -- Stats
    total_trades INTEGER DEFAULT 0,
    winners INTEGER DEFAULT 0,
    losers INTEGER DEFAULT 0,
    total_profit REAL DEFAULT 0,
    total_loss REAL DEFAULT 0,
    peak_balance REAL,
    max_drawdown REAL DEFAULT 0,
    -- Config
    config_json TEXT,                 -- JSON config
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Table des positions
CREATE TABLE positions (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL,
    alert_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    -- Entry
    entry_price REAL NOT NULL,
    entry_timestamp DATETIME NOT NULL,
    allocated_capital REAL NOT NULL,
    -- Current
    current_price REAL,
    highest_price REAL,
    current_pnl_pct REAL,
    current_pnl_usd REAL,
    -- SL Management
    initial_sl REAL NOT NULL,
    current_sl REAL NOT NULL,
    be_activated INTEGER DEFAULT 0,
    trailing_activated INTEGER DEFAULT 0,
    trailing_sl REAL,
    -- Exit
    exit_price REAL,
    exit_timestamp DATETIME,
    exit_reason TEXT,
    final_pnl_pct REAL,
    final_pnl_usd REAL,
    -- Status
    status TEXT DEFAULT 'OPEN',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    -- Foreign keys
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id),
    FOREIGN KEY (alert_id) REFERENCES alerts(id)
);

-- Table watchlist V5
CREATE TABLE v5_watchlist (
    id TEXT PRIMARY KEY,
    alert_id TEXT NOT NULL,
    pair TEXT NOT NULL,
    alert_timestamp DATETIME NOT NULL,
    deadline DATETIME NOT NULL,
    trendline_price REAL NOT NULL,
    -- Conditions (JSON)
    conditions_json TEXT,
    conditions_values_json TEXT,
    -- Monitoring
    last_check DATETIME,
    check_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'WATCHING',
    -- Result
    entry_timestamp DATETIME,
    entry_price REAL,
    position_id TEXT,
    -- Métadonnées
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (alert_id) REFERENCES alerts(id),
    FOREIGN KEY (position_id) REFERENCES positions(id)
);

-- Table historique des balances (pour graphiques)
CREATE TABLE balance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    portfolio_id TEXT NOT NULL,
    balance REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (portfolio_id) REFERENCES portfolios(id)
);

-- Table configuration
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX idx_positions_portfolio ON positions(portfolio_id);
CREATE INDEX idx_positions_status ON positions(status);
CREATE INDEX idx_alerts_timestamp ON alerts(alert_timestamp);
CREATE INDEX idx_v5_watchlist_status ON v5_watchlist(status);
CREATE INDEX idx_balance_history_portfolio ON balance_history(portfolio_id);
```

---

## 12. API ENDPOINTS

### 12.1 Endpoints Dashboard

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/overview` | Vue d'ensemble (stats globales) |
| GET | `/api/portfolios` | Liste des portefeuilles |
| GET | `/api/portfolios/{id}` | Détail d'un portefeuille |
| GET | `/api/positions` | Toutes les positions ouvertes |
| GET | `/api/positions/{id}` | Détail d'une position |
| GET | `/api/history` | Historique des trades |
| GET | `/api/watchlist` | Watchlist V5 |
| GET | `/api/watchlist/{id}` | Détail watchlist entry |
| GET | `/api/config` | Configuration actuelle |
| PUT | `/api/config` | Mise à jour config |
| POST | `/api/simulation/start` | Démarrer simulation |
| POST | `/api/simulation/stop` | Arrêter simulation |
| GET | `/api/simulation/status` | État de la simulation |

### 12.2 WebSocket Events

| Event | Direction | Description |
|-------|-----------|-------------|
| `alert_received` | Server → Client | Nouvelle alerte capturée |
| `position_opened` | Server → Client | Position ouverte |
| `position_updated` | Server → Client | Mise à jour position |
| `position_closed` | Server → Client | Position fermée |
| `watchlist_updated` | Server → Client | Mise à jour watchlist V5 |
| `balance_updated` | Server → Client | Mise à jour balance portefeuille |

---

## 13. MÉTRIQUES ET KPIs

### 13.1 Métriques par Portefeuille

| Métrique | Formule | Description |
|----------|---------|-------------|
| **Balance** | cash + Σ(positions.allocated) | Capital total |
| **P&L $** | balance - initial_balance | Profit/Perte absolu |
| **P&L %** | (P&L $ / initial) × 100 | Rendement |
| **Win Rate** | (winners / total_trades) × 100 | Taux de réussite |
| **Profit Factor** | total_profit / total_loss | Ratio gains/pertes |
| **Max Drawdown $** | peak - min_after_peak | Perte max depuis peak |
| **Max Drawdown %** | (DD $ / peak) × 100 | Drawdown relatif |
| **Avg Win** | total_profit / winners | Gain moyen |
| **Avg Loss** | total_loss / losers | Perte moyenne |
| **Risk/Reward** | Avg Win / Avg Loss | Ratio R/R |
| **Expectancy** | (WR × Avg Win) - ((1-WR) × Avg Loss) | Espérance par trade |

### 13.2 Métriques Comparatives

| Métrique | Description |
|----------|-------------|
| **Best Portfolio** | Portefeuille avec le meilleur P&L % |
| **Most Trades** | Portefeuille avec le plus de trades |
| **Highest WR** | Portefeuille avec le meilleur win rate |
| **Best PF** | Portefeuille avec le meilleur profit factor |
| **Lowest DD** | Portefeuille avec le plus faible drawdown |

### 13.3 Métriques V5 Spécifiques

| Métrique | Description |
|----------|-------------|
| **Conversion Rate** | % alertes watchlist → entries |
| **Avg Time to Entry** | Temps moyen avant entry |
| **Expiration Rate** | % alertes expirées sans entry |
| **Condition Hit Rate** | % de chaque condition validée |

---

## 14. GESTION DES ERREURS

### 14.1 Catégories d'Erreurs

| Catégorie | Exemples | Action |
|-----------|----------|--------|
| **API Alert** | Timeout, 500, connexion | Retry avec backoff |
| **API Binance** | Rate limit, timeout | Queue + retry |
| **Database** | Lock, corruption | Rollback + alert |
| **Calcul** | Division par 0, NaN | Valeur par défaut + log |

### 14.2 Stratégies de Retry

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay_sec": 1,
    "backoff_multiplier": 2,
    "max_delay_sec": 30
}
```

### 14.3 Logging

```python
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "handlers": ["console", "file"],
    "file_path": "logs/simulation.log",
    "rotation": "daily",
    "retention": 30  # jours
}
```

---

## 15. DÉPLOIEMENT

### 15.1 Prérequis

- Python 3.10+
- Node.js 18+ (pour dashboard)
- SQLite 3
- Accès API: localhost:9000 (alerts), api.binance.com

### 15.2 Installation

```bash
# Backend
cd mega-buy-ai/simulation
pip install -r requirements.txt

# Dashboard
cd mega-buy-ai/dashboard
npm install
```

### 15.3 Démarrage

```bash
# Démarrer le service de simulation
python -m simulation.main

# Démarrer le dashboard (port 9000)
cd dashboard && npm run dev
```

### 15.4 Variables d'Environnement

```bash
# .env
SIMULATION_DB_PATH=./data/simulation.db
ALERTS_API_URL=http://localhost:9000/api/alerts
BINANCE_API_URL=https://api.binance.com
LOG_LEVEL=INFO
DASHBOARD_PORT=9001
```

---

## ANNEXES

### A. Glossaire

| Terme | Définition |
|-------|------------|
| **BE** | Break-Even - niveau où le SL est déplacé à l'entrée |
| **CHoCH** | Change of Character - cassure structure |
| **Cloud Top** | Maximum entre Senkou-A et Senkou-B (Ichimoku) |
| **P&L** | Profit and Loss |
| **PF** | Profit Factor |
| **SL** | Stop Loss |
| **TL** | Trendline |
| **TSL** | Trailing Stop Loss |
| **WR** | Win Rate |

### B. Formules des Indicateurs

**EMA (Exponential Moving Average)**:
```
EMA[i] = close[i] × k + EMA[i-1] × (1-k)
k = 2 / (period + 1)
```

**Ichimoku Cloud Top**:
```
Tenkan = (Highest_9 + Lowest_9) / 2
Kijun = (Highest_26 + Lowest_26) / 2
Senkou_A = (Tenkan + Kijun) / 2
Senkou_B = (Highest_52 + Lowest_52) / 2
Cloud_Top = max(Senkou_A, Senkou_B)
```

**Swing High Detection**:
```
is_swing_high[i] = (
    high[i] > max(high[i-5:i]) AND
    high[i] > max(high[i+1:i+4])
)
```

---

**FIN DU RAPPORT**

*Document généré le 2026-03-19*
*Version 1.0*
