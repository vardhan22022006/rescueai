# RescueAI API Endpoints Documentation

Complete API reference for the RescueAI disaster response management system.

## Base URL

```
http://localhost:8000/api
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 📊 Report Endpoints

### 1. List Reports (with Filters)

Get paginated list of reports with advanced filtering and sorting.

**Excludes duplicate reports** - only shows primary reports with their corroboration counts.

```http
GET /api/reports
```

**Query Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `status` | string | Filter by status: `new`, `in_progress`, `resolved`, `false_report` | None |
| `disaster_type` | string | Filter by type: `flood`, `earthquake`, `cyclone`, `other` | None |
| `min_score` | float | Minimum urgency score (0-100) | None |
| `sort` | string | Sort order: `urgency_desc`, `urgency_asc`, `created_desc`, `created_asc` | `urgency_desc` |
| `skip` | int | Pagination offset | 0 |
| `limit` | int | Max results per page | 50 |

**Example Request:**
```bash
GET /api/reports?status=new&min_score=70&limit=10
```

**Response:**
```json
{
  "reports": [
    {
      "id": "uuid",
      "disaster_type": "flood",
      "urgency_score": 75.5,
      "status": "new",
      "verification_status": "corroborated",
      "assigned_team": null,
      "num_people": 25,
      "vulnerable_flags": ["elderly", "child"],
      "corroboration_count": 3,
      "location": {
        "latitude": 23.5,
        "longitude": 87.5,
        "text": "Near railway station"
      },
      "created_at": "2026-07-07T05:30:00Z",
      "updated_at": "2026-07-07T05:45:00Z",
      "age_hours": 2.5
    }
  ],
  "count": 10,
  "total": 55,
  "skip": 0,
  "limit": 10,
  "has_more": true
}
```

---

### 2. Get Report Details

Get full details of a single report including duplicate cluster information.

```http
GET /api/reports/{report_id}
```

**Response:**
```json
{
  "id": "uuid",
  "source": "app",
  "raw_text": "Severe flooding in residential area...",
  "language": "en",
  "translated_text": "Severe flooding in residential area...",
  "reporter_phone": "+919876543210",
  "disaster_type": "flood",
  "location": {
    "latitude": 23.5,
    "longitude": 87.5,
    "location_text": "Near railway station"
  },
  "num_people": 25,
  "vulnerable_flags": ["elderly", "child"],
  "verification_status": "corroborated",
  "urgency": {
    "score": 75.5,
    "breakdown": {
      "factors": {
        "people": {"score": 20, "explanation": "25 people affected (log-scaled)"},
        "vulnerable": {"score": 30, "explanation": "2 vulnerable groups: elderly, child"},
        "verification": {"score": 10, "explanation": "Corroborated by 2 additional reports"},
        "corroboration": {"score": 10, "explanation": "3 corroborating reports"},
        "time_decay": {"score": 5, "explanation": "2.5 hours old, slight urgency increase"}
      },
      "base_score": 75,
      "multiplier": {"value": 1.0, "explanation": "Flood (baseline multiplier)"},
      "final_score": 75.5,
      "summary": "High urgency: Multiple vulnerable groups, corroborated"
    },
    "explanation": {...}
  },
  "status": "new",
  "assigned_team": null,
  "corroboration_count": 3,
  "duplicate_info": {
    "is_duplicate": false,
    "is_duplicate_of": null,
    "primary_report": null,
    "duplicate_cluster": [
      {
        "id": "dup-uuid-1",
        "raw_text": "Flooding near station, many people trapped...",
        "num_people": 10,
        "vulnerable_flags": ["child"],
        "created_at": "2026-07-07T05:40:00Z",
        "reporter_phone": "+919876543211"
      }
    ],
    "total_duplicates": 3
  },
  "created_at": "2026-07-07T05:30:00Z",
  "updated_at": "2026-07-07T05:45:00Z"
}
```

---

### 3. Update Report Status

Manually update a report's status.

```http
PATCH /api/reports/{report_id}/status
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `new_status` | string | Yes | New status: `new`, `in_progress`, `resolved`, `false_report` |

