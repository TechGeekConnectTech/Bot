#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import asyncio
from app.services.gpt_service import GPTService

async def test_educational_query():
    """Test the educational query functionality"""
    
    gpt_service = GPTService()
    
    # Test the Python vs Java question
    message = "which is best language python or java"
    category = "general"
    user_context = {
        "user_id": 1,
        "department": "DC",
        "username": "test_user",
        "full_name": "Test User"
    }
    
    print("🧪 Testing Educational Query...")
    print(f"Question: {message}")
    print(f"Category: {category}")
    print("-" * 50)
    
    try:
        response = await gpt_service.process_user_query(
            message=message,
            category=category,
            user_context=user_context
        )
        
        print("✅ Response received:")
        print(f"AI Service Used: {response.get('ai_service_used', 'unknown')}")
        print(f"Message Length: {len(response.get('message', ''))}")
        print("-" * 50)
        print("Response Message:")
        print(response.get('message', 'No message'))
        print("-" * 50)
        print("Suggestions:")
        for suggestion in response.get('suggestions', []):
            print(f"• {suggestion}")
        print("-" * 50)
        print("Data Sources:")
        for source in response.get('data_sources', []):
            print(f"• {source}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_educational_query())