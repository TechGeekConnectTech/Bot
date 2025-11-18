#!/usr/bin/env python3

import asyncio
import sys
sys.path.append('/root/Bot/backend')
from app.services.gpt_service import GPTService

async def test_question_classification():
    """Test improved question classification"""
    
    gpt_service = GPTService()
    
    test_cases = [
        {
            "message": "what help you provide",
            "expected": "informational - should get help response"
        },
        {
            "message": "what can you do",
            "expected": "informational - should get capabilities"
        },
        {
            "message": "something is broken",
            "expected": "technical issue - should ask for details"
        },
        {
            "message": "I have an error",
            "expected": "technical issue - should ask for details"
        },
        {
            "message": "hello there",
            "expected": "greeting - should get simple response"
        },
        {
            "message": "how do you work",
            "expected": "informational - should get help response"
        }
    ]
    
    print("=== Testing Question Classification ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"Test {i}: {test_case['expected']}")
        print(f"Message: '{test_case['message']}'")
        print("-" * 50)
        
        try:
            user_context = {"username": "testuser", "full_name": "Test User"}
            
            # First check simple messages
            simple_response = gpt_service._handle_simple_messages(test_case['message'], user_context)
            if simple_response:
                print(f"✅ SIMPLE RESPONSE: {simple_response.get('ai_service_used', 'simple_response')}")
                print(f"Preview: {simple_response.get('message', '')[:80]}...")
            else:
                # Check CSV search classification
                csv_result = await gpt_service._search_csv_knowledge_base(test_case['message'])
                if csv_result.get('insufficient_info'):
                    print("✅ DETECTED: Insufficient info for technical issue")
                else:
                    print("✅ DETECTED: Not classified as insufficient info")
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
        
        print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    asyncio.run(test_question_classification())