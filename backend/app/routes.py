"""
API routes for RescueAI.

Endpoints for:
- Report management
- Team dispatch
- Urgency recommendations
- Demo simulation
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.models import Report, Team, StatusEnum, TeamStatusEnum, DisasterTypeEnum, SourceEnum, VerificationStatusEnum
from app.pipeline.dispatch import (
    recommend_dispatch,
    assign_team_to_report,
    get_dispatch_summary,
    get_team_workload
)
from app.pipeline.scoring import get_urgency_explanation

router = APIRouter()


# ==================== Demo Simulation ====================

@router.post("/demo/simulate-burst")
async def simulate_burst(db: Session = Depends(get_db)):
    """
    DEMO ENDPOINT: Simulate a burst of 15 incoming disaster reports.
    
    Generates reports over 30 seconds to demonstrate:
    - Real-time dashboard updates
    - Automatic deduplication
    - Urgency re-ranking
    - Verification status changes
    - Team dispatch recommendations
    
    Use this during demos to show the "thousands of reports flooding in" scenario.
    
    Returns:
    - Total reports created
    - Mix of disaster types
    - Some duplicates (will be auto-detected)
    - Some with vulnerable populations
    """
    import asyncio
    import random
    from faker import Faker
    from app.pipeline.dedup import find_duplicates
    from app.pipeline.scoring import update_report_urgency
    
    fake = Faker()
    created_reports = []
    
    # Base locations for clustering (to create duplicates)
    hotspots = [
        {"lat": 23.5, "lon": 87.5, "text": "Railway Station area"},
        {"lat": 23.52, "lon": 87.52, "text": "Market district"},
        {"lat": 23.48, "lon": 87.48, "text": "Residential zone near river"}
    ]
    
    # Report templates
    disaster_scenarios = {
        DisasterTypeEnum.flood: [
            "Severe flooding in {location}. Water level rising rapidly. {people} people trapped.",
            "Flash flood emergency at {location}. Need immediate evacuation. {people} families stranded.",
            "Flood water entered homes in {location}. {people} people need rescue.",
        ],
        DisasterTypeEnum.earthquake: [
            "Building collapsed in {location} after earthquake. {people} people buried in debris.",
            "Earthquake damage severe at {location}. {people} people injured, need medical help.",
            "Houses damaged by earthquake near {location}. {people} people homeless.",
        ],
        DisasterTypeEnum.cyclone: [
            "Cyclone damage in {location}. Roofs blown off. {people} people exposed.",
            "Strong winds destroyed homes at {location}. {people} families need shelter.",
            "Cyclone hit {location} hard. Trees fallen, {people} people trapped.",
        ]
    }
    
    vulnerable_options = [
        [],
        ["elderly"],
        ["child"],
        ["pregnant"],
        ["elderly", "child"],
        ["disabled"],
        ["elderly", "disabled"]
    ]
    
    # Create 15 reports over time
    for i in range(15):
        # Add slight delay to simulate real-time (but faster than 30s total for demo)
        if i > 0:
            await asyncio.sleep(2)  # 2 seconds between reports = 30s total
        
        # Pick disaster type
        disaster_type = random.choice(list(DisasterTypeEnum))
        
        # 40% chance to create near a hotspot (potential duplicate)
        if random.random() < 0.4 and hotspots:
            hotspot = random.choice(hotspots)
            # Add small variance
            lat = hotspot["lat"] + random.uniform(-0.002, 0.002)  # ~200m variance
            lon = hotspot["lon"] + random.uniform(-0.002, 0.002)
            location_text = hotspot["text"]
        else:
            # Random location
            lat = 23.5 + random.uniform(-0.1, 0.1)
            lon = 87.5 + random.uniform(-0.1, 0.1)
            location_text = fake.city()
        
        # Generate report text
        if disaster_type in disaster_scenarios:
            template = random.choice(disaster_scenarios[disaster_type])
            people_count = random.randint(5, 50)
            raw_text = template.format(
                location=location_text,
                people=people_count
            )
        else:
            raw_text = f"Emergency situation at {location_text}. {random.randint(5, 30)} people affected."
            people_count = random.randint(5, 30)
        
        # Create report
        report = Report(
            id=str(uuid.uuid4()),
            source=random.choice([SourceEnum.app, SourceEnum.sms, SourceEnum.whatsapp]),
            raw_text=raw_text,
            language=random.choice(["en", "hi", "bn"]),
            translated_text=raw_text,
            reporter_phone=fake.phone_number(),
            latitude=lat,
            longitude=lon,
            location_text=location_text,
            disaster_type=disaster_type,
            num_people=people_count,
            vulnerable_flags=random.choice(vulnerable_options),
            verification_status=VerificationStatusEnum.unverified,
            status=StatusEnum.new,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        # Check for duplicates
        find_duplicates(report, db)
        
        # Calculate urgency
        update_report_urgency(report, db)
        
        created_reports.append({
            "id": report.id,
            "disaster_type": report.disaster_type.value,
            "urgency_score": report.urgency_score,
            "num_people": report.num_people,
            "is_duplicate": report.is_duplicate_of is not None
        })
    
    # Summary statistics
    disaster_counts = {}
    for disaster_type in DisasterTypeEnum:
        count = len([r for r in created_reports if r["disaster_type"] == disaster_type.value])
        if count > 0:
            disaster_counts[disaster_type.value] = count
    
    duplicate_count = len([r for r in created_reports if r["is_duplicate"]])
    
    return {
        "success": True,
        "simulation": "burst",
        "total_created": len(created_reports),
        "duplicates_detected": duplicate_count,
        "unique_incidents": len(created_reports) - duplicate_count,
        "by_disaster_type": disaster_counts,
        "reports": created_reports,
        "message": f"Created {len(created_reports)} reports over 30 seconds. {duplicate_count} duplicates auto-detected and merged.",
        "demo_tip": "Refresh your dashboard to see real-time updates and urgency re-ranking!"
    }


# ==================== Report Endpoints ====================

@router.get("/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """
    Get a single report by ID.
    
    Returns full report details including:
    - Urgency breakdown with scoring explanation
    - Duplicate cluster members
    - Verification status and details
    - Assignment information
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get urgency explanation
    urgency_info = get_urgency_explanation(report)
    
    # Get duplicate cluster members (reports that reference this one as duplicate)
    duplicate_cluster = []
    if report.duplicates:  # This report is the primary
        duplicate_cluster = [
            {
                "id": dup.id,
                "raw_text": dup.raw_text[:100] + "..." if len(dup.raw_text) > 100 else dup.raw_text,
                "num_people": dup.num_people,
                "vulnerable_flags": dup.vulnerable_flags,
                "created_at": dup.created_at.isoformat() + 'Z',
                "reporter_phone": dup.reporter_phone
            }
            for dup in report.duplicates
        ]
    
    # If this report IS a duplicate, get the primary report info
    primary_report_info = None
    if report.is_duplicate_of:
        primary = db.query(Report).filter(Report.id == report.is_duplicate_of).first()
        if primary:
            primary_report_info = {
                "id": primary.id,
                "disaster_type": primary.disaster_type.value,
                "urgency_score": primary.urgency_score,
                "status": primary.status.value
            }
    
    return {
        "id": report.id,
        "source": report.source.value,
        "raw_text": report.raw_text,
        "language": report.language,
        "translated_text": report.translated_text,
        "reporter_phone": report.reporter_phone,
        "disaster_type": report.disaster_type.value,
        "location": {
            "latitude": report.latitude,
            "longitude": report.longitude,
            "location_text": report.location_text
        },
        "num_people": report.num_people,
        "vulnerable_flags": report.vulnerable_flags or [],
        "verification_status": report.verification_status.value,
        "urgency": {
            "score": report.urgency_score,
            "breakdown": urgency_info,
            "explanation": report.urgency_breakdown or {}
        },
        "status": report.status.value,
        "assigned_team": report.assigned_team,
        "corroboration_count": report.corroboration_count,
        "duplicate_info": {
            "is_duplicate": report.is_duplicate_of is not None,
            "is_duplicate_of": report.is_duplicate_of,
            "primary_report": primary_report_info,
            "duplicate_cluster": duplicate_cluster,
            "total_duplicates": len(duplicate_cluster)
        },
        "created_at": report.created_at.isoformat() + 'Z',
        "updated_at": report.updated_at.isoformat() + 'Z'
    }


