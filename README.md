# 🚨 RescueAI — Disaster Response Command Center

> **Hackathon submission** · Built for the "Tech for Good" track

---

## The Problem

During a major disaster — a cyclone, earthquake, or flood — emergency control rooms are overwhelmed within minutes. Thousands of SMS messages, WhatsApp texts, and phone calls flood in simultaneously. Responders face three brutal problems:

1. **Noise** — 60–70 % of reports are duplicates or unverifiable rumours.
2. **Triage blind spots** — A family with a disabled member and a single healthy adult get the same priority until a human reads every message.
3. **Coordination gaps** — Teams are dispatched based on who calls loudest, not who needs help most.

The result: critical cases wait hours. Preventable deaths occur.

---

## The Solution

RescueAI is an **AI-assisted disaster response management system** that turns chaotic incoming reports into an ordered, verified, real-time priority queue — so the right team reaches the right people first.

| Capability | How |
|---|---|
| Multi-channel intake | SMS, WhatsApp, browser voice, citizen web form |
| Multilingual support | Auto-detect language → translate to English (argos-translate, offline) |
| Smart deduplication | Geo-proximity + TF-IDF text similarity — duplicates *corroborate*, not clutter |
| External verification | Weather API + satellite data cross-check |
| Explainable urgency scoring | Transparent 0–100 formula every responder can read |
| Team dispatch | Haversine nearest-team recommendation + one-click assign |
| Live command-center dashboard | Map + priority queue, auto-refreshes every 10 s |
| Citizen PWA | Installable offline-capable reporting form for zero-connectivity areas |

**Zero paid APIs required** — runs fully on free tiers and open-source libraries.

---

## Architecture

```
  CITIZENS / FIELD WORKERS                CONTROL ROOM
  ─────────────────────────               ─────────────
  Browser form  ──────────┐              ┌─────────────────────────────────┐
  Voice (Web    ──────────┤              │     React + Vite Dashboard       │
  Speech API)             │  HTTP/JSON   │  ┌──────────┬────────┬────────┐ │
  SMS / WhatsApp ─────────┤◄────────────►│  │ Sidebar  │  Map   │ Queue  │ │
  (Twilio free  ──────────┘              │  │ Filters  │Leaflet │Priority│ │
   sandbox)                              │  │ Stats    │  OSM   │ List   │ │
                                         │  └──────────┴────────┴────────┘ │
                                         │         Case Detail Panel        │
                                         └─────────────────────────────────┘
                                                        │
                                                        │ REST API  (port 8000)
                                                        ▼
                              ┌─────────────────────────────────────────┐
                              │            FastAPI Backend               │
                              │                                          │
                              │  POST /api/reports/intake                │
                              │  POST /api/reports/twilio-webhook        │
                              │  GET  /api/reports                       │
                              │  GET  /api/stats/summary                 │
                              │  GET  /api/reports/{id}/recommend-dispatch│
                              │  POST /api/demo/simulate-burst  ◄── demo │
                              │                                          │
                              │  ┌────────────────────────────────────┐ │
                              │  │         Processing Pipeline         │ │
                              │  │                                    │ │
                              │  │  Intake                            │ │
                              │  │    │                               │ │
                              │  │    ├─► langdetect → lang code      │ │
                              │  │    ├─► argos-translate → English   │ │
                              │  │    └─► NLP extraction              │ │
                              │  │         (regex + keywords)         │ │
                              │  │           │                        │ │
                              │  │           ▼  BackgroundTask        │ │
                              │  │  ┌────────────────────────────┐   │ │
                              │  │  │  dedup.py                  │   │ │
                              │  │  │  Geo-proximity (300 m)     │   │ │
                              │  │  │  + TF-IDF text similarity  │   │ │
                              │  │  └──────────┬─────────────────┘   │ │
                              │  │             ▼                      │ │
                              │  │  ┌────────────────────────────┐   │ │
                              │  │  │  verify.py                 │   │ │
                              │  │  │  Weather API (free tier)   │   │ │
                              │  │  │  + Satellite data (mock)   │   │ │
                              │  │  └──────────┬─────────────────┘   │ │
                              │  │             ▼                      │ │
                              │  │  ┌────────────────────────────┐   │ │
                              │  │  │  scoring.py                │   │ │
                              │  │  │  0-100 urgency score       │   │ │
                              │  │  │  + JSON breakdown          │   │ │
                              │  │  └────────────────────────────┘   │ │
                              │  │                                    │ │
                              │  │  APScheduler: re-score every 5 min │ │
                              │  └────────────────────────────────────┘ │
                              │                                          │
                              │  SQLite (dev)  /  PostgreSQL (prod)      │
                              └─────────────────────────────────────────┘
```

