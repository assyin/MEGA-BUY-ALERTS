# MIRAUSDT — Analyse Complete du Trade +80.51%

## Resultat : +80.51% | Max observe : +86.8% en 42h

---

## 1. Donnees de l'Alerte

| Champ | Valeur |
|-------|--------|
| **Paire** | MIRAUSDT |
| **Date** | 25/02/2026 00:17 UTC |
| **Prix pre-alerte** | 0.0803 (close bougie precedente 24/02 23:00) |
| **Prix bougie alerte** | O=0.0802 H=0.0853 L=0.0802 C=0.0843 |
| **Volume bougie alerte** | **4.1M** (explosion vs moyenne ~150K) |
| **Prix max post-alerte** | **0.1500** (+86.8%) le 26/02 19:00 (42h apres) |
| **Prix min post-alerte** | 0.0802 (low de la bougie alerte, drawdown ~0%) |
| **Resultat officiel** | **+80.51%** |
| **Drawdown max** | **~0%** (le prix n'est jamais retourne sous 0.0803 apres l'alerte) |

---

## 2. Indicateurs au Moment de l'Alerte

| Indicateur | 15m | 30m | 1h | 4h | Daily |
|------------|-----|-----|-----|-----|-------|
| **RSI** | 71.3 | 52.5 | 54.1 | 43.5 | 33.4 |
| **ADX** | 28.8 | 27.4 | 28.0 | 25.8 | 16.7 |
| **DI+** | 57.3 | 30.2 | 27.3 | 21.0 | 15.2 |
| **DI-** | 16.6 | 27.1 | 24.9 | 24.9 | 25.9 |
| **STC** | 0.92 | 0.09 | 0.02 | - | - |
| **EMA20** | 0.0809 | 0.0803 | 0.0799 | 0.0815 | - |
| **EMA100** | 0.0799 | 0.0803 | 0.0822 | 0.0902 | - |
| **Cloud Top** | 0.0799 | 0.0795 | 0.0821 | 0.0909 | 0.1541 |

### Points cles des indicateurs :
- **STC 1H = 0.02 (OVERSOLD PROFOND)** -- signal fort de retournement imminent
- **STC 30m = 0.09** -- quasi-oversold, confirmation multi-timeframe
- **RSI Daily = 33.4** -- proche de la zone oversold, phase d'accumulation
- **DI+ 15m = 57.3 vs DI- = 16.6** -- divergence massive sur le court terme, impulsion haussiere deja en cours
- **ADX 1H = 28.0** -- tendance forte en developpement

---

## 3. Conditions Progressives : 1/5

| Condition | Status | Valeur | Distance |
|-----------|--------|--------|----------|
| EMA100 1H | ECHOUEE | 0.0803 vs 0.0822 | **-2.4%** |
| EMA20 4H | ECHOUEE | 0.0803 vs 0.0815 | **-1.5%** |
| Cloud 1H | ECHOUEE | 0.0803 vs 0.0821 | **-2.1%** |
| Cloud 30M | **VALIDEE** | 0.0803 vs 0.0795 | **+1.0%** |
| CHoCH/BOS | ECHOUEE | Swing high non confirme | - |

**Seulement 1/5 conditions validees** -- signal technique faible en apparence. Cependant, la proximite de l'EMA100 1H (-2.4%) et de l'EMA20 4H (-1.5%) indique que le prix etait sur le point de reconquerir ces niveaux. La validation du Cloud 30M montre que le retournement commencait par les timeframes inferieurs.

---

## 4. Prerequisites et Bonus

### Prerequisites (signaux de timing)

| Prerequis | Status | Detail |
|-----------|--------|--------|
| **STC Oversold** | **VALIDE** | 30m=0.09, 1h=0.02 -- signal fort de retournement |
| **Trendline** | **VALIDE** | Trendline descendante 30m (P1=0.0962 le 15/02, P2=0.0811 le 24/02, slope=descending) |

Les deux prerequisites valides = **excellent timing de detection**. Le prix touchait une trendline descendante de 10 jours au moment exact de l'alerte, avec le STC en zone oversold profonde.

### Bonus Filters (7/23 valides)

