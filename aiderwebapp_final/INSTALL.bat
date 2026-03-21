@echo off
title AiderWeb Installer
color 0B
cls

set "APP=%~dp0"

echo.
echo  ============================================
echo    AIDERWEB INSTALLER
echo  ============================================
echo.

where node   >nul 2>&1 || (echo [ERROR] Node.js not found & pause & exit /b 1)
where python >nul 2>&1 || (echo [ERROR] Python not found  & pause & exit /b 1)
for /f %%v in ('node --version')   do echo [OK] Node %%v
for /f %%v in ('python --version') do echo [OK] %%v
echo.

echo [1/3] Installing Python backend...
cd /d "%APP%backend"
py -3.12 -m pip install fastapi "uvicorn[standard]" websockets pydantic aider-chat --quiet
echo [OK] Backend ready
echo.

echo [2/3] Installing frontend...
cd /d "%APP%frontend"
call npm install --silent
echo [OK] Frontend installed
echo.

echo [3/3] Building frontend...
call npm run build
echo [OK] Frontend built
echo.

echo  ============================================
echo  DONE! Run START_AiderWeb.bat to launch.
echo  ============================================
pause
