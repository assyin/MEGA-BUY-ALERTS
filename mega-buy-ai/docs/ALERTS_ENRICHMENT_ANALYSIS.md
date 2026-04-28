# Analyse : Enrichissement des Alertes MEGA BUY

## Objectif
Reproduire dans la page `/alerts` le maximum d'informations disponibles dans le modal de trade validé du backtest, **sans lancer de backtest** — en calculant les données en temps réel depuis Binance au moment de l'alerte.

---

## 1. Données DEJA disponibles dans Supabase (aucun calcul nécessaire)

Ces champs existent déjà dans la table `alerts` Supabase et sont retournés par l'API `/api/simulation/alerts` :

| Catégorie | Champs | Description |
|-----------|--------|-------------|
| **Identité** | `id`, `pair`, `price`, `alert_timestamp`, `created_at` | Identifiant, paire, prix, horodatage |
| **Score** | `scanner_score` (0-10) | Score MEGA BUY |
| **Timeframes** | `timeframes` (array), `bougie_4h` | Combo TF détectée + bougie 4H |
| **Conditions MEGA BUY** | `rsi_check`, `dmi_check`, `ast_check` | 3 conditions mandatoires |
| **Bonus MEGA BUY** | `choch`, `zone`, `lazy`, `vol`, `st`, `pp`, `ec` | 7 conditions optionnelles |
| **Indicateurs 4H** | `di_plus_4h`, `di_minus_4h`, `adx_4h` | DMI/ADX sur 4H |
| **Volume** | `vol_pct` (dict par TF) | Volume % par timeframe |
| **Puissance** | `puissance` | Score de puissance du signal |
| **Emotion** | `emotion` | Sentiment du marché |
| **ML Decision** | `p_success`, `confidence` (table `decisions`) | Prédiction IA |

**Total : ~20 champs, affichage immédiat.**

---

## 2. Données CALCULABLES en temps réel (fetch Binance à l'ouverture du modal)

Ces données n'existent pas dans Supabase mais peuvent être calculées live en fetchant les klines Binance au moment où l'utilisateur clique sur une alerte.

### 2.1 Prérequis V5 (3 conditions)

| Champ | Calcul | Données requises |
|-------|--------|-----------------|
| `stc_validated` | Adaptive Stochastic < 0.2 sur au moins 1 TF (15m/30m/1h) | Klines 15m/30m/1h (60 bars chaque) |
| `stc_valid_tfs` | Quels TF passent le STC | Même données |
| `is_15m_alone` | Signal uniquement 15m ? | Déjà dans `timeframes` |
| `has_trendline` | Trendline existe sur 4H | Klines 4H (60 bars) |
| `tl_type` | Type : major/local | Swing highs 4H |
| `tl_price_at_alert` | Prix de la trendline au moment de l'alerte | Interpolation linéaire |

**API call : 4 fetches Binance (15m, 30m, 1h, 4h)**

### 2.2 Trendline (détection + break)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `tl_p1_date/price` | Point 1 de la trendline (swing high majeur) | `find_swing_highs(left=5, right=3)` sur 4H |
| `tl_p2_date/price` | Point 2 (swing high récent) | Idem |
| `tl_price_at_alert` | Prix TL au moment de l'alerte | Interpolation |
| `has_tl_break` | Close > trendline ? | Vérifier bougies post-alerte |
| `tl_break_datetime` | Quand le break a eu lieu | Première bougie au-dessus |
| `tl_break_price` | Prix au moment du break | Close à ce moment |
| `tl_break_delay_hours` | Heures depuis l'alerte | Calcul simple |
| `tl_retest_count` | Retests avant le break | Compter les croisements |

**Déjà inclus dans les klines 4H.**

### 2.3 Conditions Progressives (6 mandatoires - état actuel)

| Champ | Calcul | Données requises |
|-------|--------|-----------------|
| `price_1h > EMA100_1h` | Close 1H > EMA(100) | Klines 1H (110 bars) |
| `price_4h > EMA20_4h` | Close 4H > EMA(20) | Klines 4H (30 bars) |
| `price_1h > Cloud_1h` | Close 1H > max(Senkou-A, Senkou-B) | Klines 1H (60 bars) + Ichimoku |
| `price_30m > Cloud_30m` | Close 30m > Cloud Top | Klines 30m (60 bars) + Ichimoku |
| `CHoCH/BOS` | Swing high cassé avec marge 0.5% | Klines 1H (20 bars) |
| `TL Break` | Close > trendline | Klines 4H |

