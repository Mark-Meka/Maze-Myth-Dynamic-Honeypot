"""
API Maze Demo Script
Simulates an attacker navigating through the honeypot
"""
import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("="*60)
print("🕵️  SIMULATED ATTACKER - API MAZE NAVIGATION")
print("="*60)

def make_request(method, path, token=None, data=None):
    """Make request and print results"""
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data:
        headers["Content-Type"] = "application/json"
    
    print(f"\n{'='*60}")
    print(f"🔍 {method} {path}")
    if token:
        print(f"🔑 Token: {token[:30]}...")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data)
        
        print(f"📊 Status: {response.status_code}")
        
        try:
            data = response.json()
            print(f"📄 Response:")
            print(json.dumps(data, indent=2))
        except:
            print(f"📄 Response: {response.text}")
        
        return response
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

print("\n🎯 LEVEL 1: Discovery")
time.sleep(1)
make_request("GET", "/")

print("\n\n🎯 LEVEL 2: Hitting Auth Wall")
time.sleep(1)
response = make_request("GET", "/api/v1/users")

print("\n\n🎯 LEVEL 3: Attempting Login")
time.sleep(1)
response = make_request("POST", "/api/v1/auth/login", data={"username": "attacker", "password": "test123"})

if response and response.status_code == 200:
    user_token = response.json().get("token")
    
    print("\n\n🎯 LEVEL 4: Using User Token")
    time.sleep(1)
    make_request("GET", "/api/v1/users", token=user_token)
    
    print("\n\n🎯 LEVEL 5: Trying Admin Endpoint")
    time.sleep(1)
    make_request("GET", "/api/v2/admin/users", token=user_token)
    
    print("\n\n🎯 LEVEL 6: Requesting Elevation")
    time.sleep(1)
    response = make_request("POST", "/api/v1/auth/elevate", token=user_token)
    
    if response and response.status_code == 200:
        admin_token = response.json().get("admin_token")
        
        print("\n\n🎯 LEVEL 7: Using Admin Token")
        time.sleep(1)
        make_request("GET", "/api/v2/admin/users", token=admin_token)
        
        print("\n\n🎯 LEVEL 8: Exploring Internal Endpoints")
        time.sleep(1)
        make_request("GET", "/internal/debug/trace", token=admin_token)
        make_request("GET", "/internal/config/secrets", token=admin_token)

print("\n\n" + "="*60)
print("🏁 DEMO COMPLETE - Attacker is now exploring the maze!")
print("="*60)
print("\nThe honeypot:")
print("✅ Logged all requests")
print("✅ Created realistic responses")
print("✅ Guided attacker through levels")
print("✅ Kept them engaged in the loop")
