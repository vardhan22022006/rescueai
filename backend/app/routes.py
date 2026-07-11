"""
API routes for RescueAI.

Endpoints for:
- Report intake  (JSON + Twilio SMS/WhatsApp webhook)
- Report management
- Team dispatch
- Urgency recommendations
"""

import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import (
    Report, Team,
    SourceEnum, StatusEnum, VerificationStatusEnum, TeamStatusEnum,
)
from app.pipeline.dispatch import (
    recommend_dispatch,
    assign_team_to_report,
    get_dispatch_summary,
    get_team_workload,
)
from app.pipeline.scoring import get_urgency_explanation

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== Shared intake helpers ====================

class IntakePayload(BaseModel):
    source: SourceEnum
    raw_text: str = Field(..., min_length=1)
    reporter_phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    location_text: Optional[str] = None


def _run_pipeline(report_id: str) -> None:
    """
    Dedup → verify → score pipeline executed as a BackgroundTask.

    Each stage is wrapped individually so a failure in one never kills
    the rest.  Import errors emit a warning stub so the endpoint works
    even before Member A's modules are merged.
    """
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            logger.error("Pipeline: report %s not found", report_id)
            return

        # Stage 1 — deduplication
        try:
            from app.pipeline.dedup import find_duplicates
            find_duplicates(report, db)
        except ImportError:
            logger.warning("Pipeline[dedup]: module not available, skipping")  # TODO: remove stub after merge
        except Exception as exc:
            logger.exception("Pipeline[dedup] error for %s: %s", report_id, exc)

        # Stage 2 — external verification
        try:
            from app.pipeline.verify import verify_report
            verify_report(report, db)
        except ImportError:
            logger.warning("Pipeline[verify]: module not available, skipping")  # TODO: remove stub after merge
        except Exception as exc:
            logger.exception("Pipeline[verify] error for %s: %s", report_id, exc)

        # Stage 3 — urgency scoring
        try:
            from app.pipeline.scoring import update_report_urgency
            update_report_urgency(report, db)
        except ImportError:
            logger.warning("Pipeline[scoring]: module not available, skipping")  # TODO: remove stub after merge
        except Exception as exc:
            logger.exception("Pipeline[scoring] error for %s: %s", report_id, exc)

    finally:
        db.close()


