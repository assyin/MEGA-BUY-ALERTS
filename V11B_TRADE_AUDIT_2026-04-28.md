# 🔬 Audit detaille V11B Compression — chaque trade, entry & exit

_Genere : 2026-04-28 14:42 UTC_

**Filtre V11B** : `Range 30m ≤ 1.89%` ET `Range 4h ≤ 2.58%`
**Exit hybride V7** : TP1 50%@+10% / TP2 30%@+20% / Trail 20% à -8% du peak / SL initial -8% / Timeout 72h
**Capital initial** : $5,000 — **Size par position** : $400 (8%)

## 📊 Résumé global

- **Trades fermés** : 199
- **WR** : 85.9% (171W / 28L)
- **PnL total** : $+5689.70
- **Avg PnL/trade** : +7.15%
- **Hold time moyen** : 2j8h
- **Balance finale** : $10689.70 (init $5,000 → ROI +113.8%)

### Distribution close_reason

| Raison | Count | % |
|---|---:|---:|
| `TIMEOUT_72H` | 116 | 58.3% |
| `TRAIL_STOP` | 48 | 24.1% |
| `SL_HIT` | 20 | 10.1% |
| `BREAKEVEN_STOP` | 15 | 7.5% |

## 📊 Risk-adjusted metrics

| Metric | Value | Interpretation |
|---|---:|---|
| **Sharpe annualisé** | **53.55** | per-trade Sharpe × √(trades/an) |
| Sharpe per-trade | 1.010 | mean(ret) / stdev(ret) |
| **Profit Factor** | **8.68** | $wins / $losses (>1 = profitable) |
| **Calmar Ratio** | **815.52** | annualized return / max DD |
| Max drawdown | 1.97% | peak-to-trough on equity curve |
| Annualized return (linear) | +1608.3% | period return × 365/26j |
| Trades/an (extrapolated) | 2813 | window: 26j (199 trades) |
| Max losing streak | 4 | longest consecutive losses |
| Max winning streak | 59 | longest consecutive wins |
| Sum wins | $+6,430.14 | |
| Sum losses | $-740.44 | |

> ⚠️ Sharpe annualisé théorique. Ne pas comparer aux Sharpe traditionnels (S&P 500, hedge funds). En live, un Sharpe de 2-4 serait déjà excellent. Voir Profit Factor et Calmar pour des métriques plus interprétables.

### Streak distribution

| Length | Wins (count) | Losses (count) |
|---:|---:|---:|
| 1 | 4 | 15 |
| 2 | 2 | 3 |
| 3 | 3 | 1 |
| 4 | 2 | 1 |
| 5 | 2 | — |
| 7 | 2 | — |
| 19 | 1 | — |
| 21 | 1 | — |
| 23 | 1 | — |
| 59 | 1 | — |

## 🧪 Paper-trading slippage tracker (Reco #5 Phase 1)

Capture du prix Binance ~60s après l'alerte = exécution réaliste. `slip > 0` = prix monté après alerte (fill défavorable). `slip < 0` = prix redescendu (fill favorable).

_Pas encore de données paper. Appliquer `sql/v11_paper_tracker.sql` puis attendre quelques nouveaux trades._

## 📊 Paper P&L vs Backtest — Phase 1 critère go/no-go

**Couverture : 0/199 trades (0%)** — 199 trades sans paper data (bot restart, Binance error à T+60s, ou close avant T+60s).

_Pas encore de paper P&L. Lancer `scripts/backfill_paper_pnl.py` ou attendre les nouveaux closes après l'application du SQL._

## 🧊 BTC dump protection — historical impact on dataset

