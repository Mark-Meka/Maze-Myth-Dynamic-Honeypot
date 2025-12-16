"""
Test Script for Dynamic API Honeypot
Run this to verify everything is working correctly.
"""
import requests
import json
import time
from datetime import datetime
# Configuration
BASE_URL = "http://localhost:8001"
COLORS = {
    'GREEN': '\033[92m',
    'RED': '\033[91m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'END': '\033[0m'
}
def print_test(name, passed, details=""):
    """Print test result with color"""
    status = f"{COLORS['GREEN']}✓ PASS{COLORS['END']}" if passed else f"{COLORS['RED']}✗ FAIL{COLORS['END']}"
    print(f"  {status} - {name}")
    if details:
        print(f"       {details}")
def test_server_running():
    """Test 1: Check if server is running"""
    print(f"\n{COLORS['BLUE']}=== Test 1: Server Running ==={COLORS['END']}")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        passed = response.status_code == 200
        print_test("Server is accessible", passed, f"Status: {response.status_code}")
        if passed:
            print(f"       Response: {response.json()}")
        return passed
    except Exception as e:
        print_test("Server is accessible", False, f"Error: {e}")
        return False
def test_dynamic_endpoint_generation():
    """Test 2: Dynamic endpoint generation"""
    print(f"\n{COLORS['BLUE']}=== Test 2: Dynamic Endpoint Generation ==={COLORS['END']}")
    
    # Generate random endpoint
    endpoint = f"/api/v{time.time_ns() % 10}/test/endpoint/{int(time.time())}"
    
    try:
        # First call - should create endpoint
        response1 = requests.get(f"{BASE_URL}{endpoint}")
        data1 = response1.json()
        print_test("First call creates endpoint", response1.status_code == 200, 
                   f"Endpoint: {endpoint}")
        print(f"       Response: {json.dumps(data1, indent=2)[:100]}...")
        
        # Second call - should return SAME response
        time.sleep(0.5)
        response2 = requests.get(f"{BASE_URL}{endpoint}")
        data2 = response2.json()
        
        matches = data1 == data2
        print_test("Second call returns same response (PERSISTENCE)", matches,
                   f"Match: {matches}")
        
        return response1.status_code == 200 and matches
    except Exception as e:
        print_test("Dynamic generation", False, f"Error: {e}")
        return False
def test_state_management():
    """Test 3: State management (create and retrieve user)"""
    print(f"\n{COLORS['BLUE']}=== Test 3: State Management ==={COLORS['END']}")
    
    try:
        # Create a user
        test_username = f"testuser_{int(time.time())}"
        user_data = {
            "username": test_username,
            "email": f"{test_username}@test.com"
        }
        
        create_response = requests.post(
            f"{BASE_URL}/api/v1/users",
            json=user_data
        )
        
        created_user = create_response.json()
        print_test("User creation", create_response.status_code == 201,
                   f"User: {created_user.get('username')}")
        
        # List users - should include our created user
        list_response = requests.get(f"{BASE_URL}/api/v1/users")
        users_data = list_response.json()
        users = users_data.get('users', [])
        
        found = any(u.get('username') == test_username for u in users)
        print_test("User appears in list", found,
                   f"Found {len(users)} users, our user present: {found}")
        
        # Get specific user
        if 'id' in created_user:
            user_id = created_user['id']
            get_response = requests.get(f"{BASE_URL}/api/v1/users/{user_id}")
            retrieved_user = get_response.json()
            
            matches = retrieved_user.get('username') == test_username
            print_test("Retrieve specific user by ID", matches,
                       f"Retrieved: {retrieved_user.get('username')}")
        
        return create_response.status_code == 201 and found
    except Exception as e:
        print_test("State management", False, f"Error: {e}")
        return False
def test_file_generation():
    """Test 4: File generation"""
    print(f"\n{COLORS['BLUE']}=== Test 4: File Generation ==={COLORS['END']}")
    
    file_types = [
        ("secret_report.pdf", "PDF"),
        ("employee_data.xlsx", "Excel"),
        ("config.env", "Config")
    ]
    
    results = []
    for filename, file_type in file_types:
        try:
            response = requests.get(f"{BASE_URL}/api/download/{filename}")
            success = response.status_code == 200 and len(response.content) > 0
            
            print_test(f"{file_type} generation", success,
                       f"Size: {len(response.content)} bytes")
            results.append(success)
            
            # Save file for manual inspection
            if success:
                with open(f"test_{filename}", "wb") as f:
                    f.write(response.content)
                print(f"       Saved to: test_{filename}")
        except Exception as e:
            print_test(f"{file_type} generation", False, f"Error: {e}")
            results.append(False)
    
    return all(results)
def test_health_check():
    """Test 5: Health check and statistics"""
    print(f"\n{COLORS['BLUE']}=== Test 5: Health & Statistics ==={COLORS['END']}")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        health_data = response.json()
        
        print_test("Health endpoint", response.status_code == 200)
        
        if 'stats' in health_data:
            stats = health_data['stats']
            print(f"       {COLORS['YELLOW']}Statistics:{COLORS['END']}")
            print(f"         - Total endpoints: {stats.get('total_endpoints', 0)}")
            print(f"         - Total objects: {stats.get('total_objects', 0)}")
            print(f"         - Total beacons: {stats.get('total_beacons', 0)}")
            print(f"         - Activated beacons: {stats.get('activated_beacons', 0)}")
        
        return response.status_code == 200
    except Exception as e:
        print_test("Health check", False, f"Error: {e}")
        return False
def test_documentation():
    """Test 6: Auto-generated documentation"""
    print(f"\n{COLORS['BLUE']}=== Test 6: Documentation ==={COLORS['END']}")
    
    try:
        # Check if docs are accessible
        response = requests.get(f"{BASE_URL}/docs", allow_redirects=True)
        print_test("Swagger UI accessible", response.status_code == 200,
                   f"Visit: {BASE_URL}/docs")
        
        # Check OpenAPI schema
        schema_response = requests.get(f"{BASE_URL}/openapi.json")
        schema = schema_response.json()
        
        endpoints_count = len(schema.get('paths', {}))
        print_test("OpenAPI schema generated", schema_response.status_code == 200,
                   f"Documented endpoints: {endpoints_count}")
        
        return response.status_code == 200
    except Exception as e:
        print_test("Documentation", False, f"Error: {e}")
        return False
def run_all_tests():
    """Run all tests"""
    print(f"\n{COLORS['YELLOW']}{'='*60}{COLORS['END']}")
    print(f"{COLORS['YELLOW']}🍯 Dynamic API Honeypot - Test Suite{COLORS['END']}")
    print(f"{COLORS['YELLOW']}{'='*60}{COLORS['END']}")
    print(f"Testing against: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Run tests
    results.append(("Server Running", test_server_running()))
    
    if results[0][1]:  # Only continue if server is running
        results.append(("Dynamic Generation", test_dynamic_endpoint_generation()))
        results.append(("State Management", test_state_management()))
        results.append(("File Generation", test_file_generation()))
        results.append(("Health Check", test_health_check()))
        results.append(("Documentation", test_documentation()))
    else:
        print(f"\n{COLORS['RED']}⚠️  Server not running. Make sure to start it first:{COLORS['END']}")
        print(f"   python honeypot.py")
        return
    
    # Summary
    print(f"\n{COLORS['YELLOW']}{'='*60}{COLORS['END']}")
    print(f"{COLORS['YELLOW']}📊 Test Summary{COLORS['END']}")
    print(f"{COLORS['YELLOW']}{'='*60}{COLORS['END']}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{COLORS['GREEN']}✓{COLORS['END']}" if result else f"{COLORS['RED']}✗{COLORS['END']}"
        print(f"  {status} {name}")
    
    print(f"\n{COLORS['YELLOW']}Results: {passed}/{total} tests passed{COLORS['END']}")
    
    if passed == total:
        print(f"\n{COLORS['GREEN']}🎉 All tests passed! Your honeypot is working perfectly!{COLORS['END']}")
    else:
        print(f"\n{COLORS['YELLOW']}⚠️  Some tests failed. Check the output above for details.{COLORS['END']}")
    
    print(f"\n{COLORS['BLUE']}Next steps:{COLORS['END']}")
    print(f"  1. Visit {BASE_URL}/docs to see auto-generated API documentation")
    print(f"  2. Check log_files/api_audit.log for detailed logs")
    print(f"  3. Try opening test_*.xlsx or test_*.pdf files")
    print(f"  4. Check logs for 'BEACON_ACTIVATED' events")
    print(f"{COLORS['YELLOW']}{'='*60}{COLORS['END']}\n")
if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print(f"\n\n{COLORS['YELLOW']}Tests interrupted by user.{COLORS['END']}")
    except Exception as e:
        print(f"\n{COLORS['RED']}Fatal error: {e}{COLORS['END']}")