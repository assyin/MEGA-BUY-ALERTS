# 🔬 Hypothesis Discovery Report

_Generated: 2026-04-27 15:04 UTC_

**Dataset**: agent_memory rows resolved (WIN/LOSE) over last 30 days, joined with alerts table.

## 📊 Baseline

- **N**: 1658 resolved alerts
- **WR**: 61.5% (1019W / 639L)
- **Avg PnL @ close**: +4.43%

_Min N filter_: hypotheses must match ≥30 alerts to be included. p-value via one-sided binomial test (greater than baseline).

## 🎯 User's Custom filter (reference)

- N=24, **WR=75.0%**, lift +13.5pts, avg PnL +8.75%, p-value 0.123

## 🏆 Top 30 single-feature hypotheses (sorted by lift × log(N))

| Rank | Condition | N | W/L | WR | Avg PnL | Lift | p-value |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Range 30m % <= 1.46 | 395 | 321W/74L | 81.3% | +8.15% | +19.8pts | <0.001 ★★★ |
| 2 | Range 30m % <= 1.89 | 492 | 395W/97L | 80.3% | +7.98% | +18.8pts | <0.001 ★★★ |
| 3 | BB 4H width % <= 13.56 | 118 | 101W/17L | 85.6% | +9.27% | +24.1pts | <0.001 ★★★ |
| 4 | Range 30m % <= 1.17 | 297 | 242W/55L | 81.5% | +8.15% | +20.0pts | <0.001 ★★★ |
| 5 | Range 15m % <= 0.75 | 355 | 284W/71L | 80.0% | +7.82% | +18.5pts | <0.001 ★★★ |
| 6 | Range 1h % <= 1.67 | 285 | 230W/55L | 80.7% | +8.05% | +19.2pts | <0.001 ★★★ |
| 7 | Range 1h % <= 1.24 | 190 | 156W/34L | 82.1% | +8.11% | +20.6pts | <0.001 ★★★ |
| 8 | Accum days >= 3.70 | 174 | 142W/32L | 81.6% | +9.08% | +20.1pts | <0.001 ★★★ |
| 9 | Accum hours >= 88.00 | 174 | 142W/32L | 81.6% | +9.08% | +20.1pts | <0.001 ★★★ |
| 10 | Range 30m % <= 0.91 | 198 | 160W/38L | 80.8% | +7.80% | +19.3pts | <0.001 ★★★ |
| 11 | Range 1h % <= 2.13 | 379 | 298W/81L | 78.6% | +7.52% | +17.2pts | <0.001 ★★★ |
| 12 | BB 4H width % <= 8.88 | 59 | 51W/8L | 86.4% | +9.08% | +25.0pts | <0.001 ★★★ |
| 13 | Accum days >= 4.30 | 135 | 111W/24L | 82.2% | +9.54% | +20.8pts | <0.001 ★★★ |
| 14 | Accum hours >= 104.00 | 135 | 111W/24L | 82.2% | +9.54% | +20.8pts | <0.001 ★★★ |
| 15 | Accum days >= 3.20 | 201 | 162W/39L | 80.6% | +8.86% | +19.1pts | <0.001 ★★★ |
| 16 | Accum hours >= 76.00 | 201 | 162W/39L | 80.6% | +8.86% | +19.1pts | <0.001 ★★★ |
| 17 | Range 15m % <= 0.59 | 239 | 191W/48L | 79.9% | +7.63% | +18.5pts | <0.001 ★★★ |
| 18 | BTC dominance <= 56.98 | 190 | 153W/37L | 80.5% | +9.21% | +19.1pts | <0.001 ★★★ |
| 19 | Range 30m % <= 2.51 | 590 | 455W/135L | 77.1% | +7.39% | +15.7pts | <0.001 ★★★ |
| 20 | Range 15m % <= 1.28 | 576 | 442W/134L | 76.7% | +7.31% | +15.3pts | <0.001 ★★★ |
| 21 | BB 4H width % <= 11.78 | 88 | 73W/15L | 83.0% | +8.40% | +21.5pts | <0.001 ★★★ |
| 22 | Range 4h % <= 2.58 | 458 | 352W/106L | 76.9% | +7.61% | +15.4pts | <0.001 ★★★ |
| 23 | Accum days >= 2.70 | 237 | 186W/51L | 78.5% | +8.41% | +17.0pts | <0.001 ★★★ |
| 24 | Accum hours >= 64.00 | 237 | 186W/51L | 78.5% | +8.41% | +17.0pts | <0.001 ★★★ |
| 25 | Range 1h % <= 2.61 | 474 | 362W/112L | 76.4% | +7.30% | +14.9pts | <0.001 ★★★ |
| 26 | ADX move 4h <= 21.68 | 61 | 51W/10L | 83.6% | +8.31% | +22.1pts | <0.001 ★★★ |
| 27 | Body 1h % <= 0.58 | 288 | 223W/65L | 77.4% | +7.60% | +16.0pts | <0.001 ★★★ |
| 28 | Body 30m % <= 0.82 | 495 | 376W/119L | 76.0% | +7.25% | +14.5pts | <0.001 ★★★ |
| 29 | Accum range % <= 8.80 | 103 | 83W/20L | 80.6% | +8.97% | +19.1pts | <0.001 ★★★ |
| 30 | Body 30m % <= 0.39 | 299 | 230W/69L | 76.9% | +7.67% | +15.5pts | <0.001 ★★★ |

