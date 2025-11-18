# HSBC AutoAssist - Essential Implementation Guide

## 🎯 Project Overview

**HSBC AutoAssist** is an intelligent chatbot system for DC Automation Support Team featuring:
- **Multi-tier AI**: OpenAI GPT-4 → Ollama Llama 3.2 → Rule-based fallbacks
- **Category-based Routing**: General, HSBC Internal, Monitoring, Knowledge Base
- **Real-time Problem Resolution**: Server issues, API diagnostics, incident management
- **Enterprise Integration**: Splunk, Ansible, Confluence APIs

---

## 📊 Database Structure

### Database: `hsbc_autoassist`

#### Core Tables Schema:

```sql
-- 👤 Users Table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    department VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 💬 Chat Conversations Table
CREATE TABLE chat_conversations (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    title VARCHAR(255) DEFAULT 'New Conversation',
    status ENUM('active', 'archived', 'deleted') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 📝 Chat Messages Table
CREATE TABLE chat_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    sender_type ENUM('user', 'bot', 'system') NOT NULL,
    message_content TEXT NOT NULL,
    message_metadata JSON NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE
);

-- 🎫 Incident Management Table
CREATE TABLE query_resolutions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    conversation_id INT NOT NULL,
    user_id INT NOT NULL,
    incident_id VARCHAR(50) UNIQUE,
    query_type VARCHAR(50),
    server_name VARCHAR(100),
    correlation_id VARCHAR(100),
    root_cause TEXT,
    resolution_steps TEXT,
    status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    ai_service_used VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES chat_conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## 🏗️ System Architecture Flow

```mermaid
graph TB
    A[👤 User Input] --> B[🎯 Category Selection]
    B --> C[📱 React Frontend<br/>Port 3000]
    C --> D[🌐 API Gateway<br/>FastAPI Port 8000]
    
    D --> E[🔐 JWT Authentication]
    E --> F[🧠 GPT Service<br/>Core Intelligence Engine]
    
    F --> G{📋 Category Router}
    G -->|General| H[🤖 Direct LLM Processing]
    G -->|HSBC Internal| I[📊 Data Collection Phase]
    G -->|Monitoring| J[🔍 Data Collection Phase]
    G -->|Knowledge Base| K[📚 Data Collection Phase]
    
    I --> N[📈 CSV Server Issues DB]
    I --> AA[🏦 Internal HSBC APIs]
    J --> O[📊 Splunk APIs]
    J --> BB[🤖 Ansible APIs]
    K --> P[📄 Confluence APIs]
    K --> CC[📝 Text Documentation]
    
    N --> L[🧠 LLM Analysis Engine<br/>OpenAI GPT-4]
    AA --> L
    O --> L
    BB --> L
    P --> L
    CC --> L
    
    H --> L
    L --> DD[🦙 Ollama Fallback]
    DD --> M[⚙️ Built-in Responses]
    
    L --> Q[🔧 Intelligent Response Generator]
    DD --> Q
    M --> Q
    
    Q --> R[💾 Save to MySQL]
    R --> S[📱 Update UI Response]
    
    style F fill:#9c27b0,stroke:#6a1b9a,color:#fff
    style H fill:#4caf50,stroke:#2e7d32,color:#fff
    style L fill:#ff9800,stroke:#ef6c00,color:#fff
    style R fill:#f44336,stroke:#c62828,color:#fff