**Valeurs actuelles ET valeurs seuils (EMA, Cloud) pour savoir "combien il manque".**

### 2.4 Fibonacci (4H et 1H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `fib_swing_high/low` | Swing extremes sur 50 bars | 4H klines |
| `fib_levels` | 23.6%, 38.2%, 50%, 61.8%, 78.6% | Calcul standard |
| `fib_bonus` | Close > 38.2% | Vérification |
| Même chose pour 1H | | 1H klines |

**Déjà inclus dans les klines 4H et 1H.**

### 2.5 Indicateurs Techniques (à chaque moment clé)

#### ADX/DI Analysis (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `adx_value`, `di_plus`, `di_minus` | `calc_adx(14)` sur 1H et 4H |
| `di_spread` | DI+ - DI- |
| `adx_strength` | STRONG (>25), MODERATE (20-25), WEAK (<20) |

#### MACD (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `macd_line`, `macd_signal`, `macd_histogram` | EMA12 - EMA26, EMA9(MACD) |
| `macd_trend` | BULLISH/BEARISH/NEUTRAL |
| `macd_hist_growing` | Histogramme croissant ? |

#### Bollinger Bands (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `bb_upper/middle/lower` | SMA20 +/- 2*StdDev |
| `bb_width_pct` | Largeur en % |
| `bb_squeeze` | Bandes serrées (<2%) |
| `bb_breakout` | UP/DOWN/NONE |

#### Stochastic RSI (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `stoch_rsi_k/d` | Stochastique du RSI |
| `stoch_rsi_zone` | OVERSOLD/OVERBOUGHT/NEUTRAL |
| `stoch_rsi_cross` | BULLISH/BEARISH |

#### EMA Stack (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `ema8/21/50/100` | 4 EMAs |
| `ema_stack_bonus` | EMA8 > 21 > 50 > 100 ? |
| `ema_stack_count` | Combien en ordre (0-4) |

#### RSI Multi-TF
| Champ | Calcul |
|-------|--------|
| `rsi_1h/4h/daily` | RSI(14) sur 3 TFs |
| `rsi_mtf_bonus` | Tous > 50 ? |
| `rsi_aligned_count` | 0 à 3 |

#### Volume Spike (1H + 4H)
| Champ | Calcul |
|-------|--------|
| `vol_ratio` | Volume actuel / moyenne 20 bars |
| `vol_spike_level` | NORMAL / HIGH (>2x) / VERY_HIGH (>3x) |

**Total fetch : 5 TFs (15m, 30m, 1h, 4h, 1d) — ~5 appels Binance.**

### 2.6 Corrélations BTC/ETH (1H + 4H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `btc_price/ema20/ema50/rsi` | Fetch BTCUSDT 1H + 4H | Tendance BTC |
| `btc_trend` | BULLISH/BEARISH/NEUTRAL | EMA20>EMA50 + RSI>50 |
| `eth_price/ema20/ema50/rsi` | Fetch ETHUSDT 1H + 4H | Tendance ETH |
| `eth_trend` | BULLISH/BEARISH/NEUTRAL | Même logique |

**4 appels supplémentaires : BTCUSDT 1H+4H, ETHUSDT 1H+4H.**

### 2.7 CVD - Cumulative Volume Delta (1H + 4H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `cvd_value` | Somme(close > open ? vol : -vol) | Delta volume cumulé |
| `cvd_trend` | RISING/FALLING/FLAT | Pente sur 5 bars |
| `cvd_divergence` | Prix monte mais CVD descend | Divergence baissière |
| `cvd_score` | 0-100 | Score global CVD |
| `cvd_label` | STRONG BUY / BUY / WEAK | Label |

