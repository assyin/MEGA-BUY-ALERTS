# 🔬 V11B — Review des 5 recommandations Claude Chat + 6 Q techniques

_Généré : 2026-04-28 — basé sur 199 trades fermés V11B Compression_

**Méthodologie** : pour chaque reco/question, données empiriques calculées via `scripts/analyze_v11b_recos.py` (peak distribution, peak timing, walk-forward, métriques risque, breakdown WR par decision/score).

---

## 📊 Verdict synthèse — table de décision

| # | Recommandation Claude Chat | Verdict | Effort | Fichiers à toucher |
|---|---|---|---|---|
| **#1** | Exclure WATCH du filtre V11B | ✅ D'accord (avec nuance N=15) | S | `openclaw/portfolio/gates_v11.py` |
| **#2** | TP2 de +20% à +15% | 🔄 **INCOMPLÈTE — vraie réponse : TP2 = 13%** | S | `openclaw/portfolio/manager_v11.py` |
| **#3** | Timeout de 72h à 48h | 🔴 **REJET — données contredisent** | — | — |
| **#4** | NE PAS utiliser scanner_score | ✅ D'accord (CIs overlappent) | — | — |
| **#5** | Validation forward avant scaling | ✅ Indispensable | M | nouveau `paper_tracker.py` |
| **Q-A** | Walk-forward holdout | ✅ V11B PASSE (+3.4pts test vs train) | done | — |
| **Q-B** | Position sizing dynamique | 🟡 Différer (DD déjà 1.21%) | M | `manager_v11.py` |
| **Q-C** | Cap exposure simultanée | 🟢 **Important manquant** | S | `manager_v11_base.py` |
| **Q-D** | Métriques risque (Sharpe/PF/streaks) | 🟢 Trivial à ajouter | S | `audit_v11b_*.py` |
| **Q-E** | Détection régime macro | 🔴 Hors scope — trop gros | L | gros chantier |

---

# 🔍 Reco #1 — Exclure les décisions OpenClaw "WATCH"

## Données empiriques

```
Decision     | N    | WR     | Avg PnL/trade  | Total PnL
BUY STRONG   |  85  | 85.9%  | $+30.40/tr     | $+2,583.83
BUY          |  47  | 87.2%  | $+29.72/tr     | $+1,396.96
BUY WEAK     |  17  | 100.0% | $+31.55/tr     | $+536.40
BACKFILL     |  34  | 85.3%  | $+28.59/tr     | $+972.05
WATCH        |  15  | 66.7%  | $+13.24/tr     | $+198.58   ← outlier
```

## Analyse statistique

- WATCH WR = 66.7% sur **N=15** (petit)
- CI 95% Wilson sur WATCH : **[42% – 85%]** — large incertitude
- Gap directionnel net : -19pts vs autres
- Hypothèse Claude chat ("moteur hésite donc setup ambigu") plausible

## Verdict : ✅ D'accord avec nuance

La direction est claire mais **N=15 ne permet pas de conclure définitivement**. Risque de tuning sur du bruit (multiple testing creep).

## Action recommandée

**Ne PAS implémenter immédiatement** dans le gate.
- Logguer un warning quand V11B accepte un WATCH (audit trail)
- Re-vérifier après **N=50 WATCH** trades
- Si WR WATCH reste <75% → ajouter le filtre

## Effort

- **S (~5 min)** quand validé. Code :
```python
# gates_v11.py, dans gate_v11b() :
if alert.get("agent_decision") == "WATCH":
    return False, "WATCH decision (low quality on V11B)"
```

---

# 🔍 Reco #2 — TP2 +20% → +15% (INCOMPLÈTE)

## Distribution des peaks (données critiques)

```
Trades qui ont touché TP1 (peak ≥ 10%) : N=121
Median peak : 19.11%
Mean peak   : 21.13%

Histogramme des peaks :
  10-12.5% : 21 ████████████████████████████
  12.5-15% : 21 ████████████████████████████  ← pic 1
  15-17.5% : 13 ███████████████
  17.5-20% : 11 █████████████
  20-25%   : 22 ██████████████████████████████  ← pic 2
  25-30%   : 14 ███████████████████
  30-40%   : 12 ████████████████
  40-60%   :  7 █████████
```

**Distribution bimodale** : pic à 12% ET pic à 22%.