```

---

## 💻 Essential Files Structure

### Backend Core Files (FastAPI):

```
backend/
├── app/
│   ├── main.py                    # 🚀 Application Entry Point
│   ├── core/
│   │   ├── config.py             # ⚙️ Settings & Environment
│   │   ├── database.py           # 🗄️ MySQL Connection
│   │   └── security.py           # 🔒 JWT Authentication
│   ├── models/
│   │   ├── user.py               # 👤 User Data Models  
│   │   └── chat.py               # 💬 Chat Data Models
│   ├── api/
│   │   ├── auth.py               # 🔐 Login/Register APIs
│   │   ├── chat.py               # 💬 Chat Message APIs
│   │   └── admin.py              # 👨‍💼 Admin Management
│   ├── services/
│   │   ├── gpt_service.py        # 🧠 MAIN AI ENGINE
│   │   ├── csv_knowledge_service.py # 📊 Server Issues DB
│   │   └── enhanced_knowledge_service.py # 🔍 Multi-source Search
│   └── data/
│       └── knowledge_base.csv    # 🏦 HSBC Server Issues Data
├── requirements.txt              # 📦 Python Dependencies
└── .env                         # 🔑 Configuration File
```

### Frontend Core Files (React TypeScript):

```
frontend/
├── src/
│   ├── App.tsx                   # 🏠 Main Application
│   ├── pages/
│   │   ├── LoginPage.tsx         # 🔑 Authentication
│   │   ├── ChatPage.tsx          # 💬 MAIN CHAT INTERFACE
│   │   └── IncidentsPage.tsx     # 🎫 Incident Management
│   ├── services/
│   │   └── api.ts                # 🔌 Backend Communication
│   └── components/
│       └── Layout.tsx            # 🏗️ App Layout
├── package.json                  # 📦 Dependencies
└── .env                         # 🌐 API Configuration
```

---

## 🧠 Core Intelligence Engine Logic

### GPTService - The Brain (`gpt_service.py`)

**Main Function**: `process_user_query()`

```python
async def process_user_query(self, message: str, category: str = None, 
                           server_name: str = None, correlation_id: str = None, 
                           user_context: Dict = None) -> Dict:
    """
    🎯 MAIN INTELLIGENCE ROUTING ENGINE
    
    Processing Flow:
    1. Category Detection → Route to appropriate handler
    2. Knowledge Search → Check databases & external sources  
    3. AI Processing → OpenAI → Ollama → Built-in fallback
    4. Response Generation → Format structured response
    """
    
    # 🎯 Priority 1: Category-based Routing
    if category:
        return await self._handle_category_based_query(
            message, category, server_name, correlation_id, user_context
        )
    
    # 🔍 Priority 2: Technical Issue Detection
    if self._has_technical_issue_context(message):
        return await self._search_enhanced_knowledge_base(
            message, server_name, user_context
        )
    
    # 📚 Priority 3: General Information
    return self._provide_guidance_response(user_context)
```

### Category Handlers:

#### 1. General Educational Queries:
```python
async def _handle_general_educational_query(self, message: str, user_context: Dict):
    """
    📚 EDUCATIONAL QUERY PROCESSING
    
    Tier 1: OpenAI GPT-4 (Primary AI)
    Tier 2: Ollama Llama 3.2 (Local Fallback)  
    Tier 3: Built-in Responses (Final Fallback)
    """
    
    # 🥇 Try OpenAI GPT-4 first
    try:
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{
                "role": "user", 
                "content": f"Provide comprehensive educational response: {message}"
            }],
            temperature=0.7,
            max_tokens=600
        )
        
        return {
            "message": f"📚 **Educational Response**\n\n{response.choices[0].message.content}",
            "ai_service_used": "openai_educational",
            "data_sources": ["OpenAI GPT-4", "Educational Knowledge"]
        }
    except Exception:
        # 🥈 Fallback to Ollama
        return await self._get_ollama_educational_response(message, user_context)
```

#### 2. HSBC Internal Issues:
```python
async def _handle_hsbc_internal_issue(self, message: str, server_name: str, 
                                     correlation_id: str, user_context: Dict):
    """
    🏦 HSBC TECHNICAL ISSUE RESOLUTION WITH LLM ANALYSIS
    
    Enhanced Process:
    1. Extract server name (gb-, cn-, hk-, vn-, mx-, etc.)
    2. Classify issue type (auth, payload, performance, config)
    3. Collect data from ALL sources:
       - CSV knowledge base for historical solutions
       - Internal HSBC APIs for real-time server status
       - Splunk APIs for log analysis
       - Ansible APIs for automation data
    4. Send consolidated data to LLM for intelligent analysis
    5. Generate comprehensive resolution response
    """
    
    # 🔍 Server extraction & standardization
    if not server_name:
        server_name = self._extract_server_name(message)
    
    # 📊 Phase 1: Data Collection from Multiple Sources
    collected_data = {
        "csv_knowledge": self.csv_knowledge.search_issues(message, server_name),
        "hsbc_apis": await self._query_hsbc_internal_apis(server_name, correlation_id),
        "splunk_logs": await self._query_splunk_logs(server_name, correlation_id),
        "ansible_data": await self._query_ansible_status(server_name)
    }
    
    # 🧠 Phase 2: LLM Analysis of Consolidated Data
    return await self._analyze_with_llm(
        message=message,
        server_name=server_name,
        collected_data=collected_data,
        analysis_type="technical_troubleshooting"
    )
