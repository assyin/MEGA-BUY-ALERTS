# 🔬 V4 Portfolio Deep Dive

_Generated: 2026-04-26 14:09 UTC_

**Strategy V4**: Gate Score≥8 + VIP/HT + Green4H | Champion portfolio (highest WR + highest realized PnL).

Goal of this report: identify why losses happen, measure profit left on the table on winners, and propose concrete filter/exit changes.

## 📊 Summary

- **Closed trades**: 69 (43 wins, 26 losses, WR 62.3%)
- **Avg win**: +11.66% | **Avg loss**: -6.62%
- **Total realized**: wins $578.93 / losses $-201.88 → net **$377.05**
- **Avg hold time**: wins 78.8h / losses 92.6h
- **Expectancy per trade**: +4.77%

### 💸 Profit left on the table (winners only)

- Comparing **realized PnL%** vs **pnl_max** (peak the price hit during the watch window):
- Avg missed upside: **+7.54%** (median +0.66%)
- Trades where ≥5% was left on the table: **14 / 43**

Top 5 trades where TP exited too early:

- `MOVRUSDT` realized +15.83% but peak was **+52.29%** → missed **+36.46%** (TP_HIT)
- `PLUMEUSDT` realized +10.09% but peak was **+45.62%** → missed **+35.53%** (TP_HIT)
- `PLUMEUSDT` realized +10.50% but peak was **+45.62%** → missed **+35.12%** (TP_HIT)
- `LUMIAUSDT` realized +10.11% but peak was **+41.95%** → missed **+31.84%** (TP_HIT)
- `MUBARAKUSDT` realized +10.14% but peak was **+39.16%** → missed **+29.02%** (TP_HIT)

> **Implication**: V4's fixed-TP exit might be leaving a chunk of the move uncaptured. Consider a hybrid model (V7-style: TP1 partial @ +10%, TP2 partial @ +20%, trail the remainder).

## 🚨 Loss Pattern Analysis

**26 losing trades** — what they have in common:

**Close reasons (losses):**
- `SL_HIT`: 17 (65%)
- `EXPIRED`: 9 (35%)

**BTC trend at entry (losses):**
- `BEARISH`: 13 (50%)
- `BULLISH`: 10 (38%)
- `NEUTRAL`: 2 (8%)
- `BULLISH_OK`: 1 (4%)

**Quality grade distribution (losses):**
- Grade `C`: 12 (46%)
- Grade `A`: 6 (23%)
- Grade `B`: 6 (23%)
- Grade `A+`: 1 (4%)
- Grade ``: 1 (4%)

**Avg indicator at entry — Wins vs Losses:**

| Feature | Avg WIN | Avg LOSS | Δ |
|---|---:|---:|---:|
| Scanner score | 8.72 | 8.73 | -0.01 |
| Confidence | 0.71 | 0.71 | -0.00 |
| DI+ (4h) | 37.55 | 38.50 | -0.95 |
| DI- (4h) | 14.84 | 13.97 | +0.87 |
| ADX (4h) | 27.91 | 26.77 | +1.14 |
| RSI | 64.64 | 66.42 | -1.78 |
| Body 4h % | 1.74 | 4.28 | -2.54 |
| 24h change % | 2.43 | 4.26 | -1.83 |
| Vol spike vs 4h | 117.81 | 186.22 | -68.41 |
| Fear & Greed | 20.65 | 19.12 | +1.54 |
| Hold hours | 78.81 | 92.64 | -13.82 |

**Top losing pairs (recurrent losers):**
- `FIOUSDT`: 2 losses
- `NIGHTUSDT`: 2 losses
- `DUSDT`: 2 losses

**Top 5 worst losses (deep dive):**

- `C98USDT` -10.60% | score 9/10 | conf 70% | grade C | BTC BULLISH | 24h +3.45% | DI±54/9 | hold 5.8h → `SL_HIT`
- `DUSDT` -9.49% | score 8/10 | conf 30% | grade  | BTC BEARISH | 24h +10.60% | DI±32/7 | hold 78.9h → `SL_HIT`
- `STGUSDT` -9.04% | score 9/10 | conf 70% | grade B | BTC BULLISH | 24h +7.21% | DI±40/11 | hold 159.7h → `SL_HIT`
- `RESOLVUSDT` -9.00% | score 9/10 | conf 70% | grade C | BTC BULLISH | 24h +1.82% | DI±32/29 | hold 64.2h → `SL_HIT`
- `FIOUSDT` -8.64% | score 8/10 | conf 60% | grade B | BTC NEUTRAL | 24h +0.44% | DI±33/14 | hold 22.4h → `SL_HIT`

