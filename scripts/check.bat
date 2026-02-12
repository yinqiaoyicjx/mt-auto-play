@echo off
title MOTA System Check

cd /d "%~dp0.."

echo ============================================
echo     System Environment Check
echo ============================================
echo.

echo [Check Python]
python --version
if errorlevel 1 (
    echo   [X] Python not installed
    goto END
) else (
    echo   [OK] Python installed
)
echo.

echo [Check Dependencies]
echo ----------------------------------------
python -c "import mss; print('  [OK] mss')" 2>nul || echo   [X] mss
python -c "import cv2; print('  [OK] opencv-python')" 2>nul || echo   [X] opencv-python
python -c "import numpy; print('  [OK] numpy')" 2>nul || echo   [X] numpy
python -c "import pyautogui; print('  [OK] pyautogui')" 2>nul || echo   [X] pyautogui
python -c "import win32gui; print('  [OK] pywin32')" 2>nul || echo   [X] pywin32
python -c "import PIL; print('  [OK] Pillow')" 2>nul || echo   [X] Pillow
echo.

echo [Check Directories]
echo ----------------------------------------
if exist "data\templates" (echo   [OK] data\templates) else (echo   [X] data\templates)
if exist "data\monsters.json" (echo   [OK] data\monsters.json) else (echo   [X] data\monsters.json)
if exist "logs" (echo   [OK] logs) else (echo   [X] logs)
echo.

echo [Check Source Files]
echo ----------------------------------------
if exist "src\main.py" (echo   [OK] src\main.py) else (echo   [X] src\main.py)
if exist "src\capture.py" (echo   [OK] src\capture.py) else (echo   [X] src\capture.py)
if exist "src\detector.py" (echo   [OK] src\detector.py) else (echo   [X] src\detector.py)
if exist "src\state.py" (echo   [OK] src\state.py) else (echo   [X] src\state.py)
if exist "src\planner.py" (echo   [OK] src\planner.py) else (echo   [X] src\planner.py)
if exist "src\controller.py" (echo   [OK] src\controller.py) else (echo   [X] src\controller.py)
if exist "src\resource_manager.py" (echo   [OK] src\resource_manager.py) else (echo   [X] src\resource_manager.py)
if exist "src\shop.py" (echo   [OK] src\shop.py) else (echo   [X] src\shop.py)
if exist "src\tools.py" (echo   [OK] src\tools.py) else (echo   [X] src\tools.py)
echo.

echo [Check Game Window]
echo ----------------------------------------
python -c "import win32gui; w=win32gui.FindWindow(None,'MOTA'); print('[OK] Game window found' if w else '[!] Game window not found')"
echo.

:END
echo ============================================
echo     Check Complete
echo ============================================
echo.
pause
