# Analyse INITUSDT - Mouvement +176% Non Capturé par V5

## Résumé Exécutif

**Problème identifié**: INITUSDT a réalisé un mouvement de +176% (de $0.0566 à $0.1562) entre le 6 et 16 février 2026. La stratégie V4 a capturé ce trade avec +78.73% de P&L, mais la stratégie V5 l'a rejeté.

**Cause**: Le filtre `V5_DEEP_BELOW_VAL` rejette les entrées trop loin sous le VAL (Value Area Low) du Volume Profile.

---

## 1. Données du Mouvement

| Métrique | Valeur |
|----------|--------|
| **Prix Début** | $0.0566 (6 février) |
| **Prix Max** | $0.1562 (16 février) |
| **Mouvement Total** | +176% |
| **Durée** | 10 jours |

---

## 2. Comparaison V4 vs V5

### Stratégie V4 (Trailing Stop)

| Champ | Valeur |
|-------|--------|
| **Entrée** | $0.0695 |
| **Sortie** | $0.1243 (Trailing SL) |
| **P&L** | +78.73% |
| **Durée** | ~7 jours |
| **Status** | ✅ TRADE VALIDÉ |

### Stratégie V5 (Volume Profile)

| Champ | Valeur |
|-------|--------|
| **Trades** | 0 |
| **Raison Rejet** | `V5_DEEP_BELOW_VAL` |
| **Status** | ❌ REJETÉ |

---

## 3. Analyse du Problème V5

### Le Filtre V5_DEEP_BELOW_VAL

Le filtre `V5_DEEP_BELOW_VAL` vérifie si le prix d'entrée est trop bas par rapport au VAL (Value Area Low) du Volume Profile 4H. Si le prix est significativement sous le VAL, le trade est rejeté.

**Logique du filtre**:
```python
if entry_price < VAL * (1 - V5_DEEP_BELOW_VAL_PCT):
    reject_reason = "V5_DEEP_BELOW_VAL"
```

### Pourquoi c'est problématique

1. **Zones de survente**: Quand un actif est en zone de survente (comme INIT), le prix est naturellement sous le VAL
2. **Meilleurs R/R**: Les entrées en zone de survente offrent souvent le meilleur ratio risque/récompense
3. **Récupérations**: Les mouvements de +100%+ viennent souvent de zones extrêmes de survente

---

## 4. Chronologie INITUSDT

```
6 Février:  $0.0566 - Point bas (zone de survente)
            ↓ MEGA BUY Signal détecté

7 Février:  V4 entre à $0.0695 (+22% depuis le bas)
            V5 rejette: "V5_DEEP_BELOW_VAL"

8-15 Fév:   Prix monte progressivement
            V4 trailing SL suit le mouvement

16 Février: $0.1562 - Pic (+176% depuis le bas)
            V4 sort à $0.1243 via trailing SL

Résultat:   V4 = +78.73%
            V5 = 0% (pas de trade)
```

---

## 5. Impact sur les Performances

### Trades Manqués par V5

Ce n'est pas un cas isolé. Le filtre `V5_DEEP_BELOW_VAL` rejette systématiquement les entrées en zone de survente, ce qui exclut:

- Les bottoms de marché
- Les récupérations après capitulation
- Les entrées à fort potentiel R/R

### Estimation des Pertes

Pour INITUSDT seul:
- V4: +78.73%
- V5: +0%
- **Différentiel**: 78.73 points de pourcentage manqués

---

## 6. Recommandations

### Option A: Désactiver le filtre V5_DEEP_BELOW_VAL

```python
V5_DEEP_BELOW_VAL_ENABLED = False
```

**Avantages**: Capture tous les trades comme V4
**Inconvénients**: Perd la protection VP contre les mauvaises entrées

### Option B: Assouplir le seuil

```python
V5_DEEP_BELOW_VAL_PCT = 0.15  # Au lieu de 0.05 (par exemple)
```

**Avantages**: Permet les entrées en zone de survente modérée
**Inconvénients**: Compromis entre protection et opportunités

### Option C: Condition contextuelle (Recommandé)

```python
# Ignorer le filtre si STC est en zone de survente
if stc_oversold and entry_price < VAL:
    # Permettre l'entrée même si deep below VAL
    # Car la zone de survente indique un potentiel de rebond
    pass
```

**Avantages**: Logique adaptative basée sur le contexte du marché
**Inconvénients**: Plus complexe à implémenter

---

## 7. Conclusion

La stratégie V5 avec Volume Profile ajoute de la valeur en filtrant les mauvaises entrées, mais le filtre `V5_DEEP_BELOW_VAL` est trop agressif. Il rejette des trades à fort potentiel en zone de survente.

**Action recommandée**: Implémenter l'Option C (condition contextuelle) pour permettre les entrées en zone de survente tout en maintenant la protection VP pour les autres cas.

---

## 8. Métriques Techniques INITUSDT

### Signal MEGA BUY (6 Février)

| Indicateur | 15m | 30m | 1h | 4h |
|------------|-----|-----|----|----|
| RSI Move | ✅ | ✅ | ✅ | - |
| DMI+ Move | ✅ | ✅ | ✅ | - |
| SuperTrend Flip | ✅ | ✅ | ✅ | - |
| Score | 8/10 | 7/10 | 8/10 | - |

### Conditions d'entrée V4 (7 Février)

| Condition | Status |
|-----------|--------|
| TL Break | ✅ |
| EMA100 1H | ✅ |
| EMA20 4H | ✅ |
| Cloud 1H | ✅ |
| Cloud 30M | ✅ |
| CHoCH/BOS | ✅ |

### Pourquoi V5 a rejeté

| Condition VP | Valeur | Status |
|--------------|--------|--------|
| VAL (4H) | ~$0.082 | - |
| Prix entrée | $0.0695 | - |
| Distance au VAL | -15% | ❌ REJETÉ |

---

*Rapport généré le 15 Mars 2026*
*Backtest Engine V5.1*
