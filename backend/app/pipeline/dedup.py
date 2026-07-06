"""
Deduplication pipeline for disaster reports.

Uses two signals to detect duplicates:
1. Geo-proximity: Reports within 300m of each other, same disaster type, within 6-hour window
2. Text similarity: Cosine similarity of TF-IDF vectors > 0.6 threshold

Duplicates are not discarded - they corroborate the original report,
increasing urgency and confidence through corroboration_count.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from math import radians, cos, sin, asin, sqrt
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from app.models import Report, StatusEnum, VerificationStatusEnum


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points 
    on the earth (specified in decimal degrees).
    
    Args:
        lat1, lon1: Latitude and longitude of point 1
        lat2, lon2: Latitude and longitude of point 2
    
    Returns:
        Distance in meters
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    
    return c * r


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Calculate cosine similarity between two texts using TF-IDF vectors.
    
    Args:
        text1: First text
        text2: Second text
    
    Returns:
        Similarity score between 0 and 1
    """
    if not text1 or not text2:
        return 0.0
    
    try:
        # Create TF-IDF vectorizer
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)  # Use unigrams and bigrams
        )
        
        # Fit and transform the texts
        tfidf_matrix = vectorizer.fit_transform([text1, text2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        
        return float(similarity)
    except Exception as e:
        # If vectorization fails (e.g., very short texts), return 0
        print(f"Text similarity calculation failed: {e}")
        return 0.0


def check_geo_proximity(
    report: Report, 
    candidate: Report, 
    distance_threshold: float = 300.0,
    time_window_hours: int = 6
) -> bool:
    """
    Check if two reports are geo-proximate duplicates.
    
    Criteria:
    - Within distance_threshold meters (default 300m)
    - Same disaster type
    - Within time_window_hours (default 6 hours)
    
    Args:
        report: The new report to check
        candidate: Existing report to compare against
        distance_threshold: Maximum distance in meters (default 300)
        time_window_hours: Maximum time difference in hours (default 6)
    
    Returns:
        True if reports are likely geo-proximate duplicates
    """
    # Both must have GPS coordinates
    if not all([report.latitude, report.longitude, 
                candidate.latitude, candidate.longitude]):
        return False
    
    # Must be same disaster type
    if report.disaster_type != candidate.disaster_type:
        return False
    
    # Check time window
    time_diff = abs((report.created_at - candidate.created_at).total_seconds() / 3600)
    if time_diff > time_window_hours:
        return False
    
    # Check distance
    distance = haversine_distance(
        report.latitude, report.longitude,
        candidate.latitude, candidate.longitude
    )
    
    return distance <= distance_threshold


def check_text_similarity(
    report: Report,
    candidate: Report,
    similarity_threshold: float = 0.6
) -> bool:
    """
    Check if two reports have similar text content.
    
    Uses TF-IDF cosine similarity on translated_text or raw_text.
    
    Args:
        report: The new report to check
        candidate: Existing report to compare against
        similarity_threshold: Minimum similarity score (default 0.6)
    
    Returns:
        True if texts are similar above threshold
    """
    # Get text to compare (prefer translated_text, fallback to raw_text)
    text1 = report.translated_text or report.raw_text
    text2 = candidate.translated_text or candidate.raw_text
    
    if not text1 or not text2:
        return False
    
    # Calculate similarity
    similarity = calculate_text_similarity(text1, text2)
    
    return similarity >= similarity_threshold


def merge_report_data(original: Report, duplicate: Report, db: Session) -> None:
    """
    Merge data from duplicate report into original report.
    
    - Increments corroboration_count
    - Adds num_people to original
    - Merges vulnerable_flags (unique values)
    - Updates verification status if corroborated
    - Increases urgency score based on corroboration
    
    Args:
        original: The original report to merge into
        duplicate: The duplicate report to merge from
        db: Database session
    """
    # Increment corroboration count
    original.corroboration_count += 1
    
    # Merge num_people
    if duplicate.num_people:
        if original.num_people:
            original.num_people += duplicate.num_people
        else:
            original.num_people = duplicate.num_people
    
    # Merge vulnerable_flags (keep unique values)
    if duplicate.vulnerable_flags:
        original_flags = set(original.vulnerable_flags or [])
        duplicate_flags = set(duplicate.vulnerable_flags)
        merged_flags = list(original_flags | duplicate_flags)
        original.vulnerable_flags = merged_flags
    
    # Update verification status to corroborated if multiple reports
    if original.corroboration_count >= 1 and \
       original.verification_status == VerificationStatusEnum.unverified:
        original.verification_status = VerificationStatusEnum.corroborated
    
    # Increase urgency score based on corroboration
    # Each corroboration adds 0.1 to urgency (capped at 1.0)
    urgency_boost = 0.1 * original.corroboration_count
    original.urgency_score = min(original.urgency_score + urgency_boost, 1.0)
    
    # Update timestamp
    original.updated_at = datetime.utcnow()
    
    db.add(original)
    db.commit()


def find_duplicates(
    report: Report,
    db: Session,
    geo_distance_threshold: float = 300.0,
    time_window_hours: int = 6,
    text_similarity_threshold: float = 0.6
) -> Optional[Report]:
    """
    Check if a new report is a duplicate of existing unresolved reports.
    
    Uses two signals:
    1. Geo-proximity: Within 300m, same disaster type, within 6-hour window
    2. Text similarity: Cosine similarity > 0.6
    
    If a duplicate is found:
    - Sets is_duplicate_of to the earliest matching report
    - Increments corroboration_count on the original
    - Merges num_people and vulnerable_flags
    - Increases urgency score
    - Updates verification status to corroborated
    
    Args:
        report: The new report to check for duplicates
        db: Database session
        geo_distance_threshold: Max distance in meters (default 300)
        time_window_hours: Max time difference in hours (default 6)
        text_similarity_threshold: Min text similarity (default 0.6)
    
    Returns:
        The original report if duplicate found, None otherwise
    """
    # Query unresolved reports (not resolved or false reports)
    # Also exclude reports that are themselves duplicates
    candidates = db.query(Report).filter(
        Report.id != report.id,  # Don't compare with self
        Report.is_duplicate_of.is_(None),  # Only compare with originals
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])  # Unresolved
    ).all()
    
    matches = []
    
    for candidate in candidates:
        geo_match = False
        text_match = False
        
        # Check geo-proximity
        if report.latitude and report.longitude:
            geo_match = check_geo_proximity(
                report, candidate,
                distance_threshold=geo_distance_threshold,
                time_window_hours=time_window_hours
            )
        
        # Check text similarity
        text_match = check_text_similarity(
            report, candidate,
            similarity_threshold=text_similarity_threshold
        )
        
        # If either signal triggers, consider it a match
        if geo_match or text_match:
            matches.append({
                'report': candidate,
                'geo_match': geo_match,
                'text_match': text_match,
                'created_at': candidate.created_at
            })
    
    # If matches found, use the earliest one as the original
    if matches:
        # Sort by creation time to get earliest report
        matches.sort(key=lambda x: x['created_at'])
        original_report = matches[0]['report']
        
        # Mark this report as duplicate
        report.is_duplicate_of = original_report.id
        
        # Merge data into original
        merge_report_data(original_report, report, db)
        
        # Save the duplicate report with is_duplicate_of set
        db.add(report)
        db.commit()
        
        return original_report
    
    return None


def get_duplicate_info(report: Report, db: Session) -> dict:
    """
    Get information about duplicates for a report.
    
    Args:
        report: The report to get duplicate info for
        db: Database session
    
    Returns:
        Dictionary with duplicate information
    """
    if report.is_duplicate_of:
        original = db.query(Report).filter(Report.id == report.is_duplicate_of).first()
        return {
            'is_duplicate': True,
            'original_report_id': original.id if original else None,
            'original_created_at': original.created_at if original else None
        }
    
    # Check if this report has duplicates
    duplicate_count = db.query(Report).filter(
        Report.is_duplicate_of == report.id
    ).count()
    
    return {
        'is_duplicate': False,
        'is_original': duplicate_count > 0,
        'corroboration_count': report.corroboration_count,
        'duplicate_count': duplicate_count
    }
