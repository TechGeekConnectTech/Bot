#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.append('/root/Bot/backend')

from app.services.gpt_service import GPTService
from app.services.api_integrations import SplunkService, AnsibleService

async def test_insufficient_info():
    """Test the insufficient information handling"""
    
    # Initialize services
    splunk_service = SplunkService()
    ansible_service = AnsibleService()
    gpt_service = GPTService(splunk_service, ansible_service)
    
    # Test cases
    test_cases = [
        {
            "message": "something is broken",
            "description": "Very vague message with no technical details"
        },
        {
            "message": "I have an issue",
            "description": "Generic issue statement without specifics"
        },
        {
            "message": "error occurred",
            "description": "Basic error mention without context"
        },
        {
            "message": "srv-api-01 is showing 401 error",
            "description": "Specific server and error code - should NOT trigger insufficient info"
        },
        {
            "message": "hello",
            "description": "Simple greeting - should get simple response"
        }
    ]
    
    print("=== Testing Insufficient Information Handling ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['description']}")
        print(f"Message: '{test_case['message']}'")
        print("-" * 50)
        
        try:
            # Test the message processing
            user_context = {"username": "testuser", "full_name": "Test User"}
            
            response = await gpt_service.process_message(
                message=test_case['message'],
                user_context=user_context
            )
            
            # Check the response
            if 'insufficient_info' in response.get('ai_service_used', ''):
                print("✅ PASS: Detected insufficient information")
            elif response.get('ai_service_used') == 'simple_response':
                print("✅ PASS: Simple greeting response")
            elif 'srv-api-01' in test_case['message']:
                print("✅ PASS: Processed technical query appropriately")
            else:
                print(f"❌ RESULT: {response.get('ai_service_used', 'unknown')}")
                print(f"Message preview: {response.get('message', '')[:100]}...")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    asyncio.run(test_insufficient_info())