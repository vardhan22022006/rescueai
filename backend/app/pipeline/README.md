# RescueAI Deduplication Pipeline

## Overview

The deduplication pipeline identifies and merges duplicate disaster reports while preserving valuable information. Instead of discarding duplicates, the system uses them to **corroborate** the original report, increasing confidence and urgency.

## How It Works

### Duplicate Detection Signals

The system uses **two independent signals** to identify duplicates:

#### 1. Geo-Proximity Detection
Reports are considered geo-proximate duplicates if ALL of the following are true:
- Within **300 meters** of each other (haversine distance)
- Same **disaster type** (flood, earthquake, cyclone, or other)
- Reported within a **6-hour time window**

**Use case:** Multiple people in the same neighborhood reporting the same flood event.

#### 2. Text Similarity Detection
Reports are considered text-similar duplicates if:
- **Cosine similarity > 0.6** between TF-IDF vectors of translated_text
- Uses scikit-learn's TfidfVectorizer with:
  - Unigrams and bigrams (ngram_range=(1, 2))
  - English stop words removed
  - Max 1000 features

**Use case:** Reports without GPS coordinates but describing the same incident in similar language.

### Matching Logic

- **Either signal triggering** is sufficient to mark reports as duplicates
- If multiple matches exist, the **earliest report** becomes the "original"
- Subsequent reports are marked as duplicates of the original

## What Happens to Duplicates

When a duplicate is detected, the system:

1. **Marks the duplicate**: Sets `is_duplicate_of` to the original report's ID
2. **Increments corroboration count**: Increases `corroboration_count` on the original
3. **Merges affected population**: Adds `num_people` from duplicate to original
4. **Merges vulnerable flags**: Combines unique vulnerability tags (elderly, child, pregnant, disabled)
5. **Upgrades verification status**: Changes from "unverified" to "corroborated" when corroborated
6. **Boosts urgency score**: Adds 0.1 per corroboration (capped at 1.0)
7. **Updates timestamp**: Sets `updated_at` on the original

### Example

**Original Report:**
- Location: (23.500, 87.500)
- Text: "Severe flooding in residential area"
- People: 10
- Vulnerable: ["elderly"]
- Corroboration count: 0
- Urgency score: 0.5

**Duplicate Report 1** (250m away, 1 hour later):
- Location: (23.502, 87.502)
- Text: "Water rising in neighborhood, families trapped"
- People: 5
- Vulnerable: ["child"]

**After merging:**
- People: 15 (10 + 5)
- Vulnerable: ["elderly", "child"]
- Corroboration count: 1
- Urgency score: 0.6 (0.5 + 0.1 boost)
- Verification: "corroborated" (upgraded from "unverified")

## Usage

### Basic Usage

```python
from app.database import SessionLocal
from app.models import Report
from app.pipeline.dedup import find_duplicates

# Create or receive a new report
new_report = Report(...)

# Check for duplicates
db = SessionLocal()
original = find_duplicates(new_report, db)

if original:
    print(f"Duplicate detected! Original report: {original.id}")
    print(f"Corroboration count: {original.corroboration_count}")
else:
    print("No duplicate found - this is a new incident")

db.close()
```

### Custom Thresholds

```python
# Stricter geo-proximity (100m instead of 300m)
original = find_duplicates(
    new_report, 
    db,
    geo_distance_threshold=100.0
)

# Higher text similarity requirement (0.8 instead of 0.6)
original = find_duplicates(
    new_report,
    db,
    text_similarity_threshold=0.8
)

# Shorter time window (2 hours instead of 6)
original = find_duplicates(
    new_report,
    db,
    time_window_hours=2
)
```

### Get Duplicate Information

```python
from app.pipeline.dedup import get_duplicate_info

info = get_duplicate_info(report, db)

if info['is_duplicate']:
    print(f"This is a duplicate of report {info['original_report_id']}")
elif info['is_original']:
    print(f"This report has {info['duplicate_count']} duplicates")
    print(f"Corroboration count: {info['corroboration_count']}")
```

## Database Schema Changes

### New Field: `corroboration_count`

Added to the `Report` model:

```python
corroboration_count = Column(Integer, nullable=False, default=0)
```

