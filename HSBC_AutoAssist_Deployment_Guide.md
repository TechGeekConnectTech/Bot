# HSBC AutoAssist Chatbot - Complete Deployment Guide

## 📋 Executive Summary

**HSBC AutoAssist** is an enterprise-grade AI chatbot system designed for HSBC DC Automation Support Team. It provides intelligent API support, troubleshooting, and knowledge management through a category-based routing system that integrates multiple AI services and knowledge sources.

### Key Capabilities
- **Multi-tier AI System**: OpenAI GPT-4 → Ollama Llama 3.2 → Rule-based fallbacks
- **Category-based Intelligence**: General Questions, HSBC Internal Issues, System Monitoring, Knowledge Base
- **Real-time Problem Resolution**: Server issues, API errors, performance monitoring
- **Incident Management**: Create, track, and resolve support tickets
- **Enterprise Integration**: Splunk, Ansible, Confluence APIs

---

## 🏗️ System Architecture

```mermaid
graph TB
    A[User Interface - React TypeScript] --> B[Frontend App - Port 3000]
    B --> C[API Gateway - FastAPI - Port 8000]
    C --> D[JWT Authentication Service]
    C --> E[Chat Service]
    C --> F[Knowledge Management]
    C --> G[Admin Service]
    
    E --> H[GPT Service - Core Intelligence]
    H --> I[OpenAI GPT-4 - Primary AI]
    H --> J[Ollama Llama 3.2 - Fallback]
    H --> K[Rule-based Responses - Final Fallback]
    
    F --> L[CSV Knowledge Base]
    F --> M[Text Documentation]
    F --> N[Confluence API]
    
    E --> O[External Monitoring APIs]
    O --> P[Splunk API - Logs]
    O --> Q[Ansible API - Automation]
    
    D --> R[(MySQL Database - hsbc_autoassist)]
    E --> R
    F --> R
    G --> R
    
    style A fill:#e1f5fe,stroke:#01579b
    style I fill:#4caf50,stroke:#2e7d32
    style J fill:#ff9800,stroke:#ef6c00
    style R fill:#f44336,stroke:#c62828
    style H fill:#9c27b0,stroke:#6a1b9a
```

### Traffic Flow
1. **User Request** → React Frontend (Port 3000)
2. **API Call** → FastAPI Backend (Port 8000)
3. **Authentication** → JWT Token Validation
4. **Category Routing** → GPT Service Intelligence Engine
5. **AI Processing** → OpenAI → Ollama → Built-in Fallback
6. **Knowledge Integration** → CSV/Text/Confluence/APIs
7. **Response Generation** → Structured JSON Response
8. **UI Update** → Real-time Chat Interface

---

## 🗄️ Database Design

### Database: `hsbc_autoassist`
**Engine**: MySQL 8.0+
**Character Set**: utf8mb4
**Collation**: utf8mb4_unicode_ci

### Complete Schema

#### 1. Users Table
```sql
CREATE TABLE `users` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `username` VARCHAR(100) UNIQUE NOT NULL,
    `email` VARCHAR(255) UNIQUE NOT NULL,
    `full_name` VARCHAR(255) NOT NULL,
    `hashed_password` VARCHAR(255) NOT NULL,
    `role` ENUM('admin', 'user') DEFAULT 'user',
    `department` VARCHAR(100),
    `is_active` BOOLEAN DEFAULT TRUE,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `last_login` TIMESTAMP NULL,
    
    INDEX `idx_username` (`username`),
    INDEX `idx_email` (`email`),
    INDEX `idx_role` (`role`),
    INDEX `idx_department` (`department`)
);
```

#### 2. Chat Conversations Table
```sql
CREATE TABLE `chat_conversations` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `user_id` INT NOT NULL,
    `title` VARCHAR(255) DEFAULT 'New Conversation',
    `status` ENUM('active', 'archived', 'deleted') DEFAULT 'active',
    `priority` ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `resolved_at` TIMESTAMP NULL,
    
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_user_conversations` (`user_id`, `updated_at`),
    INDEX `idx_status` (`status`),
    INDEX `idx_priority` (`priority`)
);
```

#### 3. Chat Messages Table
```sql
CREATE TABLE `chat_messages` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `conversation_id` INT NOT NULL,
    `sender_type` ENUM('user', 'bot', 'system') NOT NULL,
    `message_content` TEXT NOT NULL,
    `message_metadata` JSON NULL,
    `timestamp` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversations`(`id`) ON DELETE CASCADE,
    INDEX `idx_conversation_messages` (`conversation_id`, `timestamp`),
    INDEX `idx_sender_type` (`sender_type`)
);
```

