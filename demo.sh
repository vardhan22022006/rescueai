#!/bin/bash
# RescueAI Demo Launcher
# Runs both backend and frontend concurrently for hackathon judging

set -e

echo "=== RescueAI Demo Setup ==="
echo ""

# Reset and reseed database
echo "1. Resetting database and seeding with 40 sample reports..."
cd backend
python seed_data.py

# Start backend in background
echo ""
echo "2. Starting backend on http://localhost:8000 ..."
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "   Waiting for backend to be ready..."
sleep 5

# Start frontend in background
echo ""
echo "3. Starting frontend on http://localhost:5173 ..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== Demo Ready! ==="
echo ""
echo "  🎯 Control Room Dashboard:  http://localhost:5173"
echo "  📱 Citizen Reporting Form:   http://localhost:5173/report"
echo "  🔗 API Docs:                 http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers"
echo ""

# Wait for user interrupt, then kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo 'Demo stopped.'; exit 0" INT
wait
