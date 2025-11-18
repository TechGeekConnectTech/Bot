# HSBC AutoAssist 🏦🤖

**DC Automation Support Team Chatbot**

A comprehensive AI-powered chatbot application designed for HSBC's DC Automation Support Team to streamline API support, incident management, and query resolution.

## 🚀 Features

### Core Capabilities
- **🤖 AI-Powered Support**: GPT-4o integration for intelligent query resolution
- **🔐 Secure Authentication**: JWT-based user authentication system
- **💬 Real-time Chat**: Interactive chat interface with conversation history
- **📊 Analytics Dashboard**: Comprehensive metrics and insights
- **🔗 API Integrations**: Splunk, Ansible, and other data source connections
- **🎫 Incident Management**: Automated ticket creation for complex issues
- **📱 Responsive Design**: Modern UI with HSBC corporate branding

### Query Types Supported
- 🔑 **Authentication Issues**: API key problems, token expiration
- 📦 **Payload Issues**: JSON validation, missing fields
- 🔒 **Resource Lock Issues**: Deadlocks, connection pool exhaustion
- ⚡ **Performance Issues**: Timeouts, latency problems
- ⚙️ **Configuration Issues**: Environment setup, service configuration

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React Frontend │    │  FastAPI Backend │    │  MySQL Database │
│                 │────│                 │────│                 │
│ • TypeScript    │    │ • Python 3.9+  │    │ • User Data     │
│ • Material-UI   │    │ • SQLAlchemy    │    │ • Chat History  │
│ • Axios         │    │ • JWT Auth      │    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       
         │              ┌─────────────────┐              
         └──────────────│  External APIs  │              
                        │                 │              
                        │ • OpenAI GPT-4o │              
                        │ • Splunk API    │              
                        │ • Ansible API   │              
                        └─────────────────┘              
```

## 📋 Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.9+
- **MySQL** 8.0+
- **OpenAI API Key** (for GPT-4o)
- **Splunk API Access** (optional)
- **Ansible Tower/AWX Access** (optional)

## 🛠️ Installation & Setup

### 1. Clone Repository
```bash
git clone <repository-url>
cd hsbc-autoassist
```

### 2. Database Setup
```bash
# Login to MySQL
mysql -u root -p

# Run the schema script
source database/schema.sql
```

### 3. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Run the application
python -m app.main
```

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Database
DATABASE_URL=mysql+pymysql://root:passw0rd@localhost:3306/hsbc_autoassist

# JWT Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o

# External APIs
SPLUNK_API_URL=https://your-splunk-instance.com:8089
SPLUNK_API_TOKEN=your-splunk-token
ANSIBLE_API_URL=https://your-ansible-tower.com
ANSIBLE_API_TOKEN=your-ansible-token
```

## 🎯 Usage

### Default Login Credentials
- **Admin**: `admin` / `admin123`
- **Support**: `support_user` / `support123`

### Chat Interface
1. **Start a Conversation**: Type your query or issue description
2. **Provide Context**: Add server name and correlation ID if available
3. **Review Suggestions**: Click on suggested queries for common issues
4. **Follow Recommendations**: Act on AI-provided resolution steps
5. **Escalate if Needed**: Create incidents for complex issues

### Dashboard Features
- **Real-time Metrics**: User activity, conversation stats
- **Resolution Analytics**: Success rates, common issues
- **User Management**: View team activity and performance

## 📚 API Documentation

### Authentication Endpoints
- `POST /api/auth/login` - User authentication
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Current user info

### Chat Endpoints
- `POST /api/chat/send-message` - Send chat message
- `GET /api/chat/conversations` - Get user conversations
- `GET /api/chat/conversation/{id}/messages` - Get conversation messages

### Admin Endpoints
- `GET /api/admin/dashboard` - Dashboard statistics
- `GET /api/admin/users` - User statistics
- `POST /api/admin/create-incident` - Create support incident

Full API documentation available at: `http://localhost:8000/docs`

## 🏢 HSBC Corporate Branding

### Colors
- **Primary Red**: #DB0011
- **Black**: #000000
- **Background**: #F8F9FA
- **Text**: #212121

### Typography
- **Font Family**: Open Sans
- **Headers**: 600 weight
- **Body**: 400 weight

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📊 Monitoring & Analytics

### Built-in Metrics
- Conversation volume and trends
- Resolution success rates
- User engagement patterns
- API performance monitoring
- Error tracking and analysis

### Database Views
- `conversation_stats` - Daily conversation metrics
- `user_activity` - User engagement data
- `daily_metrics` - Comprehensive daily analytics

## 🔧 Development

### Adding New Query Types
1. Update `query_type` enum in database schema
2. Add handling in `GPTService.py`
3. Update frontend suggestions in `ChatPage.tsx`

### External API Integration
1. Create new service in `app/services/`
2. Add configuration in `core/config.py`
3. Integrate in `GPTService.process_user_query()`

## 🚀 Deployment

### Production Setup
1. Configure production database
2. Set secure environment variables
3. Enable HTTPS
4. Configure reverse proxy (nginx/Apache)
5. Set up monitoring and logging

### Docker Deployment (Optional)
```bash
# Build and run with Docker Compose
docker-compose up -d
```

## 🤝 Contributing

1. Follow HSBC coding standards
2. Write comprehensive tests
3. Update documentation
4. Ensure security compliance
5. Test with multiple user roles

## 📄 License

© 2024 HSBC Holdings plc. All rights reserved.

This software is proprietary to HSBC and is intended for internal use only.

## 🆘 Support

For technical support or questions:
- **Email**: dc-automation-support@hsbc.com
- **Teams**: DC Automation Support Channel
- **Documentation**: Internal HSBC Wiki

## 🔄 Version History

- **v1.0.0** - Initial release with core features
  - User authentication and chat interface
  - GPT-4o integration
  - Basic analytics dashboard
  - HSBC corporate branding

---

**Built with ❤️ by the HSBC DC Automation Support Team**