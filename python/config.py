"""
⚙️ ASSYIN-2026 — Configuration Partagée
Bot Scanner + Entry Agent utilisent le même fichier config
"""

# ═══════════════════════════════════════════════════════
# 🔑 CREDENTIALS — MODIFIER ICI
# ═══════════════════════════════════════════════════════
TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"

# Google Sheets
GOOGLE_SHEETS_ENABLED = True
GOOGLE_SHEET_NAME = "MEGA BUY Alerts"
GOOGLE_CREDS_FILE = "google_creds.json"

# ═══════════════════════════════════════════════════════
# 🤖 BOT SCANNER — Settings
# ═══════════════════════════════════════════════════════
BOT_SCAN_INTERVAL_MIN = 15
BOT_TIMEFRAMES = ["15m", "30m", "1h", "4h"]
BOT_MIN_VOLUME_USDT = 500_000
BOT_MAX_WORKERS = 12

# ═══════════════════════════════════════════════════════
# 🎯 ENTRY AGENT — Settings
# ═══════════════════════════════════════════════════════
AGENT_CHECK_INTERVAL_MIN = 15
AGENT_GOLDEN_BOX_EXPIRY_4H = 15      # 15 × 4H = 60h max
AGENT_TP_MULTIPLIER = 1.5            # TP = Box High + height × 1.5
AGENT_SL_ATR_BUFFER = 0.5            # SL = Box Low - ATR × 0.5
AGENT_VOLUME_BREAK_MULT = 1.5        # Volume > 1.5× avg20
