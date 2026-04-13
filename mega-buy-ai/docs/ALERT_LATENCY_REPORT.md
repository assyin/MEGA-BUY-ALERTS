# Rapport d'Analyse — Latence du Pipeline d'Alertes

**Date:** 12/04/2026  
**Problème:** 5+ minutes de délai entre la détection du signal et l'entrée en position  
**Impact:** Trades ratés, entrées à prix dégradé, pullbacks subis

---

## 1. Pipeline Actuel — Chemin Critique

```
T+0s      Scanner commence le scan (400+ paires × 4 TFs)
T+180s    Scanner termine, push vers Supabase (alert_timestamp posé ici)
T+195s    AlertListener poll (attend jusqu'à 15s le prochain cycle)
T+197s    Fetch des alertes + filtre (2s)
T+202s    Début agent analysis (GPT-4o-mini triage)
T+210s    Agent analysis terminée (3.5-7.5s)
T+220s    Feature computation + memory save (9-11s)
T+232s    Chart generation + Telegram (8-12s)
T+232s    Portfolio V1 gate check (13s)
T+245s    Portfolio V2 gate check (13s)
  ...     [9 portfolios en SERIE]
T+349s    Portfolio V9 gate check terminé

TOTAL: ~350 secondes = 5.8 minutes
```

---

## 2. Les 6 Goulots d'Étranglement

### #1 — Portfolios en série (117 secondes)
**Fichier:** `processor.py` lignes 343-469  
**Cause:** Les 9 portfolio managers (V1→V9) s'exécutent **séquentiellement**  
**Chaque portfolio:** ~13s (5 appels Binance API dans le gate + Supabase + Telegram)  
**Impact:** 9 × 13s = **117 secondes** — c'est 33% du temps total  

### #2 — Gate API calls redondants (45+ secondes)
**Fichier:** `gate_v6.py` lignes 35-100  
**Cause:** Chaque portfolio refait les **mêmes appels API** :
- `_fetch_4h_candle(pair)` → 2s × 9 = 18s (même résultat pour tous)
- `_fetch_1h_trend("BTCUSDT")` → 2s × 9 = 18s (identique pour tous)
- `_fetch_1h_trend("ETHUSDT")` → 2s × 9 = 18s (identique pour tous)
- `_fetch_24h_change(pair)` → 1s × 9 = 9s (identique)
- Volume spikes → 3s × 9 = 27s (identique)

**Total gaspillé:** ~90s dont ~80s de duplications

### #3 — Feature computation dupliquée (9-11 secondes)
**Fichier:** `processor.py` lignes 183-234  
**Cause:** Le processor calcule 24h change, 4H candle, volume spike **avant** les portfolios, mais les portfolios recalculent les mêmes données dans leur gate  
**Impact:** 9-11s de calcul redondant

### #4 — Délai entre alertes (35-40 secondes)
**Fichier:** `alert_listener.py` ligne 131  
**Cause:** `await asyncio.sleep(5)` entre chaque alerte dispatched  
**Impact:** Pour 8 alertes = 40s de sleep pur

### #5 — Chart + Realtime Analysis (8-12 secondes)
**Fichier:** `processor.py` lignes 271-327  
**Cause:** Chart generation est synchrone et bloque les portfolios  
**Impact:** 8-12s avant que les portfolios puissent s'exécuter

### #6 — Poll interval (15 secondes avg)
**Fichier:** `config.py` ligne 34  
**Cause:** `poll_interval_sec = 15` — check toutes les 15s  
**Impact:** En moyenne 7.5s de latence incompressible

---

## 3. Détail des Appels API par Alerte

| Étape | Appels API | Durée | Redondant? |
|---|---|---|---|
| Feature computation | 3× Binance (24h, 4H, 48×1h) | 7s | Oui avec gate |
| Agent analysis | 1× GPT-4o-mini + tool calls | 3-7s | Non |
| Chart generation | 1× realtime_analyze (local) | 3-5s | Non |
| Gate V6 (par portfolio) | 5× Binance (4H, BTC, ETH, 24h, vol) | 10s | Oui × 9 |
| Gate V8/V9 (extra) | 1× Binance (vol 48h) + 1× BTC + 1× 24h | 5s | Oui × 2 |
| Position insert | 1× Supabase + 1× Telegram | 3s | Non |

**Total API calls par alerte:** ~55 appels Binance + 10 Supabase + 5 Telegram  
**Dont redondants:** ~40 appels Binance (identiques entre portfolios)

---

## 4. Solutions Proposées

### Fix #1 — Paralléliser les Portfolios (Gain: 100+ secondes)

**Avant:**
```python
# processor.py lignes 343-469 — SEQUENTIEL
if self.portfolio and "BUY" in decision.decision:
    await self.portfolio.try_open_position(...)
if self.portfolio_v2 and "BUY" in decision.decision:
    await self.portfolio_v2.try_open_position(...)
# ... 9 fois en série
```

