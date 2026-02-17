# CLAUDE.md — Context for Claude Code

## Project Overview
MEGA BUY BOT is a crypto trading signal detection and entry management system for Binance USDT pairs. It consists of two main components that work together:

1. **MEGA BUY Scanner Bot** (`python/mega_buy_bot.py`) — Scans 400+ Binance pairs across 4 timeframes (15m, 30m, 1h, 4h) to detect MEGA BUY signals using a score/10 system (3 mandatory + 7 optional indicators).

2. **Entry Agent v2** (`python/mega_buy_entry_agent_v2.py`) — Monitors MEGA BUY signals and detects optimal entries using the Golden Box strategy with 5 mandatory + 2 bonus conditions.

## Architecture

```
Scanner Bot (mega_buy_bot.py)
  → Detects MEGA BUY signals (score /10)
  → Writes alerts to Google Sheets "Alerts" tab
  → Sends Telegram notifications
  
Entry Agent v2 (mega_buy_entry_agent_v2.py)
  → Imports signals from Google Sheets
  → Creates Golden Box (4H candle High/Low/RSI)
  → Monitors 5 conditions every 15 min
  → Notifies when ENTRY READY
  → 7-day backtest analysis mode
```

## Key Trading Logic

### MEGA BUY Score /10
- **3 Mandatory**: RSI surge (≥12), DMI+ surge (≥10), ASSYIN SuperTrend flip
- **7 Optional**: CHoCH, Green Zone, LazyBar, Volume, SuperTrend, PP SuperTrend, Entry Confirmation

### Golden Box Entry (5 Mandatory + 2 Bonus)
1. DMI+ > DMI- on 4H
2. 4H candle CLOSE > Box High (breakout)
3. RSI 4H > RSI reference (Higher High)
4. Price > Cloud Top Assyin# Ichimoku on 1H
5. Price > Cloud Top Assyin# Ichimoku on 30M
- **Bonus 1**: Volume > 1.5× avg20
- **Bonus 2**: Retest Box High as support

### Assyin# Ichimoku Cloud
Custom dynamic Ichimoku with Senkou parameters ranging from 50 to 120 based on ATR volatility. This is NOT standard Ichimoku — it uses dynamic period calculation.

### 4H Candle Selection (PineScript-aligned)
Signal at time T → find first 4H bar where open_time >= T and < T + 4h. This matches PineScript's `gb_h4_time >= gb_startDate` logic.

## File Structure

```
python/
  mega_buy_bot.py          — Scanner Bot v3 (1158 lines)
  mega_buy_entry_agent_v2.py — Entry Agent v2 + 7J Analysis (2587 lines)
  mega_buy_backtest.py     — Backtester
  mega_buy_optimizer.py    — Parameter optimizer
  config.py                — Shared configuration
  
pinescript/
  mega_buy_v7.pine         — Main MEGA BUY indicator
  gb_entry_standalone.pine — Golden Box Entry monitor (389 lines)
  assyin_v7_golden_box.pine — Combined Assyin + Golden Box
  golden_box_entry_v5.pine — Entry visualization
  
scripts/
  start.sh / stop.sh / status.sh — Linux service management
  start_bot.bat / start_entry_agent.bat — Windows launchers

docs/
  SETUP_GUIDE.md           — Installation guide
  SETUP_GOOGLE_SHEETS.md   — Google Sheets API setup
```

## Configuration
- Telegram: Set `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` in each Python file
- Google Sheets: Place `google_creds.json` in working directory (see docs/SETUP_GOOGLE_SHEETS.md)
- Binance: Public API only (no auth needed), base URL `https://api.binance.com`

## Entry Agent v2 Commands
```
[a] Add Golden Box manually
[l] List active boxes
[d] Delete a box
[c] Clear all boxes
[s] Start monitoring
[7] 7-day analysis (collect + backtest)
[C] Collect only (scan 7d signals)
[R] Re-export results cache → Google Sheets
[q] Quit
```

CLI flags: `--auto`, `--analyze`, `--collect`, `--reexport`

## Important Implementation Details
- **15m filter**: Signals that are ONLY 15m are rejected. 15m+30m or 15m+1h = accepted.
- **Google Sheets batch writes**: Use `ws.update(values=all_rows)` not `append_row` loops (quota limit).
- **Delisted pairs**: Filter by date to avoid old data from delisted pairs.
- **Rate limiting**: 50ms sleep between Binance API calls in scan loops.
- **The bot uses `detect_mega_buy(df)` and the Entry Agent imports it dynamically** via `_import_bot()` for the 7-day analysis.

## Tech Stack
- Python 3.10+
- Binance public REST API
- Google Sheets API (gspread)
- Telegram Bot API
- PineScript v5 (TradingView)