**Example Request:**
```bash
PATCH /api/reports/uuid/status?new_status=resolved
```

**Response:**
```json
{
  "success": true,
  "report_id": "uuid",
  "old_status": "in_progress",
  "new_status": "resolved",
  "updated_at": "2026-07-07T06:00:00Z"
}
```

---

## 📈 Statistics Endpoints

### 4. Get Dashboard Summary

Get comprehensive statistics for the dashboard.

```http
GET /api/stats/summary
```

**Response:**
```json
{
  "reports": {
    "total_active": 55,
    "total_all": 71,
    "by_disaster_type": {
      "flood": 22,
      "earthquake": 14,
      "cyclone": 13,
      "other": 6
    },
    "by_verification_status": {
      "unverified": 20,
      "corroborated": 15,
      "satellite_confirmed": 7,
      "weather_confirmed": 7,
      "rejected": 6
    },
    "by_status": {
      "new": 32,
      "in_progress": 23,
      "resolved": 8,
      "false_report": 8
    },
    "average_urgency": 44.1,
    "vulnerable_unresolved": 27,
    "high_urgency_count": 5
  },
  "teams": {
    "total": 24,
    "available": 13,
    "deployed": 11,
    "by_type": {
      "NDRF": 6,
      "SDRF": 6,
      "NGO": 6,
      "volunteer": 6
    },
    "utilization_rate": 45.8
  },
  "timestamp": "2026-07-07T06:00:00Z"
}
```

**Use Cases:**
- Dashboard overview widgets
- Real-time system status monitoring
- Resource allocation planning
- Performance metrics tracking

---

## 👥 Team Endpoints

### 5. List Teams

Get list of response teams with optional filtering.

```http
GET /api/teams
```

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by: `available`, `deployed` |
| `team_type` | string | Filter by: `NDRF`, `SDRF`, `NGO`, `volunteer` |

**Example Request:**
```bash
GET /api/teams?status=available&team_type=NDRF
```

**Response:**
```json
{
  "teams": [
    {
      "id": "uuid",
      "name": "NDRF Alpha Team",
      "type": "NDRF",
      "capacity": 25,
      "status": "available",
      "location": {
        "latitude": 23.5,
        "longitude": 87.5
      }
    }
  ],
  "total": 24,
  "filtered": 6
}
```

---

### 6. Get Team Details

Get detailed information about a specific team including workload.

```http
GET /api/teams/{team_id}
```

**Response:**
```json
{
  "id": "uuid",
  "name": "NDRF Alpha Team",
  "type": "NDRF",
  "capacity": 25,
  "status": "available",
  "location": {
    "latitude": 23.5,
    "longitude": 87.5
  },
  "workload": {
    "active_assignments": 0,
    "total_resolved": 12,
    "current_utilization": 0
  },
  "created_at": "2026-07-06T00:00:00Z"
}
```

---

## 🚁 Dispatch Endpoints

### 7. Get Dispatch Recommendations

Get top 3 nearest available teams for a report.

```http
GET /api/reports/{report_id}/recommend-dispatch
```

**Response:**
```json
{
  "report_id": "uuid",
  "disaster_type": "flood",
  "urgency_score": 75.5,
  "location": {
    "latitude": 23.5,
    "longitude": 87.5
  },
  "recommendations": [
    {
      "team_id": "uuid",
      "team_name": "NDRF Alpha Team",
      "team_type": "NDRF",
      "capacity": 25,
      "distance_km": 2.4,
      "eta_estimate": "~4 min"
    },
    {
      "team_id": "uuid",
      "team_name": "SDRF Beta Team",
      "team_type": "SDRF",
      "capacity": 20,
      "distance_km": 5.1,
      "eta_estimate": "~8 min"
    }
  ],
  "total_available_teams": 13,
  "message": "Found 2 team(s) nearby"
}
```

---

### 8. Assign Team to Report

Assign a team to handle a report.

