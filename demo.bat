@echo off
REM RescueAI Demo Launcher for Windows
REM Runs both backend and frontend concurrently

echo =========================================
echo    RescueAI Demo Setup (Windows)
echo =========================================
echo.

REM Navigate to backend
cd backend

REM Check if virtual environment exists
if not exist "venv\" (
    echo 1. Creating Python virtual environment...
    python -m venv venv
    echo    Virtual environment created!
    echo.
)

REM Activate virtual environment and install dependencies
echo 2. Installing backend dependencies...
call venv\Scripts\activate.bat
pip install -q -r requirements.txt
echo    Dependencies installed!
echo.

REM Check if .env exists, if not copy from example
if not exist ".env" (
    echo 3. Creating .env configuration...
    copy .env.example .env >nul
    echo    Configuration file created!
    echo.
)

REM Reset and reseed database
echo 4. Resetting database and seeding with 40 sample reports...
if exist "rescueai.db" del rescueai.db
python seed_data.py
echo    Database ready with sample data!
echo.

REM Start backend in new window
echo 5. Starting backend server on http://localhost:8000 ...
start "RescueAI Backend" cmd /k "cd /d "%CD%" && venv\Scripts\activate.bat && python main.py"
echo    Backend server starting...
echo.

REM Wait for backend to be ready
echo 6. Waiting for backend to initialize...
timeout /t 7 /nobreak >nul

REM Navigate to frontend
cd ..\frontend

REM Check if node_modules exists
if not exist "node_modules\" (
    echo 7. Installing frontend dependencies (this may take a minute)...
    call npm install
    echo    Frontend dependencies installed!
    echo.
) else (
    echo 7. Frontend dependencies already installed!
    echo.
)

REM Start frontend in new window
echo 8. Starting frontend server on http://localhost:5173 ...
start "RescueAI Frontend" cmd /k "cd /d "%CD%" && npm run dev"
echo    Frontend server starting...
echo.

REM Wait for frontend to be ready
timeout /t 5 /nobreak >nul

echo.
echo =========================================
echo        Demo Ready! Servers Running
echo =========================================
echo.
echo   🎯 Dashboard:      http://localhost:5173
echo   📱 Citizen Form:   http://localhost:5173/report
echo   📚 API Docs:       http://localhost:8000/docs
echo.
echo   Two windows opened:
echo   - "RescueAI Backend" (port 8000)
echo   - "RescueAI Frontend" (port 5173)
echo.
echo   To stop: Close both server windows
echo.
echo =========================================
echo.
pause
