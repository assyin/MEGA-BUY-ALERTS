# V11 Architecture — État du système au 2026-04-29

> Synthèse complète des 5 variants V11 (Discovery family), Phase 1 paper trading,
> Phase 2 killswitch, et critères go/no-go pour Phase 3 live.
>
> **Audience** : référence rapide pour reprendre le contexte sans relire tout
> l'historique. Mis à jour à chaque changement structurel.

---

## 1. Vue d'ensemble

Le système trade des paires Binance USDT en **paper-only** (aucun ordre réel) avec
5 stratégies parallèles V11 dérivées d'un script de discovery (analyse statistique
sur 700+ alertes historiques pour identifier les filtres les plus prédictifs).

```
ALERT scanner ──┬──► V11A Custom (continuation thesis)
                ├──► V11B Compression (R30m + R4h compression)
                ├──► V11C Premium (Range 1h + BTC.D)
                ├──► V11D Accumulation breakout
                └──► V11E BB Squeeze 4H

Chaque variant filtre indépendamment, prend une décision INDEPENDANTE,
maintient son propre balance ($5000 initial) et ses positions.
```

Les 5 ont la même mécanique d'**exit hybride** (issue de V7) :
- TP1 : ferme 50% à +10%, SL → BE
- TP2 : ferme 30% à +20% (V11B = +13%), trail 8% activé
- Trail : continue de monter le SL à -8% du peak
- SL initial : -8%
- Timeout : 72h max

Seul le **filtre d'entrée** diffère entre variants.

## 2. Les 5 variants V11

### V11A — Custom (continuation thesis)
- **Filtre** : `DI+ 37-50 + DI- ≤14 + ADX≥15 + RSI≤79 + 24h≤36% + Body 4H≥2.7% + STC pas oversold + PP+EC + 4H green + 15m TF + vol non-rouge`
- **Hypothèse** : capturer une continuation d'une tendance haussière établie
- **Stats** : N=17 trades, WR 70.6%, **fragile (proche seuil killswitch 70%)**
- **Status** : à surveiller — petit échantillon, peu d'opens (filtre très strict)

### V11B — Compression (top combo) ⭐
- **Filtre** : `Range 30m ≤ 1.89% ET Range 4h ≤ 2.58%`
- **Hypothèse** : compression de volatilité sur 2 timeframes = breakout imminent
- **Stats** : N=199 trades, **WR 85.9%**, +$5,689, max DD 1.97%, **TP2=13%** (overridé)
- **Status** : variant principal, lead pour Phase 3

### V11C — Premium (BTC dominance)
- **Filtre** : `Range 1h ≤ 1.67% + BTC.D ≤ 57`
- **Hypothèse** : compression 1h pendant un cycle altcoin (BTC.D décroit)
- **Stats** : N=49, **WR 91.8%** (top WR), mais peu sélectif (12+ jours sans trade en moyenne)
- **Status** : healthy, échantillon petit mais qualité élevée

### V11D — Accumulation Breakout
- **Filtre** : `Accumulation days ≥3.7 + Range 30m ≤ 1.46%`
- **Hypothèse** : phase d'accumulation longue + compression récente = signal explosif
- **Stats** : N=56, **WR 91.1%**
- **Status** : healthy

### V11E — BB Squeeze 4H
- **Filtre** : `Bollinger Band 4H width ≤ 13.56`
- **Hypothèse** : Bollinger squeeze sur 4H = explosion imminente
- **Stats** : N=104, WR 79.8%
- **Status** : healthy

### Filtre commun à tous (post-2026-04-28)
- **BTC dump hard stop** : si BTC 24h ≤ -5% → reject any open
- **BTC dump soft cap** : si BTC 24h ≤ -3% AND open ≥ 6 → reject (concentration guard)
- **Killswitch** : si WR(last 30) < 70% → suspend variant (manual resume)

## 3. Schéma de données

