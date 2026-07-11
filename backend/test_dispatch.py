"""
Test script for team dispatch system.
Validates dispatch recommendations and team assignment logic.
"""

from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Report, Team, SourceEnum, DisasterTypeEnum, StatusEnum, TeamTypeEnum, TeamStatusEnum
from app.pipeline.dispatch import (
    recommend_dispatch,
    assign_team_to_report,
    unassign_team_from_report,
    get_team_workload,
    get_dispatch_summary,
    find_best_team_for_report,
    haversine_distance
)
import uuid


def create_test_report(**kwargs) -> Report:
    """Helper to create a test report."""
    defaults = {
        'id': str(uuid.uuid4()),
        'source': SourceEnum.app,
        'raw_text': "Test disaster report",
        'language': "en",
        'translated_text': "Test disaster report",
        'disaster_type': DisasterTypeEnum.flood,
        'latitude': 23.5,
        'longitude': 87.5,
        'num_people': 20,
        'urgency_score': 50.0,
        'status': StatusEnum.new,
        'created_at': datetime.utcnow()
    }
    defaults.update(kwargs)
    return Report(**defaults)


def create_test_team(**kwargs) -> Team:
    """Helper to create a test team."""
    defaults = {
        'id': str(uuid.uuid4()),
        'name': f"Test Team {uuid.uuid4().hex[:8]}",
        'type': TeamTypeEnum.NDRF,
        'capacity': 20,
        'current_location_lat': 23.5,
        'current_location_lon': 87.5,
        'status': TeamStatusEnum.available
    }
    defaults.update(kwargs)
    return Team(**defaults)


def test_haversine_distance():
    """Test 1: Haversine distance calculation."""
    print("\n=== Test 1: Haversine Distance Calculation ===\n")
    
    # Test known distances
    test_cases = [
        ((23.5, 87.5), (23.5, 87.5), 0.0, "Same location"),
        ((23.5, 87.5), (23.51, 87.51), 1.56, "~1.5 km apart"),
        ((23.5, 87.5), (23.6, 87.6), 15.6, "~15 km apart"),
        ((23.5, 87.5), (24.0, 88.0), 78.1, "~78 km apart")
    ]
    
    for (lat1, lon1), (lat2, lon2), expected, description in test_cases:
        distance = haversine_distance(lat1, lon1, lat2, lon2)
        print(f"{description}:")
        print(f"  Point 1: ({lat1}, {lon1})")
        print(f"  Point 2: ({lat2}, {lon2})")
        print(f"  Distance: {distance:.2f} km (expected ~{expected} km)")
        print()


def test_recommend_dispatch():
    """Test 2: Team dispatch recommendations."""
    print("\n=== Test 2: Team Dispatch Recommendations ===\n")
    
    # Create test report
    report = create_test_report(
        latitude=23.5,
        longitude=87.5
    )
    
    print(f"Report location: ({report.latitude}, {report.longitude})\n")
    
    # Create teams at different distances
    teams = [
        create_test_team(
            name="Nearby Team",
            current_location_lat=23.51,
            current_location_lon=87.51,  # ~1.5 km away
            status=TeamStatusEnum.available
        ),
        create_test_team(
            name="Medium Distance Team",
            current_location_lat=23.55,
            current_location_lon=87.55,  # ~7 km away
            status=TeamStatusEnum.available
        ),
        create_test_team(
            name="Far Team",
            current_location_lat=23.7,
            current_location_lon=87.7,  # ~31 km away
            status=TeamStatusEnum.available
        ),
        create_test_team(
            name="Deployed Team",
            current_location_lat=23.52,
            current_location_lon=87.52,
            status=TeamStatusEnum.deployed  # Should not appear in recommendations
        )
    ]
    
    # Get recommendations
    recommendations = recommend_dispatch(report, teams)
    
    print(f"Recommended Teams (Top 3):\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['team_name']}")
        print(f"   Type: {rec['team_type']}")
        print(f"   Distance: {rec['distance_km']} km")
        print(f"   ETA: {rec['eta_estimate']}")
        print(f"   Capacity: {rec['capacity']} personnel")
        print()
    
    # Verify nearest team is first
    if recommendations:
        assert recommendations[0]['team_name'] == "Nearby Team", "Nearest team should be first"
        assert len(recommendations) == 3, "Should return top 3 teams"
        print("✓ Recommendations correctly sorted by distance")


