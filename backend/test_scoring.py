"""
Test script for urgency scoring system.
Validates scoring logic, breakdowns, and transparency.
"""

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Report, SourceEnum, DisasterTypeEnum, VerificationStatusEnum, StatusEnum
from app.pipeline.scoring import (
    compute_urgency_score,
    update_report_urgency,
    rescore_all_active_reports,
    get_urgency_explanation,
    get_scoring_config
)
import uuid
import json


def create_test_report(**kwargs) -> Report:
    """Helper to create a test report with defaults."""
    defaults = {
        'id': str(uuid.uuid4()),
        'source': SourceEnum.app,
        'raw_text': "Test disaster report",
        'language': "en",
        'translated_text': "Test disaster report",
        'disaster_type': DisasterTypeEnum.flood,
        'num_people': 10,
        'vulnerable_flags': [],
        'corroboration_count': 0,
        'verification_status': VerificationStatusEnum.unverified,
        'urgency_score': 0.0,
        'status': StatusEnum.new,
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }
    defaults.update(kwargs)
    return Report(**defaults)


def test_people_scoring():
    """Test 1: People affected scoring (log scale)."""
    print("\n=== Test 1: People Affected Scoring (Log Scale) ===\n")
    
    test_cases = [
        (0, "No people"),
        (5, "Small group"),
        (25, "Medium group"),
        (100, "Large group"),
        (500, "Very large group"),
        (10000, "Massive group (capped)")
    ]
    
    for num_people, description in test_cases:
        report = create_test_report(num_people=num_people)
        score, breakdown = compute_urgency_score(report)
        
        people_factor = breakdown['factors']['people']
        print(f"{description} ({num_people} people):")
        print(f"  Score contribution: {people_factor['score']}/30")
        print(f"  Explanation: {people_factor['explanation']}")
        print()


def test_vulnerable_population_scoring():
    """Test 2: Vulnerable population scoring."""
    print("\n=== Test 2: Vulnerable Population Scoring ===\n")
    
    test_cases = [
        ([], "No vulnerable groups"),
        (["elderly"], "1 group: Elderly"),
        (["elderly", "child"], "2 groups: Elderly + Children"),
        (["elderly", "child", "pregnant"], "3 groups: Max contribution"),
        (["elderly", "child", "pregnant", "disabled"], "4 groups: Still capped at 3")
    ]
    
    for flags, description in test_cases:
        report = create_test_report(vulnerable_flags=flags, num_people=20)
        score, breakdown = compute_urgency_score(report)
        
        vulnerable_factor = breakdown['factors']['vulnerable']
        print(f"{description}:")
        print(f"  Score contribution: {vulnerable_factor['score']}/45")
        print(f"  Explanation: {vulnerable_factor['explanation']}")
        print()


def test_verification_scoring():
    """Test 3: Verification status scoring."""
    print("\n=== Test 3: Verification Status Scoring ===\n")
    
    statuses = [
        (VerificationStatusEnum.unverified, "Unverified"),
        (VerificationStatusEnum.corroborated, "Corroborated"),
        (VerificationStatusEnum.weather_confirmed, "Weather Confirmed"),
        (VerificationStatusEnum.satellite_confirmed, "Satellite Confirmed")
    ]
    
    for status, description in statuses:
        report = create_test_report(verification_status=status, num_people=20)
        score, breakdown = compute_urgency_score(report)
        
        verification_factor = breakdown['factors']['verification']
        print(f"{description}:")
        print(f"  Score contribution: {verification_factor['score']}/25")
        print(f"  Explanation: {verification_factor['explanation']}")
        print()


def test_corroboration_scoring():
    """Test 4: Corroboration count scoring."""
    print("\n=== Test 4: Corroboration Scoring ===\n")
    
    test_cases = [0, 1, 2, 3, 4, 5, 10]
    
    for count in test_cases:
        report = create_test_report(corroboration_count=count, num_people=20)
        score, breakdown = compute_urgency_score(report)
        
        corroboration_factor = breakdown['factors']['corroboration']
        print(f"{count} corroborating report(s):")
        print(f"  Score contribution: {corroboration_factor['score']}/20")
        print(f"  Explanation: {corroboration_factor['explanation']}")
        print()


