# Backtest Quality Filter 4 Axes — 14 Derniers Jours

**Date:** 2026-03-30 14:39
**Periode:** 2026-03-16 → 2026-03-30
**Alertes totales:** 2735 | Uniques: 2330 | Filtrees: 1190 | Analysees: 1190
**TP:** +10% | **SL:** -8% | **Horizon:** 7 jours

## 1. Expectancy par Grade

| Grade | Trades | WIN | LOSE | OPEN | WR% | Avg Win | Avg Loss | Expectancy | PnL Total |
|-------|--------|-----|------|------|-----|---------|----------|------------|-----------|
| **A+** | 69 | 19 | 35 | 15 | 35.2% | +10.0% | -8.0% | **-1.67%** | -90.0% |
| **A** | 281 | 62 | 137 | 82 | 31.2% | +10.0% | -8.0% | **-2.39%** | -476.0% |
| B | 406 | 80 | 214 | 112 | 27.2% | +10.0% | -8.0% | **-3.10%** | -912.0% |
| C | 434 | 86 | 177 | 171 | 32.7% | +10.0% | -8.0% | **-2.11%** | -556.0% |
|-------|--------|-----|------|------|-----|---------|----------|------------|-----------|
| **ALL** | 1190 | 247 | 563 | 380 | 30.5% | +10.0% | -8.0% | **-2.51%** | -2034.0% |

## 2. Simulation — Impact du filtre

| Filtre | Trades | WIN | LOSE | WR% | PnL Total | Avg/trade | Big Winners (>=+20%) |
|--------|--------|-----|------|-----|-----------|-----------|----------------------|
| Aucun filtre | 1190 | 247 | 563 | 30.5% | -2034.0% | -2.51% | 107 |
| **>= Grade A** | 350 | 81 | 172 | 32.0% | -566.0% | -2.24% | 36 |
| >= Grade B | 756 | 161 | 386 | 29.4% | -1478.0% | -2.70% | 79 |
| Grade A+ seul | 69 | 19 | 35 | 35.2% | -90.0% | -1.67% | 10 |

## 3. Distribution PnL Max par Grade

| Grade | N | PnL Max Avg | >=+5% | >=+10% | >=+20% | >=+30% | >=+50% |
|-------|---|-------------|-------|--------|--------|--------|--------|
| A+ | 69 | +10.8% | 28 (41%) | 19 (28%) | 10 (14%) | 8 (12%) | 6 (9%) |
| A | 281 | +7.7% | 116 (41%) | 62 (22%) | 26 (9%) | 16 (6%) | 5 (2%) |
| B | 406 | +8.2% | 149 (37%) | 80 (20%) | 43 (11%) | 22 (5%) | 11 (3%) |
| C | 434 | +7.6% | 173 (40%) | 86 (20%) | 28 (6%) | 18 (4%) | 10 (2%) |

## 4. Detail des 350 alertes Grade A+ et A