```

#### 3. System Monitoring:
```python
async def _handle_monitoring_query(self, message: str, server_name: str, 
                                  correlation_id: str, user_context: Dict):
    """
    📊 SYSTEM MONITORING DATA ANALYSIS WITH LLM INTELLIGENCE
    
    Enhanced Process:
    1. Collect monitoring data from multiple sources
    2. Send consolidated data to LLM for pattern analysis
    3. Generate intelligent insights and recommendations
    
    Sources:
    - Splunk API: Log analysis, error tracking, performance trends
    - Ansible API: Automation status, deployment data, job histories
    - Internal APIs: Real-time metrics, alerts, system health
    - CSV Knowledge: Historical monitoring patterns
    """
    
    # 📊 Phase 1: Comprehensive Data Collection
    monitoring_data = {
        "splunk_logs": await self._query_splunk_logs(correlation_id, server_name),
        "ansible_data": await self._query_ansible_status(server_name),
        "performance_metrics": await self._query_performance_apis(server_name),
        "alert_history": await self._query_alert_systems(server_name),
        "historical_patterns": self.csv_knowledge.search_monitoring_patterns(message, server_name)
    }
    
    # 🧠 Phase 2: LLM Analysis for Intelligent Monitoring Insights
    return await self._analyze_with_llm(
        message=message,
        server_name=server_name,
        collected_data=monitoring_data,
        analysis_type="monitoring_analysis"
    )
```

### Knowledge Base Structure:

#### CSV Server Issues Database (`knowledge_base.csv`):
```csv
issue_id,server_name,issue_type,error_code,description,root_cause,resolution_steps,priority
1,gb-api-01,auth_issue,401,"Authentication failed","JWT token expired","Check token expiration | Regenerate API token | Update headers | Retry request",medium
2,cn-db-server,performance_issue,500,"Database connection timeout","Connection pool exhausted","Monitor connection pool | Increase pool size | Restart service",high
3,hk-web-prod,payload_issue,400,"Invalid JSON format","Missing required fields","Validate JSON structure | Check required fields | Update request format",low
```

#### Server Naming Convention Recognition:
```python
def _extract_server_name(self, message: str) -> str:
    """
    🏦 HSBC Server Naming Pattern Recognition
    
    Patterns:
    - gb-* : Great Britain/UK servers
    - cn-* : China servers  
    - hk-* : Hong Kong servers
    - vn-* : Vietnam servers
    - mx-* : Mexico servers
    - us-* : United States servers
    - ca-* : Canada servers
    - au-* : Australia servers
    - sg-* : Singapore servers
    - my-* : Malaysia servers
    - in-* : India servers
    - ae-* : UAE servers
    - fr-* : France servers
    - de-* : Germany servers
    """
    
    server_patterns = [
        r'\b(gb|cn|hk|vn|mx|us|ca|au|sg|my|in|ae|fr|de)-[a-zA-Z0-9-]+\b'
    ]
    
    for pattern in server_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(0).lower()
    
        return None

### LLM Analysis Engine:

