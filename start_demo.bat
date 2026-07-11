@echo off
echo ========================================================
echo RescueAI Demo Startup
echo ========================================================
echo.
echo Starting Backend (http://localhost:8000) and Frontend (http://localhost:5173)
echo.
echo Press Ctrl+C in each window to stop
echo ========================================================
echo.

echo Starting Backend...
start "RescueAI Backend" cmd /k "cd backend && python -m uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo Starting Frontend...
start "RescueAI Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo Both services are starting...
echo.
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Frontend: http://localhost:5173
echo.
echo Close the command windows to stop the services
echo ========================================================
