"""
Seed script to generate realistic fake disaster reports and teams.
Run this script to populate the database with demo data.
"""
import random
from datetime import datetime, timedelta
from faker import Faker
from app.database import SessionLocal, engine, Base
from app.models import (
    Report, Team, SourceEnum, DisasterTypeEnum, 
    VerificationStatusEnum, StatusEnum, TeamTypeEnum, TeamStatusEnum
)

fake = Faker()

# Sample district coordinates (using a fictional district in India)
# Centered around 23.5°N, 87.5°E with some spread
BASE_LAT = 23.5
BASE_LON = 87.5
LAT_RANGE = 0.5
LON_RANGE = 0.5

# Sample disaster messages for different types
FLOOD_MESSAGES = [
    "Water level rising rapidly in our area. Need immediate help. About {} people trapped.",
    "Severe flooding in village. Houses submerged. {} families need evacuation.",
    "River overflowing. Low lying areas completely flooded. {} people stranded.",
    "Flash flood situation. Roads blocked. Need rescue for {} people urgently.",
    "Heavy rain causing flooding. Several homes damaged. {} residents need assistance.",
    "Water entered homes up to 4 feet. {} people including children stuck on roofs.",
    "Embankment breach. Entire village flooded. Approximately {} people affected.",
    "Unable to leave home due to flooding. {} of us trapped here for 2 days.",
]

EARTHQUAKE_MESSAGES = [
    "Strong tremors felt. Buildings damaged. About {} people injured and need help.",
    "Earthquake caused several houses to collapse. {} people trapped in debris.",
    "Major cracks in buildings after earthquake. {} families evacuated and homeless.",
    "Building collapsed due to earthquake. {} people trapped inside. Please send help.",
    "Earthquake damage severe. Many injured. Need medical help for {} people.",
    "Houses collapsed. {} people missing. Need rescue teams immediately.",
    "Strong earthquake. Panic situation. {} people injured, need medical assistance.",
    "Multiple buildings damaged. {} residents homeless and in need of shelter.",
]

CYCLONE_MESSAGES = [
    "Cyclone damage severe. Roofs blown away. {} people homeless and exposed.",
    "High winds destroyed homes. {} families need shelter and food urgently.",
    "Trees uprooted, power lines down. {} people trapped in damaged houses.",
    "Cyclone hit our area hard. {} people injured. Houses destroyed.",
    "Strong winds and heavy rain. Extensive damage. {} people need immediate help.",
    "Cyclone aftermath devastating. {} families lost everything. Need relief.",
    "Houses flattened by cyclone. {} people including elderly need evacuation.",
    "Severe cyclone damage. {} residents stranded without food or water.",
]

OTHER_MESSAGES = [
    "Fire broke out in residential area. {} people evacuated. Need help.",
    "Landslide blocked road. {} people trapped on other side. Send help.",
    "Building fire. {} people evacuated. Some injured. Need medical help.",
    "Gas leak caused explosion. {} people injured. Need immediate assistance.",
    "Industrial accident. {} workers affected. Need medical and rescue teams.",
    "Bridge collapse. {} people stranded. Need alternative route and rescue.",
    "Chemical spill in area. {} residents evacuated. Need assistance.",
    "Major accident on highway. {} people injured. Need ambulances.",
]

LANGUAGES = ["en", "hi", "bn", "ta", "te", "mr", "gu", "kn", "ml", "pa"]

VULNERABLE_GROUPS = ["elderly", "child", "pregnant", "disabled"]

TEAM_NAMES = [
    "NDRF Alpha Team", "NDRF Bravo Team", "NDRF Charlie Team",
    "SDRF North Unit", "SDRF South Unit", "SDRF East Unit",
    "Red Cross Relief Team", "Disaster Response NGO", "Community Volunteers East",
    "Local Volunteer Group", "Medical Response Team", "Search and Rescue Unit"
]


def get_random_location():
    """Generate random coordinates within the district."""
    lat = BASE_LAT + random.uniform(-LAT_RANGE, LAT_RANGE)
    lon = BASE_LON + random.uniform(-LON_RANGE, LON_RANGE)
    return lat, lon


def get_location_text():
    """Generate realistic location descriptions."""
    locations = [
        "Near bus stand", "Village center", "River bank area",
        "Behind hospital", "Near railway station", "Market area",
        "Gram panchayat office", "School compound", "Temple road",
        "Main road crossing", "Near water tank", "Old town area",
        "Riverside colony", "Hill slope area", "Bypass road"
    ]
    return f"{random.choice(locations)}, {fake.city()}"


def create_teams(db):
    """Create response teams."""
    teams = []
    team_types = [TeamTypeEnum.NDRF, TeamTypeEnum.SDRF, TeamTypeEnum.NGO, TeamTypeEnum.volunteer]
    
    for i, name in enumerate(TEAM_NAMES):
        team_type = team_types[i % len(team_types)]
        capacity = random.choice([10, 15, 20, 25, 30]) if team_type in [TeamTypeEnum.NDRF, TeamTypeEnum.SDRF] else random.choice([5, 8, 12, 15])
        
        lat, lon = get_random_location()
        status = random.choice([TeamStatusEnum.available, TeamStatusEnum.deployed])
        
        team = Team(
            name=name,
            type=team_type,
            capacity=capacity,
            current_location_lat=lat,
            current_location_lon=lon,
            status=status
        )
        teams.append(team)
        db.add(team)
    
    db.commit()
    return teams


