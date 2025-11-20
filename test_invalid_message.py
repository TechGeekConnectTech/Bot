#!/usr/bin/env python3

import requests
import json

def test_invalid_message_id():
    """Test with invalid message ID to reproduce the error"""
    
    base_url = "http://localhost:8000"
    
    # Login
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "username": "admin", 
        "password": "admin123"
    })
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Test with invalid message ID (999999)
    invalid_feedback = {
        "conversation_id": 40,  # Valid conversation ID
        "message_id": 999999,   # Invalid message ID
        "was_resolved": True,
        "resolution_rating": 5,
        "feedback_comment": "Test with invalid message ID"
    }
    
    print("🧪 Testing with invalid message ID...")
    print(f"Payload: {json.dumps(invalid_feedback, indent=2)}")
    
    response = requests.post(
        f"{base_url}/api/chat/resolution-feedback",
        json=invalid_feedback,
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_invalid_message_id()