"""
Usage examples for the verification pipeline.
Shows how to integrate verify_report() into your workflow.
"""

from app.database import SessionLocal
from app.models import Report
from app.pipeline.verify import verify_report, verify_all_unverified_reports


def example_1_verify_single_report():
    """
    Example 1: Verify a single report when it's created or updated.
    """
    print("\n=== Example 1: Verify Single Report ===\n")
    
    print("""
from app.pipeline.verify import verify_report

# After creating or receiving a report
db = SessionLocal()
report = db.query(Report).filter(Report.id == report_id).first()

# Run verification
result = verify_report(report, db)

print(f"Verification status: {result['new_status']}")
print(f"Signals detected: {result['signals']}")
print(f"Confidence scores: {result['confidence_scores']}")

for detail in result['details']:
    print(f"  • {detail}")

db.close()
    """)


def example_2_api_integration():
    """
    Example 2: Integrate verification into API endpoint.
    """
    print("\n=== Example 2: API Endpoint Integration ===\n")
    
    print("""
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report
from app.pipeline.verify import verify_report

router = APIRouter()

@router.post("/api/reports")
async def create_report(
    report_data: ReportCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    # Create the report
    new_report = Report(**report_data.dict())
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    # Run verification in background (non-blocking)
    background_tasks.add_task(verify_report, new_report, db)
    
    return {
        "report_id": new_report.id,
        "status": "created",
        "message": "Report created and queued for verification"
    }

@router.post("/api/reports/{report_id}/verify")
async def verify_existing_report(
    report_id: str,
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Run verification immediately
    result = verify_report(report, db)
    
    return {
        "report_id": report.id,
        "verification_status": result['new_status'],
        "status_changed": result['status_changed'],
        "signals": result['signals'],
        "details": result['details']
    }
    """)


def example_3_scheduled_verification():
    """
    Example 3: Scheduled batch verification (cron job or periodic task).
    """
    print("\n=== Example 3: Scheduled Batch Verification ===\n")
    
    print("""
from app.pipeline.verify import verify_all_unverified_reports
from app.database import SessionLocal

def scheduled_verification_job():
    '''
    Run this periodically (e.g., every hour) to verify unverified reports.
    Can be triggered by:
    - Cron job
    - APScheduler
    - Celery beat
    - Cloud scheduler (AWS EventBridge, GCP Cloud Scheduler)
    '''
    db = SessionLocal()
    
    try:
        print("Starting scheduled verification...")
        
        # Verify up to 100 reports per run
        results = verify_all_unverified_reports(db, limit=100)
        
        print(f"Verified {results['total_verified']} reports")
        print(f"Status changes: {results['status_changes']}")
        
        # Log results for monitoring
        log_to_monitoring_system(results)
        
    finally:
        db.close()

# Using APScheduler
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()
scheduler.add_job(
    scheduled_verification_job,
    'interval',
    hours=1,  # Run every hour
    id='verification_job'
)
scheduler.start()
    """)


def example_4_webhook_verification():
    """
    Example 4: Verify reports when external data is updated.
    """
    print("\n=== Example 4: Webhook-Triggered Verification ===\n")
    
    print("""
@router.post("/webhooks/weather-alert")
async def weather_alert_webhook(alert_data: dict, db: Session = Depends(get_db)):
    '''
    Webhook endpoint that receives weather alerts from external services.
    When new alert received, re-verify relevant reports.
    '''
    # Extract alert location and type
    lat = alert_data.get('latitude')
    lon = alert_data.get('longitude')
    alert_type = alert_data.get('type')  # flood, cyclone, etc.
    
    # Find unverified reports near this location
    from app.models import StatusEnum, VerificationStatusEnum
    
    nearby_reports = db.query(Report).filter(
        Report.verification_status == VerificationStatusEnum.unverified,
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress]),
        # Simple distance check (in production, use spatial query)
        Report.latitude.between(lat - 0.1, lat + 0.1),
        Report.longitude.between(lon - 0.1, lon + 0.1)
    ).all()
    
    verified_count = 0
    for report in nearby_reports:
        result = verify_report(report, db)
        if result['status_changed']:
            verified_count += 1
    
    return {
        "message": f"Re-verified {len(nearby_reports)} reports",
        "newly_verified": verified_count
    }
    """)


