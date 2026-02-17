@echo off
REM ═══════════════════════════════════════════
REM  MEGA BUY BOT — Push to GitHub
REM  Run this in the extracted folder
REM ═══════════════════════════════════════════

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║   MEGA BUY BOT — GitHub Push          ║
echo  ╚═══════════════════════════════════════╝
echo.

REM Init git repo
git init
git remote add origin https://github.com/assyin/MEGA-BUY-BOT.git 2>nul

REM Add all files
git add -A
git commit -m "🟢 MEGA BUY BOT — Scanner + Entry Agent v2 + 7J Analysis"

REM Push to main
git branch -M main
git push -u origin main --force

echo.
echo ✅ Push complete! Check: https://github.com/assyin/MEGA-BUY-BOT
pause