| Filtre | Status | Detail |
|--------|--------|--------|
| Fib 4H | **BONUS** | Prix entre Fib 0.0 (0.0766) et 0.236 (0.0819) -- zone d'accumulation basse |
| Fib 1H | **BONUS** | Prix au niveau 0.5 (0.0799) du swing 1H |
| FVG 1H | **BONUS** | 6 Fair Value Gaps, position INSIDE |
| FVG 4H | **BONUS** | 2 FVGs, position ABOVE |
| ADX 1H | **BONUS** | ADX=28.0, DI+=27.3 > DI-=24.9, force STRONG |
| ADX 4H | **BONUS** | ADX=25.8, force STRONG |
| MACD 4H | **BONUS** | Histogram croissant (+0.000255), tendance BULLISH |
| BTC Corr | Neutre/Bearish | BTC 1H neutre (RSI 48.0), 4H bearish (RSI 37.8) |
| Volume | Normal | Ratio 0.44 (1H), pas de spike pre-alerte |
| StochRSI 4H | Overbought | K=90.4 avec cross bullish -- momentum deja lance |

---

## 5. Volume Profile

### 1H Volume Profile
| Niveau | Prix | Position |
|--------|------|----------|
| **POC** (Point of Control) | 0.0807 | Prix juste sous le POC |
| **VAH** (Value Area High) | 0.0827 | Resistance a reconquerir |
| **VAL** (Value Area Low) | 0.0770 | Support solide |
| **Position** | IN_VA | Prix dans la zone de valeur |
| **HVN** (High Volume Node) | 0.0802 | Concentration de volume au prix de l'alerte |

### 4H Volume Profile
| Niveau | Prix | Position |
|--------|------|----------|
| **POC** | 0.0877 | Resistance majeure a franchir |
| **VAH** | 0.0926 | Target apres breakout |
| **VAL** | 0.0773 | Support de la zone de valeur |
| **Position** | IN_VA | Prix dans la zone de valeur |
| **HVN** | 0.0795-0.0813 | Cluster de volume = zone de demande |

Le prix au moment de l'alerte etait dans la **zone de valeur** sur les deux timeframes, et exactement sur un High Volume Node (0.0802) = zone de forte activite d'echange = support dynamique.

---

## 6. Contexte Macro (30 jours avant)

| Parametre | Valeur |
|-----------|--------|
| ATH 30j | **0.1358** (28/01) |
| Low 30j | **0.0755** (06/02) |
| Chute depuis ATH | **-40.9%** |
| RSI Daily | **33.4** (proche oversold) |
| Position vs Low 30j | A 6.4% au-dessus du low 30j |

### Chronologie pre-alerte :
```
27/01 : Prix a 0.1284, range 0.1208-0.1321
28/01 : ATH 30j a 0.1358 puis debut de correction
29/01 : Cassure baissiere 0.1305 -> 0.1155 (-11.5%)
31/01 : Acceleration : 0.1186 -> 0.0946 (-20%)
01/02 : Tentative de rebond a 0.1157, echoue (C=0.1005)
05/02 : Flash crash 0.1009 -> 0.0826 (-18%)
06/02 : LOW 30j = 0.0755 (capitulation)
07-14/02 : Phase de recovery 0.0856-0.0965
15-18/02 : Retour vers 0.0992 (double top local)
19-24/02 : Nouvelle jambe baissiere 0.0896 -> 0.0766
24/02 07:00 : Low local = 0.0766 (test du low 30j)
24/02 14:00-16:00 : Rebond 0.0776 -> 0.0811 (premier signe de vie)
25/02 00:17 : >>> ALERTE MEGA BUY <<<
```

**Pattern : Double fond** entre le low du 06/02 (0.0755) et le low du 24/02 (0.0766). Le 2eme fond est LEGEREMENT au-dessus du 1er (+1.5%) = divergence haussiere subtile. La remontee de 0.0766 a 0.0803 avant l'alerte confirme la pression acheteuse naissante.

---

## 7. Progression Post-Alerte : Anatomie du Pump en 2 Vagues

### Bougie de l'alerte : BREAKOUT IMMEDIAT
```
25/02 00:00 : O=0.0802 H=0.0853 L=0.0802 C=0.0843
Volume = 4.1M (vs moyenne ~150K = x27!)
= PUMP de +5.1% sur la bougie depuis le close precedent
```

### Vague 1 : Breakout et consolidation (25/02, J+0)
```
00:00 -> H=0.0853, C=0.0843  | Vol=4.1M   | +5.0% depuis open
01:00 -> H=0.0861, C=0.0858  | Vol=1.2M   | Continuation
02:00 -> H=0.0875, C=0.0863  | Vol=1.5M   | Extension
03:00 -> H=0.0879, C=0.0853  | Vol=1.4M   | Premier rejet
05:00 -> H=0.0878, C=0.0870  | Vol=0.7M   | Stabilisation
09:00 -> H=0.0883, C=0.0882  | Vol=0.6M   | Pic local
10:00 -> H=0.0899, C=0.0862  | Vol=1.8M   | Rejet a 0.0899 = HIGH J+0
= MAX VAGUE 1 : +12.0% depuis alert (0.0899)
```

