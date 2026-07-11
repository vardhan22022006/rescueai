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

# Realistic disaster-prone coordinates across India
# Different disaster types occur in different regions
DISASTER_LOCATIONS = {
    DisasterTypeEnum.flood: [
        # Maharashtra - Pune, Mumbai region (CURRENT RED ALERT AREA)
        (18.5204, 73.8567, "Pune district"),
        (19.0760, 72.8777, "Mumbai"),
        (18.9220, 73.3000, "Lonavala"),
        # Kerala floods
        (10.8505, 76.2711, "Thrissur"),
        (9.9312, 76.2673, "Kochi"),
        # Assam floods
        (26.2006, 92.9376, "Guwahati"),
        (26.7509, 94.2037, "Jorhat"),
        # Bihar floods
        (25.5941, 85.1376, "Patna"),
        (26.1197, 85.3910, "Darbhanga"),
        # West Bengal floods
        (23.5, 87.5, "Bankura"),
        (22.5726, 88.3639, "Kolkata"),
    ],
    DisasterTypeEnum.earthquake: [
        # Uttarakhand seismic zone
        (30.0668, 79.0193, "Uttarkashi"),
        (30.7268, 79.0806, "Dehradun"),
        # Jammu & Kashmir
        (34.0837, 74.7973, "Srinagar"),
        (32.7266, 74.8570, "Jammu"),
        # Northeast earthquakes
        (25.5788, 91.8933, "Shillong"),
        (27.4728, 94.9120, "Tezpur"),
        # Gujarat earthquakes
        (23.0225, 72.5714, "Ahmedabad"),
        (23.2156, 69.6293, "Bhuj"),
    ],
    DisasterTypeEnum.cyclone: [
        # Odisha coast
        (19.8135, 85.8312, "Bhubaneswar coast"),
        (20.2961, 85.8245, "Puri coast"),
        # Tamil Nadu coast
        (11.9139, 79.8145, "Pondicherry coast"),
        (13.0827, 80.2707, "Chennai coast"),
        # Andhra Pradesh coast
        (16.5062, 80.6480, "Vijayawada coast"),
        (17.6869, 83.2185, "Visakhapatnam coast"),
        # Gujarat coast
        (21.7645, 72.1519, "Surat coast"),
        (22.3072, 70.8022, "Junagadh coast"),
    ],
    DisasterTypeEnum.other: [
        # Industrial/urban accidents spread across major cities
        (28.7041, 77.1025, "Delhi NCR"),
        (19.0760, 72.8777, "Mumbai"),
        (12.9716, 77.5946, "Bangalore"),
        (22.5726, 88.3639, "Kolkata"),
        (17.3850, 78.4867, "Hyderabad"),
        (13.0827, 80.2707, "Chennai"),
    ]
}


def get_random_location(disaster_type):
    """Generate random coordinates appropriate for the disaster type."""
    # Get location pool for this disaster type
    locations = DISASTER_LOCATIONS.get(disaster_type, DISASTER_LOCATIONS[DisasterTypeEnum.flood])
    
    # Pick a random base location
    base_lat, base_lon, area_name = random.choice(locations)
    
    # Add small random offset (within ~10km radius)
    lat = base_lat + random.uniform(-0.05, 0.05)
    lon = base_lon + random.uniform(-0.05, 0.05)
    
    return lat, lon, area_name


def get_location_text(area_name):
    """Generate realistic location descriptions for the area."""
    locations = [
        "Near bus stand", "Village center", "River bank area",
        "Behind hospital", "Near railway station", "Market area",
        "Gram panchayat office", "School compound", "Temple road",
        "Main road crossing", "Near water tank", "Old town area",
        "Riverside colony", "Hill slope area", "Bypass road"
    ]
    return f"{random.choice(locations)}, {area_name}"

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


def create_teams(db):
    """Create response teams."""
    teams = []
    team_types = [TeamTypeEnum.NDRF, TeamTypeEnum.SDRF, TeamTypeEnum.NGO, TeamTypeEnum.volunteer]
    
    # Spread teams across major Indian cities
    team_locations = [
        (28.7041, 77.1025, "Delhi"),
        (19.0760, 72.8777, "Mumbai"),
        (18.5204, 73.8567, "Pune"),
        (12.9716, 77.5946, "Bangalore"),
        (22.5726, 88.3639, "Kolkata"),
        (17.3850, 78.4867, "Hyderabad"),
        (13.0827, 80.2707, "Chennai"),
        (23.0225, 72.5714, "Ahmedabad"),
        (26.2006, 92.9376, "Guwahati"),
        (25.5941, 85.1376, "Patna"),
        (30.7268, 79.0806, "Dehradun"),
        (19.8135, 85.8312, "Bhubaneswar"),
    ]
    
    for i, name in enumerate(TEAM_NAMES):
        team_type = team_types[i % len(team_types)]
        capacity = random.choice([10, 15, 20, 25, 30]) if team_type in [TeamTypeEnum.NDRF, TeamTypeEnum.SDRF] else random.choice([5, 8, 12, 15])
        
        lat, lon, _ = team_locations[i % len(team_locations)]
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
    """Create 20 realistic disaster reports spread across India."""
    reports = []
    disaster_types = [DisasterTypeEnum.flood] * 8 + [DisasterTypeEnum.earthquake] * 6 + [DisasterTypeEnum.cyclone] * 4 + [DisasterTypeEnum.other] * 2
    random.shuffle(disaster_types)
    
    message_templates = {
        DisasterTypeEnum.flood: FLOOD_MESSAGES,
        DisasterTypeEnum.earthquake: EARTHQUAKE_MESSAGES,
        DisasterTypeEnum.cyclone: CYCLONE_MESSAGES,
        DisasterTypeEnum.other: OTHER_MESSAGES
    }
    
    # Create reports over the past 2 days (instead of 3)
    for i in range(20):  # Reduced from 40 to 20
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
            lat, lon, area_name = get_random_location(disaster_type)
            location_text = area_name  # Store area name in location_text too
        else:
            lat, lon = None, None
            _, _, area_name = get_random_location(disaster_type)
            location_text = get_location_text(area_name)
        
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
        
        # Timestamp - spread over last 2 days (reduced from 3)
        hours_ago = random.randint(0, 48)
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
    
    # Mark some reports as duplicates (about 3 reports instead of 5)
    # Also increment corroboration_count on originals
    duplicate_count = 3
    used_originals = {}
    for _ in range(duplicate_count):
        original = random.choice(reports[:15])  # Pick from first 15
        duplicate = random.choice(reports[15:])  # Mark one from last 5 as duplicate
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
