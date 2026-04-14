@echo off
title Install Dependencies
echo.
echo  ========================================
echo    TimeImprint - Offline Install
echo  ========================================
echo.
echo  Installing Python dependencies from local packages...
echo.
cd /d "%~dp0"

echo  [1/2] Installing dependencies...
pip install --no-index --find-links=packages -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  Local install failed, trying online install...
    pip install -r requirements.txt
)

echo.
echo  [2/2] Creating directories...
if not exist "data" mkdir data
if not exist "thumbnails" mkdir thumbnails
if not exist "uploads" mkdir uploads
if not exist "exports" mkdir exports

echo.
echo  ========================================
echo    Install Complete!
echo  ========================================
echo.
echo  Next steps:
echo    1. Edit config.py to set photo/video paths
echo    2. Double click start.bat to run
echo    3. Open http://localhost:5000 in browser
echo.
pause
