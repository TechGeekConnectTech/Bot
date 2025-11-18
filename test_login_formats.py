#!/usr/bin/env python3

import requests
import json
import sys

def test_login_formats():
    """Test different login formats to verify what the backend expects"""
    
    base_url = "http://localhost:8000"
    
    test_cases = [
        {
            "name": "Plain text password (correct)",
            "payload": {"username": "admin", "password": "admin123"}
        },
        {
            "name": "Empty password",
            "payload": {"username": "admin", "password": ""}
        },
        {
            "name": "Wrong password", 
            "payload": {"username": "admin", "password": "wrong123"}
        },
        {
            "name": "Support user plain text",
            "payload": {"username": "support_user", "password": "support123"}
        }
    ]
    
    print("🔍 Testing Backend Login API Formats")
    print("=" * 50)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}")
        print(f"   Payload: {json.dumps(test['payload'])}")
        
        try:
            response = requests.post(
                f"{base_url}/api/auth/login",
                json=test['payload'],
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ SUCCESS - Token: {data.get('access_token', '')[:50]}...")
                print(f"   User: {data.get('user_info', {}).get('full_name', '')}")
            else:
                try:
                    error_data = response.json()
                    print(f"   ❌ FAILED - {error_data.get('detail', 'Unknown error')}")
                except:
                    print(f"   ❌ FAILED - HTTP {response.status_code}")
                    
        except requests.exceptions.RequestException as e:
            print(f"   🔌 CONNECTION ERROR: {e}")
    
    # Test frontend request simulation
    print(f"\n🌐 Simulating Frontend Request")
    print("-" * 30)
    
    frontend_payload = {
        "username": "admin",
        "password": "admin123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=frontend_payload,
            headers={
                "Content-Type": "application/json",
                "Origin": "http://localhost:3000",
                "User-Agent": "Mozilla/5.0 (Frontend Test)"
            },
            timeout=5
        )
        
        print(f"Frontend simulation - Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Frontend format should work!")
        else:
            print(f"❌ Frontend format issue: {response.text}")
            
    except Exception as e:
        print(f"🔌 Frontend simulation failed: {e}")

if __name__ == "__main__":
    test_login_formats()