- **Type**: Integer
- **Default**: 0
- **Purpose**: Tracks how many duplicate reports corroborate this incident
- **Usage**: Higher counts indicate more reliable/urgent incidents

### Field Updates on Corroboration

| Field | Update Behavior |
|-------|----------------|
| `corroboration_count` | Incremented by 1 for each duplicate |
| `num_people` | Sum of all duplicates' num_people |
| `vulnerable_flags` | Union of all unique vulnerability tags |
| `verification_status` | Upgraded to "corroborated" if unverified |
| `urgency_score` | +0.1 per corroboration (max 1.0) |
| `updated_at` | Set to current timestamp |

## Testing

Run the test suite to verify deduplication functionality:

```bash
cd backend
python test_dedup.py
```

The test suite includes:
1. **Geo-proximity test**: Two reports 220m apart
2. **Text similarity test**: Reports with similar descriptions
3. **Multiple duplicates test**: 3 duplicates corroborating one original
4. **False positive test**: Ensuring different incidents aren't merged

## Performance Considerations

### Query Optimization

The `find_duplicates()` function:
- Only queries **unresolved reports** (new, in_progress)
- Excludes reports that are **themselves duplicates**
- Avoids self-comparison

### Scalability

For large databases, consider:
- Adding spatial indexes for lat/lon queries
- Caching TF-IDF vectorizer for repeated similarity checks
- Processing duplicates in batch/background jobs
- Using approximate nearest neighbor for text similarity

## Configuration

Default thresholds can be adjusted based on operational needs:

| Parameter | Default | Tuning Guidelines |
|-----------|---------|-------------------|
| `geo_distance_threshold` | 300m | Lower for dense urban areas, higher for rural |
| `time_window_hours` | 6 hours | Shorter for fast-moving disasters (flash floods) |
| `text_similarity_threshold` | 0.6 | Higher to reduce false positives |

## Integration Points

### API Endpoints (Future)

```python
@app.post("/api/reports")
async def create_report(report_data: ReportCreate, db: Session):
    # Create report
    new_report = Report(**report_data)
    db.add(new_report)
    db.commit()
    
    # Check for duplicates
    original = find_duplicates(new_report, db)
    
    if original:
        return {
            "report_id": new_report.id,
            "is_duplicate": True,
            "original_report_id": original.id,
            "corroboration_count": original.corroboration_count
        }
    else:
        return {
            "report_id": new_report.id,
            "is_duplicate": False
        }
```

### Background Processing

For SMS/WhatsApp ingestion:

```python
def process_incoming_report(message):
    # Parse message
    report = parse_message(message)
    
    # Save to database
    db.add(report)
    db.commit()
    
    # Async deduplication
    find_duplicates(report, db)
```

## Benefits

1. **No Information Loss**: All reports are preserved, none discarded
2. **Increased Confidence**: Multiple independent reports validate incidents
3. **Better Prioritization**: Corroboration count helps triage
4. **Accurate Headcounts**: People counts are summed, not lost
5. **Vulnerability Tracking**: All vulnerable groups identified
6. **Automatic Verification**: Multiple reports trigger "corroborated" status

## Limitations

1. **Language Dependency**: Text similarity works best with English translated_text
2. **GPS Requirement**: Geo-proximity requires both reports to have coordinates
3. **Time Window**: Reports outside 6-hour window won't be matched geographically
4. **Single Original**: Each duplicate links to only one original (earliest match)

## Future Enhancements

- Multi-language text similarity (beyond English)
- Machine learning for better similarity scoring
- Fuzzy location matching for text-based locations
- Clustering for multi-report incidents
- Real-time duplicate alerts to response teams
- Confidence scores based on reporter history


---

# RescueAI Verification Pipeline

## Overview

The verification pipeline cross-checks disaster reports against external data sources to assess authenticity and urgency. The system uses a **pluggable architecture** allowing easy integration with real APIs or fallback to mock data for zero-setup development.

## Core Philosophy

**⚠️ NEVER AUTO-REJECT REPORTS ⚠️**

False negatives cost lives. The verification system:
- Never marks reports as "rejected" automatically
- Only adjusts confidence and urgency scores
- Keeps unverified reports active in the system
- Slightly downweights unverified single reports (-0.05 urgency)

