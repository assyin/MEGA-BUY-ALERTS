# 🟢 MEGA BUY BOT

> Crypto trading signal detection & entry management system for Binance

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

MEGA BUY BOT scans 400+ Binance USDT pairs across multiple timeframes to detect high-probability buy signals, then monitors for optimal entry points using the **Golden Box** strategy.

### Two Components

| Component | Description |
|---|---|
| 🟢 **Scanner Bot** | Detects MEGA BUY signals (score /10) on 15m, 30m, 1h, 4h |
| 🎯 **Entry Agent v2** | Monitors signals → finds entries → tracks TP/SL outcomes |

## ⚡ Quick Start

```bash
# Clone
git clone https://github.com/assyin/MEGA-BUY-BOT.git
cd MEGA-BUY-BOT

# Install
pip install -r requirements.txt

# Configure
# → Set TELEGRAM_TOKEN & TELEGRAM_CHAT_ID in python/mega_buy_bot.py
# → Place google_creds.json in root (see docs/SETUP_GOOGLE_SHEETS.md)

# Run Scanner
python python/mega_buy_bot.py

# Run Entry Agent
python python/mega_buy_entry_agent_v2.py
```

## 📊 MEGA BUY Score /10

**3 Mandatory** (must all trigger):
- RSI surge ≥ 12 points
- DMI+ surge ≥ 10 points
- ASSYIN SuperTrend flip to bullish

**7 Optional** (each adds +1):
CHoCH | Green Zone | LazyBar | Volume | SuperTrend | PP SuperTrend | Entry Confirmation

## 🎯 Golden Box Entry — 5 Conditions

1. ✅ **DMI+** > DMI- on 4H
2. ✅ **Breakout** — 4H close > Box High
3. ✅ **RSI HH** — RSI 4H > reference RSI
4. ✅ **Cloud 1H** — Price > Assyin# Ichimoku cloud on 1H
5. ✅ **Cloud 30M** — Price > Assyin# Ichimoku cloud on 30M

**Bonus**: Volume > 1.5× avg20 | Retest Box High as support

## 📁 Structure

```
python/
  mega_buy_bot.py              # Scanner Bot
  mega_buy_entry_agent_v2.py   # Entry Agent + 7J Analysis
  mega_buy_backtest.py         # Backtester
  mega_buy_optimizer.py        # Parameter optimizer
  config.py                    # Configuration

pinescript/
  mega_buy_v7.pine             # Main indicator
  gb_entry_standalone.pine     # Golden Box Entry monitor
  assyin_v7_golden_box.pine    # Combined indicator
  golden_box_entry_v5.pine     # Entry visualization

scripts/                       # Start/stop scripts
docs/                          # Setup guides
```

## 📊 7-Day Analysis Mode

Backtest the strategy on the last 7 days of real data:

```bash
python python/mega_buy_entry_agent_v2.py --analyze
```

This will:
1. 📥 **Collect** — Scan all pairs × 4 TFs × 7 days
2. 🔄 **Replay** — Run Entry Agent on each signal
3. 📊 **Analyze** — Check TP/SL outcomes
4. 📝 **Report** — Google Sheets + Telegram summary

## 🔧 Configuration

| Setting | Location |
|---|---|
| Telegram Bot | `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` in Python files |
| Google Sheets | `google_creds.json` → see `docs/SETUP_GOOGLE_SHEETS.md` |
| Binance | Public API, no auth needed |

## Author

**ASSYIN** — 2026

## License

MIT
