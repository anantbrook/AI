@echo off
title AiderWeb DEV
set "APP=%~dp0"
ollama list >nul 2>&1 || (start /min "" ollama serve & timeout /t 3 /nobreak >nul)
start "Backend"  cmd /k "cd /d "%APP%backend"  && py -3.12 main.py"
start "Frontend" cmd /k "cd /d "%APP%frontend" && npm run dev"
timeout /t 3 /nobreak >nul
start http://localhost:5173
echo.
echo  DEV mode:  http://localhost:5173  (hot reload)
echo  Backend:   http://localhost:8000
echo.
pause
taskkill /fi "WindowTitle eq Backend"  /f >nul 2>&1
taskkill /fi "WindowTitle eq Frontend" /f >nul 2>&1