Distribution des trades par bucket `btc_change_24h` (au moment de l'alerte) + PnL réel observé. Donne une estimation du nombre de trades qui auraient été skippés par la nouvelle protection layered (-5% hard / -3% soft avec ≥6 open).

| Bucket BTC 24h | Trades | WR | PnL réel | PnL/trade | Action future |
|---|---:|---:|---:|---:|---|
| >= 0% | 90 | 85.6% | $+2,995.46 | $+33.28 | ✅ OK |
| [-3%, 0%) | 56 | 85.7% | $+1,234.67 | $+22.05 | ✅ OK |
| [-5%, -3%) | 12 | 100.0% | $+347.40 | $+28.95 | ⚠️ SOFT CAP si ≥6 open |
| <= -5% | 0 | 0.0% | $+0.00 | $+0.00 | 🛑 HARD STOP — toujours skippé |
| _no btc_change_24h_ | 41 | — | — | — | (FP missing field) |

### ⚠️ Validité du filtre

**1 trades** ne semblent pas correspondre au filtre V11B (données features manquantes ou seuils non respectés). Voir les badges 🚨 dans les cartes individuelles.

---

## 🏆 Top 5 winners

1. **NEIROUSDT** — +19.91% (+79.66$) — exit: `TRAIL_STOP`
2. **ZAMAUSDT** — +19.19% (+76.78$) — exit: `TRAIL_STOP`
3. **MOVRUSDT** — +18.28% (+73.12$) — exit: `TRAIL_STOP`
4. **ZAMAUSDT** — +17.99% (+71.98$) — exit: `TRAIL_STOP`
5. **STRKUSDT** — +17.88% (+71.52$) — exit: `TRAIL_STOP`

## 💔 Top 5 losers

1. **XAIUSDT** — -8.00% (-32.00$) — exit: `SL_HIT`
2. **NFPUSDT** — -8.00% (-32.00$) — exit: `SL_HIT`
3. **LISTAUSDT** — -8.00% (-32.00$) — exit: `SL_HIT`
4. **SUPERUSDT** — -8.00% (-32.00$) — exit: `SL_HIT`
5. **ALLOUSDT** — -8.00% (-32.00$) — exit: `SL_HIT`

---

## 📋 Audit complet — un trade par carte

_199 trades, classés par date d'ouverture (le plus ancien en premier)._

Chaque carte est dépliable : clique sur ▶️ pour voir le détail complet (entry rationale + exit narrative).

<details>
<summary>[#1] ✅ <b>NEOUSDT</b> +8.68% (+34.7$) — 2026-03-31 16:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.33%` ≤ 1.89%
- ✅ `range_4h = 2.48%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 1.79%
- RSI : 57.1
- ADX 4H : 23.5 (DI+ 25 / DI- 21)
- Change 24h : -0.83%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 11

### Exit

**Trajectoire** :
- Entry : `$2.6250`
- Peak atteint : `$2.9210` (**+11.28%** du peak)
- Exit : `$2.8180`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.35%)

**PnL final** : 💰 **+8.68%** (+34.70$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#2] ✅ <b>NEOUSDT</b> +8.68% (+34.7$) — 2026-03-31 16:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.33%` ≤ 1.89%
- ✅ `range_4h = 2.48%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 1.79%
- RSI : 57.1
- ADX 4H : 23.5 (DI+ 25 / DI- 21)
- Change 24h : -0.83%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 11

### Exit

**Trajectoire** :
- Entry : `$2.6250`
- Peak atteint : `$2.9210` (**+11.28%** du peak)
- Exit : `$2.8180`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.35%)

**PnL final** : 💰 **+8.68%** (+34.70$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#3] ❌ <b>SANTOSUSDT</b> -8.00% (-32.0$) — 2026-04-01 16:01 — exit: <code>SL_HIT</code> — hold 18.8h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.8%` ≤ 1.89%
- ✅ `range_4h = 1.25%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.88%
- RSI : 64.0
- ADX 4H : 19.3 (DI+ 30 / DI- 13)
- Change 24h : +0.98%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 8

### Exit

**Trajectoire** :
- Entry : `$1.1300`
- Peak atteint : `$1.1340` (**+0.35%** du peak)
- Exit : `$1.0396`
- Hold : 18.8h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $1.0396** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$1.2430`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#4] ✅ <b>FOGOUSDT</b> +7.89% (+31.6$) — 2026-04-05 00:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.32%` ≤ 1.89%
- ✅ `range_4h = 2.44%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.23%
- RSI : 71.5
- ADX 4H : 24.7 (DI+ 52 / DI- 13)
- Change 24h : +3.38%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.017450`
- Peak atteint : `$0.020760` (**+18.97%** du peak)
- Exit : `$0.018460`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+5.79%)

**PnL final** : 💰 **+7.89%** (+31.58$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#5] ✅ <b>MIRAUSDT</b> +17.28% (+69.1$) — 2026-04-05 20:01 — exit: <code>TRAIL_STOP</code> — hold 18.3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.79%` ≤ 1.89%
- ✅ `range_4h = 0.66%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.26%
- RSI : 57.7
- ADX 4H : 36.8 (DI+ 36 / DI- 7)
- Change 24h : +0.53%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.076400`
- Peak atteint : `$0.109100` (**+42.80%** du peak)
- Exit : `$0.100372`
- Hold : 18.3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.084040` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.091680` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.109100` (+42.80%)
- 🚪 Trail stop touché à `$0.100372` (+31.38%) → 20% fermé.

**PnL final** : 💰 **+17.28%** (+69.10$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#6] ✅ <b>PNUTUSDT</b> +5.00% (+20.0$) — 2026-04-05 23:01 — exit: <code>BREAKEVEN_STOP</code> — hold 1j9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.25%` ≤ 1.89%
- ✅ `range_4h = 2.3%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 1.52%
- RSI : 68.8
- ADX 4H : 21.7 (DI+ 42 / DI- 19)
- Change 24h : -0.74%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.040100`
- Peak atteint : `$0.044600` (**+11.22%** du peak)
- Exit : `$0.040100`
- Hold : 1j9h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.044110` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.040100`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#7] ✅ <b>ENAUSDT</b> +9.59% (+38.4$) — 2026-04-06 00:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.24%` ≤ 1.89%
- ✅ `range_4h = 1.12%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 0.50%
- RSI : 76.2
- ADX 4H : 26.7 (DI+ 37 / DI- 10)
- Change 24h : +1.63%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 13

### Exit

**Trajectoire** :
- Entry : `$0.080600`
- Peak atteint : `$0.094400` (**+17.12%** du peak)
- Exit : `$0.088000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+9.18%)

**PnL final** : 💰 **+9.59%** (+38.36$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#8] ✅ <b>ZBTUSDT</b> +13.12% (+52.5$) — 2026-04-06 08:01 — exit: <code>TRAIL_STOP</code> — hold 1j0h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.53%` ≤ 1.89%
- ✅ `range_4h = 1.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.81%
- RSI : 52.0
- ADX 4H : 23.2 (DI+ 30 / DI- 12)
- Change 24h : -2.38%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 13

### Exit

**Trajectoire** :
- Entry : `$0.099300`
- Peak atteint : `$0.119400` (**+20.24%** du peak)
- Exit : `$0.109848`
- Hold : 1j0h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.109230` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.119160` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.119400` (+20.24%)
- 🚪 Trail stop touché à `$0.109848` (+10.62%) → 20% fermé.

**PnL final** : 💰 **+13.12%** (+52.50$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#9] ❌ <b>BANANAS31USDT</b> -8.00% (-32.0$) — 2026-04-06 12:01 — exit: <code>SL_HIT</code> — hold 6.0h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.51%` ≤ 1.89%
- ✅ `range_4h = 1.4%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.71%
- RSI : 49.9
- ADX 4H : 36.9 (DI+ 24 / DI- 22)
- Change 24h : -10.52%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 13

### Exit

**Trajectoire** :
- Entry : `$0.010300`
- Peak atteint : `$0.010347` (**+0.46%** du peak)
- Exit : `$0.009476`
- Hold : 6.0h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.009476** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.011330`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#10] ✅ <b>KERNELUSDT</b> +5.00% (+20.0$) — 2026-04-06 16:01 — exit: <code>BREAKEVEN_STOP</code> — hold 1j11h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.01%` ≤ 1.89%
- ✅ `range_4h = 0.2%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.10%
- RSI : 53.3
- ADX 4H : 22.4 (DI+ 27 / DI- 14)
- Change 24h : -2.53%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 13

### Exit

**Trajectoire** :
- Entry : `$0.100100`
- Peak atteint : `$0.119800` (**+19.68%** du peak)
- Exit : `$0.100100`
- Hold : 1j11h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.110110` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.100100`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#11] ✅ <b>ZECUSDT</b> +14.77% (+59.1$) — 2026-04-07 08:01 — exit: <code>TRAIL_STOP</code> — hold 2j3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.38%` ≤ 1.89%
- ✅ `range_4h = 0.8%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (86% confiance)
- Bougie 4H : direction **green**, body 0.54%
- RSI : 65.3
- ADX 4H : 30.8 (DI+ 30 / DI- 11)
- Change 24h : +4.55%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 11

### Exit

**Trajectoire** :
- Entry : `$263.3400`
- Peak atteint : `$340.1600` (**+29.17%** du peak)
- Exit : `$312.9472`
- Hold : 2j3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$289.6740` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$316.0080` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$340.1600` (+29.17%)
- 🚪 Trail stop touché à `$312.9472` (+18.84%) → 20% fermé.

**PnL final** : 💰 **+14.77%** (+59.07$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#12] ❌ <b>SAGAUSDT</b> -8.00% (-32.0$) — 2026-04-08 00:01 — exit: <code>SL_HIT</code> — hold 23.5h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.03%` ≤ 1.89%
- ✅ `range_4h = 1.03%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **red**, body 0.68%
- RSI : 79.7
- ADX 4H : 27.3 (DI+ 48 / DI- 11)
- Change 24h : +2.82%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 11

### Exit

**Trajectoire** :
- Entry : `$0.029400`
- Peak atteint : `$0.029400` (**+0.00%** du peak)
- Exit : `$0.027048`
- Hold : 23.5h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.027048** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.032340`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#13] ❌ <b>PARTIUSDT</b> -8.00% (-32.0$) — 2026-04-09 12:02 — exit: <code>SL_HIT</code> — hold 8.4h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.27%` ≤ 1.89%
- ✅ `range_4h = 0.92%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.34%
- RSI : 46.5
- ADX 4H : 42.2 (DI+ 27 / DI- 11)
- Change 24h : +4.06%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 14

### Exit

**Trajectoire** :
- Entry : `$0.087300`
- Peak atteint : `$0.095000` (**+8.82%** du peak)
- Exit : `$0.080316`
- Hold : 8.4h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.080316** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.096030`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#14] ✅ <b>ARBUSDT</b> +6.44% (+25.7$) — 2026-04-10 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.58%` ≤ 1.89%
- ✅ `range_4h = 0.74%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 72.6
- ADX 4H : 37.3 (DI+ 36 / DI- 9)
- Change 24h : +3.05%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 14

### Exit

**Trajectoire** :
- Entry : `$0.108000`
- Peak atteint : `$0.122700` (**+13.61%** du peak)
- Exit : `$0.111100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+2.87%)

**PnL final** : 💰 **+6.44%** (+25.74$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#15] ✅ <b>ONTUSDT</b> +5.76% (+23.1$) — 2026-04-10 12:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.28%` ≤ 1.89%
- ✅ `range_4h = 0.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.57%
- RSI : 50.6
- ADX 4H : 22.6 (DI+ 27 / DI- 21)
- Change 24h : -3.71%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.080560`
- Peak atteint : `$0.093850` (**+16.50%** du peak)
- Exit : `$0.081790`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+1.53%)

**PnL final** : 💰 **+5.76%** (+23.05$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#16] ❌ <b>WCTUSDT</b> -8.00% (-32.0$) — 2026-04-10 20:03 — exit: <code>SL_HIT</code> — hold 1j6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.17%` ≤ 1.89%
- ✅ `range_4h = 0.17%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.17%
- RSI : 66.6
- ADX 4H : 27.3 (DI+ 43 / DI- 14)
- Change 24h : +1.23%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.057600`
- Peak atteint : `$0.057700` (**+0.17%** du peak)
- Exit : `$0.052992`
- Hold : 1j6h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.052992** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.063360`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#17] ✅ <b>HUMAUSDT</b> +13.85% (+55.4$) — 2026-04-11 16:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.99%` ≤ 1.89%
- ✅ `range_4h = 0.66%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **red**, body 0.13%
- RSI : 51.0
- ADX 4H : 22.2 (DI+ 30 / DI- 20)
- Change 24h : -1.81%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.015180`
- Peak atteint : `$0.018270` (**+20.36%** du peak)
- Exit : `$0.017340`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+14.23%)

**PnL final** : 💰 **+13.85%** (+55.38$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#18] ✅ <b>MANTAUSDT</b> +5.00% (+20.0$) — 2026-04-11 16:18 — exit: <code>BREAKEVEN_STOP</code> — hold 16.9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.34%` ≤ 1.89%
- ✅ `range_4h = 1.34%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.88%
- RSI : 59.6
- ADX 4H : 24.6 (DI+ 47 / DI- 14)
- Change 24h : +1.69%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.063420`
- Peak atteint : `$0.072960` (**+15.04%** du peak)
- Exit : `$0.063420`
- Hold : 16.9h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.069762` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.063420`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#19] ❌ <b>SKYUSDT</b> -8.00% (-32.0$) — 2026-04-11 18:48 — exit: <code>SL_HIT</code> — hold 1j17h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.92%` ≤ 1.89%
- ✅ `range_4h = 1.39%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.80%
- RSI : 61.8
- ADX 4H : 24.1 (DI+ 34 / DI- 16)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.078020`
- Peak atteint : `$0.078270` (**+0.32%** du peak)
- Exit : `$0.071778`
- Hold : 1j17h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.071778** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.085822`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#20] ❌ <b>DYDXUSDT</b> -3.13% (-12.5$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.13%` ≤ 1.89%
- ✅ `range_4h = 0.62%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.41%
- RSI : 77.5
- ADX 4H : 35.9 (DI+ 57 / DI- 10)
- Change 24h : +0.31%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.098200`
- Peak atteint : `$0.100370` (**+2.21%** du peak)
- Exit : `$0.095130`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.108020`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-3.13%** (-12.51$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#21] ❌ <b>MAGICUSDT</b> -4.11% (-16.5$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.48%` ≤ 1.89%
- ✅ `range_4h = 2.1%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.27%
- RSI : 63.4
- ADX 4H : 20.2 (DI+ 22 / DI- 11)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.063200`
- Peak atteint : `$0.063300` (**+0.16%** du peak)
- Exit : `$0.060600`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.069520`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-4.11%** (-16.46$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#22] ✅ <b>EDUUSDT</b> +8.27% (+33.1$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.68%` ≤ 1.89%
- ✅ `range_4h = 2.05%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.00%
- RSI : 67.2
- ADX 4H : 30.6 (DI+ 29 / DI- 12)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.044400`
- Peak atteint : `$0.051600` (**+16.22%** du peak)
- Exit : `$0.047300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+6.53%)

**PnL final** : 💰 **+8.27%** (+33.06$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#23] ❌ <b>MORPHOUSDT</b> -8.00% (-32.0$) — 2026-04-11 20:02 — exit: <code>SL_HIT</code> — hold 19.2h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.61%` ≤ 1.89%
- ✅ `range_4h = 0.55%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.38%
- RSI : 80.8
- ADX 4H : 30.2 (DI+ 42 / DI- 11)
- Change 24h : -0.87%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$1.8250`
- Peak atteint : `$1.8250` (**+0.00%** du peak)
- Exit : `$1.6790`
- Hold : 19.2h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $1.6790** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$2.0075`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#24] ✅ <b>IDUSDT</b> +5.00% (+20.0$) — 2026-04-11 20:02 — exit: <code>BREAKEVEN_STOP</code> — hold 15.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.91%` ≤ 1.89%
- ✅ `range_4h = 2.45%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.00%
- RSI : 55.0
- ADX 4H : 29.1 (DI+ 42 / DI- 5)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.033000`
- Peak atteint : `$0.036800` (**+11.52%** du peak)
- Exit : `$0.033000`
- Hold : 15.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.036300` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.033000`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#25] ❌ <b>UNIUSDT</b> -2.74% (-11.0$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.5%` ≤ 1.89%
- ✅ `range_4h = 2.23%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.87%
- RSI : 74.8
- ADX 4H : 29.2 (DI+ 42 / DI- 11)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$3.2090`
- Peak atteint : `$3.2580` (**+1.53%** du peak)
- Exit : `$3.1210`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$3.5299`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-2.74%** (-10.97$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#26] ✅ <b>FOGOUSDT</b> +13.29% (+53.1$) — 2026-04-11 20:02 — exit: <code>TRAIL_STOP</code> — hold 17.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.93%` ≤ 1.89%
- ✅ `range_4h = 1.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 1.37%
- RSI : 59.4
- ADX 4H : 28.4 (DI+ 29 / DI- 13)
- Change 24h : -7.42%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.017460`
- Peak atteint : `$0.021150` (**+21.13%** du peak)
- Exit : `$0.019458`
- Hold : 17.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.019206` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.020952` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.021150` (+21.13%)
- 🚪 Trail stop touché à `$0.019458` (+11.44%) → 20% fermé.

**PnL final** : 💰 **+13.29%** (+53.15$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#27] ❌ <b>ALICEUSDT</b> -1.92% (-7.7$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.79%` ≤ 1.89%
- ✅ `range_4h = 1.23%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.70%
- RSI : 62.6
- ADX 4H : 22.5 (DI+ 38 / DI- 17)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.114600`
- Peak atteint : `$0.116700` (**+1.83%** du peak)
- Exit : `$0.112400`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.126060`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-1.92%** (-7.68$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#28] ❌ <b>AXLUSDT</b> -4.88% (-19.5$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.43%` ≤ 1.89%
- ✅ `range_4h = 1.95%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.49%
- RSI : 64.6
- ADX 4H : 25.4 (DI+ 35 / DI- 17)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.047100`
- Peak atteint : `$0.047700` (**+1.27%** du peak)
- Exit : `$0.044800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.051810`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-4.88%** (-19.53$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#29] ✅ <b>CAKEUSDT</b> +3.92% (+15.7$) — 2026-04-11 20:02 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.53%` ≤ 1.89%
- ✅ `range_4h = 0.94%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.80%
- RSI : 72.9
- ADX 4H : 27.2 (DI+ 36 / DI- 14)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$1.5060`
- Peak atteint : `$1.6520` (**+9.69%** du peak)
- Exit : `$1.5650`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$1.6566`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.92%** (+15.67$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#30] ✅ <b>PHBUSDT</b> +13.79% (+55.2$) — 2026-04-12 00:02 — exit: <code>TRAIL_STOP</code> — hold 17.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.15%` ≤ 1.89%
- ✅ `range_4h = 0.0%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 49.2
- ADX 4H : 40.3 (DI+ 24 / DI- 6)
- Change 24h : +1.15%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 15

### Exit

**Trajectoire** :
- Entry : `$0.088000`
- Peak atteint : `$0.109000` (**+23.86%** du peak)
- Exit : `$0.100280`
- Hold : 17.6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.096800` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.105600` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.109000` (+23.86%)
- 🚪 Trail stop touché à `$0.100280` (+13.95%) → 20% fermé.

**PnL final** : 💰 **+13.79%** (+55.16$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#31] ✅ <b>GMTUSDT</b> +0.47% (+1.9$) — 2026-04-12 11:48 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.47%` ≤ 1.89%
- ✅ `range_4h = 1.81%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **SKIP**
- Bougie 4H : direction **green**, body 0.28%
- RSI : 55.6
- ADX 4H : 17.7 (DI+ 27 / DI- 25)
- Change 24h : -0.74%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.010640`
- Peak atteint : `$0.010870` (**+2.16%** du peak)
- Exit : `$0.010690`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.011704`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+0.47%** (+1.88$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#32] ✅ <b>COMPUSDT</b> +3.58% (+14.3$) — 2026-04-12 12:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.54%` ≤ 1.89%
- ✅ `range_4h = 1.54%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.33%
- RSI : 64.7
- ADX 4H : 24.9 (DI+ 41 / DI- 14)
- Change 24h : +3.06%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$20.9600`
- Peak atteint : `$22.9600` (**+9.54%** du peak)
- Exit : `$21.7100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$23.0560`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.58%** (+14.31$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#33] ✅ <b>BELUSDT</b> +9.00% (+36.0$) — 2026-04-12 12:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.7%` ≤ 1.89%
- ✅ `range_4h = 0.7%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (86% confiance)
- Bougie 4H : direction **green**, body 0.60%
- RSI : 48.9
- ADX 4H : 28.1 (DI+ 32 / DI- 17)
- Change 24h : +1.00%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.100000`
- Peak atteint : `$0.113500` (**+13.50%** du peak)
- Exit : `$0.108000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+8.00%)

**PnL final** : 💰 **+9.00%** (+36.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#34] ✅ <b>EPICUSDT</b> +13.09% (+52.4$) — 2026-04-12 12:33 — exit: <code>TRAIL_STOP</code> — hold 2j21h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.18%` ≤ 1.89%
- ✅ `range_4h = 1.57%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (80% confiance)
- Bougie 4H : direction **red**, body 1.16%
- RSI : 53.0
- ADX 4H : 17.8 (DI+ 26 / DI- 19)
- Change 24h : -0.78%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.259000`
- Peak atteint : `$0.311000` (**+20.08%** du peak)
- Exit : `$0.286120`
- Hold : 2j21h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.284900` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.310800` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.311000` (+20.08%)
- 🚪 Trail stop touché à `$0.286120` (+10.47%) → 20% fermé.

**PnL final** : 💰 **+13.09%** (+52.38$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#35] ✅ <b>EGLDUSDT</b> +0.79% (+3.2$) — 2026-04-12 12:48 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.53%` ≤ 1.89%
- ✅ `range_4h = 1.87%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY** (60% confiance)
- Bougie 4H : direction **green**, body 0.27%
- RSI : 71.6
- ADX 4H : 10.8 (DI+ 37 / DI- 15)
- Change 24h : -1.57%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$3.8000`
- Peak atteint : `$3.9300` (**+3.42%** du peak)
- Exit : `$3.8300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$4.1800`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+0.79%** (+3.16$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#36] ✅ <b>YGGUSDT</b> +4.07% (+16.3$) — 2026-04-12 12:48 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.59%` ≤ 1.89%
- ✅ `range_4h = 1.7%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.67%
- RSI : 65.5
- ADX 4H : 21.1 (DI+ 41 / DI- 22)
- Change 24h : +0.64%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.037550`
- Peak atteint : `$0.039520` (**+5.25%** du peak)
- Exit : `$0.039080`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.041305`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.07%** (+16.30$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#37] ✅ <b>TIAUSDT</b> +8.01% (+32.0$) — 2026-04-12 12:48 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.02%` ≤ 1.89%
- ✅ `range_4h = 1.95%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.44%
- RSI : 62.6
- ADX 4H : 38.5 (DI+ 29 / DI- 23)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.297300`
- Peak atteint : `$0.321100` (**+8.01%** du peak)
- Exit : `$0.321100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.327030`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+8.01%** (+32.02$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#38] ✅ <b>SANDUSDT</b> +1.30% (+5.2$) — 2026-04-12 12:48 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.66%` ≤ 1.89%
- ✅ `range_4h = 1.72%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 0.53%
- RSI : 73.5
- ADX 4H : 19.5 (DI+ 34 / DI- 16)
- Change 24h : -0.13%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.076700`
- Peak atteint : `$0.080200` (**+4.56%** du peak)
- Exit : `$0.077700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.084370`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.30%** (+5.22$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#39] ❌ <b>MANAUSDT</b> -0.91% (-3.6$) — 2026-04-12 13:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.92%` ≤ 1.89%
- ✅ `range_4h = 2.08%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.27%
- RSI : 60.4
- ADX 4H : 39.3 (DI+ 33 / DI- 18)
- Change 24h : -0.45%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.087900`
- Peak atteint : `$0.089800` (**+2.16%** du peak)
- Exit : `$0.087100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.096690`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-0.91%** (-3.64$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#40] ✅ <b>MAGICUSDT</b> +4.77% (+19.1$) — 2026-04-12 16:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.99%` ≤ 1.89%
- ✅ `range_4h = 0.66%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (55% confiance)
- Bougie 4H : direction **red**, body 0.33%
- RSI : 45.1
- ADX 4H : 24.2 (DI+ 24 / DI- 26)
- Change 24h : -3.04%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.060800`
- Peak atteint : `$0.065600` (**+7.89%** du peak)
- Exit : `$0.063700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.066880`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.77%** (+19.08$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#41] ✅ <b>SLPUSDT</b> +3.18% (+12.7$) — 2026-04-12 16:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.67%` ≤ 1.89%
- ✅ `range_4h = 0.67%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **WATCH** (40% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 45.4
- ADX 4H : 19.9 (DI+ 28 / DI- 28)
- Change 24h : -2.29%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.00059700`
- Peak atteint : `$0.00063400` (**+6.20%** du peak)
- Exit : `$0.00061600`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.00065670`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.18%** (+12.73$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#42] ✅ <b>COMPUSDT</b> +5.00% (+20.0$) — 2026-04-12 16:03 — exit: <code>BREAKEVEN_STOP</code> — hold 1j22h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.36%` ≤ 1.89%
- ✅ `range_4h = 0.87%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.38%
- RSI : 57.6
- ADX 4H : 32.8 (DI+ 33 / DI- 13)
- Change 24h : +0.24%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$20.8100`
- Peak atteint : `$22.9600` (**+10.33%** du peak)
- Exit : `$20.8100`
- Hold : 1j22h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$22.8910` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$20.8100`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#43] ✅ <b>AUSDT</b> +3.71% (+14.8$) — 2026-04-12 18:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.38%` ≤ 1.89%
- ✅ `range_4h = 2.09%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.43%
- RSI : 58.5
- ADX 4H : 39.8 (DI+ 26 / DI- 17)
- Change 24h : -2.86%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.078200`
- Peak atteint : `$0.081100` (**+3.71%** du peak)
- Exit : `$0.081100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.086020`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.71%** (+14.83$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#44] ✅ <b>JUPUSDT</b> +4.47% (+17.9$) — 2026-04-12 18:03 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.31%` ≤ 1.89%
- ✅ `range_4h = 1.44%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.25%
- RSI : 62.5
- ADX 4H : 35.8 (DI+ 30 / DI- 19)
- Change 24h : -2.48%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.161200`
- Peak atteint : `$0.172300` (**+6.89%** du peak)
- Exit : `$0.168400`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.177320`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.47%** (+17.87$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#45] ✅ <b>DEXEUSDT</b> +15.52% (+62.1$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.99%` ≤ 1.89%
- ✅ `range_4h = 0.99%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 0.12%
- RSI : 70.5
- ADX 4H : 18.6 (DI+ 36 / DI- 13)
- Change 24h : +3.10%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$9.8720`
- Peak atteint : `$12.8240` (**+29.90%** du peak)
- Exit : `$12.1020`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+22.59%)

**PnL final** : 💰 **+15.52%** (+62.07$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#46] ✅ <b>PLUMEUSDT</b> +14.05% (+56.2$) — 2026-04-12 20:23 — exit: <code>TRAIL_STOP</code> — hold 1j2h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.7%` ≤ 1.89%
- ✅ `range_4h = 0.7%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 0.70%
- RSI : 68.5
- ADX 4H : 18.6 (DI+ 37 / DI- 13)
- Change 24h : +3.38%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.010010`
- Peak atteint : `$0.012540` (**+25.27%** du peak)
- Exit : `$0.011537`
- Hold : 1j2h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.011011` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.012012` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.012540` (+25.27%)
- 🚪 Trail stop touché à `$0.011537` (+15.25%) → 20% fermé.

**PnL final** : 💰 **+14.05%** (+56.20$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#47] ✅ <b>LUMIAUSDT</b> +5.80% (+23.2$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.5%` ≤ 1.89%
- ✅ `range_4h = 1.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.62%
- RSI : 73.3
- ADX 4H : 29.7 (DI+ 37 / DI- 8)
- Change 24h : +2.94%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.081000`
- Peak atteint : `$0.088200` (**+8.89%** du peak)
- Exit : `$0.085700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.089100`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.80%** (+23.21$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#48] ✅ <b>AUSDT</b> +4.87% (+19.5$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 2.34%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.41%
- RSI : 54.9
- ADX 4H : 35.5 (DI+ 22 / DI- 15)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.078000`
- Peak atteint : `$0.082200` (**+5.38%** du peak)
- Exit : `$0.081800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.085800`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.87%** (+19.49$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#49] ✅ <b>LUMIAUSDT</b> +5.80% (+23.2$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.5%` ≤ 1.89%
- ✅ `range_4h = 1.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.62%
- RSI : 73.3
- ADX 4H : 29.7 (DI+ 37 / DI- 8)
- Change 24h : +2.94%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.081000`
- Peak atteint : `$0.088200` (**+8.89%** du peak)
- Exit : `$0.085700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.089100`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.80%** (+23.21$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#50] ✅ <b>PLUMEUSDT</b> +14.05% (+56.2$) — 2026-04-12 20:23 — exit: <code>TRAIL_STOP</code> — hold 1j2h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.7%` ≤ 1.89%
- ✅ `range_4h = 0.7%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 0.70%
- RSI : 68.5
- ADX 4H : 18.6 (DI+ 37 / DI- 13)
- Change 24h : +3.38%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.010010`
- Peak atteint : `$0.012540` (**+25.27%** du peak)
- Exit : `$0.011537`
- Hold : 1j2h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.011011` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.012012` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.012540` (+25.27%)
- 🚪 Trail stop touché à `$0.011537` (+15.25%) → 20% fermé.

**PnL final** : 💰 **+14.05%** (+56.20$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#51] ✅ <b>SPELLUSDT</b> +1.97% (+7.9$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 0.51%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (89% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 43.7
- ADX 4H : 34.5 (DI+ 41 / DI- 12)
- Change 24h : -2.30%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.00015730`
- Peak atteint : `$0.00016890` (**+7.37%** du peak)
- Exit : `$0.00016040`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.00017303`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.97%** (+7.88$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#52] ✅ <b>SPELLUSDT</b> +1.97% (+7.9$) — 2026-04-12 20:23 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 0.51%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (89% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 43.7
- ADX 4H : 34.5 (DI+ 41 / DI- 12)
- Change 24h : -2.30%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.00015730`
- Peak atteint : `$0.00016890` (**+7.37%** du peak)
- Exit : `$0.00016040`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.00017303`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.97%** (+7.88$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#53] ✅ <b>CAKEUSDT</b> +9.49% (+38.0$) — 2026-04-12 20:50 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.27%` ≤ 1.89%
- ✅ `range_4h = 0.68%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.48%
- RSI : 63.3
- ADX 4H : 20.8 (DI+ 29 / DI- 17)
- Change 24h : -1.74%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$1.4700`
- Peak atteint : `$1.6520` (**+12.38%** du peak)
- Exit : `$1.6020`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+8.98%)

**PnL final** : 💰 **+9.49%** (+37.96$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#54] ✅ <b>LINKUSDT</b> +5.21% (+20.8$) — 2026-04-12 20:50 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.14%` ≤ 1.89%
- ✅ `range_4h = 1.49%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.34%
- RSI : 65.8
- ADX 4H : 23.2 (DI+ 27 / DI- 14)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$8.8300`
- Peak atteint : `$9.4400` (**+6.91%** du peak)
- Exit : `$9.2900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$9.7130`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.21%** (+20.84$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#55] ✅ <b>MANTRAUSDT</b> +1.91% (+7.7$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.77%` ≤ 1.89%
- ✅ `range_4h = 0.19%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (83% confiance)
- Bougie 4H : direction **red**, body 0.10%
- RSI : 46.8
- ADX 4H : 38.7 (DI+ 41 / DI- 18)
- Change 24h : -1.50%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.010460`
- Peak atteint : `$0.010960` (**+4.78%** du peak)
- Exit : `$0.010660`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.011506`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.91%** (+7.65$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#56] ✅ <b>TRBUSDT</b> +7.11% (+28.4$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.26%` ≤ 1.89%
- ✅ `range_4h = 1.71%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.05%
- RSI : 64.2
- ADX 4H : 28.8 (DI+ 34 / DI- 18)
- Change 24h : -3.38%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$15.2000`
- Peak atteint : `$16.4300` (**+8.09%** du peak)
- Exit : `$16.2800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$16.7200`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.11%** (+28.42$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#57] ✅ <b>DOGEUSDT</b> +4.68% (+18.7$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 0.98%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.40%
- RSI : 58.1
- ADX 4H : 30.7 (DI+ 27 / DI- 19)
- Change 24h : -2.84%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.090660`
- Peak atteint : `$0.098050` (**+8.15%** du peak)
- Exit : `$0.094900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.099726`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.68%** (+18.71$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#58] ✅ <b>MORPHOUSDT</b> +8.91% (+35.6$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.54%` ≤ 1.89%
- ✅ `range_4h = 0.54%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (60% confiance)
- Bougie 4H : direction **green**, body 0.24%
- RSI : 46.3
- ADX 4H : 38.3 (DI+ 24 / DI- 30)
- Change 24h : -6.21%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$1.6880`
- Peak atteint : `$1.9000` (**+12.56%** du peak)
- Exit : `$1.8200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.82%)

**PnL final** : 💰 **+8.91%** (+35.64$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#59] ✅ <b>SOLUSDT</b> +4.12% (+16.5$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.47%` ≤ 1.89%
- ✅ `range_4h = 1.98%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **red**, body 0.46%
- RSI : 40.9
- ADX 4H : 31.8 (DI+ 15 / DI- 27)
- Change 24h : -3.91%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$81.5400`
- Peak atteint : `$87.6700` (**+7.52%** du peak)
- Exit : `$84.9000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$89.6940`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.12%** (+16.48$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#60] ✅ <b>ETHUSDT</b> +8.79% (+35.1$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.47%` ≤ 1.89%
- ✅ `range_4h = 1.13%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.42%
- RSI : 56.8
- ADX 4H : 33.4 (DI+ 29 / DI- 21)
- Change 24h : -4.19%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$2191.6800`
- Peak atteint : `$2415.5000` (**+10.21%** du peak)
- Exit : `$2357.6800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.57%)

**PnL final** : 💰 **+8.79%** (+35.15$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#61] ✅ <b>DOGEUSDT</b> +4.68% (+18.7$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 0.98%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.40%
- RSI : 58.1
- ADX 4H : 30.7 (DI+ 27 / DI- 19)
- Change 24h : -2.84%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$0.090660`
- Peak atteint : `$0.098050` (**+8.15%** du peak)
- Exit : `$0.094900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.099726`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.68%** (+18.71$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#62] ✅ <b>TRBUSDT</b> +7.11% (+28.4$) — 2026-04-12 23:45 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.26%` ≤ 1.89%
- ✅ `range_4h = 1.71%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.05%
- RSI : 64.2
- ADX 4H : 28.8 (DI+ 34 / DI- 18)
- Change 24h : -3.38%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 16

### Exit

**Trajectoire** :
- Entry : `$15.2000`
- Peak atteint : `$16.4300` (**+8.09%** du peak)
- Exit : `$16.2800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$16.7200`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.11%** (+28.42$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#63] ✅ <b>DOGEUSDT</b> +4.22% (+16.9$) — 2026-04-13 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.65%` ≤ 1.89%
- ✅ `range_4h = 0.86%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.39%
- RSI : 45.1
- ADX 4H : 25.6 (DI+ 16 / DI- 22)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.090840`
- Peak atteint : `$0.098050` (**+7.94%** du peak)
- Exit : `$0.094670`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.099924`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.22%** (+16.86$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#64] ✅ <b>TRBUSDT</b> +7.39% (+29.6$) — 2026-04-13 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.19%` ≤ 1.89%
- ✅ `range_4h = 1.26%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.46%
- RSI : 42.6
- ADX 4H : 22.4 (DI+ 21 / DI- 26)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$15.1500`
- Peak atteint : `$16.4300` (**+8.45%** du peak)
- Exit : `$16.2700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$16.6650`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.39%** (+29.57$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#65] ✅ <b>MORPHOUSDT</b> +8.94% (+35.8$) — 2026-04-13 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.77%` ≤ 1.89%
- ✅ `range_4h = 0.77%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (80% confiance)
- Bougie 4H : direction **green**, body 0.42%
- RSI : 45.9
- ADX 4H : 36.5 (DI+ 23 / DI- 30)
- Change 24h : -6.41%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$1.6870`
- Peak atteint : `$1.9000` (**+12.63%** du peak)
- Exit : `$1.8200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.88%)

**PnL final** : 💰 **+8.94%** (+35.77$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#66] ✅ <b>ETHUSDT</b> +8.67% (+34.7$) — 2026-04-13 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.8%` ≤ 1.89%
- ✅ `range_4h = 1.0%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.12%
- RSI : 43.3
- ADX 4H : 27.7 (DI+ 16 / DI- 24)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$2191.6500`
- Peak atteint : `$2415.5000` (**+10.21%** du peak)
- Exit : `$2352.4800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.34%)

**PnL final** : 💰 **+8.67%** (+34.68$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#67] ✅ <b>SOLUSDT</b> +3.80% (+15.2$) — 2026-04-13 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.58%` ≤ 1.89%
- ✅ `range_4h = 0.58%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (70% confiance)
- Bougie 4H : direction **green**, body 0.20%
- RSI : 40.8
- ADX 4H : 31.6 (DI+ 14 / DI- 25)
- Change 24h : -3.78%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$81.5300`
- Peak atteint : `$87.6700` (**+7.53%** du peak)
- Exit : `$84.6300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$89.6830`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.80%** (+15.21$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#68] ❌ <b>NIGHTUSDT</b> -8.00% (-32.0$) — 2026-04-13 04:01 — exit: <code>SL_HIT</code> — hold 1j1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.95%` ≤ 1.89%
- ✅ `range_4h = 2.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **red**, body 1.61%
- RSI : 65.4
- ADX 4H : 45.7 (DI+ 56 / DI- 7)
- Change 24h : -0.43%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.039730`
- Peak atteint : `$0.039730` (**+0.00%** du peak)
- Exit : `$0.036552`
- Hold : 1j1h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.036552** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.043703`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#69] ✅ <b>MMTUSDT</b> +14.00% (+56.0$) — 2026-04-13 04:01 — exit: <code>TRAIL_STOP</code> — hold 1j3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.14%` ≤ 1.89%
- ✅ `range_4h = 1.89%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.65%
- RSI : 64.2
- ADX 4H : 17.2 (DI+ 38 / DI- 20)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.123500`
- Peak atteint : `$0.154600` (**+25.18%** du peak)
- Exit : `$0.142048`
- Hold : 1j3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.135850` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.148200` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.154600` (+25.18%)
- 🚪 Trail stop touché à `$0.142048` (+15.02%) → 20% fermé.

**PnL final** : 💰 **+14.00%** (+56.01$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#70] ✅ <b>AXLUSDT</b> +14.96% (+59.8$) — 2026-04-13 05:10 — exit: <code>TRAIL_STOP</code> — hold 2j22h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.11%` ≤ 1.89%
- ✅ `range_4h = 2.01%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.67%
- RSI : 59.8
- ADX 4H : 22.4 (DI+ 53 / DI- 21)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.044700`
- Peak atteint : `$0.058200` (**+30.20%** du peak)
- Exit : `$0.053544`
- Hold : 2j22h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.049170` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.053640` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.058200` (+30.20%)
- 🚪 Trail stop touché à `$0.053544` (+19.79%) → 20% fermé.

**PnL final** : 💰 **+14.96%** (+59.83$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#71] ✅ <b>SHELLUSDT</b> +7.29% (+29.2$) — 2026-04-13 05:38 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.7%` ≤ 1.89%
- ✅ `range_4h = 2.48%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.73%
- RSI : 44.7
- ADX 4H : 35.7 (DI+ 25 / DI- 50)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.028800`
- Peak atteint : `$0.031200` (**+8.33%** du peak)
- Exit : `$0.030900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.031680`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.29%** (+29.17$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#72] ✅ <b>ROSEUSDT</b> +6.62% (+26.5$) — 2026-04-13 06:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.7%` ≤ 1.89%
- ✅ `range_4h = 2.58%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 2.24%
- RSI : 55.9
- ADX 4H : 19.4 (DI+ 32 / DI- 31)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.010720`
- Peak atteint : `$0.011470` (**+7.00%** du peak)
- Exit : `$0.011430`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.011792`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+6.62%** (+26.49$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#73] ✅ <b>BELUSDT</b> +12.77% (+51.1$) — 2026-04-13 06:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.21%` ≤ 1.89%
- ✅ `range_4h = 2.04%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.71%
- RSI : 63.6
- ADX 4H : 17.3 (DI+ 50 / DI- 23)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.099700`
- Peak atteint : `$0.117400` (**+17.75%** du peak)
- Exit : `$0.115200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+15.55%)

**PnL final** : 💰 **+12.77%** (+51.09$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#74] ✅ <b>LAYERUSDT</b> +4.85% (+19.4$) — 2026-04-13 06:37 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.25%` ≤ 1.89%
- ✅ `range_4h = 1.77%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.75%
- RSI : 57.8
- ADX 4H : 19.3 (DI+ 30 / DI- 24)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.080400`
- Peak atteint : `$0.084600` (**+5.22%** du peak)
- Exit : `$0.084300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.088440`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.85%** (+19.40$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#75] ✅ <b>XRPUSDT</b> +5.26% (+21.1$) — 2026-04-13 06:37 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.32%` ≤ 1.89%
- ✅ `range_4h = 1.37%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.00%
- RSI : 66.6
- ADX 4H : 19.4 (DI+ 33 / DI- 18)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$1.3360`
- Peak atteint : `$1.4156` (**+5.96%** du peak)
- Exit : `$1.4063`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$1.4696`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.26%** (+21.05$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#76] ✅ <b>EPICUSDT</b> +13.43% (+53.7$) — 2026-04-13 07:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.16%` ≤ 1.89%
- ✅ `range_4h = 1.95%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **5/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.39%
- RSI : 62.2
- ADX 4H : 22.5 (DI+ 38 / DI- 21)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.261000`
- Peak atteint : `$0.311000` (**+19.16%** du peak)
- Exit : `$0.305000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+16.86%)

**PnL final** : 💰 **+13.43%** (+53.72$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#77] ❌ <b>DASHUSDT</b> -8.00% (-32.0$) — 2026-04-13 08:30 — exit: <code>SL_HIT</code> — hold 1j10h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.56%` ≤ 1.89%
- ✅ `range_4h = 1.84%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **WATCH** (60% confiance)
- Bougie 4H : direction **red**, body 0.17%
- RSI : 45.2
- ADX 4H : 19.1 (DI+ 27 / DI- 23)
- Change 24h : -6.63%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$41.3300`
- Peak atteint : `$42.3600` (**+2.49%** du peak)
- Exit : `$38.0236`
- Hold : 1j10h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $38.0236** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$45.4630`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#78] ✅ <b>FIDAUSDT</b> +7.45% (+29.8$) — 2026-04-13 08:30 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.73%` ≤ 1.89%
- ✅ `range_4h = 1.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 1.16%
- RSI : 48.1
- ADX 4H : 30.7 (DI+ 33 / DI- 12)
- Change 24h : +1.29%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.016320`
- Peak atteint : `$0.018560` (**+13.73%** du peak)
- Exit : `$0.017120`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+4.90%)

**PnL final** : 💰 **+7.45%** (+29.80$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#79] ✅ <b>FIDAUSDT</b> +7.45% (+29.8$) — 2026-04-13 08:30 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.73%` ≤ 1.89%
- ✅ `range_4h = 1.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 1.16%
- RSI : 48.1
- ADX 4H : 30.7 (DI+ 33 / DI- 12)
- Change 24h : +1.29%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.016320`
- Peak atteint : `$0.018560` (**+13.73%** du peak)
- Exit : `$0.017120`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+4.90%)

**PnL final** : 💰 **+7.45%** (+29.80$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#80] ✅ <b>FIDAUSDT</b> +7.45% (+29.8$) — 2026-04-13 08:30 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.73%` ≤ 1.89%
- ✅ `range_4h = 1.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **green**, body 1.16%
- RSI : 48.1
- ADX 4H : 30.7 (DI+ 33 / DI- 12)
- Change 24h : +1.29%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.016320`
- Peak atteint : `$0.018560` (**+13.73%** du peak)
- Exit : `$0.017120`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+4.90%)

**PnL final** : 💰 **+7.45%** (+29.80$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#81] ✅ <b>SAPIENUSDT</b> +1.49% (+6.0$) — 2026-04-13 09:44 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.36%` ≤ 1.89%
- ✅ `range_4h = 2.46%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 1.47%
- RSI : 63.7
- ADX 4H : 27.5 (DI+ 34 / DI- 15)
- Change 24h : +2.08%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.074000`
- Peak atteint : `$0.080100` (**+8.24%** du peak)
- Exit : `$0.075100`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.081400`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.49%** (+5.95$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#82] ✅ <b>FLOWUSDT</b> +13.44% (+53.8$) — 2026-04-13 10:15 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.23%` ≤ 1.89%
- ✅ `range_4h = 1.75%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.71%
- RSI : 65.8
- ADX 4H : 14.7 (DI+ 41 / DI- 18)
- Change 24h : -1.17%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.031230`
- Peak atteint : `$0.036750` (**+17.68%** du peak)
- Exit : `$0.036500`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+16.87%)

**PnL final** : 💰 **+13.44%** (+53.75$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#83] ✅ <b>BLURUSDT</b> +14.20% (+56.8$) — 2026-04-13 12:01 — exit: <code>TRAIL_STOP</code> — hold 2j9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.14%` ≤ 1.89%
- ✅ `range_4h = 0.14%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.09%
- RSI : 44.7
- ADX 4H : 23.9 (DI+ 31 / DI- 22)
- Change 24h : -3.30%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.021410`
- Peak atteint : `$0.026990` (**+26.06%** du peak)
- Exit : `$0.024831`
- Hold : 2j9h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.023551` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.025692` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.026990` (+26.06%)
- 🚪 Trail stop touché à `$0.024831` (+15.98%) → 20% fermé.

**PnL final** : 💰 **+14.20%** (+56.78$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#84] ✅ <b>BTCUSDT</b> +5.01% (+20.1$) — 2026-04-13 13:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.28%` ≤ 1.89%
- ✅ `range_4h = 0.65%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.26%
- RSI : 61.6
- ADX 4H : 12.2 (DI+ 29 / DI- 18)
- Change 24h : +0.11%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$71074.9100`
- Peak atteint : `$76038.0000` (**+6.98%** du peak)
- Exit : `$74636.9800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$78182.4010`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.01%** (+20.05$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#85] ✅ <b>ADAUSDT</b> +3.94% (+15.8$) — 2026-04-13 13:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.37%` ≤ 1.89%
- ✅ `range_4h = 1.77%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.09%
- RSI : 65.8
- ADX 4H : 22.5 (DI+ 31 / DI- 15)
- Change 24h : +0.42%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.241200`
- Peak atteint : `$0.251800` (**+4.39%** du peak)
- Exit : `$0.250700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.265320`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.94%** (+15.75$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#86] ✅ <b>CRVUSDT</b> +6.27% (+25.1$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.95%` ≤ 1.89%
- ✅ `range_4h = 1.72%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.76%
- RSI : 66.3
- ADX 4H : 17.4 (DI+ 34 / DI- 17)
- Change 24h : -0.05%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.212200`
- Peak atteint : `$0.232000` (**+9.33%** du peak)
- Exit : `$0.225500`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.233420`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+6.27%** (+25.07$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#87] ✅ <b>RUNEUSDT</b> +3.84% (+15.3$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 1.81%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **WATCH** (45% confiance)
- Bougie 4H : direction **green**, body 0.77%
- RSI : 68.2
- ADX 4H : 28.8 (DI+ 43 / DI- 14)
- Change 24h : +1.03%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.391000`
- Peak atteint : `$0.414000` (**+5.88%** du peak)
- Exit : `$0.406000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.430100`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.84%** (+15.35$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#88] ✅ <b>PENDLEUSDT</b> +9.40% (+37.6$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.94%` ≤ 1.89%
- ✅ `range_4h = 2.49%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.95%
- RSI : 69.9
- ADX 4H : 13.2 (DI+ 35 / DI- 19)
- Change 24h : +0.10%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$1.0690`
- Peak atteint : `$1.2090` (**+13.10%** du peak)
- Exit : `$1.1630`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+8.79%)

**PnL final** : 💰 **+9.40%** (+37.59$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#89] ✅ <b>TURBOUSDT</b> +13.84% (+55.4$) — 2026-04-13 14:01 — exit: <code>TRAIL_STOP</code> — hold 2j19h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.7%` ≤ 1.89%
- ✅ `range_4h = 2.33%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 0.90%
- RSI : 62.7
- ADX 4H : 14.3 (DI+ 33 / DI- 29)
- Change 24h : -0.49%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.001007`
- Peak atteint : `$0.001250` (**+24.13%** du peak)
- Exit : `$0.001150`
- Hold : 2j19h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.001108` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.001208` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.001250` (+24.13%)
- 🚪 Trail stop touché à `$0.001150` (+14.20%) → 20% fermé.

**PnL final** : 💰 **+13.84%** (+55.36$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#90] ✅ <b>LDOUSDT</b> +13.24% (+53.0$) — 2026-04-13 14:01 — exit: <code>TRAIL_STOP</code> — hold 1j2h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.97%` ≤ 1.89%
- ✅ `range_4h = 2.49%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 1.04%
- RSI : 69.9
- ADX 4H : 23.8 (DI+ 41 / DI- 20)
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.311700`
- Peak atteint : `$0.376700` (**+20.85%** du peak)
- Exit : `$0.346564`
- Hold : 1j2h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.342870` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.374040` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.376700` (+20.85%)
- 🚪 Trail stop touché à `$0.346564` (+11.19%) → 20% fermé.

**PnL final** : 💰 **+13.24%** (+52.95$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#91] ✅ <b>FLOKIUSDT</b> +8.43% (+33.7$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.65%` ≤ 1.89%
- ✅ `range_4h = 1.93%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.34%
- RSI : 67.8
- ADX 4H : 17.1 (DI+ 34 / DI- 16)
- Change 24h : +0.50%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.00002800`
- Peak atteint : `$0.00003110` (**+11.07%** du peak)
- Exit : `$0.00002992`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+6.86%)

**PnL final** : 💰 **+8.43%** (+33.71$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#92] ✅ <b>INJUSDT</b> +11.33% (+45.3$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.96%` ≤ 1.89%
- ✅ `range_4h = 1.83%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.00%
- RSI : 68.9
- ADX 4H : 22.6 (DI+ 35 / DI- 14)
- Change 24h : +1.21%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$2.9530`
- Peak atteint : `$3.4670` (**+17.41%** du peak)
- Exit : `$3.3270`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+12.67%)

**PnL final** : 💰 **+11.33%** (+45.33$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#93] ✅ <b>LINKUSDT</b> +4.30% (+17.2$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.03%` ≤ 1.89%
- ✅ `range_4h = 1.96%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.80%
- RSI : 64.5
- ADX 4H : 19.5 (DI+ 26 / DI- 17)
- Change 24h : +0.80%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$8.8400`
- Peak atteint : `$9.4400` (**+6.79%** du peak)
- Exit : `$9.2200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$9.7240`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.30%** (+17.19$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#94] ✅ <b>SUIUSDT</b> +5.05% (+20.2$) — 2026-04-13 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.41%` ≤ 1.89%
- ✅ `range_4h = 2.27%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.09%
- RSI : 72.5
- ADX 4H : 14.7 (DI+ 40 / DI- 20)
- Change 24h : +1.20%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.919900`
- Peak atteint : `$0.994700` (**+8.13%** du peak)
- Exit : `$0.966400`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$1.0119`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.05%** (+20.22$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#95] ✅ <b>PHBUSDT</b> +13.24% (+53.0$) — 2026-04-13 16:01 — exit: <code>TRAIL_STOP</code> — hold 2j21h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.11%` ≤ 1.89%
- ✅ `range_4h = 2.22%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 49.4
- ADX 4H : 36.4 (DI+ 31 / DI- 11)
- Change 24h : -8.08%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.091000`
- Peak atteint : `$0.110000` (**+20.88%** du peak)
- Exit : `$0.101200`
- Hold : 2j21h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.100100` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.109200` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.110000` (+20.88%)
- 🚪 Trail stop touché à `$0.101200` (+11.21%) → 20% fermé.

**PnL final** : 💰 **+13.24%** (+52.97$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#96] ✅ <b>ALTUSDT</b> +14.44% (+57.7$) — 2026-04-13 16:01 — exit: <code>TRAIL_STOP</code> — hold 2j14h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.44%` ≤ 1.89%
- ✅ `range_4h = 1.63%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.60%
- RSI : 62.6
- ADX 4H : 17.1 (DI+ 34 / DI- 16)
- Change 24h : +1.20%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.006870`
- Peak atteint : `$0.008750` (**+27.37%** du peak)
- Exit : `$0.008050`
- Hold : 2j14h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.007557` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.008244` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.008750` (+27.37%)
- 🚪 Trail stop touché à `$0.008050` (+17.18%) → 20% fermé.

**PnL final** : 💰 **+14.44%** (+57.74$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#97] ✅ <b>STXUSDT</b> +10.63% (+42.5$) — 2026-04-13 16:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.28%` ≤ 1.89%
- ✅ `range_4h = 1.07%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.14%
- RSI : 54.7
- ADX 4H : 19.9 (DI+ 23 / DI- 20)
- Change 24h : +0.19%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.214800`
- Peak atteint : `$0.242800` (**+13.04%** du peak)
- Exit : `$0.239000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+11.27%)

**PnL final** : 💰 **+10.63%** (+42.53$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#98] ✅ <b>SPELLUSDT</b> +6.08% (+24.3$) — 2026-04-13 19:50 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.25%` ≤ 1.89%
- ✅ `range_4h = 0.51%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.32%
- RSI : 52.3
- ADX 4H : 19.4 (DI+ 68 / DI- 8)
- Change 24h : +0.00%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.00015800`
- Peak atteint : `$0.00016760` (**+6.08%** du peak)
- Exit : `$0.00016760`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.00017380`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+6.08%** (+24.30$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#99] ❌ <b>ALLOUSDT</b> -3.00% (-12.0$) — 2026-04-13 19:50 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.69%` ≤ 1.89%
- ✅ `range_4h = 1.16%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.27%
- RSI : 67.5
- ADX 4H : 18.7 (DI+ 36 / DI- 17)
- Change 24h : +5.13%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.113300`
- Peak atteint : `$0.117100` (**+3.35%** du peak)
- Exit : `$0.109900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.124630`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-3.00%** (-12.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#100] ✅ <b>SPELLUSDT</b> +5.69% (+22.7$) — 2026-04-13 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.38%` ≤ 1.89%
- ✅ `range_4h = 1.84%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 1.01%
- RSI : 53.3
- ADX 4H : 17.6 (DI+ 58 / DI- 9)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.00015830`
- Peak atteint : `$0.00016820` (**+6.25%** du peak)
- Exit : `$0.00016730`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.00017413`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+5.69%** (+22.74$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#101] ✅ <b>TURTLEUSDT</b> +3.56% (+14.2$) — 2026-04-13 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.33%` ≤ 1.89%
- ✅ `range_4h = 1.56%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.22%
- RSI : 72.9
- ADX 4H : 21.5 (DI+ 41 / DI- 11)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 12

### Exit

**Trajectoire** :
- Entry : `$0.045000`
- Peak atteint : `$0.046800` (**+4.00%** du peak)
- Exit : `$0.046600`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.049500`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+3.56%** (+14.22$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#102] ✅ <b>SUSDT</b> +7.93% (+31.7$) — 2026-04-13 23:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.97%` ≤ 1.89%
- ✅ `range_4h = 1.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.32%
- RSI : 72.7
- ADX 4H : 25.3 (DI+ 40 / DI- 8)
- Change 24h : -1.27%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.042760`
- Peak atteint : `$0.046510` (**+8.77%** du peak)
- Exit : `$0.046150`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.047036`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.93%** (+31.71$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#103] ✅ <b>1000CHEEMSUSDT</b> +12.22% (+48.9$) — 2026-04-14 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.8%` ≤ 1.89%
- ✅ `range_4h = 2.22%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.78%
- RSI : 64.5
- ADX 4H : 19.6 (DI+ 33 / DI- 12)
- Change 24h : -1.19%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.00049200`
- Peak atteint : `$0.00058600` (**+19.11%** du peak)
- Exit : `$0.00056300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+14.43%)

**PnL final** : 💰 **+12.22%** (+48.86$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#104] ✅ <b>FLOWUSDT</b> +7.59% (+30.4$) — 2026-04-14 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.52%` ≤ 1.89%
- ✅ `range_4h = 0.86%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.29%
- RSI : 64.6
- ADX 4H : 25.4 (DI+ 35 / DI- 10)
- Change 24h : +0.46%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.034260`
- Peak atteint : `$0.037150` (**+8.44%** du peak)
- Exit : `$0.036860`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.037686`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.59%** (+30.36$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#105] ✅ <b>FLOWUSDT</b> +7.59% (+30.4$) — 2026-04-14 00:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.52%` ≤ 1.89%
- ✅ `range_4h = 0.86%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.29%
- RSI : 64.6
- ADX 4H : 25.4 (DI+ 35 / DI- 10)
- Change 24h : +0.46%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.034260`
- Peak atteint : `$0.037150` (**+8.44%** du peak)
- Exit : `$0.036860`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.037686`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+7.59%** (+30.36$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#106] ✅ <b>OPNUSDT</b> +15.93% (+63.7$) — 2026-04-14 00:01 — exit: <code>TRAIL_STOP</code> — hold 2j16h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.19%` ≤ 1.89%
- ✅ `range_4h = 0.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.06%
- RSI : 59.1
- ADX 4H : 29.8 (DI+ 30 / DI- 19)
- Change 24h : +5.18%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.160300`
- Peak atteint : `$0.217200` (**+35.50%** du peak)
- Exit : `$0.199824`
- Hold : 2j16h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.176330` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.192360` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.217200` (+35.50%)
- 🚪 Trail stop touché à `$0.199824` (+24.66%) → 20% fermé.

**PnL final** : 💰 **+15.93%** (+63.73$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#107] ✅ <b>ZAMAUSDT</b> +17.99% (+72.0$) — 2026-04-14 00:01 — exit: <code>TRAIL_STOP</code> — hold 5.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.96%` ≤ 1.89%
- ✅ `range_4h = 0.96%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.42%
- RSI : 63.6
- ADX 4H : 26.9 (DI+ 31 / DI- 15)
- Change 24h : +1.88%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.025970`
- Peak atteint : `$0.038100` (**+46.71%** du peak)
- Exit : `$0.035052`
- Hold : 5.6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.028567` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.031164` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.038100` (+46.71%)
- 🚪 Trail stop touché à `$0.035052` (+34.97%) → 20% fermé.

**PnL final** : 💰 **+17.99%** (+71.98$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#108] ✅ <b>OPNUSDT</b> +15.93% (+63.7$) — 2026-04-14 00:01 — exit: <code>TRAIL_STOP</code> — hold 2j16h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.19%` ≤ 1.89%
- ✅ `range_4h = 0.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.06%
- RSI : 59.1
- ADX 4H : 29.8 (DI+ 30 / DI- 19)
- Change 24h : +5.18%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.160300`
- Peak atteint : `$0.217200` (**+35.50%** du peak)
- Exit : `$0.199824`
- Hold : 2j16h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.176330` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.192360` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.217200` (+35.50%)
- 🚪 Trail stop touché à `$0.199824` (+24.66%) → 20% fermé.

**PnL final** : 💰 **+15.93%** (+63.73$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#109] ✅ <b>TREEUSDT</b> +13.82% (+55.3$) — 2026-04-14 00:36 — exit: <code>TRAIL_STOP</code> — hold 7.3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.15%` ≤ 1.89%
- ✅ `range_4h = 1.67%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (77% confiance)
- Bougie 4H : direction **green**, body 0.15%
- RSI : 80.3
- ADX 4H : 61.4 (DI+ 49 / DI- 6)
- Change 24h : -0.74%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.064500`
- Peak atteint : `$0.080000` (**+24.03%** du peak)
- Exit : `$0.073600`
- Hold : 7.3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.070950` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.077400` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.080000` (+24.03%)
- 🚪 Trail stop touché à `$0.073600` (+14.11%) → 20% fermé.

**PnL final** : 💰 **+13.82%** (+55.29$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#110] ✅ <b>IOUSDT</b> +8.49% (+34.0$) — 2026-04-14 04:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.97%` ≤ 1.89%
- ✅ `range_4h = 2.04%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.33%
- RSI : 69.2
- ADX 4H : 34.0 (DI+ 24 / DI- 8)
- Change 24h : +1.67%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.106000`
- Peak atteint : `$0.122000` (**+15.09%** du peak)
- Exit : `$0.113400`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+6.98%)

**PnL final** : 💰 **+8.49%** (+33.96$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#111] ✅ <b>STXUSDT</b> +8.70% (+34.8$) — 2026-04-14 04:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.27%` ≤ 1.89%
- ✅ `range_4h = 1.67%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.85%
- RSI : 60.0
- ADX 4H : 16.1 (DI+ 33 / DI- 13)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.224200`
- Peak atteint : `$0.248500` (**+10.84%** du peak)
- Exit : `$0.240800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+7.40%)

**PnL final** : 💰 **+8.70%** (+34.81$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#112] ✅ <b>NEIROUSDT</b> +19.91% (+79.7$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 1j21h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.02%` ≤ 1.89%
- ✅ `range_4h = 0.41%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.02%
- RSI : 70.0
- ADX 4H : 24.0 (DI+ 44 / DI- 8)
- Change 24h : +13.36%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00006650`
- Peak atteint : `$0.00010450` (**+57.14%** du peak)
- Exit : `$0.00009614`
- Hold : 1j21h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00007315` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00007980` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00010450` (+57.14%)
- 🚪 Trail stop touché à `$0.00009614` (+44.57%) → 20% fermé.

**PnL final** : 💰 **+19.91%** (+79.66$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#113] ✅ <b>1000CHEEMSUSDT</b> +13.32% (+53.3$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 2j8h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.63%` ≤ 1.89%
- ✅ `range_4h = 1.68%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.03%
- RSI : 60.4
- ADX 4H : 21.4 (DI+ 31 / DI- 12)
- Change 24h : +8.86%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00048300`
- Peak atteint : `$0.00058600` (**+21.33%** du peak)
- Exit : `$0.00053912`
- Hold : 2j8h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00053130` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00057960` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00058600` (+21.33%)
- 🚪 Trail stop touché à `$0.00053912` (+11.62%) → 20% fermé.

**PnL final** : 💰 **+13.32%** (+53.30$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#114] ✅ <b>EIGENUSDT</b> +14.42% (+57.7$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.49%` ≤ 1.89%
- ✅ `range_4h = 2.03%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 1.81%
- RSI : 60.9
- ADX 4H : 18.6 (DI+ 30 / DI- 14)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.166000`
- Peak atteint : `$0.207000` (**+24.70%** du peak)
- Exit : `$0.194400`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+17.11%)

**PnL final** : 💰 **+14.42%** (+57.69$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#115] ✅ <b>PNUTUSDT</b> +14.98% (+59.9$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 2j0h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.13%` ≤ 1.89%
- ✅ `range_4h = 1.35%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 62.5
- ADX 4H : 22.3 (DI+ 40 / DI- 10)
- Change 24h : +9.85%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.044500`
- Peak atteint : `$0.058000` (**+30.34%** du peak)
- Exit : `$0.053360`
- Hold : 2j0h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.048950` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.053400` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.058000` (+30.34%)
- 🚪 Trail stop touché à `$0.053360` (+19.91%) → 20% fermé.

**PnL final** : 💰 **+14.98%** (+59.93$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#116] ✅ <b>NEWTUSDT</b> +10.40% (+41.6$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.65%` ≤ 1.89%
- ✅ `range_4h = 1.32%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.92%
- RSI : 55.7
- ADX 4H : 40.0 (DI+ 32 / DI- 12)
- Change 24h : +8.64%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.069400`
- Peak atteint : `$0.079600` (**+14.70%** du peak)
- Exit : `$0.076900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+10.81%)

**PnL final** : 💰 **+10.40%** (+41.61$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#117] ❌ <b>MDTUSDT</b> -8.00% (-32.0$) — 2026-04-14 07:59 — exit: <code>SL_HIT</code> — hold 10.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.24%` ≤ 1.89%
- ✅ `range_4h = 2.02%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.52%
- RSI : 61.1
- ADX 4H : 24.6 (DI+ 34 / DI- 15)
- Change 24h : -5.26%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.007400`
- Peak atteint : `$0.007800` (**+5.41%** du peak)
- Exit : `$0.006808`
- Hold : 10.6h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.006808** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.008140`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#118] ✅ <b>FLOWUSDT</b> +9.82% (+39.3$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.6%` ≤ 1.89%
- ✅ `range_4h = 0.83%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.57%
- RSI : 58.4
- ADX 4H : 27.3 (DI+ 33 / DI- 10)
- Change 24h : +0.81%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.033510`
- Peak atteint : `$0.037970` (**+13.31%** du peak)
- Exit : `$0.036740`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+9.64%)

**PnL final** : 💰 **+9.82%** (+39.28$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#119] ❌ <b>HOMEUSDT</b> -8.00% (-32.0$) — 2026-04-14 07:59 — exit: <code>SL_HIT</code> — hold 1j9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.21%` ≤ 1.89%
- ✅ `range_4h = 0.05%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.05%
- RSI : 61.4
- ADX 4H : 21.7 (DI+ 32 / DI- 11)
- Change 24h : +3.01%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.019640`
- Peak atteint : `$0.019640` (**+0.00%** du peak)
- Exit : `$0.018069`
- Hold : 1j9h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.018069** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.021604`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#120] ✅ <b>TREEUSDT</b> +9.97% (+39.9$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.9%` ≤ 1.89%
- ✅ `range_4h = 1.36%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.30%
- RSI : 63.2
- ADX 4H : 43.2 (DI+ 53 / DI- 6)
- Change 24h : -0.89%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.063400`
- Peak atteint : `$0.074100` (**+16.88%** du peak)
- Exit : `$0.069700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+9.94%)

**PnL final** : 💰 **+9.97%** (+39.87$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#121] ✅ <b>ZAMAUSDT</b> +19.19% (+76.8$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 2.7h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.91%` ≤ 1.89%
- ✅ `range_4h = 2.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.88%
- RSI : 59.7
- ADX 4H : 31.9 (DI+ 63 / DI- 6)
- Change 24h : -4.53%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.028010`
- Peak atteint : `$0.042920` (**+53.23%** du peak)
- Exit : `$0.039486`
- Hold : 2.7h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.030811` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.033612` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.042920` (+53.23%)
- 🚪 Trail stop touché à `$0.039486` (+40.97%) → 20% fermé.

**PnL final** : 💰 **+19.19%** (+76.78$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#122] ✅ <b>TURTLEUSDT</b> +6.95% (+27.8$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.23%` ≤ 1.89%
- ✅ `range_4h = 0.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.23%
- RSI : 67.8
- ADX 4H : 25.6 (DI+ 37 / DI- 14)
- Change 24h : -1.79%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.044600`
- Peak atteint : `$0.048600` (**+8.97%** du peak)
- Exit : `$0.047700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.049060`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+6.95%** (+27.80$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#123] ✅ <b>1000SATSUSDT</b> +17.37% (+69.5$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 1j21h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.79%` ≤ 1.89%
- ✅ `range_4h = 2.23%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 1.97%
- RSI : 71.0
- ADX 4H : 19.8 (DI+ 40 / DI- 15)
- Change 24h : +10.80%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00001168`
- Peak atteint : `$0.00001674` (**+43.32%** du peak)
- Exit : `$0.00001540`
- Hold : 1j21h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00001285` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00001402` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00001674` (+43.32%)
- 🚪 Trail stop touché à `$0.00001540` (+31.85%) → 20% fermé.

**PnL final** : 💰 **+17.37%** (+69.48$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#124] ❌ <b>HOMEUSDT</b> -8.00% (-32.0$) — 2026-04-14 07:59 — exit: <code>SL_HIT</code> — hold 1j9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.21%` ≤ 1.89%
- ✅ `range_4h = 0.05%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.05%
- RSI : 61.4
- ADX 4H : 21.7 (DI+ 32 / DI- 11)
- Change 24h : +3.01%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.019640`
- Peak atteint : `$0.019640` (**+0.00%** du peak)
- Exit : `$0.018069`
- Hold : 1j9h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.018069** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.021604`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#125] ✅ <b>TURTLEUSDT</b> +6.95% (+27.8$) — 2026-04-14 07:59 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.23%` ≤ 1.89%
- ✅ `range_4h = 0.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.23%
- RSI : 67.8
- ADX 4H : 25.6 (DI+ 37 / DI- 14)
- Change 24h : -1.79%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.044600`
- Peak atteint : `$0.048600` (**+8.97%** du peak)
- Exit : `$0.047700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.049060`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+6.95%** (+27.80$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#126] ✅ <b>ORDIUSDT</b> +15.02% (+60.1$) — 2026-04-14 07:59 — exit: <code>TRAIL_STOP</code> — hold 1j9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.25%` ≤ 1.89%
- ✅ `range_4h = 1.04%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.16%
- RSI : 63.2
- ADX 4H : 28.2 (DI+ 39 / DI- 15)
- Change 24h : +12.12%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$2.5110`
- Peak atteint : `$3.2780` (**+30.55%** du peak)
- Exit : `$3.0158`
- Hold : 1j9h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$2.7621` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$3.0132` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$3.2780` (+30.55%)
- 🚪 Trail stop touché à `$3.0158` (+20.10%) → 20% fermé.

**PnL final** : 💰 **+15.02%** (+60.08$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#127] ✅ <b>PEOPLEUSDT</b> +14.60% (+58.4$) — 2026-04-14 10:01 — exit: <code>TRAIL_STOP</code> — hold 2j6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.96%` ≤ 1.89%
- ✅ `range_4h = 1.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 1.08%
- RSI : 79.2
- ADX 4H : 25.4 (DI+ 64 / DI- 11)
- Change 24h : +2.38%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.007110`
- Peak atteint : `$0.009120` (**+28.27%** du peak)
- Exit : `$0.008390`
- Hold : 2j6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.007821` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.008532` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.009120` (+28.27%)
- 🚪 Trail stop touché à `$0.008390` (+18.01%) → 20% fermé.

**PnL final** : 💰 **+14.60%** (+58.41$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#128] ✅ <b>EIGENUSDT</b> +15.26% (+61.1$) — 2026-04-14 12:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.55%` ≤ 1.89%
- ✅ `range_4h = 0.37%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 55.8
- ADX 4H : 20.6 (DI+ 27 / DI- 14)
- Change 24h : +5.91%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.163200`
- Peak atteint : `$0.207000` (**+26.84%** du peak)
- Exit : `$0.198000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+21.32%)

**PnL final** : 💰 **+15.26%** (+61.06$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#129] ✅ <b>1000CHEEMSUSDT</b> +6.83% (+27.3$) — 2026-04-14 12:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 2.98%` ≤ 1.89%
- ✅ `range_4h = 2.98%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 2.13%
- RSI : 67.4
- ADX 4H : 24.6 (DI+ 37 / DI- 12)
- Change 24h : +11.45%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00051800`
- Peak atteint : `$0.00058600` (**+13.13%** du peak)
- Exit : `$0.00053700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+3.67%)

**PnL final** : 💰 **+6.83%** (+27.34$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#130] ✅ <b>SYRUPUSDT</b> +9.17% (+36.7$) — 2026-04-14 13:15 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.3%` ≤ 1.89%
- ✅ `range_4h = 2.22%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 0.77%
- RSI : 55.3
- ADX 4H : 32.9 (DI+ 29 / DI- 20)
- Change 24h : -1.58%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.224700`
- Peak atteint : `$0.246900` (**+9.88%** du peak)
- Exit : `$0.245300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.247170`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+9.17%** (+36.67$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#131] ❌ <b>FFUSDT</b> -4.41% (-17.6$) — 2026-04-14 13:36 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.3%` ≤ 1.89%
- ✅ `range_4h = 1.67%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.10%
- RSI : 64.7
- ADX 4H : 14.6 (DI+ 35 / DI- 15)
- Change 24h : +0.49%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.078170`
- Peak atteint : `$0.079990` (**+2.33%** du peak)
- Exit : `$0.074720`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.085987`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💔 **-4.41%** (-17.65$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#132] ✅ <b>RENDERUSDT</b> +2.10% (+8.4$) — 2026-04-14 13:51 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.49%` ≤ 1.89%
- ✅ `range_4h = 1.87%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.33%
- RSI : 62.5
- ADX 4H : 18.4 (DI+ 27 / DI- 17)
- Change 24h : +0.37%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$1.9060`
- Peak atteint : `$1.9500` (**+2.31%** du peak)
- Exit : `$1.9460`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$2.0966`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+2.10%** (+8.39$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#133] ✅ <b>VIRTUALUSDT</b> +11.56% (+46.2$) — 2026-04-14 13:51 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.77%` ≤ 1.89%
- ✅ `range_4h = 2.37%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.93%
- RSI : 69.9
- ADX 4H : 18.1 (DI+ 33 / DI- 10)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.693800`
- Peak atteint : `$0.789300` (**+13.76%** du peak)
- Exit : `$0.784800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+13.12%)

**PnL final** : 💰 **+11.56%** (+46.23$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#134] ✅ <b>METUSDT</b> +10.26% (+41.0$) — 2026-04-14 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.36%` ≤ 1.89%
- ✅ `range_4h = 2.58%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.84%
- RSI : 61.3
- ADX 4H : 23.1 (DI+ 36 / DI- 20)
- Change 24h : +0.29%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.138700`
- Peak atteint : `$0.153500` (**+10.67%** du peak)
- Exit : `$0.153300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+10.53%)

**PnL final** : 💰 **+10.26%** (+41.05$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#135] ✅ <b>GALAUSDT</b> +11.79% (+47.1$) — 2026-04-14 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.66%` ≤ 1.89%
- ✅ `range_4h = 2.36%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 1.34%
- RSI : 62.1
- ADX 4H : 19.1 (DI+ 25 / DI- 14)
- Change 24h : +2.37%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.003020`
- Peak atteint : `$0.003460` (**+14.57%** du peak)
- Exit : `$0.003430`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+13.58%)

**PnL final** : 💰 **+11.79%** (+47.15$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#136] ✅ <b>METUSDT</b> +10.26% (+41.0$) — 2026-04-14 14:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.36%` ≤ 1.89%
- ✅ `range_4h = 2.58%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.84%
- RSI : 61.3
- ADX 4H : 23.1 (DI+ 36 / DI- 20)
- Change 24h : +0.29%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.138700`
- Peak atteint : `$0.153500` (**+10.67%** du peak)
- Exit : `$0.153300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+10.53%)

**PnL final** : 💰 **+10.26%** (+41.05$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#137] ✅ <b>EGLDUSDT</b> +13.92% (+55.7$) — 2026-04-14 14:29 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.79%` ≤ 1.89%
- ✅ `range_4h = 1.59%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.06%
- RSI : 52.9
- ADX 4H : 24.1 (DI+ 27 / DI- 21)
- Change 24h : +2.96%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$3.8100`
- Peak atteint : `$4.5000` (**+18.11%** du peak)
- Exit : `$4.4900`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+17.85%)

**PnL final** : 💰 **+13.92%** (+55.70$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#138] ❌ <b>OXTUSDT</b> -8.00% (-32.0$) — 2026-04-14 15:29 — exit: <code>SL_HIT</code> — hold 18.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.95%` ≤ 1.89%
- ✅ `range_4h = 0.95%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 63.2
- ADX 4H : 33.5 (DI+ 47 / DI- 6)
- Change 24h : -2.75%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.011000`
- Peak atteint : `$0.011400` (**+3.64%** du peak)
- Exit : `$0.010120`
- Hold : 18.6h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.010120** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.012100`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#139] ✅ <b>APTUSDT</b> +11.94% (+47.8$) — 2026-04-14 15:50 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.51%` ≤ 1.89%
- ✅ `range_4h = 2.22%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.86%
- RSI : 64.4
- ADX 4H : 14.7 (DI+ 26 / DI- 18)
- Change 24h : +3.31%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.872000`
- Peak atteint : `$1.0190` (**+16.86%** du peak)
- Exit : `$0.993000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+13.88%)

**PnL final** : 💰 **+11.94%** (+47.75$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#140] ✅ <b>BOMEUSDT</b> +14.31% (+57.2$) — 2026-04-14 16:01 — exit: <code>TRAIL_STOP</code> — hold 1j14h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.96%` ≤ 1.89%
- ✅ `range_4h = 0.72%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.48%
- RSI : 56.5
- ADX 4H : 26.4 (DI+ 33 / DI- 15)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00041600`
- Peak atteint : `$0.00052700` (**+26.68%** du peak)
- Exit : `$0.00048484`
- Hold : 1j14h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00045760` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00049920` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00052700` (+26.68%)
- 🚪 Trail stop touché à `$0.00048484` (+16.55%) → 20% fermé.

**PnL final** : 💰 **+14.31%** (+57.24$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#141] ✅ <b>BOMEUSDT</b> +14.31% (+57.2$) — 2026-04-14 16:01 — exit: <code>TRAIL_STOP</code> — hold 1j14h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.96%` ≤ 1.89%
- ✅ `range_4h = 0.72%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.48%
- RSI : 56.5
- ADX 4H : 26.4 (DI+ 33 / DI- 15)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.00041600`
- Peak atteint : `$0.00052700` (**+26.68%** du peak)
- Exit : `$0.00048484`
- Hold : 1j14h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00045760` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00049920` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00052700` (+26.68%)
- 🚪 Trail stop touché à `$0.00048484` (+16.55%) → 20% fermé.

**PnL final** : 💰 **+14.31%** (+57.24$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#142] ✅ <b>SCRUSDT</b> +9.61% (+38.4$) — 2026-04-14 16:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.03%` ≤ 1.89%
- ✅ `range_4h = 0.97%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **10/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.26%
- RSI : 79.2
- ADX 4H : 24.3 (DI+ 56 / DI- 13)
- Change 24h : -1.72%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.044790`
- Peak atteint : `$0.050950` (**+13.75%** du peak)
- Exit : `$0.048920`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+9.22%)

**PnL final** : 💰 **+9.61%** (+38.44$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#143] ✅ <b>NILUSDT</b> +13.21% (+52.8$) — 2026-04-14 17:01 — exit: <code>TRAIL_STOP</code> — hold 2j7h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.84%` ≤ 1.89%
- ✅ `range_4h = 1.32%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.28%
- RSI : 67.1
- ADX 4H : 25.2 (DI+ 41 / DI- 14)
- Change 24h : +3.02%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.034960`
- Peak atteint : `$0.042200` (**+20.71%** du peak)
- Exit : `$0.038824`
- Hold : 2j7h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.038456` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.041952` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.042200` (+20.71%)
- 🚪 Trail stop touché à `$0.038824` (+11.05%) → 20% fermé.

**PnL final** : 💰 **+13.21%** (+52.84$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#144] ✅ <b>SHELLUSDT</b> +10.93% (+43.7$) — 2026-04-14 17:15 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.67%` ≤ 1.89%
- ✅ `range_4h = 1.01%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 56.2
- ADX 4H : 22.8 (DI+ 31 / DI- 14)
- Change 24h : +3.79%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.029500`
- Peak atteint : `$0.034000` (**+15.25%** du peak)
- Exit : `$0.033000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+11.86%)

**PnL final** : 💰 **+10.93%** (+43.73$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#145] ❌ <b>BARUSDT</b> -8.00% (-32.0$) — 2026-04-14 20:01 — exit: <code>SL_HIT</code> — hold 1.4h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.58%` ≤ 1.89%
- ✅ `range_4h = 1.15%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **WATCH** (45% confiance)
- Bougie 4H : direction **red**, body 0.38%
- RSI : 76.0
- ADX 4H : 27.4 (DI+ 43 / DI- 12)
- Change 24h : -0.19%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.570000`
- Peak atteint : `$0.582000` (**+2.11%** du peak)
- Exit : `$0.524400`
- Hold : 1.4h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.524400** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.627000`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#146] ✅ <b>ETHFIUSDT</b> +15.74% (+63.0$) — 2026-04-14 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.95%` ≤ 1.89%
- ✅ `range_4h = 0.95%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **red**, body 0.47%
- RSI : 45.3
- ADX 4H : 20.0 (DI+ 21 / DI- 23)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.422000`
- Peak atteint : `$0.537000` (**+27.25%** du peak)
- Exit : `$0.522000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+23.70%)

**PnL final** : 💰 **+15.74%** (+62.96$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#147] ✅ <b>LISTAUSDT</b> +16.53% (+66.1$) — 2026-04-14 20:01 — exit: <code>TRAIL_STOP</code> — hold 2j15h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.24%` ≤ 1.89%
- ✅ `range_4h = 0.87%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.12%
- RSI : 57.2
- ADX 4H : 23.4 (DI+ 33 / DI- 12)
- Change 24h : +5.46%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.081000`
- Peak atteint : `$0.112400` (**+38.77%** du peak)
- Exit : `$0.103408`
- Hold : 2j15h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.089100` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.097200` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.112400` (+38.77%)
- 🚪 Trail stop touché à `$0.103408` (+27.66%) → 20% fermé.

**PnL final** : 💰 **+16.53%** (+66.13$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#148] ✅ <b>ORDIUSDT</b> +15.78% (+63.1$) — 2026-04-14 20:01 — exit: <code>TRAIL_STOP</code> — hold 21.4h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.37%` ≤ 1.89%
- ✅ `range_4h = 0.37%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (83% confiance)
- Bougie 4H : direction **green**, body 0.21%
- RSI : 54.3
- ADX 4H : 28.6 (DI+ 29 / DI- 20)
- Change 24h : -2.71%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$2.4340`
- Peak atteint : `$3.2780` (**+34.68%** du peak)
- Exit : `$3.0158`
- Hold : 21.4h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$2.6774` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$2.9208` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$3.2780` (+34.68%)
- 🚪 Trail stop touché à `$3.0158` (+23.90%) → 20% fermé.

**PnL final** : 💰 **+15.78%** (+63.12$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#149] ✅ <b>ACMUSDT</b> +4.78% (+19.1$) — 2026-04-14 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.24%` ≤ 1.89%
- ✅ `range_4h = 0.48%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.24%
- RSI : 59.7
- ADX 4H : 22.4 (DI+ 24 / DI- 13)
- Change 24h : +0.48%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.418000`
- Peak atteint : `$0.443000` (**+5.98%** du peak)
- Exit : `$0.438000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.459800`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.78%** (+19.14$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#150] ✅ <b>LISTAUSDT</b> +16.53% (+66.1$) — 2026-04-14 20:01 — exit: <code>TRAIL_STOP</code> — hold 2j15h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.24%` ≤ 1.89%
- ✅ `range_4h = 0.87%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.12%
- RSI : 57.2
- ADX 4H : 23.4 (DI+ 33 / DI- 12)
- Change 24h : +5.46%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.081000`
- Peak atteint : `$0.112400` (**+38.77%** du peak)
- Exit : `$0.103408`
- Hold : 2j15h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.089100` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.097200` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.112400` (+38.77%)
- 🚪 Trail stop touché à `$0.103408` (+27.66%) → 20% fermé.

**PnL final** : 💰 **+16.53%** (+66.13$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#151] ✅ <b>ACMUSDT</b> +4.78% (+19.1$) — 2026-04-14 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.24%` ≤ 1.89%
- ✅ `range_4h = 0.48%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.24%
- RSI : 59.7
- ADX 4H : 22.4 (DI+ 24 / DI- 13)
- Change 24h : +0.48%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.418000`
- Peak atteint : `$0.443000` (**+5.98%** du peak)
- Exit : `$0.438000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.459800`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+4.78%** (+19.14$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#152] ✅ <b>0GUSDT</b> +1.47% (+5.9$) — 2026-04-14 20:30 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.51%` ≤ 1.89%
- ✅ `range_4h = 1.36%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.67%
- RSI : 71.5
- ADX 4H : 26.0 (DI+ 49 / DI- 12)
- Change 24h : -0.34%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.614000`
- Peak atteint : `$0.634000` (**+3.26%** du peak)
- Exit : `$0.623000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ⏰ **Timeout 72h** : prix oscillé sans atteindre TP1 (`$0.675400`) ni SL (-8.0%)
- Position fermée à 100% au prix de fin de fenêtre.

**PnL final** : 💰 **+1.47%** (+5.86$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#153] ✅ <b>STRKUSDT</b> +10.50% (+42.0$) — 2026-04-15 09:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.47%` ≤ 1.89%
- ✅ `range_4h = 1.77%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 0.59%
- RSI : 66.1
- ADX 4H : 25.4 (DI+ 28 / DI- 15)
- Change 24h : +6.19%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.032700`
- Peak atteint : `$0.037900` (**+15.90%** du peak)
- Exit : `$0.036300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+11.01%)

**PnL final** : 💰 **+10.50%** (+42.02$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#154] ✅ <b>INITUSDT</b> +10.95% (+43.8$) — 2026-04-15 09:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.0%` ≤ 1.89%
- ✅ `range_4h = 0.36%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (80% confiance)
- Bougie 4H : direction **red**, body 0.12%
- RSI : 73.9
- ADX 4H : 17.4 (DI+ 43 / DI- 18)
- Change 24h : +3.76%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.082400`
- Peak atteint : `$0.094900` (**+15.17%** du peak)
- Exit : `$0.092200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+11.89%)

**PnL final** : 💰 **+10.95%** (+43.79$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#155] ✅ <b>METUSDT</b> +10.17% (+40.7$) — 2026-04-15 09:16 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.0%` ≤ 1.89%
- ✅ `range_4h = 0.64%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY STRONG** (95% confiance)
- Bougie 4H : direction **red**, body 0.50%
- RSI : 61.1
- ADX 4H : 28.5 (DI+ 41 / DI- 16)
- Change 24h : +4.47%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.138200`
- Peak atteint : `$0.157700` (**+14.11%** du peak)
- Exit : `$0.152500`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+10.35%)

**PnL final** : 💰 **+10.17%** (+40.69$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#156] ✅ <b>CFXUSDT</b> +14.70% (+58.8$) — 2026-04-15 10:30 — exit: <code>TRAIL_STOP</code> — hold 1j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.78%` ≤ 1.89%
- ✅ `range_4h = 2.44%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 2.12%
- RSI : 63.6
- ADX 4H : 19.3 (DI+ 33 / DI- 17)
- BTC trend 1H : `BEARISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.054170`
- Peak atteint : `$0.069780` (**+28.82%** du peak)
- Exit : `$0.064198`
- Hold : 1j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.059587` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.065004` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.069780` (+28.82%)
- 🚪 Trail stop touché à `$0.064198` (+18.51%) → 20% fermé.

**PnL final** : 💰 **+14.70%** (+58.81$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#157] ✅ <b>SXTUSDT</b> +13.15% (+52.6$) — 2026-04-15 13:23 — exit: <code>TRAIL_STOP</code> — hold 2j6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.93%` ≤ 1.89%
- ✅ `range_4h = 2.51%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.50%
- RSI : 57.5
- ADX 4H : 22.9 (DI+ 29 / DI- 17)
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.016240`
- Peak atteint : `$0.019550` (**+20.38%** du peak)
- Exit : `$0.017986`
- Hold : 2j6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.017864` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.019488` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.019550` (+20.38%)
- 🚪 Trail stop touché à `$0.017986` (+10.75%) → 20% fermé.

**PnL final** : 💰 **+13.15%** (+52.60$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#158] ✅ <b>BERAUSDT</b> +6.11% (+24.5$) — 2026-04-15 17:08 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.24%` ≤ 1.89%
- ✅ `range_4h = 2.26%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 1.50%
- RSI : 65.7
- ADX 4H : 32.1 (DI+ 29 / DI- 14)
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.404000`
- Peak atteint : `$0.473000` (**+17.08%** du peak)
- Exit : `$0.413000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+2.23%)

**PnL final** : 💰 **+6.11%** (+24.46$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#159] ✅ <b>GUNUSDT</b> +13.78% (+55.1$) — 2026-04-15 20:20 — exit: <code>TRAIL_STOP</code> — hold 1j19h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.21%` ≤ 1.89%
- ✅ `range_4h = 1.91%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.13%
- RSI : 65.8
- ADX 4H : 21.2 (DI+ 32 / DI- 19)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.015790`
- Peak atteint : `$0.019550` (**+23.81%** du peak)
- Exit : `$0.017986`
- Hold : 1j19h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.017369` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.018948` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.019550` (+23.81%)
- 🚪 Trail stop touché à `$0.017986` (+13.91%) → 20% fermé.

**PnL final** : 💰 **+13.78%** (+55.13$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#160] ✅ <b>AVAUSDT</b> +12.45% (+49.8$) — 2026-04-15 23:43 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.76%` ≤ 1.89%
- ✅ `range_4h = 1.92%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.96%
- RSI : 62.6
- ADX 4H : 14.0 (DI+ 41 / DI- 20)
- Change 24h : +1.01%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 23

### Exit

**Trajectoire** :
- Entry : `$0.210800`
- Peak atteint : `$0.252300` (**+19.69%** du peak)
- Exit : `$0.242200`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+14.90%)

**PnL final** : 💰 **+12.45%** (+49.79$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#161] ❌ <b>PHAUSDT</b> -8.00% (-32.0$) — 2026-04-17 07:55 — exit: <code>SL_HIT</code> — hold 1j3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.53%` ≤ 1.89%
- ✅ `range_4h = 1.53%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.76%
- RSI : 69.4
- ADX 4H : 22.4 (DI+ 37 / DI- 16)
- Change 24h : +3.15%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.039800`
- Peak atteint : `$0.039800` (**+0.00%** du peak)
- Exit : `$0.036616`
- Hold : 1j3h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.036616** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.043780`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#162] ✅ <b>SAGAUSDT</b> +5.00% (+20.0$) — 2026-04-17 07:55 — exit: <code>BREAKEVEN_STOP</code> — hold 16.9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.79%` ≤ 1.89%
- ✅ `range_4h = 1.79%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.15%
- RSI : 39.9
- ADX 4H : 16.6 (DI+ 24 / DI- 23)
- Change 24h : -3.94%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 21

### Exit

**Trajectoire** :
- Entry : `$0.025800`
- Peak atteint : `$0.028950` (**+12.21%** du peak)
- Exit : `$0.025800`
- Hold : 16.9h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.028380` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.025800`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#163] ✅ <b>BIOUSDT</b> +5.00% (+20.0$) — 2026-04-18 20:01 — exit: <code>BREAKEVEN_STOP</code> — hold 19.7h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.35%` ≤ 1.89%
- ✅ `range_4h = 2.46%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **WATCH** (50% confiance)
- Bougie 4H : direction **red**, body 1.38%
- RSI : 60.6
- ADX 4H : 25.5 (DI+ 33 / DI- 14)
- Change 24h : -4.35%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 26

### Exit

**Trajectoire** :
- Entry : `$0.029100`
- Peak atteint : `$0.034900` (**+19.93%** du peak)
- Exit : `$0.029100`
- Hold : 19.7h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.032010` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.029100`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#164] ✅ <b>BIOUSDT</b> +5.00% (+20.0$) — 2026-04-18 20:01 — exit: <code>BREAKEVEN_STOP</code> — hold 19.7h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.35%` ≤ 1.89%
- ✅ `range_4h = 2.46%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **WATCH** (50% confiance)
- Bougie 4H : direction **red**, body 1.38%
- RSI : 60.6
- ADX 4H : 25.5 (DI+ 33 / DI- 14)
- Change 24h : -4.35%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 26

### Exit

**Trajectoire** :
- Entry : `$0.029100`
- Peak atteint : `$0.034900` (**+19.93%** du peak)
- Exit : `$0.029100`
- Hold : 19.7h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.032010` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.029100`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#165] ❌ <b>XAIUSDT</b> -8.00% (-32.0$) — 2026-04-18 20:01 — exit: <code>SL_HIT</code> — hold 21.9h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.18%` ≤ 1.89%
- ✅ `range_4h = 1.99%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 0.09%
- RSI : 51.2
- ADX 4H : 35.5 (DI+ 30 / DI- 11)
- Change 24h : +7.42%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 26

### Exit

**Trajectoire** :
- Entry : `$0.011150`
- Peak atteint : `$0.011400` (**+2.24%** du peak)
- Exit : `$0.010258`
- Hold : 21.9h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.010258** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.012265`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#166] ❌ <b>NFPUSDT</b> -8.00% (-32.0$) — 2026-04-19 00:01 — exit: <code>SL_HIT</code> — hold 17.5h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.33%` ≤ 1.89%
- ✅ `range_4h = 1.33%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 1.11%
- RSI : 43.9
- ADX 4H : 21.8 (DI+ 37 / DI- 19)
- Change 24h : -0.40%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.015290`
- Peak atteint : `$0.015290` (**+0.00%** du peak)
- Exit : `$0.014067`
- Hold : 17.5h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.014067** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.016819`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#167] ✅ <b>BOMEUSDT</b> +13.74% (+55.0$) — 2026-04-19 04:01 — exit: <code>TRAIL_STOP</code> — hold 9.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.98%` ≤ 1.89%
- ✅ `range_4h = 0.98%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.78%
- RSI : 62.9
- ADX 4H : 28.6 (DI+ 38 / DI- 15)
- Change 24h : -2.47%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.00050900`
- Peak atteint : `$0.00062900` (**+23.58%** du peak)
- Exit : `$0.00057868`
- Hold : 9.6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.00055990` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.00061080` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.00062900` (+23.58%)
- 🚪 Trail stop touché à `$0.00057868` (+13.69%) → 20% fermé.

**PnL final** : 💰 **+13.74%** (+54.95$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#168] ✅ <b>ZBTUSDT</b> +5.00% (+20.0$) — 2026-04-19 04:01 — exit: <code>BREAKEVEN_STOP</code> — hold 1j20h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.09%` ≤ 1.89%
- ✅ `range_4h = 1.09%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.54%
- RSI : 56.7
- ADX 4H : 32.9 (DI+ 30 / DI- 22)
- Change 24h : -10.60%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.110700`
- Peak atteint : `$0.127100` (**+14.81%** du peak)
- Exit : `$0.110700`
- Hold : 1j20h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.121770` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.110700`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#169] ❌ <b>LISTAUSDT</b> -8.00% (-32.0$) — 2026-04-19 20:01 — exit: <code>SL_HIT</code> — hold 1j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.42%` ≤ 1.89%
- ✅ `range_4h = 0.43%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.43%
- RSI : 53.5
- ADX 4H : 17.9 (DI+ 34 / DI- 25)
- Change 24h : +0.22%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.093100`
- Peak atteint : `$0.093100` (**+0.00%** du peak)
- Exit : `$0.085652`
- Hold : 1j23h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.085652** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.102410`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#170] ✅ <b>SUPERUSDT</b> +15.05% (+60.2$) — 2026-04-19 20:01 — exit: <code>TRAIL_STOP</code> — hold 11.3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.1%` ≤ 1.89%
- ✅ `range_4h = 0.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 59.8
- ADX 4H : 32.3 (DI+ 31 / DI- 22)
- Change 24h : +1.01%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.119600`
- Peak atteint : `$0.156300` (**+30.69%** du peak)
- Exit : `$0.143796`
- Hold : 11.3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.131560` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.143520` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.156300` (+30.69%)
- 🚪 Trail stop touché à `$0.143796` (+20.23%) → 20% fermé.

**PnL final** : 💰 **+15.05%** (+60.18$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#171] ✅ <b>EDUUSDT</b> +13.56% (+54.2$) — 2026-04-20 00:01 — exit: <code>TRAIL_STOP</code> — hold 15.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.43%` ≤ 1.89%
- ✅ `range_4h = 0.0%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 45.0
- ADX 4H : 22.1 (DI+ 27 / DI- 23)
- Change 24h : -12.68%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.042000`
- Peak atteint : `$0.051500` (**+22.62%** du peak)
- Exit : `$0.047380`
- Hold : 15.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.046200` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.050400` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.051500` (+22.62%)
- 🚪 Trail stop touché à `$0.047380` (+12.81%) → 20% fermé.

**PnL final** : 💰 **+13.56%** (+54.25$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#172] ✅ <b>EDUUSDT</b> +13.56% (+54.2$) — 2026-04-20 00:01 — exit: <code>TRAIL_STOP</code> — hold 15.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.43%` ≤ 1.89%
- ✅ `range_4h = 0.0%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 45.0
- ADX 4H : 22.1 (DI+ 27 / DI- 23)
- Change 24h : -12.68%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 27

### Exit

**Trajectoire** :
- Entry : `$0.042000`
- Peak atteint : `$0.051500` (**+22.62%** du peak)
- Exit : `$0.047380`
- Hold : 15.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.046200` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.050400` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.051500` (+22.62%)
- 🚪 Trail stop touché à `$0.047380` (+12.81%) → 20% fermé.

**PnL final** : 💰 **+13.56%** (+54.25$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#173] ✅ <b>THEUSDT</b> +8.02% (+32.1$) — 2026-04-20 02:22 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.22%` ≤ 1.89%
- ✅ `range_4h = 2.47%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.75%
- RSI : 61.6
- ADX 4H : 30.5 (DI+ 31 / DI- 20)
- Change 24h : -1.20%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.099300`
- Peak atteint : `$0.111200` (**+11.98%** du peak)
- Exit : `$0.105300`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+6.04%)

**PnL final** : 💰 **+8.02%** (+32.08$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#174] ✅ <b>CHZUSDT</b> +7.85% (+31.4$) — 2026-04-20 04:00 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.85%` ≤ 1.89%
- ✅ `range_4h = 0.5%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **red**, body 0.25%
- RSI : 74.1
- ADX 4H : 22.2 (DI+ 40 / DI- 13)
- Change 24h : +7.01%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.043920`
- Peak atteint : `$0.049140` (**+11.89%** du peak)
- Exit : `$0.046420`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+5.69%)

**PnL final** : 💰 **+7.85%** (+31.38$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#175] ✅ <b>RUNEUSDT</b> +13.90% (+55.6$) — 2026-04-20 07:36 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.72%` ≤ 1.89%
- ✅ `range_4h = 2.18%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.48%
- RSI : 71.1
- ADX 4H : 12.3 (DI+ 41 / DI- 15)
- Change 24h : +0.24%
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.420000`
- Peak atteint : `$0.512000` (**+21.90%** du peak)
- Exit : `$0.481000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+14.52%)

**PnL final** : 💰 **+13.90%** (+55.62$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#176] ✅ <b>STRKUSDT</b> +17.88% (+71.5$) — 2026-04-20 08:07 — exit: <code>TRAIL_STOP</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.87%` ≤ 1.89%
- ✅ `range_4h = 2.33%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.87%
- RSI : 54.8
- ADX 4H : 20.7 (DI+ 36 / DI- 24)
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.034500`
- Peak atteint : `$0.050400` (**+46.09%** du peak)
- Exit : `$0.046368`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.037950` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.041400` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.050400` (+46.09%)
- 🚪 Trail stop touché à `$0.046368` (+34.40%) → 20% fermé.

**PnL final** : 💰 **+17.88%** (+71.52$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#177] ✅ <b>DASHUSDT</b> +6.32% (+25.3$) — 2026-04-20 08:07 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.88%` ≤ 1.89%
- ✅ `range_4h = 1.74%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.03%
- RSI : 56.6
- ADX 4H : 25.9 (DI+ 27 / DI- 18)
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$34.0700`
- Peak atteint : `$37.6100` (**+10.39%** du peak)
- Exit : `$34.9700`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+2.64%)

**PnL final** : 💰 **+6.32%** (+25.28$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#178] ✅ <b>KATUSDT</b> +5.00% (+20.0$) — 2026-04-20 08:07 — exit: <code>BREAKEVEN_STOP</code> — hold 2j21h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.86%` ≤ 1.89%
- ✅ `range_4h = 0.86%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.32%
- RSI : 58.2
- ADX 4H : 19.6 (DI+ 31 / DI- 20)
- Change 24h : -1.58%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.009370`
- Peak atteint : `$0.010390` (**+10.89%** du peak)
- Exit : `$0.009370`
- Hold : 2j21h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.010307` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.009370`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#179] ✅ <b>RUNEUSDT</b> +13.92% (+55.7$) — 2026-04-20 08:07 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.48%` ≤ 1.89%
- ✅ `range_4h = 0.96%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **red**, body 0.24%
- RSI : 59.1
- ADX 4H : 16.2 (DI+ 34 / DI- 16)
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.418000`
- Peak atteint : `$0.512000` (**+22.49%** du peak)
- Exit : `$0.479000`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ✅ **TP2 hit** (30% fermé à +20.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+14.59%)

**PnL final** : 💰 **+13.92%** (+55.67$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#180] ✅ <b>NEWTUSDT</b> +15.24% (+61.0$) — 2026-04-20 08:07 — exit: <code>TRAIL_STOP</code> — hold 1j2h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.47%` ≤ 1.89%
- ✅ `range_4h = 1.07%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.40%
- RSI : 56.6
- ADX 4H : 37.3 (DI+ 30 / DI- 15)
- Change 24h : +3.44%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.075000`
- Peak atteint : `$0.099900` (**+33.20%** du peak)
- Exit : `$0.090896`
- Hold : 1j2h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.082500` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.090000` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.099900` (+33.20%)
- 🚪 Trail stop touché à `$0.090896` (+21.19%) → 20% fermé.

**PnL final** : 💰 **+15.24%** (+60.96$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#181] ✅ <b>GMTUSDT</b> +5.58% (+22.3$) — 2026-04-20 08:29 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.89%` ≤ 1.89%
- ✅ `range_4h = 0.71%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 60.7
- ADX 4H : 20.0 (DI+ 28 / DI- 15)
- Change 24h : +0.54%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.011230`
- Peak atteint : `$0.012550` (**+11.75%** du peak)
- Exit : `$0.011360`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+1.16%)

**PnL final** : 💰 **+5.58%** (+22.32$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#182] ✅ <b>GMTUSDT</b> +5.58% (+22.3$) — 2026-04-20 08:29 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.89%` ≤ 1.89%
- ✅ `range_4h = 0.71%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.00%
- RSI : 60.7
- ADX 4H : 20.0 (DI+ 28 / DI- 15)
- Change 24h : +0.54%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.011230`
- Peak atteint : `$0.012550` (**+11.75%** du peak)
- Exit : `$0.011360`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+1.16%)

**PnL final** : 💰 **+5.58%** (+22.32$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#183] ❌ <b>SUPERUSDT</b> -8.00% (-32.0$) — 2026-04-20 16:01 — exit: <code>SL_HIT</code> — hold 2j8h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.17%` ≤ 1.89%
- ✅ `range_4h = 0.73%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.29%
- RSI : 62.1
- ADX 4H : 35.7 (DI+ 38 / DI- 12)
- Change 24h : +17.55%
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.137700`
- Peak atteint : `$0.144300` (**+4.79%** du peak)
- Exit : `$0.126684`
- Hold : 2j8h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.126684** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.151470`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#184] ✅ <b>ALLOUSDT</b> +5.00% (+20.0$) — 2026-04-20 16:01 — exit: <code>BREAKEVEN_STOP</code> — hold 2j13h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.75%` ≤ 1.89%
- ✅ `range_4h = 1.31%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.09%
- RSI : 63.9
- ADX 4H : 22.2 (DI+ 34 / DI- 16)
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.115400`
- Peak atteint : `$0.132000` (**+14.38%** du peak)
- Exit : `$0.115400`
- Hold : 2j13h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.126940` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.115400`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#185] ✅ <b>ALLOUSDT</b> +7.87% (+31.5$) — 2026-04-20 20:01 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.17%` ≤ 1.89%
- ✅ `range_4h = 0.18%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.18%
- RSI : 56.1
- ADX 4H : 23.3 (DI+ 31 / DI- 14)
- Change 24h : +11.52%
- BTC trend 1H : `BULLISH_OK`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$0.111400`
- Peak atteint : `$0.132000` (**+18.49%** du peak)
- Exit : `$0.117800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+5.75%)

**PnL final** : 💰 **+7.87%** (+31.49$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#186] ✅ <b>ALLOUSDT</b> +5.00% (+20.0$) — 2026-04-21 00:01 — exit: <code>BREAKEVEN_STOP</code> — hold 2j5h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.06%` ≤ 1.89%
- ✅ `range_4h = 1.06%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.26%
- RSI : 58.8
- ADX 4H : 24.3 (DI+ 29 / DI- 13)
- Change 24h : +14.59%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.113400`
- Peak atteint : `$0.132000` (**+16.40%** du peak)
- Exit : `$0.113400`
- Hold : 2j5h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.124740` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.113400`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#187] ✅ <b>EULUSDT</b> +13.38% (+53.5$) — 2026-04-21 00:01 — exit: <code>TRAIL_STOP</code> — hold 1j8h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.64%` ≤ 1.89%
- ✅ `range_4h = 0.31%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **green**, body 0.23%
- RSI : 63.6
- ADX 4H : 27.3 (DI+ 39 / DI- 11)
- Change 24h : +8.98%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 29

### Exit

**Trajectoire** :
- Entry : `$1.2950`
- Peak atteint : `$1.5750` (**+21.62%** du peak)
- Exit : `$1.4490`
- Hold : 1j8h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$1.4245` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$1.5540` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$1.5750` (+21.62%)
- 🚪 Trail stop touché à `$1.4490` (+11.89%) → 20% fermé.

**PnL final** : 💰 **+13.38%** (+53.51$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#188] ✅ <b>JSTUSDT</b> +9.50% (+38.0$) — 2026-04-21 01:22 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.39%` ≤ 1.89%
- ✅ `range_4h = 2.31%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (60% confiance)
- Bougie 4H : direction **green**, body 1.25%
- RSI : 65.4
- ADX 4H : 24.9 (DI+ 40 / DI- 15)
- Change 24h : -0.53%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.074130`
- Peak atteint : `$0.084950` (**+14.60%** du peak)
- Exit : `$0.080800`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+9.00%)

**PnL final** : 💰 **+9.50%** (+38.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#189] ✅ <b>RUNEUSDT</b> +13.17% (+52.7$) — 2026-04-21 06:51 — exit: <code>TRAIL_STOP</code> — hold 2j3h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.47%` ≤ 1.89%
- ✅ `range_4h = 1.19%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BACKFILL**
- Bougie 4H : direction **green**, body 0.95%
- RSI : 62.8
- ADX 4H : 15.5 (DI+ 27 / DI- 19)
- BTC trend 1H : `BULLISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.425000`
- Peak atteint : `$0.512000` (**+20.47%** du peak)
- Exit : `$0.471040`
- Hold : 2j3h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.467500` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.510000` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.512000` (+20.47%)
- 🚪 Trail stop touché à `$0.471040` (+10.83%) → 20% fermé.

**PnL final** : 💰 **+13.17%** (+52.67$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#190] ✅ <b>BIOUSDT</b> +16.21% (+64.8$) — 2026-04-21 12:01 — exit: <code>TRAIL_STOP</code> — hold 1j14h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.37%` ≤ 1.89%
- ✅ `range_4h = 2.42%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.37%
- RSI : 52.8
- ADX 4H : 34.0 (DI+ 29 / DI- 12)
- Change 24h : +9.26%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.029200`
- Peak atteint : `$0.040000` (**+36.99%** du peak)
- Exit : `$0.036800`
- Hold : 1j14h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.032120` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.035040` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.040000` (+36.99%)
- 🚪 Trail stop touché à `$0.036800` (+26.03%) → 20% fermé.

**PnL final** : 💰 **+16.21%** (+64.82$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#191] ✅ <b>PEOPLEUSDT</b> +7.68% (+30.7$) — 2026-04-23 07:52 — exit: <code>TIMEOUT_72H</code> — hold 2j23h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.53%` ≤ 1.89%
- ✅ `range_4h = 2.02%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.21%
- RSI : 46.6
- ADX 4H : 17.8 (DI+ 22 / DI- 20)
- Change 24h : -5.75%
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 46

### Exit

**Trajectoire** :
- Entry : `$0.007460`
- Peak atteint : `$0.008270` (**+10.86%** du peak)
- Exit : `$0.007860`
- Hold : 2j23h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** (50% fermé à +10.0%)
- ⏰ **Timeout 72h** atteint avant trail/SL → 20-50% restants fermés au prix actuel (+5.36%)

**PnL final** : 💰 **+7.68%** (+30.72$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#192] ✅ <b>PLUMEUSDT</b> +5.00% (+20.0$) — 2026-04-23 08:35 — exit: <code>BREAKEVEN_STOP</code> — hold 1j15h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.79%` ≤ 1.89%
- ✅ `range_4h = 2.47%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 1.35%
- RSI : 64.5
- ADX 4H : 19.2 (DI+ 30 / DI- 16)
- BTC trend 1H : `NEUTRAL`
- Fear & Greed : 46

### Exit

**Trajectoire** :
- Entry : `$0.012840`
- Peak atteint : `$0.014250` (**+10.98%** du peak)
- Exit : `$0.012840`
- Hold : 1j15h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.014124` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.012840`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#193] ✅ <b>ESPUSDT</b> +14.25% (+57.0$) — 2026-04-23 11:56 — exit: <code>TRAIL_STOP</code> — hold 20.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.65%` ≤ 1.89%
- ✅ `range_4h = 0.14%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 0.06%
- RSI : 70.7
- ADX 4H : 23.4 (DI+ 44 / DI- 12)
- Change 24h : +2.33%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 46

### Exit

**Trajectoire** :
- Entry : `$0.070590`
- Peak atteint : `$0.089180` (**+26.34%** du peak)
- Exit : `$0.082046`
- Hold : 20.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.077649` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.084708` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.089180` (+26.34%)
- 🚪 Trail stop touché à `$0.082046` (+16.23%) → 20% fermé.

**PnL final** : 💰 **+14.25%** (+56.98$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#194] ✅ <b>MOVRUSDT</b> +18.28% (+73.1$) — 2026-04-23 12:00 — exit: <code>TRAIL_STOP</code> — hold 1.6h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 1.39%` ≤ 1.89%
- ✅ `range_4h = 1.39%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **red**, body 0.11%
- RSI : 68.6
- ADX 4H : 38.8 (DI+ 34 / DI- 7)
- Change 24h : +4.62%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 46

### Exit

**Trajectoire** :
- Entry : `$1.8130`
- Peak atteint : `$2.6880` (**+48.26%** du peak)
- Exit : `$2.4730`
- Hold : 1.6h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$1.9943` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$2.1756` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$2.6880` (+48.26%)
- 🚪 Trail stop touché à `$2.4730` (+36.40%) → 20% fermé.

**PnL final** : 💰 **+18.28%** (+73.12$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#195] ✅ <b>TREEUSDT</b> +16.56% (+66.2$) — 2026-04-23 21:35 — exit: <code>TRAIL_STOP</code> — hold 16.7h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.3%` ≤ 1.89%
- ✅ `range_4h = 1.97%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 1.82%
- RSI : 59.1
- ADX 4H : 26.1 (DI+ 32 / DI- 25)
- Change 24h : -3.44%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 46

### Exit

**Trajectoire** :
- Entry : `$0.067300`
- Peak atteint : `$0.093500` (**+38.93%** du peak)
- Exit : `$0.086020`
- Hold : 16.7h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.074030` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.080760` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.093500` (+38.93%)
- 🚪 Trail stop touché à `$0.086020` (+27.82%) → 20% fermé.

**PnL final** : 💰 **+16.56%** (+66.25$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#196] ✅ <b>0GUSDT</b> +5.00% (+20.0$) — 2026-04-25 14:36 — exit: <code>BREAKEVEN_STOP</code> — hold 1j11h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.52%` ≤ 1.89%
- ✅ `range_4h = 2.47%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **7/10**
- Décision OpenClaw : **BUY WEAK** (55% confiance)
- Bougie 4H : direction **green**, body 2.11%
- RSI : 70.7
- ADX 4H : 18.3 (DI+ 30 / DI- 19)
- Change 24h : +0.69%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 31

### Exit

**Trajectoire** :
- Entry : `$0.579000`
- Peak atteint : `$0.654000` (**+12.95%** du peak)
- Exit : `$0.579000`
- Hold : 1j11h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.636900` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.579000`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#197] ✅ <b>ACTUSDT</b> +5.00% (+20.0$) — 2026-04-26 00:01 — exit: <code>BREAKEVEN_STOP</code> — hold 1j5h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.69%` ≤ 1.89%
- ✅ `range_4h = 0.69%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **8/10**
- Décision OpenClaw : **BUY** (65% confiance)
- Bougie 4H : direction **green**, body 0.69%
- RSI : 66.5
- ADX 4H : 27.0 (DI+ 35 / DI- 11)
- Change 24h : +2.11%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 31

### Exit

**Trajectoire** :
- Entry : `$0.014500`
- Peak atteint : `$0.016500` (**+13.79%** du peak)
- Exit : `$0.014500`
- Hold : 1j5h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.015950` (+10.0%) → fermeture de **50%** = profit locké de **$20.00**.
- 🛡 Stop déplacé à BREAKEVEN (`$0.014500`).
- Le prix n'a PAS atteint TP2 (+20.0%) → est redescendu à BE.
- Les 50% restants fermés au breakeven (0% sur cette portion).

**PnL final** : 💰 **+5.00%** (+20.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#198] ❌ <b>ALLOUSDT</b> -8.00% (-32.0$) — 2026-04-26 01:01 — exit: <code>SL_HIT</code> — hold 1j10h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.08%` ≤ 1.89%
- ✅ `range_4h = 1.46%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **6/10**
- Décision OpenClaw : **WATCH** (30% confiance)
- Bougie 4H : direction **green**, body 0.77%
- RSI : 55.0
- ADX 4H : 18.9 (DI+ 34 / DI- 23)
- Change 24h : -3.13%
- BTC trend 1H : `BEARISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.117700`
- Peak atteint : `$0.118900` (**+1.02%** du peak)
- Exit : `$0.108284`
- Hold : 1j10h

**Évènements (logique exit hybride V7)** :
- ❌ **Stop Loss touché à $0.108284** (-8.0% sous l'entry).
- Le prix n'a JAMAIS atteint TP1 (+10.0%, soit `$0.129470`).
- Position fermée à 100% au prix du SL.

**PnL final** : 💔 **-8.00%** (-32.00$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>

<details>
<summary>[#199] ✅ <b>LDOUSDT</b> +13.69% (+54.8$) — 2026-04-26 08:01 — exit: <code>TRAIL_STOP</code> — hold 12.1h</summary>

### Entry

**Conditions du filtre V11B (gate)** :
- ✅ `range_30m = 0.4%` ≤ 1.89%
- ✅ `range_4h = 0.4%` ≤ 2.58%
- ✅ Les 2 conditions du gate V11B passent → entrée AUTORISÉE.

**Contexte au moment de l'alerte** :
- Scanner score : **9/10**
- Décision OpenClaw : **BUY STRONG** (75% confiance)
- Bougie 4H : direction **red**, body 0.37%
- RSI : 68.3
- ADX 4H : 26.7 (DI+ 34 / DI- 12)
- Change 24h : +0.37%
- BTC trend 1H : `BULLISH`
- Fear & Greed : 33

### Exit

**Trajectoire** :
- Entry : `$0.381200`
- Peak atteint : `$0.470000` (**+23.29%** du peak)
- Exit : `$0.432400`
- Hold : 12.1h

**Évènements (logique exit hybride V7)** :
- ✅ **TP1 hit** à `$0.419320` (+10.0%) → 50% fermé = $20.00
- ✅✅ **TP2 hit** à `$0.457440` (+20.0%) → 30% fermé = $24.00
- 🔄 **Trailing activé** sur les 20% restants (distance -8.0% du peak)
- 📈 Peak final : `$0.470000` (+23.29%)
- 🚪 Trail stop touché à `$0.432400` (+13.43%) → 20% fermé.

**PnL final** : 💰 **+13.69%** (+54.75$ sur $400.0 investis)

_Trade simulé en backfill (HYDRATED_BACKTEST). Logique exit hybride V7 appliquée sur klines historiques 5m._

</details>