| # | Pair | Date | Score | Grade | T | S | M | Ti | PnL Max | PnL Min | Outcome | Details |
|---|------|------|-------|-------|---|---|---|-----|---------|---------|---------|---------|
| 1 | CUSDT | 03-25T20:00 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +73.3% | -4.6% | WIN | Trend(ADX=32,DI=27), Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 2 | CUSDT | 03-25T08:16 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +70.2% | -6.3% | WIN | Trend(ADX=25,DI=31), Mom(MACD), Time(Vol=0.7x) |
| 3 | CUSDT | 03-25T16:01 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +64.8% | -9.3% | WIN | Trend(ADX=31,DI=33), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 4 | ONTUSDT | 03-24T20:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +63.9% | -15.8% | WIN | Trend(ADX=37,DI=52), Mom(MACD), Time(Vol=0.5x) |
| 5 | ONTUSDT | 03-29T08:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +61.7% | -3.8% | WIN | Trend(ADX=52,DI=26), Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 6 | ONTUSDT | 03-25T00:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +57.1% | -19.3% | WIN | Trend(ADX=40,DI=48), Mom(MACD), Time(Vol=0.3x) |
| 7 | ONTUSDT | 03-29T04:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +57.1% | -6.5% | WIN | Trend(ADX=52,DI=27), Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 8 | DUSDT | 03-29T16:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +56.7% | -3.7% | WIN | Trend(ADX=32,DI=33), Struct(FVG), Mom(MACD) |
| 9 | ONTUSDT | 03-28T23:18 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +56.1% | -7.1% | WIN | Trend(ADX=52,DI=30), Struct(OB), Mom(MACD), Time(Vol=0.7x) |
| 10 | ONTUSDT | 03-28T16:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +54.3% | -8.1% | WIN | Trend(ADX=52,DI=32), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 11 | ONTUSDT | 03-29T00:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +50.6% | -10.3% | WIN | Trend(ADX=52,DI=32), Struct(FVG), Mom(MACD) |
| 12 | KNCUSDT | 03-23T23:44 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +45.8% | -1.4% | WIN | Trend(ADX=29,DI=20), Mom(MACD), Time(Vol=0.2x) |
| 13 | ONTUSDT | 03-26T00:31 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +45.1% | -25.5% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 14 | KNCUSDT | 03-24T00:02 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +45.0% | -1.9% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 15 | DUSKUSDT | 03-23T00:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +44.2% | +1.4% | WIN | Trend(ADX=29,DI=21), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 16 | KNCUSDT | 03-23T16:02 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +43.5% | -2.9% | WIN | Trend(ADX=29,DI=22), Struct(FVG), Mom(MACD) |
| 17 | KNCUSDT | 03-24T15:36 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +43.4% | -2.9% | WIN | Trend(ADX=31,DI=27), Struct(FVG), Mom(MACD) |
| 18 | DUSKUSDT | 03-23T11:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +40.6% | +6.2% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 19 | DUSKUSDT | 03-23T04:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +40.1% | -1.5% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 20 | ENJUSDT | 03-18T04:33 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +39.8% | -9.1% | WIN | Trend(ADX=53,DI=44), Mom(MACD), Time(Vol=0.3x) |
| 21 | DUSKUSDT | 03-22T23:03 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +39.4% | -3.6% | WIN | Trend(ADX=28,DI=23), Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 22 | FORTHUSDT | 03-26T14:08 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +34.7% | -20.3% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 23 | PROVEUSDT | 03-26T14:08 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +31.9% | -16.1% | WIN | Trend(ADX=42,DI=34), Mom(MACD), Time(Vol=0.1x) |
| 24 | PROVEUSDT | 03-26T16:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +31.8% | -16.1% | WIN | Trend(ADX=43,DI=32), Mom(MACD), Time(Vol=0.1x) |
| 25 | DUSDT | 03-30T07:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +26.5% | -1.5% | WIN | Trend(ADX=57,DI=50), Struct(FVG), Mom(MACD) |
| 26 | PROVEUSDT | 03-26T09:36 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +25.7% | -20.1% | WIN | Trend(ADX=41,DI=42), Mom(MACD), Time(Vol=0.3x) |
| 27 | DUSDT | 03-30T09:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +24.9% | +13.3% | WIN | Trend(ADX=61,DI=43), Struct(FVG), Mom(MACD) |
| 28 | CATIUSDT | 03-24T16:02 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +23.5% | -4.8% | WIN | Trend(ADX=32,DI=20), Struct(FVG), Mom(MACD) |
| 29 | VANRYUSDT | 03-17T09:33 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +23.1% | -15.4% | WIN | Trend(ADX=62,DI=53), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 30 | RDNTUSDT | 03-29T00:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +23.0% | -3.3% | WIN | Trend(ADX=29,DI=23), Mom(MACD), Time(Vol=0.2x) |
| 31 | JTOUSDT | 03-24T08:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +22.3% | -14.9% | WIN | Trend(ADX=32,DI=24), Mom(MACD), Time(Vol=0.5x) |
| 32 | BANANAS31USDT | 03-22T23:03 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +21.9% | -7.8% | WIN | Trend(ADX=32,DI=45), Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 33 | BANANAS31USDT | 03-23T04:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +20.9% | -8.5% | WIN | Trend(ADX=38,DI=41), Mom(MACD), Time |
| 34 | JTOUSDT | 03-24T00:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +20.6% | -16.1% | WIN | Trend(ADX=28,DI=29), Mom(MACD), Time(Vol=0.6x) |
| 35 | RSRUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +20.6% | -4.8% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 36 | RSRUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +20.0% | -5.3% | WIN | Trend(ADX=29,DI=23), Struct(FVG), Mom(MACD) |
| 37 | DYDXUSDT | 03-24T20:32 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +19.6% | +0.4% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 38 | JTOUSDT | 03-24T07:15 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +19.5% | -16.8% | WIN | Trend(ADX=30,DI=28), Mom(MACD), Time(Vol=0.5x) |
| 39 | BANANAS31USDT | 03-23T00:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +19.4% | -9.7% | WIN | Trend(ADX=35,DI=43), Mom(MACD), Time(Vol=0.3x) |
| 40 | NIGHTUSDT | 03-21T20:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +19.3% | -6.8% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 41 | DYDXUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +18.7% | -3.2% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 42 | GLMUSDT | 03-17T10:07 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +18.7% | -10.6% | WIN | Trend(ADX=56,DI=22), Struct(FVG), Mom(MACD) |
| 43 | BATUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +18.1% | -8.0% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 44 | OPENUSDT | 03-23T00:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +18.0% | -3.3% | WIN | Trend(ADX=20,DI=30), Struct(FVG), Mom(MACD) |
| 45 | DYDXUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +17.7% | -4.0% | WIN | Trend(ADX=31,DI=29), Struct(OB), Mom(MACD) |
| 46 | PIXELUSDT | 03-25T09:31 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +16.9% | -14.3% | WIN | Trend(ADX=11,DI=22), Struct(OB), Mom(MACD), Time(Vol=0.8x) |
| 47 | ONGUSDT | 03-29T08:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +16.5% | -2.3% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.1x) |
| 48 | ONGUSDT | 03-29T04:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +15.4% | -3.2% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 49 | OPENUSDT | 03-23T04:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +15.0% | -5.8% | WIN | Trend(ADX=23,DI=38), Struct(FVG), Mom(MACD) |
| 50 | CFGUSDT | 03-28T03:01 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +14.7% | -8.3% | WIN | Trend(ADX=31,DI=36), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 51 | ENJUSDT | 03-27T12:00 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +14.2% | -6.2% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.1x) |
| 52 | ZBTUSDT | 03-28T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +13.9% | -1.1% | WIN | Trend(ADX=23,DI=24), Struct(FVG), Mom(MACD) |
| 53 | JTOUSDT | 03-23T23:44 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +13.9% | -20.7% | WIN | Trend(ADX=26,DI=34), Mom(MACD), Time(Vol=0.4x) |
| 54 | CFGUSDT | 03-29T12:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +13.7% | -3.0% | WIN | Trend(ADX=27,DI=29), Struct(FVG), Mom(MACD) |
| 55 | 1000SATSUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +13.6% | -10.0% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 56 | OPENUSDT | 03-23T23:44 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +13.2% | -7.2% | WIN | Trend(ADX=35,DI=31), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 57 | ONGUSDT | 03-28T20:00 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +13.0% | -5.2% | WIN | Trend(ADX=35,DI=23), Struct(FVG), Mom(MACD) |
| 58 | STEEMUSDT | 03-28T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +13.0% | -3.6% | WIN | Trend(ADX=40,DI=23), Struct(FVG), Mom(MACD) |
| 59 | OPENUSDT | 03-23T11:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +13.0% | -7.4% | WIN | Trend(ADX=27,DI=36), Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 60 | ALLOUSDT | 03-23T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +12.9% | -7.8% | WIN | Trend(ADX=26,DI=25), Struct(OB), Mom(MACD) |
| 61 | COTIUSDT | 03-16T17:33 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +12.8% | -11.4% | WIN | Trend(ADX=41,DI=17), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 62 | FLUXUSDT | 03-27T16:00 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +12.4% | -1.3% | WIN | Trend(ADX=29,DI=20), Struct(FVG), Mom(MACD) |
| 63 | DEGOUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +12.3% | -13.8% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 64 | CVCUSDT | 03-24T20:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +12.2% | -11.4% | WIN | Trend(ADX=35,DI=32), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 65 | PROVEUSDT | 03-26T00:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +12.1% | -28.7% | WIN | Trend(ADX=26,DI=45), Struct(FVG), Mom(MACD) |
| 66 | THEUSDT | 03-29T21:58 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +11.9% | -1.4% | WIN | Trend(ADX=41,DI=16), Struct(FVG), Mom(MACD) |
| 67 | PROVEUSDT | 03-26T20:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +11.9% | -14.0% | WIN | Trend(ADX=44,DI=29), Mom(MACD), Time(Vol=0.1x) |
| 68 | ONGUSDT | 03-28T16:02 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +11.8% | -6.2% | WIN | Trend(ADX=34,DI=27), Mom(MACD), Time(Vol=0.5x) |
| 69 | LDOUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +11.6% | -5.9% | WIN | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 70 | INITUSDT | 03-17T09:33 | 10/10 | A | ✅ | ✅ | ❌ | ✅ | +11.4% | -19.0% | WIN | Trend(ADX=44,DI=11), Struct(OB), Time(Vol=0.7x) |
| 71 | BANKUSDT | 03-24T20:02 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | +11.2% | -4.1% | WIN | Trend(ADX=40,DI=-2), Struct(OB), Time(Vol=0.7x) |
| 72 | FORTHUSDT | 03-29T08:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +11.1% | -15.7% | WIN | Trend(ADX=21,DI=24), Struct(OB), Mom(MACD) |
| 73 | SXPUSDT | 03-25T16:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +11.0% | -35.6% | WIN | Trend(ADX=27,DI=21), Struct(FVG), Mom(MACD) |
| 74 | CVCUSDT | 03-24T16:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +10.6% | -12.7% | WIN | Trend(ADX=32,DI=35), Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 75 | ENJUSDT | 03-27T08:45 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +10.5% | -9.2% | WIN | Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 76 | LDOUSDT | 03-24T20:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +10.5% | -7.0% | WIN | Trend(ADX=28,DI=24), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 77 | XLMUSDT | 03-23T18:30 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +10.5% | -2.5% | WIN | Trend(ADX=40,DI=15), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 78 | OPENUSDT | 03-23T18:30 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +10.4% | -9.5% | WIN | Trend(ADX=33,DI=37), Mom(MACD), Time(Vol=0.4x) |
| 79 | FORTHUSDT | 03-28T11:24 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +10.3% | -18.0% | WIN | Trend(ADX=30,DI=20), Struct(OB), Mom(MACD) |
| 80 | BANKUSDT | 03-21T20:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +10.2% | -15.8% | WIN | Trend(ADX=25,DI=21), Struct(FVG), Mom(MACD) |
| 81 | CVCUSDT | 03-24T15:36 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +10.1% | -13.1% | WIN | Trend(ADX=30,DI=32), Struct(FVG), Mom(MACD) |
| 82 | STEEMUSDT | 03-24T12:02 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +10.0% | -9.0% | LOSE | Trend(ADX=21,DI=23), Struct(FVG), Mom(MACD) |
| 83 | ONGUSDT | 03-30T04:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +9.9% | -2.9% | OPEN | Trend(ADX=30,DI=37), Struct(FVG), Mom(MACD) |
| 84 | DGBUSDT | 03-23T16:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +9.9% | -2.7% | OPEN | Trend(ADX=39,DI=21), Mom(MACD), Time |
| 85 | CFGUSDT | 03-29T11:31 | 10/10 | A | ✅ | ❌ | ✅ | ✅ | +9.8% | -6.3% | OPEN | Trend(ADX=24,DI=34), Mom(MACD), Time(Vol=0.6x) |
| 86 | THEUSDT | 03-30T00:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +9.7% | -3.3% | OPEN | Trend(ADX=45,DI=33), Mom(MACD), Time(Vol=0.8x) |
| 87 | ONGUSDT | 03-24T20:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +9.7% | -13.4% | LOSE | Trend(ADX=29,DI=32), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 88 | DYDXUSDT | 03-28T07:13 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +9.7% | -3.4% | OPEN | Trend(ADX=23,DI=27), Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 89 | HEMIUSDT | 03-29T03:21 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +9.7% | -7.2% | OPEN | Trend(ADX=50,DI=10), Struct(OB), Mom(MACD) |
| 90 | ZBTUSDT | 03-29T09:31 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +9.6% | -1.2% | OPEN | Trend(ADX=23,DI=24), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 91 | BIFIUSDT | 03-29T12:02 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +9.6% | -2.8% | OPEN | Trend(ADX=21,DI=31), Struct(OB), Mom(MACD) |
| 92 | LUMIAUSDT | 03-23T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +9.4% | -13.3% | LOSE | Trend(ADX=32,DI=21), Struct(FVG), Mom(MACD) |
| 93 | ZBTUSDT | 03-29T12:02 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +8.9% | -1.9% | OPEN | Trend(ADX=28,DI=22), Struct(FVG), Mom(MACD) |
| 94 | ICXUSDT | 03-24T15:36 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +8.8% | -13.6% | LOSE | Trend(ADX=20,DI=37), Struct(FVG), Mom(MACD) |
| 95 | HEMIUSDT | 03-28T23:18 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +8.8% | -7.9% | OPEN | Trend(ADX=34,DI=27), Struct(FVG), Mom(MACD) |
| 96 | DYDXUSDT | 03-28T08:26 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +8.7% | -4.3% | OPEN | Trend(ADX=21,DI=29), Struct(FVG), Mom(MACD) |
| 97 | SENTUSDT | 03-29T12:02 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +8.7% | -5.3% | OPEN | Trend(ADX=31,DI=45), Struct(OB), Mom(MACD) |
| 98 | LRCUSDT | 03-24T20:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +8.6% | -15.8% | LOSE | Trend(ADX=54,DI=30), Mom(MACD), Time(Vol=0.6x) |
| 99 | SENTUSDT | 03-30T04:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +8.6% | +2.1% | OPEN | Trend(ADX=46,DI=12), Mom(MACD), Time(Vol=0.2x) |
| 100 | BONKUSDT | 03-17T21:33 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +8.4% | -16.0% | LOSE | Trend(ADX=43,DI=20), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 101 | FLUXUSDT | 03-27T20:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +8.3% | -4.9% | OPEN | Trend(ADX=37,DI=30), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 102 | DCRUSDT | 03-25T12:55 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +8.3% | -11.2% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 103 | PENGUUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +8.2% | -13.0% | LOSE | Trend(ADX=27,DI=27), Struct(OB), Mom(MACD) |
| 104 | SENTUSDT | 03-30T00:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +7.8% | -1.2% | OPEN | Trend(ADX=47,DI=16), Mom(MACD), Time(Vol=0.3x) |
| 105 | ONGUSDT | 03-24T16:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +7.8% | -15.0% | LOSE | Trend(ADX=26,DI=38), Mom(MACD), Time(Vol=0.5x) |
| 106 | SKYUSDT | 03-23T11:31 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +7.7% | -3.6% | OPEN | Trend(ADX=27,DI=23), Struct(OB), Time(Vol=0.2x) |
| 107 | 1000CHEEMSUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +7.7% | -16.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 108 | AXSUSDT | 03-27T16:00 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +7.7% | -1.3% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 109 | BANANAUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +7.6% | -9.9% | LOSE | Trend(ADX=34,DI=28), Struct(OB), Mom(MACD) |
| 110 | CELOUSDT | 03-17T13:32 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +7.5% | -7.3% | OPEN | Trend(ADX=33,DI=23), Struct(FVG), Mom(MACD) |
| 111 | 币安人生USDT | 03-23T16:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +7.5% | -25.1% | LOSE | Trend(ADX=38,DI=23), Struct(FVG), Mom(MACD) |
| 112 | SAHARAUSDT | 03-25T16:01 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +7.4% | -12.0% | LOSE | Trend(ADX=33,DI=27), Struct(FVG), Time(Vol=0.1x) |
| 113 | OGNUSDT | 03-30T00:02 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +7.4% | +0.5% | OPEN | Trend(ADX=45,DI=27), Mom(MACD), Time(Vol=0.6x) |
| 114 | ENJUSDT | 03-27T00:00 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +7.3% | -11.8% | LOSE | Trend(ADX=25,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 115 | AXSUSDT | 03-27T20:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +7.3% | -1.6% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 116 | GASUSDT | 03-24T20:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +7.2% | -9.4% | LOSE | Trend(ADX=33,DI=39), Mom(MACD), Time(Vol=0.4x) |
| 117 | DYDXUSDT | 03-28T11:24 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +7.1% | -5.7% | OPEN | Trend(ADX=26,DI=26), Struct(FVG), Mom(MACD) |
| 118 | AXSUSDT | 03-28T03:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +6.9% | -1.9% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 119 | YBUSDT | 03-25T05:30 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +6.8% | -17.1% | LOSE | Trend(ADX=26,DI=22), Struct(FVG), Mom(MACD) |
| 120 | BANANAUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +6.7% | -10.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 121 | WLDUSDT | 03-28T12:01 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | +6.7% | -2.4% | OPEN | Trend(ADX=51,DI=10), Struct(FVG), Time(Vol=0.3x) |
| 122 | DYDXUSDT | 03-28T12:01 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +6.7% | -6.1% | OPEN | Trend(ADX=27,DI=25), Struct(FVG), Mom(MACD) |
| 123 | SAHARAUSDT | 03-25T15:31 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +6.6% | -12.7% | LOSE | Trend(ADX=31,DI=29), Struct(FVG), Time(Vol=0.1x) |
| 124 | FUNUSDT | 03-24T16:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +6.5% | -13.1% | LOSE | Trend(ADX=32,DI=25), Struct(FVG), Mom(MACD) |
| 125 | DGBUSDT | 03-24T07:15 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +6.5% | -5.8% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 126 | PENGUUSDT | 03-24T20:32 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +6.4% | -14.5% | LOSE | Trend(ADX=21,DI=25), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 127 | BROCCOLI714USDT | 03-23T00:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +6.4% | -11.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 128 | TUTUSDT | 03-23T11:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +6.2% | -19.5% | LOSE | Trend(ADX=30,DI=21), Struct(FVG), Mom(MACD) |
| 129 | RIFUSDT | 03-25T12:55 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +6.2% | -14.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 130 | SANTOSUSDT | 03-29T04:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +6.1% | -5.9% | OPEN | Trend(ADX=26,DI=21), Mom(MACD), Time(Vol=0.7x) |
| 131 | TURBOUSDT | 03-23T00:01 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +6.0% | -14.2% | LOSE | Trend(ADX=37,DI=32), Mom(MACD), Time(Vol=0.5x) |
| 132 | LAZIOUSDT | 03-26T20:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +5.9% | -1.7% | OPEN | Trend(ADX=42,DI=27), Mom(MACD), Time(Vol=0.5x) |
| 133 | KAVAUSDT | 03-27T20:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +5.9% | -5.5% | OPEN | Trend(ADX=30,DI=27), Mom(MACD), Time(Vol=0.2x) |
| 134 | BROCCOLI714USDT | 03-22T23:03 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +5.9% | -12.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 135 | ETCUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +5.9% | -6.8% | OPEN | Trend(ADX=29,DI=25), Struct(OB), Mom(MACD) |
| 136 | TRUMPUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +5.8% | -15.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 137 | HEMIUSDT | 03-29T21:58 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +5.7% | -2.9% | OPEN | Trend(ADX=43,DI=6), Mom(MACD), Time(Vol=0.4x) |
| 138 | ADAUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +5.7% | -11.2% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 139 | CUSDT | 03-29T16:32 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | +5.5% | -11.6% | LOSE | Trend(ADX=20,DI=31), Struct(OB), Time(Vol=0.5x) |
| 140 | PLUMEUSDT | 03-23T18:30 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +5.4% | -9.6% | LOSE | Trend(ADX=44,DI=13), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 141 | CVCUSDT | 03-25T00:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +5.2% | -12.9% | LOSE | Trend(ADX=37,DI=31), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 142 | AAVEUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +5.2% | -16.3% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 143 | KAVAUSDT | 03-27T16:00 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +5.1% | -6.2% | OPEN | Trend(ADX=28,DI=29), Mom(MACD), Time(Vol=0.7x) |
| 144 | RIFUSDT | 03-25T08:16 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +5.1% | -15.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 145 | POLYXUSDT | 03-24T20:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +4.9% | -8.9% | LOSE | Trend(ADX=37,DI=29), Mom(MACD), Time(Vol=0.1x) |
| 146 | AAVEUSDT | 03-24T20:32 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.9% | -16.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 147 | NEWTUSDT | 03-24T16:02 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +4.8% | -10.0% | LOSE | Trend(ADX=40,DI=29), Struct(FVG), Mom(MACD) |
| 148 | ZILUSDT | 03-18T00:33 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +4.8% | -15.8% | LOSE | Trend(ADX=45,DI=36), Mom(MACD), Time(Vol=0.7x) |
| 149 | YBUSDT | 03-26T14:08 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +4.8% | -18.6% | LOSE | Trend(ADX=21,DI=20), Struct(FVG), Mom(MACD) |
| 150 | XVGUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +4.7% | -13.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 151 | FLOKIUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.7% | -10.8% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 152 | IOTXUSDT | 03-24T13:49 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +4.7% | -13.8% | LOSE | Trend(ADX=31,DI=28), Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 153 | TURBOUSDT | 03-22T23:03 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +4.6% | -16.4% | LOSE | Trend(ADX=35,DI=35), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 154 | SENTUSDT | 03-29T21:58 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +4.6% | -6.0% | OPEN | Trend(ADX=48,DI=23), Struct(OB), Mom(MACD), Time(Vol=0.4x) |
| 155 | AVAXUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +4.5% | -10.8% | LOSE | Trend(ADX=29,DI=32), Struct(OB), Mom(MACD) |
| 156 | POLYXUSDT | 03-24T16:02 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +4.5% | -9.3% | LOSE | Trend(ADX=35,DI=32), Mom(MACD), Time(Vol=0.5x) |
| 157 | NEARUSDT | 03-29T22:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +4.4% | -0.8% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 158 | LAZIOUSDT | 03-26T09:36 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +4.4% | -5.1% | OPEN | Trend(ADX=40,DI=32), Mom(MACD), Time(Vol=0.5x) |
| 159 | VELODROMEUSDT | 03-23T19:46 | 7/10 | A | ✅ | ✅ | ✅ | ❌ | +4.4% | -8.3% | LOSE | Trend(ADX=55,DI=5), Struct(FVG), Mom(MACD) |
| 160 | LAZIOUSDT | 03-26T14:08 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +4.3% | -3.1% | OPEN | Trend(ADX=40,DI=28), Mom(MACD), Time(Vol=0.3x) |
| 161 | RIFUSDT | 03-25T07:52 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.3% | -15.7% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 162 | SANDUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +4.3% | -12.0% | LOSE | Trend(ADX=30,DI=27), Struct(FVG), Mom(MACD) |
| 163 | 1INCHUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.3% | -9.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 164 | ETCUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +4.3% | -8.3% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 165 | ACTUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +4.3% | -18.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.0x) |
| 166 | TONUSDT | 03-23T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +4.2% | -7.0% | OPEN | Trend(ADX=23,DI=34), Struct(FVG), Mom(MACD) |
| 167 | SANTOSUSDT | 03-29T08:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +4.2% | -7.6% | OPEN | Trend(ADX=28,DI=22), Struct(FVG), Mom(MACD) |
| 168 | CAKEUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +4.1% | -5.1% | OPEN | Trend(ADX=23,DI=24), Struct(FVG), Mom(MACD) |
| 169 | EIGENUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +4.1% | -16.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 170 | LINKUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.0% | -10.2% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 171 | LAZIOUSDT | 03-26T16:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +4.0% | -3.4% | OPEN | Trend(ADX=42,DI=31), Mom(MACD), Time(Vol=0.7x) |
| 172 | SANTOSUSDT | 03-29T16:02 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +4.0% | -7.8% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 173 | QTUMUSDT | 03-24T11:01 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +4.0% | -13.3% | LOSE | Trend(ADX=22,DI=36), Struct(FVG), Mom(MACD) |
| 174 | ACMUSDT | 03-23T04:01 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +3.9% | -4.4% | OPEN | Trend(ADX=44,DI=23), Mom(MACD), Time(Vol=0.4x) |
| 175 | SUNUSDT | 03-28T12:32 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +3.9% | -1.3% | OPEN | Trend(ADX=22,DI=37), Struct(FVG), Time(Vol=0.4x) |
| 176 | 1INCHUSDT | 03-23T13:01 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.8% | -9.8% | LOSE | Trend(ADX=41,DI=17), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 177 | TSTUSDT | 03-23T11:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +3.8% | -17.1% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 178 | ARKMUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +3.8% | -12.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 179 | SANDUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.7% | -12.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 180 | HEMIUSDT | 03-29T04:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.6% | -11.6% | LOSE | Trend(ADX=49,DI=15), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 181 | ACMUSDT | 03-23T00:01 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +3.6% | -4.6% | OPEN | Trend(ADX=44,DI=29), Mom(MACD), Time(Vol=0.5x) |
| 182 | TUTUSDT | 03-23T23:44 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +3.6% | -17.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 183 | ALLOUSDT | 03-25T08:16 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.6% | -15.4% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 184 | INITUSDT | 03-25T15:31 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.6% | -9.4% | LOSE | Trend(ADX=34,DI=26), Struct(OB), Mom(MACD), Time(Vol=0.1x) |
| 185 | MANAUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +3.6% | -10.1% | LOSE | Trend(ADX=24,DI=26), Struct(FVG), Mom(MACD) |
| 186 | DOGEUSDT | 03-24T07:15 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +3.6% | -7.0% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 187 | HEMIUSDT | 03-29T16:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +3.5% | -5.8% | OPEN | Trend(ADX=45,DI=9), Mom(MACD), Time(Vol=0.4x) |
| 188 | TURTLEUSDT | 03-27T12:00 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.5% | -4.5% | OPEN | Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 189 | INITUSDT | 03-25T08:16 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.5% | -9.6% | LOSE | Trend(ADX=33,DI=26), Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 190 | SYRUPUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +3.5% | -15.1% | LOSE | Trend(ADX=18,DI=23), Struct(OB), Mom(MACD) |
| 191 | GASUSDT | 03-25T08:16 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.5% | -6.6% | OPEN | Trend(ADX=40,DI=32), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 192 | ALLOUSDT | 03-25T07:52 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.4% | -15.6% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 193 | PHAUSDT | 03-28T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +3.4% | -4.8% | OPEN | Trend(ADX=24,DI=34), Struct(FVG), Mom(MACD) |
| 194 | KAVAUSDT | 03-27T12:00 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +3.3% | -7.8% | OPEN | Trend(ADX=25,DI=31), Mom(MACD), Time(Vol=0.7x) |
| 195 | JASMYUSDT | 03-23T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +3.2% | -7.6% | OPEN | Trend(ADX=30,DI=21), Struct(OB), Mom(MACD) |
| 196 | MBLUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.2% | -3.2% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 197 | ALLOUSDT | 03-25T15:31 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +3.2% | -15.8% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 198 | DOGEUSDT | 03-23T18:30 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +3.1% | -7.3% | OPEN | Trend(ADX=38,DI=26), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 199 | VELODROMEUSDT | 03-24T00:02 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +3.0% | -9.5% | LOSE | Trend(ADX=50,DI=7), Mom(MACD), Time(Vol=0.3x) |
| 200 | SUSHIUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +3.0% | -7.8% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 201 | ALPINEUSDT | 03-25T18:31 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +2.9% | -5.6% | OPEN | Trend(ADX=25,DI=32), Struct(FVG), Mom(MACD) |
| 202 | ACMUSDT | 03-22T23:03 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +2.9% | -5.3% | OPEN | Trend(ADX=49,DI=24), Struct(FVG), Mom(MACD) |
| 203 | DOGEUSDT | 03-24T08:01 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.9% | -7.6% | OPEN | Trend(ADX=22,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 204 | BNSOLUSDT | 03-23T23:44 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.8% | -13.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 205 | SXPUSDT | 03-26T06:33 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +2.7% | -35.6% | LOSE | Trend(ADX=29,DI=21), Struct(FVG), Mom(MACD) |
| 206 | WUSDT | 03-30T04:02 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.7% | +1.3% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 207 | VETUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +2.6% | -9.3% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 208 | INITUSDT | 03-25T00:02 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.6% | -10.9% | LOSE | Trend(ADX=27,DI=35), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 209 | BNSOLUSDT | 03-24T00:02 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.6% | -13.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 210 | ZKUSDT | 03-17T11:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.6% | -18.7% | LOSE | Trend(ADX=40,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 211 | KAIAUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.6% | -13.0% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 212 | POLYXUSDT | 03-25T07:52 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +2.6% | -8.6% | LOSE | Trend(ADX=40,DI=32), Mom(MACD), Time(Vol=0.1x) |
| 213 | TRXUSDT | 03-27T08:15 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +2.6% | -2.8% | OPEN | Trend(ADX=23,DI=23), Struct(FVG), Mom(MACD) |
| 214 | PUNDIXUSDT | 03-17T11:02 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +2.5% | -8.2% | LOSE | Trend(ADX=38,DI=21), Struct(FVG), Mom(MACD) |
| 215 | TIAUSDT | 03-24T20:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.5% | -14.2% | LOSE | Trend(ADX=42,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 216 | ACHUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +2.5% | -10.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 217 | ENJUSDT | 03-26T20:02 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +2.5% | -15.8% | LOSE | Trend(ADX=37,DI=26), Struct(OB), Mom(MACD) |
| 218 | GASUSDT | 03-25T15:31 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +2.5% | -7.5% | OPEN | Trend(ADX=41,DI=30), Mom(MACD), Time(Vol=0.2x) |
| 219 | 1MBABYDOGEUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +2.5% | -11.1% | LOSE | Trend(ADX=21,DI=28), Struct(OB), Mom(MACD) |
| 220 | BANANAUSDT | 03-30T00:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.4% | +0.3% | OPEN | Trend(ADX=26,DI=21), Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 221 | DCRUSDT | 03-26T07:45 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.4% | -11.5% | LOSE | Trend(ADX=48,DI=-7), Struct(OB), Mom(MACD), Time(Vol=0.7x) |
| 222 | AVAXUSDT | 03-24T07:15 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.4% | -12.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 223 | SUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +2.4% | -11.9% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 224 | RUNEUSDT | 03-23T18:30 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.4% | -7.7% | OPEN | Trend(ADX=41,DI=15), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 225 | HBARUSDT | 03-24T20:32 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +2.4% | -8.2% | LOSE | Trend(ADX=23,DI=24), Mom(MACD), Time(Vol=0.5x) |
| 226 | POLYXUSDT | 03-25T08:16 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +2.4% | -7.0% | OPEN | Trend(ADX=41,DI=27), Mom(MACD), Time(Vol=0.2x) |
| 227 | ORDIUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.4% | -13.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 228 | BOMEUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.4% | -15.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 229 | LTCUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.4% | -5.9% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 230 | VELODROMEUSDT | 03-24T07:15 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.3% | -10.1% | LOSE | Trend(ADX=47,DI=6), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 231 | AUCTIONUSDT | 03-23T11:31 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +2.3% | -10.2% | LOSE | Trend(ADX=18,DI=37), Struct(FVG), Time(Vol=0.7x) |
| 232 | LAZIOUSDT | 03-26T07:45 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +2.3% | -7.0% | OPEN | Trend(ADX=38,DI=38), Mom(MACD), Time(Vol=0.5x) |
| 233 | SOLUSDT | 03-23T23:44 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.3% | -13.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 234 | BNSOLUSDT | 03-24T15:36 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.3% | -13.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 235 | BROCCOLI714USDT | 03-23T11:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.2% | -14.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 236 | FFUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +2.2% | -3.6% | OPEN | Trend(ADX=31,DI=42), Struct(FVG), Mom(MACD) |
| 237 | SOLUSDT | 03-24T00:02 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.2% | -13.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 238 | ALPINEUSDT | 03-25T20:00 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +2.2% | -6.3% | OPEN | Trend(ADX=31,DI=21), Struct(FVG), Mom(MACD) |
| 239 | PARTIUSDT | 03-27T08:45 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +2.2% | -17.5% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 240 | ETHUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +2.1% | -9.9% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 241 | STEEMUSDT | 03-29T08:01 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +2.1% | -4.1% | OPEN | Trend(ADX=21,DI=30), Mom(MACD), Time(Vol=0.1x) |
| 242 | BTCUSDT | 03-24T07:15 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.1% | -7.9% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 243 | BROCCOLI714USDT | 03-23T04:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +2.1% | -14.7% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 244 | AVAXUSDT | 03-24T08:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +2.1% | -12.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 245 | ETCUSDT | 03-24T20:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +2.1% | -10.2% | LOSE | Trend(ADX=15,DI=25), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 246 | ALCXUSDT | 03-30T04:02 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +2.0% | -1.6% | OPEN | Trend(ADX=35,DI=30), Mom(MACD), Time(Vol=0.7x) |
| 247 | ALGOUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.9% | -9.2% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 248 | NEARUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +1.9% | -13.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 249 | STRKUSDT | 03-24T20:32 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.9% | -12.1% | LOSE | Trend(ADX=19,DI=23), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 250 | SUSHIUSDT | 03-23T14:31 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +1.9% | -8.8% | LOSE | Trend(ADX=35,DI=22), Struct(FVG), Mom(MACD) |
| 251 | VELODROMEUSDT | 03-23T23:44 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.8% | -10.5% | LOSE | Trend(ADX=52,DI=8), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 252 | SANDUSDT | 03-24T20:32 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.8% | -14.1% | LOSE | Trend(ADX=18,DI=21), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 253 | INJUSDT | 03-28T16:02 | 7/10 | A | ✅ | ✅ | ❌ | ✅ | +1.8% | -6.2% | OPEN | Trend(ADX=26,DI=27), Struct(FVG), Time(Vol=0.7x) |
| 254 | AXLUSDT | 03-25T04:00 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +1.7% | -14.7% | LOSE | Trend(ADX=29,DI=42), Struct(OB), Mom(MACD) |
| 255 | LAZIOUSDT | 03-26T00:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +1.7% | -7.6% | OPEN | Trend(ADX=36,DI=41), Mom(MACD), Time(Vol=0.3x) |
| 256 | SPELLUSDT | 03-17T19:33 | 10/10 | A | ✅ | ❌ | ✅ | ✅ | +1.6% | -13.3% | LOSE | Trend(ADX=58,DI=35), Mom(MACD), Time(Vol=0.7x) |
| 257 | ANIMEUSDT | 03-21T13:33 | 10/10 | A | ✅ | ❌ | ✅ | ✅ | +1.6% | -17.3% | LOSE | Trend(ADX=34,DI=33), Mom(MACD), Time(Vol=0.7x) |
| 258 | BIFIUSDT | 03-30T09:01 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +1.6% | +0.5% | OPEN | Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 259 | BIFIUSDT | 03-30T04:02 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +1.6% | -1.2% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 260 | SUIUSDT | 03-23T18:30 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.5% | -14.7% | LOSE | Trend(ADX=41,DI=22), Struct(OB), Mom(MACD), Time(Vol=0.5x) |
| 261 | NMRUSDT | 03-28T08:26 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +1.5% | -6.0% | OPEN | Trend(ADX=28,DI=23), Struct(FVG), Time(Vol=0.3x) |
| 262 | TSTUSDT | 03-23T04:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +1.5% | -18.9% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 263 | FFUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.5% | -4.3% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 264 | NOMUSDT | 03-30T08:57 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +1.4% | -9.2% | LOSE | Trend(ADX=35,DI=23), Mom(MACD), Time(Vol=0.8x) |
| 265 | NEOUSDT | 03-30T09:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +1.4% | +0.7% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 266 | OGNUSDT | 03-30T04:02 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +1.4% | -2.7% | OPEN | Trend(ADX=24,DI=26), Mom(MACD), Time(Vol=0.3x) |
| 267 | 1MBABYDOGEUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.4% | -12.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 268 | DCRUSDT | 03-26T09:36 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | +1.4% | -11.7% | LOSE | Trend(ADX=46,DI=-8), Mom(MACD), Time(Vol=0.6x) |
| 269 | RADUSDT | 03-29T21:58 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | +1.4% | -1.4% | OPEN | Trend(ADX=42,DI=18), Mom(MACD), Time(Vol=0.5x) |
| 270 | ALLOUSDT | 03-25T00:02 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.4% | -17.2% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 271 | DENTUSDT | 03-25T08:16 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +1.4% | -18.2% | LOSE | Trend(ADX=29,DI=25), Struct(FVG), Mom(MACD) |
| 272 | BTCUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +1.3% | -8.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 273 | ICPUSDT | 03-24T20:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.2% | -10.8% | LOSE | Trend(ADX=25,DI=25), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 274 | TURTLEUSDT | 03-28T12:32 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +1.2% | -4.7% | OPEN | Trend(ADX=18,DI=21), Struct(OB), Mom(MACD) |
| 275 | JASMYUSDT | 03-23T18:30 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +1.2% | -9.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 276 | EGLDUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.2% | -10.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 277 | WUSDT | 03-23T11:31 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | +1.2% | -14.9% | LOSE | Trend(ADX=21,DI=24), Struct(OB), Time(Vol=0.4x) |
| 278 | KAVAUSDT | 03-28T03:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +1.2% | -7.7% | OPEN | Trend(ADX=33,DI=29), Mom(MACD), Time(Vol=0.1x) |
| 279 | VELODROMEUSDT | 03-24T08:01 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.1% | -11.2% | LOSE | Trend(ADX=45,DI=6), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 280 | BIFIUSDT | 03-29T21:58 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +1.1% | -5.7% | OPEN | Trend(ADX=26,DI=21), Struct(FVG), Mom(MACD) |
| 281 | GASUSDT | 03-25T07:52 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.1% | -8.7% | LOSE | Trend(ADX=38,DI=39), Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 282 | AUCTIONUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +1.0% | -10.6% | LOSE | Trend(ADX=28,DI=24), Struct(FVG), Mom(MACD) |
| 283 | MOVEUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.0% | -13.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 284 | RESOLVUSDT | 03-30T04:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +1.0% | -3.0% | OPEN | Trend(ADX=22,DI=20), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 285 | ALLOUSDT | 03-25T16:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +1.0% | -16.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 286 | NEIROUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +1.0% | -18.2% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 287 | WAXPUSDT | 03-23T23:44 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +0.9% | -17.3% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.1x) |
| 288 | PNUTUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.9% | -15.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 289 | NEOUSDT | 03-30T04:02 | 10/10 | A | ✅ | ✅ | ✅ | ❌ | +0.9% | -1.1% | OPEN | Trend(ADX=28,DI=21), Struct(FVG), Mom(MACD) |
| 290 | SENTUSDT | 03-30T09:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.9% | -0.8% | OPEN | Trend(ADX=45,DI=15), Struct(OB), Mom(MACD), Time(Vol=0.7x) |
| 291 | AUCTIONUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.8% | -10.8% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 292 | PARTIUSDT | 03-27T12:00 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.7% | -17.3% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 293 | USUALUSDT | 03-30T09:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +0.6% | -3.8% | OPEN | Trend(ADX=46,DI=24), Struct(FVG), Mom(MACD) |
| 294 | CVCUSDT | 03-25T08:16 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | +0.5% | -12.8% | LOSE | Trend(ADX=42,DI=37), Mom(MACD), Time(Vol=0.2x) |
| 295 | HEMIUSDT | 03-29T12:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.5% | -8.5% | LOSE | Trend(ADX=47,DI=15), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 296 | TNSRUSDT | 03-23T18:30 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +0.5% | -12.9% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 297 | HOMEUSDT | 03-23T18:30 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +0.5% | -15.8% | LOSE | Trend(ADX=29,DI=21), Struct(FVG), Mom(MACD) |
| 298 | FLOWUSDT | 03-18T06:03 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | +0.4% | -19.7% | LOSE | Trend(ADX=52,DI=-18), Struct(FVG), Time(Vol=0.7x) |
| 299 | ZECUSDT | 03-25T15:31 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.4% | -12.6% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 300 | SEIUSDT | 03-30T09:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +0.4% | -0.6% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 301 | SNXUSDT | 03-24T20:32 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.3% | -10.9% | LOSE | Trend(ADX=23,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 302 | TUTUSDT | 03-23T18:30 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.3% | -20.0% | LOSE | Trend(ADX=32,DI=22), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 303 | BANANAUSDT | 03-30T09:01 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | +0.3% | -0.6% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 304 | EDENUSDT | 03-23T12:31 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +0.3% | -24.6% | LOSE | Trend(ADX=23,DI=31), Struct(FVG), Mom(MACD) |
| 305 | ADXUSDT | 03-23T18:30 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.3% | -10.4% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 306 | FIOUSDT | 03-18T02:33 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | +0.2% | -25.5% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 307 | ZKCUSDT | 03-25T20:00 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | +0.2% | -18.1% | LOSE | Trend(ADX=34,DI=40), Struct(FVG), Mom(MACD) |
| 308 | GIGGLEUSDT | 03-29T21:58 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.2% | -2.1% | OPEN | Trend(ADX=30,DI=20), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 309 | FFUSDT | 03-24T20:02 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.2% | -4.0% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 310 | TUSDT | 03-25T00:32 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.1% | -13.4% | LOSE | Trend(ADX=18,DI=25), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 311 | TURBOUSDT | 03-28T12:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | +0.1% | -9.6% | LOSE | Trend(ADX=45,DI=33), Struct(OB), Mom(MACD) |
| 312 | BIFIUSDT | 03-30T00:02 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | +0.1% | -4.3% | OPEN | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 313 | ALTUSDT | 03-23T13:31 | 9/10 | A | ✅ | ✅ | ❌ | ✅ | +0.0% | -15.8% | LOSE | Trend(ADX=30,DI=23), Struct(FVG), Time(Vol=0.6x) |
| 314 | POLYXUSDT | 03-25T00:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | +0.0% | -10.8% | LOSE | Trend(ADX=38,DI=31), Struct(FVG), Mom(MACD), Time(Vol=0.3x) |
| 315 | ZECUSDT | 03-26T00:01 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | -0.1% | -10.3% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 316 | GIGGLEUSDT | 03-21T04:33 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | -0.1% | -16.9% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.6x) |
| 317 | ZECUSDT | 03-25T20:00 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | -0.1% | -11.4% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 318 | HEMIUSDT | 03-29T08:01 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | -0.2% | -9.1% | LOSE | Trend(ADX=48,DI=17), Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 319 | BANANAUSDT | 03-30T04:02 | 8/10 | A+ | ✅ | ✅ | ✅ | ✅ | -0.3% | -1.8% | OPEN | Trend(ADX=28,DI=20), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 320 | INITUSDT | 03-25T07:52 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | -0.3% | -12.9% | LOSE | Trend(ADX=31,DI=32), Struct(OB), Mom(MACD), Time(Vol=0.3x) |
| 321 | AUSDT | 03-28T08:26 | 8/10 | A | ✅ | ✅ | ❌ | ✅ | -0.4% | -8.0% | LOSE | Trend(ADX=33,DI=29), Struct(FVG), Time(Vol=0.7x) |
| 322 | CVCUSDT | 03-25T15:31 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | -0.4% | -13.1% | LOSE | Trend(ADX=45,DI=35), Mom(MACD), Time(Vol=0.3x) |
| 323 | WAXPUSDT | 03-24T07:15 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -0.5% | -16.3% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 324 | ATOMUSDT | 03-23T12:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | -0.6% | -11.6% | LOSE | Trend(ADX=28,DI=27), Struct(FVG), Mom(MACD) |
| 325 | DYMUSDT | 03-26T14:08 | 9/10 | A | ❌ | ✅ | ✅ | ✅ | -0.7% | -15.8% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.8x) |
| 326 | WAXPUSDT | 03-23T18:30 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | -0.8% | -19.2% | LOSE | Trend(ADX=31,DI=23), Struct(FVG), Mom(MACD), Time(Vol=0.5x) |
| 327 | BANANAUSDT | 03-29T21:58 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | -0.9% | -3.8% | OPEN | Trend(ADX=28,DI=45), Struct(FVG), Mom(MACD) |
| 328 | ALCXUSDT | 03-30T09:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | -1.0% | -3.3% | OPEN | Trend(ADX=38,DI=30), Mom(MACD), Time(Vol=0.2x) |
| 329 | KAVAUSDT | 03-27T08:45 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | -1.0% | -11.7% | LOSE | Trend(ADX=26,DI=53), Struct(FVG), Mom(MACD) |
| 330 | ATMUSDT | 03-29T09:31 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | -1.2% | -4.9% | OPEN | Trend(ADX=30,DI=39), Struct(FVG), Mom(MACD), Time(Vol=0.4x) |
| 331 | SXPUSDT | 03-25T13:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | -1.2% | -42.7% | LOSE | Trend(ADX=27,DI=39), Struct(OB), Mom(MACD) |
| 332 | AXLUSDT | 03-25T08:16 | 7/10 | A+ | ✅ | ✅ | ✅ | ✅ | -1.5% | -15.7% | LOSE | Trend(ADX=32,DI=24), Struct(FVG), Mom(MACD), Time(Vol=0.8x) |
| 333 | DCRUSDT | 03-26T00:01 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | -1.5% | -14.9% | LOSE | Trend(ADX=50,DI=-2), Struct(FVG), Mom(MACD) |
| 334 | FFUSDT | 03-30T04:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | -1.6% | -3.1% | OPEN | Trend(ADX=19,DI=23), Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 335 | GASUSDT | 03-25T00:02 | 9/10 | A+ | ✅ | ✅ | ✅ | ✅ | -1.6% | -11.2% | LOSE | Trend(ADX=36,DI=36), Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 336 | IQUSDT | 03-24T15:36 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | -1.6% | -18.4% | LOSE | Trend(ADX=27,DI=25), Mom(MACD), Time(Vol=0.4x) |
| 337 | WOOUSDT | 03-26T07:45 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -1.6% | -15.4% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.7x) |
| 338 | WOOUSDT | 03-26T08:01 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -1.7% | -14.0% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.6x) |
| 339 | PEOPLEUSDT | 03-28T23:18 | 8/10 | A | ❌ | ✅ | ✅ | ✅ | -1.7% | -8.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 340 | WAXPUSDT | 03-24T00:02 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -1.7% | -18.2% | LOSE | Struct(OB), Mom(MACD), Time(Vol=0.2x) |
| 341 | TUTUSDT | 03-24T00:02 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -1.8% | -19.1% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.1x) |
| 342 | CVCUSDT | 03-25T07:52 | 10/10 | A | ✅ | ❌ | ✅ | ✅ | -1.9% | -15.8% | LOSE | Trend(ADX=40,DI=41), Mom(MACD), Time(Vol=0.3x) |
| 343 | FILUSDT | 03-21T19:57 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -2.5% | -16.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.7x) |
| 344 | SOPHUSDT | 03-29T22:01 | 9/10 | A | ✅ | ✅ | ✅ | ❌ | -2.5% | -6.6% | OPEN | Trend(ADX=30,DI=69), Struct(FVG), Mom(MACD) |
| 345 | TURBOUSDT | 03-28T23:18 | 7/10 | A | ❌ | ✅ | ✅ | ✅ | -2.5% | -8.0% | LOSE | Struct(FVG), Mom(MACD), Time(Vol=0.2x) |
| 346 | OGNUSDT | 03-30T09:01 | 8/10 | A | ✅ | ❌ | ✅ | ✅ | -2.7% | -4.1% | OPEN | Trend(ADX=26,DI=30), Mom(MACD), Time(Vol=0.4x) |
| 347 | JASMYUSDT | 03-27T08:45 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | -3.2% | -9.2% | LOSE | Trend(ADX=36,DI=22), Struct(FVG), Mom(MACD) |
| 348 | ZKCUSDT | 03-26T00:01 | 9/10 | A | ✅ | ❌ | ✅ | ✅ | -4.3% | -17.7% | LOSE | Trend(ADX=31,DI=34), Mom(MACD), Time(Vol=0.4x) |
| 349 | SXPUSDT | 03-18T00:03 | 8/10 | A | ✅ | ✅ | ✅ | ❌ | -5.0% | -47.5% | LOSE | Trend(ADX=45,DI=-17), Struct(OB), Mom(MACD) |
| 350 | PIXELUSDT | 03-27T20:01 | 7/10 | A | ✅ | ❌ | ✅ | ✅ | -6.7% | -22.7% | LOSE | Trend(ADX=24,DI=26), Mom(MACD), Time(Vol=0.7x) |

