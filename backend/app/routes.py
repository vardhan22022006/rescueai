"""
API routes for RescueAI.

Endpoints for:
- Report management
- Team dispatch
- Urgency recommendations
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models import Report, Team, StatusEnum, TeamStatusEnum
from app.pipeline.dispatch import (
    recommend_dispatch,
    assign_team_to_report,
    get_dispatch_summary,
    get_team_workload
)
from app.pipeline.scoring import get_urgency_explanation

router = APIRouter()


# ==================== Report Endpoints ====================

@router.get("/reports/{report_id}")
async def get_report(report_id: str, db: Session = Depends(get_db)):
    """
    Get a single report by ID.
    
    Returns report with urgency breakdown and assignment info.
    """
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get urgency explanation
    urgency_info = get_urgency_explanation(report)
    
    return {
        "id": report.id,
        "source": report.source.value,
        "raw_text": report.raw_text,
        "language": report.language,
        "disaster_type": report.disaster_type.value,
        "location": {
            "latitude": report.latitude,
            "longitude": report.longitude,
            "location_text": report.location_text
        },
        "num_people": report.num_people,
        "vulnerable_flags": report.vulnerable_flags,
        "verification_status": report.verification_status.value,
        "urgency": {
            "score": report.urgency_score,
            "breakdown": urgency_info
        },
        "status": report.status.value,
        "assigned_team": report.assigned_team,
        "corroboration_count": report.corroboration_count,
        "is_duplicate_of": report.is_duplicate_of,
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
    min_urgency: Optional[float] = None,
    assigned_only: Optional[bool] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    List reports with filtering and sorting.
    
    Query Parameters:
    - status: Filter by status (new, in_progress, resolved)
    - disaster_type: Filter by disaster type
    - min_urgency: Minimum urgency score
    - assigned_only: Show only assigned (true) or unassigned (false) reports
    - limit: Maximum number of results (default 50)
    
    Returns reports sorted by urgency score (descending).
    """
    query = db.query(Report)
    
    # Apply filters
    if status:
        try:
            status_enum = StatusEnum(status)
            query = query.filter(Report.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    
    if disaster_type:
        from app.models import DisasterTypeEnum
        try:
            type_enum = DisasterTypeEnum(disaster_type)
            query = query.filter(Report.disaster_type == type_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid disaster_type: {disaster_type}")
    
    if min_urgency is not None:
        query = query.filter(Report.urgency_score >= min_urgency)
    
    if assigned_only is not None:
        if assigned_only:
            query = query.filter(Report.assigned_team.isnot(None))
        else:
            query = query.filter(Report.assigned_team.is_(None))
    
    # Sort by urgency (highest first) and limit
    reports = query.order_by(Report.urgency_score.desc()).limit(limit).all()
    
    return {
        "reports": [
            {
                "id": report.id,
                "disaster_type": report.disaster_type.value,
                "urgency_score": report.urgency_score,
                "status": report.status.value,
                "assigned_team": report.assigned_team,
                "num_people": report.num_people,
                "location": {
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "text": report.location_text
                },
                "created_at": report.created_at.isoformat() + 'Z',
                "age_hours": (report.updated_at - report.created_at).total_seconds() / 3600
            }
            for report in reports
        ],
        "count": len(reports),
        "total_matching": query.count()
    }