### Phase de consolidation (25/02 10:00 - 26/02 17:00)
```
25/02 10:00 - 26/02 08:00 : Range 0.0844-0.0899
Volume moyen : ~300-500K par heure
Pas de panique, pas de retrace sous 0.0838
= ACCUMULATION pendant 32 heures
```

### Vague 2 : MEGA PUMP (26/02 18:00-19:00)
```
26/02 08:00 : Premier breakout 0.0861 -> 0.0886 | Vol=1.7M
26/02 10:00 : Extension H=0.0901 | Vol=1.3M | Nouveau plus haut
26/02 12:00 : H=0.0907, C=0.0892 | Vol=1.4M
26/02 18:00 : EXPLOSION 0.0882 -> H=0.1357, C=0.1281 | Vol=25.0M (!!!)
             -> +59.0% EN 1 HEURE depuis l'open de la bougie
             -> +69.0% depuis le prix de l'alerte
26/02 19:00 : H=0.1500 (ATH) C=0.1195 | Vol=39.7M (!!!)
             -> +86.8% depuis l'alerte = MAXIMUM ABSOLU
```

### Correction rapide et phase volatile (26/02 20:00 - 04/03)
```
26/02 20:00 : Retrace H=0.1194 L=0.1074 C=0.1117 | Vol=16.6M
26/02 22:00 : L=0.1046 | -30% depuis ATH (correction violente)
27/02 02:00 : Rebond H=0.1200 | Vol=12.4M (2eme tentative)
27/02 03:00 : H=0.1277 | Vol=16.5M | 2eme pic local
27/02 07:00 : Retrace L=0.1006 | Vol=10.8M
27/02 11:00 : Cassure H=0.1044, L=0.0971 C=0.0989 | Chute
27/02 16:00 : L=0.0929 | -38% depuis ATH
01/03 13:00 : Flash spike H=0.1100 | Vol=15.6M (dernier sursaut)
03/03 09:00 : L=0.0873 | Retour sous le POC 4H
04/03 : Stabilisation autour de 0.089
```

---

## 8. Fibonacci et Zones Cles

### Niveaux Fibonacci 4H (Swing 0.0766 - 0.0992)

| Niveau | Prix | Signification |
|--------|------|---------------|
| 0.0 | 0.0766 | Low (support = low 24/02) |
| **0.236** | **0.0819** | Resistance 1 (franchie sur la bougie alerte) |
| **0.382** | **0.0852** | Resistance 2 (franchie lors du breakout) |
| 0.5 | 0.0879 | Resistance 3 |
| 0.618 | 0.0906 | Target pre-pump |
| 0.786 | 0.0944 | - |
| 1.0 | 0.0992 | Swing high (ATH locale 18/02) |

Le prix au moment de l'alerte (0.0803) etait entre les niveaux 0.0 et 0.236 du swing 4H = **zone basse de retracement**. Le pump a traverse TOUS les niveaux Fibonacci en 42h, depassant meme le swing high de +51%.

### Niveaux Fibonacci 1H (Swing 0.0766 - 0.0832)

| Niveau | Prix | Signification |
|--------|------|---------------|
| 0.0 | 0.0766 | Low |
| 0.5 | 0.0799 | **~ prix de l'alerte (0.0803)** |
| 1.0 | 0.0832 | Swing high 1H |

Le prix etait au **milieu exact** (Fib 0.5) du swing 1H = point d'equilibre, position ideale pour un mouvement directionnel.

### Order Blocks 4H

| Zone | Type | Force | Position |
|------|------|-------|----------|
| 0.0767-0.0783 | BULLISH | STRONG | Support (age=4 bars, impulse +7.4%) |
| 0.0809-0.0860 | BULLISH | STRONG | Au-dessus (prix a reconquerir) |
| 0.0825-0.0857 | BULLISH | STRONG | Au-dessus (zone de confluence) |

Le prix etait **juste au-dessus** de l'Order Block STRONG 4H (0.0767-0.0783) = rebond depuis une zone de demande institutionnelle recente (seulement 4 bougies 4H d'age). L'impulse de +7.4% depuis cet OB confirme la force de la zone.

---

## 9. Meilleure Entree

### Entree 1 : Au Signal (0.0803) -- AGRESSIVE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0803** (prix pre-alerte) |
| SL | **0.0755** (sous le low 30j) = -6.0% |
| TP1 | **0.0992** (swing high 4H) = +23.5% |
| TP2 | **0.1200** = +49.4% |
| TP3 | **0.1449** = +80.5% (~resultat officiel) |
| Drawdown max | **~0%** (le low post-alerte est 0.0802) |
| R:R sur TP3 | **13.4:1** |