## 📋 Every Closed Trade

Sorted by date (newest first). `Δmax` = peak after entry vs realized close.

| # | Date | Pair | PnL% | PnL$ | Score | Conf | Grade | BTC | DI± | ADX | 24h% | Hold | Close | Δmax |
|---|---|---|---:|---:|---:|---:|---|---|---|---:|---:|---:|---|---:|
| 1 | 04-26 13:03 | `NEARUSDT` | ✅ +2.35% | $3.03 | 9 | 60% | C | BEARISH | 33/16 | 23 | -1.81% | 168h | EXPIRED | — |
| 2 | 04-26 12:52 | `BICOUSDT` | ✅ +10.27% | $12.02 | 9 | 80% | A | NEUTRAL | 32/16 | 19 | +5.22% | 69h | TP_HIT | — |
| 3 | 04-25 20:29 | `AXLUSDT` | ❌ -8.09% | $-9.90 | 8 | 80% | A | BEARISH | 33/14 | 14 | — | 58h | SL_HIT | +9.6% |
| 4 | 04-25 14:03 | `NIGHTUSDT` | ❌ -4.28% | $-5.14 | 9 | 83% | A | BEARISH | 34/19 | 19 | +0.82% | 168h | EXPIRED | +5.9% |
| 5 | 04-24 14:42 | `APEUSDT` | ✅ +10.55% | $13.06 | 9 | 65% | B | BEARISH | 56/10 | 38 | +2.61% | 145h | TP_HIT | — |
| 6 | 04-24 11:55 | `ZKPUSDT` | ✅ +14.48% | $16.53 | 9 | 95% | A | BEARISH | 42/14 | 17 | +13.15% | 1h | TP_HIT | — |
| 7 | 04-24 01:48 | `KAITOUSDT` | ✅ +10.10% | $11.13 | 8 | 55% | B | BEARISH | 34/15 | 28 | -0.15% | 9h | TP_HIT | +0.9% |
| 8 | 04-23 21:38 | `ZBTUSDT` | ✅ +10.84% | $12.03 | 8 | 65% | C | BULLISH | 32/18 | 29 | -5.57% | 38h | TP_HIT | +0.4% |
| 9 | 04-23 15:58 | `IOUSDT` | ✅ +4.79% | $5.69 | 8 | 70% | A | NEUTRAL | 35/18 | 37 | +13.55% | 168h | EXPIRED | +3.0% |
| 10 | 04-23 15:27 | `FLOKIUSDT` | ✅ +10.36% | $13.79 | 9 | 60% | C | ? | 43/14 | 25 | — | 99h | TP_HIT | — |
| 11 | 04-23 13:28 | `MOVRUSDT` | ✅ +15.83% | $17.68 | 9 | 65% | B | BEARISH | 34/7 | 39 | +4.62% | 1h | TP_HIT | +36.5% |
| 12 | 04-23 07:57 | `BIOUSDT` | ✅ +10.96% | $11.83 | 9 | 65% | B | BULLISH | 29/12 | 34 | +9.26% | 43h | TP_HIT | — |
| 13 | 04-23 07:52 | `DUSDT` | ❌ -9.49% | $-11.83 | 8 | 30% |  | BEARISH | 32/7 | 43 | +10.60% | 79h | SL_HIT | +61.0% |
| 14 | 04-23 07:52 | `XTZUSDT` | ✅ +4.01% | $4.73 | 8 | 60% | C | BULLISH | 43/15 | 16 | +3.70% | 178h | EXPIRED | +4.6% |
| 15 | 04-23 07:52 | `ADAUSDT` | ✅ +0.32% | $0.41 | 10 | 75% |  | BULLISH | 45/13 | 21 | +3.53% | 189h | EXPIRED | +8.0% |
| 16 | 04-22 07:55 | `PENGUUSDT` | ✅ +11.37% | $14.23 | 9 | 75% |  | BEARISH | 33/16 | 29 | -1.59% | 67h | TP_HIT | — |
| 17 | 04-21 17:29 | `AUDIOUSDT` | ❌ -8.09% | $-9.49 | 8 | 95% | A+ | BEARISH | 40/14 | 21 | +18.31% | 34h | SL_HIT | +9.9% |
| 18 | 04-21 17:18 | `NEIROUSDT` | ❌ -8.31% | $-10.32 | 8 | 55% | B | BEARISH | 41/19 | 37 | -14.94% | 68h | SL_HIT | +16.9% |
| 19 | 04-21 16:29 | `DUSDT` | ❌ -8.09% | $-8.66 | 8 | 86% | A | BEARISH | 36/12 | 23 | +11.09% | 30h | SL_HIT | +52.6% |
| 20 | 04-21 12:55 | `NEWTUSDT` | ✅ +22.27% | $25.33 | 9 | 65% | B | BEARISH | 30/15 | 37 | +3.44% | 29h | TP_HIT | +0.7% |
| 21 | 04-19 18:42 | `MANTRAUSDT` | ❌ -3.89% | $-4.32 | 9 | 70% | C | BEARISH | 42/17 | 35 | +4.05% | 169h | EXPIRED | +11.0% |
| 22 | 04-19 12:08 | `FIOUSDT` | ❌ -8.64% | $-11.02 | 8 | 60% | B | NEUTRAL | 33/14 | 27 | +0.44% | 22h | SL_HIT | +9.1% |
| 23 | 04-19 07:18 | `ALLOUSDT` | ❌ -8.53% | $-10.12 | 8 | 55% | C | BULLISH_OK | 37/23 | 34 | +3.28% | 66h | SL_HIT | +25.4% |
| 24 | 04-19 06:01 | `HEMIUSDT` | ❌ -8.25% | $-8.81 | 9 | 65% | C | BULLISH | 47/9 | 40 | +16.57% | 108h | SL_HIT | +35.9% |
| 25 | 04-19 02:52 | `STGUSDT` | ❌ -9.04% | $-9.35 | 9 | 70% | B | BULLISH | 40/11 | 30 | +7.21% | 160h | SL_HIT | +14.9% |
| 26 | 04-18 16:51 | `TREEUSDT` | ✅ +10.08% | $12.64 | 8 | 77% | A | BULLISH | 49/6 | 61 | -0.74% | 67h | TP_HIT | +19.2% |
| 27 | 04-18 15:33 | `FIOUSDT` | ❌ -8.30% | $-10.92 | 8 | 60% | B | NEUTRAL | 33/14 | 27 | +0.44% | 3h | SL_HIT | +8.7% |
| 28 | 04-18 12:02 | `PORTALUSDT` | ✅ +40.66% | $48.34 | 10 | 70% | C | BEARISH | 66/6 | 32 | +9.99% | 48h | TP_HIT | +4.7% |
| 29 | 04-17 22:28 | `SPELLUSDT` | ✅ +16.93% | $20.60 | 9 | 70% | C | BEARISH | 43/16 | 17 | +4.60% | 125h | TP_HIT | +2.2% |
| 30 | 04-17 13:27 | `SXTUSDT` | ✅ +0.23% | $0.24 | 8 | 60% | C | BULLISH | 35/17 | 14 | +2.99% | 168h | EXPIRED | +0.3% |
| 31 | 04-17 07:40 | `STRKUSDT` | ✅ +14.68% | $17.39 | 8 | 55% | C | BULLISH | 28/15 | 25 | +6.19% | 34h | TP_HIT | — |
| 32 | 04-16 15:44 | `WIFUSDT` | ✅ +10.61% | $11.35 | 10 | 75% | C | BULLISH | 41/8 | 25 | +5.29% | 65h | TP_HIT | — |
| 33 | 04-16 11:57 | `SHELLUSDT` | ✅ +10.45% | $10.61 | 9 | 89% | A | BEARISH | 37/15 | 27 | -2.05% | 144h | TP_HIT | — |
| 34 | 04-16 10:35 | `EGLDUSDT` | ✅ +10.50% | $12.07 | 8 | 65% | C | BULLISH | 27/21 | 24 | +3.72% | 13h | TP_HIT | +7.4% |
| 35 | 04-16 03:52 | `LUMIAUSDT` | ✅ +10.11% | $10.98 | 9 | 75% | C | BEARISH | 37/10 | 27 | +2.95% | 80h | TP_HIT | +31.8% |
| 36 | 04-15 21:39 | `NEWTUSDT` | ✅ +10.52% | $12.80 | 8 | 55% | B | BULLISH | 32/12 | 40 | +8.64% | 0h | TP_HIT | +22.3% |
| 37 | 04-15 20:22 | `CTSIUSDT` | ✅ +37.73% | $39.89 | 9 | 65% | B | BEARISH | 28/11 | 27 | +6.11% | 68h | TP_HIT | +1.8% |
| 38 | 04-15 09:15 | `CUSDT` | ✅ +10.51% | $11.41 | 8 | 65% | C | BEARISH | 43/21 | 49 | -2.51% | 63h | TP_HIT | +27.6% |
| 39 | 04-15 08:40 | `DEXEUSDT` | ✅ +25.42% | $26.76 | 9 | 95% | A | BEARISH | 39/13 | 16 | +2.65% | 61h | TP_HIT | +23.1% |
| 40 | 04-15 08:40 | `WIFUSDT` | ❌ -4.46% | $-4.50 | 10 | 75% | C | BEARISH | 47/8 | 29 | +12.29% | 178h | EXPIRED | +4.0% |
| 41 | 04-14 20:16 | `EPICUSDT` | ✅ +10.23% | $13.23 | 8 | 76% | A | BEARISH | 39/14 | 15 | +3.15% | 52h | TP_HIT | +10.2% |
| 42 | 04-14 18:51 | `RESOLVUSDT` | ❌ -9.00% | $-9.27 | 9 | 70% | C | BULLISH | 32/29 | 19 | +1.82% | 64h | SL_HIT | +17.5% |
| 43 | 04-14 18:50 | `TNSRUSDT` | ❌ -8.15% | $-10.87 | 10 | 75% | B | BULLISH | 32/14 | 20 | +2.19% | 51h | SL_HIT | +12.2% |
| 44 | 04-14 05:36 | `NIGHTUSDT` | ❌ -8.25% | $-8.81 | 9 | 60% | C | BEARISH | 65/4 | 34 | +1.28% | 26h | SL_HIT | +8.3% |
| 45 | 04-13 15:19 | `MUBARAKUSDT` | ✅ +10.14% | $10.78 | 9 | 65% | C | BEARISH | 26/24 | 28 | -5.43% | 14h | TP_HIT | +29.0% |
| 46 | 04-13 03:06 | `PLUMEUSDT` | ✅ +10.50% | $11.32 | 9 | 75% | C | BEARISH | 38/23 | 15 | +3.34% | 9h | TP_HIT | +35.1% |
| 47 | 04-13 00:32 | `PLUMEUSDT` | ✅ +10.09% | $11.56 | 9 | 70% | C | BEARISH | 38/23 | 15 | +1.77% | 7h | TP_HIT | +35.5% |
| 48 | 04-12 21:40 | `C98USDT` | ❌ -10.60% | $-14.26 | 9 | 70% | C | BULLISH | 54/9 | 24 | +3.45% | 6h | SL_HIT | +14.8% |
| 49 | 04-12 18:55 | `BIFIUSDT` | ❌ -8.53% | $-10.07 | 9 | 93% | A | BEARISH | 36/13 | 29 | +5.69% | 2h | SL_HIT | +6.9% |
| 50 | 04-12 18:29 | `MDTUSDT` | ❌ -8.09% | $-8.46 | 9 | 70% | C | BEARISH | 33/15 | 20 | +5.01% | 0h | SL_HIT | — |
| 51 | 04-12 18:28 | `MANTRAUSDT` | ✅ +14.02% | $17.60 | 8 | 60% | C | BULLISH | 30/22 | 20 | -1.33% | 2h | TP_HIT | — |
| 52 | 04-12 16:04 | `HFTUSDT` | ❌ -2.16% | $-2.11 | 9 | 75% | C | BEARISH | 25/9 | 21 | +4.51% | 168h | EXPIRED | +7.9% |
| 53 | 04-12 15:44 | `AVAXUSDT` | ✅ +0.67% | $0.72 | 8 | 70% | C | BULLISH | 30/19 | 25 | -0.56% | 168h | EXPIRED | +7.4% |
| 54 | 04-12 15:38 | `BTCUSDT` | ✅ +4.92% | $6.34 | 9 | 75% | C | BULLISH | 43/19 | 21 | +0.17% | 168h | EXPIRED | — |
| 55 | 04-12 15:38 | `UNIUSDT` | ❌ -2.86% | $-3.57 | 9 | 70% | C | BULLISH | 33/20 | 22 | -0.42% | 168h | EXPIRED | +6.0% |
| 56 | 04-12 15:38 | `ADAUSDT` | ❌ -2.38% | $-2.88 | 9 | 70% | B | BULLISH | 31/17 | 27 | -0.45% | 168h | EXPIRED | +8.8% |
| 57 | 04-12 15:38 | `DOGEUSDT` | ❌ -0.49% | $-0.56 | 8 | 60% | C | BULLISH | 34/21 | 30 | -0.85% | 168h | EXPIRED | +3.1% |
| 58 | 04-12 15:38 | `LTCUSDT` | ✅ +0.64% | $0.75 | 8 | 70% | C | BULLISH | 36/17 | 23 | -0.43% | 168h | EXPIRED | +1.7% |
| 59 | 04-12 15:32 | `MEUSDT` | ❌ -3.71% | $-5.08 | 9 | 95% | A | BULLISH | 40/2 | 35 | +5.42% | 168h | EXPIRED | +6.6% |
| 60 | 04-12 15:32 | `LUNAUSDT` | ❌ -2.16% | $-3.15 | 9 | 93% | A | BULLISH | 33/19 | 20 | +1.28% | 168h | EXPIRED | +2.7% |
| 61 | 04-12 15:08 | `PYRUSDT` | ✅ +12.55% | $16.66 | 8 | 95% | A+ | BULLISH | 45/13 | 32 | -5.56% | 168h | TP_HIT | — |
| 62 | 04-12 10:57 | `CATIUSDT` | ✅ +14.55% | $15.04 | 9 | 75% | B | BEARISH | 42/3 | 26 | +2.80% | 37h | TP_HIT | — |
| 63 | 04-12 01:48 | `ENSOUSDT` | ❌ -8.38% | $-8.41 | 9 | 70% | C | BEARISH | 58/9 | 18 | +7.37% | 111h | SL_HIT | +9.4% |
| 64 | 04-10 20:30 | `DGBUSDT` | ✅ +10.00% | $10.09 | 9 | 95% | A | BEARISH | 45/6 | 59 | +4.27% | 124h | TP_HIT | — |
| 65 | 04-10 13:11 | `LUNCUSDT` | ✅ +10.02% | $14.14 | 9 | 93% | A | BULLISH | 48/16 | 36 | +1.32% | 118h | TP_HIT | — |
| 66 | 04-10 12:01 | `LUNCUSDT` | ✅ +10.32% | $10.75 | 9 | 70% | B | BEARISH | 28/17 | 36 | +0.06% | 116h | TP_HIT | — |
| 67 | 04-07 22:40 | `ARBUSDT` | ✅ +10.30% | $11.39 | 8 | 60% | C | BULLISH | 24/19 | 26 | -1.40% | 55h | TP_HIT | — |
| 68 | 04-07 10:45 | `ENSOUSDT` | ✅ +12.99% | $12.99 | 9 | 70% | C | BULLISH | 37/22 | 15 | +0.45% | 22h | TP_HIT | — |
| 69 | 04-06 13:09 | `AVNTUSDT` | ✅ +12.67% | $19.00 | 10 | 70% | C | BULLISH | 41/12 | 31 | +1.45% | 22h | TP_HIT | +10.7% |

---

## 💡 Improvement Proposals

1. 🎯 **Migrate to V7-style hybrid TP** — winners leave 7.5% on the table on average. V7 captures more by: TP1 partial @ +10% (locks profit), TP2 partial @ +20%, trail the remainder. Apply the same exit logic to V4's entry filter to potentially boost avg win from +11.66% toward +15.43%.

---

## ⚙️ How to apply these

V4's gate is implemented in `mega-buy-ai/openclaw/portfolio/manager_v4.py` — the entry logic checks `scanner_score ≥ 8`, `is_vip OR is_high_ticket`, and `green_4h`. To apply a new filter:

```python
# In manager_v4.py, in the gate check:
if features.get('btc_trend_1h') == 'BEARISH':
    return None, 'BTC bearish — skip'
if features.get('quality_grade') in {'C', ''}:
    return None, 'Grade C — skip'
```

Backtest each proposed filter individually before stacking them — combining too many filters can starve the portfolio of trades.
