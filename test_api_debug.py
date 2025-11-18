#!/usr/bin/env python3

import requests
import json

def test_chat_api():
    """Test the chat API to debug the issue"""
    
    # API endpoint
    url = "http://localhost:8000/api/chat/send-message"
    
    # Test payload with HSBC Internal category (same as frontend)
    payload = {
        "message": "404 error",
        "category": "hsbc_internal",
        "server_name": "gb-api-01",
        "correlation_id": "12345"
    }
    
    headers = {
        "Content-Type": "application/json",
        # You'll need to add Authorization header with JWT token
        # "Authorization": "Bearer YOUR_JWT_TOKEN"
    }
    
    print("🧪 Testing HSBC AutoAssist API...")
    print(f"📤 Sending: {json.dumps(payload, indent=2)}")
    print("="*50)
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success!")
            print(f"🤖 AI Service Used: {result.get('ai_service_used', 'Unknown')}")
            print(f"💬 Response: {result.get('message', '')}")
            print(f"📋 Data Sources: {result.get('data_sources', [])}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

if __name__ == "__main__":
    test_chat_api()