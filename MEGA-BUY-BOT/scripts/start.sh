#!/bin/bash
# ═══════════════════════════════════════════════════════
# 🚀 ASSYIN-2026 — Start All Services
# Scanner Bot + Entry Agent
# ═══════════════════════════════════════════════════════

echo "╔═══════════════════════════════════════════════════╗"
echo "║     🚀 ASSYIN-2026 — Crypto Trading Suite         ║"
echo "║     🤖 MEGA BUY Scanner Bot v3                    ║"
echo "║     🎯 Entry Agent v2 — Golden Box Monitor        ║"
echo "╚═══════════════════════════════════════════════════╝"
echo ""

# Dossier de travail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 non trouvé"
    exit 1
fi

# Vérifier les dépendances
echo "📦 Vérification des dépendances..."
python3 -c "import requests, numpy, pandas" 2>/dev/null || {
    echo "📥 Installation des dépendances..."
    pip install requests numpy pandas --break-system-packages -q
}

python3 -c "import gspread" 2>/dev/null || {
    echo "📥 Installation gspread..."
    pip install gspread google-auth --break-system-packages -q
}

# Vérifier les fichiers
echo ""
for f in mega_buy_bot.py mega_buy_entry_agent_v2.py; do
    if [ -f "$f" ]; then
        echo "  ✅ $f"
    else
        echo "  ❌ $f MANQUANT"
    fi
done

# Vérifier config
if [ -f "google_creds.json" ]; then
    echo "  ✅ google_creds.json"
else
    echo "  ⚠️  google_creds.json manquant (Google Sheets désactivé)"
fi
echo ""

# ═══════════════════════════════════════════════════════
# Menu
# ═══════════════════════════════════════════════════════
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Que voulez-vous lancer ?"
echo ""
echo "  [1] 🤖 Bot Scanner uniquement"
echo "  [2] 🎯 Entry Agent uniquement"
echo "  [3] 🚀 Les deux (Bot + Agent)"
echo "  [q] ❌ Quitter"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
read -p "  > " choice

case $choice in
    1)
        echo ""
        echo "🤖 Lancement du Bot Scanner..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 mega_buy_bot.py
        ;;
    2)
        echo ""
        echo "🎯 Lancement de l'Entry Agent v2..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        python3 mega_buy_entry_agent_v2.py
        ;;
    3)
        echo ""
        echo "🚀 Lancement des deux services..."
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""

        # Créer dossier logs
        mkdir -p logs

        LOG_BOT="logs/bot_$(date +%Y%m%d_%H%M%S).log"
        LOG_AGENT="logs/agent_$(date +%Y%m%d_%H%M%S).log"

        # Lancer Bot en background
        echo "  🤖 Bot Scanner → PID: en cours..."
        python3 mega_buy_bot.py > "$LOG_BOT" 2>&1 &
        PID_BOT=$!
        echo "  🤖 Bot Scanner → PID: $PID_BOT (log: $LOG_BOT)"

        sleep 2

        # Lancer Entry Agent en background
        echo "  🎯 Entry Agent → PID: en cours..."
        python3 mega_buy_entry_agent_v2.py --auto > "$LOG_AGENT" 2>&1 &
        PID_AGENT=$!
        echo "  🎯 Entry Agent → PID: $PID_AGENT (log: $LOG_AGENT)"

        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "  ✅ Les deux services tournent !"
        echo ""
        echo "  📋 Commandes utiles :"
        echo "    tail -f $LOG_BOT        # Voir logs Bot"
        echo "    tail -f $LOG_AGENT      # Voir logs Agent"
        echo "    kill $PID_BOT            # Arrêter Bot"
        echo "    kill $PID_AGENT          # Arrêter Agent"
        echo "    kill $PID_BOT $PID_AGENT # Arrêter tout"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "  Appuyez Ctrl+C pour arrêter les deux..."
        echo ""

        # Trap Ctrl+C pour kill les deux
        trap "echo ''; echo '🛑 Arrêt...'; kill $PID_BOT $PID_AGENT 2>/dev/null; echo '✅ Services arrêtés'; exit 0" INT TERM

        # Attendre et monitorer
        while true; do
            # Check si les process tournent encore
            if ! kill -0 $PID_BOT 2>/dev/null; then
                echo "  ⚠️ Bot Scanner s'est arrêté ! Redémarrage..."
                python3 mega_buy_bot.py >> "$LOG_BOT" 2>&1 &
                PID_BOT=$!
                echo "  🤖 Nouveau PID: $PID_BOT"
            fi
            if ! kill -0 $PID_AGENT 2>/dev/null; then
                echo "  ⚠️ Entry Agent s'est arrêté ! Redémarrage..."
                python3 mega_buy_entry_agent_v2.py --auto >> "$LOG_AGENT" 2>&1 &
                PID_AGENT=$!
                echo "  🎯 Nouveau PID: $PID_AGENT"
            fi
            sleep 60
        done
        ;;
    q|Q)
        echo "👋 Au revoir"
        exit 0
        ;;
    *)
        echo "❓ Choix invalide"
        exit 1
        ;;
esac
