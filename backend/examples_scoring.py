"""
Usage examples for the urgency scoring system.
Shows integration patterns and dashboard display.
"""

from app.database import SessionLocal
from app.models import Report
from app.pipeline.scoring import (
    compute_urgency_score,
    update_report_urgency,
    get_urgency_explanation,
    get_scoring_config
)
import json


def example_1_score_on_creation():
    """
    Example 1: Score a report when it's created.
    """
    print("\n=== Example 1: Score on Report Creation ===\n")
    
    print("""
from app.pipeline.scoring import update_report_urgency

@app.post("/api/reports")
async def create_report(report_data: ReportCreate, db: Session = Depends(get_db)):
    # Create report
    new_report = Report(**report_data.dict())
    db.add(new_report)
    db.commit()
    db.refresh(new_report)
    
    # Calculate urgency score
    breakdown = update_report_urgency(new_report, db)
    
    return {
        "report_id": new_report.id,
        "urgency_score": breakdown['final_score'],
        "urgency_level": "CRITICAL" if breakdown['final_score'] >= 80 else
                         "HIGH" if breakdown['final_score'] >= 60 else
                         "MEDIUM" if breakdown['final_score'] >= 40 else "LOW",
        "breakdown": breakdown
    }
    """)


def example_2_rescore_on_update():
    """
    Example 2: Re-score when report is updated.
    """
    print("\n=== Example 2: Re-score on Update ===\n")
    
    print("""
from app.pipeline.scoring import update_report_urgency
from app.pipeline.verify import verify_report

@app.patch("/api/reports/{report_id}")
async def update_report(
    report_id: str,
    updates: ReportUpdate,
    db: Session = Depends(get_db)
):
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404)
    
    # Apply updates
    for field, value in updates.dict(exclude_unset=True).items():
        setattr(report, field, value)
    
    # Re-verify if location or disaster type changed
    if 'latitude' in updates.dict() or 'disaster_type' in updates.dict():
        verify_report(report, db)
    
    # Re-score (verification may have changed factors)
    breakdown = update_report_urgency(report, db)
    
    return {
        "report_id": report.id,
        "urgency_score": breakdown['final_score'],
        "score_change": breakdown['score_change'],
        "summary": breakdown['summary']
    }
    """)


def example_3_dashboard_display():
    """
    Example 3: Display urgency breakdown in dashboard.
    """
    print("\n=== Example 3: Dashboard Display ===\n")
    
    print("""
# React Component Example

function UrgencyBreakdown({ report }) {
  const breakdown = report.urgency_breakdown;
  
  // Urgency level color
  const getScoreColor = (score) => {
    if (score >= 80) return 'text-red-600';
    if (score >= 60) return 'text-orange-600';
    if (score >= 40) return 'text-yellow-600';
    return 'text-blue-600';
  };
  
  return (
    <div className="urgency-breakdown">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Urgency Score</h3>
        <div className={`text-3xl font-bold ${getScoreColor(breakdown.final_score)}`}>
          {breakdown.final_score}/100
        </div>
      </div>
      
      <p className="text-sm text-gray-600 mb-4">
        {breakdown.summary}
      </p>
      
      <div className="space-y-2">
        <h4 className="font-medium">Contributing Factors:</h4>
        
        {Object.entries(breakdown.factors).map(([name, data]) => (
          data.score > 0 && (
            <div key={name} className="flex items-center justify-between p-2 bg-gray-50 rounded">
              <div>
                <div className="font-medium capitalize">{name}</div>
                <div className="text-xs text-gray-600">{data.explanation}</div>
              </div>
              <div className="text-lg font-semibold">+{data.score}</div>
            </div>
          )
        ))}
        
        <div className="flex items-center justify-between p-2 bg-blue-50 rounded border-t-2 border-blue-200">
          <div className="font-medium">Base Score</div>
          <div className="text-lg font-semibold">{breakdown.base_score}</div>
        </div>
        
        <div className="flex items-center justify-between p-2 bg-purple-50 rounded">
          <div>
            <div className="font-medium">Disaster Type Multiplier</div>
            <div className="text-xs text-gray-600">{breakdown.multiplier.explanation}</div>
          </div>
          <div className="text-lg font-semibold">×{breakdown.multiplier.value}</div>
        </div>
        
        <div className="flex items-center justify-between p-3 bg-indigo-100 rounded border-2 border-indigo-400">
          <div className="font-bold">Final Score</div>
          <div className={`text-2xl font-bold ${getScoreColor(breakdown.final_score)}`}>
            {breakdown.final_score}
          </div>
        </div>
      </div>
      
      <div className="mt-4 text-xs text-gray-500">
        Last updated: {new Date(breakdown.timestamp).toLocaleString()}
      </div>
    </div>
  );
}
    """)