def create_reports(db, teams):
    """Create 40 realistic disaster reports."""
    reports = []
    disaster_types = [DisasterTypeEnum.flood] * 16 + [DisasterTypeEnum.earthquake] * 12 + [DisasterTypeEnum.cyclone] * 9 + [DisasterTypeEnum.other] * 3
    random.shuffle(disaster_types)
    
    message_templates = {
        DisasterTypeEnum.flood: FLOOD_MESSAGES,
        DisasterTypeEnum.earthquake: EARTHQUAKE_MESSAGES,
        DisasterTypeEnum.cyclone: CYCLONE_MESSAGES,
        DisasterTypeEnum.other: OTHER_MESSAGES
    }
    
    # Create reports over the past 3 days
    for i in range(40):
        disaster_type = disaster_types[i]
        num_people = random.randint(5, 50)
        
        # Select message template
        template = random.choice(message_templates[disaster_type])
        raw_text = template.format(num_people)
        
        # Random source
        source = random.choice(list(SourceEnum))
        
        # Language and translation
        language = random.choice(LANGUAGES)
        translated_text = raw_text if language == "en" else None
        
        # Location - 80% have GPS, 20% only text
        has_gps = random.random() < 0.8
        if has_gps:
            lat, lon = get_random_location()
            location_text = None
        else:
            lat, lon = None, None
            location_text = get_location_text()
        
        # Phone number
        reporter_phone = f"+91{random.randint(7000000000, 9999999999)}"
        
        # Vulnerable flags - 40% of reports have vulnerable people
        vulnerable_flags = []
        if random.random() < 0.4:
            num_flags = random.randint(1, 2)
            vulnerable_flags = random.sample(VULNERABLE_GROUPS, num_flags)
        
        # Verification status
        verification_statuses = [
            VerificationStatusEnum.unverified,
            VerificationStatusEnum.unverified,
            VerificationStatusEnum.unverified,
            VerificationStatusEnum.corroborated,
            VerificationStatusEnum.corroborated,
            VerificationStatusEnum.satellite_confirmed,
            VerificationStatusEnum.weather_confirmed,
            VerificationStatusEnum.rejected
        ]
        verification_status = random.choice(verification_statuses)
        
        # Urgency score based on factors
        urgency_score = random.uniform(0.3, 1.0)
        if vulnerable_flags:
            urgency_score = min(urgency_score + 0.2, 1.0)
        if num_people > 30:
            urgency_score = min(urgency_score + 0.15, 1.0)
        
        # Status distribution
        statuses = [
            StatusEnum.new,
            StatusEnum.new,
            StatusEnum.new,
            StatusEnum.in_progress,
            StatusEnum.in_progress,
            StatusEnum.resolved,
            StatusEnum.false_report
        ]
        status = random.choice(statuses)
        
        # Assigned team for in_progress and resolved
        assigned_team = None
        if status in [StatusEnum.in_progress, StatusEnum.resolved] and teams:
            assigned_team = random.choice(teams).name
        
        # Timestamp - spread over last 3 days
        hours_ago = random.randint(0, 72)
        created_at = datetime.utcnow() - timedelta(hours=hours_ago)
        
        report = Report(
            source=source,
            raw_text=raw_text,
            language=language,
            translated_text=translated_text,
            reporter_phone=reporter_phone,
            latitude=lat,
            longitude=lon,
            location_text=location_text,
            disaster_type=disaster_type,
            num_people=num_people,
            vulnerable_flags=vulnerable_flags,
            verification_status=verification_status,
            urgency_score=round(urgency_score, 2),
            status=status,
            assigned_team=assigned_team,
            created_at=created_at,
            updated_at=created_at
        )
        reports.append(report)
        db.add(report)
    
    db.commit()
    
    # Mark some reports as duplicates (about 5 reports)
    # Also increment corroboration_count on originals
    duplicate_count = 5
    used_originals = {}
    for _ in range(duplicate_count):
        original = random.choice(reports[:30])  # Pick from first 30
        duplicate = random.choice(reports[30:])  # Mark one from last 10 as duplicate
        duplicate.is_duplicate_of = original.id
        
        # Track how many duplicates each original has
        if original.id not in used_originals:
            used_originals[original.id] = 0
        used_originals[original.id] += 1
    
    # Update corroboration counts
    for original_id, count in used_originals.items():
        original_report = next((r for r in reports if r.id == original_id), None)
        if original_report:
            original_report.corroboration_count = count
            # Update verification status if corroborated
            if original_report.verification_status == VerificationStatusEnum.unverified:
                original_report.verification_status = VerificationStatusEnum.corroborated
    
    db.commit()
    print(f"✓ Created {len(reports)} disaster reports")
    print(f"  - {sum(1 for r in reports if r.disaster_type == DisasterTypeEnum.flood)} flood reports")
    print(f"  - {sum(1 for r in reports if r.disaster_type == DisasterTypeEnum.earthquake)} earthquake reports")
    print(f"  - {sum(1 for r in reports if r.disaster_type == DisasterTypeEnum.cyclone)} cyclone reports")
    print(f"  - {sum(1 for r in reports if r.disaster_type == DisasterTypeEnum.other)} other disaster reports")
    print(f"  - {sum(1 for r in reports if r.vulnerable_flags)} reports with vulnerable people")
    print(f"  - {duplicate_count} duplicate reports marked")


def init_db():
    """Initialize database and create all tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created")


def seed_database():
    """Main seeding function."""
    print("\n=== RescueAI Database Seeding ===\n")
    
    # Initialize database
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create teams
        print("Creating response teams...")
        teams = create_teams(db)
        print(f"✓ Created {len(teams)} response teams")
        
        # Create reports
        print("\nCreating disaster reports...")
        create_reports(db, teams)
        
        print("\n=== Seeding completed successfully! ===\n")
        
    except Exception as e:
        print(f"\n✗ Error during seeding: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
