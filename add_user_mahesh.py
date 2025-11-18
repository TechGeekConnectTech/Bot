#!/usr/bin/env python3
"""
Add new user to HSBC AutoAssist database
"""
import sys
import os
sys.path.append('/root/Bot/backend')

from passlib.context import CryptContext
import mysql.connector
from datetime import datetime

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def add_user():
    try:
        # Database connection
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='',  # Update if you have a root password
            database='hsbc_autoassist'
        )
        cursor = conn.cursor()
        
        # User details
        username = "mahesh.gavandar"
        email = "mahesh.gavandar@hsbc.com"
        full_name = "Mahesh Gavandar"
        password = "abcd1234"
        department = "DC Automation Support"
        role = "user"  # Can be changed to "admin" if needed
        
        # Hash the password
        hashed_password = hash_password(password)
        
        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s", (username, email))
        existing_user = cursor.fetchone()
        
        if existing_user:
            print(f"❌ User '{username}' or email '{email}' already exists!")
            return False
        
        # Insert new user
        insert_query = """
        INSERT INTO users (username, email, full_name, hashed_password, department, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        current_time = datetime.utcnow()
        cursor.execute(insert_query, (
            username, email, full_name, hashed_password, 
            department, role, True, current_time, current_time
        ))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        print(f"✅ Successfully added user:")
        print(f"   - ID: {user_id}")
        print(f"   - Username: {username}")
        print(f"   - Email: {email}")
        print(f"   - Full Name: {full_name}")
        print(f"   - Department: {department}")
        print(f"   - Role: {role}")
        print(f"   - Password: {password} (hashed: {hashed_password[:50]}...)")
        
        cursor.close()
        conn.close()
        return True
        
    except mysql.connector.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🏦 Adding new user to HSBC AutoAssist database...")
    success = add_user()
    
    if success:
        print("\n🎉 User added successfully!")
        print("📱 Login credentials:")
        print("   - Username: mahesh.gavandar")
        print("   - Password: abcd1234")
        print("🌐 Access the app at: http://localhost:3000")
    else:
        print("\n❌ Failed to add user. Please check the error above.")