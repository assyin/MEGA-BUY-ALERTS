# 📊 OpenClaw Portfolio Performance Report

_Generated: 2026-04-26 14:03 UTC_

Cumulative analysis of all 9 virtual portfolios (V1 → V9) — open positions, closed history, win rates, drawdown, and live P&L. Capital initial: $5,000 per portfolio.

## 🎯 Executive Summary

| V | Strategy | Closed | WR | Avg PnL | Total PnL$ | Open | Live PnL$ | Balance | DD% |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **V1** | TP +10% / SL -8% (fixed) | 215 | 41.4% | +0.02% | $-11.38 | 10 | $-31.65 | $3,878.93 | 31.16% |
| **V2** | Trailing TP + partial close | 62 | 38.7% | +2.74% | $80.77 | 10 | $1.43 | $4,216.97 | 19.56% |
| **V3** | 95% conf | 3% × 25 pos | Timeout 48h | 149 | 44.3% | +0.59% | $120.62 | 7 | $-10.25 | $4,186.92 | 49.93% |
| **V4** | Gate: Score>=8 + VIP/HT + Green4H | 69 | 62.3% | +4.77% | $377.05 | 14 | $-5.19 | $3,777.86 | 33.29% |
| **V5** | Combo: 95% + Green4H + 24h>0% | 53 | 60.4% | +2.22% | $110.64 | 5 | $-9.91 | $4,389.83 | 0.95% |
| **V6** | Body 4H>=3% + Fixed TP+15% | 12 slots × 8% × $5K | 43 | 41.9% | +0.73% | $125.72 | 2 | $-1.26 | $4,325.72 | 4.95% |
| **V7** | Body 4H>=3% + Hybrid Trailing | TP1 50%@+10% + TP2 30%@+20% + 20% Trail | 43 | 46.5% | +0.72% | $124.32 | 2 | $-1.26 | $4,324.32 | 4.26% |
| **V8** | V6 + Ultra Filter (ADX 15-35 + BTC Bull + 24h>=1%) | Fixed TP+15% | 42 | 40.5% | +1.44% | $242.54 | 2 | $-9.67 | $4,442.54 | 6.44% |
| **V9** | V8 strategy + V7 trailing | 41 | 53.7% | +2.02% | $330.94 | 3 | $-36.27 | $4,130.94 | 4.22% |

### Totals across all portfolios

- **Initial capital combined**: $45,000.00
- **Current balance combined**: $37,674.03 (-16.28%)
- **Closed trades total**: 717 (331 wins / 376 losses → WR 46.2%)
- **Realized P&L closed**: $1,501.22
- **Open positions**: 55 (live unrealized: $-104.03)

---

## 📈 Per-Portfolio Deep Dive

### V1 — TP +10% / SL -8% (fixed)

**State**

- Balance: **$3,878.93** (init: $5,000.00, peak: $5,000.00)
- Cumulative PnL (state): $-11.38
- Max drawdown: **31.16%** 🚨 in DD mode

**Trades stats**

- Closed: **215** | Open: 10 | Breakeven: 1
- Wins: **89** | Losses: **125** → WR **41.4%**
- Avg win: **+6.81%** | Avg loss: **-4.81%**
- Avg PnL closed: +0.02% (median: -1.10%)
- Realized PnL closed: **$-11.38**
- Live open PnL sum: $-31.65 (-19.84%)

**Best trade**: `VICUSDT` +30.76% ($66.78) — TP_HIT on 2026-04-18
**Worst trade**: `BANDUSDT` -17.04% ($-17.85) — SL_HIT on 2026-04-17

**Top pairs by trade count**: `FFUSDT` (5x), `FUNUSDT` (5x), `NEWTUSDT` (4x), `ONGUSDT` (4x), `DGBUSDT` (3x)

**Close reasons**: SL_HIT=117, TP_HIT=81, EXPIRED=16, DELISTED=1

---

### V2 — Trailing TP + partial close

**State**

- Balance: **$4,216.97** (init: $5,000.00, peak: $5,000.00)
- Cumulative PnL (state): $80.77
- Max drawdown: **19.56%** 🚨 in DD mode

**Trades stats**

- Closed: **62** | Open: 10 | Breakeven: 2
- Wins: **24** | Losses: **36** → WR **38.7%**
- Avg win: **+14.23%** | Avg loss: **-4.76%**
- Avg PnL closed: +2.74% (median: -1.62%)
- Realized PnL closed: **$80.77**
- Live open PnL sum: $1.43 (+0.80%)

**Best trade**: `1000SATSUSDT` +43.80% ($16.71) — TRAILING_SL on 2026-04-16
**Worst trade**: `KATUSDT` -14.83% ($-3.14) — SL_HIT on 2026-04-26

**Top pairs by trade count**: `RESOLVUSDT` (2x), `FFUSDT` (2x), `C98USDT` (2x), `BOMEUSDT` (2x), `OGUSDT` (2x)

