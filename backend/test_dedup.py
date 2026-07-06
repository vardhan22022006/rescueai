"""
Test script for deduplication pipeline.
Demonstrates how find_duplicates() works with various scenarios.
"""

from datetime import datetime, timedelta
from app.database import SessionLocal, engine, Base
from app.models import Report, SourceEnum, DisasterTypeEnum, StatusEnum
from app.pipeline.dedup import find_duplicates, get_duplicate_info
import uuid


def create_test_report(
    raw_text: str,
    disaster_type: DisasterTypeEnum,
    latitude: float = None,
    longitude: float = None,
    num_people: int = None,
    vulnerable_flags: list = None,
    created_at: datetime = None
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
        num_people=num_people,
        vulnerable_flags=vulnerable_flags or [],
        created_at=created_at or datetime.utcnow()
    )


def test_geo_proximity():
    """Test geo-proximity duplicate detection."""
    print("\n=== Test 1: Geo-Proximity Duplicate Detection ===\n")
    
    db = SessionLocal()
    try:
        # Create original report
        original = create_test_report(
            raw_text="Severe flooding in residential area, need immediate evacuation",
            disaster_type=DisasterTypeEnum.flood,
            latitude=23.5,
            longitude=87.5,
            num_people=10,
            vulnerable_flags=["elderly"],
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.add(original)
        db.commit()
        db.refresh(original)
        
        print(f"Original report created:")
        print(f"  ID: {original.id}")
        print(f"  Location: ({original.latitude}, {original.longitude})")
        print(f"  People: {original.num_people}")
        print(f"  Corroboration count: {original.corroboration_count}")
        
        # Create duplicate report within 300m (0.002 degrees ~ 220m)
        duplicate = create_test_report(
            raw_text="Water rising rapidly in the neighborhood, families trapped",
            disaster_type=DisasterTypeEnum.flood,
            latitude=23.502,  # ~220m away
            longitude=87.502,
            num_people=5,
            vulnerable_flags=["child"],
            created_at=datetime.utcnow()
        )
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        
        print(f"\nDuplicate report created:")
        print(f"  ID: {duplicate.id}")
        print(f"  Location: ({duplicate.latitude}, {duplicate.longitude})")
        print(f"  People: {duplicate.num_people}")
        
        # Check for duplicates
        result = find_duplicates(duplicate, db)
        
        if result:
            db.refresh(original)
            db.refresh(duplicate)
            
            print(f"\n✓ Duplicate detected!")
            print(f"  Original report ID: {result.id}")
            print(f"  Duplicate marked as: {duplicate.is_duplicate_of}")
            print(f"\nOriginal report updated:")
            print(f"  Corroboration count: {original.corroboration_count}")
            print(f"  Total people: {original.num_people}")
            print(f"  Vulnerable flags: {original.vulnerable_flags}")
            print(f"  Urgency score: {original.urgency_score:.2f}")
            print(f"  Verification status: {original.verification_status.value}")
        else:
            print("\n✗ No duplicate detected (unexpected)")
            
    finally:
        # Cleanup
        db.query(Report).filter(Report.id.in_([original.id, duplicate.id])).delete()
        db.commit()
        db.close()


def test_text_similarity():
    """Test text similarity duplicate detection."""
    print("\n=== Test 2: Text Similarity Duplicate Detection ===\n")
    
    db = SessionLocal()
    try:
        # Create original report
        original = create_test_report(
            raw_text="Earthquake caused building collapse. Multiple families trapped in debris. Need rescue team urgently.",
            disaster_type=DisasterTypeEnum.earthquake,
            latitude=None,  # No GPS
            longitude=None,
            num_people=15,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        db.add(original)
        db.commit()
        db.refresh(original)
        
        print(f"Original report created:")
        print(f"  ID: {original.id}")
        print(f"  Text: {original.raw_text[:60]}...")
        print(f"  People: {original.num_people}")
        
        # Create duplicate with similar text
        duplicate = create_test_report(
            raw_text="Building collapsed after earthquake. Families are trapped under rubble. Urgent rescue needed.",
            disaster_type=DisasterTypeEnum.earthquake,
            latitude=None,
            longitude=None,
            num_people=8,
            vulnerable_flags=["pregnant"],
            created_at=datetime.utcnow()
        )
        db.add(duplicate)
        db.commit()
        db.refresh(duplicate)
        
        print(f"\nDuplicate report created:")
        print(f"  ID: {duplicate.id}")
        print(f"  Text: {duplicate.raw_text[:60]}...")
        print(f"  People: {duplicate.num_people}")
        
        # Check for duplicates
        result = find_duplicates(duplicate, db)
        
        if result:
            db.refresh(original)
            db.refresh(duplicate)
            
            print(f"\n✓ Duplicate detected via text similarity!")
            print(f"  Original report ID: {result.id}")
            print(f"\nOriginal report updated:")
            print(f"  Corroboration count: {original.corroboration_count}")
            print(f"  Total people: {original.num_people}")
            print(f"  Vulnerable flags: {original.vulnerable_flags}")
            print(f"  Urgency score: {original.urgency_score:.2f}")
            print(f"  Verification status: {original.verification_status.value}")
        else:
            print("\n✗ No duplicate detected")
            
    finally:
        # Cleanup
        db.query(Report).filter(Report.id.in_([original.id, duplicate.id])).delete()
        db.commit()
        db.close()


def test_multiple_duplicates():
    """Test multiple duplicates corroborating the same report."""
    print("\n=== Test 3: Multiple Duplicates Corroboration ===\n")
    
    db = SessionLocal()
    report_ids = []
    
    try:
        # Create original report
        original = create_test_report(
            raw_text="Cyclone damage in coastal area. Homes destroyed.",
            disaster_type=DisasterTypeEnum.cyclone,
            latitude=23.5,
            longitude=87.5,
            num_people=20,
            created_at=datetime.utcnow() - timedelta(hours=3)
        )
        db.add(original)
        db.commit()
        db.refresh(original)
        report_ids.append(original.id)
        
        print(f"Original report created:")
        print(f"  ID: {original.id}")
        print(f"  Initial people: {original.num_people}")
        print(f"  Initial corroboration: {original.corroboration_count}")
        
        # Create 3 duplicate reports
        duplicates = []
        for i in range(3):
            dup = create_test_report(
                raw_text=f"Severe cyclone damage near coast. Many houses damaged. Report #{i+1}",
                disaster_type=DisasterTypeEnum.cyclone,
                latitude=23.5 + (0.001 * (i+1)),  # Close by
                longitude=87.5 + (0.001 * (i+1)),
                num_people=5 + i*2,
                vulnerable_flags=["elderly"] if i == 0 else ["child"] if i == 1 else ["disabled"],
                created_at=datetime.utcnow() - timedelta(hours=2-i)
            )
            db.add(dup)
            db.commit()
            db.refresh(dup)
            report_ids.append(dup.id)
            
            # Check for duplicates
            find_duplicates(dup, db)
            duplicates.append(dup)
            
            print(f"\nDuplicate #{i+1} processed:")
            print(f"  ID: {dup.id}")
            print(f"  People: {dup.num_people}")
        
        # Refresh original to see final state
        db.refresh(original)
        
        print(f"\n=== Final State of Original Report ===")
        print(f"  Corroboration count: {original.corroboration_count}")
        print(f"  Total people: {original.num_people}")
        print(f"  Vulnerable flags: {original.vulnerable_flags}")
        print(f"  Urgency score: {original.urgency_score:.2f}")
        print(f"  Verification status: {original.verification_status.value}")
        
        # Get duplicate info
        info = get_duplicate_info(original, db)
        print(f"\n  Is original: {info['is_original']}")
        print(f"  Duplicate count: {info['duplicate_count']}")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id.in_(report_ids)).delete()
        db.commit()
        db.close()


def test_no_duplicate():
    """Test that non-duplicate reports are not flagged."""
    print("\n=== Test 4: No False Positives ===\n")
    
    db = SessionLocal()
    try:
        # Create original report
        original = create_test_report(
            raw_text="Flooding in north district",
            disaster_type=DisasterTypeEnum.flood,
            latitude=23.5,
            longitude=87.5,
            num_people=10,
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.add(original)
        db.commit()
        db.refresh(original)
        
        print(f"Original report: Flood at (23.5, 87.5)")
        
        # Create report far away and different text
        other_report = create_test_report(
            raw_text="Earthquake aftershocks felt in southern region",
            disaster_type=DisasterTypeEnum.earthquake,
            latitude=24.0,  # Far away (~50km)
            longitude=88.0,
            num_people=5,
            created_at=datetime.utcnow()
        )
        db.add(other_report)
        db.commit()
        db.refresh(other_report)
        
        print(f"Other report: Earthquake at (24.0, 88.0)")
        
        # Check for duplicates
        result = find_duplicates(other_report, db)
        
        if result:
            print(f"\n✗ False positive! Reports incorrectly marked as duplicates")
        else:
            print(f"\n✓ Correctly identified as separate incidents")
            print(f"  Different disaster types, far apart, different text")
            
    finally:
        # Cleanup
        db.query(Report).filter(Report.id.in_([original.id, other_report.id])).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("RescueAI Deduplication Pipeline Test Suite")
    print("=" * 60)
    
    test_geo_proximity()
    test_text_similarity()
    test_multiple_duplicates()
    test_no_duplicate()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