@router.get("/reports/{report_id}/recommend-dispatch")
async def get_dispatch_recommendations(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Get team dispatch recommendations for a report.
    
    Returns top 3 nearest available teams with distance and ETA.
    
    Example Response:
    {
        "report_id": "...",
        "location": {"lat": 23.5, "lon": 87.5},
        "recommendations": [
            {
                "team_id": "...",
                "team_name": "NDRF Alpha Team",
                "team_type": "NDRF",
                "capacity": 20,
                "distance_km": 5.2,
                "eta_estimate": "~8 min"
            }
        ]
    }
    """
    # Get report
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Check if report has location
    if not report.latitude or not report.longitude:
        raise HTTPException(
            status_code=400,
            detail="Report does not have location data for dispatch recommendation"
        )
    
    # Get all teams
    all_teams = db.query(Team).all()
    
    # Get recommendations
    recommendations = recommend_dispatch(report, all_teams)
    
    return {
        "report_id": report.id,
        "disaster_type": report.disaster_type.value,
        "urgency_score": report.urgency_score,
        "location": {
            "latitude": report.latitude,
            "longitude": report.longitude
        },
        "recommendations": recommendations,
        "total_available_teams": len([t for t in all_teams if t.status == TeamStatusEnum.available]),
        "message": "No available teams nearby" if not recommendations else f"Found {len(recommendations)} team(s) nearby"
    }


@router.post("/reports/{report_id}/assign")
async def assign_team(
    report_id: str,
    team_id: str,
    db: Session = Depends(get_db)
):
    """
    Assign a team to a report.
    
    Actions:
    - Sets report.assigned_team
    - Updates report.status to "in_progress"
    - Updates team.status to "deployed"
    
    Request Body:
    {
        "team_id": "uuid-of-team"
    }
    
    Example Response:
    {
        "success": true,
        "report_id": "...",
        "team_id": "...",
        "team_name": "NDRF Alpha Team",
        "assignment": {
            "report_status": "in_progress",
            "team_status": "deployed",
            "assigned_at": "2026-07-06T12:34:56Z"
        }
    }
    """
    # Get report
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get team
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Check if team is available
    if team.status != TeamStatusEnum.available:
        raise HTTPException(
            status_code=400,
            detail=f"Team is not available (current status: {team.status.value})"
        )
    
    # Check if report is already assigned
    if report.assigned_team and report.status == StatusEnum.in_progress:
        raise HTTPException(
            status_code=400,
            detail=f"Report is already assigned to {report.assigned_team}"
        )
    
    # Perform assignment
    result = assign_team_to_report(report, team, db)
    
    return result


@router.delete("/reports/{report_id}/assign")
async def unassign_team(
    report_id: str,
    db: Session = Depends(get_db)
):
    """
    Unassign a team from a report.
    
    Actions:
    - Clears report.assigned_team
    - Updates team.status back to "available"
    
    Example Response:
    {
        "success": true,
        "report_id": "...",
        "message": "Team unassigned successfully"
    }
    """
    from app.pipeline.dispatch import unassign_team_from_report
    
    # Get report
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Check if report has assignment
    if not report.assigned_team:
        raise HTTPException(status_code=400, detail="Report has no team assigned")
    
    # Find the team
    team = db.query(Team).filter(Team.name == report.assigned_team).first()
    
    if not team:
        # Team not found, just clear the assignment
        report.assigned_team = None
        db.add(report)
        db.commit()
        return {
            "success": True,
            "report_id": report.id,
            "message": "Assignment cleared (team not found in database)"
        }
    
    # Perform unassignment
    result = unassign_team_from_report(report, team, db)
    
    return {
        **result,
        "message": "Team unassigned successfully"
    }


@router.patch("/reports/{report_id}/status")
async def update_report_status(
    report_id: str,
    new_status: str,
    db: Session = Depends(get_db)
):
    """
    Manually update a report's status.
    
    Request Body:
    {
        "status": "in_progress" | "resolved" | "false_report" | "new"
    }
    
    Example Response:
    {
        "success": true,
        "report_id": "...",
        "old_status": "new",
        "new_status": "resolved",
        "updated_at": "2026-07-06T12:34:56Z"
    }
    """
    # Get report
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Validate new status
    try:
        status_enum = StatusEnum(new_status)
    except ValueError:
        valid_statuses = [s.value for s in StatusEnum]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}"
        )
    
    # Store old status
    old_status = report.status.value
    
    # Update status
    report.status = status_enum
    report.updated_at = datetime.utcnow()
    
    db.add(report)
    db.commit()
    db.refresh(report)
    
    return {
        "success": True,
        "report_id": report.id,
        "old_status": old_status,
        "new_status": report.status.value,
        "updated_at": report.updated_at.isoformat() + 'Z'
    }


# ==================== Statistics Endpoints ====================

@router.get("/stats/summary")
async def get_stats_summary(db: Session = Depends(get_db)):
    """
    Get dashboard statistics summary.
    
    Returns:
    - Total active reports (excluding resolved/false_report/duplicates)
    - Reports by disaster type
    - Reports by verification status
    - Average urgency score
    - Count of vulnerable-flagged cases still unresolved
    - Teams available vs deployed
    
    Example Response:
    {
        "reports": {
            "total_active": 25,
            "by_disaster_type": {"flood": 10, "earthquake": 8, "cyclone": 7},
            "by_verification_status": {"unverified": 15, "corroborated": 8, "satellite_confirmed": 2},
            "by_status": {"new": 10, "in_progress": 12, "resolved": 3},
            "average_urgency": 65.4,
            "vulnerable_unresolved": 8
        },
        "teams": {
            "total": 12,
            "available": 7,
            "deployed": 5,
            "by_type": {"NDRF": 4, "SDRF": 3, "NGO": 3, "volunteer": 2}
        }
    }
    """
    from app.models import DisasterTypeEnum, VerificationStatusEnum, TeamTypeEnum
    from sqlalchemy import func
    
    # Get active reports (exclude resolved, false_report, and duplicates)
    active_reports = db.query(Report).filter(
        Report.is_duplicate_of.is_(None),
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).all()
    
    # All reports (excluding duplicates for statistics)
    all_reports = db.query(Report).filter(Report.is_duplicate_of.is_(None)).all()
    
    # Count by disaster type
    by_disaster_type = {}
    for disaster_type in DisasterTypeEnum:
        count = len([r for r in active_reports if r.disaster_type == disaster_type])
        if count > 0:
            by_disaster_type[disaster_type.value] = count
    
    # Count by verification status
    by_verification_status = {}
    for verification_status in VerificationStatusEnum:
        count = len([r for r in active_reports if r.verification_status == verification_status])
        if count > 0:
            by_verification_status[verification_status.value] = count
    
    # Count by status (all reports, not just active)
    by_status = {}
    for status in StatusEnum:
        count = len([r for r in all_reports if r.status == status])
        if count > 0:
            by_status[status.value] = count
    
    # Calculate average urgency
    if active_reports:
        average_urgency = round(sum(r.urgency_score for r in active_reports) / len(active_reports), 1)
    else:
        average_urgency = 0.0
    
    # Count vulnerable-flagged cases still unresolved
    vulnerable_unresolved = len([
        r for r in active_reports
        if r.vulnerable_flags and len(r.vulnerable_flags) > 0
    ])
    
    # Team statistics
    all_teams = db.query(Team).all()
    teams_available = len([t for t in all_teams if t.status == TeamStatusEnum.available])
    teams_deployed = len([t for t in all_teams if t.status == TeamStatusEnum.deployed])
    
    # Teams by type
    by_team_type = {}
    for team_type in TeamTypeEnum:
        count = len([t for t in all_teams if t.type == team_type])
        if count > 0:
            by_team_type[team_type.value] = count
    
    return {
        "reports": {
            "total_active": len(active_reports),
            "total_all": len(all_reports),
            "by_disaster_type": by_disaster_type,
            "by_verification_status": by_verification_status,
            "by_status": by_status,
            "average_urgency": average_urgency,
            "vulnerable_unresolved": vulnerable_unresolved,
            "high_urgency_count": len([r for r in active_reports if r.urgency_score >= 70])
        },
        "teams": {
            "total": len(all_teams),
            "available": teams_available,
            "deployed": teams_deployed,
            "by_type": by_team_type,
            "utilization_rate": round(teams_deployed / len(all_teams) * 100, 1) if all_teams else 0.0
        },
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }


# ==================== Team Endpoints ====================

@router.get("/teams")
async def list_teams(
    status: Optional[str] = None,
    team_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all teams with optional filtering.
    
    Query Parameters:
    - status: Filter by status (available, deployed)
    - team_type: Filter by type (NDRF, SDRF, NGO, volunteer)
    
    Example Response:
    {
        "teams": [...],
        "total": 12,
        "filtered": 5
    }
    """
    query = db.query(Team)
    
    # Apply filters
    if status:
        try:
            status_enum = TeamStatusEnum(status)
            query = query.filter(Team.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if team_type:
        from app.models import TeamTypeEnum
        try:
            type_enum = TeamTypeEnum(team_type)
            query = query.filter(Team.type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid team_type: {team_type}")
    
    teams = query.all()
    
    return {
        "teams": [
            {
                "id": team.id,
                "name": team.name,
                "type": team.type.value,
                "capacity": team.capacity,
                "status": team.status.value,
                "location": {
                    "latitude": team.current_location_lat,
                    "longitude": team.current_location_lon
                }
            }
            for team in teams
        ],
        "total": db.query(Team).count(),
        "filtered": len(teams)
    }


@router.get("/teams/{team_id}")
async def get_team(team_id: str, db: Session = Depends(get_db)):
    """
    Get a single team by ID with workload info.
    """
    team = db.query(Team).filter(Team.id == team_id).first()
    
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    # Get workload
    workload = get_team_workload(team, db)
    
    return {
        "id": team.id,
        "name": team.name,
        "type": team.type.value,
        "capacity": team.capacity,
        "status": team.status.value,
        "location": {
            "latitude": team.current_location_lat,
            "longitude": team.current_location_lon
        },
        "workload": workload,
        "created_at": team.created_at.isoformat() + 'Z'
    }


# ==================== Dashboard Endpoints ====================

@router.get("/dispatch/summary")
async def dispatch_summary(db: Session = Depends(get_db)):
    """
    Get dispatch summary for dashboard.
    
    Returns:
    - Team statistics (available, deployed, by type)
    - Report statistics (assigned, unassigned)
    - System utilization rates
    
    Example Response:
    {
        "teams": {
            "total_teams": 12,
            "available": 7,
            "deployed": 5
        },
        "reports": {
            "total_active": 25,
            "assigned": 18,
            "unassigned": 7
        }
    }
    """
    summary = get_dispatch_summary(db)
    
    return summary


@router.get("/reports")
async def list_reports(
    status: Optional[str] = None,
    disaster_type: Optional[str] = None,
    min_score: Optional[float] = None,
    sort: Optional[str] = "urgency_desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List reports with filtering and sorting.
    
    Query Parameters:
    - status: Filter by status (new, in_progress, resolved, false_report)
    - disaster_type: Filter by disaster type (flood, earthquake, cyclone, other)
    - min_score: Minimum urgency score (0-100)
    - sort: Sort order (urgency_desc, urgency_asc, created_desc, created_asc) default: urgency_desc
    - skip: Pagination offset (default 0)
    - limit: Maximum number of results (default 50)
    
    Returns reports sorted by urgency score (descending) by default.
    EXCLUDES reports that are marked as duplicates (only shows primary reports).
    """
    from app.models import DisasterTypeEnum
    
    # Start with base query: exclude duplicates
    query = db.query(Report).filter(Report.is_duplicate_of.is_(None))
    
    # Apply filters
    if status:
        try:
            status_enum = StatusEnum(status)
            query = query.filter(Report.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if disaster_type:
        try:
            type_enum = DisasterTypeEnum(disaster_type)
            query = query.filter(Report.disaster_type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid disaster_type: {disaster_type}")
    
    if min_score is not None:
        query = query.filter(Report.urgency_score >= min_score)
    
    # Apply sorting
    if sort == "urgency_desc":
        query = query.order_by(Report.urgency_score.desc())
    elif sort == "urgency_asc":
        query = query.order_by(Report.urgency_score.asc())
    elif sort == "created_desc":
        query = query.order_by(Report.created_at.desc())
    elif sort == "created_asc":
        query = query.order_by(Report.created_at.asc())
    else:
        raise HTTPException(status_code=400, detail=f"Invalid sort parameter: {sort}")
    
    # Get total count before pagination
    total_matching = query.count()
    
    # Apply pagination
    reports = query.offset(skip).limit(limit).all()
    
    return {
        "reports": [
            {
                "id": report.id,
                "disaster_type": report.disaster_type.value,
                "urgency_score": report.urgency_score,
                "status": report.status.value,
                "verification_status": report.verification_status.value,
                "assigned_team": report.assigned_team,
                "num_people": report.num_people,
                "vulnerable_flags": report.vulnerable_flags or [],
                "corroboration_count": report.corroboration_count,
                "location": {
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "text": report.location_text
                },
                "created_at": report.created_at.isoformat() + 'Z',
                "updated_at": report.updated_at.isoformat() + 'Z',
                "age_hours": round((datetime.utcnow() - report.created_at).total_seconds() / 3600, 1)
            }
            for report in reports
        ],
        "count": len(reports),
        "total": total_matching,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(reports)) < total_matching
    }
