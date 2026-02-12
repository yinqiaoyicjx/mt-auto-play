@echo off
title MOTA Auto-Play Bot [GUI Mode]

cd /d "%~dp0.."

echo ============================================
echo     MOTA Auto-Play Bot [GUI Mode]
echo ============================================
echo.
echo Starting GUI...
echo.

python src\gui_launcher.py

pause