```python
async def _analyze_with_llm(self, message: str, server_name: str, 
                          collected_data: Dict, analysis_type: str) -> Dict:
    """
    🧠 CENTRAL LLM ANALYSIS ENGINE
    
    Takes collected data from multiple sources and uses LLM to:
    1. Analyze patterns and correlations
    2. Generate intelligent troubleshooting steps
    3. Provide consolidated recommendations
    4. Format responses in user-friendly manner
    """
    
    # 🔍 Prepare context for LLM analysis
    analysis_context = self._prepare_llm_context(
        message, server_name, collected_data, analysis_type
    )
    
    # 🥇 Primary: OpenAI GPT-4 Analysis
    try:
        if self.api_key and self.client:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"""
                        You are an expert HSBC technical support analyst. Analyze the provided data and give:
                        1. Root cause analysis
                        2. Step-by-step troubleshooting guide
                        3. Prevention recommendations
                        4. Priority assessment
                        
                        Analysis Type: {analysis_type}
                        Server Context: {server_name or 'Multiple servers'}
                        """
                    },
                    {
                        "role": "user",
                        "content": f"""
                        User Query: {message}
                        
                        Collected Data Analysis:
                        {analysis_context}
                        
                        Please provide a comprehensive technical resolution response.
                        """
                    }
                ],
                temperature=0.3,  # Lower temperature for technical accuracy
                max_tokens=800
            )
            
            llm_response = response.choices[0].message.content
            
            return {
                "message": f"🔧 **Technical Analysis & Resolution**\n\n{llm_response}",
                "ai_service_used": "openai_technical_analysis",
                "data_sources": list(collected_data.keys()),
                "server_name": server_name,
                "analysis_type": analysis_type,
                "confidence_level": "high"
            }
            
    except Exception as e:
        logger.error(f"OpenAI analysis error: {e}")
    
    # 🥈 Fallback: Ollama Analysis
    return await self._analyze_with_ollama(
        message, server_name, collected_data, analysis_type
    )

def _prepare_llm_context(self, message: str, server_name: str, 
                        collected_data: Dict, analysis_type: str) -> str:
    """
    📋 PREPARE STRUCTURED CONTEXT FOR LLM ANALYSIS
    
    Formats collected data into structured context that LLM can analyze effectively
    """
    
    context_parts = []
    
    # 🏦 CSV Knowledge Base Results
    if collected_data.get("csv_knowledge"):
        context_parts.append("## Historical Knowledge Base:")
        for item in collected_data["csv_knowledge"][:3]:  # Top 3 matches
            context_parts.append(f"- Issue: {item.get('description', 'N/A')}")
            context_parts.append(f"  Root Cause: {item.get('root_cause', 'N/A')}")
            context_parts.append(f"  Resolution: {item.get('resolution_steps', 'N/A')}")
    
    # 📊 Splunk Log Data
    if collected_data.get("splunk_logs"):
        context_parts.append("\n## Splunk Log Analysis:")
        context_parts.append(f"- Recent errors: {len(collected_data['splunk_logs'].get('errors', []))}")
        context_parts.append(f"- Error patterns: {collected_data['splunk_logs'].get('patterns', 'None detected')}")
    
    # 🤖 Ansible Automation Data
    if collected_data.get("ansible_data"):
        context_parts.append("\n## Automation Status:")
        context_parts.append(f"- Job status: {collected_data['ansible_data'].get('status', 'Unknown')}")
        context_parts.append(f"- Last deployment: {collected_data['ansible_data'].get('last_deployment', 'N/A')}")
    
    # 🏦 Internal HSBC API Data
    if collected_data.get("hsbc_apis"):
        context_parts.append("\n## Real-time Server Status:")
        context_parts.append(f"- Server health: {collected_data['hsbc_apis'].get('health_status', 'Unknown')}")
        context_parts.append(f"- Current load: {collected_data['hsbc_apis'].get('current_load', 'N/A')}")
    
    # 📄 Documentation/Confluence Data
    if collected_data.get("confluence_data"):
        context_parts.append("\n## Documentation References:")
        for doc in collected_data["confluence_data"][:2]:  # Top 2 relevant docs
            context_parts.append(f"- {doc.get('title', 'Untitled')}: {doc.get('summary', 'N/A')}")
    
    return "\n".join(context_parts)
```---

## 📱 Frontend Implementation

### Main Chat Interface (`ChatPage.tsx`)

**Core Features**:
1. **Category Selection Dialog**: 4 categories with descriptions
2. **Real-time Chat Interface**: Message bubbles, typing indicators
3. **Response Processing**: Markdown rendering, code highlighting
4. **Incident Management**: Create tickets, track resolutions

#### Category Selection Logic:
```typescript
const categoryOptions = [
    {
        id: 'general',
        title: 'General Question',
        description: 'Educational queries, tutorials, best practices',
        icon: '📚',
        color: '#2196F3'
    },
    {
        id: 'hsbc_internal', 
        title: 'HSBC Internal Issue',
        description: 'Server problems, API errors, technical issues',
        icon: '🏦', 
        color: '#DB0011'  // HSBC Red
    },
    {
        id: 'monitoring',
        title: 'System Monitoring', 
        description: 'Splunk logs, Ansible data, performance metrics',
        icon: '📊',
        color: '#FF9800'
    },
    {
        id: 'knowledge_base',
        title: 'Internal Knowledge',
        description: 'Documentation, procedures, team knowledge', 
        icon: '📖',
        color: '#4CAF50'
    }
];
```

