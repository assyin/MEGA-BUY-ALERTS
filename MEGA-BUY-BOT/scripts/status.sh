#!/bin/bash
# 📊 Status des services ASSYIN-2026
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  📊 ASSYIN-2026 — Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Bot
BOT_PID=$(pgrep -f "mega_buy_bot.py" 2>/dev/null)
if [ -n "$BOT_PID" ]; then
    echo "  🤖 Bot Scanner    : 🟢 RUNNING (PID: $BOT_PID)"
else
    echo "  🤖 Bot Scanner    : 🔴 STOPPED"
fi

# Agent
AGENT_PID=$(pgrep -f "mega_buy_entry_agent" 2>/dev/null)
if [ -n "$AGENT_PID" ]; then
    echo "  🎯 Entry Agent    : 🟢 RUNNING (PID: $AGENT_PID)"
else
    echo "  🎯 Entry Agent    : 🔴 STOPPED"
fi

# Golden Boxes
if [ -f "golden_boxes.json" ]; then
    WATCHING=$(python3 -c "import json; d=json.load(open('golden_boxes.json')); print(sum(1 for v in d.values() if v.get('status')=='WATCHING'))" 2>/dev/null)
    READY=$(python3 -c "import json; d=json.load(open('golden_boxes.json')); print(sum(1 for v in d.values() if v.get('status')=='ENTRY_READY'))" 2>/dev/null)
    echo ""
    echo "  📦 Golden Boxes   : ${WATCHING:-0} watching | ${READY:-0} entry ready"
fi

# Logs
if [ -d "logs" ]; then
    LATEST_BOT=$(ls -t logs/bot_*.log 2>/dev/null | head -1)
    LATEST_AGENT=$(ls -t logs/agent_*.log 2>/dev/null | head -1)
    echo ""
    if [ -n "$LATEST_BOT" ]; then
        echo "  📄 Dernier log Bot: $LATEST_BOT"
        tail -1 "$LATEST_BOT" 2>/dev/null | sed 's/^/     /'
    fi
    if [ -n "$LATEST_AGENT" ]; then
        echo "  📄 Dernier log Agent: $LATEST_AGENT"
        tail -1 "$LATEST_AGENT" 2>/dev/null | sed 's/^/     /'
    fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
