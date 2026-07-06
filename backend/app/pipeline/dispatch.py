"""
Team dispatch recommendation system.

Helps coordinate response by:
1. Finding available teams
2. Ranking by proximity to incident
3. Recommending top 3 nearest teams
4. Managing team assignments and status

Uses haversine distance for accurate geographic calculations.
"""

from typing import List, Dict, Optional
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.orm import Session

from app.models import Report, Team, StatusEnum, TeamStatusEnum


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees).
    
    Args:
        lat1, lon1: Latitude and longitude of point 1
        lat2, lon2: Latitude and longitude of point 2
    
    Returns:
        Distance in kilometers
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def recommend_dispatch(report: Report, available_teams: List[Team]) -> List[Dict]:
    """
    Recommend teams for dispatch based on proximity to incident.
    
    Algorithm:
    1. Filter teams with status "available"
    2. Calculate haversine distance from each team to report location
    3. Rank by distance (nearest first)
    4. Return top 3 with distance in km
    
    Args:
        report: Report requiring response
        available_teams: List of all teams (will be filtered to available)
    
    Returns:
        List of top 3 recommended teams with distance info:
        [
            {
                'team_id': str,
                'team_name': str,
                'team_type': str,
                'capacity': int,
                'current_location': {'lat': float, 'lon': float},
                'distance_km': float,
                'eta_estimate': str
            }
        ]
    """
    # Validate report has location
    if not report.latitude or not report.longitude:
        return []
    
    # Filter to available teams only
    available = [team for team in available_teams if team.status == TeamStatusEnum.available]
    
    if not available:
        return []
    
    # Calculate distances for teams with location data
    team_distances = []
    
    for team in available:
        # Skip teams without location data
        if not team.current_location_lat or not team.current_location_lon:
            continue
        
        # Calculate distance
        distance = haversine_distance(
            report.latitude,
            report.longitude,
            team.current_location_lat,
            team.current_location_lon
        )
        
        # Estimate ETA (rough estimate: 40 km/h average speed)
        eta_minutes = int((distance / 40) * 60)
        if eta_minutes < 5:
            eta_str = "< 5 min"
        elif eta_minutes < 60:
            eta_str = f"~{eta_minutes} min"
        else:
            hours = eta_minutes // 60
            minutes = eta_minutes % 60
            eta_str = f"~{hours}h {minutes}min"
        
        team_distances.append({
            'team_id': team.id,
            'team_name': team.name,
            'team_type': team.type.value,
            'capacity': team.capacity,
            'current_location': {
                'lat': team.current_location_lat,
                'lon': team.current_location_lon
            },
            'distance_km': round(distance, 2),
            'eta_estimate': eta_str
        })
    
    # Sort by distance (nearest first)
    team_distances.sort(key=lambda x: x['distance_km'])
    
    # Return top 3
    return team_distances[:3]


def assign_team_to_report(
    report: Report,
    team: Team,
    db: Session,
    auto_update_status: bool = True
) -> Dict:
    """
    Assign a team to a report and update statuses.
    
    Actions:
    1. Set report.assigned_team to team name
    2. Update report.status to "in_progress"
    3. Update team.status to "deployed"
    4. Commit changes to database
    
    Args:
        report: Report to assign
        team: Team to assign
        db: Database session
        auto_update_status: Whether to automatically update statuses
    
    Returns:
        Dict with assignment details and previous states
    """
    # Store previous states
    previous_report_status = report.status
    previous_team_status = team.status
    previous_assigned_team = report.assigned_team
    
    # Update report
    report.assigned_team = team.name
    
    if auto_update_status and report.status == StatusEnum.new:
        report.status = StatusEnum.in_progress
    
    # Update team
    if auto_update_status:
        team.status = TeamStatusEnum.deployed
    
    # Commit changes
    db.add(report)
    db.add(team)
    db.commit()
    db.refresh(report)
    db.refresh(team)
    
    return {
        'success': True,
        'report_id': report.id,
        'team_id': team.id,
        'team_name': team.name,
        'assignment': {
            'report_status': report.status.value,
            'team_status': team.status.value,
            'assigned_at': report.updated_at.isoformat() + 'Z'
        },
        'previous_state': {
            'report_status': previous_report_status.value,
            'team_status': previous_team_status.value,
            'previously_assigned': previous_assigned_team
        }
    }


