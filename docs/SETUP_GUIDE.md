# 🚀 MEGA BUY Scanner Bot — Guide d'Installation

## Étape 1 : Installer Python (5 min)

1. Va sur https://www.python.org/downloads/
2. Télécharge **Python 3.11** ou plus récent
3. **IMPORTANT** : Coche ✅ "Add Python to PATH" pendant l'installation
4. Clique "Install Now"

**Vérification :** Ouvre un terminal (cmd ou PowerShell) et tape :
```
python --version
```
Tu dois voir `Python 3.11.x` ou plus.

---

## Étape 2 : Créer un Bot Telegram (2 min)

1. Ouvre Telegram, cherche **@BotFather**
2. Envoie `/newbot`
3. Choisis un nom : `MEGA BUY Scanner`
4. Choisis un username : `megabuy_scanner_bot` (doit finir par `_bot`)
5. **BotFather te donne un TOKEN** → copie-le (format : `7123456789:AAH...`)

### Récupérer ton Chat ID :
1. Cherche **@userinfobot** sur Telegram
2. Envoie `/start`
3. Il te répond avec ton **Chat ID** (un nombre comme `123456789`)

---

## Étape 3 : Installer le Bot (2 min)

1. Crée un dossier `C:\MegaBuyBot\`
2. Copie le fichier `mega_buy_bot.py` dedans
3. Ouvre un terminal dans ce dossier et tape :

```
pip install requests pandas numpy
```

---

## Étape 4 : Configurer le Bot

Ouvre `mega_buy_bot.py` et modifie ces 2 lignes en haut :

```python
TELEGRAM_TOKEN = "COLLE_TON_TOKEN_ICI"
TELEGRAM_CHAT_ID = "COLLE_TON_CHAT_ID_ICI"
```

---

## Étape 5 : Lancer le Bot

Double-clique sur `start_bot.bat` ou dans le terminal :

```
cd C:\MegaBuyBot
python mega_buy_bot.py
```

Tu verras :
```
🟢 MEGA BUY Scanner démarré
📊 Scan de 500+ paires USDT toutes les 30 min
⏰ Prochain scan dans : 12 min 30 sec
```

---

## Commandes Telegram

Une fois le bot lancé, tu peux lui envoyer ces commandes :

| Commande | Action |
|----------|--------|
| `/scan` | Force un scan immédiat |
| `/status` | Affiche l'état du bot |
| `/top` | Affiche les derniers signaux |
| `/help` | Liste des commandes |

---

## FAQ

**Q: Le bot doit tourner 24/7 ?**
R: Oui, tant que ton PC est allumé. Si tu veux qu'il tourne même PC éteint → VPS Linux à 5$/mois.

**Q: C'est sécurisé ?**
R: Oui. Le bot utilise l'API publique de Binance (lecture seule, pas de clé API nécessaire). Il ne peut pas trader.

**Q: Combien de paires sont scannées ?**
R: Toutes les paires USDT actives sur Binance (500+).