def example_5_custom_data_sources():
    """
    Example 5: Swapping in real API implementations.
    """
    print("\n=== Example 5: Custom Data Source Integration ===\n")
    
    print("""
# To integrate real Sentinel Hub satellite API:

import requests
from config import settings

def get_satellite_flood_extent_sentinel(lat: float, lon: float) -> Dict[str, any]:
    '''
    Real Sentinel Hub integration for flood detection.
    Replaces the mock function in verify.py
    '''
    # Sentinel Hub API configuration
    api_url = "https://services.sentinel-hub.com/api/v1/process"
    
    headers = {
        "Authorization": f"Bearer {settings.sentinel_hub_token}",
        "Content-Type": "application/json"
    }
    
    # Request flood detection layer
    payload = {
        "input": {
            "bounds": {
                "bbox": [lon - 0.01, lat - 0.01, lon + 0.01, lat + 0.01]
            },
            "data": [{
                "type": "sentinel-1-grd",
                "dataFilter": {
                    "timeRange": {
                        "from": (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z",
                        "to": datetime.utcnow().isoformat() + "Z"
                    }
                }
            }]
        },
        "output": {
            "width": 512,
            "height": 512,
            "responses": [{
                "identifier": "default",
                "format": {"type": "image/tiff"}
            }]
        },
        "evalscript": FLOOD_DETECTION_SCRIPT  # Custom evalscript
    }
    
    response = requests.post(api_url, json=payload, headers=headers)
    
    if response.status_code == 200:
        # Analyze response to detect flood
        flood_detected = analyze_flood_data(response.content)
        
        return {
            'in_affected_zone': flood_detected,
            'confidence': 0.9 if flood_detected else 0.1,
            'source': 'sentinel_hub',
            'details': 'Sentinel-1 SAR flood detection'
        }
    else:
        # Fall back to mock if API fails
        return _get_satellite_flood_extent_mock(lat, lon)

# To use real API, modify verify.py:
# Replace call to _get_satellite_flood_extent_mock() with your real function
    """)


def example_6_monitoring_verification():
    """
    Example 6: Monitor verification pipeline performance.
    """
    print("\n=== Example 6: Verification Monitoring ===\n")
    
    print("""
from collections import Counter
from datetime import datetime, timedelta

def get_verification_metrics(db: Session, hours: int = 24):
    '''
    Get verification pipeline metrics for monitoring dashboard.
    '''
    since = datetime.utcnow() - timedelta(hours=hours)
    
    reports = db.query(Report).filter(
        Report.created_at >= since
    ).all()
    
    metrics = {
        'total_reports': len(reports),
        'by_status': Counter(r.verification_status.value for r in reports),
        'by_source': {},
        'avg_urgency': {
            'satellite_confirmed': [],
            'weather_confirmed': [],
            'corroborated': [],
            'unverified': []
        }
    }
    
    # Calculate average urgency by verification status
    for report in reports:
        status = report.verification_status.value
        metrics['avg_urgency'][status].append(report.urgency_score)
    
    # Calculate averages
    for status in metrics['avg_urgency']:
        scores = metrics['avg_urgency'][status]
        metrics['avg_urgency'][status] = sum(scores) / len(scores) if scores else 0
    
    return metrics

# Usage in dashboard endpoint
@router.get("/api/metrics/verification")
async def verification_metrics(db: Session = Depends(get_db)):
    metrics = get_verification_metrics(db, hours=24)
    
    return {
        "period": "last_24_hours",
        "total_reports": metrics['total_reports'],
        "verification_breakdown": dict(metrics['by_status']),
        "average_urgency_by_status": metrics['avg_urgency']
    }
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Verification Pipeline - Usage Examples")
    print("=" * 70)
    
    example_1_verify_single_report()
    example_2_api_integration()
    example_3_scheduled_verification()
    example_4_webhook_verification()
    example_5_custom_data_sources()
    example_6_monitoring_verification()
    
    print("\n" + "=" * 70)
    print("For more information, see: backend/app/pipeline/README.md")
    print("=" * 70)
