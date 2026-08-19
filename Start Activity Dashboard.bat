@echo off
REM Double-click this file to start the Activity Schedule Dashboard.
REM Starts the server in its own window, then opens your browser to it.

set PORT=8000

start "Activity Schedule Dashboard - SERVER (keep this window open)" cmd /k python "%~dp0app.py"

timeout /t 3 /nobreak >nul

start "" http://localhost:%PORT%

echo ============================================================
echo  Activity Schedule Dashboard is starting.
echo.
echo  On THIS computer:      http://localhost:%PORT%
echo.
echo  On your PHONE, connect to the SAME WIFI as this PC, then
echo  combine one of the addresses below with :%PORT%
echo  (skip anything that says 169.254... - that one won't work):
echo.
ipconfig | findstr /i "IPv4"
echo.
echo  Example: http://192.168.1.42:%PORT%
echo.
echo  If Windows Firewall pops up asking about Python, click
echo  "Allow access" - otherwise your phone won't be able to connect.
echo.
echo  The server itself is running in the OTHER window titled
echo  "Activity Schedule Dashboard - SERVER". Close that window
echo  (or press Ctrl+C in it) to stop the app.
echo ============================================================
echo.
pause