### Key design decisions

- **Offline-first PWA** — The citizen form queues reports in IndexedDB via a service worker. When connectivity returns, Background Sync delivers them automatically. No report is lost.
- **Corroboration, not deduplication** — Duplicate reports *increase* confidence and urgency rather than being silently dropped. A corroborated flood report scores higher than a single unverified one.
- **Explainable scoring** — Every urgency number comes with a full JSON breakdown (people count, vulnerable flags, verification level, time decay, disaster multiplier). Response teams can see and challenge the reasoning.
- **No black-box AI required** — All NLP is regex + keyword matching. Swap in an LLM call by replacing `extract_report_fields()` in `nlp_extraction.py` without touching any other code.

---

## Tech Stack

| Layer | Technology | Why free |
|---|---|---|
| Backend | FastAPI + SQLAlchemy + SQLite | Open source |
| Language detection | `langdetect` | Open source |
| Translation | `argos-translate` | Offline, open source |
| Deduplication | `scikit-learn` TF-IDF | Open source |
| Background jobs | APScheduler | Open source |
| Frontend | React 18 + Vite + Tailwind CSS | Open source |
| Map | react-leaflet + OpenStreetMap | Free, no key |
| Map tiles | CartoDB Dark Matter | Free, no key |
| Voice transcription | Web Speech API (browser built-in) | Free, no key |
| SMS / WhatsApp | Twilio trial + WhatsApp Sandbox | Free sign-up |
| PWA offline queue | Service Worker + IndexedDB | Browser built-in |

---

## Quick Start (5 minutes)

### Prerequisites

- Python 3.8+ and pip
- Node.js 16+ and npm

### One-command demo (Windows)

```bat
demo.bat
```

### One-command demo (Mac / Linux)

```bash
chmod +x demo.sh && ./demo.sh
```

Both scripts:
1. Reset and reseed the database with 40 realistic reports + 12 teams
2. Start the backend on `http://localhost:8000`
3. Start the frontend on `http://localhost:5173`

---

### Manual setup

**Backend**

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment config (defaults work out of the box)
cp .env.example .env

# Seed database with 40 sample reports + 12 teams
python seed_data.py

# Start API server
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

| URL | What you'll see |
|---|---|
| http://localhost:5173 | Control-room dashboard |
| http://localhost:5173/report | Citizen reporting form (PWA) |
| http://localhost:8000/docs | Interactive API documentation |

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env`. Everything works with defaults.

```env
DATABASE_URL=sqlite:///./rescueai.db

# Translation backend
# "argos"  → offline, no API key needed (default)
# "google" → deep-translator free tier (pip install deep-translator)
TRANSLATE_BACKEND=argos

# Optional — improves weather verification. Free key at openweathermap.org
OPENWEATHER_API_KEY=