## 5. Opportunites manquees — Grade B/C avec PnL Max >= +14%

| # | Pair | Date | Score | Grade | Axes | PnL Max | Details |
|---|------|------|-------|-------|------|---------|---------|
| 1 | STOUSDT | 03-25T07:52 | 9/10 | B | 2/4 | +121.2% | Struct(FVG), Time(Vol=0.3x) |
| 2 | STOUSDT | 03-25T08:16 | 9/10 | C | 1/4 | +121.2% | Struct(FVG) |
| 3 | STOUSDT | 03-25T16:01 | 9/10 | B | 2/4 | +115.8% | Trend(ADX=27,DI=34), Struct(FVG) |
| 4 | CUSDT | 03-23T12:01 | 7/10 | C | 1/4 | +107.1% | Struct(OB) |
| 5 | STOUSDT | 03-25T20:00 | 9/10 | B | 2/4 | +104.8% | Trend(ADX=30,DI=21), Struct(FVG) |
| 6 | GUNUSDT | 03-16T23:03 | 9/10 | C | 1/4 | +84.4% | Mom(MACD) |
| 7 | NOMUSDT | 03-23T18:30 | 8/10 | B | 2/4 | +81.9% | Mom(MACD), Time(Vol=0.6x) |
| 8 | NOMUSDT | 03-23T12:01 | 9/10 | B | 2/4 | +78.9% | Trend(ADX=25,DI=38), Mom(MACD) |
| 9 | NOMUSDT | 03-28T12:32 | 9/10 | B | 2/4 | +78.9% | Trend(ADX=31,DI=48), Mom(MACD) |
| 10 | KATUSDT | 03-25T23:31 | 7/10 | B | 2/4 | +76.5% | Struct(FVG), Time(Vol=0.5x) |
| 11 | KATUSDT | 03-26T00:01 | 8/10 | C | 1/4 | +74.7% | Struct(FVG) |
| 12 | BANANAS31USDT | 03-21T04:33 | 8/10 | C | 1/4 | +72.7% | Struct(OB) |
| 13 | CUSDT | 03-25T07:52 | 9/10 | B | 2/4 | +72.4% | Trend(ADX=22,DI=35), Mom(MACD) |
| 14 | CUSDT | 03-25T00:02 | 9/10 | B | 2/4 | +71.0% | Trend(ADX=19,DI=41), Mom(MACD) |
| 15 | GUNUSDT | 03-17T04:03 | 7/10 | C | 1/4 | +68.4% | Mom(MACD) |
| 16 | CUSDT | 03-25T12:55 | 7/10 | B | 2/4 | +64.8% | Struct(FVG), Mom(MACD) |
| 17 | STGUSDT | 03-23T12:01 | 9/10 | B | 2/4 | +61.8% | Struct(OB), Mom(MACD) |
| 18 | RDNTUSDT | 03-19T09:33 | 9/10 | C | 1/4 | +59.9% | Time(Vol=0.7x) |
| 19 | PROVEUSDT | 03-23T18:30 | 8/10 | C | 1/4 | +54.1% | Time(Vol=0.5x) |
| 20 | PROVEUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +52.6% | Trend(ADX=34,DI=21) |
| 21 | ONTUSDT | 03-28T07:13 | 9/10 | C | 1/4 | +50.5% | Trend(ADX=34,DI=47) |
| 22 | DEXEUSDT | 03-16T15:03 | 8/10 | C | 0/4 | +49.5% |  |
| 23 | ONTUSDT | 03-28T12:01 | 8/10 | B | 2/4 | +48.8% | Trend(ADX=51,DI=38), Mom(MACD) |
| 24 | KNCUSDT | 03-24T08:01 | 9/10 | B | 2/4 | +47.4% | Mom(MACD), Time(Vol=0.2x) |
| 25 | KNCUSDT | 03-24T07:15 | 9/10 | B | 2/4 | +47.0% | Mom(MACD), Time(Vol=0.2x) |
| 26 | KNCUSDT | 03-23T14:46 | 8/10 | B | 2/4 | +45.1% | Struct(FVG), Mom(MACD) |
| 27 | ONTUSDT | 03-28T08:26 | 9/10 | B | 2/4 | +44.6% | Trend(ADX=37,DI=51), Struct(OB) |
| 28 | KNCUSDT | 03-26T11:02 | 9/10 | B | 2/4 | +44.6% | Trend(ADX=26,DI=36), Mom(MACD) |
| 29 | ANKRUSDT | 03-17T09:33 | 10/10 | B | 2/4 | +43.9% | Struct(FVG), Mom(MACD) |
| 30 | ONTUSDT | 03-28T11:24 | 9/10 | B | 2/4 | +43.4% | Trend(ADX=45,DI=43), Struct(OB) |
| 31 | PROVEUSDT | 03-25T21:45 | 10/10 | C | 1/4 | +41.3% | Mom(MACD) |
| 32 | DEXEUSDT | 03-17T09:03 | 10/10 | C | 0/4 | +40.5% |  |
| 33 | PHAUSDT | 03-17T07:03 | 9/10 | C | 1/4 | +39.9% | Struct(FVG) |
| 34 | CFGUSDT | 03-23T12:01 | 8/10 | C | 1/4 | +39.8% | Trend(ADX=28,DI=22) |
| 35 | CFGUSDT | 03-23T18:30 | 8/10 | C | 1/4 | +38.7% | Struct(FVG) |
| 36 | CETUSUSDT | 03-21T11:03 | 9/10 | B | 2/4 | +35.5% | Trend(ADX=44,DI=29), Struct(FVG) |
| 37 | SIGNUSDT | 03-16T14:03 | 7/10 | C | 0/4 | +34.9% |  |
| 38 | IDEXUSDT | 03-28T11:24 | 9/10 | C | 1/4 | +34.9% | Mom(MACD) |
| 39 | NTRNUSDT | 03-19T09:33 | 7/10 | B | 2/4 | +33.9% | Trend(ADX=59,DI=-31), Time(Vol=0.3x) |
| 40 | IDEXUSDT | 03-28T12:01 | 9/10 | B | 2/4 | +32.4% | Mom(MACD), Time(Vol=0.5x) |
| 41 | CATIUSDT | 03-23T18:30 | 9/10 | B | 2/4 | +29.7% | Trend(ADX=30,DI=24), Mom(MACD) |
| 42 | CATIUSDT | 03-23T23:44 | 8/10 | B | 2/4 | +29.1% | Mom(MACD), Time(Vol=0.3x) |
| 43 | CATIUSDT | 03-24T00:02 | 8/10 | B | 2/4 | +29.1% | Mom(MACD), Time(Vol=0.2x) |
| 44 | CATIUSDT | 03-24T15:36 | 8/10 | B | 2/4 | +27.1% | Struct(FVG), Mom(MACD) |
| 45 | CHZUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +26.5% | Mom(MACD) |
| 46 | COSUSDT | 03-25T12:00 | 7/10 | C | 1/4 | +26.5% | Struct(FVG) |
| 47 | CATIUSDT | 03-23T15:46 | 10/10 | B | 2/4 | +26.5% | Trend(ADX=25,DI=37), Mom(MACD) |
| 48 | INITUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +26.2% | Mom(MACD) |
| 49 | DUSKUSDT | 03-23T12:01 | 9/10 | B | 2/4 | +26.0% | Trend(ADX=33,DI=30), Mom(MACD) |
| 50 | CHZUSDT | 03-23T18:30 | 8/10 | B | 2/4 | +26.0% | Struct(FVG), Mom(MACD) |
| 51 | CATIUSDT | 03-24T07:15 | 8/10 | B | 2/4 | +25.9% | Struct(FVG), Mom(MACD) |
| 52 | JTOUSDT | 03-24T15:36 | 9/10 | B | 2/4 | +25.8% | Mom(MACD), Time(Vol=0.7x) |
| 53 | JTOUSDT | 03-24T16:02 | 9/10 | B | 2/4 | +25.7% | Mom(MACD), Time(Vol=0.2x) |
| 54 | FETUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +25.6% | Trend(ADX=23,DI=25) |
| 55 | CUSDT | 03-27T09:00 | 8/10 | B | 2/4 | +24.7% | Trend(ADX=46,DI=35), Mom(MACD) |
| 56 | PIXELUSDT | 03-27T00:00 | 9/10 | B | 2/4 | +24.6% | Trend(ADX=30,DI=24), Struct(FVG) |
| 57 | COSUSDT | 03-25T10:30 | 7/10 | B | 2/4 | +24.5% | Trend(ADX=23,DI=25), Time(Vol=0.7x) |
| 58 | CATIUSDT | 03-24T08:01 | 8/10 | B | 2/4 | +24.3% | Struct(FVG), Mom(MACD) |
| 59 | JTOUSDT | 03-23T18:30 | 8/10 | B | 2/4 | +24.2% | Trend(ADX=23,DI=23), Mom(MACD) |
| 60 | FETUSDT | 03-23T18:30 | 7/10 | B | 2/4 | +23.6% | Struct(FVG), Time(Vol=0.6x) |
| 61 | MBOXUSDT | 03-17T02:03 | 10/10 | C | 1/4 | +23.5% | Struct(OB) |
| 62 | INITUSDT | 03-23T18:30 | 9/10 | B | 2/4 | +23.0% | Struct(FVG), Mom(MACD) |
| 63 | KITEUSDT | 03-18T16:47 | 9/10 | C | 0/4 | +22.7% |  |
| 64 | GASUSDT | 03-23T12:01 | 8/10 | C | 0/4 | +22.5% |  |
| 65 | GASUSDT | 03-23T11:46 | 8/10 | C | 0/4 | +22.1% |  |
| 66 | POLYXUSDT | 03-23T12:01 | 9/10 | C | 0/4 | +21.6% |  |
| 67 | GASUSDT | 03-23T18:30 | 9/10 | B | 2/4 | +21.6% | Struct(FVG), Time(Vol=0.4x) |
| 68 | CATIUSDT | 03-27T14:45 | 9/10 | B | 2/4 | +21.1% | Trend(ADX=29,DI=21), Struct(FVG) |
| 69 | BATUSDT | 03-23T11:31 | 9/10 | B | 2/4 | +21.1% | Trend(ADX=26,DI=25), Time(Vol=0.2x) |
| 70 | BATUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +20.8% | Mom(MACD) |
| 71 | POLYXUSDT | 03-23T18:30 | 8/10 | B | 2/4 | +20.6% | Struct(FVG), Time(Vol=0.2x) |
| 72 | APTUSDT | 03-23T12:01 | 8/10 | B | 2/4 | +19.6% | Trend(ADX=40,DI=16), Struct(OB) |
| 73 | SANTOSUSDT | 03-25T20:00 | 9/10 | C | 1/4 | +19.4% | Mom(MACD) |
| 74 | PIXELUSDT | 03-25T12:55 | 8/10 | B | 2/4 | +19.2% | Struct(OB), Mom(MACD) |
| 75 | APTUSDT | 03-23T01:01 | 8/10 | B | 2/4 | +19.2% | Trend(ADX=43,DI=5), Struct(OB) |
| 76 | ZBTUSDT | 03-28T02:54 | 9/10 | C | 0/4 | +19.1% |  |
| 77 | SOPHUSDT | 03-19T01:02 | 8/10 | B | 2/4 | +19.0% | Trend(ADX=42,DI=14), Struct(OB) |
| 78 | SENTUSDT | 03-29T10:01 | 9/10 | C | 1/4 | +18.8% | Trend(ADX=24,DI=42) |
| 79 | HUMAUSDT | 03-16T13:03 | 7/10 | C | 1/4 | +18.6% | Struct(OB) |
| 80 | APTUSDT | 03-23T04:01 | 8/10 | B | 2/4 | +18.6% | Struct(OB), Time(Vol=0.6x) |
| 81 | OPENUSDT | 03-22T23:03 | 8/10 | C | 1/4 | +18.3% | Trend(ADX=39,DI=40) |
| 82 | ENAUSDT | 03-23T18:30 | 7/10 | C | 0/4 | +18.2% |  |
| 83 | KAVAUSDT | 03-23T16:02 | 9/10 | C | 1/4 | +17.6% | Mom(MACD) |
| 84 | FETUSDT | 03-20T22:03 | 7/10 | C | 1/4 | +17.4% | Struct(OB) |
| 85 | NIGHTUSDT | 03-27T20:01 | 8/10 | B | 2/4 | +17.3% | Struct(FVG), Time(Vol=0.3x) |
| 86 | FORTHUSDT | 03-25T16:01 | 8/10 | C | 1/4 | +17.1% | Mom(MACD) |
| 87 | DUSKUSDT | 03-16T20:32 | 7/10 | B | 2/4 | +17.0% | Struct(FVG), Time(Vol=0.8x) |
| 88 | A2ZUSDT | 03-28T08:26 | 8/10 | B | 2/4 | +17.0% | Struct(FVG), Mom(MACD) |
| 89 | KAVAUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +16.9% | Mom(MACD) |
| 90 | SANTOSUSDT | 03-25T18:01 | 10/10 | B | 2/4 | +16.8% | Trend(ADX=31,DI=45), Mom(MACD) |
| 91 | GUSDT | 03-23T04:01 | 8/10 | B | 2/4 | +16.5% | Struct(FVG), Time(Vol=0.6x) |
| 92 | RENDERUSDT | 03-23T12:01 | 9/10 | B | 2/4 | +16.4% | Trend(ADX=31,DI=22), Struct(FVG) |
| 93 | COSUSDT | 03-23T00:01 | 9/10 | C | 1/4 | +16.3% | Struct(FVG) |
| 94 | KAVAUSDT | 03-23T11:31 | 9/10 | B | 2/4 | +16.2% | Trend(ADX=12,DI=26), Time(Vol=0.7x) |
| 95 | AXLUSDT | 03-23T18:30 | 8/10 | C | 1/4 | +16.2% | Time(Vol=0.5x) |
| 96 | CHRUSDT | 03-23T12:01 | 9/10 | C | 0/4 | +15.9% |  |
| 97 | ENJUSDT | 03-25T04:00 | 9/10 | C | 1/4 | +15.9% | Struct(OB) |
| 98 | CUSDT | 03-29T04:01 | 8/10 | C | 1/4 | +15.7% | Time(Vol=0.7x) |
| 99 | WAXPUSDT | 03-23T04:01 | 8/10 | B | 2/4 | +15.6% | Trend(ADX=44,DI=19), Struct(FVG) |
| 100 | NIGHTUSDT | 03-27T17:31 | 7/10 | C | 1/4 | +15.6% | Struct(FVG) |
| 101 | ONDOUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +15.4% | Trend(ADX=38,DI=20) |
| 102 | ENJUSDT | 03-25T01:02 | 9/10 | B | 2/4 | +15.2% | Trend(ADX=12,DI=20), Struct(OB) |
| 103 | 1000SATSUSDT | 03-23T12:01 | 9/10 | B | 2/4 | +15.2% | Trend(ADX=36,DI=23), Struct(OB) |
| 104 | GUSDT | 03-23T01:31 | 8/10 | C | 1/4 | +15.0% | Trend(ADX=37,DI=21) |
| 105 | AXLUSDT | 03-23T12:01 | 9/10 | C | 0/4 | +15.0% |  |
| 106 | HOOKUSDT | 03-20T15:32 | 7/10 | B | 2/4 | +15.0% | Struct(FVG), Time(Vol=0.4x) |
| 107 | ZBTUSDT | 03-27T20:01 | 9/10 | B | 2/4 | +14.9% | Trend(ADX=27,DI=22), Struct(FVG) |
| 108 | MEMEUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +14.9% | Mom(MACD) |
| 109 | STEEMUSDT | 03-28T23:18 | 7/10 | B | 2/4 | +14.9% | Mom(MACD), Time(Vol=0.1x) |
| 110 | RDNTUSDT | 03-25T10:00 | 7/10 | C | 1/4 | +14.8% | Trend(ADX=29,DI=27) |
| 111 | STEEMUSDT | 03-28T16:02 | 7/10 | B | 2/4 | +14.8% | Mom(MACD), Time(Vol=0.8x) |
| 112 | ENAUSDT | 03-23T12:01 | 9/10 | C | 0/4 | +14.7% |  |
| 113 | ASRUSDT | 03-23T12:16 | 7/10 | C | 0/4 | +14.5% |  |
| 114 | ZBTUSDT | 03-23T18:30 | 8/10 | C | 1/4 | +14.5% | Time(Vol=0.2x) |
| 115 | DEXEUSDT | 03-25T20:30 | 9/10 | C | 0/4 | +14.5% |  |
| 116 | ONDOUSDT | 03-23T18:30 | 9/10 | B | 2/4 | +14.5% | Struct(FVG), Mom(MACD) |
| 117 | USUALUSDT | 03-29T21:58 | 9/10 | C | 1/4 | +14.5% | Mom(MACD) |
| 118 | APTUSDT | 03-23T18:30 | 9/10 | B | 2/4 | +14.4% | Trend(ADX=37,DI=26), Struct(FVG) |
| 119 | ZBTUSDT | 03-28T11:24 | 8/10 | C | 1/4 | +14.4% | Struct(FVG) |
| 120 | USUALUSDT | 03-30T00:02 | 9/10 | C | 1/4 | +14.4% | Mom(MACD) |
| 121 | CHRUSDT | 03-23T16:46 | 7/10 | B | 2/4 | +14.3% | Struct(FVG), Time(Vol=0.7x) |
| 122 | XAIUSDT | 03-20T17:03 | 10/10 | C | 1/4 | +14.3% | Mom(MACD) |
| 123 | 1000CHEEMSUSDT | 03-23T12:01 | 9/10 | C | 1/4 | +14.2% | Trend(ADX=27,DI=22) |
| 124 | ENJUSDT | 03-27T16:00 | 7/10 | B | 2/4 | +14.1% | Struct(OB), Mom(MACD) |
| 125 | STEEMUSDT | 03-28T11:24 | 8/10 | B | 2/4 | +14.0% | Trend(ADX=40,DI=18), Struct(FVG) |

