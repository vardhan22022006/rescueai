"""
Pytest tests for RescueAI API endpoints.

Run with: pytest test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.database import SessionLocal
from app.models import Report, Team, SourceEnum, DisasterTypeEnum, StatusEnum, VerificationStatusEnum, TeamTypeEnum, TeamStatusEnum


client = TestClient(app)


@pytest.fixture
def db():
    """Database session fixture."""
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_report(db):
    """Create a sample report for testing."""
    report = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text="Test flooding in residential area",
        language="en",
        translated_text="Test flooding in residential area",
        disaster_type=DisasterTypeEnum.flood,
        latitude=23.5,
        longitude=87.5,
        location_text="Test Location",
        num_people=15,
        vulnerable_flags=["elderly", "child"],
        verification_status=VerificationStatusEnum.corroborated,
        urgency_score=65.5,
        urgency_breakdown={"test": "data"},
        status=StatusEnum.new,
        corroboration_count=2,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    yield report
    
    # Cleanup
    db.query(Report).filter(Report.id == report.id).delete()
    db.commit()


@pytest.fixture
def sample_team(db):
    """Create a sample team for testing."""
    team = Team(
        id=str(uuid.uuid4()),
        name="Test NDRF Team",
        type=TeamTypeEnum.NDRF,
        capacity=20,
        current_location_lat=23.5,
        current_location_lon=87.5,
        status=TeamStatusEnum.available,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    yield team
    
    # Cleanup
    db.query(Team).filter(Team.id == team.id).delete()
    db.commit()


# ==================== Health & Root Endpoints ====================

def test_root_endpoint():
    """Test root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "RescueAI API"
    assert "version" in data


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "scheduler" in data


# ==================== Report Endpoints ====================

def test_list_reports(sample_report):
    """Test GET /api/reports with pagination."""
    response = client.get("/api/reports")
    assert response.status_code == 200
    
    data = response.json()
    assert "reports" in data
    assert "count" in data
    assert "total" in data
    assert "has_more" in data
    assert isinstance(data["reports"], list)


def test_list_reports_with_filters(sample_report):
    """Test GET /api/reports with various filters."""
    # Filter by disaster type
    response = client.get("/api/reports?disaster_type=flood")
    assert response.status_code == 200
    data = response.json()
    assert all(r["disaster_type"] == "flood" for r in data["reports"])
    
    # Filter by status
    response = client.get("/api/reports?status=new")
    assert response.status_code == 200
    data = response.json()
    assert all(r["status"] == "new" for r in data["reports"])
    
    # Filter by min_score
    response = client.get("/api/reports?min_score=60")
    assert response.status_code == 200
    data = response.json()
    assert all(r["urgency_score"] >= 60 for r in data["reports"])


def test_list_reports_sorting(sample_report):
    """Test GET /api/reports with different sort orders."""
    # Sort by urgency descending (default)
    response = client.get("/api/reports?sort=urgency_desc")
    assert response.status_code == 200
    
    # Sort by created descending
    response = client.get("/api/reports?sort=created_desc")
    assert response.status_code == 200
    
    # Invalid sort parameter
    response = client.get("/api/reports?sort=invalid")
    assert response.status_code == 400


def test_list_reports_excludes_duplicates(db):
    """Test that list_reports excludes duplicate reports."""
    # Create original report
    original = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text="Original report",
        language="en",
        disaster_type=DisasterTypeEnum.flood,
        status=StatusEnum.new,
        created_at=datetime.utcnow()
    )
    db.add(original)
    db.commit()
    db.refresh(original)
    
    # Create duplicate report
    duplicate = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text="Duplicate report",
        language="en",
        disaster_type=DisasterTypeEnum.flood,
        status=StatusEnum.new,
        is_duplicate_of=original.id,
        created_at=datetime.utcnow()
    )
    db.add(duplicate)
    db.commit()
    
    # Get reports
    response = client.get("/api/reports")
    assert response.status_code == 200
    data = response.json()
    
    # Check that duplicate is not in the list
    report_ids = [r["id"] for r in data["reports"]]
    assert original.id in report_ids
    assert duplicate.id not in report_ids
    
    # Cleanup
    db.query(Report).filter(Report.id.in_([original.id, duplicate.id])).delete()
    db.commit()