**Close reasons**: SL_HIT=33, TRAILING_SL=18, EXPIRED=11

---

### V3 — 95% conf | 3% × 25 pos | Timeout 48h

**State**

- Balance: **$4,186.92** (init: $5,000.00, peak: $5,054.68)
- Cumulative PnL (state): $120.62
- Max drawdown: **49.93%** 

**Trades stats**

- Closed: **149** | Open: 7 | Breakeven: 4
- Wins: **66** | Losses: **79** → WR **44.3%**
- Avg win: **+6.26%** | Avg loss: **-4.12%**
- Avg PnL closed: +0.59% (median: -0.41%)
- Realized PnL closed: **$120.62**
- Live open PnL sum: $-10.25 (-7.16%)

**Best trade**: `STOUSDT` +20.32% ($30.48) — TP_HIT on 2026-04-04
**Worst trade**: `STOUSDT` -9.99% ($-14.10) — SL_HIT on 2026-04-04

**Top pairs by trade count**: `SYSUSDT` (5x), `ALTUSDT` (4x), `COMPUSDT` (4x), `BERAUSDT` (3x), `SOPHUSDT` (3x)

**Close reasons**: TIMEOUT_48H=102, TP_HIT=26, SL_HIT=21

---

### V4 — Gate: Score>=8 + VIP/HT + Green4H

**State**

- Balance: **$3,777.86** (init: $5,000.00, peak: $5,000.00)
- Cumulative PnL (state): $377.05
- Max drawdown: **33.29%** 

**Trades stats**

- Closed: **69** | Open: 14 | Breakeven: 0
- Wins: **43** | Losses: **26** → WR **62.3%**
- Avg win: **+11.66%** | Avg loss: **-6.62%**
- Avg PnL closed: +4.77% (median: +10.00%)
- Realized PnL closed: **$377.05**
- Live open PnL sum: $-5.19 (-3.96%)

**Best trade**: `PORTALUSDT` +40.66% ($48.34) — TP_HIT on 2026-04-18
**Worst trade**: `C98USDT` -10.60% ($-14.26) — SL_HIT on 2026-04-12

**Top pairs by trade count**: `ADAUSDT` (2x), `LUNCUSDT` (2x), `MANTRAUSDT` (2x), `ENSOUSDT` (2x), `PLUMEUSDT` (2x)

**Close reasons**: TP_HIT=35, EXPIRED=17, SL_HIT=17

---

### V5 — Combo: 95% + Green4H + 24h>0%

**State**

- Balance: **$4,389.83** (init: $5,000.00, peak: $110.64)
- Cumulative PnL (state): $110.64
- Max drawdown: **0.95%** 

**Trades stats**

- Closed: **53** | Open: 5 | Breakeven: 0
- Wins: **32** | Losses: **21** → WR **60.4%**
- Avg win: **+7.92%** | Avg loss: **-6.47%**
- Avg PnL closed: +2.22% (median: +3.96%)
- Realized PnL closed: **$110.64**
- Live open PnL sum: $-9.91 (-6.57%)

**Best trade**: `GPSUSDT` +10.00% ($7.42) — TP_HIT on 2026-04-13
**Worst trade**: `ADAUSDT` -8.00% ($-6.93) — SL_HIT on 2026-04-12

**Top pairs by trade count**: `SUPERUSDT` (3x), `SUSDT` (2x), `ALTUSDT` (2x), `1000SATSUSDT` (2x), `FIDAUSDT` (2x)

**Close reasons**: TP_HIT=21, EXPIRED=18, SL_HIT=14

---

### V6 — Body 4H>=3% + Fixed TP+15% | 12 slots × 8% × $5K

**State**

- Balance: **$4,325.72** (init: $5,000.00, peak: $322.46)
- Cumulative PnL (state): $125.72
- Max drawdown: **4.95%** 

**Trades stats**

- Closed: **43** | Open: 2 | Breakeven: 2
- Wins: **18** | Losses: **23** → WR **41.9%**
- Avg win: **+9.55%** | Avg loss: **-6.11%**
- Avg PnL closed: +0.73% (median: -0.86%)
- Realized PnL closed: **$125.72**
- Live open PnL sum: $-1.26 (-0.32%)

**Best trade**: `币安人生USDT` +16.80% ($67.19) — TP_HIT on 2026-04-10
**Worst trade**: `SSVUSDT` -8.00% ($-32.00) — SL_HIT on 2026-04-19

**Top pairs by trade count**: `TRUUSDT` (3x), `MDTUSDT` (2x), `ARBUSDT` (1x), `STOUSDT` (1x), `SSVUSDT` (1x)

**Close reasons**: TIMEOUT_48H=22, SL_HIT=13, TP_HIT=8

---

### V7 — Body 4H>=3% + Hybrid Trailing | TP1 50%@+10% + TP2 30%@+20% + 20% Trail

**State**

- Balance: **$4,324.32** (init: $5,000.00, peak: $261.07)
- Cumulative PnL (state): $124.32
- Max drawdown: **4.26%** 