#### Message Sending Flow:
```typescript
const sendMessage = async () => {
    // 🎯 Ensure category is selected for new conversations
    if (!selectedCategory && !currentConversationId) {
        setShowCategorySelector(true);
        return;
    }
    
    // 📤 Send message with category context
    const messageData = {
        message: inputMessage,
        category: selectedCategory,
        conversation_id: currentConversationId || undefined,
        server_name: extractServerName(inputMessage),
        correlation_id: extractCorrelationId(inputMessage)
    };
    
    try {
        const response = await apiService.sendMessage(messageData);
        
        // 🎨 Display bot response with formatting
        displayBotResponse(response);
        
        // 💾 Save conversation state
        if (response.conversation_id) {
            setCurrentConversationId(response.conversation_id);
        }
    } catch (error) {
        console.error('Message send error:', error);
    }
};
```

### API Communication (`api.ts`):

```typescript
class ApiService {
    private api: AxiosInstance;
    
    constructor() {
        this.api = axios.create({
            baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
            timeout: 30000
        });
        
        // 🔒 JWT token interceptor
        this.api.interceptors.request.use((config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });
    }
    
    // 💬 Send chat message
    async sendMessage(messageData: MessageRequest): Promise<MessageResponse> {
        const response = await this.api.post('/api/chat/send-message', messageData);
        return response.data;
    }
    
    // 👤 User authentication
    async login(username: string, password: string): Promise<LoginResponse> {
        const response = await this.api.post('/api/auth/login', {
            username,
            password
        });
        return response.data;
    }
}
```

---

## 🔧 Configuration Files

### Backend Environment (`.env`):
```bash
# 🗄️ Database Configuration
DATABASE_URL=mysql+pymysql://hsbc_user:secure_password@localhost:3306/hsbc_autoassist

# 🔐 Security Settings  
SECRET_KEY=your-32-character-jwt-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 🧠 AI Services
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
OPENAI_MODEL=gpt-4

# 🦙 Ollama Fallback (Optional)
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
USE_OLLAMA_FALLBACK=true

# 🔌 External APIs
SPLUNK_API_URL=https://your-splunk-instance.com
SPLUNK_API_TOKEN=your-splunk-token
ANSIBLE_API_URL=https://your-ansible-tower.com  
ANSIBLE_API_TOKEN=your-ansible-token

# 🏢 Corporate Settings
COMPANY_NAME=HSBC
DEPARTMENT=DC Automation Support Team
BOT_NAME=DC AutoAssist
```

### Frontend Environment (`.env`):
```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_COMPANY_NAME=HSBC
REACT_APP_BOT_NAME=DC AutoAssist
```

### Python Dependencies (`requirements.txt`):
```txt
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
cryptography==41.0.7
```

### Node.js Dependencies (`package.json`):
```json
{
  "name": "hsbc-autoassist-frontend",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0", 
    "typescript": "^4.9.5",
    "@mui/material": "^5.14.18",
    "@mui/icons-material": "^5.14.18",
    "@emotion/react": "^11.11.1",
    "@emotion/styled": "^11.11.0",
    "axios": "^1.6.2",
    "react-router-dom": "^6.18.0",
    "react-markdown": "^9.0.1"
  }
}
```

---

## 🚀 Quick Deployment Steps

### 1. Database Setup:
```sql
-- Create database and user
CREATE DATABASE hsbc_autoassist;
CREATE USER 'hsbc_user'@'localhost' IDENTIFIED BY 'secure_password';
GRANT ALL PRIVILEGES ON hsbc_autoassist.* TO 'hsbc_user'@'localhost';

-- Run table creation scripts (from schema above)
-- Insert sample data for testing
```

### 2. Backend Deployment:
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run application
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Frontend Deployment:
```bash
# Install Node.js dependencies
npm install

# Configure API endpoint
echo "REACT_APP_API_URL=http://your-backend-server:8000" > .env

# Build and serve
npm run build
npx serve -s build -l 3000
```

---

## 📊 Sample API Requests & Responses

### 1. Educational Query:
**Request**:
```json
POST /api/chat/send-message
{
  "message": "What is REST API?",
  "category": "general"
}
```