#### 4. Query Resolutions Table (Incident Management)
```sql
CREATE TABLE `query_resolutions` (
    `id` INT PRIMARY KEY AUTO_INCREMENT,
    `conversation_id` INT NOT NULL,
    `user_id` INT NOT NULL,
    `incident_id` VARCHAR(50) UNIQUE,
    `query_type` VARCHAR(50),
    `server_name` VARCHAR(100),
    `correlation_id` VARCHAR(100),
    `root_cause` TEXT,
    `resolution_steps` TEXT,
    `priority` ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    `status` ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    `incident_created` BOOLEAN DEFAULT FALSE,
    `resolved_automatically` BOOLEAN DEFAULT FALSE,
    `ai_service_used` VARCHAR(50),
    `data_sources` JSON,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversations`(`id`) ON DELETE CASCADE,
    FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON DELETE CASCADE,
    INDEX `idx_incident_id` (`incident_id`),
    INDEX `idx_user_incidents` (`user_id`, `status`),
    INDEX `idx_server_name` (`server_name`),
    INDEX `idx_correlation_id` (`correlation_id`),
    INDEX `idx_query_type` (`query_type`)
);
```

---

## 🚀 Quick Setup Instructions

### 1. Prerequisites
- Python 3.9+
- Node.js 16+
- MySQL 8.0+
- Git

### 2. Database Setup
```sql
CREATE DATABASE hsbc_autoassist CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'hsbc_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON hsbc_autoassist.* TO 'hsbc_user'@'localhost';
-- Run table creation scripts above
```

### 3. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure .env file
DATABASE_URL=mysql+pymysql://hsbc_user:secure_password@localhost:3306/hsbc_autoassist
OPENAI_API_KEY=your-openai-api-key-here
SECRET_KEY=your-jwt-secret-key

uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4. Frontend Setup
```bash
cd frontend
npm install
echo "REACT_APP_API_URL=http://localhost:8000" > .env
npm start
```

---

## 🔧 Configuration Files

### Backend Dependencies (requirements.txt)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
pymysql==1.1.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
openai==1.3.7
requests==2.31.0
pandas==2.1.3
python-dotenv==1.0.0
mysql-connector-python==8.2.0
```

### Frontend Dependencies (package.json)
```json
{
  "name": "hsbc-autoassist-frontend",
  "dependencies": {
    "react": "^18.2.0",
    "typescript": "^4.9.5",
    "@mui/material": "^5.14.18",
    "axios": "^1.6.2",
    "react-router-dom": "^6.18.0"
  }
}
```

---

## 📊 Core Features

### 1. Category-Based Intelligence
- **General**: Educational queries via OpenAI GPT-4
- **HSBC Internal**: Technical issues via knowledge base
- **Monitoring**: System data via Splunk/Ansible APIs
- **Knowledge Base**: Documentation search

### 2. Multi-tier AI System
- **Primary**: OpenAI GPT-4 for comprehensive responses
- **Fallback**: Ollama Llama 3.2 for offline capability
- **Final**: Built-in responses for guaranteed availability

### 3. HSBC Server Recognition
Supports server naming patterns: `gb-`, `cn-`, `hk-`, `vn-`, `mx-`, `us-`, `ca-`, `au-`, `sg-`, `my-`, `in-`, `ae-`, `fr-`, `de-`

### 4. Incident Management
- Automatic ticket creation for unresolved issues
- Resolution tracking and analytics
- Integration with corporate ticketing systems

---

## 🔒 Security Features

- JWT-based authentication
- Password hashing with bcrypt
- Input validation and sanitization
- CORS configuration
- Environment-based secrets management
- Role-based access control (Admin/User)

---

## 📈 Performance Optimization

- Database connection pooling
- Async/await processing
- Response caching for knowledge base
- API rate limiting
- Background task processing
- Load balancing ready

---

## 🐛 Troubleshooting

### Common Issues:
1. **Database Connection**: Check MySQL service and credentials
2. **OpenAI API**: Verify API key and usage limits
3. **CORS Errors**: Update ALLOWED_ORIGINS in environment
4. **Port Conflicts**: Ensure ports 3000 and 8000 are available

### Health Checks:
```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/api/admin/db-health
```

---

## 📚 API Documentation

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration

### Chat Operations
- `POST /api/chat/send-message` - Send chat message
- `GET /api/chat/conversations` - Get user conversations
- `GET /api/chat/conversations/{id}/messages` - Get conversation messages

### Admin Operations
- `GET /api/admin/users` - Manage users
- `GET /api/admin/incidents` - View all incidents
- `GET /api/admin/stats` - System statistics

---

## 🎯 Success Metrics

- **Response Accuracy**: >85% correct technical resolutions
- **Response Time**: <3 seconds average
- **System Uptime**: >99.5% availability
- **User Adoption**: Target 90+ concurrent users
- **Incident Reduction**: 40% fewer manual support tickets

---

This deployment guide provides comprehensive instructions for setting up HSBC AutoAssist in your corporate environment. The system is designed for scalability, security, and ease of maintenance while providing intelligent automation support for your DC team.