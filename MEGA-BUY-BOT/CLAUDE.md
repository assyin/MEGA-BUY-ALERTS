# CLAUDE.md — Instructions pour Claude Code

## Projet
MEGA-BUY-BOT est un bot de trading crypto (Binance spot) qui scanne 500+ paires USDT et détecte des setups d'achat basés sur une stratégie multi-indicateurs.

## Architecture
- `mega_buy_bot.py` — Scanner principal : scanne les paires, calcule le score /10 (RSI, DMI, AST obligatoires + 7 optionnels), envoie alertes Telegram + Google Sheets
- `mega_buy_entry_agent_v2.py` — Agent d'entrée : surveille les Golden Boxes détectées, attend la confirmation d'entrée (MSB, CHoCH, volume break), calcule TP/SL
- `mega_buy_entry_agent_backtest-v2.py` — Backtesting de l'agent d'entrée
- `config.py` — Configuration partagée (credentials, paramètres)
- `scripts/` — Scripts shell pour démarrer/arrêter/status

## Stratégie Trading (MEGA BUY)
- **Score /10** : 3 indicateurs obligatoires (RSI momentum, DMI crossover, AST flip) + 7 optionnels
- **Golden Box** : Zone de consolidation détectée sur 4H avant un breakout
- **Entry Confirmation** : MSB (Market Structure Break) + CHoCH (Change of Character) + Volume break
- **Multi-timeframe** : 15m, 30m, 1h, 4h

## Stack technique
- Python 3.10+
- API Binance (public, pas de clé requise pour les données OHLCV)
- Telegram Bot API pour les alertes
- Google Sheets API (gspread) pour le logging
- numpy/pandas pour le calcul des indicateurs

## Conventions
- Les credentials ne doivent JAMAIS être hardcodés — utiliser `.env` ou `config.py` local
- `google_creds.json` est dans `.gitignore`
- Les images de stratégie sont dans `docs/strategy-images/`

## Commandes utiles
```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer le scanner
python mega_buy_bot.py

# Lancer l'agent d'entrée
python mega_buy_entry_agent_v2.py

# Lancer le backtest
python mega_buy_entry_agent_backtest-v2.py

# Scripts de gestion
bash scripts/start.sh    # Menu interactif
bash scripts/status.sh   # Status des services
bash scripts/stop.sh     # Arrêter tout
```