### Entree 2 : Au Breakout du Fib 0.382 (0.0853) -- CONFIRMEE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0853** (breakout confirme le 25/02 00:00 sur la bougie alerte) |
| SL | **0.0800** = -6.2% |
| TP1 | **0.0992** = +16.3% |
| TP2 | **0.1200** = +40.7% |
| TP3 | **0.1500** = +75.9% |
| Drawdown | -1.8% (min post = 0.0838 le 28/02 12:00) |

### Entree 3 : Au Breakout du Swing High 4H (0.0992) -- CONSERVATIVE

| Parametre | Valeur |
|-----------|--------|
| Entry | **0.0992** (zone atteinte brievement le 26/02 apres-midi) |
| SL | **0.0920** = -7.3% |
| TP1 | **0.1200** = +21.0% |
| TP2 | **0.1500** = +51.2% |
| Drawdown | Variable (prix tres volatile dans cette zone) |

**Recommandation : L'entree au signal (0.0803) est la meilleure** avec un drawdown quasi-nul et un R:R exceptionnel de 13.4:1. Le fait que le prix n'ait JAMAIS retrace sous le prix de l'alerte rend cette entree optimale.

---

## 10. Score de Qualite

| Facteur | Score | Detail |
|---------|-------|--------|
| Conditions progressives | **2/10** | 1/5 validee, proches mais insuffisantes |
| STC Oversold | **9/10** | 1H=0.02 + 30m=0.09 = signal fort |
| Trendline | **8/10** | Contact trendline descendante 10 jours (15/02-24/02) |
| Fibonacci | **7/10** | Entre Fib 0.0 et 0.236 4H, au Fib 0.5 1H |
| Order Block | **8/10** | Juste au-dessus OB 4H STRONG recent (4 bougies) |
| Volume alerte | **9/10** | 4.1M = x27 la moyenne (~150K) |
| RSI Daily | **6/10** | 33.4 = proche oversold mais pas extreme |
| MACD 4H | **7/10** | Histogram croissant, divergence haussiere naissante |
| BTC Context | **3/10** | BTC neutre 1H, bearish 4H (RSI 37.8) |
| Drawdown | **10/10** | ~0% de drawdown = entree parfaite |
| **Score global** | **6.9/10** | **Signal technique MOYEN mais execution PARFAITE** |

---

## 11. Le Pump du 26/02 : Evenement Exogene Probable

Le mouvement de +69% en 2 bougies (26/02 18:00-19:00) n'est pas un mouvement purement technique. Les indices :

1. **Volume 26/02 18:00 : 25.0M** -- multiplication par x167 vs la moyenne horaire (~150K)
2. **Volume 26/02 19:00 : 39.7M** -- continuation avec un volume encore plus eleve
3. **Volume daily 26/02 : 115.5M** -- le jour le plus actif de tout l'historique visible
4. **Mouvement de 0.0882 a 0.1500 en 2h** -- trop rapide pour etre organique

### Hypotheses :
- **Annonce projet / listing** -- MIRA est un token gaming/metaverse, potentielle annonce de partenariat
- **Pump coordonne** -- le volume pre-pump (26/02 08:00-17:00) montre une accumulation progressive
- **Short squeeze** -- le prix etait a -40% du ATH 30j, beaucoup de positions short potentielles

### Ce que le MEGA BUY a detecte 18h AVANT le pump :
L'alerte du 25/02 00:17 a identifie le retournement **avant** le mega pump du 26/02 18:00. Cela donne une fenetre de 18h pour se positionner a 0.0803, soit 71% en dessous du pic a 0.1500.

---

## 12. Anatomie du Pump : Pourquoi +80.51% (et pas +86.8%)

Le prix maximum observe est 0.1500 (+86.8%), mais le resultat officiel est +80.51%. Explications possibles :

1. **TP fixe** : un target a 0.1449 (=0.0803 x 1.8051) correspond au prix atteint le 26/02 18:00 (H=0.1357, bougie suivante H=0.1500) -- le TP a probablement ete touche pendant la bougie explosive
2. **Trailing stop** : un trailing de 5-7% applique apres le pic a 0.1500 aurait donne un exit vers 0.1400-0.1425
3. **Exit partiel** : la volatilite extreme (0.1131-0.1500 sur la bougie de 19:00) peut declencher des exits anticipes

**+80.51% reste un resultat exceptionnel**, surtout avec un drawdown quasi-nul depuis l'entree.

---