## 🤝 Top 30 2-feature combos

| Rank | Condition | N | W/L | WR | Avg PnL | Lift | p-value |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | Range 1h % <= 1.67 AND BTC dominance <= 56.98 | 55 | 53W/2L | 96.4% | +11.59% | +34.9pts | <0.001 ★★★ |
| 2 | Range 30m % <= 1.89 AND Range 4h % <= 2.58 | 247 | 214W/33L | 86.6% | +9.58% | +25.2pts | <0.001 ★★★ |
| 3 | Range 30m % <= 1.46 AND Accum days >= 3.20 | 76 | 71W/5L | 93.4% | +11.80% | +32.0pts | <0.001 ★★★ |
| 4 | Range 30m % <= 1.46 AND Accum hours >= 76.00 | 76 | 71W/5L | 93.4% | +11.80% | +32.0pts | <0.001 ★★★ |
| 5 | Accum days >= 4.30 AND Range 15m % <= 1.28 | 75 | 70W/5L | 93.3% | +12.10% | +31.9pts | <0.001 ★★★ |
| 6 | Accum hours >= 104.00 AND Range 15m % <= 1.28 | 75 | 70W/5L | 93.3% | +12.10% | +31.9pts | <0.001 ★★★ |
| 7 | Range 30m % <= 1.46 AND Accum days >= 3.70 | 67 | 63W/4L | 94.0% | +11.69% | +32.6pts | <0.001 ★★★ |
| 8 | Range 30m % <= 1.46 AND Accum hours >= 88.00 | 67 | 63W/4L | 94.0% | +11.69% | +32.6pts | <0.001 ★★★ |
| 9 | Range 30m % <= 1.89 AND BTC dominance <= 56.98 | 81 | 75W/6L | 92.6% | +11.76% | +31.1pts | <0.001 ★★★ |
| 10 | Range 30m % <= 1.89 AND Accum days >= 3.20 | 87 | 80W/7L | 92.0% | +11.56% | +30.5pts | <0.001 ★★★ |
| 11 | Range 30m % <= 1.89 AND Accum hours >= 76.00 | 87 | 80W/7L | 92.0% | +11.56% | +30.5pts | <0.001 ★★★ |
| 12 | Range 30m % <= 1.46 AND Range 4h % <= 2.58 | 218 | 189W/29L | 86.7% | +9.38% | +25.2pts | <0.001 ★★★ |
| 13 | Accum days >= 3.20 AND Range 30m % <= 2.51 | 93 | 85W/8L | 91.4% | +11.30% | +29.9pts | <0.001 ★★★ |
| 14 | Accum hours >= 76.00 AND Range 30m % <= 2.51 | 93 | 85W/8L | 91.4% | +11.30% | +29.9pts | <0.001 ★★★ |
| 15 | Range 30m % <= 1.46 AND Accum days >= 2.70 | 86 | 79W/7L | 91.9% | +11.48% | +30.4pts | <0.001 ★★★ |
| 16 | Range 30m % <= 1.46 AND Accum hours >= 64.00 | 86 | 79W/7L | 91.9% | +11.48% | +30.4pts | <0.001 ★★★ |
| 17 | Accum days >= 4.30 AND Range 4h % <= 2.58 | 65 | 61W/4L | 93.8% | +12.20% | +32.4pts | <0.001 ★★★ |
| 18 | Accum hours >= 104.00 AND Range 4h % <= 2.58 | 65 | 61W/4L | 93.8% | +12.20% | +32.4pts | <0.001 ★★★ |
| 19 | Range 1h % <= 2.13 AND BTC dominance <= 56.98 | 72 | 67W/5L | 93.1% | +11.26% | +31.6pts | <0.001 ★★★ |
| 20 | Range 30m % <= 1.89 AND Accum days >= 3.70 | 76 | 70W/6L | 92.1% | +11.41% | +30.6pts | <0.001 ★★★ |
| 21 | Range 30m % <= 1.89 AND Accum hours >= 88.00 | 76 | 70W/6L | 92.1% | +11.41% | +30.6pts | <0.001 ★★★ |
| 22 | Accum days >= 3.20 AND Range 4h % <= 2.58 | 88 | 80W/8L | 90.9% | +11.39% | +29.4pts | <0.001 ★★★ |
| 23 | Accum hours >= 76.00 AND Range 4h % <= 2.58 | 88 | 80W/8L | 90.9% | +11.39% | +29.4pts | <0.001 ★★★ |
| 24 | Range 30m % <= 1.17 AND Range 4h % <= 2.58 | 181 | 157W/24L | 86.7% | +9.28% | +25.3pts | <0.001 ★★★ |
| 25 | Accum days >= 3.70 AND Range 30m % <= 2.51 | 81 | 74W/7L | 91.4% | +11.14% | +29.9pts | <0.001 ★★★ |
| 26 | Accum hours >= 88.00 AND Range 30m % <= 2.51 | 81 | 74W/7L | 91.4% | +11.14% | +29.9pts | <0.001 ★★★ |
| 27 | Accum days >= 3.70 AND Range 4h % <= 2.58 | 80 | 73W/7L | 91.2% | +11.21% | +29.8pts | <0.001 ★★★ |
| 28 | Accum hours >= 88.00 AND Range 4h % <= 2.58 | 80 | 73W/7L | 91.2% | +11.21% | +29.8pts | <0.001 ★★★ |
| 29 | Range 30m % <= 1.46 AND Range 15m % <= 1.28 | 340 | 285W/55L | 83.8% | +8.75% | +22.4pts | <0.001 ★★★ |
| 30 | Range 15m % <= 0.75 AND Range 4h % <= 2.58 | 200 | 172W/28L | 86.0% | +9.11% | +24.5pts | <0.001 ★★★ |

## 📍 Where does Custom rank?

- 166 single-feature hypotheses score higher than Custom on the rank metric
- 218 combo hypotheses score higher
- 🔴 **Several hypotheses outperform Custom** — see top 5 above

## 💡 Recommendations

1. **Prioritize hypotheses with low p-value (★, ★★, ★★★)** — they are statistically significant.
2. **Avoid combos with N < 50** unless the lift is dramatic (>15pts) — small samples are noise-prone.
3. **Run a second pass** in 1-2 weeks to verify top hypotheses still hold (regime stability check).
4. **Combos that look like extensions of Custom** (e.g. score>=8 + body 4h>=3) confirm your trader intuition is on track.
