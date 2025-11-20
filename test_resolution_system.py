#!/usr/bin/env python3

import requests
import json
import sys
import asyncio
from datetime import datetime

# Test Resolution Rate API
def test_resolution_api():
    """Test the resolution feedback and stats APIs"""
    
    base_url = "http://localhost:8000"
    
    # You'll need to get a valid JWT token first
    # Login to get token
    login_response = requests.post(f"{base_url}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    print("🎯 Testing Resolution Rate System...")
    print("="*50)
    
    # Test 1: Submit resolution feedback
    print("\n1. 📝 Testing Resolution Feedback Submission...")
    
    # Assuming we have conversation_id=1 and message_id=2 from existing data
    feedback_data = {
        "conversation_id": 1,
        "message_id": 2,
        "was_resolved": True,
        "resolution_rating": 5,
        "feedback_comment": "Excellent! The 404 error solution worked perfectly."
    }
    
    try:
        feedback_response = requests.post(
            f"{base_url}/api/chat/resolution-feedback", 
            json=feedback_data,
            headers=headers
        )
        
        if feedback_response.status_code == 200:
            print("✅ Feedback submitted successfully!")
            result = feedback_response.json()
            print(f"   Feedback ID: {result['id']}")
            print(f"   Resolved: {result['was_resolved']}")
            print(f"   Rating: {result['resolution_rating']}/5")
        else:
            print(f"❌ Feedback failed: {feedback_response.text}")
    
    except Exception as e:
        print(f"💥 Feedback submission error: {e}")
    
    # Test 2: Get resolution statistics
    print("\n2. 📊 Testing Resolution Statistics...")
    
    try:
        stats_response = requests.get(
            f"{base_url}/api/chat/resolution-stats",
            headers=headers
        )
        
        if stats_response.status_code == 200:
            stats = stats_response.json()
            print("✅ Resolution statistics loaded!")
            print(f"   📈 Total Queries: {stats['total_queries']}")
            print(f"   ✅ Resolved Queries: {stats['resolved_queries']}")
            print(f"   📊 Resolution Rate: {stats['resolution_rate']}%")
            print(f"   ⭐ Average Rating: {stats['average_rating']}")
            
            print("\n   📋 Resolution by Category:")
            for category, data in stats['resolution_by_category'].items():
                print(f"      {category}: {data['resolved']}/{data['total']} ({data['rate']:.1f}%)")
            
            print("\n   🤖 Resolution by AI Service:")
            for service, data in stats['resolution_by_ai_service'].items():
                print(f"      {service}: {data['resolved']}/{data['total']} ({data['rate']:.1f}%)")
                
        else:
            print(f"❌ Stats failed: {stats_response.text}")
    
    except Exception as e:
        print(f"💥 Statistics error: {e}")
    
    print("\n" + "="*50)
    print("🎯 Resolution Rate System Testing Complete!")

def simulate_resolution_data():
    """Add some sample resolution feedback data for testing"""
    print("\n🔧 Adding sample resolution data...")
    
    import mysql.connector
    
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            database='hsbc_autoassist',
            user='root',
            password=''  # Update with your MySQL root password
        )
        
        cursor = conn.cursor()
        
        # Sample feedback data
        sample_feedback = [
            (1, 2, 1, True, 5, 'Perfect solution for API authentication issue!', 'hsbc_internal', 'openai_technical_analysis', 45),
            (2, 4, 2, True, 4, 'Good explanation of REST API concepts', 'general', 'openai_educational', 120),
            (3, 6, 1, False, 2, 'Did not resolve the 500 error completely', 'hsbc_internal', 'fallback', 90),
            (4, 8, 3, True, 5, 'Excellent monitoring guidance!', 'monitoring', 'openai_technical_analysis', 60),
            (5, 10, 2, True, 3, 'Helpful but could be more detailed', 'knowledge_base', 'ollama_fallback', 180),
        ]
        
        for feedback in sample_feedback:
            cursor.execute("""
                INSERT IGNORE INTO resolution_feedback 
                (conversation_id, message_id, user_id, was_resolved, resolution_rating, 
                 feedback_comment, category, ai_service_used, response_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, feedback)
        
        conn.commit()
        print("✅ Sample resolution data added successfully!")
        
        # Show current stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_queries,
                SUM(was_resolved) as resolved_queries,
                ROUND(AVG(CASE WHEN was_resolved THEN resolution_rating END), 2) as avg_rating
            FROM resolution_feedback
        """)
        
        result = cursor.fetchone()
        total, resolved, avg_rating = result
        resolution_rate = (resolved / total * 100) if total > 0 else 0
        
        print(f"   📊 Current Stats:")
        print(f"      Total: {total}, Resolved: {resolved}, Rate: {resolution_rate:.1f}%, Avg Rating: {avg_rating}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--add-sample-data":
        simulate_resolution_data()
    
    test_resolution_api()