**Response**:
```json
{
  "message": "📚 **Educational Response**\n\n# REST API Fundamentals\n\nREST (Representational State Transfer) is an architectural style for designing networked applications...",
  "conversation_id": 123,
  "ai_service_used": "openai_educational", 
  "data_sources": ["OpenAI GPT-4", "Educational Knowledge"],
  "suggestions": ["Learn about HTTP methods", "API authentication patterns"],
  "processing_time": "2.3s"
}
```

### 2. Technical Issue (LLM-Enhanced Analysis):
**Request**:
```json
POST /api/chat/send-message
{
  "message": "gb-api-01 showing 401 error with correlation ID CID12345",
  "category": "hsbc_internal", 
  "server_name": "gb-api-01",
  "correlation_id": "CID12345"
}
```

**Response**:
```json
{
  "message": "🔧 **Technical Analysis & Resolution**\n\n## Root Cause Analysis\nBased on analysis of multiple data sources, the 401 authentication error on gb-api-01 is caused by JWT token expiration combined with recent security policy changes.\n\n## Comprehensive Resolution Steps\n\n### Immediate Actions (Priority: High)\n1. **Verify Token Status**\n   - Check current JWT token expiration: `curl -H 'Authorization: Bearer [token]' /api/auth/verify`\n   - Expected result: Token expired at 14:30 UTC\n\n2. **Generate New Token**\n   - Use HSBC token service: `/api/auth/refresh`\n   - Update application configuration with new token\n\n3. **Validate Resolution**\n   - Test API endpoint with new token\n   - Monitor Splunk logs for correlation ID CID12345\n\n### Preventive Measures\n- Implement token auto-refresh mechanism\n- Set up monitoring alerts for token expiration\n- Review authentication flow documentation\n\n## Supporting Evidence\n- **Splunk Logs**: 15 similar 401 errors in last hour\n- **Historical Data**: Same issue resolved previously with token refresh\n- **Server Health**: gb-api-01 operational, authentication service healthy\n\n**Estimated Resolution Time**: 10-15 minutes",
  "ai_service_used": "openai_technical_analysis",
  "data_sources": ["csv_knowledge", "hsbc_apis", "splunk_logs", "ansible_data"],
  "server_name": "gb-api-01",
  "analysis_type": "technical_troubleshooting",
  "confidence_level": "high",
  "incident_required": false,
  "server_region": "UK",
  "issue_priority": "high"
}
```

---

## 💡 Key Implementation Points for Your Team

### 🎯 **Why Category-First Approach**:
1. **Intelligent Routing**: Different categories need different AI processing
2. **Resource Optimization**: Avoid expensive API calls for simple queries  
3. **Context Preservation**: Category provides essential context for AI
4. **User Experience**: Clear expectations for response type

### 🧠 **Multi-tier AI Strategy with Data Integration**:
1. **Data Collection Phase**: Gather information from all relevant sources
   - CSV knowledge base (historical solutions)
   - Splunk APIs (log analysis)
   - Internal HSBC APIs (real-time status)
   - Confluence (documentation)
   - Ansible (automation data)

2. **LLM Analysis Phase**: Send consolidated data to AI for intelligent analysis
   - **Primary**: OpenAI GPT-4 for comprehensive technical analysis
   - **Fallback**: Ollama Llama 3.2 for when OpenAI unavailable
   - **Final**: Built-in responses for guaranteed availability

3. **Response Generation**: LLM creates contextual, actionable responses
   - Root cause analysis
   - Step-by-step troubleshooting
   - Prevention recommendations
   - Priority assessment

### 📊 **Enhanced Knowledge Integration Design**:
1. **Multi-source Data Collection**: Systematic gathering from all knowledge sources
2. **Structured Context Preparation**: Format data optimally for LLM analysis
3. **Intelligent Correlation**: LLM identifies patterns across different data sources
4. **Consolidated Response**: Single, comprehensive answer combining all insights
5. **Continuous Learning**: System improves based on resolution outcomes

### 🔒 **Security Considerations**:
1. **JWT Authentication**: Stateless, secure token-based auth
2. **Environment Variables**: Sensitive data not in code
3. **Input Validation**: Prevents injection attacks
4. **CORS Configuration**: Controlled cross-origin access

---

This guide provides your team with all essential implementation details while being concise enough for corporate environments with code access restrictions. The modular design allows for gradual implementation and customization based on your specific HSBC requirements! 🎉