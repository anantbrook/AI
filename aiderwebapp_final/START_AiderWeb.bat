@echo off
title AiderWeb
color 0A
cls

set "APP=%~dp0"
set PORT=8000

echo.
echo  ============================================
echo    AIDERWEB - Cloud AI Coding
echo  ============================================
echo.

:: Kill anything already on port 8000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
:: Kill any old AiderWeb backend window
taskkill /fi "WindowTitle eq AiderWeb-Backend" /f >nul 2>&1
timeout /t 1 /nobreak >nul

:: Start Ollama if not already running
ollama list >nul 2>&1
if %errorlevel% neq 0 (
    echo  Starting Ollama...
    start /min "" ollama serve
    timeout /t 4 /nobreak >nul
)
echo  [OK] Ollama running

:: Start Python backend
echo  Starting backend...
start "AiderWeb-Backend" /min cmd /k "cd /d "%APP%backend" && py -3.12 main.py"
timeout /t 3 /nobreak >nul

:: Get local IP
set IP=unknown
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4" ^| findstr /v "169.254"') do (
    set RAW=%%a & goto :gotip
)
:gotip
set IP=%RAW: =%

echo  [OK] Backend running
echo.
echo  ============================================
echo.
echo    Local:    http://localhost:%PORT%
echo    Network:  http://%IP%:%PORT%  ^<-- phone/other PC
echo.
echo  ============================================
echo.

timeout /t 2 /nobreak >nul
start http://localhost:%PORT%

echo  Press any key to STOP AiderWeb...
pause >nul

taskkill /fi "WindowTitle eq AiderWeb-Backend" /f >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT% " ^| findstr "LISTENING" 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
echo  Stopped.
