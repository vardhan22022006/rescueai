"""
Transparent urgency scoring system for disaster reports.

Uses a weighted formula with explicit breakdown for explainability.
Scores range from 0-100 with detailed contribution tracking.

Philosophy: Transparent scoring builds trust with response teams.
Every factor and its contribution is tracked and visible.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, Tuple
from sqlalchemy.orm import Session

from app.models import Report, DisasterTypeEnum, VerificationStatusEnum, StatusEnum


# Scoring constants - all tunable and transparent
SCORING_CONFIG = {
    # People affected scoring (log scale to prevent dominance)
    'people_base': 10,
    'people_log_multiplier': 8,
    'people_max_score': 30,
    
    # Vulnerable population scoring
    'vulnerable_per_flag': 15,
    'vulnerable_max_score': 45,
    
    # Verification status scoring
    'verification_scores': {
        VerificationStatusEnum.unverified: 0,
        VerificationStatusEnum.corroborated: 10,
        VerificationStatusEnum.weather_confirmed: 20,
        VerificationStatusEnum.satellite_confirmed: 25
    },
    
    # Corroboration scoring
    'corroboration_per_report': 5,
    'corroboration_max_score': 20,
    
    # Disaster type severity multipliers
    'disaster_multipliers': {
        DisasterTypeEnum.earthquake: 1.2,  # Less warning time
        DisasterTypeEnum.cyclone: 1.1,     # Moderate warning
        DisasterTypeEnum.flood: 1.0,       # More warning time
        DisasterTypeEnum.other: 1.0
    },
    
    # Time decay (urgency increases with delay)
    'time_decay_per_hour': 5,
    'time_decay_threshold_hours': 2,
    'time_decay_max_score': 20
}


def compute_people_score(num_people: int) -> Tuple[float, str]:
    """
    Calculate score based on number of people affected.
    
    Uses logarithmic scale to prevent single large number from dominating.
    Formula: base + log_multiplier * log10(num_people + 1)
    
    Args:
        num_people: Number of people affected
    
    Returns:
        Tuple of (score, explanation)
    """
    if not num_people or num_people <= 0:
        return 0.0, "No people count provided"
    
    base = SCORING_CONFIG['people_base']
    multiplier = SCORING_CONFIG['people_log_multiplier']
    max_score = SCORING_CONFIG['people_max_score']
    
    # Logarithmic scaling: log10(1) = 0, log10(10) = 1, log10(100) = 2
    score = base + multiplier * math.log10(num_people + 1)
    score = min(score, max_score)
    
    explanation = f"{num_people} people (log scale: {score:.1f}/30)"
    
    return score, explanation


def compute_vulnerable_score(vulnerable_flags: list) -> Tuple[float, str]:
    """
    Calculate score based on vulnerable population flags.
    
    Each flag type adds fixed points, capped at max.
    Flags: elderly, child, pregnant, disabled
    
    Args:
        vulnerable_flags: List of vulnerability indicators
    
    Returns:
        Tuple of (score, explanation)
    """
    if not vulnerable_flags:
        return 0.0, "No vulnerable populations identified"
    
    per_flag = SCORING_CONFIG['vulnerable_per_flag']
    max_score = SCORING_CONFIG['vulnerable_max_score']
    
    # Count unique flags
    unique_flags = list(set(vulnerable_flags))
    num_flags = len(unique_flags)
    
    score = min(num_flags * per_flag, max_score)
    
    explanation = f"{num_flags} vulnerable group(s): {', '.join(unique_flags)} (+{score})"
    
    return score, explanation


def compute_verification_score(verification_status: VerificationStatusEnum) -> Tuple[float, str]:
    """
    Calculate score based on verification status.
    
    Higher verification = higher confidence = higher urgency
    
    Args:
        verification_status: Verification status enum
    
    Returns:
        Tuple of (score, explanation)
    """
    score = SCORING_CONFIG['verification_scores'].get(verification_status, 0)
    
    status_names = {
        VerificationStatusEnum.unverified: "Unverified",
        VerificationStatusEnum.corroborated: "Corroborated by multiple reports",
        VerificationStatusEnum.weather_confirmed: "Weather data confirms",
        VerificationStatusEnum.satellite_confirmed: "Satellite data confirms"
    }
    
    explanation = f"{status_names.get(verification_status, 'Unknown')} (+{score})"
    
    return score, explanation


def compute_corroboration_score(corroboration_count: int) -> Tuple[float, str]:
    """
    Calculate score based on number of corroborating reports.
    
    More independent reports = higher confidence
    
    Args:
        corroboration_count: Number of duplicate reports
    
    Returns:
        Tuple of (score, explanation)
    """
    if corroboration_count <= 0:
        return 0.0, "Single report, no corroboration"
    
    per_report = SCORING_CONFIG['corroboration_per_report']
    max_score = SCORING_CONFIG['corroboration_max_score']
    
    score = min(corroboration_count * per_report, max_score)
    
    explanation = f"{corroboration_count} corroborating report(s) (+{score})"
    
    return score, explanation


def compute_disaster_multiplier(disaster_type: DisasterTypeEnum) -> Tuple[float, str]:
    """
    Get severity multiplier for disaster type.
    
    Earthquakes have less warning time, hence higher urgency.
    
    Args:
        disaster_type: Type of disaster
    
    Returns:
        Tuple of (multiplier, explanation)
    """
    multiplier = SCORING_CONFIG['disaster_multipliers'].get(disaster_type, 1.0)
    
    explanations = {
        DisasterTypeEnum.earthquake: "Earthquake: Minimal warning time (×1.2)",
        DisasterTypeEnum.cyclone: "Cyclone: Limited warning time (×1.1)",
        DisasterTypeEnum.flood: "Flood: More warning time (×1.0)",
        DisasterTypeEnum.other: "Other disaster type (×1.0)"
    }
    
    explanation = explanations.get(disaster_type, f"{disaster_type.value} (×{multiplier})")
    
    return multiplier, explanation


def compute_time_decay_score(created_at: datetime, updated_at: datetime) -> Tuple[float, str]:
    """
    Calculate urgency boost based on time since last update.
    
    Reports that have been waiting longer need more urgent attention.
    Delayed help compounds risk.
    
    Args:
        created_at: When report was created
        updated_at: When report was last updated
    
    Returns:
        Tuple of (score, explanation)
    """
    now = datetime.utcnow()
    
    # Use the more recent of created_at or updated_at
    reference_time = max(created_at, updated_at)
    
    hours_stale = (now - reference_time).total_seconds() / 3600
    threshold = SCORING_CONFIG['time_decay_threshold_hours']
    
    if hours_stale < threshold:
        return 0.0, f"Recent report ({hours_stale:.1f}h old, no decay)"
    
    # Calculate decay score
    hours_over_threshold = hours_stale - threshold
    per_hour = SCORING_CONFIG['time_decay_per_hour']
    max_score = SCORING_CONFIG['time_decay_max_score']
    
    score = min(hours_over_threshold * per_hour, max_score)
    
    explanation = f"Report {hours_stale:.1f}h old, no update for {hours_over_threshold:.1f}h (+{score:.0f})"
    
    return score, explanation


def compute_urgency_score(report: Report) -> Tuple[float, Dict]:
    """
    Calculate comprehensive urgency score for a disaster report.
    
    Returns score (0-100) with detailed breakdown of all contributing factors.
    This transparency is crucial for trust and explainability to judges/stakeholders.
    
    Scoring Formula:
    1. Base factors (additive, 0-100 range before multiplier):
       - People affected: 0-30 points (log scale)
       - Vulnerable populations: 0-45 points (15 per flag type, max 3)
       - Verification status: 0-25 points
       - Corroboration: 0-20 points (5 per report, max 4)
       - Time decay: 0-20 points (delayed help compounds risk)
    
    2. Disaster type multiplier (1.0-1.2x):
       - Applied to base score to reflect warning time differences
    
    3. Final capping at 100
    
    Args:
        report: Report object to score
    
    Returns:
        Tuple of (final_score, breakdown_dict)
        
    Example breakdown:
    {
        'final_score': 78.5,
        'base_score': 65.0,
        'factors': {
            'people': {'score': 18.5, 'explanation': '...'},
            'vulnerable': {'score': 30.0, 'explanation': '...'},
            'verification': {'score': 25.0, 'explanation': '...'},
            'corroboration': {'score': 10.0, 'explanation': '...'},
            'time_decay': {'score': 15.0, 'explanation': '...'}
        },
        'multiplier': {'value': 1.2, 'explanation': '...'},
        'timestamp': '2026-07-06T12:34:56Z'
    }
    """
    # Initialize breakdown
    breakdown = {
        'factors': {},
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    # Factor 1: People affected
    people_score, people_exp = compute_people_score(report.num_people)
    breakdown['factors']['people'] = {
        'score': round(people_score, 1),
        'explanation': people_exp
    }
    
    # Factor 2: Vulnerable populations
    vulnerable_score, vulnerable_exp = compute_vulnerable_score(report.vulnerable_flags)
    breakdown['factors']['vulnerable'] = {
        'score': round(vulnerable_score, 1),
        'explanation': vulnerable_exp
    }
    
    # Factor 3: Verification status
    verification_score, verification_exp = compute_verification_score(report.verification_status)
    breakdown['factors']['verification'] = {
        'score': round(verification_score, 1),
        'explanation': verification_exp
    }
    
    # Factor 4: Corroboration count
    corroboration_score, corroboration_exp = compute_corroboration_score(report.corroboration_count)
    breakdown['factors']['corroboration'] = {
        'score': round(corroboration_score, 1),
        'explanation': corroboration_exp
    }
    
    # Factor 5: Time decay
    time_decay_score, time_decay_exp = compute_time_decay_score(
        report.created_at,
        report.updated_at
    )
    breakdown['factors']['time_decay'] = {
        'score': round(time_decay_score, 1),
        'explanation': time_decay_exp
    }
    
    # Calculate base score (sum of all factors)
    base_score = (
        people_score +
        vulnerable_score +
        verification_score +
        corroboration_score +
        time_decay_score
    )
    
    breakdown['base_score'] = round(base_score, 1)
    
    # Apply disaster type multiplier
    multiplier, multiplier_exp = compute_disaster_multiplier(report.disaster_type)
    breakdown['multiplier'] = {
        'value': multiplier,
        'explanation': multiplier_exp
    }
    
    # Calculate final score
    final_score = base_score * multiplier
    final_score = min(final_score, 100.0)  # Cap at 100
    
    breakdown['final_score'] = round(final_score, 1)
    
    # Add summary explanation
    breakdown['summary'] = generate_summary_explanation(breakdown)
    
    return final_score, breakdown


def generate_summary_explanation(breakdown: Dict) -> str:
    """
    Generate human-readable summary of why report has its urgency score.
    
    Args:
        breakdown: Breakdown dictionary from compute_urgency_score
    
    Returns:
        Summary string
    """
    score = breakdown['final_score']
    factors = breakdown['factors']
    
    # Determine primary drivers (factors contributing >20% of base score)
    base = breakdown['base_score']
    if base == 0:
        return "No urgency factors present"
    
    drivers = []
    for factor_name, factor_data in factors.items():
        if factor_data['score'] > 0 and (factor_data['score'] / base) >= 0.2:
            drivers.append(factor_name)
    
    if not drivers:
        drivers = [max(factors.items(), key=lambda x: x[1]['score'])[0]]
    
    # Format driver names
    driver_names = {
        'people': 'number of people affected',
        'vulnerable': 'vulnerable populations',
        'verification': 'external verification',
        'corroboration': 'multiple corroborating reports',
        'time_decay': 'time waiting without update'
    }
    
    driver_list = [driver_names.get(d, d) for d in drivers]
    
    if len(driver_list) == 1:
        primary = driver_list[0]
    elif len(driver_list) == 2:
        primary = f"{driver_list[0]} and {driver_list[1]}"
    else:
        primary = f"{', '.join(driver_list[:-1])}, and {driver_list[-1]}"
    
    # Urgency level
    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"
    
    return f"{level} urgency ({score:.0f}/100) driven primarily by {primary}"


def update_report_urgency(report: Report, db: Session) -> Dict:
    """
    Update urgency score and breakdown for a report.
    
    Calculates new score, stores it on the report, and commits to database.
    
    Args:
        report: Report to update
        db: Database session
    
    Returns:
        Breakdown dictionary
    """
    old_score = report.urgency_score
    
    # Compute new score
    new_score, breakdown = compute_urgency_score(report)
    
    # Update report
    report.urgency_score = new_score
    report.urgency_breakdown = breakdown
    report.updated_at = datetime.utcnow()
    
    db.add(report)
    db.commit()
    
    # Add change info to breakdown
    breakdown['score_change'] = {
        'old_score': round(old_score, 1),
        'new_score': round(new_score, 1),
        'change': round(new_score - old_score, 1)
    }
    
    return breakdown


def rescore_all_active_reports(db: Session) -> Dict:
    """
    Re-score all active (unresolved) reports.
    
    Useful for:
    - Applying time decay to aging reports
    - Updating scores after system-wide config changes
    - Periodic maintenance (run every 5 minutes)
    
    Args:
        db: Database session
    
    Returns:
        Summary of rescoring operation
    """
    # Get all active reports
    active_reports = db.query(Report).filter(
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).all()
    
    results = {
        'total_rescored': 0,
        'scores_increased': 0,
        'scores_decreased': 0,
        'scores_unchanged': 0,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'details': []
    }
    
    for report in active_reports:
        old_score = report.urgency_score
        breakdown = update_report_urgency(report, db)
        new_score = breakdown['final_score']
        
        results['total_rescored'] += 1
        
        if new_score > old_score:
            results['scores_increased'] += 1
        elif new_score < old_score:
            results['scores_decreased'] += 1
        else:
            results['scores_unchanged'] += 1
        
        # Track significant changes
        if abs(new_score - old_score) >= 5:
            results['details'].append({
                'report_id': report.id,
                'old_score': old_score,
                'new_score': new_score,
                'change': new_score - old_score,
                'summary': breakdown['summary']
            })
    
    return results


def get_urgency_explanation(report: Report) -> Dict:
    """
    Get human-readable explanation of a report's urgency score.
    
    Returns the stored breakdown or computes fresh if not available.
    
    Args:
        report: Report to explain
    
    Returns:
        Breakdown dictionary with explanations
    """
    if report.urgency_breakdown:
        return report.urgency_breakdown
    else:
        # Compute fresh breakdown
        _, breakdown = compute_urgency_score(report)
        return breakdown


def get_scoring_config() -> Dict:
    """
    Get the current scoring configuration.
    
    Useful for dashboard display and documentation.
    
    Returns:
        Copy of SCORING_CONFIG
    """
    return SCORING_CONFIG.copy()