```http
POST /api/reports/{report_id}/assign
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `team_id` | string | Yes | UUID of team to assign |

**Example Request:**
```bash
POST /api/reports/uuid/assign?team_id=team-uuid
```

**Response:**
```json
{
  "success": true,
  "report_id": "uuid",
  "team_id": "team-uuid",
  "team_name": "NDRF Alpha Team",
  "assignment": {
    "report_status": "in_progress",
    "team_status": "deployed",
    "assigned_at": "2026-07-07T06:00:00Z"
  }
}
```

---

### 9. Get Dispatch Summary

Get overview of dispatch system status.

```http
GET /api/dispatch/summary
```

**Response:**
```json
{
  "teams": {
    "total_teams": 24,
    "available": 13,
    "deployed": 11,
    "by_type": {
      "NDRF": 6,
      "SDRF": 6,
      "NGO": 6,
      "volunteer": 6
    }
  },
  "reports": {
    "total_active": 60,
    "unassigned": 36,
    "assigned": 24,
    "new": 35,
    "in_progress": 25
  },
  "utilization": {
    "team_deployment_rate": 45.8,
    "report_assignment_rate": 40.0
  }
}
```

---

## 🔧 System Endpoints

### 10. Health Check

Check API health and background scheduler status.

```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-07-07T06:00:00Z",
  "service": "rescueai-api",
  "scheduler": {
    "running": true,
    "jobs": [
      {
        "name": "rescore_reports",
        "next_run": "2026-07-07T06:05:00Z"
      }
    ]
  }
}
```

---

## 🔒 CORS Configuration

The API allows requests from:
- `http://localhost:5173` (Vite default)
- `http://localhost:5174` (Vite alternate)
- `http://localhost:3000` (React default)

All methods (`GET`, `POST`, `PATCH`, `DELETE`) and headers are allowed.

---

## 📝 Error Responses

All endpoints return standardized error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid status. Valid values: new, in_progress, resolved, false_report"
}
```

### 404 Not Found
```json
{
  "detail": "Report not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error message"
}
```

---

## 🧪 Testing

### Run All Tests

```bash
# API endpoint tests
pytest test_api.py -v

# Deduplication tests
python test_dedup.py

# Scoring tests
python test_scoring.py

# Quick endpoint verification
python test_endpoints.py
```

### Test Coverage

- ✅ Report CRUD operations
- ✅ Filtering and pagination
- ✅ Duplicate report exclusion
- ✅ Status updates
- ✅ Statistics aggregation
- ✅ Team management
- ✅ Dispatch recommendations
- ✅ Team assignment workflow

---

## 📊 Key Features

### 1. Duplicate Report Handling
- Reports marked as duplicates (`is_duplicate_of != null`) are **automatically excluded** from list endpoints
- Only primary reports shown with their `corroboration_count`
- Duplicate cluster members accessible via detail endpoint

### 2. Transparent Urgency Scoring
- Every report includes full `urgency_breakdown` with scoring explanation
- Judges and stakeholders can see exactly how scores are calculated
- No black-box algorithms

### 3. Real-time Statistics
- Dashboard stats updated in real-time
- Background scheduler re-scores reports every 5 minutes
- Team utilization rates calculated automatically

### 4. Flexible Filtering
- Combine multiple filters: `status`, `disaster_type`, `min_score`
- Sort by urgency or creation time
- Pagination support for large datasets

---

## 🚀 Quick Start Examples

### Get High-Priority Unassigned Floods
```bash
curl "http://localhost:8000/api/reports?disaster_type=flood&status=new&min_score=70"
```

### Get Dashboard Stats
```bash
curl "http://localhost:8000/api/stats/summary"
```

### Update Report to Resolved
```bash
curl -X PATCH "http://localhost:8000/api/reports/{id}/status?new_status=resolved"
```

### Find Nearest Teams
```bash
curl "http://localhost:8000/api/reports/{id}/recommend-dispatch"
```

---

## 📚 Related Documentation

- [Backend Pipeline README](app/pipeline/README.md) - Scoring, dedup, verification details
- [Main README](../README.md) - Project overview and setup
- [Swagger Docs](http://localhost:8000/docs) - Interactive API testing
