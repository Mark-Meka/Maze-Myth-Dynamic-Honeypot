"""
Verify Gemini Integration
This script forces Gemini to generate a response and prints it to the console.
"""
import sys
import os
import json
import time

# Add local libs to path
sys.path.append(os.path.join(os.getcwd(), "libs"))

try:
    from llm_integration import LLMGenerator
    
    print("\n" + "="*50)
    print("🧪 GEMINI GENERATION TEST")
    print("="*50)
    
    print("\n[1] Initializing Gemini Connection...")
    llm = LLMGenerator()
    print("✅ Connection Established")
    
    # Test Case 1: User Profile
    endpoint = "/api/v1/user/profile/123"
    method = "GET"
    print(f"\n[2] Generating response for: {method} {endpoint}")
    print("⏳ Waiting for Gemini...")
    
    start_time = time.time()
    response = llm.generate_api_response(endpoint, method)
    duration = time.time() - start_time
    
    print(f"✅ Generated in {duration:.2f} seconds!")
    print("\n👇 GEMINI OUTPUT 👇")
    print("-" * 30)
    print(json.dumps(json.loads(response), indent=2))
    print("-" * 30)
    
    # Test Case 2: Error Message
    endpoint = "/api/admin/system/delete"
    method = "POST"
    print(f"\n[3] Generating response for: {method} {endpoint}")
    print("⏳ Waiting for Gemini...")
    
    response = llm.generate_api_response(endpoint, method, context="User does not have permission")
    
    print("\n👇 GEMINI OUTPUT 👇")
    print("-" * 30)
    print(json.dumps(json.loads(response), indent=2))
    print("-" * 30)
    
    print("\n✨ VERIFICATION COMPLETE: Gemini is working!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