def example_4_api_endpoint_breakdown():
    """
    Example 4: API endpoint to get urgency explanation.
    """
    print("\n=== Example 4: Urgency Explanation API ===\n")
    
    print("""
from app.pipeline.scoring import get_urgency_explanation

@app.get("/api/reports/{report_id}/urgency")
async def get_report_urgency(report_id: str, db: Session = Depends(get_db)):
    '''
    Get detailed urgency breakdown for a report.
    Useful for:
    - Dashboard tooltips
    - Detailed report view
    - Explaining priorities to stakeholders
    '''
    report = db.query(Report).filter(Report.id == report_id).first()
    
    if not report:
        raise HTTPException(status_code=404)
    
    breakdown = get_urgency_explanation(report)
    
    return {
        "report_id": report.id,
        "urgency_score": breakdown['final_score'],
        "summary": breakdown['summary'],
        "breakdown": breakdown,
        "visual_data": {
            "level": "CRITICAL" if breakdown['final_score'] >= 80 else
                     "HIGH" if breakdown['final_score'] >= 60 else
                     "MEDIUM" if breakdown['final_score'] >= 40 else "LOW",
            "color": "#DC2626" if breakdown['final_score'] >= 80 else
                     "#EA580C" if breakdown['final_score'] >= 60 else
                     "#CA8A04" if breakdown['final_score'] >= 40 else "#2563EB",
            "percentage": breakdown['final_score']
        }
    }
    """)


def example_5_sorted_by_urgency():
    """
    Example 5: Query reports sorted by urgency.
    """
    print("\n=== Example 5: Priority Queue (Sorted by Urgency) ===\n")
    
    print("""
@app.get("/api/reports/priority-queue")
async def get_priority_queue(
    limit: int = 20,
    min_score: float = 0,
    db: Session = Depends(get_db)
):
    '''
    Get reports in priority order (highest urgency first).
    Perfect for response team dashboard.
    '''
    reports = db.query(Report).filter(
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress]),
        Report.urgency_score >= min_score
    ).order_by(
        Report.urgency_score.desc()
    ).limit(limit).all()
    
    return {
        "priority_queue": [
            {
                "id": r.id,
                "urgency_score": r.urgency_score,
                "summary": r.urgency_breakdown.get('summary', ''),
                "disaster_type": r.disaster_type.value,
                "num_people": r.num_people,
                "location": {
                    "lat": r.latitude,
                    "lon": r.longitude,
                    "text": r.location_text
                },
                "created_at": r.created_at.isoformat(),
                "age_hours": (datetime.utcnow() - r.updated_at).total_seconds() / 3600
            }
            for r in reports
        ],
        "total_count": len(reports),
        "highest_score": reports[0].urgency_score if reports else 0
    }
    """)


