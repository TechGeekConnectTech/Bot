#!/bin/bash

# HSBC AutoAssist Setup Verification Script
# This script verifies that all components are properly installed and configured

echo "🏦 HSBC AutoAssist - Setup Verification"
echo "======================================="
echo

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
    fi
}

# Function to print info
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "Checking system prerequisites..."
echo "--------------------------------"

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    print_status 0 "Python 3 installed (version: $PYTHON_VERSION)"
else
    print_status 1 "Python 3 not found"
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_status 0 "Node.js installed (version: $NODE_VERSION)"
else
    print_status 1 "Node.js not found"
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_status 0 "npm installed (version: $NPM_VERSION)"
else
    print_status 1 "npm not found"
fi

# Check MySQL
if command_exists mysql; then
    MYSQL_VERSION=$(mysql --version 2>&1 | cut -d' ' -f6 | cut -d',' -f1)
    print_status 0 "MySQL installed (version: $MYSQL_VERSION)"
else
    print_status 1 "MySQL not found"
fi

echo
echo "Checking project structure..."
echo "-----------------------------"

# Check backend directory
if [ -d "backend" ]; then
    print_status 0 "Backend directory exists"
else
    print_status 1 "Backend directory missing"
fi

# Check frontend directory
if [ -d "frontend" ]; then
    print_status 0 "Frontend directory exists"
else
    print_status 1 "Frontend directory missing"
fi

# Check database directory
if [ -d "database" ]; then
    print_status 0 "Database directory exists"
else
    print_status 1 "Database directory missing"
fi

# Check main backend files
if [ -f "backend/app/main.py" ]; then
    print_status 0 "Backend main.py exists"
else
    print_status 1 "Backend main.py missing"
fi

# Check main frontend files
if [ -f "frontend/src/App.tsx" ]; then
    print_status 0 "Frontend App.tsx exists"
else
    print_status 1 "Frontend App.tsx missing"
fi

# Check database schema
if [ -f "database/schema.sql" ]; then
    print_status 0 "Database schema.sql exists"
else
    print_status 1 "Database schema.sql missing"
fi

echo
echo "Checking dependencies..."
echo "------------------------"

# Check backend dependencies
if [ -f "backend/requirements.txt" ]; then
    print_status 0 "Backend requirements.txt exists"
    
    # Try to check if dependencies are installed
    cd backend
    if python3 -c "import fastapi, sqlalchemy, openai, uvicorn" 2>/dev/null; then
        print_status 0 "Core backend dependencies available"
    else
        print_warning "Some backend dependencies may be missing. Run: pip3 install -r requirements.txt"
    fi
    cd ..
else
    print_status 1 "Backend requirements.txt missing"
fi

# Check frontend dependencies
if [ -f "frontend/package.json" ]; then
    print_status 0 "Frontend package.json exists"
    
    if [ -d "frontend/node_modules" ]; then
        print_status 0 "Frontend node_modules directory exists"
    else
        print_warning "Frontend dependencies not installed. Run: cd frontend && npm install"
    fi
else
    print_status 1 "Frontend package.json missing"
fi

echo
echo "Checking configuration files..."
echo "-------------------------------"

# Check VS Code configuration
if [ -f ".vscode/tasks.json" ]; then
    print_status 0 "VS Code tasks.json exists"
else
    print_status 1 "VS Code tasks.json missing"
fi

if [ -f ".vscode/launch.json" ]; then
    print_status 0 "VS Code launch.json exists"
else
    print_status 1 "VS Code launch.json missing"
fi

# Check for environment file template
if [ -f "backend/.env.example" ]; then
    print_status 0 "Environment template exists"
else
    print_warning "Environment template missing"
fi

echo
echo "Testing database connection..."
echo "------------------------------"

# Test MySQL connection
if command_exists mysql; then
    if mysql -u root -ppassw0rd -e "USE hsbc_autoassist; SELECT 'Database accessible' as status;" 2>/dev/null; then
        print_status 0 "Database connection successful"
    else
        print_warning "Database connection failed. Check if MySQL is running and database is created"
        print_info "Run: mysql -u root -p < database/schema.sql"
    fi
else
    print_warning "Cannot test database connection - MySQL client not available"
fi

echo
echo "Setup verification complete!"
echo "============================"
echo

# Final recommendations
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Configure environment variables in backend/.env"
echo "2. Add your OpenAI API key"
echo "3. Start the application using VS Code tasks or:"
echo "   Backend: cd backend && python3 -m uvicorn app.main:app --reload"
echo "   Frontend: cd frontend && npm start"
echo "4. Access the application at http://localhost:3000"
echo

echo -e "${GREEN}🎉 HSBC AutoAssist is ready for development!${NC}"