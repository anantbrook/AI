@echo off
color 0B
title Starting AiderWeb Advanced Agent...

echo =======================================================
echo          Starting Backend API
echo =======================================================
cd backend
start cmd /k "python -m uvicorn main:app --port 8000"

echo.
echo Server should now be running at http://127.0.0.1:8000
echo Opening in default browser...
timeout /t 3 > NUL
start http://127.0.0.1:8000

pause