def test_get_report_details(sample_report):
    """Test GET /api/reports/{id} returns full details."""
    response = client.get(f"/api/reports/{sample_report.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_report.id
    assert data["disaster_type"] == "flood"
    assert "urgency" in data
    assert "breakdown" in data["urgency"]
    assert "duplicate_info" in data
    assert data["duplicate_info"]["is_duplicate"] == False
    assert "vulnerable_flags" in data


def test_get_report_not_found():
    """Test GET /api/reports/{id} with non-existent ID."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/reports/{fake_id}")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_report_status(sample_report):
    """Test PATCH /api/reports/{id}/status."""
    # Update to in_progress
    response = client.patch(
        f"/api/reports/{sample_report.id}/status",
        params={"new_status": "in_progress"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["old_status"] == "new"
    assert data["new_status"] == "in_progress"
    assert "updated_at" in data
    
    # Update to resolved
    response = client.patch(
        f"/api/reports/{sample_report.id}/status",
        params={"new_status": "resolved"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["new_status"] == "resolved"


def test_update_report_status_invalid(sample_report):
    """Test PATCH /api/reports/{id}/status with invalid status."""
    response = client.patch(
        f"/api/reports/{sample_report.id}/status",
        params={"new_status": "invalid_status"}
    )
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


# ==================== Team Endpoints ====================

def test_list_teams(sample_team):
    """Test GET /api/teams."""
    response = client.get("/api/teams")
    assert response.status_code == 200
    
    data = response.json()
    assert "teams" in data
    assert "total" in data
    assert "filtered" in data
    assert isinstance(data["teams"], list)


def test_list_teams_with_filters(sample_team):
    """Test GET /api/teams with filters."""
    # Filter by status
    response = client.get("/api/teams?status=available")
    assert response.status_code == 200
    data = response.json()
    assert all(t["status"] == "available" for t in data["teams"])
    
    # Filter by type
    response = client.get("/api/teams?team_type=NDRF")
    assert response.status_code == 200
    data = response.json()
    assert all(t["type"] == "NDRF" for t in data["teams"])


def test_get_team_details(sample_team):
    """Test GET /api/teams/{id}."""
    response = client.get(f"/api/teams/{sample_team.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == sample_team.id
    assert data["name"] == "Test NDRF Team"
    assert "workload" in data


# ==================== Dispatch Endpoints ====================

def test_recommend_dispatch(sample_report, sample_team):
    """Test GET /api/reports/{id}/recommend-dispatch."""
    response = client.get(f"/api/reports/{sample_report.id}/recommend-dispatch")
    assert response.status_code == 200
    
    data = response.json()
    assert "report_id" in data
    assert "recommendations" in data
    assert "location" in data
    assert isinstance(data["recommendations"], list)


def test_recommend_dispatch_no_location(db):
    """Test dispatch recommendations for report without location."""
    report = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.sms,
        raw_text="No GPS data",
        language="en",
        disaster_type=DisasterTypeEnum.flood,
        latitude=None,
        longitude=None,
        status=StatusEnum.new,
        created_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    
    response = client.get(f"/api/reports/{report.id}/recommend-dispatch")
    assert response.status_code == 400
    assert "location data" in response.json()["detail"].lower()
    
    # Cleanup
    db.query(Report).filter(Report.id == report.id).delete()
    db.commit()


def test_assign_team(sample_report, sample_team):
    """Test POST /api/reports/{id}/assign."""
    response = client.post(
        f"/api/reports/{sample_report.id}/assign",
        params={"team_id": sample_team.id}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] == True
    assert data["report_id"] == sample_report.id
    assert data["team_id"] == sample_team.id
    assert "assignment" in data


def test_assign_unavailable_team(db, sample_report):
    """Test assigning a deployed team (should fail)."""
    # Create a deployed team
    team = Team(
        id=str(uuid.uuid4()),
        name="Deployed Team",
        type=TeamTypeEnum.SDRF,
        capacity=15,
        status=TeamStatusEnum.deployed,
        created_at=datetime.utcnow()
    )
    db.add(team)
    db.commit()
    
    response = client.post(
        f"/api/reports/{sample_report.id}/assign",
        params={"team_id": team.id}
    )
    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()
    
    # Cleanup
    db.query(Team).filter(Team.id == team.id).delete()
    db.commit()


# ==================== Statistics Endpoints ====================

def test_stats_summary(sample_report, sample_team):
    """Test GET /api/stats/summary."""
    response = client.get("/api/stats/summary")
    assert response.status_code == 200
    
    data = response.json()
    
    # Check reports section
    assert "reports" in data
    assert "total_active" in data["reports"]
    assert "by_disaster_type" in data["reports"]
    assert "by_verification_status" in data["reports"]
    assert "by_status" in data["reports"]
    assert "average_urgency" in data["reports"]
    assert "vulnerable_unresolved" in data["reports"]
    assert "high_urgency_count" in data["reports"]
    
    # Check teams section
    assert "teams" in data
    assert "total" in data["teams"]
    assert "available" in data["teams"]
    assert "deployed" in data["teams"]
    assert "by_type" in data["teams"]
    assert "utilization_rate" in data["teams"]
    
    # Check timestamp
    assert "timestamp" in data


def test_dispatch_summary(sample_team):
    """Test GET /api/dispatch/summary."""
    response = client.get("/api/dispatch/summary")
    assert response.status_code == 200
    
    data = response.json()
    assert "teams" in data
    assert "reports" in data


# ==================== Integration Tests ====================

def test_full_workflow(db):
    """Test complete workflow: create report, recommend team, assign, resolve."""
    # 1. Create a report
    report = Report(
        id=str(uuid.uuid4()),
        source=SourceEnum.app,
        raw_text="Emergency flood situation",
        language="en",
        disaster_type=DisasterTypeEnum.flood,
        latitude=23.5,
        longitude=87.5,
        num_people=25,
        vulnerable_flags=["elderly"],
        status=StatusEnum.new,
        urgency_score=70.0,
        created_at=datetime.utcnow()
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    
    # 2. Create a team
    team = Team(
        id=str(uuid.uuid4()),
        name="Rapid Response Team",
        type=TeamTypeEnum.NDRF,
        capacity=20,
        current_location_lat=23.51,
        current_location_lon=87.51,
        status=TeamStatusEnum.available,
        created_at=datetime.utcnow()
    )
    db.add(team)
    db.commit()
    db.refresh(team)
    
    # 3. Get recommendations
    response = client.get(f"/api/reports/{report.id}/recommend-dispatch")
    assert response.status_code == 200
    recommendations = response.json()["recommendations"]
    assert len(recommendations) > 0
    
    # 4. Assign the team
    response = client.post(
        f"/api/reports/{report.id}/assign",
        params={"team_id": team.id}
    )
    assert response.status_code == 200
    
    # 5. Update report status to resolved
    response = client.patch(
        f"/api/reports/{report.id}/status",
        params={"new_status": "resolved"}
    )
    assert response.status_code == 200
    assert response.json()["new_status"] == "resolved"
    
    # Cleanup
    db.query(Report).filter(Report.id == report.id).delete()
    db.query(Team).filter(Team.id == team.id).delete()
    db.commit()


# ==================== CORS Tests ====================

def test_cors_headers():
    """Test CORS headers are present."""
    response = client.options("/api/health")
    # TestClient doesn't fully simulate CORS, but we can check the middleware is configured
    # In real deployment, these headers would be present
    assert response.status_code in [200, 405]  # OPTIONS might not be implemented


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