def unassign_team_from_report(
    report: Report,
    team: Team,
    db: Session,
    auto_update_status: bool = True
) -> Dict:
    """
    Unassign a team from a report (e.g., if mission completed or reassigned).
    
    Actions:
    1. Clear report.assigned_team
    2. Optionally update team.status back to "available"
    3. Commit changes
    
    Args:
        report: Report to unassign
        team: Team to unassign
        db: Database session
        auto_update_status: Whether to automatically update team status
    
    Returns:
        Dict with unassignment details
    """
    previous_assigned = report.assigned_team
    
    # Clear assignment
    report.assigned_team = None
    
    # Update team status if auto-updating
    if auto_update_status and team.status == TeamStatusEnum.deployed:
        team.status = TeamStatusEnum.available
    
    db.add(report)
    db.add(team)
    db.commit()
    
    return {
        'success': True,
        'report_id': report.id,
        'team_id': team.id,
        'previous_assignment': previous_assigned,
        'team_status': team.status.value
    }


def get_team_workload(team: Team, db: Session) -> Dict:
    """
    Get current workload for a team.
    
    Returns count of assigned reports by status.
    
    Args:
        team: Team to check
        db: Database session
    
    Returns:
        Dict with workload info
    """
    from sqlalchemy import func
    
    # Count reports assigned to this team by status
    workload = db.query(
        Report.status,
        func.count(Report.id)
    ).filter(
        Report.assigned_team == team.name
    ).group_by(
        Report.status
    ).all()
    
    workload_dict = {status.value: 0 for status in StatusEnum}
    for status, count in workload:
        workload_dict[status.value] = count
    
    total_assigned = sum(workload_dict.values())
    active_count = workload_dict.get('new', 0) + workload_dict.get('in_progress', 0)
    
    return {
        'team_id': team.id,
        'team_name': team.name,
        'status': team.status.value,
        'total_assigned': total_assigned,
        'active_assignments': active_count,
        'by_status': workload_dict
    }


def get_dispatch_summary(db: Session) -> Dict:
    """
    Get overall dispatch summary for dashboard.
    
    Returns:
        Dict with system-wide dispatch statistics
    """
    # Count teams by status
    teams = db.query(Team).all()
    
    team_stats = {
        'total_teams': len(teams),
        'available': sum(1 for t in teams if t.status == TeamStatusEnum.available),
        'deployed': sum(1 for t in teams if t.status == TeamStatusEnum.deployed),
        'by_type': {}
    }
    
    # Count by team type
    from app.models import TeamTypeEnum
    for team_type in TeamTypeEnum:
        count = sum(1 for t in teams if t.type == team_type)
        team_stats['by_type'][team_type.value] = count
    
    # Count reports by assignment status
    reports = db.query(Report).filter(
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).all()
    
    report_stats = {
        'total_active': len(reports),
        'unassigned': sum(1 for r in reports if not r.assigned_team),
        'assigned': sum(1 for r in reports if r.assigned_team),
        'new': sum(1 for r in reports if r.status == StatusEnum.new),
        'in_progress': sum(1 for r in reports if r.status == StatusEnum.in_progress)
    }
    
    return {
        'teams': team_stats,
        'reports': report_stats,
        'utilization': {
            'team_deployment_rate': (team_stats['deployed'] / team_stats['total_teams'] * 100) if team_stats['total_teams'] > 0 else 0,
            'report_assignment_rate': (report_stats['assigned'] / report_stats['total_active'] * 100) if report_stats['total_active'] > 0 else 0
        }
    }


def find_best_team_for_report(report: Report, db: Session) -> Optional[Dict]:
    """
    Find the single best team for a report based on:
    1. Proximity (distance)
    2. Availability
    3. Team capacity
    
    Args:
        report: Report needing assignment
        db: Database session
    
    Returns:
        Best team recommendation or None
    """
    all_teams = db.query(Team).all()
    recommendations = recommend_dispatch(report, all_teams)
    
    if not recommendations:
        return None
    
    # Return the closest available team
    return recommendations[0]
