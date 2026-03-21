#!/bin/bash
# Start the Live Simulation System

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Activate virtual environment if it exists
if [ -f "/home/assyin/MEGA-BUY-BOT/python/venv/bin/activate" ]; then
    source /home/assyin/MEGA-BUY-BOT/python/venv/bin/activate
fi

# Install dependencies if needed
pip install -q aiohttp numpy fastapi uvicorn pydantic websockets

echo "========================================"
echo "  MEGA BUY Live Simulation System"
echo "========================================"
echo ""
echo "Starting simulation API server..."
echo "Dashboard: http://localhost:8001"
echo "API Docs: http://localhost:8001/docs"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start the API server
python -m simulation.api.server
