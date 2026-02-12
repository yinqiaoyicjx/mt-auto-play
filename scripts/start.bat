@echo off
title MOTA Auto-Play Bot

cd /d "%~dp0.."

echo ============================================
echo     MOTA Auto-Play Bot
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not detected, please install Python 3.8+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check dependencies
echo [1/3] Checking dependencies...
python -c "import mss, cv2, numpy, pyautogui, win32gui" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Missing dependencies, installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
) else (
    echo [OK] Dependencies installed
)

echo.
echo [2/3] Starting game...
echo Please make sure MOTA game is running!
echo.

:: Wait for user
echo Press any key to start the bot...
pause >nul

echo.
echo [3/3] Starting bot...
echo.
echo Tips:
echo   - Press Ctrl+C to stop
echo   - Game window must be in foreground
echo   - First run requires collecting monster templates
echo.

:: Run main program
python src\main.py %*

echo.
echo ============================================
echo Bot stopped
echo ============================================
pause
