"""
Report verification pipeline using external data sources.

Integrates with:
1. OpenWeatherMap API (optional, falls back to mock)
2. Satellite flood extent data (mocked with realistic polygon)

Philosophy: Never auto-reject reports. False negatives cost lives.
Only downweight unverified single reports slightly, never discard them.
"""

from typing import Optional, Dict, Tuple
from datetime import datetime
import requests
from shapely.geometry import Point, Polygon
from sqlalchemy.orm import Session

from app.models import Report, DisasterTypeEnum, VerificationStatusEnum
from config import settings


# Demo affected zone polygon (covers area around base coordinates 23.5°N, 87.5°E)
# In production, this would be fetched from satellite/flood mapping APIs
DEMO_FLOOD_AFFECTED_ZONES = [
    Polygon([
        (87.45, 23.45),
        (87.55, 23.45),
        (87.55, 23.55),
        (87.45, 23.55)
    ]),
    # Additional affected zone
    Polygon([
        (87.48, 23.48),
        (87.52, 23.48),
        (87.52, 23.52),
        (87.48, 23.52)
    ])
]

DEMO_EARTHQUAKE_AFFECTED_ZONES = [
    Polygon([
        (87.40, 23.40),
        (87.60, 23.40),
        (87.60, 23.60),
        (87.40, 23.60)
    ])
]

DEMO_CYCLONE_AFFECTED_ZONES = [
    Polygon([
        (87.30, 23.30),
        (87.70, 23.30),
        (87.70, 23.70),
        (87.30, 23.70)
    ])
]


def get_weather_alert(
    lat: float,
    lon: float,
    disaster_type: DisasterTypeEnum,
    use_mock: bool = None
) -> Dict[str, any]:
    """
    Check weather alerts for a location using OpenWeatherMap API.
    
    Falls back to mock data if API key is not configured.
    This is a pluggable function - real API integration or mock.
    
    Args:
        lat: Latitude
        lon: Longitude
        disaster_type: Type of disaster to check for
        use_mock: Force mock mode (None = auto-detect based on API key)
    
    Returns:
        Dict with:
        - alert_found: bool - Whether relevant alert exists
        - confidence: float - Confidence score 0-1
        - source: str - 'openweather_api' or 'mock'
        - details: str - Description of alert
        - raw_data: dict - Raw API response (if applicable)
    """
    # Auto-detect: use mock if no API key configured
    if use_mock is None:
        use_mock = not bool(settings.openweather_api_key)
    
    if use_mock or not settings.openweather_api_key:
        return _get_weather_alert_mock(lat, lon, disaster_type)
    else:
        return _get_weather_alert_api(lat, lon, disaster_type)


