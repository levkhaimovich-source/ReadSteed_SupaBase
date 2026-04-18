@echo off
setlocal enabledelayedexpansion

:: Get the local IP address (IPv4)
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set ip=%%a
    set ip=!ip: ^=!
)

cd /d "%~dp0"

echo ======================================================
echo           ReadSteed RSVP Reader Launching...
echo ======================================================
echo.
echo  Local access:    http://localhost:5000
echo  Network access:  http://!ip!:5000
echo.
echo  Note: Make sure other devices are on the same WiFi!
echo.
echo ======================================================
echo.

:: Open browser
echo Opening your browser...
start http://localhost:5000

:: Run the app
echo Starting the server...
py app.py

pause
