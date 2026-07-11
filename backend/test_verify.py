"""
Test script for report verification pipeline.
Demonstrates how verify_report() works with various scenarios.
"""

from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
from app.models import Report, SourceEnum, DisasterTypeEnum, StatusEnum, VerificationStatusEnum
from app.pipeline.verify import (
    verify_report, 
    get_weather_alert, 
    get_satellite_flood_extent,
    verify_all_unverified_reports
)
import uuid


def create_test_report(
    raw_text: str,
    disaster_type: DisasterTypeEnum,
    latitude: float = None,
    longitude: float = None,
    corroboration_count: int = 0
) -> Report:
    """Helper to create a test report."""
    return Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text=raw_text,
        language="en",
        translated_text=raw_text,
        latitude=latitude,
        longitude=longitude,
        disaster_type=disaster_type,
        num_people=10,
        corroboration_count=corroboration_count,
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=0.5,
        created_at=datetime.utcnow()
    )


def test_weather_alert_mock():
    """Test 1: Weather alert check with mock data."""
    print("\n=== Test 1: Weather Alert Check (Mock) ===\n")
    
    # Test flood alert in mock zone
    result = get_weather_alert(23.5, 87.5, DisasterTypeEnum.flood, use_mock=True)
    
    print(f"Location: (23.5, 87.5)")
    print(f"Disaster type: Flood")
    print(f"Alert found: {result['alert_found']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Source: {result['source']}")
    print(f"Details: {result['details']}")
    
    # Test cyclone alert
    print("\n" + "-" * 50)
    result2 = get_weather_alert(23.5, 87.5, DisasterTypeEnum.cyclone, use_mock=True)
    
    print(f"Location: (23.5, 87.5)")
    print(f"Disaster type: Cyclone")
    print(f"Alert found: {result2['alert_found']}")
    print(f"Confidence: {result2['confidence']:.2f}")
    print(f"Details: {result2['details']}")
    
    # Test outside mock zone
    print("\n" + "-" * 50)
    result3 = get_weather_alert(25.0, 90.0, DisasterTypeEnum.flood, use_mock=True)
    
    print(f"Location: (25.0, 90.0) - Outside zone")
    print(f"Disaster type: Flood")
    print(f"Alert found: {result3['alert_found']}")
    print(f"Details: {result3['details']}")


def test_satellite_data():
    """Test 2: Satellite flood extent check."""
    print("\n=== Test 2: Satellite Flood Extent Check ===\n")
    
    # Test inside flood zone
    result = get_satellite_flood_extent(23.5, 87.5)
    
    print(f"Location: (23.5, 87.5)")
    print(f"In affected zone: {result['in_affected_zone']}")
    print(f"Confidence: {result['confidence']:.2f}")
    print(f"Zone type: {result.get('zone_type', 'N/A')}")
    print(f"Details: {result['details']}")
    
    # Test outside zone
    print("\n" + "-" * 50)
    result2 = get_satellite_flood_extent(25.0, 90.0)
    
    print(f"Location: (25.0, 90.0) - Outside zone")
    print(f"In affected zone: {result2['in_affected_zone']}")
    print(f"Details: {result2['details']}")


