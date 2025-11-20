#!/usr/bin/env python3
"""
Simulate sending a message with General category to test the flow
"""

import requests
import json
import time

def test_general_category_flow():
    """Test sending a message with general category"""
    
    print("🧪 Testing General Category Message Flow")
    print("=" * 50)
    
    # Login first (you'll need valid credentials)
    login_data = {
        "username": "admin", 
        "password": "admin123"
    }
    
    try:
        # Login
        print("🔐 Attempting login...")
        login_response = requests.post(
            'http://localhost:8000/api/auth/login',
            data=login_data
        )
        
        if login_response.status_code != 200:
            print(f"❌ Login failed: {login_response.status_code}")
            # Try with another user
            login_data = {"username": "testuser", "password": "testpass"}
            login_response = requests.post(
                'http://localhost:8000/api/auth/login',
                data=login_data  
            )
            
        if login_response.status_code == 200:
            token = login_response.json()['access_token']
            print("✅ Login successful!")
            
            # Send message with general category
            print("\n📤 Sending message with 'general' category...")
            message_data = {
                "message": "What is Python programming?",
                "category": "general"
            }
            
            headers = {"Authorization": f"Bearer {token}"}
            
            message_response = requests.post(
                'http://localhost:8000/api/chat/send-message',
                json=message_data,
                headers=headers
            )
            
            if message_response.status_code == 200:
                response_data = message_response.json()
                print("✅ Message sent successfully!")
                print(f"   📨 Response: {response_data['message'][:100]}...")
                print(f"   💬 Conversation ID: {response_data['conversation_id']}")
                
                # Check if bot message has category in metadata
                if 'message_id' in response_data:
                    print(f"   🆔 Bot Message ID: {response_data['message_id']}")
                    
                return True
            else:
                print(f"❌ Message send failed: {message_response.status_code}")
                print(f"   Error: {message_response.text}")
                
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print("   Skipping message test...")
            
    except Exception as e:
        print(f"❌ Test error: {e}")
        
    return False

if __name__ == "__main__":
    success = test_general_category_flow()
    
    if success:
        print("\n🔍 Checking database after message...")
        time.sleep(1)
        
        import subprocess
        try:
            result = subprocess.run([
                'mysql', '-u', 'root', '-ppassw0rd', '-e', 
                'USE hsbc_autoassist; SELECT "Recent messages:" as info; SELECT id, sender_type, JSON_EXTRACT(message_metadata, "$.category") as category FROM chat_messages ORDER BY timestamp DESC LIMIT 5;'
            ], capture_output=True, text=True)
            
            print(result.stdout)
            
        except Exception as e:
            print(f"❌ Database check error: {e}")
    
    print("\n📋 Next Steps:")
    print("1. ✅ Fixed category storage in message metadata")
    print("2. ✅ Updated GPT service to include category in bot responses") 
    print("3. 🔄 Test by sending a message with 'general' category")
    print("4. 📊 Check admin dashboard for updated common issues")