## Simulation PnL avec différents TP2 (TP1=10% fixe, Trail=8% du peak sur 20% restant)

| TP2 | TP2-hit count | Total PnL backtest |
|---|---|---|
| 12% | 102 | $+5,323 |
| **13%** | 97 | **$+5,349** ⭐ optimum |
| 15% (Claude chat) | 79 | $+5,174 |
| 17.5% | 66 | $+5,052 |
| **20% (actuel)** | 55 | **$+4,890** baseline |
| 22.5% | 42 | $+4,569 |
| 25% | 33 | $+4,313 |

## Pourquoi TP2 plus bas est meilleur ?

Avec TP2=13%, **plus de trades convertissent en TP2 partial** (+97 vs 55). Le trail récupère ensuite le reste sur 20% du capital.

Avec TP2=20%, beaucoup de trades stagnent à +12-18% et finissent BE-stop sur les 50% restants → on **perd la fenêtre** entre +10% et +20%.

## Verdict : 🔄 Reco directionnellement correcte mais sous-tirée

Claude chat a vu "le mode est vers +10-15%" → vrai. Mais 15% n'est pas optimal.
**Optimum = TP2 = 13%**, gain backtest = **+$459 / +9.4% PnL**.

## Action recommandée

**Implémenter TP2=13% pour V11B uniquement.** Garder 20% pour V11A/C/D/E (l'optimum peut différer par variant).

## Effort

- **S (~10 min)** :
- Override `TP2_PCT` dans la sous-classe `PortfolioManagerV11B` au lieu de constantes du base
- Fichier : `mega-buy-ai/openclaw/portfolio/manager_v11.py`

⚠️ **Avertissement** : la backtest est sur 30 jours. Le TP2 optimum peut bouger avec un autre régime de marché. À ré-évaluer trimestriellement.

---

# 🔍 Reco #3 — Timeout 72h → 48h (REJETÉ)

## Données critiques — peak timing pour 109 TIMEOUT trades (5m klines fetched de Binance)

```
Bucket  | Count | %     | Avg peak %
--------|-------|-------|-----------
  0-12h |   4   |  3.7% | +11.12%
 12-24h |   7   |  6.4% | +7.33%
 24-36h |  11   | 10.1% | +9.52%
 36-48h |  13   | 11.9% | +9.38%
 48-60h |  19   | 17.4% | +13.46%
 60-72h |  55   | 50.5% | +10.75%

PEAK avant h48 : 32.1%
PEAK après h48 : 67.9%   ← l'inverse de ce que Claude chat suppose
```

## Verdict : 🔴 Rejet net

**Hypothèse Claude chat invalidée par les données** : "si pas de mouvement après 48h → ne continuera plus statistiquement" est **FAUX**.

→ Couper à 48h supprimerait **67.9% des opportunités de peak** sur les TIMEOUT trades. C'est l'inverse de ce qu'on veut.

## Recommandation contre-intuitive

Tester un timeout **PLUS LONG** (96h ou 120h) :
- 50.5% des peaks sont dans les **dernières 12h** (60-72h)
- Suggère que le breakout de compression met du temps à se développer
- Trade-off : occupe le slot longtemps. Avec MAX_POSITIONS=12 et ~6 alertes V11B/jour, peu de risque de saturation.

## Action recommandée

**Ne PAS toucher** le timeout 72h actuel. Possible test futur : variant V11B-bis avec timeout=96h pour A/B.

---

# 🔍 Reco #4 — Pas de filtre scanner_score

## Données

```
Score | N    | W    | L   | WR     | Avg PnL  | CI 95% Wilson
   5  |   1  |  1   |  0  | 100.0% | +13.43%  | [20.7 – 100%]   (noise)
   6  |  14  | 12   |  2  |  85.7% |  +7.68%  | [60.1 – 96.0%]
   7  |  25  | 25   |  0  | 100.0% |  +7.16%  | [86.7 – 100%]
   8  |  64  | 55   |  9  |  85.9% |  +7.08%  | [75.4 – 92.4%]
   9  |  86  | 69   | 17  |  80.2% |  +7.01%  | [70.6 – 87.3%]   ← worst, biggest N
  10  |   9  |  9   |  0  | 100.0% |  +7.37%  | [70.1 – 100%]
```

## Analyse

- Score 9 (N=86, le plus reliable) montre WR 80.2% — le plus bas.
- Score 7 (N=25) montre WR 100% — surprenant.
- **MAIS** les CIs Wilson **overlappent largement** :
  - Score 8 : [75.4 – 92.4%]
  - Score 9 : [70.6 – 87.3%]
  - Score 7 : [86.7 – 100%]
- Différence **non statistiquement significative** au seuil 95%.

## Hypothèse causale Claude chat

> "Score élevé = breakout fatigué (RSI haut, MACD étendu) → corrélation négative avec compression"

Plausible mais **non prouvée sur N=86**.

## Verdict : ✅ D'accord

Le scanner_score n'apporte **aucun edge discriminant** sur V11B. Ne pas filtrer dessus.

## Action positive alternative

Tester d'autres features comme **filtre additionnel** sur le top de V11B :
- BTC trend 1H (BULLISH only ?)
- EMA Stack 4H ≥ 3 ?
- MACD 4H BULLISH + growing ?
- Volume USDT ≥ seuil minimum ?

→ Sujet pour une **Phase D — Optimization additive** future.

---

# 🔍 Reco #5 — Validation forward avant scaling

## Métriques actuelles (suspicieusement bonnes)

```
Sharpe annualisé    : 49.68     ← extrême (S&P 500 ~1, top hedge funds 3-5)
Profit Factor       : 8.68      ← exceptionnel (>3 = excellent)
Max consecutive WIN : 28
Max consecutive LOSS:  3        ← très resilient
Max DD intra-period : 1.21%     ← extrêmement bas
Distribution streaks losses : 19×1, 3×2, 1×3
```

## Pourquoi ces chiffres sont "trop beaux"

1. **Backtest hydraté** : pas de slippage, pas de fees, latence parfaite
2. **Hybrid TP exit cap le downside** artificiellement (BE-stop après TP1)
3. **30 jours** = un seul régime macro, possible biais de fenêtre

**Dégradation attendue en live** : -5 à -10pts WR, Sharpe annualisé tombera à 1-3 (réaliste).

## Verdict : ✅ Critical

## Plan d'implémentation (3 phases)

### Phase 1 — Paper trading mode (M, ~2h)

Le bot tourne en mode "shadow" : ouvre des positions virtuelles avec timestamps + prix RÉELS Binance, ne touche pas au capital.

Implémentation :
- Flag `live_paper=true` dans `openclaw_positions_v11b`
- Tracker delta : pour chaque alerte V11B, comparer **prix exécution simulé** vs **prix exécution réel** (avec slippage estimé)
- Logguer dans table `v11b_paper_log` : alert_id, paper_pnl, expected_pnl, delta

### Phase 2 — Killswitch automatique (S, ~30 min)

```python
# Dans manager_v11.py.check_positions :
recent = self._get_last_n_closed(30)
if recent and len(recent) >= 30:
    wr = sum(1 for r in recent if (r.get("pnl_usd") or 0) > 0) / len(recent)
    if wr < 0.70:
        self._suspended = True
        await self._tg(f"⚠️ V11B SUSPENDED — WR {wr*100:.1f}% sur 30 dernières trades")
```

### Phase 3 — Live small ($500) après 50 trades paper (1 semaine)

- Si WR paper > 80% → activer V11B en live à $500/position pour 50 trades supplémentaires
- Si performance maintenue → scale à $1000-2000

### Critères go/no-go quantifiables

| Métrique | Target | Action si fail |
|---|---|---|
| WR live (50 trades) | ≥ 75% | STOP — investiguer biais |
| Sharpe annualisé | ≥ 1.5 | Acceptable si > 0 |
| Max DD live | ≤ 5% | STOP si dépasse |
| Slippage moyen | ≤ 0.3% | Acceptable jusqu'à 0.5% |
| Gap backtest vs live | ≤ 8pts WR | Investiguer si > 10pts |

## Effort total : M (~3-4h dev)

---

# 🔬 Q-A — Walk-forward holdout (FAIT)

## Méthode

Split chronologique 70/30 sur 199 trades :
- Train : premiers 139 trades (31/03 → 14/04, 14j)
- Test : derniers 60 trades (14/04 → 26/04, 12j)

## Résultats

```
Train (premiers 70%) : N=139 | 118W/21L | WR 84.9% | avg +6.60%
Test  (derniers 30%) : N=60  |  53W/7L  | WR 88.3% | avg +8.41%
Δ WR : +3.4pts (test STRONGER que train)
```

## Verdict : ✅ V11B passe le test out-of-sample

V11B **n'est PAS un faux positif** issu du multiple testing en discovery. Le strategy se maintient (et améliore légèrement) sur les données les plus récentes.

## Caveat

Le test set ne couvre que 12 jours. Pour validation rigoureuse, nécessite :
- Test set plus long (≥30j)
- Régime BTC différent du train (ex: bull vs sideways)

→ Le tracker live va naturellement le fournir au fil de l'eau.

---

# 💼 Q-B — Position sizing dynamique

## État actuel

`SIZE_PCT = 8.0` → $400 par position fixe, indépendant de la paire ou du contexte.

## Options évaluées

### Kelly fractionnel
- Stats observées : WR=86%, avg_win=10%, avg_loss=8%
- Kelly optimum théorique : `f* = (p×b - q) / b = (0.86×1.25 - 0.14)/1.25 = 76%` (insane)
- 1/4 Kelly fractionnel = 19% par position
- Avec 12 slots → exposure max = 228% du capital → **impossible en pratique**

### ATR-based (volatility-adjusted)
- Sizing inversement proportionnel à l'ATR de la paire
- Réduit l'exposition sur les paires sauvages (BOMEUSDT > BTCUSDT)
- Effort : refactor `try_open_position` pour fetcher ATR live = ~2h

## Verdict : 🟡 Différer

- DD actuel = **1.21%** (déjà excellent)
- Gain marginal attendu : peut-être -0.3pt DD, +0% PnL absolu
- Effort/impact pas favorable maintenant

**Action** : laisser sizing fixe 8% pour l'instant. Re-évaluer si DD live > 5%.

---

# 🛡 Q-C — Cap exposure simultanée (corrélation BTC)

## Code actuel

```python
# manager_v11_base.py
MAX_POSITIONS = 12   # cap absolu sur # positions concurrentes
MAX_PER_PAIR = 1     # 1 par paire
```

## Risque identifié

Si 12 alts ouverts simultanément et BTC dump -5% :
- Tous les alts corrèlent à ~1 dans un dump
- Perte cumulée potentielle : 12 × ~$32 (8% × $400) = **$384** simultané
- Soit **7.7% du capital** en un événement

## Solution propre (S, ~30 min)

```python
# Dans try_open_position(), avant insert :
btc_change_24h = alert.get("btc_change_24h_pct", 0)  # ou via market_sentiment
if btc_change_24h is not None and btc_change_24h <= -3:
    # Mode prudence : max 6 positions concurrentes
    if len(open_positions) >= 6:
        return None
```

## Variantes

- Cap dynamique : `max_positions = 12 if btc_change >= 0 else 8 if btc_change >= -3 else 4`
- Pause de nouveaux trades si DD intra-jour > 3%

## Effort

**S (~30 min)** sur `manager_v11_base.py` + test smoke.

---

# 📊 Q-D — Métriques risque manquantes

## Ajouts triviaux (S, ~30 min)

Toutes calculables depuis les données existantes. À ajouter au summary HTML/MD :

```python
# Sharpe per-trade : mean(returns) / stdev(returns)
# Sharpe annualisé : sharpe_per_trade × sqrt(trades_per_year)
# Profit Factor : sum(positive_returns) / |sum(negative_returns)|
# Max consec losses : itérer la liste des trades, compter
# Recovery time : à partir de quand le balance rebondit du DD max
```

## Implémentation

Modifier `audit_v11b_html.py` (et `audit_v11b_trades.py` MD version) pour inclure une nouvelle section "⚠️ Risk metrics" avec :
- Sharpe per-trade + annualisé
- Profit Factor
- Max consecutive wins/losses
- Distribution des séries de pertes
- Max drawdown intra-période
- Recovery time

---

# 🌍 Q-E — Détection de régime macro

## Pourquoi c'est pertinent

Les 30j de V11B couvrent un seul régime BTC. Le filtre Compression peut performer différemment en :
- BTC range : haute volatilité altcoins → compressions tactiques
- BTC strong trend : altcoins suivent → moins de compressions
- BTC capitulation : tout dump, compressions = pièges

## Effort estimé : L (~1-2 jours dev)

1. **Définir 4 régimes** : RANGE, BULL_TREND, BEAR_TREND, CAPITULATION
2. **Classifier** chaque alerte historique selon régime au moment T
3. **Buckets** : WR/PnL par régime
4. **Conditioner** : ne trader V11B que dans régimes favorables

## Verdict : 🔴 Différer

Trop tôt. Recommandation :
1. Laisser le tracker live tourner 60-90j
2. Quand on a vraiment 2-3 régimes différents dans les data
3. Alors ré-évaluer avec analyse régime-conditionnée

---

# 🎯 Q-F — Roadmap priorisée par impact/effort

## ⚡ TIER 1 — High impact / Low effort (cette semaine)

| Action | Impact attendu | Effort | Files |
|---|---|---|---|
| **Reco #2 → TP2 = 13% pour V11B** | +$459 PnL backtest (+9.4%) | S (10 min) | `manager_v11.py` |
| **Q-D → Sharpe / PF / streaks au reporting** | Visibilité décisionnelle | S (30 min) | `audit_v11b_html.py`, `audit_v11b_trades.py` |
| **Q-C → BTC dump cap (max 6 si BTC -3%)** | Réduit risque tail | S (30 min) | `manager_v11_base.py` |

**Total : ~1h10 dev pour gain mesurable + safety net.**

## 🟡 TIER 2 — Medium effort / Medium impact (prochaine semaine)

| Action | Impact | Effort | Files |
|---|---|---|---|
| **Reco #5 P1 — Paper trading mode** | Mesure dégradation backtest→live | M (2h) | nouveau `paper_tracker.py` |
| **Reco #5 P2 — Killswitch automatique** | Safety net sur drift live | S (30 min) | `manager_v11.py` |
| **Reco #1 — Filtre WATCH (après N=50)** | Marginal (gap statistiquement faible) | S (5 min) | `gates_v11.py` — DIFFÉRÉ |

## 🔴 TIER 3 — Différer ou rejeter

| Action | Raison |
|---|---|
| **Reco #3 — Timeout 48h** | ❌ Données contredisent (67.9% peaks après h48) |
| **Reco #4 — Filtre score** | ❌ Pas d'edge statistique (CIs overlap) |
| **Q-B — Kelly sizing** | DD déjà 1.21% — gain marginal incertain |
| **Q-E — Régime macro** | Trop gros — re-évaluer après 90j live |

---

# 📌 Plan d'action concret pour aujourd'hui

```
ÉTAPE 1 (10 min) :
  manager_v11.py
  └── Override TP2_PCT = 13.0 dans PortfolioManagerV11B

ÉTAPE 2 (30 min) :
  audit_v11b_html.py + audit_v11b_trades.py
  └── Ajouter section "⚠️ Risk metrics" :
      ├── Sharpe per-trade + annualisé
      ├── Profit Factor
      ├── Max consecutive losses
      └── Distribution streaks

ÉTAPE 3 (30 min) :
  manager_v11_base.py
  └── Ajouter check BTC dump :
      if btc_change_24h <= -3 and len(open_positions) >= 6:
          return None, "BTC dump risk"

ÉTAPE 4 (vérification) :
  pm2 restart mega-openclaw
  └── Confirmer dans logs : "V11B started — TP2=13%"

ÉTAPE 5 (cette semaine) :
  Lancer Reco #5 Phase 1 (paper trading mode)
  └── ~3-4h dev étalé

ÉTAPE 6 (1 mois) :
  Re-tourner ce script `analyze_v11b_recos.py`
  └── Voir si conclusions tiennent avec +200 trades supplémentaires
```

---

# ⚠️ Caveats généraux

1. **Toutes ces conclusions sont sur 199 trades / 30 jours / 1 régime BTC**. À ré-évaluer trimestriellement.
2. **L'optimisation TP2** peut différer entre V11A/B/C/D/E. Ce rapport ne couvre que V11B. Refaire le même exercice pour les autres si on les scale.
3. **Le killswitch <70% WR sur 30 trades** est conservateur. Peut générer des faux positifs si bad streak naturelle. À calibrer.
4. **Les chiffres backtest seront dégradés en live** (slippage, fees, latence). Compter -5 à -10pts WR.

---

_Ce rapport est généré automatiquement par les scripts d'analyse. Pour le re-générer après nouveaux trades : `python3 scripts/analyze_v11b_recos.py`._
