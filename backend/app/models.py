from sqlalchemy import Column, String, Float, Integer, DateTime, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from app.database import Base


class SourceEnum(str, enum.Enum):
    app = "app"
    sms = "sms"
    whatsapp = "whatsapp"
    voice = "voice"


class DisasterTypeEnum(str, enum.Enum):
    flood = "flood"
    earthquake = "earthquake"
    cyclone = "cyclone"
    other = "other"


class VerificationStatusEnum(str, enum.Enum):
    unverified = "unverified"
    corroborated = "corroborated"
    satellite_confirmed = "satellite_confirmed"
    weather_confirmed = "weather_confirmed"
    rejected = "rejected"


class StatusEnum(str, enum.Enum):
    new = "new"
    in_progress = "in_progress"
    resolved = "resolved"
    false_report = "false_report"


class TeamTypeEnum(str, enum.Enum):
    NDRF = "NDRF"
    SDRF = "SDRF"
    NGO = "NGO"
    volunteer = "volunteer"


class TeamStatusEnum(str, enum.Enum):
    available = "available"
    deployed = "deployed"


class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(Enum(SourceEnum), nullable=False)
    raw_text = Column(String, nullable=False)
    language = Column(String, nullable=False)
    translated_text = Column(String, nullable=True)
    reporter_phone = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_text = Column(String, nullable=True)
    disaster_type = Column(Enum(DisasterTypeEnum), nullable=False)
    num_people = Column(Integer, nullable=True)
    vulnerable_flags = Column(JSON, nullable=True, default=list)
    is_duplicate_of = Column(String, ForeignKey("reports.id"), nullable=True)
    corroboration_count = Column(Integer, nullable=False, default=0)
    verification_status = Column(
        Enum(VerificationStatusEnum), 
        nullable=False, 
        default=VerificationStatusEnum.unverified
    )
    urgency_score = Column(Float, nullable=False, default=0.0)
    urgency_breakdown = Column(JSON, nullable=True, default=dict)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.new)
    assigned_team = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship for duplicate reports
    duplicate_of = relationship("Report", remote_side=[id], backref="duplicates")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    type = Column(Enum(TeamTypeEnum), nullable=False)
    capacity = Column(Integer, nullable=False)
    current_location_lat = Column(Float, nullable=True)
    current_location_lon = Column(Float, nullable=True)
    status = Column(Enum(TeamStatusEnum), nullable=False, default=TeamStatusEnum.available)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