**Après:**
```python
# PARALLELE avec asyncio.gather
tasks = []
for pm in [self.portfolio, self.portfolio_v2, ..., self.portfolio_v9]:
    if pm and "BUY" in decision.decision:
        tasks.append(pm.try_open_position(...))
results = await asyncio.gather(*tasks, return_exceptions=True)
```

**Gain estimé:** 117s → ~15s = **-102 secondes**  
**Effort:** 30 minutes

---

### Fix #2 — Cache Gate Data (Gain: 45+ secondes)

**Concept:** Calculer les données gate UNE SEULE FOIS dans le processor, puis les passer aux portfolios.

```python
# processor.py — avant les appels portfolio
gate_cache = {
    "candle_4h": _fetch_4h_candle(pair),       # 1 appel au lieu de 9
    "btc_trend": _fetch_1h_trend("BTCUSDT"),   # 1 appel au lieu de 9
    "eth_trend": _fetch_1h_trend("ETHUSDT"),   # 1 appel au lieu de 9
    "change_24h": _fetch_24h_change(pair),     # 1 appel au lieu de 9
    "vol_spikes": _fetch_volume_spikes(pair),  # 1 appel au lieu de 9
}
# Passer gate_cache à chaque portfolio
await pm.try_open_position(..., gate_cache=gate_cache)
```

**Gain estimé:** 5 appels × 2s = 10s (au lieu de 45 appels × 2s = 90s) = **-80 secondes**  
**Effort:** 1 heure (modifier gate_v6.py + tous les managers)

---

### Fix #3 — Chart en Parallèle (Gain: 8-12 secondes)

**Avant:** Chart bloque tout → puis portfolios commencent  
**Après:** Lancer chart en background, lancer portfolios immédiatement

```python
# processor.py
chart_task = asyncio.create_task(self._generate_chart(...))
# Lancer portfolios en parallèle PENDANT le chart
await asyncio.gather(portfolio_tasks, chart_task)
```

**Gain estimé:** **-8 à -12 secondes**  
**Effort:** 20 minutes

---

### Fix #4 — Réduire le Dispatch Delay (Gain: 35 secondes)

**Avant:** `await asyncio.sleep(5)` entre chaque alerte  
**Après:** `await asyncio.sleep(1)` ou 0

```python
# alert_listener.py ligne 131
await asyncio.sleep(1)  # 1s au lieu de 5s
```

**Gain estimé:** (5-1) × 8 = **-32 secondes**  
**Effort:** 5 minutes

---

### Fix #5 — Réduire le Poll Interval (Gain: 7 secondes avg)

```python
# config.py
poll_interval_sec: int = 5  # au lieu de 15
```

**Gain estimé:** **-10 secondes** en moyenne  
**Effort:** 1 minute

---

## 5. Impact Projeté

| Métrique | Actuel | Après Fix #1-5 | Amélioration |
|---|---|---|---|
| Poll → Processing | 15s | 5s | -10s |
| Agent Analysis | 7s | 7s | 0 |
| Features + Memory | 11s | 11s | 0 |
| Chart | 10s (bloquant) | 0s (parallèle) | -10s |
| Portfolios | 117s (série) | 15s (parallèle) | -102s |
| Gate API calls | 90s (redondant) | 10s (cache) | -80s |
| Dispatch delay | 40s | 8s | -32s |
| **TOTAL** | **~290s** | **~56s** | **-234s (-81%)** |

**Résultat:** De **~5 minutes** à **~1 minute** entre la détection et l'entrée.

---

## 6. Priorité d'Implémentation

| Priorité | Fix | Gain | Effort | ROI |
|---|---|---|---|---|
| 🔴 P0 | Paralléliser portfolios | -102s | 30 min | ⭐⭐⭐ |
| 🔴 P0 | Cache gate data | -80s | 1h | ⭐⭐⭐ |
| 🟡 P1 | Dispatch delay 5s → 1s | -32s | 5 min | ⭐⭐⭐ |
| 🟡 P1 | Chart en parallèle | -10s | 20 min | ⭐⭐ |
| 🟢 P2 | Poll interval 15s → 5s | -10s | 1 min | ⭐⭐ |

**Total effort estimé:** ~2 heures pour un gain de 234 secondes (-81%)

---

## 7. Risques

- **Rate limiting Binance:** Si toutes les portfolios fetch en parallèle, on risque de dépasser 1200 req/min. Le cache résout ce problème.
- **Telegram flood:** 9 notifications simultanées. Utiliser un queue avec 500ms de délai.
- **Memory save timing:** Si les portfolios s'exécutent avant le memory save, les données STC ne seront pas encore dans features. → Extraire le STC avant les portfolios (déjà fait).

---

*Rapport généré le 12/04/2026 par Claude Code*
