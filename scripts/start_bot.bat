@echo off
title MEGA BUY Scanner Bot v3 - Multi-TF + Google Sheets
echo.
echo ==========================================
echo   MEGA BUY Scanner Bot v3
echo   Multi-TF + Google Sheets Logging
echo ==========================================
echo.
pip install requests pandas numpy gspread google-auth --quiet
echo.
python mega_buy_bot.py
pause