### Tables Supabase (par variant)
```
openclaw_positions_v11{a,b,c,d,e}
├─ id (uuid PK)
├─ pair, entry_price, exit_price, size_usd
├─ sl_price, tp1_price, tp2_price
├─ partial1_done, partial2_done, trail_active, trail_stop
├─ pnl_pct, pnl_usd, realized_pnl_usd, remaining_size_pct
├─ status ∈ {OPEN, CLOSED}, close_reason
├─ opened_at, closed_at
├─ alert_id (FK → alerts), decision, confidence, scanner_score
├─ is_vip, is_high_ticket, quality_grade
├─ gate_snapshot (JSONB)              ← Phase 0 : audit trail
├─ paper_entry_price (NUMERIC)        ← Phase 1 : prix Binance T+60s
├─ paper_slippage_pct (NUMERIC)       ← Phase 1
├─ paper_logged_at (TIMESTAMPTZ)      ← Phase 1
├─ paper_pnl_pct (NUMERIC)            ← Phase 1 : PnL recalculé au close
└─ paper_pnl_usd (NUMERIC)            ← Phase 1

openclaw_portfolio_state_v11{a,b,c,d,e}
├─ id ('main')
├─ balance, initial_capital, total_pnl, total_trades, wins, losses
├─ peak_balance, max_drawdown_pct, drawdown_mode, daily_loss_today
├─ is_suspended (BOOL)                ← Phase 2 : killswitch
├─ suspended_at (TIMESTAMPTZ)         ← Phase 2
└─ suspended_reason (TEXT)            ← Phase 2
```

## 4. Phase 1 — Paper trading instrumentation

