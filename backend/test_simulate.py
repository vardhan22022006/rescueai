"""
Quick test for the simulate-burst demo endpoint.
Run with: python test_simulate.py
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000/api"

def test_simulate_burst():
    """Test the demo simulate-burst endpoint."""
    print("\n" + "="*60)
    print("Testing POST /api/demo/simulate-burst")
    print("="*60 + "\n")
    
    print("Sending request to simulate burst...")
    print("(This will take ~30 seconds to create 15 reports)")
    print("-"*60)
    
    start_time = time.time()
    
    try:
        response = requests.post(f"{BASE_URL}/demo/simulate-burst", timeout=60)
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ Response received in {elapsed:.1f} seconds")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n" + "="*60)
            print("SIMULATION RESULTS")
            print("="*60)
            print(f"✅ Success: {data.get('success')}")
            print(f"📊 Total Created: {data.get('total_created')}")
            print(f"🔁 Duplicates Detected: {data.get('duplicates_detected')}")
            print(f"✨ Unique Incidents: {data.get('unique_incidents')}")
            print(f"\n📈 By Disaster Type:")
            for dtype, count in data.get('by_disaster_type', {}).items():
                print(f"   - {dtype}: {count}")
            
            print(f"\n💬 Message: {data.get('message')}")
            print(f"💡 Demo Tip: {data.get('demo_tip')}")
            
            print("\n" + "="*60)
            print("CREATED REPORTS SUMMARY")
            print("="*60)
            for i, report in enumerate(data.get('reports', [])[:5], 1):
                print(f"\n{i}. {report['disaster_type'].upper()}")
                print(f"   Score: {report['urgency_score']:.1f}")
                print(f"   People: {report['num_people']}")
                print(f"   Duplicate: {'Yes' if report['is_duplicate'] else 'No'}")
            
            if len(data.get('reports', [])) > 5:
                print(f"\n   ... and {len(data.get('reports', [])) - 5} more reports")
            
            print("\n" + "="*60)
            print("✅ Simulation completed successfully!")
            print("="*60)
            
            return True
        else:
            print(f"\n❌ FAILED")
            print(f"Error: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"\n❌ Request timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    print("="*60)
    print("RescueAI Demo Simulation Test")
    print("="*60)
    
    success = test_simulate_burst()
    
    if success:
        print("\n✅ You can now refresh your dashboard to see the new reports!")
        print("   Dashboard: http://localhost:5173")
        print("   API Docs: http://localhost:8000/docs")
    else:
        print("\n⚠️  Test failed. Check if backend is running on port 8000")