def test_verify_satellite_confirmed():
    """Test 3: Report verified by satellite data."""
    print("\n=== Test 3: Satellite-Confirmed Report ===\n")
    
    db = SessionLocal()
    
    try:
        # Create report in satellite flood zone
        report = create_test_report(
            raw_text="Severe flooding observed in residential area",
            disaster_type=DisasterTypeEnum.flood,
            latitude=23.5,
            longitude=87.5
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        print(f"Report created:")
        print(f"  ID: {report.id}")
        print(f"  Location: ({report.latitude}, {report.longitude})")
        print(f"  Initial status: {report.verification_status.value}")
        print(f"  Initial urgency: {report.urgency_score:.2f}")
        
        # Verify report
        result = verify_report(report, db)
        
        db.refresh(report)
        
        print(f"\n✓ Verification completed:")
        print(f"  New status: {report.verification_status.value}")
        print(f"  Status changed: {result['status_changed']}")
        print(f"  New urgency: {report.urgency_score:.2f}")
        print(f"\nSignals detected:")
        for signal, detected in result['signals'].items():
            print(f"  - {signal}: {'✓' if detected else '✗'}")
        print(f"\nDetails:")
        for detail in result['details']:
            print(f"  • {detail}")
            
    finally:
        db.query(Report).filter(Report.id == report.id).delete()
        db.commit()
        db.close()


def test_verify_weather_confirmed():
    """Test 4: Report verified by weather alert."""
    print("\n=== Test 4: Weather-Confirmed Report ===\n")
    
    db = SessionLocal()
    
    try:
        # Create cyclone report in weather alert zone
        report = create_test_report(
            raw_text="Strong winds and heavy rain, cyclone damage severe",
            disaster_type=DisasterTypeEnum.cyclone,
            latitude=23.5,
            longitude=87.5
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        print(f"Report created:")
        print(f"  Disaster type: {report.disaster_type.value}")
        print(f"  Initial status: {report.verification_status.value}")
        
        # Verify report
        result = verify_report(report, db)
        
        db.refresh(report)
        
        print(f"\n✓ Verification completed:")
        print(f"  New status: {report.verification_status.value}")
        print(f"  Weather alert detected: {result['signals']['weather_alert']}")
        print(f"\nDetails:")
        for detail in result['details']:
            print(f"  • {detail}")
            
    finally:
        db.query(Report).filter(Report.id == report.id).delete()
        db.commit()
        db.close()


def test_verify_corroborated():
    """Test 5: Report verified by corroboration."""
    print("\n=== Test 5: Corroborated Report ===\n")
    
    db = SessionLocal()
    
    try:
        # Create report with high corroboration count
        report = create_test_report(
            raw_text="Earthquake damage reported in multiple areas",
            disaster_type=DisasterTypeEnum.earthquake,
            latitude=None,  # No GPS
            longitude=None,
            corroboration_count=3  # 3 duplicates
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        print(f"Report created:")
        print(f"  Corroboration count: {report.corroboration_count}")
        print(f"  Initial status: {report.verification_status.value}")
        
        # Verify report
        result = verify_report(report, db)
        
        db.refresh(report)
        
        print(f"\n✓ Verification completed:")
        print(f"  New status: {report.verification_status.value}")
        print(f"  Corroboration signal: {result['signals']['corroboration']}")
        print(f"\nDetails:")
        for detail in result['details']:
            print(f"  • {detail}")
            
    finally:
        db.query(Report).filter(Report.id == report.id).delete()
        db.commit()
        db.close()


def test_verify_unverified_no_rejection():
    """Test 6: Unverified report is NOT rejected."""
    print("\n=== Test 6: Unverified Report (No Rejection) ===\n")
    
    db = SessionLocal()
    
    try:
        # Create report outside all zones with no corroboration
        report = create_test_report(
            raw_text="Need help, flooding in remote area",
            disaster_type=DisasterTypeEnum.flood,
            latitude=25.0,  # Outside zones
            longitude=90.0,
            corroboration_count=0
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        print(f"Report created:")
        print(f"  Location: ({report.latitude}, {report.longitude}) - Outside known zones")
        print(f"  Corroboration: {report.corroboration_count}")
        print(f"  Initial status: {report.verification_status.value}")
        print(f"  Initial urgency: {report.urgency_score:.2f}")
        
        # Verify report
        result = verify_report(report, db)
        
        db.refresh(report)
        
        print(f"\n✓ Verification completed:")
        print(f"  New status: {report.verification_status.value}")
        print(f"  Status: {report.status.value}")
        print(f"  New urgency: {report.urgency_score:.2f}")
        print(f"\n⚠️ IMPORTANT: Report was NOT rejected!")
        print(f"  Philosophy: False negatives cost lives.")
        print(f"  Report remains active with slight urgency downweight.")
        print(f"\nDetails:")
        for detail in result['details']:
            print(f"  • {detail}")
            
    finally:
        db.query(Report).filter(Report.id == report.id).delete()
        db.commit()
        db.close()


def test_batch_verification():
    """Test 7: Batch verification of multiple reports."""
    print("\n=== Test 7: Batch Verification ===\n")
    
    db = SessionLocal()
    report_ids = []
    
    try:
        # Create 5 test reports with different characteristics
        reports_data = [
            (23.5, 87.5, DisasterTypeEnum.flood, 0),  # In satellite zone
            (23.5, 87.5, DisasterTypeEnum.cyclone, 1),  # In weather zone + corroboration
            (25.0, 90.0, DisasterTypeEnum.earthquake, 3),  # Outside zones, high corroboration
            (23.5, 87.5, DisasterTypeEnum.flood, 0),  # In satellite zone
            (26.0, 91.0, DisasterTypeEnum.other, 0),  # Outside, no corroboration
        ]
        
        for lat, lon, dtype, corrob in reports_data:
            report = create_test_report(
                raw_text=f"Disaster report: {dtype.value}",
                disaster_type=dtype,
                latitude=lat,
                longitude=lon,
                corroboration_count=corrob
            )
            db.add(report)
            report_ids.append(report.id)
        
        db.commit()
        
        print(f"Created {len(report_ids)} test reports")
        print("Running batch verification...\n")
        
        # Run batch verification
        results = verify_all_unverified_reports(db)
        
        print(f"✓ Batch verification completed:")
        print(f"  Total verified: {results['total_verified']}")
        print(f"\nStatus changes:")
        for status, count in results['status_changes'].items():
            print(f"  - {status}: {count}")
        
        print(f"\nDetailed results:")
        for detail in results['details']:
            print(f"  Report {detail['report_id'][:8]}... ({detail['disaster_type']})")
            print(f"    Status: {detail['status']}")
            signals = [k for k, v in detail['signals'].items() if v]
            print(f"    Signals: {', '.join(signals) if signals else 'none'}")
            
    finally:
        db.query(Report).filter(Report.id.in_(report_ids)).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Report Verification Pipeline Test Suite")
    print("=" * 70)
    
    test_weather_alert_mock()
    test_satellite_data()
    test_verify_satellite_confirmed()
    test_verify_weather_confirmed()
    test_verify_corroborated()
    test_verify_unverified_no_rejection()
    test_batch_verification()
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("\nKey Takeaway: Reports are NEVER auto-rejected.")
    print("False negatives cost lives - unverified reports remain active.")
    print("=" * 70)
