#!/usr/bin/env python3

import requests
import json

def test_resolution_feedback_api():
    """Test the resolution feedback API directly"""
    
    base_url = "http://localhost:8000"
    
    # Step 1: Login to get JWT token
    print("🔐 Logging in to get authentication token...")
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("✅ Login successful!")
    
    # Step 2: Get existing conversations and messages
    print("\n📋 Getting existing conversations...")
    conversations_response = requests.get(f"{base_url}/api/chat/conversations", headers=headers)
    
    if conversations_response.status_code == 200:
        conversations = conversations_response.json()
        print(f"Found {len(conversations)} conversations")
        
        if conversations:
            conv = conversations[0]
            conv_id = conv['id']
            print(f"Using conversation ID: {conv_id}")
            
            # Get messages for this conversation
            messages_response = requests.get(f"{base_url}/api/chat/conversation/{conv_id}/messages", headers=headers)
            
            if messages_response.status_code == 200:
                messages = messages_response.json()
                bot_messages = [m for m in messages if m['sender_type'] == 'bot']
                
                if bot_messages:
                    message = bot_messages[0]
                    message_id = message['id']
                    print(f"Using bot message ID: {message_id}")
                    
                    # Step 3: Submit resolution feedback
                    print(f"\n📝 Submitting resolution feedback...")
                    feedback_data = {
                        "conversation_id": conv_id,
                        "message_id": message_id,
                        "was_resolved": True,
                        "resolution_rating": 5,
                        "feedback_comment": "Test feedback - this worked perfectly!"
                    }
                    
                    print(f"Feedback payload: {json.dumps(feedback_data, indent=2)}")
                    
                    feedback_response = requests.post(
                        f"{base_url}/api/chat/resolution-feedback",
                        json=feedback_data,
                        headers=headers
                    )
                    
                    print(f"📊 Response Status: {feedback_response.status_code}")
                    
                    if feedback_response.status_code == 200:
                        print("✅ Resolution feedback submitted successfully!")
                        result = feedback_response.json()
                        print(f"Response: {json.dumps(result, indent=2)}")
                    else:
                        print(f"❌ Resolution feedback failed!")
                        print(f"Response: {feedback_response.text}")
                        print(f"Headers: {feedback_response.headers}")
                else:
                    print("❌ No bot messages found in conversation")
            else:
                print(f"❌ Failed to get messages: {messages_response.text}")
        else:
            print("❌ No conversations found")
    else:
        print(f"❌ Failed to get conversations: {conversations_response.text}")

if __name__ == "__main__":
    test_resolution_feedback_api()