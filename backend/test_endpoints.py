"""
Quick test script to verify new API endpoints.
Run with: python test_endpoints.py
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"


def test_endpoint(method, endpoint, description, params=None, json_data=None):
    """Test an API endpoint and print results."""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{method} {url}")
    if params:
        print(f"Params: {params}")
    if json_data:
        print(f"JSON: {json_data}")
    print('-'*60)
    
    try:
        if method == "GET":
            response = requests.get(url, params=params)
        elif method == "POST":
            response = requests.post(url, params=params, json=json_data)
        elif method == "PATCH":
            response = requests.patch(url, params=params, json=json_data)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        print(f"Status: {response.status_code}")
        
        if response.status_code < 400:
            data = response.json()
            print(f"✅ SUCCESS")
            print(f"Response preview:")
            print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
            return True
        else:
            print(f"❌ FAILED")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all endpoint tests."""
    print("="*60)
    print("RescueAI API Endpoints Test Suite")
    print("="*60)
    
    results = []
    
    # Test 1: GET /api/reports (with filters)
    results.append(test_endpoint(
        "GET",
        "/reports",
        "List reports with pagination (default)",
        params={"skip": 0, "limit": 5}
    ))
    
    # Test 2: GET /api/reports (filtered by status)
    results.append(test_endpoint(
        "GET",
        "/reports",
        "List reports filtered by status=new",
        params={"status": "new", "limit": 3}
    ))
    
    # Test 3: GET /api/reports (filtered by disaster type)
    results.append(test_endpoint(
        "GET",
        "/reports",
        "List reports filtered by disaster_type=flood",
        params={"disaster_type": "flood", "limit": 3}
    ))
    
    # Test 4: GET /api/reports (filtered by urgency score)
    results.append(test_endpoint(
        "GET",
        "/reports",
        "List reports with min_score=70",
        params={"min_score": 70, "limit": 3}
    ))
    
    # Test 5: GET /api/reports (different sort)
    results.append(test_endpoint(
        "GET",
        "/reports",
        "List reports sorted by created_desc",
        params={"sort": "created_desc", "limit": 3}
    ))
    
    # Test 6: GET /api/stats/summary
    results.append(test_endpoint(
        "GET",
        "/stats/summary",
        "Get dashboard statistics summary"
    ))
    
    # Get a report ID for detailed tests
    response = requests.get(f"{BASE_URL}/reports", params={"limit": 1})
    if response.status_code == 200 and response.json()["reports"]:
        report_id = response.json()["reports"][0]["id"]
        
        # Test 7: GET /api/reports/{id}
        results.append(test_endpoint(
            "GET",
            f"/reports/{report_id}",
            "Get report details with duplicate cluster"
        ))
        
        # Test 8: PATCH /api/reports/{id}/status
        results.append(test_endpoint(
            "PATCH",
            f"/reports/{report_id}/status",
            "Update report status to in_progress",
            params={"new_status": "in_progress"}
        ))
    
    # Test 9: GET /api/teams
    results.append(test_endpoint(
        "GET",
        "/teams",
        "List all teams",
        params={"status": "available"}
    ))
    
    # Test 10: GET /api/dispatch/summary
    results.append(test_endpoint(
        "GET",
        "/dispatch/summary",
        "Get dispatch summary"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("="*60)


if __name__ == "__main__":
    main()
