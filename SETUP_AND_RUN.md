# 🚀 Quick Setup Guide - Run RescueAI on Windows

## Prerequisites Check

Before starting, make sure you have:

- [ ] **Python 3.8+** - Check: Open CMD and type `python --version`
- [ ] **Node.js 16+** - Check: Open CMD and type `node --version`
- [ ] **npm** - Check: Open CMD and type `npm --version`

If any are missing:
- **Python**: Download from https://www.python.org/downloads/
- **Node.js & npm**: Download from https://nodejs.org/ (includes npm)

---

## Option 1: Automated Setup (Recommended - 2 minutes)

Just run the demo script which does everything automatically:

### Open Command Prompt and run:

```bat
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main
demo.bat
```

This will:
1. ✅ Set up Python virtual environment
2. ✅ Install all backend dependencies
3. ✅ Reset database with 40 sample reports + 12 teams
4. ✅ Start backend server on http://localhost:8000
5. ✅ Install frontend dependencies
6. ✅ Start frontend on http://localhost:5173

**Skip to "Access the Application" section below!**

---

## Option 2: Manual Setup (Step-by-Step)

If the automated script doesn't work, follow these steps:

### Step 1: Setup Backend (Python/FastAPI)

```bat
:: Navigate to backend folder
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\backend

:: Create virtual environment
python -m venv venv

:: Activate virtual environment
venv\Scripts\activate

:: Install dependencies
pip install -r requirements.txt

:: Copy environment configuration
copy .env.example .env

:: Create and seed database with sample data
python seed_data.py
```

### Step 2: Start Backend Server

In the same Command Prompt (with venv activated):

```bat
:: Start FastAPI server
python main.py
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

**✅ Keep this window open!**

---

### Step 3: Setup Frontend (React/Vite)

Open a **NEW** Command Prompt window:

```bat
:: Navigate to frontend folder
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\frontend

:: Install dependencies
npm install
```

### Step 4: Start Frontend Server

In the same Command Prompt:

```bat
:: Start Vite development server
npm run dev
```

You should see:
```
VITE v5.0.8  ready in XXX ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

**✅ Keep this window open too!**

---

## Access the Application

Now open your browser and visit:

### 🎯 Main Screens:

| URL | What you'll see |
|-----|-----------------|
| **http://localhost:5173** | Command Center Dashboard (responsive!) |
| **http://localhost:5173/report** | Citizen Report Form (PWA) |
| **http://localhost:8000/docs** | API Documentation (Swagger UI) |

---

## Testing the Responsive Design

### Using Chrome/Edge DevTools:

1. Open http://localhost:5173
2. Press **F12** (or right-click → Inspect)
3. Click the **device toolbar icon** (📱) or press **Ctrl+Shift+M**
4. Select different devices:
   - **iPhone SE** (375px) - Mobile view
   - **iPad Mini** (768px) - Tablet view
   - **Laptop** (1440px) - Desktop view

### What to Check:

**On Mobile (375px)**:
- ✅ Hamburger menu in navigation
- ✅ Bottom tab bar in Dashboard (Map/Queue/Overview/Report)
- ✅ Filters collapsed by default in Overview tab
- ✅ No horizontal scrolling
- ✅ All buttons are easy to tap (44x44px minimum)

**On Desktop (1440px)**:
- ✅ Full horizontal navigation bar
- ✅ 3-column layout (Sidebar | Map | Queue)
- ✅ Filters always visible
- ✅ All details fully expanded

---

## Testing PWA Installation

### On Chrome/Edge (Desktop):
1. Visit http://localhost:5173
2. Look for **Install** icon in address bar (⊕)
3. Click to install as standalone app
4. App should open in its own window without browser chrome

### On Mobile (Real Device):
1. Open http://localhost:5173 in mobile Chrome
2. Menu → **Add to Home Screen**
3. Name it "RescueAI" and confirm
4. App icon appears on home screen
5. Open from home screen - runs fullscreen without browser UI

### Testing Offline Mode:
1. Open DevTools → **Network** tab
2. Select **Offline** from throttling dropdown
3. Refresh page - should still load from cache
4. Try submitting a report - it queues for later delivery

---

## Quick Demo Steps

### 1. View Dashboard
- Open http://localhost:5173
- See 40 pre-loaded reports on map and in queue
- Try filtering by disaster type or urgency

### 2. Submit a New Report
- Go to http://localhost:5173/report
- Select disaster type (e.g., 🌊 Flood)
- Enter location and description
- Mark vulnerable people if needed
- Click "Send for Help"
- Switch back to dashboard - new report appears!

### 3. Simulate Disaster Burst
In a new Command Prompt:
```bat
curl -X POST http://localhost:8000/api/demo/simulate-burst
```
Watch 15 reports appear over 30 seconds on the dashboard!

### 4. Assign a Team
- Click any report on map or in queue
- Case detail panel opens
- Click "Assign" on a recommended team
- Status changes to "In Progress"

---

## Troubleshooting

### Backend won't start?

**Error: "Module not found"**
```bat
:: Make sure virtual environment is activated
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\backend
venv\Scripts\activate
pip install -r requirements.txt
```

**Error: "Port 8000 already in use"**
```bat
:: Check what's using port 8000
netstat -ano | findstr :8000

:: Kill the process (replace PID with actual number)
taskkill /PID <PID> /F
```

### Frontend won't start?

**Error: "npm: command not found"**
- Install Node.js from https://nodejs.org/

**Error: "ENOENT: no such file or directory"**
```bat
:: Make sure you're in the right folder
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\frontend
npm install
```

**Error: "Port 5173 already in use"**
- Kill the existing Vite process or use a different port:
```bat
npm run dev -- --port 5174
```

### Database issues?

**Reset everything:**
```bat
cd C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\backend
del rescueai.db
python seed_data.py
```

### Page shows "Mock Data" badge?

To use live API instead of mock data:
1. Open `frontend/src/data/mockData.js`
2. Change line 1: `export const USE_MOCK = false`
3. Save and refresh browser

---

## Stopping the Servers

### Stop Backend:
- Go to the backend Command Prompt window
- Press **Ctrl+C**
- Type `deactivate` to exit virtual environment

### Stop Frontend:
- Go to the frontend Command Prompt window
- Press **Ctrl+C**

---

## File Locations

Your project is located at:
```
C:\Users\vardh\Downloads\rescueai-sanskar\rescueai-main\
├── backend\          ← Python FastAPI server
├── frontend\         ← React frontend
├── demo.bat          ← Automated setup script
└── README.md         ← Full documentation
```

---

## Need Help?

1. **Check the logs** in the Command Prompt windows
2. **Check browser console** (F12 → Console tab) for errors
3. **Check API docs** at http://localhost:8000/docs to test endpoints
4. **Read the full README.md** for advanced features

---

## Next Steps

Once everything is running:

1. ✅ Test the responsive design at different screen sizes
2. ✅ Try the PWA installation
3. ✅ Submit test reports through the form
4. ✅ Test the offline mode
5. ✅ Explore the API documentation
6. ✅ Read `RESPONSIVE_IMPLEMENTATION.md` for detailed testing checklist

---

**🎉 You're all set! The application is now fully responsive and installable as a PWA!**