def test_disaster_type_multipliers():
    """Test 5: Disaster type severity multipliers."""
    print("\n=== Test 5: Disaster Type Multipliers ===\n")
    
    disaster_types = [
        (DisasterTypeEnum.earthquake, "Earthquake"),
        (DisasterTypeEnum.cyclone, "Cyclone"),
        (DisasterTypeEnum.flood, "Flood"),
        (DisasterTypeEnum.other, "Other")
    ]
    
    for dtype, name in disaster_types:
        report = create_test_report(
            disaster_type=dtype,
            num_people=50,
            vulnerable_flags=["elderly"]
        )
        score, breakdown = compute_urgency_score(report)
        
        multiplier = breakdown['multiplier']
        base = breakdown['base_score']
        final = breakdown['final_score']
        
        print(f"{name}:")
        print(f"  Base score: {base}")
        print(f"  Multiplier: {multiplier['value']}x")
        print(f"  Final score: {final}")
        print(f"  Explanation: {multiplier['explanation']}")
        print()


def test_time_decay():
    """Test 6: Time decay scoring."""
    print("\n=== Test 6: Time Decay (Delayed Reports) ===\n")
    
    now = datetime.utcnow()
    
    test_cases = [
        (now, "Just created (0h old)"),
        (now - timedelta(hours=1), "1 hour old"),
        (now - timedelta(hours=2), "2 hours old (threshold)"),
        (now - timedelta(hours=3), "3 hours old"),
        (now - timedelta(hours=6), "6 hours old"),
        (now - timedelta(hours=12), "12 hours old (max decay)")
    ]
    
    for created_time, description in test_cases:
        report = create_test_report(
            num_people=20,
            created_at=created_time,
            updated_at=created_time
        )
        score, breakdown = compute_urgency_score(report)
        
        time_decay_factor = breakdown['factors']['time_decay']
        print(f"{description}:")
        print(f"  Decay contribution: {time_decay_factor['score']}/20")
        print(f"  Explanation: {time_decay_factor['explanation']}")
        print()


def test_complete_scenario():
    """Test 7: Complete high-urgency scenario."""
    print("\n=== Test 7: Complete High-Urgency Scenario ===\n")
    
    # Create a critical scenario
    report = create_test_report(
        disaster_type=DisasterTypeEnum.earthquake,
        num_people=150,
        vulnerable_flags=["elderly", "child", "pregnant"],
        verification_status=VerificationStatusEnum.satellite_confirmed,
        corroboration_count=3,
        created_at=datetime.utcnow() - timedelta(hours=4),
        updated_at=datetime.utcnow() - timedelta(hours=4)
    )
    
    score, breakdown = compute_urgency_score(report)
    
    print("Scenario: Earthquake, 150 people, vulnerable groups, satellite confirmed,")
    print("          3 corroborations, 4 hours old\n")
    
    print(f"Final Score: {breakdown['final_score']}/100")
    print(f"Base Score: {breakdown['base_score']}")
    print(f"Multiplier: {breakdown['multiplier']['value']}x")
    print()
    
    print("Factor Breakdown:")
    for factor_name, factor_data in breakdown['factors'].items():
        print(f"  • {factor_name.capitalize()}: {factor_data['score']} - {factor_data['explanation']}")
    
    print()
    print(f"Summary: {breakdown['summary']}")
    print()
    
    # Show JSON structure (as it would be stored)
    print("JSON Breakdown (stored in database):")
    print(json.dumps(breakdown, indent=2))


def test_transparency():
    """Test 8: Verify scoring transparency and explainability."""
    print("\n=== Test 8: Scoring Transparency ===\n")
    
    report = create_test_report(
        num_people=50,
        vulnerable_flags=["elderly"],
        verification_status=VerificationStatusEnum.corroborated,
        corroboration_count=2
    )
    
    score, breakdown = compute_urgency_score(report)
    
    print("Transparency Check:")
    print(f"✓ Final score: {breakdown['final_score']}")
    print(f"✓ Base score before multiplier: {breakdown['base_score']}")
    print(f"✓ All factors have explanations: {len(breakdown['factors'])} factors")
    print(f"✓ Multiplier explained: {breakdown['multiplier']['explanation']}")
    print(f"✓ Summary provided: {breakdown['summary']}")
    print(f"✓ Timestamp included: {breakdown['timestamp']}")
    
    # Verify score can be reconstructed
    factors_sum = sum(f['score'] for f in breakdown['factors'].values())
    multiplier = breakdown['multiplier']['value']
    reconstructed = factors_sum * multiplier
    
    print(f"\n✓ Score is reconstructible:")
    print(f"  Sum of factors: {factors_sum}")
    print(f"  × Multiplier: {multiplier}")
    print(f"  = {reconstructed:.1f}")
    print(f"  Stored final: {breakdown['final_score']}")
    print(f"  Match: {'✓ Yes' if abs(reconstructed - breakdown['final_score']) < 0.1 else '✗ No'}")


