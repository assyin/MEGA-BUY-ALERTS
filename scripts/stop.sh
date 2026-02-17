#!/bin/bash
# 🛑 Stop all ASSYIN-2026 services
echo "🛑 Arrêt des services ASSYIN-2026..."

# Kill bot
BOT_PIDS=$(pgrep -f "mega_buy_bot.py" 2>/dev/null)
if [ -n "$BOT_PIDS" ]; then
    kill $BOT_PIDS 2>/dev/null
    echo "  ✅ Bot Scanner arrêté (PID: $BOT_PIDS)"
else
    echo "  ⚪ Bot Scanner non actif"
fi

# Kill agent
AGENT_PIDS=$(pgrep -f "mega_buy_entry_agent" 2>/dev/null)
if [ -n "$AGENT_PIDS" ]; then
    kill $AGENT_PIDS 2>/dev/null
    echo "  ✅ Entry Agent arrêté (PID: $AGENT_PIDS)"
else
    echo "  ⚪ Entry Agent non actif"
fi

echo ""
echo "✅ Tous les services arrêtés"
