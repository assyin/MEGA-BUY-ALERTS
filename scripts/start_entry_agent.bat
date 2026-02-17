@echo off
title MEGA BUY Entry Agent v1 - Golden Box Monitor
echo.
echo ==========================================
echo   MEGA BUY Entry Agent v1
echo   Golden Box + Span B + DMI Cross
echo ==========================================
echo.
pip install requests pandas numpy gspread google-auth --quiet
echo.
python mega_buy_entry_agent.py
pause
