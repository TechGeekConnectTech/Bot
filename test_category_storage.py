#!/usr/bin/env python3
"""
Test Category Storage in Admin Dashboard
"""

import mysql.connector
import time
import requests
import json

def check_category_storage():
    """Check if categories are being stored properly in resolution_feedback table"""
    
    print("🔍 Checking category storage in database...")
    
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            user='root', 
            password='passw0rd',
            database='hsbc_autoassist'
        )
        cursor = conn.cursor()
        
        # Check resolution feedback categories 
        cursor.execute("""
            SELECT category, COUNT(*) as count, MAX(created_at) as latest 
            FROM resolution_feedback 
            WHERE category IS NOT NULL 
            GROUP BY category 
            ORDER BY count DESC
        """)
        
        categories = cursor.fetchall()
        print("\n📊 Current Resolution Feedback Categories:")
        if categories:
            for category, count, latest in categories:
                print(f"   ✅ {category}: {count} entries (latest: {latest})")
        else:
            print("   ❌ No categories found in resolution_feedback")
            
        # Check recent messages with metadata
        cursor.execute("""
            SELECT id, sender_type, message_metadata, timestamp
            FROM chat_messages 
            WHERE message_metadata IS NOT NULL 
            AND JSON_UNQUOTE(JSON_EXTRACT(message_metadata, '$.category')) IS NOT NULL
            ORDER BY timestamp DESC 
            LIMIT 5
        """)
        
        messages = cursor.fetchall()
        print("\n💬 Recent Messages with Category:")
        if messages:
            for msg_id, sender_type, metadata, timestamp in messages:
                print(f"   📝 Message {msg_id} ({sender_type}): {metadata}")
        else:
            print("   ❌ No messages with category metadata found")
            
        conn.close()
        return len(categories) > 0
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_dashboard_api():
    """Test the admin dashboard API to see what's returned"""
    
    print("\n🌐 Testing Dashboard API...")
    
    try:
        # Test without auth (should get 403)
        response = requests.get('http://localhost:8000/api/admin/dashboard')
        print(f"   📡 Dashboard API Status: {response.status_code}")
        
        if response.status_code == 403:
            print("   ✅ API is running (authentication required as expected)")
            return True
        elif response.status_code == 200:
            data = response.json()
            print(f"   📊 Common Issues: {data.get('common_issues', 'Not found')}")
            return True
        else:
            print(f"   ❌ Unexpected status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ API Error: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Category Storage System")
    print("=" * 50)
    
    # Wait for backend to start
    print("⏳ Waiting for backend to start...")
    time.sleep(3)
    
    # Check database
    db_ok = check_category_storage()
    
    # Check API
    api_ok = test_dashboard_api()
    
    print("\n📋 Test Summary:")
    print(f"   Database: {'✅ OK' if db_ok else '❌ Issues'}")
    print(f"   API: {'✅ OK' if api_ok else '❌ Issues'}")
    
    if not db_ok:
        print("\n💡 Solution: Send a message with category 'general' to test the fix!")
    
    print("\nTest completed! 🎯")