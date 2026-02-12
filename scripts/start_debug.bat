@echo off
title MOTA Auto-Play Bot [DEBUG MODE]

cd /d "%~dp0.."

echo ============================================
echo     MOTA Auto-Play Bot [DEBUG MODE]
echo ============================================
echo.
echo Debug mode shows detailed decision info
echo.

python src\main.py --debug %*

pause