def test_assign_team():
    """Test 3: Team assignment to report."""
    print("\n=== Test 3: Team Assignment ===\n")
    
    db = SessionLocal()
    
    try:
        # Create and save report
        report = create_test_report()
        db.add(report)
        
        # Create and save team
        team = create_test_team(name="Response Team Alpha")
        db.add(team)
        
        db.commit()
        db.refresh(report)
        db.refresh(team)
        
        print(f"Before Assignment:")
        print(f"  Report status: {report.status.value}")
        print(f"  Report assigned_team: {report.assigned_team}")
        print(f"  Team status: {team.status.value}")
        print()
        
        # Perform assignment
        result = assign_team_to_report(report, team, db)
        
        db.refresh(report)
        db.refresh(team)
        
        print(f"After Assignment:")
        print(f"  Report status: {report.status.value}")
        print(f"  Report assigned_team: {report.assigned_team}")
        print(f"  Team status: {team.status.value}")
        print()
        
        # Verify changes
        assert report.assigned_team == team.name, "Report should be assigned to team"
        assert report.status == StatusEnum.in_progress, "Report should be in_progress"
        assert team.status == TeamStatusEnum.deployed, "Team should be deployed"
        
        print("✓ Assignment completed successfully")
        print(f"\nAssignment Details:")
        print(f"  {result}")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id == report.id).delete()
        db.query(Team).filter(Team.id == team.id).delete()
        db.commit()
        db.close()


def test_unassign_team():
    """Test 4: Unassigning team from report."""
    print("\n=== Test 4: Team Unassignment ===\n")
    
    db = SessionLocal()
    
    try:
        # Create assigned report and deployed team
        report = create_test_report(
            assigned_team="Response Team Beta",
            status=StatusEnum.in_progress
        )
        team = create_test_team(
            name="Response Team Beta",
            status=TeamStatusEnum.deployed
        )
        
        db.add(report)
        db.add(team)
        db.commit()
        db.refresh(report)
        db.refresh(team)
        
        print(f"Before Unassignment:")
        print(f"  Report assigned_team: {report.assigned_team}")
        print(f"  Team status: {team.status.value}")
        print()
        
        # Perform unassignment
        result = unassign_team_from_report(report, team, db)
        
        db.refresh(report)
        db.refresh(team)
        
        print(f"After Unassignment:")
        print(f"  Report assigned_team: {report.assigned_team}")
        print(f"  Team status: {team.status.value}")
        print()
        
        # Verify changes
        assert report.assigned_team is None, "Report should have no assignment"
        assert team.status == TeamStatusEnum.available, "Team should be available"
        
        print("✓ Unassignment completed successfully")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id == report.id).delete()
        db.query(Team).filter(Team.id == team.id).delete()
        db.commit()
        db.close()


def test_team_workload():
    """Test 5: Team workload calculation."""
    print("\n=== Test 5: Team Workload Calculation ===\n")
    
    db = SessionLocal()
    
    try:
        # Create team
        team = create_test_team(name="Workload Test Team")
        db.add(team)
        
        # Create multiple reports assigned to this team
        reports = [
            create_test_report(assigned_team=team.name, status=StatusEnum.new),
            create_test_report(assigned_team=team.name, status=StatusEnum.in_progress),
            create_test_report(assigned_team=team.name, status=StatusEnum.in_progress),
            create_test_report(assigned_team=team.name, status=StatusEnum.resolved)
        ]
        
        for r in reports:
            db.add(r)
        
        db.commit()
        db.refresh(team)
        
        # Get workload
        workload = get_team_workload(team, db)
        
        print(f"Team: {workload['team_name']}")
        print(f"Status: {workload['status']}")
        print(f"Total assigned: {workload['total_assigned']}")
        print(f"Active assignments: {workload['active_assignments']}")
        print(f"\nBy Status:")
        for status, count in workload['by_status'].items():
            if count > 0:
                print(f"  {status}: {count}")
        
        # Verify counts
        assert workload['total_assigned'] == 4, "Should have 4 total assignments"
        assert workload['active_assignments'] == 3, "Should have 3 active (new + in_progress)"
        
        print("\n✓ Workload calculation correct")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.assigned_team == team.name).delete()
        db.query(Team).filter(Team.id == team.id).delete()
        db.commit()
        db.close()


