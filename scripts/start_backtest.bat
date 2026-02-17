@echo off
title MEGA BUY Backtester - ASSYIN 2026
echo.
echo ==========================================
echo   MEGA BUY Backtester
echo ==========================================
echo.
pip install requests pandas numpy --quiet
echo.
python mega_buy_backtest.py
pause