## Data Sources

### 1. Weather Alert Integration

**Function:** `get_weather_alert(lat, lon, disaster_type)`

**Real API:** OpenWeatherMap (Free Tier)
- 1,000 calls/day
- No credit card required
- Current conditions + weather alerts
- Get API key: https://openweathermap.org/api

**Setup:**
```bash
# Add to backend/.env
OPENWEATHER_API_KEY=your_key_here
```

**Mock Fallback:** If no API key configured, returns realistic mock data based on location

**Checks:**
- Active weather alerts for the location
- Current conditions (rainfall, wind speed)
- Matches disaster type to weather patterns

### 2. Satellite Data Integration

**Function:** `get_satellite_flood_extent(lat, lon)`

**Current:** Mock with hardcoded affected zone polygons

**Real API Integration (Future):**
- Sentinel Hub (ESA Copernicus) - SAR flood detection
- NASA MODIS flood mapping
- Google Earth Engine
- Planet Labs

**Mock Coverage:**
- Flood zones: 23.45-23.55°N, 87.45-87.55°E
- Earthquake zones: 23.40-23.60°N, 87.40-87.60°E
- Cyclone zones: 23.30-23.70°N, 87.30-87.70°E

## Verification Hierarchy

Reports are verified using the **strongest available signal**:

### 1. Satellite Confirmation (Highest)
- Confidence: 0.85-0.90
- Status: `satellite_confirmed`
- Urgency boost: +0.20
- **Example:** Report location falls within satellite-detected flood extent

### 2. Weather Confirmation
- Confidence: 0.70-0.85
- Status: `weather_confirmed`
- Urgency boost: +0.15
- **Example:** Weather API shows active flood warning matching report

### 3. Corroboration
- Confidence: 0.80
- Status: `corroborated`
- Urgency boost: +0.10
- **Example:** 2+ independent reports of same incident

### 4. Unverified (NOT Rejected)
- Status: `unverified`
- Urgency adjustment: -0.05 (slight downweight)
- **Report remains active** - false negatives cost lives

## Usage

### Basic Verification

```python
from app.pipeline.verify import verify_report
from app.database import SessionLocal

db = SessionLocal()

# Verify a single report
result = verify_report(report, db)

print(f"Status: {result['new_status']}")
print(f"Signals: {result['signals']}")
print(f"Confidence: {result['confidence_scores']}")

db.close()
```

### Batch Verification

```python
from app.pipeline.verify import verify_all_unverified_reports

# Verify all unverified reports (or limit to N)
results = verify_all_unverified_reports(db, limit=100)

print(f"Verified: {results['total_verified']}")
print(f"Status changes: {results['status_changes']}")
```

### API Integration

```python
@app.post("/api/reports")
async def create_report(report_data: ReportCreate, bg: BackgroundTasks, db: Session):
    # Create report
    report = Report(**report_data.dict())
    db.add(report)
    db.commit()
    
    # Verify in background
    bg.add_task(verify_report, report, db)
    
    return {"report_id": report.id, "status": "created"}
```

## Verification Results

The `verify_report()` function returns:

```python
{
    'report_id': str,
    'original_status': str,
    'new_status': str,
    'status_changed': bool,
    'signals': {
        'corroboration': bool,
        'weather_alert': bool,
        'satellite': bool
    },
    'confidence_scores': {
        'corroboration': float,
        'weather': float,
        'satellite': float
    },
    'details': [str],  # Human-readable details
    'urgency_adjustment': float  # Change in urgency score
}
```

## Configuration

### Environment Variables

```bash
# Optional - Leave empty to use mock data
OPENWEATHER_API_KEY=your_api_key_here
```

### Demo Affected Zones

Edit `verify.py` to customize mock polygon zones:

```python
DEMO_FLOOD_AFFECTED_ZONES = [
    Polygon([
        (lon1, lat1),
        (lon2, lat2),
        (lon3, lat3),
        (lon4, lat4)
    ])
]
```

## Swapping in Real APIs

The system is designed for easy API integration:

### Step 1: Implement Real Function

```python
def _get_weather_alert_api(lat, lon, disaster_type):
    # Your real API implementation
    response = requests.get(api_url, params={...})
    return {
        'alert_found': bool,
        'confidence': float,
        'source': 'your_api',
        'details': str
    }
```

