@echo off
echo ================================================
echo Starting RescueAI Backend (Port 8000)
echo ================================================
echo.
python -m uvicorn main:app --reload --port 8000