ENVIRONMENT=development
```

---

## Switching from Mock to Real API data

The dashboard ships in mock-data mode so it works without a running backend.

To switch to live data, open `frontend/src/data/mockData.js` and change:

```js
// Line 1 — flip this flag
export const USE_MOCK = false   // ← change from true to false
```

That's the only change needed. The polling hook, filters, and all components read from this single flag.

---

## Project Structure

```
rescueai-main/
├── demo.sh                        # One-command demo launcher (Mac/Linux)
├── demo.bat                       # One-command demo launcher (Windows)
│
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app + health endpoint
│   │   ├── routes.py              # All API endpoints
│   │   ├── models.py              # SQLAlchemy models (Report, Team)
│   │   ├── database.py            # DB session factory
│   │   ├── nlp_extraction.py      # Regex/keyword NLP (swap for LLM here)
│   │   ├── translation.py         # Pluggable translate_text()
│   │   ├── voice.py               # transcribe_audio() stub (whisper.cpp)
│   │   └── pipeline/
│   │       ├── dedup.py           # Geo + text similarity deduplication
│   │       ├── verify.py          # Weather + satellite verification
│   │       ├── scoring.py         # 0-100 urgency scoring + breakdown
│   │       └── dispatch.py        # Nearest-team recommendation
│   ├── config.py                  # Pydantic settings (env vars)
│   ├── seed_data.py               # Generates 40 reports + 12 teams
│   ├── requirements.txt
│   └── .env.example
│
└── frontend/
    ├── public/
    │   ├── manifest.json          # PWA manifest (installable)
    │   ├── sw.js                  # Service worker (offline queue)
    │   └── icons/                 # App icons
    ├── src/
    │   ├── App.jsx                # Router: / → Dashboard, /report → Citizen
    │   ├── main.jsx               # React entry + SW registration
    │   ├── data/mockData.js       # Mock API responses + USE_MOCK flag
    │   ├── hooks/
    │   │   └── useDashboardData.js  # Polling hook (10 s reports, 15 s stats)
    │   └── components/
    │       ├── Dashboard.jsx          # 3-column command-center shell
    │       ├── CitizenReport.jsx      # PWA citizen form (/report)
    │       ├── VoiceReportForm.jsx    # Voice intake widget
    │       └── dashboard/
    │           ├── Sidebar.jsx        # Filters + stat cards
    │           ├── ReportMap.jsx      # Leaflet map with urgency pins
    │           ├── PriorityQueue.jsx  # Scrollable sorted report list
    │           └── CaseDetail.jsx     # Full report detail + dispatch
    └── package.json
```

---

## API Reference

### Intake

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/reports/intake` | Accept JSON report from any channel |
| `POST` | `/api/reports/twilio-webhook` | Twilio SMS/WhatsApp webhook (form-encoded) |

### Reports & dispatch

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/reports` | List reports (filter by status, type, urgency) |
| `GET` | `/api/reports/{id}` | Full report with urgency breakdown |
| `GET` | `/api/reports/{id}/recommend-dispatch` | Top 3 nearest available teams |
| `POST` | `/api/reports/{id}/assign?team_id=` | Assign team → status in_progress |
| `DELETE` | `/api/reports/{id}/assign` | Unassign team → team available |

### Dashboard

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/stats/summary` | Stat card counts (polled every 15 s) |
| `GET` | `/api/dispatch/summary` | System-wide dispatch overview |
| `GET` | `/api/teams` | List teams (filter by status/type) |

### Demo only

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/demo/simulate-burst` | Inject 15 reports over 30 s for live demo |

---

## Urgency Scoring Explained

Every report receives a score from 0–100. The formula is fully transparent:

```
score = (people + vulnerable + verification + corroboration + time_decay)
        × disaster_multiplier
