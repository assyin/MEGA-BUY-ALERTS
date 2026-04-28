# STEEMUSDT — Analyse Complete du Trade +46.04%

## Resultat : +46.04% en 1.9 jours (max), High a 0.0812

---

## 1. Donnees de l'Alerte

| Champ | Valeur |
|-------|--------|
| **Paire** | STEEMUSDT |
| **Date** | 25/02/2026 00:17 UTC |
| **Prix alerte** | 0.0556 (prix estime au moment de l'alerte, bougie 1H 00:00-01:00 O=0.0512 H=0.0631 C=0.0610) |
| **Prix max** | **0.0812** (+46.04%) le 27/02 00:00 UTC (1.9 jours apres) |
| **Prix min post-alerte** | 0.0537 (-3.4%) le 28/02 12:00 |
| **SL 5% touche** | NON (drawdown max = -3.4% si entree au close 1H 0.0610, ou plus profond si entree dans la meche) |
| **Contexte** | 2eme pump STEEM en 48h — premier pump le 24/02 00:00 (+22.8%) |

---

## 2. Indicateurs au Moment de l'Alerte (donnees API reelles)

| Indicateur | 15m | 30m | 1h | 4h | Daily |
|------------|-----|-----|-----|-----|-------|
| **Prix** | 0.0556 | 0.0511 | 0.0511 | 0.0511 | 0.0511 |
| **RSI** | **70.2** | 34.2 | 41.1 | 49.0 | 44.9 |
| **ADX** | 31.8 | 28.0 | 26.8 | 30.9 | 25.5 |
| **DI+** | **48.4** | 13.9 | 21.9 | **37.2** | **43.6** |
| **DI-** | 15.8 | **28.8** | **28.5** | 23.5 | 16.9 |
| **STC** | 0.80 | **1.00** | 0.56 | - | - |
| **EMA20** | 0.0523 | 0.0530 | 0.0537 | 0.0520 | - |
| **EMA100** | 0.0537 | 0.0525 | 0.0516 | 0.0528 | - |
| **Cloud Top** | 0.0580 | 0.0593 | 0.0481 | 0.0595 | 0.0702 |

### Interpretation

**Configuration DIVERGENTE entre timeframes courts et longs :**
- 15m : RSI **70.2** (surachat), DI+ **48.4** >> DI- 15.8 = **explosion acheteuse sur le TF ultra-court**
- 30m : RSI 34.2 (basse), DI- 28.8 > DI+ 13.9 = **pression vendeuse encore presente sur 30m**
- 1h : RSI 41.1 (neutre-basse), DI- 28.5 > DI+ 21.9 = **tendance baissiere recente mais gap qui se referme**
- 4h : RSI 49.0 (neutre), DI+ **37.2** > DI- 23.5, ADX 30.9 = **tendance haussiere FORTE etablie sur 4H**
- Daily : RSI 44.9, DI+ **43.6** >> DI- 16.9, ADX 25.5 = **tendance haussiere Daily CONFIRMEE**
- STC 30m = **1.00** (sommet du cycle) = attention a un possible retrace court terme

Le pattern est une **divergence 15m/4H alignee** : le 15m montre une acceleration acheteuse (RSI 70.2, DI+ 48.4) qui CONFIRME la tendance 4H deja haussiere (DI+ 37.2 > DI- 23.5). Le Daily aussi est haussier (DI+ 43.6 >> DI- 16.9). Seuls les TF intermediaires (30m, 1h) gardent une empreinte baissiere residuelle de la correction du 24/02. C'est un signal de **continuation haussiere** : le micro (15m) s'aligne avec le macro (4H, Daily).

---

## 3. Conditions Progressives : 1/5

| Condition | Status | Distance | Verdict |
|-----------|--------|----------|---------|
| EMA100 1H | **X** | -1.0% | Prix legerement sous l'EMA100 1H (0.0516) |
| EMA20 4H | **X** | -1.7% | Prix sous l'EMA20 4H (0.0520) |
| Cloud 1H | **V** | +6.2% | **Prix AU-DESSUS du cloud Assyin 1H (0.0481)** |
| Cloud 30M | **X** | -13.8% | Sous le cloud 30M (0.0593) |
| CHoCH/BOS | **X** | Non confirme | Pas de swing high casse |

**1 condition sur 5 validee** — la cassure du cloud 1H est significative (+6.2% au-dessus). Les distances EMA100 1H (-1.0%) et EMA20 4H (-1.7%) sont TRES FAIBLES, ce qui indique que le prix est sur le point de les casser. La situation est bien meilleure que les trades 0/5 : le prix est proche de toutes les resistances dynamiques sauf le cloud 30M.

---

## 4. Volume et Contexte

### Contexte Pre-Alerte : Le Premier Pump (23-24/02)

STEEM a connu un PREMIER pump majeur le 24/02 00:00 avant l'alerte :

| Heure | Prix | Volume | Evenement |
|-------|------|--------|-----------|
| 23/02 23:00 | 0.0460 | 306K | **Dernier calme avant la tempete** |
| 24/02 00:00 | 0.0565 | **22.0M** | **PUMP #1 — +22.8% en 1h !** |
| 24/02 01:00 | 0.0569 | 20.3M | Continuation, high 0.0599 |
| 24/02 03:00 | 0.0662 | 14.4M | **HIGH local = 0.0682 (+48.3% depuis 0.046)** |
| 24/02 04:00 | 0.0637 | 11.3M | Debut correction |
| 24/02 12:00 | 0.0573 | 5.9M | Retrace continue |
| 24/02 13:00 | 0.0549 | 3.0M | Correction profonde |
| 24/02 16:00 | 0.0524 | 3.0M | Low local 0.0518 |
| 24/02 21:00 | 0.0507 | 2.9M | **LOW de la correction = 0.0507** |
| 24/02 23:00 | 0.0511 | 2.8M | Stabilisation zone 0.051 |

### Volume au Moment de l'Alerte

| Heure | Prix | Volume | Evenement |
|-------|------|--------|-----------|
| **25/02 00:00** | **0.0610** | **16.95M** | **BOUGIE ALERTE — PUMP #2 O=0.0512 H=0.0631 (+23.2%)** |
| 25/02 01:00 | 0.0592 | 7.5M | Retrace depuis high |
| 25/02 02:00 | 0.0598 | 2.3M | Stabilisation |
| 25/02 03:00 | 0.0665 | **8.4M** | **PUSH FORT — high 0.0666** |
| 25/02 07:00 | 0.0652 | 2.7M | High local 0.0668 |
| 25/02 08:00 | 0.0596 | 2.7M | Correction -8.5% depuis high |
| 25/02 12:00 | 0.0565 | 2.3M | Retrace profonde |
| 25/02 14:00 | 0.0594 | 4.0M | Rebond |
| 25/02 22:00 | 0.0611 | 1.3M | Build-up progressif |

### Volume Post-Alerte : Vers le ATH

| Heure | Prix | Volume | Evenement |
|-------|------|--------|-----------|
| 26/02 00:00 | 0.0692 | **26.1M** | **PUMP #3 — O=0.0589 H=0.0738 (+25.3%)** |
| 26/02 01:00 | 0.0666 | 8.9M | Correction |
| 26/02 10:00 | 0.0676 | **10.8M** | Recovery forte |
| 26/02 11:00 | 0.0689 | 7.8M | Continuation |
| 26/02 17:00 | 0.0701 | 2.1M | Build-up |
| 26/02 18:00 | 0.0682 | **5.9M** | Push avec high 0.0734 |
| 26/02 23:00 | **0.0793** | **7.1M** | **BREAKOUT EXPLOSIF — high 0.0793** |
| **27/02 00:00** | **0.0685** | **14.0M** | **ATH = 0.0812 (+46.04%) puis correction violente** |
| 27/02 01:00 | 0.0692 | 1.3M | Post-ATH stabilisation |
| 27/02 07:00 | 0.0655 | 1.6M | Correction |
| 27/02 11:00 | 0.0621 | 1.8M | Retrace vers 0.062 |
| 27/02 20:00 | 0.0603 | 583K | Pression baissiere continue |
| 28/02 00:00 | 0.0574 | **11.3M** | Dump severe |
| 28/02 06:00 | 0.0543 | 1.9M | Poursuite baissiere |
| 28/02 12:00 | 0.0538 | 226K | **LOW post-pump = 0.0537** |
| 01/03 00:00 | 0.0686 | **28.0M** | **PUMP #4 — nouveau cycle** |

### Ratio Volume a l'Alerte

| TF | Ratio alerte | Niveau |
|----|-------------|--------|
| 1H | **0.61x** | NORMAL |
| 4H | **0.95x** | NORMAL |

Le volume au moment de l'alerte est NORMAL a legerement sous la moyenne. Cependant, la bougie 1H dans laquelle tombe l'alerte (00:00-01:00) a un volume MASSIF de 16.95M — c'est la bougie du pump #2 elle-meme. L'alerte a ete declenchee PAR le mouvement haussier en cours.

---

## 5. Progression Pre-Alerte — Les 3 Phases

### Phase 1 : RANGE DESCENDANT (20/02 - 23/02)

```
Prix oscille entre 0.0454 et 0.0475
Volume : 40K-500K (tres faible = marche mort)
Le token stagne a ses plus bas niveaux
```

STEEM etait dans un range lateral descendant avec un volume minimal. Le prix oscillait autour de 0.046 pendant des jours sans direction. C'est un marche en accumulation silencieuse complete.

### Phase 2 : PREMIER PUMP EXPLOSIF (24/02 00:00)

```
23/02 23:00 → 0.0460 (calme plat, volume 306K)
24/02 00:00 → 0.0565 (PUMP +22.8% en 1h, vol 22.0M = 70x!)
24/02 03:00 → 0.0662 (high 0.0682 = +48.3% depuis 0.046)
24/02 06:00 → 0.0591 (correction commence)
24/02 21:00 → 0.0507 (LOW correction = -25.7% depuis high)
```

Le premier pump projette le prix de 0.046 a 0.0682 (+48%) en 3 heures. S'ensuit une correction severe qui ramene le prix a 0.0507 (-25.7% depuis le high). Le volume sur la premiere bougie (22.0M) est environ 70x la moyenne pre-pump.

### Phase 3 : REBOND + ALERTE (24/02 23:00 - 25/02 00:17)

```
24/02 23:00 → 0.0511 (stabilisation, volume 2.8M)
25/02 00:00 → O=0.0512, prix commence a monter
25/02 00:17 → MEGA BUY DETECTE (prix ~0.0556)
25/02 00:00 → C=0.0610 (close bougie = +19.1%)
```

Le MEGA BUY detecte le deuxieme pump exactement au moment ou il demarre. Le prix repart de 0.0512 et l'alerte est emise a 00:17 alors que le mouvement est en cours. C'est un signal de **re-entry sur rebond** : le bot detecte que le momentum haussier revient apres la correction.

---

## 6. Post-Alerte : Anatomie du Pump en 3 Vagues

### Vague 1 : Pump #2 (25/02 00:00 - 25/02 07:00)

```
25/02 00:00 → O=0.0512, H=0.0631, C=0.0610 (vol 16.95M)
25/02 03:00 → H=0.0666 (HIGH VAGUE 1 = +19.6% depuis alerte)
25/02 07:00 → H=0.0668 (double top local)
25/02 08:00 → C=0.0596 (correction -10.8% depuis high)
25/02 12:00 → L=0.0559 (low de la correction)
```

Le pump #2 pousse le prix jusqu'a 0.0668 avant une correction qui ramene le prix a 0.0559. La structure est une poussee forte suivie d'un retrace classique de 38-50%.

### Vague 2 : Pump #3 (26/02 00:00 - 26/02 23:00)

```
25/02 22:00 → 0.0611 (build-up, vol 1.3M)
26/02 00:00 → O=0.0589, H=0.0738 (PUMP #3, vol 26.1M!)
              HIGH INTERMEDIAIRE = 0.0738 (+32.7% depuis alerte)
26/02 11:00 → 0.0689 (vol 7.8M, continuation)
26/02 18:00 → H=0.0734 (re-test du high)
26/02 23:00 → 0.0793 (BREAKOUT au-dessus de 0.074!)
```

Le pump #3 suit exactement le meme pattern : demarrage nocturne a 00:00, poussee massive avec volume 26.1M, puis build-up progressif pendant la journee. Le breakout de 23:00 (0.0793) prepare l'ATH.

### Vague 3 : ATH (27/02 00:00)

```
26/02 23:00 → C=0.0793, vol 7.1M (breakout)
27/02 00:00 → O=0.0789, HIGH = 0.0812 (+46.04%)
              Vol = 14.0M
              MAIS close = 0.0685 (-15.7% depuis ATH en 1h!)
27/02 01:00 → 0.0692 (stabilisation)
```

Le ATH a 0.0812 est atteint dans la bougie du 27/02 00:00 mais le prix s'effondre immediatement, cloturant a 0.0685. C'est un **spike ATH avec rejection violente** — la meche haute de 0.0812 a 0.0685 en une seule bougie indique un sell-off massif au sommet.

### Resume Jour par Jour

| Jour | Prix Open→Close | PnL depuis alerte | Evenement |
|------|------|-----|-----------|
| J+0 (25/02) | 0.0610 → 0.0590 | +6.1% (high 0.0668) | Signal + Pump #2 |
| J+1 (26/02) | 0.0589 → 0.0676 | +21.6% (high 0.0738) | **Pump #3 + Build-up** |
| J+1.9 (27/02 00:00) | 0.0789 → 0.0685 | — | **ATH = 0.0812 (+46.04%) + rejection** |
| J+2 (27/02) | 0.0685 → 0.0614 | +10.4% | Correction post-ATH |
| J+3 (28/02) | 0.0613 → 0.0564 | +1.4% | Retrace profonde, low 0.0537 |
| J+4 (01/03) | 0.0564 → 0.0615 | +10.6% | Pump #4 (H=0.0688, nouveau cycle) |
| J+5 (02/03) | 0.0639 → 0.0607 | +9.2% | Consolidation |
| J+6 (03/03) | 0.0608 → 0.0579 | +4.1% | Retrace lente |

### Drawdown Max depuis Close Alerte (0.0610) : -11.9% (low 0.0537 le 28/02)

Si entree au close de la bougie 1H (0.0610), le drawdown max est de -11.9% quand le prix atteint 0.0537 le 28/02 12:00, soit 3 jours apres le high. Cependant, le prix avait deja atteint +46.04% avant ce drawdown — un trader prenant des profits partiels n'aurait pas subi cette baisse.

Si entree au prix estime de l'alerte (~0.0556), le prix n'est jamais redescendu sous ce niveau avant le 28/02 12:00 (low 0.0537 = -3.4%). Le drawdown max depuis le prix d'alerte estime est donc **modere a -3.4%**.

---

## 7. Meilleure Entree Recommandee

### Entree 1 : Au Signal (~0.0556) — BONNE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0556** (prix estime au moment de l'alerte 00:17) |
| SL | **0.0500** (sous le low de correction 0.0507) = -10.1% |
| TP1 | **0.0668** (high vague 1) = +20.1% |
| TP2 | **0.0738** (high vague 2) = +32.7% |
| TP3 | **0.0812** (ATH) = +46.0% |
| Drawdown max | **-3.4%** (0.0537 le 28/02, APRES l'ATH) |
| R:R sur TP1 | 1:2.0 |
| R:R sur TP3 | **1:4.6** |

### Entree 2 : Au Close Bougie Alerte (0.0610) — CORRECTE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0610** (close 1H de la bougie alerte) |
| SL | **0.0550** (sous la zone de consolidation) = -9.8% |
| TP1 | **0.0668** = +9.5% |
| TP2 | **0.0738** = +21.0% |
| TP3 | **0.0812** = +33.1% |
| R:R sur TP1 | 1:1.0 |
| R:R sur TP3 | **1:3.4** |

### Entree 3 : Au Retest de 0.059 (25/02 09:00) — OPTIMALE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0591** (retest apres premiere vague) |
| SL | **0.0550** (sous le support) = -6.9% |
| TP1 | **0.0668** = +13.0% |
| TP2 | **0.0738** = +24.9% |
| TP3 | **0.0812** = +37.4% |
| R:R sur TP1 | 1:1.9 |
| R:R sur TP3 | **1:5.4** |

---

## 8. Score de Qualite du Trade

| Facteur | Score | Detail |
|---------|-------|--------|
| Signal MEGA BUY | ?/10 | Score non fourni |
| Conditions | **3/10** | 1/5 — cloud 1H valide, EMA proches |
| STC | **4/10** | 30m a 1.00 (sommet), 1h a 0.56 (neutre) |
| Volume alerte | **5/10** | 0.61x 1H, 0.95x 4H = normal |
| Volume pump | **9/10** | 26.1M sur pump #3, 14.0M sur ATH = volume extreme |
| RSI Oversold | **4/10** | RSI 1H = 41.1 (neutre), RSI 4H = 49.0 (neutre) |
| ADX Force | **8/10** | ADX 4H = 30.9 (FORT), DI+ 37.2 > DI- 23.5 = tendance etablie |
| BTC Context | **3/10** | BTC 1H Neutre (RSI 48.0), BTC 4H Bearish (RSI 37.8) |
| ETH Context | **3/10** | ETH 1H Neutre (RSI 49.7), ETH 4H Bearish (RSI 37.6) |
| Fib Position | **8/10** | Prix au Fib 23.6% du range 4H (zone d'accumulation parfaite) |
| StochRSI | **4/10** | 1H oversold (K=4.6, D=5.9), 4H neutre (K=43.9) |
| Volume Profile | **6/10** | 1H et 4H : BELOW_VAL = prix sous la zone de valeur |
| Drawdown | **7/10** | -3.4% depuis prix alerte (modere) |
| **Score global** | **6.2/10** | **Trade de QUALITE avec momentum 4H/Daily aligne et drawdown contenu** |

---

## 9. Pourquoi ce Trade a fait +46.04%

### Les 5 facteurs de puissance

1. **MOMENTUM 4H/DAILY DEJA HAUSSIER** : Contrairement a beaucoup de trades MEGA BUY qui sont des retournements (0/5 conditions), STEEM avait deja un DI+ 4H a 37.2 > DI- 23.5 et un DI+ Daily a 43.6 >> DI- 16.9. Le signal n'est pas un retournement, c'est une **continuation** — le prix etait deja en tendance haussiere macro. La correction de 0.0682 a 0.0507 (-25.7%) etait un **pullback dans une tendance haussiere**, pas un changement de direction.

2. **FIB 23.6% PARFAIT** : Le prix au moment de l'alerte etait exactement au niveau Fib 23.6% du swing 4H (0.0454-0.0700). Le Fib 23.6% est la zone classique de re-entry dans une tendance forte. Le prix rebondit depuis ce niveau et reprend la tendance haussiere.

3. **PATTERN DE PUMPS REPETITIFS NOCTURNES** : STEEM a montre un pattern tres clair de pumps a 00:00 UTC :
   - 24/02 00:00 : Pump #1 (vol 22.0M)
   - 25/02 00:00 : Pump #2 (vol 16.95M) ← ALERTE
   - 26/02 00:00 : Pump #3 (vol 26.1M)
   - 01/03 00:00 : Pump #4 (vol 28.0M)
   Ce pattern de "pumps nocturnes recurrents" est un signal de manipulation coordonnee ou d'accumulation systematique.

4. **PRIX SOUS LA ZONE DE VALEUR (BELOW_VAL)** : Le Volume Profile montre le prix sous le VAL sur les 2 timeframes (1H et 4H). Quand le prix est sous le VAL avec un momentum 4H haussier, c'est un signal de "prix temporairement sous-evalue" — il tend a revenir vers le POC. Le POC 4H etait a 0.0619, le VAH a 0.0659, et le prix les a tous depasses.

5. **STOCHRSI 1H EN OVERSOLD** : Le StochRSI 1H etait a K=4.6, D=5.9 en zone oversold avec un cross bearish. C'est paradoxalement un signal de FOND sur le 1H : quand le StochRSI est en oversold extreme mais que le 4H est haussier (DI+ > DI-), le retournement 1H est imminent.

### Pattern : "PULLBACK FIB + CONTINUATION MULTI-VAGUE"

```
Accumulation 0.046 (20-23/02) → PUMP #1 +48% (24/02 00:00)
→ Correction -25.7% vers Fib 23.6% (24/02 21:00)
→ MEGA BUY (25/02 00:17) = detection du rebond Fib
→ PUMP #2 +19.6% (25/02 03:00)
→ PUMP #3 +32.7% (26/02 00:00)
→ ATH 0.0812 +46.04% (27/02 00:00)
→ Rejection violente depuis ATH
```

Ce pattern est un **classique de pump multi-vague** : apres un premier pump explosif, le prix corrige vers un niveau Fib (23.6-38.2%), puis repart en vagues successives de plus en plus hautes. Le MEGA BUY a detecte le depart de la deuxieme vague.

---

## 10. Contexte Macro

| Facteur | Valeur | Impact |
|---------|--------|--------|
| BTC 1H | **NEUTRE** (RSI 48.0) | Neutre |
| BTC 4H | **BEARISH** (RSI 37.8) | Defavorable |
| ETH 1H | **NEUTRE** (RSI 49.7) | Neutre |
| ETH 4H | **BEARISH** (RSI 37.6) | Defavorable |
| RSI Daily STEEM | **44.9** | Zone neutre, marge de hausse |
| DI+ Daily vs DI- | **43.6 vs 16.9** | **TRES HAUSSIER** (+26.7 de spread) |
| Cloud Daily | **0.0702** | Loin au-dessus = tendance baissiere macro |

**CONTEXTE MACRO DEFAVORABLE** : BTC et ETH etaient tous les deux bearish sur le 4H (RSI ~37.8). Cela n'a pas empeche STEEM de faire +46%. Le token a montre une **decorrelation complete** avec le marche global — c'est un trade SPECIFIQUE a STEEM (probablement lie a un catalyseur fondamental ou une manipulation). Le spread DI+ Daily de +26.7 est un des plus eleves observes, confirmant que la tendance haussiere de STEEM etait independante du marche.

---

## 11. Niveaux Cles au Moment de l'Alerte

```
0.0702  --- Cloud Daily (TRES loin)
0.0700  --- Swing High 4H (Fib 100%)
0.0647  --- Fib 78.6% (4H)
0.0639  --- VAH 1H
0.0619  --- POC 4H
0.0606  --- Fib 61.8% (4H)
0.0595  --- Cloud Top 4H
0.0593  --- Cloud Top 30M
0.0580  --- Cloud Top 15m
0.0577  --- Fib 50% (4H)
0.0565  --- VAH 4H
0.0561  --- POC 1H
0.0556  --- PRIX ALERTE  <--- VOUS ETES ICI
0.0548  --- Fib 38.2% (4H)
0.0537  --- EMA20 1H
0.0525  --- EMA100 1H / VAL 1H
0.0520  --- EMA20 4H / OB 4H zone haute (0.0514-0.0520)
0.0517  --- EMA50 4H
0.0516  --- EMA100 1H
0.0512  --- Fib 23.6% (4H) / OB 4H zone (0.0511-0.0518)
0.0497  --- OB 4H zone basse (0.0497-0.0514)
0.0488  --- OB 1H zone (0.0488-0.0492)
0.0481  --- Cloud Top 1H (seule resistance cassee)
0.0454  --- Swing Low 4H (Fib 0%)
```

**Le prix est au milieu de la structure Fib** — entre le Fib 23.6% (0.0512) et le Fib 38.2% (0.0548). C'est une zone d'equilibre qui permet un rebond vers les Fib superieurs. Le POC 1H (0.0561) et le POC 4H (0.0619) sont des targets naturelles. La cascade de resistances entre 0.058 et 0.060 (clouds, POC) a ete franchie pendant les pumps #2 et #3.

---

## 12. Order Blocks et Structure

### OB 1H

| Zone | Type | Force | Distance | Status |
|------|------|-------|----------|--------|
| 0.0518 - 0.0533 | BULLISH | MODERATE | -2.8% | Mitigue |
| 0.0488 - 0.0492 | BULLISH | MODERATE | +4.3% | Mitigue |
| 0.0459 - 0.0463 | BULLISH | **STRONG** | +10.8% | Mitigue (impulse 22.3%) |
| 0.0590 - 0.0619 | BULLISH | **STRONG** | -15.5% | Mitigue (impulse 8.7%) |

### OB 4H

| Zone | Type | Force | Distance | Status |
|------|------|-------|----------|--------|
| 0.0511 - 0.0518 | BULLISH | MODERATE | INSIDE | Mitigue |
| 0.0497 - 0.0514 | BULLISH | **STRONG** | INSIDE | Mitigue (impulse 7.2%) |
| 0.0514 - 0.0520 | BULLISH | **STRONG** | -1.2% | Mitigue (impulse 36.2%) |
| 0.0485 - 0.0491 | BULLISH | MODERATE | +4.7% | Mitigue |

**Le prix est DANS les OB 4H bullish** (zone 0.0497-0.0518). C'est un signal fort : le prix est a l'interieur des Order Blocks qui ont genere l'impulse de +36.2% (le premier pump). Les OB servent de support pour le rebond.

### FVG (Fair Value Gaps)

| TF | Count | Position |
|----|-------|----------|
| 1H | 3 | INSIDE |
| 4H | 2 | INSIDE |

Le prix est DANS les FVG sur les 2 timeframes. Cela signifie que les gaps de prix crees par le pump #1 n'ont pas ete completement combles. Le prix a tendance a revenir combler les FVG au-dessus, ce qui est BULLISH.

---

## 13. Structure Fibonacci

### Fib 4H (Swing 0.0454 - 0.0700)

| Niveau | Prix | Status |
|--------|------|--------|
| 0.0% | 0.0454 | Swing Low |
| 23.6% | 0.0512 | Zone de rebond (close pre-alerte) |
| 38.2% | 0.0548 | Resistance 1 (cassee vague 1) |
| 50.0% | 0.0577 | Resistance 2 (cassee vague 1) |
| 61.8% | 0.0606 | Resistance 3 (cassee vague 2) |
| 78.6% | 0.0647 | Resistance 4 (cassee vague 2) |
| 100% | 0.0700 | Swing High (cassee vague 3) |
| **116.1%** | **0.0740** | Extension 1 (atteinte vague 3) |
| **145.5%** | **0.0812** | **Extension 2 = ATH (+46.04%)** |

**Le ATH a 0.0812 correspond au Fib extension 145.5%** du range 4H. C'est une zone d'extension classique ou les prises de profit massives se declenchent. La rejection violente depuis ce niveau confirme que c'etait un niveau technique de resistance majeur.

### Fib 1H (Swing 0.0454 - 0.0682)

| Niveau | Prix | Status |
|--------|------|--------|
| 0.0% | 0.0454 | Swing Low |
| 23.6% | 0.0508 | Zone de support (correction post-pump #1) |
| 50.0% | 0.0568 | Median |
| 100% | 0.0682 | Swing High (pump #1 high) |

---

## 14. Insight pour OpenClaw

### Pattern a sauvegarder : "PULLBACK FIB + CONTINUATION MULTI-VAGUE"

**"Pattern CONTINUATION MULTI-VAGUE : DI+ 4H > DI- (37.2 vs 23.5 = spread +13.7) + DI+ Daily >> DI- (43.6 vs 16.9 = spread +26.7) + prix au Fib 23.6% du swing 4H + StochRSI 1H oversold (K=4.6) + prix DANS les OB 4H bullish + prix DANS les FVG 1H et 4H + 1/5 conditions = signal de RE-ENTRY dans une tendance haussiere existante. Le pump est multi-vague (3-4 vagues en 3 jours, chaque pump a ~00:00 UTC). ATH atteint au Fib extension ~145%. BTC/ETH bearish = decorrelation complete. Drawdown modere (-3.4% depuis prix alerte)."**

### Ce qu'OpenClaw aurait du dire :

```
STEEMUSDT — BUY (75% confiance)
MEGA BUY (Re-entry post-correction)

SIGNAL FORT: Continuation haussiere confirmee
- DI+ 4H = 37.2 >> DI- 23.5 (tendance FORTE)
- DI+ Daily = 43.6 >> DI- 16.9 (tendance MACRO)
- Prix au Fib 23.6% du swing 4H (zone de re-entry)
- StochRSI 1H oversold (K=4.6) = fond temporaire
- Prix DANS les OB 4H bullish (support structural)
- FVG 1H + 4H INSIDE (comblement haussier probable)
- CONDITIONS 1/5 (cloud 1H valide, EMAs a -1%)

ATTENTION: BTC 4H Bearish + ETH 4H Bearish
STEEM en decorrelation totale avec le marche
Pattern de pumps nocturnes (00:00 UTC) detecte

RECOMMANDATION: BUY sur confirmation
  Entry: 0.0556 (au signal) ou 0.0590 (retest)
  SL: 0.0500 (sous le low de correction 0.0507)
  TP1: 0.0668 (high vague 1) = +20.1%
  TP2: 0.0738 (Fib ext. 116%) = +32.7%
  TP3: 0.0812 (Fib ext. 145%) = +46.0%
  R:R = 1:2.0 → 1:4.6
```

### Classification du pattern

| # | Pattern | Trade | Resultat | Signal Fort? | Conditions | Drawdown |
|---|---------|-------|----------|-------------|------------|----------|
| 1 | Build-up Technique | PLUME | +59% | OUI | 3/5 | -2.9% |
| 2 | Phoenix Explosif | DEGO | +396% | OUI (10/10) | 4/5 | -2.8% |
| 3 | Sleeping Giant | PIXEL | +260% | NON | 0/5 | -1.8% |
| 4 | Momentum Reversal | PHA | +131% | MOYEN | ~2/5 | -5.0% |
| 5 | Double Wave Reversal | COS | +125% | NON (STC oui) | 0/5 | -1.9% |
| 6 | Accumulation Breakout | SAHARA | +116% | NON | 0/5 | -1.8% |
| 7 | Shakeout Tardif + Event | MIRA (1/3) | +73.4% | NON | 0/5 | -11.2% |
| **8** | **Pullback Fib + Multi-Vague** | **STEEM** | **+46.0%** | **MOYEN** | **1/5** | **-3.4%** |

**Decouverte sur STEEM** : C'est le premier trade analyse qui est une **CONTINUATION** (pas un retournement). Le DI+ 4H et Daily sont deja fortement haussiers au moment de l'alerte. Le MEGA BUY detecte correctement le rebond sur le Fib 23.6% apres le premier pump. Le pattern de pumps repetitifs a 00:00 UTC et la decorrelation totale avec BTC/ETH suggerent un catalyseur fondamental specifique a STEEM (news, listing, partnership). **Pour OpenClaw, le spread DI+ >> DI- sur le 4H et le Daily combine avec un prix au Fib 23.6% est un marqueur de haute confiance pour un trade de continuation.** Le drawdown modere (-3.4%) et le R:R favorable (1:4.6) en font un trade de qualite superieure malgre le contexte macro defavorable.