**Calculé à partir des klines déjà fetchées (pas d'appel supplémentaire).**

### 2.8 Volume Profile (1H + 4H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `vp_poc` | Point of Control (prix avec max volume) | Histogramme volume par prix |
| `vp_vah/val` | Value Area High/Low (70% du volume) | Zones de valeur |
| `vp_entry_position` | AT_POC / IN_VA / ABOVE_VA / BELOW_VA | Position de l'entrée |
| `vp_hvn/lvn` | High/Low Volume Nodes | Niveaux clés |
| `vp_score` | 0-100 | Score VP |

**Calculé à partir des klines déjà fetchées.**

### 2.9 Order Block SMC (1H + 4H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `ob_found` | Bougie opposée dans séquence | Foreign Candle OB |
| `ob_zone_high/low` | Zone de demande | Zone OB |
| `ob_strength` | STRONG/MODERATE/WEAK | Nombre de bougies |
| `ob_position` | INSIDE/ABOVE/BELOW | Position vs zone |
| `ob_retest` | Prix a retesté la zone ? | Confirmation |

**Calculé à partir des klines déjà fetchées.**

### 2.10 Fair Value Gap (1H + 4H)

| Champ | Calcul | Description |
|-------|--------|-------------|
| `fvg_found` | Gap entre 3 bougies consécutives | High[N-1] < Low[N+1] |
| `fvg_zone_high/low` | Zone FVG | Bornes du gap |
| `fvg_position` | INSIDE/ABOVE/BELOW | Position vs FVG |
| `fvg_filled_pct` | % rempli | Combien du gap a été comblé |

**Calculé à partir des klines déjà fetchées.**

---

## 3. Données qui NECESSITENT le backtest (non calculables en live)

Ces données ne peuvent pas être obtenues en temps réel car elles dépendent d'événements futurs post-alerte :

| Catégorie | Champs | Pourquoi impossible en live |
|-----------|--------|----------------------------|
| **Golden Box** | `v3_box_high/low`, `v3_breakout_dt`, `v3_retest_price/datetime`, `v3_hours_to_entry` | Nécessite le breakout + retest futur |
| **V3 Quality Score** | `v3_quality_score`, `v3_risk_level/score` | Basé sur le retest (événement futur) |
| **GB Power Score** | `gb_power_score/grade` + 10 composants | Calculé au moment du retest |
| **AI Agent Decision** | `agent_decision/score/grade`, facteurs | Analyse multi-indicateurs au moment de l'entry |
| **P&L** | `pnl_c`, `pnl_d`, `exit_price/datetime` | Résultat du trade (futur) |
| **Exit Info** | `trailing_active`, `tp1/tp2_hit`, `be_activated` | Événements post-entry |
| **Conditions at Retest** | Toutes les conditions "at retest time" | Le retest n'a pas encore eu lieu |
| **CVD at 4 moments** | `cvd_at_break/breakout/retest/entry` | Les 4 moments-clés sont futurs |
| **ADX/DI at 4 moments** | `adx_di_1h_at_break/breakout/retest/entry` | Idem |

---

## 4. Synthèse : Ce qu'on peut afficher par alerte

### Tier 1 — Affichage immédiat (déjà dans Supabase)
- Score MEGA BUY (X/10) avec les 10 conditions colorées
- Timeframes combo
- Prix alerte + indicateurs 4H (DI+, DI-, ADX)
- Volume % par TF
- Decision IA (p_success, confidence)
- PP, EC, CHoCH, Zone, Lazy, Vol, ST

### Tier 2 — Calcul live au clic (fetch Binance ~9 appels)
- **Prérequis V5** : STC oversold, trendline, 15m alone
- **6 Conditions progressives** : EMA100, EMA20, Cloud 1H/30m, CHoCH/BOS, TL Break
  - Avec valeurs actuelles + seuils + distance en %
- **Fibonacci** 4H + 1H : 5 niveaux avec statut (cassé ou non)
- **15 Bonus filters** :
  - Fib 4H/1H, OB 1H/4H, BTC 1H/4H, ETH 1H/4H
  - FVG 1H/4H, Vol 1H/4H, RSI MTF (3/3)
  - ADX 1H/4H, MACD 1H/4H, BB 1H/4H
  - StochRSI 1H/4H, EMA Stack 1H/4H
- **CVD** : score, trend, divergence (1H + 4H)
- **Volume Profile** : POC, VAH, VAL, position (1H + 4H)
- **Corrélation BTC/ETH** : trend + RSI

### Tier 3 — Impossible en live (besoin backtest)
- Golden Box (box, breakout, retest)
- GB Power Score + AI Agent Decision
- P&L, Exit, Risk Assessment
- Indicateurs aux 4 moments-clés

---

## 5. Architecture technique recommandée

### API Backend (FastAPI - nouveau endpoint)
```
GET /api/alerts/{alert_id}/analysis
```
- Input : `pair`, `alert_timestamp`
- Fetch Binance : 15m(60), 30m(60), 1h(110), 4h(60), 1d(30), BTCUSDT 1h+4h, ETHUSDT 1h+4h
- Calcule tous les indicateurs Tier 2
- Retourne un JSON structuré

### Frontend (Next.js - modal au clic)
- Au clic sur une alerte → appel API → affichage progressif
- Sections pliables comme dans le modal backtest
- Indicateurs avec couleurs (vert=validé, rouge=non, jaune=partiel)

### Nombre total de fetches Binance par analyse
| Fetch | Paire | TF | Bars |
|-------|-------|----|------|
| 1 | PAIR | 15m | 60 |
| 2 | PAIR | 30m | 60 |
| 3 | PAIR | 1h | 110 |
| 4 | PAIR | 4h | 60 |
| 5 | PAIR | 1d | 30 |
| 6 | BTCUSDT | 1h | 60 |
| 7 | BTCUSDT | 4h | 30 |
| 8 | ETHUSDT | 1h | 60 |
| 9 | ETHUSDT | 4h | 30 |

**Total : 9 appels, ~2-3 secondes avec rate limiting.**

---

## 6. Indicateurs récupérables : Comptage final

| Catégorie | Nombre de champs | Source |
|-----------|-----------------|--------|
| Supabase (existant) | ~20 | Direct |
| Prérequis V5 | 6 | Binance live |
| Trendline | 8 | Binance 4H |
| Conditions progressives | 12 | Binance multi-TF |
| Fibonacci | 14 | Binance 4H + 1H |
| Order Block SMC | 20 | Binance 1H + 4H |
| Fair Value Gap | 16 | Binance 1H + 4H |
| BTC/ETH Corrélation | 16 | Binance BTC/ETH |
| Volume Spike | 8 | Binance 1H + 4H |
| RSI Multi-TF | 6 | Binance 1H + 4H + 1D |
| ADX/DI | 12 | Binance 1H + 4H |
| MACD | 12 | Binance 1H + 4H |
| Bollinger Bands | 12 | Binance 1H + 4H |
| Stochastic RSI | 8 | Binance 1H + 4H |
| EMA Stack | 12 | Binance 1H + 4H |
| CVD | 10 | Calculé des klines |
| Volume Profile | 15 | Calculé des klines |
| **TOTAL RECUPERABLE** | **~197 champs** | **9 appels Binance** |
| Non récupérable (backtest only) | ~180+ champs | Golden Box, P&L, AI Agent, etc. |

---

## 7. Priorité d'implémentation recommandée

### Phase 1 — Quick wins (données Supabase)
Afficher proprement les 20 champs existants dans un modal :
- Score coloré (X/10), 10 conditions avec icones
- TF combo, prix, DI+/DI-/ADX
- Decision IA (p_success avec couleur)

### Phase 2 — Conditions progressives + Prérequis
Au clic, fetch Binance et afficher :
- 3 prérequis (STC, 15m alone, TL)
- 6 conditions progressives avec barres de progression
- Distance actuelle vs seuil pour chaque condition

### Phase 3 — Bonus Filters (22 filtres)
Ajouter le tableau de bonus comme dans le backtest :
- Fib, OB, BTC, ETH, FVG, Vol, RSI MTF, ADX, MACD, BB, StochRSI, EMA
- Score X/22 avec couleurs

### Phase 4 — Analyses avancées
- CVD analysis (score + trend + divergence)
- Volume Profile (POC, VAH, VAL, position)
- ADX/DI détaillé

---

## Conclusion

Sur les **~380 champs** affichés dans le modal backtest, **~197 (52%)** sont récupérables en temps réel avec **9 appels Binance API** (~2-3s). Les **~180 champs restants (48%)** nécessitent le backtest car ils dépendent d'événements futurs (Golden Box retest, P&L, AI Agent decision au moment de l'entry).

La richesse des données calculables en live est largement suffisante pour donner une vue complète de la qualité technique d'une alerte MEGA BUY avant même qu'un trade soit exécuté.
