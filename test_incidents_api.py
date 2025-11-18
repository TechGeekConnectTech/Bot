#!/usr/bin/env python3
"""
Test script for incidents API endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login_and_incidents():
    # Test login first
    login_data = {
        "username": "admin",
        "password": "admin123"  # Default admin password
    }
    
    print("🔐 Testing login...")
    login_response = requests.post(
        f"{BASE_URL}/api/auth/login", 
        json=login_data,
        headers={"Content-Type": "application/json"}
    )
    print(f"Login Status: {login_response.status_code}")
    
    if login_response.status_code == 200:
        login_result = login_response.json()
        token = login_result.get("access_token")
        print(f"✅ Login successful, token received")
        
        # Test incidents endpoint with token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        print("\n📊 Testing incidents endpoint...")
        incidents_response = requests.get(f"{BASE_URL}/api/incidents", headers=headers)
        print(f"Incidents Status: {incidents_response.status_code}")
        print(f"Response: {incidents_response.text}")
        
        if incidents_response.status_code == 200:
            incidents_data = incidents_response.json()
            print(f"✅ Found {len(incidents_data.get('incidents', []))} incidents")
        
        # Test admin incidents endpoint
        print("\n👨‍💼 Testing admin incidents endpoint...")
        admin_incidents_response = requests.get(f"{BASE_URL}/api/admin/incidents", headers=headers)
        print(f"Admin Incidents Status: {admin_incidents_response.status_code}")
        print(f"Response: {admin_incidents_response.text}")
        
    else:
        print(f"❌ Login failed: {login_response.text}")
        
        # Try with other credentials
        print("\n🔄 Trying with testuser...")
        login_data = {
            "username": "testuser", 
            "password": "test123"
        }
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login", 
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"Testuser Login Status: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"Response: {login_response.text}")

if __name__ == "__main__":
    test_login_and_incidents()