**Trades stats**

- Closed: **43** | Open: 2 | Breakeven: 0
- Wins: **20** | Losses: **23** → WR **46.5%**
- Avg win: **+8.94%** | Avg loss: **-6.42%**
- Avg PnL closed: +0.72% (median: -1.33%)
- Realized PnL closed: **$124.32**
- Live open PnL sum: $-1.26 (-0.32%)

**Best trade**: `ENJUSDT` +24.09% ($96.37) — TRAIL_STOP on 2026-04-12
**Worst trade**: `TRUUSDT` -8.00% ($-32.00) — SL_HIT on 2026-04-08

**Top pairs by trade count**: `TRUUSDT` (2x), `MDTUSDT` (2x), `COMPUSDT` (1x), `SPELLUSDT` (1x), `GLMRUSDT` (1x)

**Close reasons**: TIMEOUT_72H=17, SL_HIT=15, TRAIL_STOP=6, BREAKEVEN_STOP=5

---

### V8 — V6 + Ultra Filter (ADX 15-35 + BTC Bull + 24h>=1%) | Fixed TP+15%

**State**

- Balance: **$4,442.54** (init: $5,000.00, peak: $416.44)
- Cumulative PnL (state): $242.54
- Max drawdown: **6.44%** 

**Trades stats**

- Closed: **42** | Open: 2 | Breakeven: 1
- Wins: **17** | Losses: **24** → WR **40.5%**
- Avg win: **+10.15%** | Avg loss: **-4.66%**
- Avg PnL closed: +1.44% (median: -0.76%)
- Realized PnL closed: **$242.54**
- Live open PnL sum: $-9.67 (-2.41%)

**Best trade**: `币安人生USDT` +16.80% ($67.19) — TP_HIT on 2026-04-10
**Worst trade**: `TNSRUSDT` -8.00% ($-32.00) — SL_HIT on 2026-04-12

**Top pairs by trade count**: `TRUUSDT` (2x), `GLMRUSDT` (1x), `SKLUSDT` (1x), `BONKUSDT` (1x), `NEARUSDT` (1x)

**Close reasons**: TIMEOUT_48H=26, TP_HIT=9, SL_HIT=7

---

### V9 — V8 strategy + V7 trailing

**State**

- Balance: **$4,130.94** (init: $5,000.00, peak: $400.99)
- Cumulative PnL (state): $330.94
- Max drawdown: **4.22%** 

**Trades stats**

- Closed: **41** | Open: 3 | Breakeven: 0
- Wins: **22** | Losses: **19** → WR **53.7%**
- Avg win: **+8.77%** | Avg loss: **-5.80%**
- Avg PnL closed: +2.02% (median: +1.23%)
- Realized PnL closed: **$330.94**
- Live open PnL sum: $-36.27 (-9.06%)

**Best trade**: `ENJUSDT` +23.96% ($95.82) — TRAIL_STOP on 2026-04-12
**Worst trade**: `DENTUSDT` -8.00% ($-32.00) — SL_HIT on 2026-04-16

**Top pairs by trade count**: `GLMRUSDT` (1x), `SKLUSDT` (1x), `BONKUSDT` (1x), `NEARUSDT` (1x), `ICPUSDT` (1x)

**Close reasons**: TIMEOUT_72H=19, SL_HIT=10, TRAIL_STOP=8, BREAKEVEN_STOP=4

---

## 🏆 Verdict & Synthesis

### Most profitable (realized USD)

1. **V4** — $377.05 on 69 trades (WR 62.3%)
2. **V9** — $330.94 on 41 trades (WR 53.7%)
3. **V8** — $242.54 on 42 trades (WR 40.5%)

### Highest win rate (min 5 trades)

1. **V4** — WR 62.3% on 69 trades, avg +4.77%
2. **V5** — WR 60.4% on 53 trades, avg +2.22%
3. **V9** — WR 53.7% on 41 trades, avg +2.02%

### Lowest drawdown (most defensive)

1. **V5** — DD 0.95%, balance $4,389.83
2. **V9** — DD 4.22%, balance $4,130.94
3. **V7** — DD 4.26%, balance $4,324.32

### Best risk-adjusted (PnL$ / DD%)

1. **V5** — ratio 116.5 ($110.64 ÷ 0.95% DD)
2. **V9** — ratio 78.4 ($330.94 ÷ 4.22% DD)
3. **V8** — ratio 37.7 ($242.54 ÷ 6.44% DD)

### Notes & caveats

- All PnL values are computed from positions stored in Supabase tables `openclaw_positions[_v*]`.
- `Live PnL$` represents unrealized P&L on currently open positions (snapshot at report time).
- Win rate is calculated over closed trades only; PENDING/OPEN trades excluded.
- Capital is virtual ($5,000 per portfolio) — these portfolios run in parallel for strategy comparison.
- Some portfolios may have very few trades — interpret WR/avg figures with caution if `closed < 10`.