## 6. Top 30 Performers

| # | Pair | Date | Score | Grade | PnL Max | PnL Min | Outcome |
|---|------|------|-------|-------|---------|---------|---------|
| 1 | STOUSDT | 03-25T07:52 | 9/10 | **B** | **+121.2%** | -4.1% | WIN |
| 2 | STOUSDT | 03-25T08:16 | 9/10 | **C** | **+121.2%** | -4.1% | WIN |
| 3 | STOUSDT | 03-25T16:01 | 9/10 | **B** | **+115.8%** | +3.3% | WIN |
| 4 | CUSDT | 03-23T12:01 | 7/10 | **C** | **+107.1%** | -6.5% | WIN |
| 5 | STOUSDT | 03-25T20:00 | 9/10 | **B** | **+104.8%** | -1.9% | WIN |
| 6 | GUNUSDT | 03-16T23:03 | 9/10 | **C** | **+84.4%** | +2.1% | WIN |
| 7 | NOMUSDT | 03-23T18:30 | 8/10 | **B** | **+81.9%** | -27.3% | WIN |
| 8 | NOMUSDT | 03-23T12:01 | 9/10 | **B** | **+78.9%** | -28.5% | WIN |
| 9 | NOMUSDT | 03-28T12:32 | 9/10 | **B** | **+78.9%** | -6.2% | WIN |
| 10 | KATUSDT | 03-25T23:31 | 7/10 | **B** | **+76.5%** | -1.6% | WIN |
| 11 | KATUSDT | 03-26T00:01 | 8/10 | **C** | **+74.7%** | -2.6% | WIN |
| 12 | CUSDT | 03-25T20:00 | 9/10 | **A+** | **+73.3%** | -4.6% | WIN |
| 13 | BANANAS31USDT | 03-21T04:33 | 8/10 | **C** | **+72.7%** | -3.1% | WIN |
| 14 | CUSDT | 03-25T07:52 | 9/10 | **B** | **+72.4%** | -5.1% | WIN |
| 15 | CUSDT | 03-25T00:02 | 9/10 | **B** | **+71.0%** | -5.9% | WIN |
| 16 | CUSDT | 03-25T08:16 | 9/10 | **A** | **+70.2%** | -6.3% | WIN |
| 17 | GUNUSDT | 03-17T04:03 | 7/10 | **C** | **+68.4%** | -6.7% | WIN |
| 18 | CUSDT | 03-25T12:55 | 7/10 | **B** | **+64.8%** | -9.3% | WIN |
| 19 | CUSDT | 03-25T16:01 | 9/10 | **A+** | **+64.8%** | -9.3% | WIN |
| 20 | ONTUSDT | 03-24T20:02 | 9/10 | **A** | **+63.9%** | -15.8% | WIN |
| 21 | STGUSDT | 03-23T12:01 | 9/10 | **B** | **+61.8%** | -0.6% | WIN |
| 22 | ONTUSDT | 03-29T08:01 | 8/10 | **A+** | **+61.7%** | -3.8% | WIN |
| 23 | RDNTUSDT | 03-19T09:33 | 9/10 | **C** | **+59.9%** | -8.6% | WIN |
| 24 | ONTUSDT | 03-25T00:02 | 9/10 | **A** | **+57.1%** | -19.3% | WIN |
| 25 | ONTUSDT | 03-29T04:01 | 8/10 | **A+** | **+57.1%** | -6.5% | WIN |
| 26 | DUSDT | 03-29T16:02 | 9/10 | **A** | **+56.7%** | -3.7% | WIN |
| 27 | ONTUSDT | 03-28T23:18 | 8/10 | **A+** | **+56.1%** | -7.1% | WIN |
| 28 | ONTUSDT | 03-28T16:02 | 8/10 | **A+** | **+54.3%** | -8.1% | WIN |
| 29 | PROVEUSDT | 03-23T18:30 | 8/10 | **C** | **+54.1%** | -11.8% | WIN |
| 30 | PROVEUSDT | 03-23T12:01 | 9/10 | **C** | **+52.6%** | -12.6% | WIN |

## 7. Resume et Conclusion

### Sans filtre
- **810** trades resolus (247W / 563L)
- Win Rate: **30.5%**
- PnL Total: **-2034.0%**
- Avg/trade: **-2.51%**

### Avec filtre >= Grade A
- **253** trades resolus (81W / 172L)
- Win Rate: **32.0%**
- PnL Total: **-566.0%**
- Avg/trade: **-2.24%**
- Trades evites: **557** (dont **391** pertes)

---
*Genere par backtest_quality_fast.py*