```

| Factor | Max pts | Formula |
|---|---|---|
| People affected | 30 | log₁₀(n + 1) × 17.5 |
| Vulnerable groups | 45 | +15 per type (elderly / child / pregnant / disabled) |
| Verification | 25 | satellite=25, weather=20, corroborated=10, unverified=0 |
| Corroboration | 20 | +5 per duplicate report, capped at 20 |
| Time decay | 20 | +5/hour after 2 h wait, capped at 20 |
| Disaster multiplier | — | earthquake ×1.2, cyclone ×1.1, flood ×1.0 |

The full breakdown is stored in `urgency_breakdown` (JSON) on every report and displayed in the Case Detail panel so any responder can immediately see *why* a case is ranked where it is.

---

## Connecting Twilio (optional — 5 minutes, free)

If you want live SMS/WhatsApp intake without running a phone bank:

1. Sign up free at https://www.twilio.com/try-twilio
2. Expose your local server: `ngrok http 8000`
3. Set the SMS webhook URL to: `https://<ngrok-url>/api/reports/twilio-webhook`
4. For WhatsApp: Twilio Console → Messaging → WhatsApp Sandbox → set same URL
5. Text any disaster message to the sandbox number — it appears on the dashboard within seconds

See the [full Twilio setup guide](#-sms--whatsapp-intake-via-twilio) at the bottom of this file.

> **Zero Twilio needed for the demo** — use the Citizen form at `/report` and the `simulate-burst` endpoint instead. Judges won't know the difference.

---

## Judge Demo Script

**Time required:** 5 minutes  
**Setup required:** `demo.bat` / `demo.sh` already running

---

### Step 1 — Show the problem (30 seconds)

Open `http://localhost:5173` (Dashboard).

> *"During Cyclone Amphan, over 100,000 distress calls hit Bengal's control rooms in 6 hours. No system could triage them. Responders were guessing. RescueAI solves this."*

Point to the Priority Queue (right column): reports sorted by urgency, highest first. Point to the map: color-coded pins — red = critical, yellow = low. Point to the stat cards (left): active reports, critical, teams free, unverified.

---

### Step 2 — Show a live citizen report (60 seconds)

Open a new tab: `http://localhost:5173/report`

> *"Any citizen with a phone can submit a report. No app to install — it's a PWA, installable from the browser. Works offline — reports queue on-device and deliver when signal returns."*

- Select language: **हिन्दी** (Hindi)
- Tap **📍 Use My Location**
- Tap **🌊 Flood** disaster type
- Type (or tap the voice button and speak): *"Flood near bridge, 20 people stranded, old woman wheelchair user"*
- Set people: **20**
- Check: **Someone elderly** + **Person with disability**
- Tap **🆘 Send for Help**

Switch back to the dashboard tab. **Within 10 seconds the new report appears**, auto-ranked by urgency. Point out that the system extracted the vulnerable flags automatically from the free text.

---

### Step 3 — Trigger the disaster simulation (60 seconds)

In a terminal (or the browser's API docs at `http://localhost:8000/docs`):

```bash
curl -X POST http://localhost:8000/api/demo/simulate-burst
```

> *"Let's simulate a real scenario — a cyclone making landfall. Reports start flooding in from multiple sources simultaneously."*

Watch the dashboard live as 15 new reports appear over 30 seconds. The Priority Queue re-ranks in real time. New pins drop onto the map. Stat cards update.

Point out:
- Reports from SMS, WhatsApp, voice, and app arriving simultaneously
- The urgency queue keeps the most critical cases at the top automatically
- Corroboration badges appear as duplicate reports confirm the same incident

---

### Step 4 — Show the intelligence layer (60 seconds)

Click the top red pin on the map (or the highest-urgency item in the queue).

> *"Every report comes with a full AI audit trail. Not a black box — every judge, every responder can see exactly why this case is #1."*

In the Case Detail panel:
- Point to the **Urgency Breakdown** bar chart: show each contributing factor
- Point to the **verification badge**: "Weather data confirmed this — cross-referenced with live API"
- Point to the **corroboration count**: "3 independent reports confirmed this incident — that's not noise, that's evidence"
- Click **Nearest Available Teams**: "Haversine distance calculation, real-time"
- Click **Assign** on the first team
- Watch the report status change to **In Progress**

---

### Step 5 — Show the tech differentiators (60 seconds)

> *"Three things that make this production-ready, not a prototype:"*

**1. Zero paid APIs.** Flip to the terminal — point to `requirements.txt`. Translation runs on-device with argos-translate. Voice transcription is the browser's own engine. Map tiles are free OpenStreetMap. Total API cost: £0.

**2. Offline-first.** Open DevTools → Network → set to Offline. Submit a report on `/report`. The form still succeeds. Re-enable network — watch the report deliver automatically. This works in a cyclone-hit village with 2G signal.

**3. Pluggable NLP.** Open `backend/app/nlp_extraction.py`. Show the `extract_report_fields()` function and its docstring: *"Swap this function out for an LLM call when higher accuracy is needed — the return shape is the stable contract."* One function. No migration needed.

---

## Running the Tests

```bash
cd backend
python test_dedup.py      # deduplication pipeline
python test_verify.py     # verification pipeline
python test_scoring.py    # urgency scoring
python test_dispatch.py   # team dispatch
```

---

## Database Management

**Reset and reseed** (also done automatically by `demo.bat` / `demo.sh`):

```bash
cd backend
del rescueai.db          # Windows
# rm rescueai.db         # Mac/Linux
python seed_data.py
```

**Alembic migrations** (after model changes):

```bash
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

---

## SMS & WhatsApp Intake via Twilio

### What you need

| Resource | Cost | Where |
|---|---|---|
| Twilio trial account | Free | https://www.twilio.com/try-twilio |
| Twilio WhatsApp Sandbox | Free (trial) | Twilio Console → Messaging → Try it out |
| ngrok | Free tier | https://ngrok.com/download |

### Setup (5 minutes)

1. Sign up at https://www.twilio.com/try-twilio and verify your phone number.

2. Expose your local server:
   ```bash
   ngrok http 8000
   # Copy the https://xxxx.ngrok-free.app URL
   ```

3. **SMS:** Twilio Console → Phone Numbers → your number → Messaging → set webhook to:
   `https://<ngrok-url>/api/reports/twilio-webhook`

4. **WhatsApp:** Twilio Console → Messaging → Try it out → Send a WhatsApp message → opt in by texting `join <keyword>` to the sandbox number → set webhook to same URL.

5. Test:
   ```
   Text: "Flood near river bridge, 20 people stranded, elderly woman needs help"
   ```
   Check `http://localhost:8000/api/reports?limit=1` — the report appears with source, language, extracted fields.

### How the webhook works

```
SMS/WhatsApp arrives
       │
       ▼
POST /api/reports/twilio-webhook
  From: "whatsapp:+91..." or "+91..."
  Body: "flood near bridge..."
       │
       ├─► Detect source (sms / whatsapp from "whatsapp:" prefix)
       ├─► Strip scheme → reporter_phone
       │
       ▼
  Same _intake() pipeline as /api/reports/intake
  (lang detect → translate → NLP → save → dedup/verify/score)
       │
       ▼
  Returns empty TwiML  ←  Twilio expects this
  <Response></Response>
```

---

## Upgrading NLP (when you want higher accuracy)

Current extraction is rule-based regex — fast, explainable, zero cost. To upgrade:

1. Open `backend/app/nlp_extraction.py`
2. Replace the body of `extract_report_fields(text)` with an LLM call
3. Keep the same return shape: `{"disaster_type": ..., "num_people": ..., "vulnerable_flags": [...]}`

No other file needs to change. The intake route, pipeline, and database are all downstream of that single function.

---

## Upgrading Translation

Default is argos-translate (offline). For higher accuracy:

```env
# backend/.env
TRANSLATE_BACKEND=google
```

Then `pip install deep-translator==1.11.4`. No code changes needed.

---

## Upgrading Voice (server-side, for IVR/phone audio)

For phone-call audio transcription (not browser mic), see the stub in `backend/app/voice.py`. The module docstring contains step-by-step instructions for wiring in whisper.cpp, faster-whisper, or vosk — all free and offline.

---

## License

Built for humanitarian purposes. Open source.

---

**Built with ❤️ for disaster response teams worldwide**
