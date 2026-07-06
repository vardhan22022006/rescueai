# 🚨 RescueAI - Disaster Response Management System

RescueAI is an intelligent disaster response management system designed to help emergency response teams coordinate relief efforts effectively during natural disasters. The system aggregates reports from multiple channels (SMS, WhatsApp, voice, mobile app), performs intelligent triage, detects duplicates, and coordinates response teams.

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI with Python
- **Database**: SQLite with SQLAlchemy ORM
- **Migrations**: Alembic
- **API Documentation**: Auto-generated OpenAPI/Swagger docs at `/docs`

### Frontend (React + Vite)
- **Framework**: React 18
- **Build Tool**: Vite 5
- **Styling**: Tailwind CSS
- **Dev Server**: Hot reload enabled

## 📋 Features

### Report Management
- Multi-channel report ingestion (app, SMS, WhatsApp, voice)
- Multi-language support with translation tracking
- GPS coordinates and text-based location
- Disaster type classification (flood, earthquake, cyclone, other)
- Vulnerable population flagging (elderly, children, pregnant, disabled)
- **Intelligent duplicate detection and linking**
  - Geo-proximity detection (300m radius, same disaster type, 6-hour window)
  - Text similarity analysis (TF-IDF cosine similarity > 0.6)
  - Corroboration system (duplicates increase confidence, not discarded)
  - Automatic merging of people counts and vulnerability flags
- Multi-level verification system (satellite, weather, corroboration)
- Urgency scoring algorithm (boosted by corroboration)

### Team Coordination
- Multiple team types (NDRF, SDRF, NGO, volunteer)
- Real-time location tracking
- Capacity management
- Deployment status tracking
- Team assignment to reports

## 📊 Database Schema

### Report Model
- `id` - UUID primary key
- `source` - Enum: app, sms, whatsapp, voice
- `raw_text` - Original message/transcript
- `language` - Detected language code
- `translated_text` - Translation if needed
- `reporter_phone` - Contact number
- `latitude/longitude` - GPS coordinates
- `location_text` - Free-text location description
- `disaster_type` - Enum: flood, earthquake, cyclone, other
- `num_people` - Number of people affected
- `vulnerable_flags` - JSON array of vulnerability tags
- `is_duplicate_of` - Foreign key to original report
- `corroboration_count` - Number of duplicate reports corroborating this incident
- `verification_status` - Enum: unverified, corroborated, satellite_confirmed, weather_confirmed, rejected
- `urgency_score` - Float 0-1 priority score
- `status` - Enum: new, in_progress, resolved, false_report
- `assigned_team` - Team name handling the report
- `created_at/updated_at` - Timestamps

### Team Model
- `id` - UUID primary key
- `name` - Team name
- `type` - Enum: NDRF, SDRF, NGO, volunteer
- `capacity` - Number of personnel
- `current_location_lat/lon` - Current GPS position
- `status` - Enum: available, deployed
- `created_at/updated_at` - Timestamps

## 🚀 Getting Started

### Prerequisites

**Backend:**
- Python 3.8+
- pip (Python package manager)

