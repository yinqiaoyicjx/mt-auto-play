@echo off
title MOTA Tools

cd /d "%~dp0.."

:MENU
cls
echo ============================================
echo     MOTA Tools
echo ============================================
echo.
echo  [1] Collect Monster Templates (Manual)
echo  [2] Collect Monster Templates (From Book)
echo  [3] Resize Game Window
echo  [4] Calibrate Grid Size
echo  [5] Test Detection
echo.
echo  [0] Exit
echo.
echo ============================================
set /p choice=Select function (0-5):

if "%choice%"=="1" goto COLLECT_MANUAL
if "%choice%"=="2" goto COLLECT_BOOK
if "%choice%"=="3" goto RESIZE
if "%choice%"=="4" goto CALIBRATE
if "%choice%"=="5" goto TEST
if "%choice%"=="0" goto EXIT

echo [ERROR] Invalid choice
pause
goto MENU

:COLLECT_MANUAL
cls
echo ============================================
echo  Manual Template Collection
echo ============================================
echo.
echo Instructions:
echo   1. Make sure game is running
echo   2. Find a monster
echo   3. Press 'c' to capture
echo   4. Enter monster name and stats
echo   5. Press 'q' to exit
echo.
pause
python src\tools.py --collect-manual
pause
goto MENU

:COLLECT_BOOK
cls
echo ============================================
echo  Collect From Monster Book
echo ============================================
echo.
echo Instructions:
echo   1. Make sure game is running
echo   2. Open monster book in game
echo   3. Press Enter to start
echo   4. Press ESC to exit
echo.
pause
python src\tools.py --collect-book
pause
goto MENU

:RESIZE
cls
echo ============================================
echo  Resize Game Window
echo ============================================
echo.
echo Resizing window to 640x480...
echo.
python src\tools.py --resize
echo.
pause
goto MENU

:CALIBRATE
cls
echo ============================================
echo  Calibrate Grid Size
echo ============================================
echo.
echo Instructions:
echo   1. Make sure game is running
echo   2. Click two adjacent grid points
echo   3. Program calculates grid size
echo.
pause
python src\tools.py --calibrate
pause
goto MENU

:TEST
cls
echo ============================================
echo  Test Detection
echo ============================================
echo.
echo Instructions:
echo   - Press Enter to capture
echo   - Press q to exit
echo.
pause
python src\main.py --test
pause
goto MENU

:EXIT
exit