def example_6_scoring_config_api():
    """
    Example 6: Expose scoring configuration for transparency.
    """
    print("\n=== Example 6: Scoring Configuration API ===\n")
    
    print("""
from app.pipeline.scoring import get_scoring_config

@app.get("/api/scoring/config")
async def get_scoring_configuration():
    '''
    Get the current scoring configuration.
    
    Perfect for:
    - Documentation pages
    - Judge presentations
    - Transparency dashboards
    - Explaining "why" to stakeholders
    '''
    config = get_scoring_config()
    
    return {
        "scoring_config": config,
        "description": {
            "people_scoring": "Logarithmic scale to prevent single large number from dominating",
            "vulnerable_scoring": "15 points per vulnerable group type (elderly, child, pregnant, disabled)",
            "verification_scoring": "Higher verification = higher confidence = higher priority",
            "corroboration_scoring": "5 points per additional independent report",
            "disaster_multipliers": "Earthquakes have less warning time (×1.2 multiplier)",
            "time_decay": "Reports waiting longer get urgency boost (delayed help = compounded risk)"
        },
        "philosophy": "Transparent, explainable scoring builds trust with response teams"
    }
    """)


def example_7_judge_presentation():
    """
    Example 7: Generate judge-friendly explanation.
    """
    print("\n=== Example 7: Judge Presentation Format ===\n")
    
    print("""
def generate_judge_explanation(report: Report) -> dict:
    '''
    Generate a judge-friendly explanation of urgency scoring.
    
    Perfect for:
    - Hackathon presentations
    - Stakeholder demos
    - Transparency documentation
    '''
    breakdown = get_urgency_explanation(report)
    
    # Simple, non-technical summary
    summary = {
        "urgency_level": (
            "🔴 CRITICAL" if breakdown['final_score'] >= 80 else
            "🟠 HIGH" if breakdown['final_score'] >= 60 else
            "🟡 MEDIUM" if breakdown['final_score'] >= 40 else
            "🔵 LOW"
        ),
        "score": f"{breakdown['final_score']}/100",
        "plain_english": breakdown['summary'],
        
        "why_this_score": []
    }
    
    # Extract key factors in plain language
    for factor, data in breakdown['factors'].items():
        if data['score'] > 0:
            summary['why_this_score'].append({
                "factor": factor.replace('_', ' ').title(),
                "contribution": f"+{data['score']} points",
                "reason": data['explanation']
            })
    
    # Add disaster context
    summary['disaster_context'] = breakdown['multiplier']['explanation']
    
    # Transparency note
    summary['transparency_note'] = (
        "This score is calculated using a transparent, weighted formula. "
        "Every factor and its contribution is visible to response teams. "
        "This builds trust and allows teams to understand priorities."
    )
    
    return summary

# Example output:
{
  "urgency_level": "🔴 CRITICAL",
  "score": "87.6/100",
  "plain_english": "CRITICAL urgency (88/100) driven primarily by number of people affected and vulnerable populations",
  "why_this_score": [
    {
      "factor": "People",
      "contribution": "+25.4 points",
      "reason": "150 people (log scale: 25.4/30)"
    },
    {
      "factor": "Vulnerable",
      "contribution": "+45.0 points",
      "reason": "3 vulnerable group(s): elderly, child, pregnant (+45)"
    },
    {
      "factor": "Verification",
      "contribution": "+25.0 points",
      "reason": "Satellite data confirms (+25)"
    }
  ],
  "disaster_context": "Earthquake: Minimal warning time (×1.2)",
  "transparency_note": "This score is calculated using a transparent..."
}
    """)


if __name__ == "__main__":
    print("=" * 70)
    print("RescueAI Urgency Scoring - Usage Examples")
    print("=" * 70)
    
    example_1_score_on_creation()
    example_2_rescore_on_update()
    example_3_dashboard_display()
    example_4_api_endpoint_breakdown()
    example_5_sorted_by_urgency()
    example_6_scoring_config_api()
    example_7_judge_presentation()
    
    print("\n" + "=" * 70)
    print("Key Takeaways for Judges:")
    print("=" * 70)
    print()
    print("✓ TRANSPARENT: Every factor and contribution is visible")
    print("✓ EXPLAINABLE: Non-technical stakeholders can understand")
    print("✓ FAIR: Log-scale prevents single factor dominance")
    print("✓ PRACTICAL: Time decay reflects real-world urgency")
    print("✓ TRUSTWORTHY: Teams can see WHY priorities are set")
    print()
    print("=" * 70)