def _intake(payload: IntakePayload, background_tasks: BackgroundTasks, db: Session) -> dict:
    """
    Core intake logic shared by the JSON endpoint and the Twilio webhook.

    1. Detect language of raw_text.
    2. Translate to English if needed.
    3. Extract disaster_type / num_people / vulnerable_flags via rule-based NLP.
    4. Persist report (status=new, verification_status=unverified).
    5. Enqueue background pipeline.

    Returns {"report_id": "<uuid>"}.
    """
    # ── Step 1: Language detection ────────────────────────────────────────
    try:
        from langdetect import detect, LangDetectException
        try:
            detected_lang = detect(payload.raw_text)
        except LangDetectException:
            detected_lang = "en"
    except ImportError:
        logger.warning("langdetect not installed — defaulting to 'en'")
        detected_lang = "en"

    # ── Step 2: Translation ───────────────────────────────────────────────
    if detected_lang != "en":
        from app.translation import translate_text
        translated_text: Optional[str] = translate_text(payload.raw_text, detected_lang)
    else:
        translated_text = None  # no translation needed

    # ── Step 3: NLP extraction ────────────────────────────────────────────
    from app.nlp_extraction import extract_report_fields
    extracted = extract_report_fields(translated_text or payload.raw_text)

    # ── Step 4: Persist ───────────────────────────────────────────────────
    now = datetime.utcnow()
    report = Report(
        source=payload.source,
        raw_text=payload.raw_text,
        language=detected_lang,
        translated_text=translated_text,
        reporter_phone=payload.reporter_phone,
        latitude=payload.latitude,
        longitude=payload.longitude,
        location_text=payload.location_text,
        disaster_type=extracted["disaster_type"],
        num_people=extracted["num_people"],
        vulnerable_flags=extracted["vulnerable_flags"],
        status=StatusEnum.new,
        verification_status=VerificationStatusEnum.unverified,
        created_at=now,
        updated_at=now,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # ── Step 5: Background pipeline ───────────────────────────────────────
    background_tasks.add_task(_run_pipeline, report.id)

    return {"report_id": report.id}


# ==================== Intake Endpoints ====================

@router.post("/reports/intake", status_code=201)
async def intake_report(
    payload: IntakePayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Accept a disaster report as JSON from any channel.

    Returns {"report_id": "<uuid>"} immediately; processing pipeline runs
    in the background (dedup → verify → score).
    """
    return _intake(payload, background_tasks, db)


@router.post("/reports/twilio-webhook", status_code=200)
async def twilio_webhook(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    From: str = Form(...),
    Body: str = Form(...),
):
    """
    Receive an inbound SMS or WhatsApp message from Twilio.

    Twilio POSTs application/x-www-form-urlencoded with at minimum:
      From  — sender address, e.g. "+919876543210" or "whatsapp:+919876543210"
      Body  — message text

    Source is inferred from the From prefix:
      "whatsapp:..." → source=whatsapp
      anything else  → source=sms

    The message is forwarded into the same intake pipeline as the JSON
    endpoint, then a valid empty TwiML response is returned so Twilio
    does not raise a webhook error.
    """
    is_whatsapp = From.lower().startswith("whatsapp:")
    source = SourceEnum.whatsapp if is_whatsapp else SourceEnum.sms
    # Strip the "whatsapp:" scheme so we store a plain E.164 phone number
    reporter_phone = From[len("whatsapp:"):] if is_whatsapp else From

    payload = IntakePayload(
        source=source,
        raw_text=Body,
        reporter_phone=reporter_phone,
    )

    _intake(payload, background_tasks, db)

    # Twilio requires a well-formed TwiML response; an empty <Response> is valid
    # and suppresses any default reply to the sender.
    twiml = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'
    return Response(content=twiml, media_type="application/xml")


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


# ==================== Stats & Dashboard Endpoints ====================

@router.get("/stats/summary")
async def stats_summary(db: Session = Depends(get_db)):
    """
    Aggregate statistics for the dashboard header stat cards.

    Returns counts by disaster type, verification status, report status,
    plus totals for active/critical reports and team availability.
    Polled every 15 s by the frontend.
    """
    from sqlalchemy import func
    from app.models import DisasterTypeEnum, VerificationStatusEnum

    # ── report counts ────────────────────────────────────────────────────
    total_reports   = db.query(Report).count()
    active_reports  = db.query(Report).filter(
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).count()
    critical_reports = db.query(Report).filter(
        Report.urgency_score >= 80,
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).count()
    unverified_reports = db.query(Report).filter(
        Report.verification_status == VerificationStatusEnum.unverified,
        Report.status.in_([StatusEnum.new, StatusEnum.in_progress])
    ).count()

    # ── by disaster type (active only) ───────────────────────────────────
    by_type_rows = (
        db.query(Report.disaster_type, func.count(Report.id))
        .filter(Report.status.in_([StatusEnum.new, StatusEnum.in_progress]))
        .group_by(Report.disaster_type)
        .all()
    )
    by_type = {row[0].value: row[1] for row in by_type_rows}

    # ── by verification status (active only) ─────────────────────────────
    by_verification_rows = (
        db.query(Report.verification_status, func.count(Report.id))
        .filter(Report.status.in_([StatusEnum.new, StatusEnum.in_progress]))
        .group_by(Report.verification_status)
        .all()
    )
    by_verification = {row[0].value: row[1] for row in by_verification_rows}

    # ── team counts ──────────────────────────────────────────────────────
    total_teams     = db.query(Team).count()
    available_teams = db.query(Team).filter(Team.status == TeamStatusEnum.available).count()
    deployed_teams  = db.query(Team).filter(Team.status == TeamStatusEnum.deployed).count()

    return {
        "reports": {
            "total":      total_reports,
            "active":     active_reports,
            "critical":   critical_reports,
            "unverified": unverified_reports,
            "by_type":    by_type,
            "by_verification": by_verification,
        },
        "teams": {
            "total":     total_teams,
            "available": available_teams,
            "deployed":  deployed_teams,
        },
    }


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


# ==================== Demo Endpoints ====================

# Realistic burst scenario: 15 reports spread across 3 disaster types,
# with mixed verification statuses, some duplicates, some vulnerable flags.
# Staggered across the Eastern India / Bay of Bengal region so they
# land on the map visibly spread out.
_BURST_TEMPLATES = [
    # --- High urgency floods ---
    dict(
        source=SourceEnum.sms,
        raw_text="Flood near Jalpaiguri bridge. 35 people stranded including elderly woman. Water still rising.",
        latitude=26.5159, longitude=88.7180, location_text="Jalpaiguri Bridge, WB",
        verification_status=VerificationStatusEnum.weather_confirmed,
        urgency_score=91.0, num_people=35, vulnerable_flags=["elderly"],
        corroboration_count=3,
    ),
    dict(
        source=SourceEnum.whatsapp,
        raw_text="Same Jalpaiguri bridge area flooded. Confirming previous report. Old people need help.",
        latitude=26.5160, longitude=88.7182, location_text="Jalpaiguri Bridge area",
        verification_status=VerificationStatusEnum.corroborated,
        urgency_score=62.0, num_people=10, vulnerable_flags=["elderly"],
        corroboration_count=0,
    ),
    dict(
        source=SourceEnum.app,
        raw_text="Cyclone making landfall near Digha coast. 200 residents evacuating. Pregnant woman needs ambulance urgently.",
        latitude=21.6267, longitude=87.5388, location_text="Digha Coast, WB",
        verification_status=VerificationStatusEnum.satellite_confirmed,
        urgency_score=84.0, num_people=200, vulnerable_flags=["pregnant"],
        corroboration_count=5,
    ),
    dict(
        source=SourceEnum.voice,
        raw_text="Earthquake tremors in Sikkim. Buildings cracked. Family of 6 trapped, baby inside.",
        latitude=27.3389, longitude=88.6065, location_text="Gangtok, Sikkim",
        verification_status=VerificationStatusEnum.satellite_confirmed,
        urgency_score=87.0, num_people=6, vulnerable_flags=["child"],
        corroboration_count=1,
    ),
    # --- Medium urgency ---
    dict(
        source=SourceEnum.sms,
        raw_text="River embankment breach in Malda. Water entering homes. 8 people including 2 children.",
        latitude=25.0108, longitude=88.1415, location_text="Malda, WB",
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=58.0, num_people=8, vulnerable_flags=["child"],
        corroboration_count=0,
    ),
    dict(
        source=SourceEnum.whatsapp,
        raw_text="Flooding in low-lying areas near Kaziranga. 12 families displaced. Wheelchair user cannot move.",
        latitude=26.5775, longitude=93.1721, location_text="Kaziranga, Assam",
        verification_status=VerificationStatusEnum.corroborated,
        urgency_score=72.0, num_people=48, vulnerable_flags=["elderly", "disabled"],
        corroboration_count=2,
    ),
    dict(
        source=SourceEnum.app,
        raw_text="Flood damage in Barpeta district. 25 villagers need food and shelter. No injuries reported.",
        latitude=26.3232, longitude=91.0027, location_text="Barpeta, Assam",
        verification_status=VerificationStatusEnum.weather_confirmed,
        urgency_score=55.0, num_people=25, vulnerable_flags=[],
        corroboration_count=1,
    ),
    dict(
        source=SourceEnum.sms,
        raw_text="Cyclone damaged houses in Paradip. 40 families homeless. Children and elderly present.",
        latitude=20.3164, longitude=86.6111, location_text="Paradip, Odisha",
        verification_status=VerificationStatusEnum.corroborated,
        urgency_score=76.0, num_people=160, vulnerable_flags=["child", "elderly"],
        corroboration_count=2,
    ),
    # --- New unverified reports flooding in ---
    dict(
        source=SourceEnum.voice,
        raw_text="Flash flood warning in Cooch Behar. Water rising fast near the market area.",
        latitude=26.3452, longitude=89.4458, location_text="Cooch Behar market, WB",
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=43.0, num_people=None, vulnerable_flags=[],
        corroboration_count=0,
    ),
    dict(
        source=SourceEnum.sms,
        raw_text="Bridge collapsed in Dhubri. People stranded on both sides. Around 30 people.",
        latitude=26.0210, longitude=89.9762, location_text="Dhubri Bridge, Assam",
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=66.0, num_people=30, vulnerable_flags=[],
        corroboration_count=0,
    ),
    dict(
        source=SourceEnum.whatsapp,
        raw_text="Minor earthquake tremors in Darjeeling. No major damage visible. Reporting for awareness.",
        latitude=27.0974, longitude=88.2663, location_text="Darjeeling, WB",
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=12.0, num_people=None, vulnerable_flags=[],
        corroboration_count=0,
    ),
    dict(
        source=SourceEnum.app,
        raw_text="Flood situation in Murshidabad. Three villages cut off. Approx 150 people, including pregnant women.",
        latitude=24.1794, longitude=88.2686, location_text="Murshidabad, WB",
        verification_status=VerificationStatusEnum.satellite_confirmed,
        urgency_score=79.0, num_people=150, vulnerable_flags=["pregnant"],
        corroboration_count=3,
    ),
    dict(
        source=SourceEnum.sms,
        raw_text="Cyclone aftermath in Balasore. Roofs blown off. 60 families need shelter. Some elderly cannot walk.",
        latitude=21.4934, longitude=86.9398, location_text="Balasore, Odisha",
        verification_status=VerificationStatusEnum.weather_confirmed,
        urgency_score=69.0, num_people=240, vulnerable_flags=["elderly"],
        corroboration_count=1,
    ),
    dict(
        source=SourceEnum.voice,
        raw_text="Heavy flooding near Kolkata suburb. Sewage overflow, waterborne disease risk. 500 people affected.",
        latitude=22.6708, longitude=88.4272, location_text="Howrah suburbs, WB",
        verification_status=VerificationStatusEnum.corroborated,
        urgency_score=74.0, num_people=500, vulnerable_flags=["child"],
        corroboration_count=4,
    ),
    dict(
        source=SourceEnum.app,
        raw_text="Landslide blocking NH31 in Darjeeling hills. 3 vehicles stuck. 12 passengers stranded.",
        latitude=27.0410, longitude=88.4820, location_text="NH31, Darjeeling hills",
        verification_status=VerificationStatusEnum.unverified,
        urgency_score=38.0, num_people=12, vulnerable_flags=[],
        corroboration_count=0,
    ),
]


@router.post("/demo/simulate-burst", status_code=202)
async def simulate_burst(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Demo endpoint: inject 15 realistic reports into the database staggered
    over 30 seconds so the dashboard visibly re-ranks in real time.

    Designed for judge demos to illustrate "thousands of reports flooding
    in" without needing real Twilio traffic.

    Returns immediately with the scheduled report IDs; the actual DB writes
    happen in the background (one per ~2 s).

    ⚠  Only enabled when ENVIRONMENT != "production".
    """
    from config import settings
    if settings.environment == "production":
        raise HTTPException(
            status_code=403,
            detail="simulate-burst is disabled in production",
        )

    import asyncio

    async def _write_burst():
        """Write each report with a short pause so the dashboard polls pick
        them up incrementally rather than all at once."""
        now = datetime.utcnow()
        interval = 30.0 / len(_BURST_TEMPLATES)   # ~2 s between reports

        for i, tmpl in enumerate(_BURST_TEMPLATES):
            await asyncio.sleep(interval)
            report = Report(
                source=tmpl["source"],
                raw_text=tmpl["raw_text"],
                language="en",
                translated_text=None,
                reporter_phone=None,
                latitude=tmpl.get("latitude"),
                longitude=tmpl.get("longitude"),
                location_text=tmpl.get("location_text"),
                disaster_type=_infer_disaster_type(tmpl["raw_text"]),
                num_people=tmpl.get("num_people"),
                vulnerable_flags=tmpl.get("vulnerable_flags", []),
                verification_status=tmpl["verification_status"],
                urgency_score=tmpl["urgency_score"],
                corroboration_count=tmpl.get("corroboration_count", 0),
                status=StatusEnum.new,
                created_at=now,
                updated_at=now,
            )
            # Need a fresh session for each write from the background thread
            from app.database import SessionLocal
            _db = SessionLocal()
            try:
                _db.add(report)
                _db.commit()
                logger.info("simulate-burst: wrote report %d/%d", i + 1, len(_BURST_TEMPLATES))
            except Exception as exc:
                logger.exception("simulate-burst write error: %s", exc)
                _db.rollback()
            finally:
                _db.close()

    background_tasks.add_task(asyncio.run, _write_burst())

    return {
        "message": f"Burst simulation started — {len(_BURST_TEMPLATES)} reports will appear over ~30 seconds.",
        "report_count": len(_BURST_TEMPLATES),
        "duration_seconds": 30,
        "tip": "Watch the dashboard re-rank automatically as reports arrive.",
    }


def _infer_disaster_type(text: str):
    """Quick keyword scan used only by simulate-burst (avoids importing nlp_extraction)."""
    t = text.lower()
    if any(w in t for w in ("earthquake", "tremor", "quake", "shaking")):
        return "earthquake"
    if any(w in t for w in ("cyclone", "storm", "wind", "hurricane")):
        return "cyclone"
    if any(w in t for w in ("flood", "water", "river", "rain", "embankment")):
        return "flood"
    return "other"


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
    
    NOTE: Automatically excludes duplicate reports (is_duplicate_of is not null)
    to show only primary/merged incidents.
    """
    # Start with base query - EXCLUDE duplicates by default
    query = db.query(Report).filter(Report.is_duplicate_of.is_(None))
    
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