def test_dispatch_summary():
    """Test 6: Dispatch summary for dashboard."""
    print("\n=== Test 6: Dispatch Summary ===\n")
    
    db = SessionLocal()
    
    try:
        # Create mix of teams
        teams = [
            create_test_team(name="Team 1", type=TeamTypeEnum.NDRF, status=TeamStatusEnum.available),
            create_test_team(name="Team 2", type=TeamTypeEnum.NDRF, status=TeamStatusEnum.deployed),
            create_test_team(name="Team 3", type=TeamTypeEnum.SDRF, status=TeamStatusEnum.available),
            create_test_team(name="Team 4", type=TeamTypeEnum.NGO, status=TeamStatusEnum.deployed)
        ]
        
        for team in teams:
            db.add(team)
        
        # Create mix of reports
        reports = [
            create_test_report(assigned_team="Team 1", status=StatusEnum.in_progress),
            create_test_report(assigned_team="Team 2", status=StatusEnum.in_progress),
            create_test_report(status=StatusEnum.new),  # Unassigned
            create_test_report(status=StatusEnum.new)   # Unassigned
        ]
        
        for report in reports:
            db.add(report)
        
        db.commit()
        
        # Get summary
        summary = get_dispatch_summary(db)
        
        print("Team Statistics:")
        print(f"  Total teams: {summary['teams']['total_teams']}")
        print(f"  Available: {summary['teams']['available']}")
        print(f"  Deployed: {summary['teams']['deployed']}")
        print(f"  By type: {summary['teams']['by_type']}")
        
        print(f"\nReport Statistics:")
        print(f"  Total active: {summary['reports']['total_active']}")
        print(f"  Assigned: {summary['reports']['assigned']}")
        print(f"  Unassigned: {summary['reports']['unassigned']}")
        
        print(f"\nUtilization:")
        print(f"  Team deployment rate: {summary['utilization']['team_deployment_rate']:.1f}%")
        print(f"  Report assignment rate: {summary['utilization']['report_assignment_rate']:.1f}%")
        
        print("\n✓ Summary calculated successfully")
        
    finally:
        # Cleanup
        for team in teams:
            db.query(Report).filter(Report.assigned_team == team.name).delete()
            db.query(Team).filter(Team.id == team.id).delete()
        db.query(Report).filter(Report.id.in_([r.id for r in reports])).delete()
        db.commit()
        db.close()


def test_find_best_team():
    """Test 7: Find single best team for report."""
    print("\n=== Test 7: Find Best Team ===\n")
    
    db = SessionLocal()
    
    try:
        # Create report
        report = create_test_report(latitude=23.5, longitude=87.5)
        db.add(report)
        
        # Create teams
        teams = [
            create_test_team(
                name="Closest Team",
                current_location_lat=23.51,
                current_location_lon=87.51,
                status=TeamStatusEnum.available
            ),
            create_test_team(
                name="Further Team",
                current_location_lat=23.6,
                current_location_lon=87.6,
                status=TeamStatusEnum.available
            )
        ]
        
        for team in teams:
            db.add(team)
        
        db.commit()
        db.refresh(report)
        
        # Find best team
        best = find_best_team_for_report(report, db)
        
        if best:
            print(f"Best team for report:")
            print(f"  Name: {best['team_name']}")
            print(f"  Distance: {best['distance_km']} km")
            print(f"  ETA: {best['eta_estimate']}")
            
            assert best['team_name'] == "Closest Team", "Should recommend closest team"
            print("\n✓ Best team correctly identified")
        else:
            print("✗ No team found")
        
    finally:
        # Cleanup
        db.query(Report).filter(Report.id == report.id).delete()
        for team in teams:
            db.query(Team).filter(Team.id == team.id).delete()
        db.commit()
        db.close()


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Team Dispatch System Test Suite")
    print("=" * 70)
    
    test_haversine_distance()
    test_recommend_dispatch()
    test_assign_team()
    test_unassign_team()
    test_team_workload()
    test_dispatch_summary()
    test_find_best_team()
    
    print("\n" + "=" * 70)
    print("All tests completed!")
    print("\nKey Features Demonstrated:")
    print("✓ Distance-based team recommendations")
    print("✓ Team assignment with status updates")
    print("✓ Team unassignment and availability management")
    print("✓ Workload tracking per team")
    print("✓ System-wide dispatch summary")
    print("✓ Best team selection algorithm")
    print("=" * 70)
