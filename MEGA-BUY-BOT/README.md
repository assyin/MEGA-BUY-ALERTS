# 🟢 MEGA BUY BOT — Crypto Trading Scanner & Entry Agent

> Bot de trading crypto automatisé — Scanner 500+ paires USDT sur Binance avec alertes Telegram et Google Sheets.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Binance](https://img.shields.io/badge/Binance-API-yellow?logo=binance)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram)

## 📋 Vue d'ensemble

MEGA BUY BOT est un système de trading en 2 composants :

1. **🤖 Scanner Bot** (`mega_buy_bot.py`) — Scanne 500+ paires USDT toutes les 15 min sur 4 timeframes (15m, 30m, 1h, 4h). Attribue un score /10 basé sur 10 indicateurs techniques.

2. **🎯 Entry Agent** (`mega_buy_entry_agent_v2.py`) — Surveille les "Golden Boxes" détectées et attend les conditions d'entrée optimales (MSB + CHoCH + Volume Break).

## 🏗️ Structure du projet

```
MEGA-BUY-BOT/
├── mega_buy_bot.py                      # Scanner principal
├── mega_buy_entry_agent_v2.py           # Agent d'entrée
├── mega_buy_entry_agent_backtest-v2.py  # Backtesting
├── config.py                            # Configuration partagée
├── requirements.txt                     # Dépendances Python
├── .env.example                         # Template variables d'env
├── CLAUDE.md                            # Instructions Claude Code
├── scripts/
│   ├── start.sh                         # Démarrer les services
│   ├── status.sh                        # Status des services
│   └── stop.sh                          # Arrêter les services
└── docs/
    └── strategy-images/                 # Screenshots de la stratégie
```

## 🚀 Installation

```bash
# Cloner le repo
git clone https://github.com/assyin/MEGA-BUY-BOT.git
cd MEGA-BUY-BOT

# Installer les dépendances
pip install -r requirements.txt

# Configurer les credentials
cp .env.example .env
# Éditer .env avec vos tokens Telegram + Google Sheets
```

## ⚙️ Configuration

Éditer `config.py` ou créer un `.env` :

| Variable | Description |
|---|---|
| `TELEGRAM_TOKEN` | Token du bot Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID pour les alertes |
| `GOOGLE_SHEETS_ENABLED` | Activer le logging Google Sheets |
| `GOOGLE_CREDS_FILE` | Chemin vers `google_creds.json` |

## 📊 Stratégie MEGA BUY

**Score /10** avec 3 indicateurs obligatoires + 7 optionnels :

| # | Indicateur | Type | Description |
|---|---|---|---|
| 1 | RSI Momentum | ✅ Obligatoire | RSI move > seuil |
| 2 | DMI Crossover | ✅ Obligatoire | +DI > -DI avec ADX |
| 3 | AST Flip | ✅ Obligatoire | SuperTrend flip bullish |
| 4-10 | Optionnels | ⭐ Bonus | EC, CHoCH, Volume, etc. |

## 🎯 Golden Box & Entry

- **Golden Box** = Zone de consolidation pré-breakout
- **Entry** = MSB (Market Structure Break) + CHoCH + Volume > 1.5× avg
- **TP** = Box High + hauteur × 1.5
- **SL** = Box Low - ATR × 0.5

## 🖥️ Utilisation

```bash
# Menu interactif
bash scripts/start.sh

# Ou lancer individuellement
python mega_buy_bot.py                      # Scanner
python mega_buy_entry_agent_v2.py           # Agent
python mega_buy_entry_agent_backtest-v2.py  # Backtest

# Status & Stop
bash scripts/status.sh
bash scripts/stop.sh
```

## 👤 Auteur

**ASSYIN-2026**

---
*⚠️ Ce bot est un outil d'analyse. Il ne constitue pas un conseil financier. Tradez à vos propres risques.*