### Step 2: Update get_weather_alert()

```python
def get_weather_alert(lat, lon, disaster_type, use_mock=None):
    if use_mock or not settings.your_api_key:
        return _get_weather_alert_mock(...)
    else:
        return _get_weather_alert_api(...)  # Your implementation
```

### Step 3: Add Configuration

```python
# config.py
class Settings(BaseSettings):
    your_api_key: Optional[str] = None
```

## Testing

Run the verification test suite:

```bash
cd backend
python test_verify.py
```

Tests cover:
1. Weather alert detection (mock)
2. Satellite data detection
3. Satellite-confirmed reports
4. Weather-confirmed reports
5. Corroborated reports
6. Unverified reports (no rejection)
7. Batch verification

## Integration Examples

See `backend/examples_verify.py` for:
- Single report verification
- API endpoint integration
- Scheduled batch verification
- Webhook-triggered verification
- Custom data source integration
- Monitoring and metrics

## Performance Considerations

### API Rate Limits

**OpenWeatherMap Free Tier:**
- 1,000 calls/day
- ~40 calls/hour average

**Strategy:**
- Cache weather data for 1 hour per location
- Batch verify reports periodically (not per-report)
- Use mock data during development

### Optimization Tips

1. **Batch Processing:** Verify reports in batches rather than individually
2. **Caching:** Cache weather/satellite data for locations
3. **Background Jobs:** Run verification asynchronously
4. **Rate Limiting:** Implement exponential backoff for API calls
5. **Fallback:** Always have mock fallback for reliability

## Monitoring

Track verification metrics:

```python
# Reports by verification status
SELECT verification_status, COUNT(*) 
FROM reports 
GROUP BY verification_status;

# Average urgency by status
SELECT verification_status, AVG(urgency_score)
FROM reports
GROUP BY verification_status;

# Verification source distribution
# (Track in application logs)
```

## Future Enhancements

1. **Real Satellite Integration**
   - Sentinel Hub API
   - NASA MODIS flood products
   - Google Earth Engine

2. **Additional Data Sources**
   - Seismic monitoring (USGS earthquake API)
   - River gauge data (for floods)
   - Social media sentiment analysis
   - News article verification

3. **Machine Learning**
   - Historical pattern matching
   - Anomaly detection
   - Confidence score optimization

4. **Advanced Features**
   - Multi-source confidence fusion
   - Temporal verification (check historical patterns)
   - Spatial clustering for incident confirmation

## Best Practices

1. ✅ **Never Auto-Reject:** Keep all reports active
2. ✅ **Multiple Signals:** Use all available data sources
3. ✅ **Graceful Degradation:** Fall back to mock if APIs fail
4. ✅ **Background Processing:** Don't block report creation
5. ✅ **Monitor Performance:** Track API usage and success rates
6. ✅ **Cache Strategically:** Reduce API calls with smart caching
7. ✅ **Document Sources:** Always indicate data source in responses

## Security & Privacy

- API keys stored in environment variables
- Never log API responses containing PII
- Rate limit API calls to prevent abuse
- Validate all external data before use
- Use HTTPS for all API communications


---

# RescueAI Urgency Scoring System

## Overview

The urgency scoring system calculates a 0-100 score for each disaster report using a **transparent, weighted formula**. Every factor and its contribution is tracked and visible—crucial for trust with response teams and explainability to judges/stakeholders.

## Core Philosophy

**Transparency Builds Trust**

- All scoring factors are explicitly calculated and stored
- Every report includes a JSON breakdown showing how the score was computed
- No black-box algorithms—responders can see WHY a report has its priority
- Perfect for explaining to non-technical stakeholders and judges

## Scoring Formula

### Base Factors (Additive, 0-100 range)

1. **People Affected** (0-30 points)
   - Logarithmic scale: `10 + 8 × log10(num_people + 1)`
   - Prevents single huge number from dominating
   - Example: 10 people = 18pts, 100 people = 26pts, 1000 people = 34pts (capped at 30)

2. **Vulnerable Populations** (0-45 points)
   - +15 points per flag type present
   - Flags: elderly, child, pregnant, disabled
   - Capped at 45 (max 3 types counted)
   - Example: elderly + child = 30pts