**Frontend:**
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd rescueai/backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Copy the example file
   cp .env.example .env
   # Edit .env if needed (default values work for local development)
   ```

5. **Initialize database with seed data:**
   ```bash
   python seed_data.py
   ```
   This will:
   - Create all database tables
   - Generate 12 response teams (NDRF, SDRF, NGO, volunteer types)
   - Create 40 realistic disaster reports with:
     - 16 flood reports
     - 12 earthquake reports
     - 9 cyclone reports
     - 3 other disaster reports
   - Mix of verification statuses, urgency levels, and vulnerable populations
   - 5 reports marked as duplicates

6. **Run the development server:**
   ```bash
   uvicorn main:app --reload
   ```
   Backend API will be available at: http://localhost:8000
   API documentation at: http://localhost:8000/docs

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd rescueai/frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Run the development server:**
   ```bash
   npm run dev
   ```
   Frontend will be available at: http://localhost:5173

## 🔍 Deduplication System

RescueAI includes an intelligent deduplication pipeline that identifies and merges duplicate reports while preserving valuable information.

### How It Works

The system uses **two independent signals** to detect duplicates:

1. **Geo-Proximity Detection**
   - Reports within **300 meters** of each other
   - Same disaster type
   - Within a **6-hour time window**

2. **Text Similarity Detection**
   - Cosine similarity > **0.6** between TF-IDF vectors
   - Works on translated_text or raw_text
   - Uses scikit-learn for analysis

### Corroboration, Not Deletion

Instead of discarding duplicates, the system:
- Marks duplicates but **keeps them in the database**
- **Increments corroboration_count** on the original report
- **Merges people counts** from all duplicates
- **Combines vulnerable_flags** (unique values)
- **Boosts urgency_score** (+0.1 per corroboration, max 1.0)
- **Upgrades verification** to "corroborated" status

### Testing Deduplication

```bash
cd backend
python test_dedup.py
```

See `backend/app/pipeline/README.md` for detailed documentation.

## 🔌 API Endpoints

### Health Check
- `GET /` - Root endpoint with API info
- `GET /api/health` - Health check endpoint

### Future Endpoints (to be implemented)
- `GET /api/reports` - List all reports with filters
- `GET /api/reports/{id}` - Get specific report
- `POST /api/reports` - Create new report
- `PATCH /api/reports/{id}` - Update report
- `GET /api/teams` - List all teams
- `GET /api/teams/{id}` - Get specific team
- `PATCH /api/teams/{id}` - Update team status/location

## 🗂️ Project Structure

```
rescueai/
├── backend/
│   ├── alembic/                 # Database migrations
│   │   ├── versions/            # Migration scripts
│   │   └── env.py               # Alembic configuration
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── database.py          # Database connection
│   │   ├── models.py            # SQLAlchemy models
│   │   └── pipeline/            # Processing pipelines
│   │       ├── __init__.py
│   │       ├── dedup.py         # Deduplication logic
│   │       └── README.md        # Pipeline documentation
│   ├── .env                     # Environment variables
│   ├── .env.example             # Example environment file
│   ├── .gitignore
│   ├── alembic.ini              # Alembic config
│   ├── config.py                # Application config
│   ├── main.py                  # Entry point
│   ├── requirements.txt         # Python dependencies
│   ├── seed_data.py             # Database seeding script
│   └── test_dedup.py            # Deduplication tests
├── frontend/
│   ├── public/                  # Static assets
│   ├── src/
│   │   ├── App.jsx              # Main React component
│   │   ├── index.css            # Tailwind styles
│   │   └── main.jsx             # React entry point
│   ├── .gitignore
│   ├── index.html               # HTML entry point
│   ├── package.json             # NPM dependencies
│   ├── postcss.config.js        # PostCSS config
│   ├── tailwind.config.js       # Tailwind config
│   └── vite.config.js           # Vite config
└── README.md                    # This file
```

## 🧪 Testing the Setup

1. **Test Backend:**
   - Visit http://localhost:8000
   - Visit http://localhost:8000/api/health
   - Visit http://localhost:8000/docs for interactive API documentation

2. **Test Frontend:**
   - Visit http://localhost:5173
   - Check that the system status shows "Backend API: Connected"
   - Verify the health check timestamp updates

## 🔧 Database Management

### Using Alembic for Migrations

Create a new migration after model changes:
```bash
cd backend
alembic revision --autogenerate -m "Description of changes"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

### Reset Database

To reset and reseed the database:
```bash
cd backend
# Delete the database file
rm rescueai.db
# Reseed
python seed_data.py
```

## 📦 Building for Production

### Backend
```bash
cd backend
# Install dependencies
pip install -r requirements.txt
# Run with production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm run build
# Serve the dist/ folder with any static file server
npm run preview  # Preview production build locally
```

## 🛠️ Technology Stack

**Backend:**
- FastAPI 0.109.0
- SQLAlchemy 2.0.25
- Alembic 1.13.1
- Uvicorn 0.27.0
- Faker 22.0.0 (for seed data)
- Pydantic 2.5.3
- scikit-learn 1.3.2 (for deduplication)

**Frontend:**
- React 18.2.0
- Vite 5.0.8
- Tailwind CSS 3.4.0
- PostCSS & Autoprefixer

## 🎯 Next Steps

To extend this project, consider implementing:

1. **API Endpoints**: Add CRUD operations for reports and teams
2. **Dashboard UI**: Create interactive dashboard with maps and charts
3. **Real-time Updates**: Implement WebSocket for live report updates
4. **Authentication**: Add user authentication and role-based access
5. **Map Integration**: Integrate mapping library (Leaflet, Mapbox) for visualization
6. **Analytics**: Add reporting and analytics features
7. **Mobile App**: Develop mobile app for field reporting
8. **SMS Integration**: Connect to SMS gateway for report ingestion
9. **AI/ML Features**: 
   - Automatic language detection and translation
   - Duplicate detection algorithm
   - Urgency score calculation
   - Location extraction from text
10. **External Integrations**:
    - Weather API for verification
    - Satellite imagery API
    - Government alert systems

## 📝 License

This project is created for disaster response management and humanitarian purposes.

## 🤝 Contributing

Contributions are welcome! This is a humanitarian project aimed at improving disaster response coordination.

## 📧 Support

For questions or issues, please open an issue in the project repository.

---

**Built with ❤️ for disaster response teams worldwide**