## 13. Pattern : "DOUBLE FOND + STC ZERO + TRENDLINE CONTACT"

```
Phase 1 : Correction prolongee depuis ATH (28/01 -> 24/02) = -43.6% en 27 jours
Phase 2 : Double fond : 0.0755 (06/02) et 0.0766 (24/02) = 2eme fond plus haut
Phase 3 : Contact trendline descendante 10j + STC 1H = 0.02
Phase 4 : MEGA BUY detecte le retournement le 25/02 00:17
Phase 5 : Breakout immediat sur la bougie alerte (O=0.0802 -> H=0.0853, Vol x27)
Phase 6 : Consolidation 32h (0.0838-0.0899) = accumulation
Phase 7 : MEGA PUMP exogene 26/02 18:00 (+69% en 2h, Vol x167)
Phase 8 : Correction volatile puis stabilisation autour de 0.088
```

### Ce qui rend ce trade UNIQUE :
- **Drawdown zero** : le prix n'est JAMAIS retourne sous le prix de l'alerte (0.0803). C'est le trade avec le meilleur drawdown de tous les trades analyses.
- **Timing 18h avant le pump** : l'alerte a detecte le retournement technique bien avant l'evenement exogene qui a provoque l'explosion
- **Double fond classique** : pattern chartiste pur (0.0755 puis 0.0766) avec divergence haussiere
- **Pump en 2 heures** : contrairement aux autres trades qui mettent 5-7 jours, le gros du mouvement s'est fait en 2 bougies horaires

---

## 14. Insight pour OpenClaw

**"Pattern DOUBLE FOND + STC ZERO + TRENDLINE CONTACT : Quand le prix forme un double fond (2eme fond legerement au-dessus du 1er), touche simultanement une trendline descendante multi-jours, avec STC 1H < 0.05 et RSI Daily < 35, le MEGA BUY detecte un point de retournement avec un timing exceptionnel. Le drawdown quasi-nul (0%) et l'explosion du volume des la bougie alerte (x27) confirment immediatement la validite. Ce pattern peut generer des mouvements de +80% a +87% avec une execution optimale. Le pump final peut etre amplifie par un evenement exogene, mais la position est deja profitable avant."**

### Regle a implementer :
```
SI trendline_valid = true
ET stc_1h < 0.05
ET stc_30m < 0.15
ET double_fond_detect = true (low_recent > low_precedent, delta < 5%)
ET rsi_daily < 35
ET ob_4h_recent = STRONG (age < 10 bars)
-> SCORE += 3 points
-> FLAG = "DOUBLE FOND + TRENDLINE"
-> CONFIANCE_DRAWDOWN = "TRES_FAIBLE"
```

---

## 15. Comparaison Globale des Trades Analyses

| Facteur | PLUME (+59%) | DEGO (+396%) | PIXEL (+260%) | SAHARA 1 (+84%) | **MIRA (+80.51%)** |
|---------|-------------|-------------|---------------|-----------------|---------------------|
| Conditions | 3/5 | 4/5 | 0/5 | 1/5 | **1/5** |
| STC | 0.01 | 0.00 (triple) | 0.23-0.52 | 0.00 (1H) | **0.02 (1H)** |
| Vol alerte | 2.6x | 60x | 1x | 66x | **27x** |
| BTC | Bullish | Bearish | Bullish | Neutre | **Neutre/Bearish** |
| Driver | Technique | Institutionnel | Evenement | Trendline+Fib | **Double Fond + Exogene** |
| Timing pump | Immediat | Immediat | 12h delai | Immediat | **18h delai** |
| Drawdown | -2.9% | -2.8% | -1.8% | -1.6% | **~0%** |
| Pattern | Build-up | Phoenix | Sleeping Giant | Trendline Bounce | **Double Fond** |
| Score | 8/10 | 10/10 | 5.5/10 | 7.1/10 | **6.9/10** |

### 6 types de trades gagnants identifies :
1. **Build-up technique** (PLUME) : conditions fortes, accumulation, breakout previsible
2. **Phoenix explosif** (DEGO) : capitulation extreme, STC triple zero, volume record
3. **Sleeping Giant** (PIXEL) : signal faible mais accumulation extreme + evenement exogene
4. **Trendline Bounce** (SAHARA 1) : confluence trendline + Fibonacci + OB + STC zero
5. **Compound** (SAHARA 2) : 2eme alerte consecutive = confirmation et pyramidage
6. **Double Fond** (MIRA) : double fond chartiste + STC zero + trendline + pump exogene amplifiant le mouvement. Se distingue par un drawdown quasi-nul et un timing 18h avant le pump principal.