3. **Verification Status** (0-25 points)
   - Unverified: 0
   - Corroborated: +10
   - Weather confirmed: +20
   - Satellite confirmed: +25

4. **Corroboration Count** (0-20 points)
   - +5 per additional independent report
   - Capped at 20 (max 4 counted)
   - Example: 3 corroborations = 15pts

5. **Time Decay** (0-20 points)
   - Reports >2 hours old without update get urgency boost
   - +5 per hour over threshold
   - Capped at 20 (max 4 hours counted)
   - **Rationale:** Delayed help compounds risk

### Disaster Type Multiplier (1.0-1.2×)

Applied to base score to reflect warning time differences:
- **Earthquake**: ×1.2 (minimal warning time)
- **Cyclone**: ×1.1 (limited warning)
- **Flood**: ×1.0 (more warning time)
- **Other**: ×1.0

### Final Score

`final_score = min(base_score × multiplier, 100)`

## Scoring Breakdown Structure

Every report stores a JSON breakdown:

```json
{
  "final_score": 78.5,
  "base_score": 65.4,
  "factors": {
    "people": {
      "score": 18.5,
      "explanation": "50 people (log scale: 18.5/30)"
    },
    "vulnerable": {
      "score": 30.0,
      "explanation": "2 vulnerable group(s): elderly, child (+30)"
    },
    "verification": {
      "score": 20.0,
      "explanation": "Weather data confirms (+20)"
    },
    "corroboration": {
      "score": 10.0,
      "explanation": "2 corroborating report(s) (+10)"
    },
    "time_decay": {
      "score": 5.0,
      "explanation": "Report 3.0h old, no update for 1.0h (+5)"
    }
  },
  "multiplier": {
    "value": 1.2,
    "explanation": "Earthquake: Minimal warning time (×1.2)"
  },
  "summary": "HIGH urgency (79/100) driven primarily by vulnerable populations and verification",
  "timestamp": "2026-07-06T12:34:56Z"
}
```

## Usage

### Basic Scoring

```python
from app.pipeline.scoring import compute_urgency_score

# Calculate score
score, breakdown = compute_urgency_score(report)

print(f"Score: {score}/100")
print(f"Summary: {breakdown['summary']}")
```

### Update Report with Score

```python
from app.pipeline.scoring import update_report_urgency

# Calculate and store
breakdown = update_report_urgency(report, db)

# Score and breakdown now stored on report
print(report.urgency_score)        # 78.5
print(report.urgency_breakdown)    # Full JSON breakdown
```

### Get Explanation

```python
from app.pipeline.scoring import get_urgency_explanation

# Get stored or fresh breakdown
explanation = get_urgency_explanation(report)

# Display to user
for factor_name, factor_data in explanation['factors'].items():
    if factor_data['score'] > 0:
        print(f"{factor_name}: +{factor_data['score']} - {factor_data['explanation']}")
```

### Batch Re-scoring

```python
from app.pipeline.scoring import rescore_all_active_reports

# Re-score all active reports (applies time decay)
results = rescore_all_active_reports(db)

print(f"Rescored {results['total_rescored']} reports")
print(f"Scores increased: {results['scores_increased']}")
```

## Automatic Re-scoring

The system automatically re-scores reports via background scheduler:

### Scheduler Configuration

- **Runs every**: 5 minutes
- **Target**: All active (new/in_progress) reports
- **Purpose**: Apply time decay to aging reports
- **Library**: APScheduler (BackgroundScheduler)

### Scheduler Integration

```python
# In app/main.py
from app.scheduler import start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)
```

### Manual Trigger

```python
from app.scheduler import run_rescore_now

# Manually trigger rescoring
results = run_rescore_now()
```

## Dashboard Display

### Urgency Levels

```python
if score >= 80:
    level = "🔴 CRITICAL"
    color = "red"
elif score >= 60:
    level = "🟠 HIGH"
    color = "orange"
elif score >= 40:
    level = "🟡 MEDIUM"
    color = "yellow"
else:
    level = "🔵 LOW"
    color = "blue"
```

### Factor Visualization