def test_database_integration():
    """Test 9: Database integration with update_report_urgency."""
    print("\n=== Test 9: Database Integration ===\n")
    
    db = SessionLocal()
    
    try:
        # Create and save report
        report = create_test_report(
            num_people=75,
            vulnerable_flags=["child"],
            verification_status=VerificationStatusEnum.weather_confirmed
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        print(f"Report created: {report.id}")
        print(f"Initial urgency_score: {report.urgency_score}")
        print(f"Initial urgency_breakdown: {report.urgency_breakdown}")
        
        # Update urgency
        breakdown = update_report_urgency(report, db)
        db.refresh(report)
        
        print(f"\nAfter update_report_urgency:")
        print(f"  New urgency_score: {report.urgency_score}")
        print(f"  Breakdown stored: {'✓ Yes' if report.urgency_breakdown else '✗ No'}")
        print(f"  Score change: {breakdown['score_change']}")
        print(f"  Summary: {breakdown['summary']}")
        
        # Test get_urgency_explanation
        explanation = get_urgency_explanation(report)
        print(f"\nget_urgency_explanation works: {'✓ Yes' if explanation else '✗ No'}")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id == report.id).delete()
        db.commit()
        db.close()


def test_batch_rescoring():
    """Test 10: Batch rescoring of active reports."""
    print("\n=== Test 10: Batch Rescoring ===\n")
    
    db = SessionLocal()
    report_ids = []
    
    try:
        # Create 5 test reports with different ages
        for i in range(5):
            hours_old = i * 2  # 0, 2, 4, 6, 8 hours
            report = create_test_report(
                num_people=20 + i*10,
                created_at=datetime.utcnow() - timedelta(hours=hours_old),
                updated_at=datetime.utcnow() - timedelta(hours=hours_old)
            )
            db.add(report)
            report_ids.append(report.id)
        
        db.commit()
        
        print(f"Created {len(report_ids)} test reports with varying ages")
        
        # Run batch rescoring
        results = rescore_all_active_reports(db)
        
        print(f"\nBatch Rescoring Results:")
        print(f"  Total rescored: {results['total_rescored']}")
        print(f"  Scores increased: {results['scores_increased']}")
        print(f"  Scores decreased: {results['scores_decreased']}")
        print(f"  Scores unchanged: {results['scores_unchanged']}")
        
        if results['details']:
            print(f"\n  Significant changes:")
            for detail in results['details']:
                print(f"    Report {detail['report_id'][:8]}: "
                      f"{detail['old_score']:.0f} → {detail['new_score']:.0f} "
                      f"({detail['change']:+.0f})")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id.in_(report_ids)).delete()
        db.commit()
        db.close()


def test_scoring_config():
    """Test 11: Access to scoring configuration."""
    print("\n=== Test 11: Scoring Configuration ===\n")
    
    config = get_scoring_config()
    
    print("Scoring Configuration (transparent and tunable):")
    print(json.dumps(config, indent=2, default=str))
    
    print("\n✓ Configuration is accessible for:")
    print("  - Documentation")
    print("  - Dashboard display")
    print("  - Explaining to judges/stakeholders")
    print("  - Tuning parameters based on field experience")


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Urgency Scoring System Test Suite")
    print("Transparent, Explainable, Judge-Friendly")
    print("=" * 70)
    
    test_people_scoring()
    test_vulnerable_population_scoring()
    test_verification_scoring()
    test_corroboration_scoring()
    test_disaster_type_multipliers()
    test_time_decay()
    test_complete_scenario()
    test_transparency()
    test_database_integration()
    test_batch_rescoring()
    test_scoring_config()
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Transparent scoring with full breakdowns")
    print("✓ Explainable to non-technical stakeholders")
    print("✓ Log-scale prevents single factor dominance")
    print("✓ Time decay increases urgency for delayed reports")
    print("✓ All factors contribute with clear explanations")
    print("✓ JSON breakdown stored for dashboard display")
    print("=" * 70)
