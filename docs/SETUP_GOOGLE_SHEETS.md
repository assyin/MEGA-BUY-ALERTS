# 📊 Setup Google Sheets — MEGA BUY Bot

## Étape 1 : Créer un projet Google Cloud

1. Va sur https://console.cloud.google.com/
2. Clique **"Créer un projet"** → Nom : `MegaBuyBot` → Créer
3. Sélectionne le projet créé

## Étape 2 : Activer les APIs

1. Menu ☰ → **APIs & Services** → **Bibliothèque**
2. Cherche **"Google Sheets API"** → **Activer**
3. Cherche **"Google Drive API"** → **Activer**

## Étape 3 : Créer un Service Account

1. Menu ☰ → **APIs & Services** → **Identifiants (Credentials)**
2. Clique **"+ Créer des identifiants"** → **Compte de service**
3. Nom : `megabuy-bot` → Créer
4. Rôle : **Éditeur** → Continuer → Terminé

## Étape 4 : Télécharger la clé JSON

1. Clique sur le Service Account créé (megabuy-bot@...)
2. Onglet **"Clés"** → **Ajouter une clé** → **Créer une clé**
3. Format : **JSON** → Créer
4. Le fichier se télécharge automatiquement
5. **Renomme-le** en `google_creds.json`
6. **Copie-le** dans le dossier `C:\Mega_BUY_BOT\`

## Étape 5 : Créer le Google Sheet

1. Va sur https://docs.google.com/spreadsheets/
2. Crée un nouveau spreadsheet
3. **Renomme-le** exactement : `MEGA BUY Alerts`
4. **Partage-le** avec l'email du Service Account :
   - Ouvre le fichier `google_creds.json`
   - Copie la valeur de `"client_email"` (ex: `megabuy-bot@megabuybot.iam.gserviceaccount.com`)
   - Dans Google Sheet : **Partager** → Colle l'email → Rôle **Éditeur** → Envoyer

## Étape 6 : Lancer le bot

```
C:\Mega_BUY_BOT\
├── mega_buy_bot.py
├── google_creds.json    ← ta clé
├── start_bot.bat
```

Lance `start_bot.bat`. Le bot affichera :
```
✅ Google Sheets connecté
```

## Résultat dans Google Sheet

Le tableau se remplit automatiquement à chaque alerte :

| Date/Heure | Paire | Score | TFs | Nb TF | Émotion | Prix | RSI | DI+ | RSI✓ | DMI✓ | AST✓ | CHoCH | Zone | Lazy | Vol | ST | PP | EC | Bougie 4H |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-02-16 08:00 | BTC | 9 | 30m, 1h | 2 | 🔥 STRONG | 98500.5 | 55.2 | 22.1 | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ | ✓ | ✓ | ✗ | ✓ | 2026-02-16 08h |

**Couleurs automatiques :**
- 🟢 Score ≥ 9 : fond vert
- 🟡 Score ≥ 7 : fond jaune
- 🟠 Score < 7 : fond orange
- ✓ vert / ✗ rouge pour les conditions
- Bordure spéciale pour les multi-TF (2+, 3+, 4 TF)
