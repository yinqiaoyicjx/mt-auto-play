@echo off
title Install Dependencies

cd /d "%~dp0.."

echo ============================================
echo     Install MOTA Bot Dependencies
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not detected
    echo.
    echo Please install Python 3.8 or higher
    echo Download: https://www.python.org/downloads/
    echo.
    echo Check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [OK] Python installed
python --version
echo.

:: Upgrade pip
echo [1/4] Upgrading pip...
python -m pip install --upgrade pip
echo.

:: Install dependencies
echo [2/4] Installing core dependencies...
pip install mss opencv-python numpy pyautogui Pillow pywin32
echo.

:: Verify installation
echo [3/4] Verifying installation...
python -c "import mss; print('  - mss: OK')" 2>nul || echo "  - mss: FAILED"
python -c "import cv2; print('  - opencv-python: OK')" 2>nul || echo "  - opencv-python: FAILED"
python -c "import numpy; print('  - numpy: OK')" 2>nul || echo "  - numpy: FAILED"
python -c "import pyautogui; print('  - pyautogui: OK')" 2>nul || echo "  - pyautogui: FAILED"
python -c "import win32gui; print('  - pywin32: OK')" 2>nul || echo "  - pywin32: FAILED"
echo.

:: Create directories
echo [4/4] Creating directory structure...
if not exist "data\templates" mkdir data\templates
if not exist "logs" mkdir logs
echo   - data\templates: OK
echo   - logs: OK
echo.

echo ============================================
echo     Installation Complete!
echo ============================================
echo.
echo Next steps:
echo   1. Start MOTA game
echo   2. Run tools.bat to collect monster templates
echo   3. Run start.bat to begin auto-play
echo.
pause
