"""
Usage examples for the deduplication pipeline.
These examples show how to integrate find_duplicates() into your workflow.
"""

from datetime import datetime
from app.database import SessionLocal
from app.models import Report, SourceEnum, DisasterTypeEnum
from app.pipeline.dedup import find_duplicates, get_duplicate_info
import uuid


def example_1_basic_usage():
    """
    Example 1: Basic usage when receiving a new report.
    """
    print("\n=== Example 1: Basic Usage ===\n")
    
    db = SessionLocal()
    
    # Simulate receiving a new report from SMS
    new_report = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.sms,
        raw_text="Flood in main street, 20 people need rescue",
        language="en",
        translated_text="Flood in main street, 20 people need rescue",
        disaster_type=DisasterTypeEnum.flood,
        latitude=23.5,
        longitude=87.5,
        num_people=20,
        reporter_phone="+919876543210"
    )
    
    # Add to database
    db.add(new_report)
    db.commit()
    
    # Check for duplicates
    original = find_duplicates(new_report, db)
    
    if original:
        print(f"✓ This report is a duplicate of existing report {original.id}")
        print(f"  Corroboration count: {original.corroboration_count}")
        print(f"  Total people affected: {original.num_people}")
    else:
        print(f"✓ This is a new incident (report {new_report.id})")
        print(f"  No duplicates found")
    
    db.close()


def example_2_api_endpoint():
    """
    Example 2: Integration with FastAPI endpoint.
    """
    print("\n=== Example 2: API Endpoint Integration ===\n")
    
    print("""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Report
from app.pipeline.dedup import find_duplicates

router = APIRouter()

@router.post("/api/reports")
async def create_report(report_data: ReportCreate, db: Session = Depends(get_db)):
    # Create the report
    new_report = Report(**report_data.dict())
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    # Check for duplicates
    original = find_duplicates(new_report, db)
    
    if original:
        return {
            "report_id": new_report.id,
            "status": "duplicate",
            "original_report_id": original.id,
            "corroboration_count": original.corroboration_count,
            "message": "Report marked as duplicate and used to corroborate existing incident"
        }
    else:
        return {
            "report_id": new_report.id,
            "status": "new",
            "message": "New incident report created"
        }
    """)


def example_3_custom_thresholds():
    """
    Example 3: Using custom thresholds for specific scenarios.
    """
    print("\n=== Example 3: Custom Thresholds ===\n")
    
    db = SessionLocal()
    
    new_report = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text="Earthquake damage in commercial district",
        language="en",
        translated_text="Earthquake damage in commercial district",
        disaster_type=DisasterTypeEnum.earthquake,
        latitude=23.5,
        longitude=87.5,
        num_people=30
    )
    
    db.add(new_report)
    db.commit()
    
    # Stricter matching for urban areas
    original = find_duplicates(
        new_report,
        db,
        geo_distance_threshold=100.0,  # Only 100m radius
        text_similarity_threshold=0.75,  # Higher text similarity
        time_window_hours=3  # Shorter time window
    )
    
    print("Custom thresholds applied:")
    print("  - Geo distance: 100m (instead of 300m)")
    print("  - Text similarity: 0.75 (instead of 0.6)")
    print("  - Time window: 3 hours (instead of 6)")
    
    if original:
        print(f"\n✓ Duplicate found with strict matching: {original.id}")
    else:
        print(f"\n✓ No duplicates with strict thresholds")
    
    db.close()


def example_4_get_duplicate_info():
    """
    Example 4: Getting duplicate information for a report.
    """
    print("\n=== Example 4: Get Duplicate Information ===\n")
    
    db = SessionLocal()
    
    # Get any report from database
    report = db.query(Report).first()
    
    if report:
        info = get_duplicate_info(report, db)
        
        print(f"Report ID: {report.id}")
        print(f"Status: {report.status.value}")
        
        if info['is_duplicate']:
            print(f"\n✓ This is a DUPLICATE report")
            print(f"  Original report: {info['original_report_id']}")
            print(f"  Original created: {info['original_created_at']}")
        elif info['is_original']:
            print(f"\n✓ This is an ORIGINAL report with duplicates")
            print(f"  Corroboration count: {info['corroboration_count']}")
            print(f"  Number of duplicates: {info['duplicate_count']}")
        else:
            print(f"\n✓ This is a standalone report (no duplicates)")
    
    db.close()


def example_5_batch_processing():
    """
    Example 5: Batch processing multiple reports.
    """
    print("\n=== Example 5: Batch Processing ===\n")
    
    print("""
def process_sms_batch(messages: list):
    '''Process a batch of incoming SMS reports.'''
    db = SessionLocal()
    
    results = {
        'new': 0,
        'duplicates': 0,
        'errors': 0
    }
    
    for message in messages:
        try:
            # Parse message
            report = parse_sms_message(message)
            
            # Save to database
            db.add(report)
            db.commit()
            db.refresh(report)
            
            # Check for duplicates
            original = find_duplicates(report, db)
            
            if original:
                results['duplicates'] += 1
                print(f"  SMS from {report.reporter_phone}: Duplicate (corroborates {original.id})")
            else:
                results['new'] += 1
                print(f"  SMS from {report.reporter_phone}: New incident")
                
        except Exception as e:
            results['errors'] += 1
            print(f"  Error processing message: {e}")
    
    db.close()
    return results

# Usage
messages = get_incoming_sms()
results = process_sms_batch(messages)
print(f"Processed {len(messages)} messages: {results['new']} new, {results['duplicates']} duplicates")
    """)


def example_6_dashboard_query():
    """
    Example 6: Query for dashboard display.
    """
    print("\n=== Example 6: Dashboard Queries ===\n")
    
    print("""
# Get all original reports with their corroboration counts
def get_corroborated_reports(db: Session):
    '''Get reports sorted by corroboration count.'''
    return db.query(Report).filter(
        Report.is_duplicate_of.is_(None),  # Only originals
        Report.corroboration_count > 0     # Has corroboration
    ).order_by(
        Report.corroboration_count.desc()
    ).all()

# Get the most corroborated incidents
def get_high_confidence_reports(db: Session, min_corroboration: int = 3):
    '''Get highly corroborated (high confidence) reports.'''
    return db.query(Report).filter(
        Report.is_duplicate_of.is_(None),
        Report.corroboration_count >= min_corroboration
    ).order_by(
        Report.urgency_score.desc()
    ).all()

# Dashboard example
db = SessionLocal()

print("=== High Confidence Incidents ===")
for report in get_high_confidence_reports(db, min_corroboration=2):
    print(f"Report {report.id}")
    print(f"  Type: {report.disaster_type.value}")
    print(f"  Corroborations: {report.corroboration_count}")
    print(f"  People affected: {report.num_people}")
    print(f"  Urgency: {report.urgency_score:.2f}")
    print()

db.close()
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Deduplication Pipeline - Usage Examples")
    print("=" * 70)
    
    example_1_basic_usage()
    example_2_api_endpoint()
    example_3_custom_thresholds()
    example_4_get_duplicate_info()
    example_5_batch_processing()
    example_6_dashboard_query()
    
    print("\n" + "=" * 70)
    print("For more information, see: backend/app/pipeline/README.md")
    print("=" * 70)
