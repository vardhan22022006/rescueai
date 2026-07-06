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
