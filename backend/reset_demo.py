"""
Demo Reset Script for RescueAI

Resets the database and reseeds with fresh demo data.
Use this before presentations/demos.

Run with: python reset_demo.py
"""

import os
from app.database import engine, Base
from seed_data import seed_database


def reset_demo():
    """Reset database and reseed with demo data."""
    print("\n" + "="*60)
    print("RescueAI Demo Reset")
    print("="*60 + "\n")
    
    # Ask for confirmation
    print("⚠️  WARNING: This will delete all existing data!")
    confirm = input("Type 'YES' to confirm reset: ")
    
    if confirm != "YES":
        print("\n❌ Reset cancelled.")
        return
    
    print("\n🗑️  Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("✅ All tables dropped")
    
    print("\n📊 Creating fresh tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created")
    
    print("\n🌱 Seeding database with demo data...")
    seed_database()
    
    print("\n" + "="*60)
    print("✅ Demo Reset Complete!")
    print("="*60)
    print("\nYou can now:")
    print("  1. Start the backend: python -m uvicorn main:app --reload")
    print("  2. Start the frontend: cd ../frontend && npm run dev")
    print("  3. Visit: http://localhost:5173")
    print("  4. Simulate burst: POST http://localhost:8000/api/demo/simulate-burst")
    print("\n")


if __name__ == "__main__":
    reset_demo()
