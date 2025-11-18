#!/usr/bin/env python3
"""
Test login for Mahesh Gavandar
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_mahesh_login():
    # Test login with new user
    login_data = {
        "username": "mahesh.gavandar",
        "password": "abcd1234"
    }
    
    print("🔐 Testing login for Mahesh Gavandar...")
    print(f"Username: {login_data['username']}")
    print(f"Password: {login_data['password']}")
    
    try:
        login_response = requests.post(
            f"{BASE_URL}/api/auth/login", 
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Login Status Code: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_result = login_response.json()
            print("✅ Login successful!")
            print(f"User Info: {login_result.get('user_info', {})}")
            print(f"Token received: {login_result.get('access_token', 'N/A')[:20]}...")
            
            # Test accessing incidents with this user
            token = login_result.get("access_token")
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            print("\n📊 Testing incidents access...")
            incidents_response = requests.get(f"{BASE_URL}/api/incidents", headers=headers)
            print(f"Incidents Status: {incidents_response.status_code}")
            
            if incidents_response.status_code == 200:
                incidents_data = incidents_response.json()
                print(f"✅ Incidents accessible - found {len(incidents_data.get('incidents', []))} incidents")
            else:
                print(f"❌ Incidents access failed: {incidents_response.text}")
                
        else:
            print(f"❌ Login failed: {login_response.text}")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")

if __name__ == "__main__":
    test_mahesh_login()