**Objectif** : mesurer le delta entre P&L théorique (entrée au prix d'alerte, comme un backtest)
et P&L réaliste (entrée 60s après l'alerte, comme un trader en réaction).

### Mécanique
```
T=0    ALERT @ price P_alert
       ├─ filtre V11x passe ✅
       ├─ INSERT position {entry_price=P_alert, paper_entry_price=NULL}
       └─ asyncio.create_task(_log_paper_entry(pos_id, pair, P_alert))
                                                          │
                                                          ▼
T=60s  fetch Binance ticker price → P_paper
       ├─ slippage = (P_paper - P_alert) / P_alert * 100
       └─ UPDATE position SET paper_entry_price=P_paper,
                              paper_slippage_pct=slippage,
                              paper_logged_at=NOW()
       ...
T=close   _close_full() :
          ├─ pnl_pct (existant) — utilise entry_price (alert) + partials TP1/TP2
          ├─ paper_pnl_pct (nouveau) = (exit_price - paper_entry) / paper_entry × 100
          └─ paper_pnl_usd (nouveau) = size_usd × paper_pnl_pct / 100
```

### Critère go/no-go (avant Phase 3 live $)
- **Δ WR** = `WR_paper − WR_backtest`
- Min sample : N ≥ 50 trades paper
- Threshold : `|Δ WR| ≤ 8 pts` → ✅ PASS, scaling autorisé
  - Entre 8 et 10 pts → ⚠️ WATCH (investiguer)
  - > 10 pts → 🛑 FAIL (filtre overfit, ne pas live)

### Slippage cible
- Avg slip ≤ 0.3% → fenêtre +60s acceptable
- Avg slip > 0.5% systématique → réaction trop lente OU alertes en avance

### Visibilité
- Onglet `🧪 Phase 1` dans `/portfolio` (V11x only) — bandeau couverture + delta WR + 4 charts time-series
- Section dédiée dans les rapports `V11B_TRADE_AUDIT_*.{md,html}`

### Backfill
`scripts/backfill_paper_pnl.py` — pour les positions fermées avec `paper_entry_price` mais
`paper_pnl_pct` NULL (cas où le bot crashe entre le close et le compute).

## 5. Phase 2 — Killswitch automatique

**Objectif** : suspendre automatiquement un variant qui dérive en live, avant que les
pertes ne s'accumulent.

### Logique (par variant, indépendant)
```python
# Après chaque _close_full :
recent = last_30_closed
if len(recent) >= 30:
    wr = wins / 30
    if wr < 0.70:
        is_suspended = True
        suspended_at = NOW()
        suspended_reason = f"WR {wr*100:.1f}% < 70% on last 30 closes"
        send_telegram_alert()

# try_open_position : block immédiatement si suspended
```

### Reprise manuelle (pas auto-resume)
- Bouton **▶️ Reprendre les opens** dans le dashboard `/portfolio` quand un variant est suspended
- OU SQL : `UPDATE openclaw_portfolio_state_v11x SET is_suspended=false, suspended_at=null, suspended_reason=null WHERE id='main';`

### Pourquoi pas d'auto-resume
Si auto-resume sur WR ≥ 75% : impossible d'atteindre ce seuil quand on est suspended (pas de nouveaux trades). Ferait flapping.

## 6. Phase 3 — Live small $500 (à venir)

**Pré-requis** :
- ≥ 50 trades paper sur V11B
- |Δ WR backtest vs paper| ≤ 8 pts
- Slippage moyen ≤ 0.3%
- Aucune suspension active

**Implementation prévue** (pas encore codée) :
- Variable `LIVE_MODE=False` actuellement → `True` quand Phase 1 valide
- Hooks Binance API REST pour POST orders (avec auth API key)
- Size live = $500 par position (vs $400 en paper)
- 50 trades live → si performance maintenue → scale à $1000-2000

## 7. Monitoring

### Dashboard temps réel
- `http://172.17.112.163:3000/portfolio` (local WSL2)
- Onglets par variant : Overview, Details, Historique, Statistiques, **🧪 Phase 1** (V11x only)
- Bandeau rouge SUSPENDED si killswitch actif (avec bouton reprise)

### Digest 3×/jour (cron)
- 07:00, 14:00, 22:00 local time
- Telegram (HTML formaté) + Email (HTML détaillé)
- Window 8h glissante (couvre 24h sans gap)
- Voir `scripts/send_digest.py` + cron entries

### Rapports audit V11B
- `scripts/audit_v11b_trades.py` (markdown) + `audit_v11b_html.py` (HTML)
- À régénérer manuellement quand on veut un snapshot complet
- Sections : par-trade entry+exit, risk metrics, BTC bucket, paper P&L delta

## 8. Roadmap futur

| Item | Status | Bloquant |
|---|---|---|
| Phase 3 live small $500 | TODO | Paper data N≥50 + Δ WR ≤ 8 |
| Filtre WATCH (exclusion decision="WATCH") | DEFERRED | Besoin N≥50 sur WATCH décisions |
| V11A threshold optim (grid search) | DEFERRED | N=17 trop petit, risque overfit |
| Q-B Kelly position sizing | DEFERRED | DD actuel 1.97% pas critique |
| Q-E régime macro detection | OUT OF SCOPE | Trop complexe |

## 9. Fichiers clés

```
mega-buy-ai/
├─ openclaw/portfolio/
│  ├─ manager_v11.py          # Base class + 5 subclasses
│  └─ gates_v11.py            # 5 gate functions + BTC helpers
├─ scripts/
│  ├─ digest_report.py        # Digest generator (HTML + text)
│  ├─ send_digest.py          # Telegram + Email dispatcher
│  ├─ audit_v11b_trades.py    # Per-trade markdown audit
│  ├─ audit_v11b_html.py      # Per-trade HTML audit
│  ├─ _risk_metrics.py        # Sharpe/PF/Calmar + paper P&L renders
│  ├─ backfill_paper_pnl.py   # Retroactive paper PnL compute
│  ├─ hydrate_v11_portfolios.py  # Initial backfill V11 from history
│  └─ analyze_v11b_recos.py   # Walk-forward, peak distribution
└─ sql/
   ├─ portfolio_v11.sql       # CREATE TABLE positions + state
   ├─ v11_gate_snapshot.sql   # ADD gate_snapshot JSONB
   ├─ v11_paper_tracker.sql   # ADD paper_entry_price + slippage + logged_at
   ├─ v11_paper_pnl.sql       # ADD paper_pnl_pct + paper_pnl_usd
   └─ v11_killswitch.sql      # ADD is_suspended + suspended_at + reason

dashboard/src/app/portfolio/PortfolioPageClient.tsx
                              # /portfolio UI : Phase1MetricsTab + SuspendedBanner

V11B_TRADE_AUDIT_*.md / .html # Rapports audit régénérables
V11B_REVIEW_RECOS_*.md        # Analyse des 5 recos + 6 Q techniques
V11B_PRE_IMPL_CHECKS_*.md     # Vérifs Sharpe / TP2=13% / BTC layered
V11_DIGEST_*.html             # Archives digest 3×/jour
```

## 10. Dependencies / env

`python/.env` :
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` — DB access
- `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` — alerts + digest
- `SMTP_USER`, `SMTP_APP_PASSWORD`, `DIGEST_TO_EMAIL` — digest email (Gmail SMTP)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` — agent OpenClaw

PM2 services :
- `mega-scanner` — scan Binance pairs
- `mega-entry-agent` — Golden Box entry monitor (legacy)
- `mega-openclaw` — AI agent + V11 portfolios (port 8002)
- `mega-backtest` — backtest API (port 9001)
- `mega-simulation` — simulation API (port 8001)
- `mega-dashboard` — Next.js dev (port 3000)