def _get_weather_alert_api(
    lat: float,
    lon: float,
    disaster_type: DisasterTypeEnum
) -> Dict[str, any]:
    """
    Real OpenWeatherMap API integration.
    
    Uses the free tier:
    - 1,000 calls/day
    - Current weather + alerts
    - No credit card required
    """
    try:
        # OpenWeatherMap One Call API 3.0 (includes alerts)
        # Free tier: https://openweathermap.org/api/one-call-3
        url = "https://api.openweathermap.org/data/3.0/onecall"
        
        params = {
            'lat': lat,
            'lon': lon,
            'appid': settings.openweather_api_key,
            'exclude': 'minutely,hourly,daily'  # Only need current + alerts
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for alerts
        alerts = data.get('alerts', [])
        current = data.get('current', {})
        
        # Check if alerts match disaster type
        alert_found = False
        alert_description = ""
        
        disaster_keywords = {
            DisasterTypeEnum.flood: ['flood', 'rain', 'heavy rain', 'precipitation', 'water'],
            DisasterTypeEnum.cyclone: ['cyclone', 'hurricane', 'storm', 'wind', 'tropical'],
            DisasterTypeEnum.earthquake: ['earthquake', 'seismic'],
            DisasterTypeEnum.other: []
        }
        
        keywords = disaster_keywords.get(disaster_type, [])
        
        for alert in alerts:
            event = alert.get('event', '').lower()
            description = alert.get('description', '').lower()
            
            # Check if alert matches disaster type
            if any(keyword in event or keyword in description for keyword in keywords):
                alert_found = True
                alert_description = alert.get('event', 'Weather alert')
                break
        
        # Also check current conditions for supporting evidence
        weather_conditions = current.get('weather', [])
        rain = current.get('rain', {})
        wind_speed = current.get('wind_speed', 0)
        
        # Additional confidence based on conditions
        confidence = 0.5 if alert_found else 0.0
        
        if disaster_type == DisasterTypeEnum.flood:
            # Check rainfall
            rain_1h = rain.get('1h', 0)
            if rain_1h > 10:  # Heavy rain (>10mm/hour)
                confidence += 0.3
                alert_description += f" (Heavy rainfall: {rain_1h}mm/h)"
        
        elif disaster_type == DisasterTypeEnum.cyclone:
            # Check wind speed
            if wind_speed > 20:  # Strong winds (>20 m/s = 72 km/h)
                confidence += 0.3
                alert_description += f" (High winds: {wind_speed}m/s)"
        
        confidence = min(confidence, 1.0)
        
        return {
            'alert_found': alert_found or confidence > 0.5,
            'confidence': confidence,
            'source': 'openweather_api',
            'details': alert_description if alert_description else "No matching alerts",
            'raw_data': {
                'alerts': alerts,
                'current_conditions': {
                    'weather': weather_conditions,
                    'rain': rain,
                    'wind_speed': wind_speed
                }
            }
        }
        
    except requests.exceptions.RequestException as e:
        print(f"OpenWeatherMap API error: {e}")
        # Fall back to mock on API failure
        return _get_weather_alert_mock(lat, lon, disaster_type)
    except Exception as e:
        print(f"Unexpected error in weather API: {e}")
        return _get_weather_alert_mock(lat, lon, disaster_type)


def _get_weather_alert_mock(
    lat: float,
    lon: float,
    disaster_type: DisasterTypeEnum
) -> Dict[str, any]:
    """
    Mock weather alert data for development/demo.
    Returns realistic responses based on location and disaster type.
    """
    # Mock: Consider alerts active in certain areas
    # This simulates realistic weather patterns for demo
    
    alert_found = False
    confidence = 0.0
    details = "No active weather alerts (mock data)"
    
    # Define "active alert zones" for demo
    if disaster_type == DisasterTypeEnum.flood:
        # Mock flood alerts in areas with lat 23.4-23.6, lon 87.4-87.6
        if 23.4 <= lat <= 23.6 and 87.4 <= lon <= 87.6:
            alert_found = True
            confidence = 0.8
            details = "Heavy rainfall warning - 50mm/hour (mock data)"
    
    elif disaster_type == DisasterTypeEnum.cyclone:
        # Mock cyclone alerts in coastal-like coordinates
        if 23.3 <= lat <= 23.7 and 87.3 <= lon <= 87.7:
            alert_found = True
            confidence = 0.85
            details = "Tropical cyclone warning - winds 80km/h (mock data)"
    
    elif disaster_type == DisasterTypeEnum.earthquake:
        # Earthquakes don't have weather alerts, but return realistic response
        details = "No weather data available for seismic events (mock data)"
        confidence = 0.0
    
    return {
        'alert_found': alert_found,
        'confidence': confidence,
        'source': 'mock',
        'details': details,
        'raw_data': {
            'note': 'Mock data - configure OPENWEATHER_API_KEY for real data'
        }
    }


def get_satellite_flood_extent(lat: float, lon: float) -> Dict[str, any]:
    """
    Check if location falls within satellite-detected flood extent.
    
    Currently mocked with hardcoded polygon for demo area.
    In production, would integrate with:
    - Sentinel Hub API (ESA Copernicus)
    - NASA MODIS flood mapping
    - Google Earth Engine
    - Planet Labs
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Dict with:
        - in_affected_zone: bool - Whether location is in flood zone
        - confidence: float - Confidence score 0-1
        - source: str - Data source
        - details: str - Description
    """
    return _get_satellite_flood_extent_mock(lat, lon)


def _get_satellite_flood_extent_mock(lat: float, lon: float) -> Dict[str, any]:
    """
    Mock satellite flood extent data.
    Uses hardcoded polygons to simulate affected zones.
    
    Real implementation would query actual satellite APIs.
    """
    point = Point(lon, lat)
    
    # Check all demo flood zones
    in_flood_zone = any(zone.contains(point) for zone in DEMO_FLOOD_AFFECTED_ZONES)
    
    # Check earthquake zones
    in_earthquake_zone = any(zone.contains(point) for zone in DEMO_EARTHQUAKE_AFFECTED_ZONES)
    
    # Check cyclone zones
    in_cyclone_zone = any(zone.contains(point) for zone in DEMO_CYCLONE_AFFECTED_ZONES)
    
    # Determine which zone and details
    if in_flood_zone:
        return {
            'in_affected_zone': True,
            'confidence': 0.9,
            'source': 'mock_satellite',
            'details': 'Location within satellite-detected flood extent (mock polygon)',
            'zone_type': 'flood'
        }
    elif in_earthquake_zone:
        return {
            'in_affected_zone': True,
            'confidence': 0.85,
            'source': 'mock_satellite',
            'details': 'Location within seismic activity zone (mock polygon)',
            'zone_type': 'earthquake'
        }
    elif in_cyclone_zone:
        return {
            'in_affected_zone': True,
            'confidence': 0.88,
            'source': 'mock_satellite',
            'details': 'Location within cyclone impact zone (mock polygon)',
            'zone_type': 'cyclone'
        }
    else:
        return {
            'in_affected_zone': False,
            'confidence': 0.0,
            'source': 'mock_satellite',
            'details': 'Location outside known affected zones (mock data)',
            'zone_type': None
        }


def verify_report(report: Report, db: Session) -> Dict[str, any]:
    """
    Verify a disaster report against external data sources.
    
    Verification hierarchy (strongest signal wins):
    1. Satellite confirmation (highest confidence)
    2. Weather API confirmation
    3. Corroboration from multiple reports
    4. Single unverified report (lowest, but never rejected)
    
    Philosophy: Never auto-reject reports. False negatives cost lives.
    Only downweight unverified single reports slightly in urgency scoring.
    
    Args:
        report: Report to verify
        db: Database session
    
    Returns:
        Dict with verification results and updated status
    """
    verification_result = {
        'report_id': report.id,
        'original_status': report.verification_status.value,
        'new_status': report.verification_status.value,
        'signals': {
            'corroboration': False,
            'weather_alert': False,
            'satellite': False
        },
        'confidence_scores': {},
        'details': [],
        'urgency_adjustment': 0.0
    }
    
    # Signal 1: Corroboration from duplicates
    if report.corroboration_count >= 2:
        verification_result['signals']['corroboration'] = True
        verification_result['confidence_scores']['corroboration'] = 0.8
        verification_result['details'].append(
            f"Corroborated by {report.corroboration_count} independent reports"
        )
    
    # Signal 2: Weather alert check (if location available)
    weather_check = None
    if report.latitude and report.longitude:
        weather_check = get_weather_alert(
            report.latitude,
            report.longitude,
            report.disaster_type
        )
        
        if weather_check['alert_found']:
            verification_result['signals']['weather_alert'] = True
            verification_result['confidence_scores']['weather'] = weather_check['confidence']
            verification_result['details'].append(
                f"Weather alert: {weather_check['details']} (source: {weather_check['source']})"
            )
    
    # Signal 3: Satellite data check (if location available and relevant disaster type)
    satellite_check = None
    if report.latitude and report.longitude:
        if report.disaster_type in [DisasterTypeEnum.flood, DisasterTypeEnum.cyclone, 
                                     DisasterTypeEnum.earthquake]:
            satellite_check = get_satellite_flood_extent(
                report.latitude,
                report.longitude
            )
            
            if satellite_check['in_affected_zone']:
                # Check if zone type matches disaster type
                zone_matches = (
                    (satellite_check['zone_type'] == 'flood' and 
                     report.disaster_type == DisasterTypeEnum.flood) or
                    (satellite_check['zone_type'] == 'earthquake' and 
                     report.disaster_type == DisasterTypeEnum.earthquake) or
                    (satellite_check['zone_type'] == 'cyclone' and 
                     report.disaster_type == DisasterTypeEnum.cyclone)
                )
                
                if zone_matches:
                    verification_result['signals']['satellite'] = True
                    verification_result['confidence_scores']['satellite'] = satellite_check['confidence']
                    verification_result['details'].append(
                        f"Satellite data: {satellite_check['details']}"
                    )
    
    # Determine verification status (strongest signal wins)
    original_status = report.verification_status
    
    if verification_result['signals']['satellite']:
        # Highest confidence: satellite confirmation
        report.verification_status = VerificationStatusEnum.satellite_confirmed
        verification_result['urgency_adjustment'] = +0.2
        
    elif verification_result['signals']['weather_alert']:
        # Weather API confirmation
        report.verification_status = VerificationStatusEnum.weather_confirmed
        verification_result['urgency_adjustment'] = +0.15
        
    elif verification_result['signals']['corroboration']:
        # Multiple reports corroborate
        report.verification_status = VerificationStatusEnum.corroborated
        verification_result['urgency_adjustment'] = +0.1
        
    else:
        # No external verification, but NEVER reject
        # Keep as unverified, slight urgency downweight
        report.verification_status = VerificationStatusEnum.unverified
        verification_result['urgency_adjustment'] = -0.05
        verification_result['details'].append(
            "No external verification yet - report remains active (false negatives cost lives)"
        )
    
    # Apply urgency adjustment
    if verification_result['urgency_adjustment'] != 0:
        old_urgency = report.urgency_score
        report.urgency_score = max(0.0, min(1.0, 
            report.urgency_score + verification_result['urgency_adjustment']
        ))
        verification_result['details'].append(
            f"Urgency adjusted: {old_urgency:.2f} → {report.urgency_score:.2f}"
        )
    
    # Update report
    report.updated_at = datetime.utcnow()
    db.add(report)
    db.commit()
    
    verification_result['new_status'] = report.verification_status.value
    verification_result['status_changed'] = (original_status != report.verification_status)
    
    return verification_result


def verify_all_unverified_reports(db: Session, limit: Optional[int] = None) -> Dict[str, any]:
    """
    Batch verify all unverified reports.
    
    Useful for:
    - Initial verification of seeded data
    - Periodic re-verification as new data becomes available
    - Testing verification pipeline
    
    Args:
        db: Database session
        limit: Maximum number of reports to verify (None = all)
    
    Returns:
        Summary of verification results
    """
    from app.models import StatusEnum
    
    query = db.query(Report).filter(
        Report.verification_status == VerificationStatusEnum.unverified,
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    )
    
    if limit:
        query = query.limit(limit)
    
    reports = query.all()
    
    results = {
        'total_verified': 0,
        'status_changes': {
            'satellite_confirmed': 0,
            'weather_confirmed': 0,
            'corroborated': 0,
            'remained_unverified': 0
        },
        'details': []
    }
    
    for report in reports:
        result = verify_report(report, db)
        results['total_verified'] += 1
        
        if result['status_changed']:
            results['status_changes'][result['new_status']] += 1
        else:
            results['status_changes']['remained_unverified'] += 1
        
        results['details'].append({
            'report_id': report.id,
            'disaster_type': report.disaster_type.value,
            'status': result['new_status'],
            'signals': result['signals']
        })
    
    return results