Display each factor's contribution:
- Show score/max (e.g., "18.5/30")
- Display explanation text
- Visual progress bars
- Highlight factors contributing >20%

### Summary Card

```
┌─────────────────────────────────┐
│ Urgency Score: 78/100           │
│ Level: 🟠 HIGH                  │
├─────────────────────────────────┤
│ HIGH urgency (78/100) driven   │
│ primarily by vulnerable         │
│ populations and verification    │
├─────────────────────────────────┤
│ Contributing Factors:           │
│ • Vulnerable: +30               │
│ • Verification: +20             │
│ • People: +18                   │
│ • Time Decay: +5                │
│ • Corroboration: +10            │
│                                 │
│ Base: 83 × Earthquake (1.2)    │
│ = 78 (capped at 100)            │
└─────────────────────────────────┘
```

## Testing

Run the scoring test suite:

```bash
cd backend
python test_scoring.py
```

Tests cover:
1. People affected (log scale validation)
2. Vulnerable population scoring
3. Verification status scoring
4. Corroboration counting
5. Disaster type multipliers
6. Time decay calculation
7. Complete high-urgency scenario
8. Transparency verification
9. Database integration
10. Batch rescoring
11. Configuration access

## Configuration

All scoring parameters are in `scoring.py`:

```python
SCORING_CONFIG = {
    'people_base': 10,
    'people_log_multiplier': 8,
    'people_max_score': 30,
    
    'vulnerable_per_flag': 15,
    'vulnerable_max_score': 45,
    
    'verification_scores': {...},
    
    'corroboration_per_report': 5,
    'corroboration_max_score': 20,
    
    'disaster_multipliers': {...},
    
    'time_decay_per_hour': 5,
    'time_decay_threshold_hours': 2,
    'time_decay_max_score': 20
}
```

**All parameters are tunable** based on field experience!

## API Endpoints

### Get Urgency Breakdown

```http
GET /api/reports/{report_id}/urgency

Response:
{
  "report_id": "...",
  "urgency_score": 78.5,
  "summary": "HIGH urgency...",
  "breakdown": {...},
  "visual_data": {
    "level": "HIGH",
    "color": "#EA580C",
    "percentage": 78.5
  }
}
```

### Priority Queue

```http
GET /api/reports/priority-queue?limit=20&min_score=40

Response:
{
  "priority_queue": [
    {
      "id": "...",
      "urgency_score": 87.5,
      "summary": "CRITICAL urgency...",
      ...
    }
  ]
}
```

### Scoring Configuration

```http
GET /api/scoring/config

Response:
{
  "scoring_config": {...},
  "description": {...},
  "philosophy": "Transparent, explainable..."
}
```

## Transparency Benefits

### For Response Teams

✅ **Understand priorities** - See why one report ranks higher  
✅ **Trust the system** - No black-box algorithms  
✅ **Make informed decisions** - Full context available  
✅ **Explain to superiors** - Clear rationale for actions

### For Judges/Stakeholders

✅ **Explainable AI** - Every calculation visible  
✅ **Fair scoring** - Log-scale prevents dominance  
✅ **Real-world logic** - Time decay reflects urgency  
✅ **Audit trail** - JSON breakdown stored with report

### For Development

✅ **Debuggable** - Can trace why score changed  
✅ **Tunable** - All parameters configurable  
✅ **Testable** - Breakdown enables unit tests  
✅ **Extensible** - Easy to add new factors

## Best Practices

1. **Always store breakdown** - Use `update_report_urgency()` not just `compute_urgency_score()`
2. **Display to users** - Show factor contributions in UI
3. **Re-score on changes** - After verification, corroboration, or updates
4. **Run periodic rescoring** - Keep time decay current (scheduler does this)
5. **Explain to stakeholders** - Use breakdown for transparency
6. **Monitor score distribution** - Track if scores cluster or spread well
7. **Tune based on feedback** - Adjust SCORING_CONFIG with field experience

## Future Enhancements

- **Machine learning weights** - Learn optimal weights from historical outcomes
- **Geographic factors** - Adjust for remote areas with limited resources
- **Resource availability** - Lower score if nearby teams available
- **Historical patterns** - Learn from past incidents in same area
- **Severity prediction** - Use early indicators to adjust scores
