#!/bin/bash

echo "🔍 HSBC AutoAssist - Network Connectivity Test"
echo "=============================================="
echo

# Test 1: Check if frontend can reach backend
echo "1. Testing frontend → backend connectivity..."
echo "   Frontend URL: http://localhost:3000"
echo "   Backend URL: http://localhost:8000"
echo

# Try to access the frontend
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 2>/dev/null)
echo "   Frontend Status: HTTP $FRONTEND_STATUS"

# Try to access the backend
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000 2>/dev/null)
echo "   Backend Status: HTTP $BACKEND_STATUS"

echo
echo "2. Testing login API from localhost (simulating frontend)..."

# Test the exact same request the frontend would make
LOGIN_TEST=$(curl -s -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -H "Origin: http://localhost:3000" \
    -H "Referer: http://localhost:3000/" \
    -H "User-Agent: Mozilla/5.0 (HSBC Frontend Test)" \
    -d '{"username":"admin","password":"admin123"}' 2>/dev/null)

if echo "$LOGIN_TEST" | grep -q "access_token"; then
    echo "   ✅ Login API works from localhost"
    echo "   Response: $(echo "$LOGIN_TEST" | cut -c1-100)..."
else
    echo "   ❌ Login API failed"
    echo "   Response: $LOGIN_TEST"
fi

echo
echo "3. Frontend JavaScript Console Debugging Steps:"
echo "   1. Open http://localhost:3000 in browser"
echo "   2. Press F12 to open Developer Tools"
echo "   3. Go to Console tab"
echo "   4. Try to login with admin/admin123"
echo "   5. Watch for errors in Console and Network tabs"
echo
echo "4. Expected console logs (if our debugging code works):"
echo "   - ApiService: Sending login request for username: admin"
echo "   - ApiService: Request URL: http://localhost:8000/api/auth/login"  
echo "   - ApiService: Login response status: 200"
echo "   - AuthContext: Login successful, user set: [user object]"
echo
echo "5. If you see network errors, the issue is connectivity."
echo "   If you see 401 errors, the issue is authentication."
echo "   If you see no logs, the JavaScript isn't running."
echo

echo "💡 Quick Test: Try this URL in browser:"
echo "   http://localhost:8000/docs"
echo "   (Should show FastAPI documentation)"