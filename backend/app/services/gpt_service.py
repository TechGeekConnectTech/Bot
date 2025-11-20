import openai
from openai import OpenAI
import json
import requests
import logging
from typing import Dict, List, Optional, Any
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.chat import QueryResolution

logger = logging.getLogger(__name__)
from app.services.api_integrations import SplunkService, AnsibleService
from app.services.csv_knowledge_service import CSVKnowledgeService
from app.services.enhanced_knowledge_service import EnhancedKnowledgeService

class GPTService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.splunk_service = SplunkService()
        self.ansible_service = AnsibleService()
        self.csv_knowledge = CSVKnowledgeService()
        self.enhanced_knowledge = EnhancedKnowledgeService()
        self.ollama_url = settings.OLLAMA_API_URL
        self.ollama_model = settings.OLLAMA_MODEL
        self.use_ollama_fallback = settings.USE_OLLAMA_FALLBACK
    
    async def process_user_query(
        self, 
        message: str, 
        server_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        category: Optional[str] = None,
        user_context: Dict[str, Any] = None,
        conversation_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process user query using CSV knowledge base first, then external APIs
        """
        try:
            # Add debug logging for all incoming queries
            logger.info(f"🚀 Processing query - Message: '{message[:100]}...', Category: '{category}', Server: '{server_name}', User: {user_context.get('username', 'Unknown') if user_context else 'No context'}")
            
            # Handle category-based routing first (highest priority)
            if category:
                logger.info(f"✅ Category provided: '{category}' - routing to category handler")
                response = await self._handle_category_based_query(message, category, server_name, correlation_id, user_context)
                # Ensure category is in metadata
                if 'metadata' not in response:
                    response['metadata'] = {}
                response['metadata']['category'] = category
                return response
            
            # Quick check for simple greetings and casual messages (only non-educational ones)
            simple_response = self._handle_simple_messages(message, user_context, category_provided=False)
            if simple_response:
                return simple_response
            
            # Check if this is actually a technical issue before deep searching
            if not self._has_technical_issue_context(message):
                # This seems like a general question, provide informational response
                return {
                    "message": f"Hello {user_context.get('full_name', 'there')}! 👋\n\nI'm here to help with both general questions and technical troubleshooting.\n\n**For General Information:**\nFeel free to ask about APIs, authentication, databases, or development concepts like:\n• \"What is REST API?\"\n• \"How does JWT authentication work?\"\n• \"What are HTTP status codes?\"\n\n**For Technical Issues:**\nPlease provide specific details like:\n• Server names (e.g., gb-api-01, cn-db-server, hk-web-prod)\n• Error codes (401, 403, 500, etc.)\n• Correlation IDs or specific error messages\n\n**Examples:**\n• \"gb-api-01 giving 401 error\" → I'll provide troubleshooting steps\n• \"What is API?\" → I'll explain the concept\n\nHow can I assist you today?",
                    "suggestions": [
                        "Ask \"What is API?\" for educational info",
                        "Report technical issues with server details", 
                        "Learn about authentication methods",
                        "Get help with HTTP status codes"
                    ],
                    "incident_required": False,
                    "ai_service_used": "guidance_response",
                    "data_sources": ["Assistant Logic"]
                }
            
            # Step 1: Search all knowledge sources for technical issues
            processing_updates = ["🔍 Searching knowledge base (CSV, Text, Confluence)..."]
            knowledge_results = await self._search_enhanced_knowledge_base(message, server_name, user_context)
            
            # Check if insufficient information was provided
            if knowledge_results.get('insufficient_info'):
                processing_updates.append("⚠️ Insufficient information for troubleshooting")
                processing_updates.append("❓ Asking user for additional details...")
                
                missing_details = []
                if not self._is_hsbc_server_reference(message) and not server_name:
                    missing_details.append("server name or ID (e.g., gb-api-01, cn-db-server, hk-web-prod)")
                if not any(code in message for code in ['401', '403', '404', '500', '502', '503', '504', '400', '422', '423']):
                    missing_details.append("error code")
                if 'correlation' not in message.lower() and 'cid' not in message.lower() and not correlation_id:
                    missing_details.append("correlation ID (if available)")
                
                response = {
                    "message": f"I need more details to troubleshoot your issue effectively. I couldn't find sufficient information in any of our knowledge sources.\n\n**Please provide:**\n",
                    "suggestions": [],
                    "incident_required": False,
                    "processing_updates": processing_updates,
                    "ai_service_used": "insufficient_info_handler"
                }
                
                for detail in missing_details:
                    response["message"] += f"• {detail.title()}\n"
                    response["suggestions"].append(f"Provide {detail}")
                
                response["message"] += f"\n**Additional helpful information:**\n"
                response["message"] += f"• Specific error message or description\n"
                response["message"] += f"• When the issue started\n"
                response["message"] += f"• Any recent changes made\n\n"
                response["message"] += f"With these details, I can better search our knowledge base and external monitoring systems to provide accurate troubleshooting steps."
                
                response["suggestions"].extend([
                    "Share specific error messages",
                    "Mention when issue started",
                    "Describe recent changes"
                ])
                
                return response
            
            if knowledge_results['found_match']:
                processing_updates.append("✅ Found matching entry in knowledge base")
                processing_updates.append("📋 Preparing response from existing data...")
                
                response = await self._generate_knowledge_based_response(
                    message, knowledge_results, user_context, processing_updates
                )
                response['processing_updates'] = processing_updates
                # Add category to metadata if provided
                if category:
                    if 'metadata' not in response:
                        response['metadata'] = {}
                    response['metadata']['category'] = category
                return response
            elif knowledge_results.get('common_error_guidance'):
                processing_updates.append("📚 Found general guidance for this error code")
                processing_updates.append("💡 Providing common troubleshooting steps...")
                
                response = self._generate_common_error_response(
                    message, knowledge_results['common_error_guidance'], user_context, processing_updates
                )
                response['processing_updates'] = processing_updates
                # Add category to metadata if provided
                if category:
                    if 'metadata' not in response:
                        response['metadata'] = {}
                    response['metadata']['category'] = category
                return response
            else:
                processing_updates.append("❌ No exact match found in knowledge base")
                processing_updates.append("🔍 Searching for similar issues...")
                
                # Check if CSV search returned similar issues
                similar_issues = knowledge_results.get('similar_issues', [])
                
                # If no similar issues from CSV search, do broader search
                if not similar_issues:
                    similar_issues = await self._find_similar_csv_issues(message, server_name)
                
                if similar_issues:
                    processing_updates.append(f"📊 Found {len(similar_issues)} similar issues")
                    
                    # If we have similar issues for the same server, provide those as suggestions
                    if server_name and any(issue.get('server_name', '').lower() == server_name.lower() for issue in similar_issues):
                        processing_updates.append("✅ Found issues for this server - providing suggestions")
                        
                        response = await self._generate_similar_issues_response(
                            message, similar_issues, user_context, processing_updates, server_name
                        )
                        response['processing_updates'] = processing_updates
                        # Add category to metadata if provided
                        if category:
                            if 'metadata' not in response:
                                response['metadata'] = {}
                            response['metadata']['category'] = category
                        return response
            
            # Step 2: If no CSV match, proceed with real-time analysis
            processing_updates.append("🤖 Analyzing query with AI...")
            query_analysis = await self._analyze_query(message, server_name, correlation_id)
            
            # Step 3: Gather external data if needed
            processing_updates.append("🌐 Checking external data sources...")
            external_data = await self._gather_external_data(query_analysis, processing_updates)
            
            # Check if external sources couldn't find the requested server/correlation
            if (server_name and not external_data.get('splunk_data') and not external_data.get('ansible_data')):
                processing_updates.append(f"⚠️ Could not find server '{server_name}' in monitoring systems")
            if (correlation_id and not any(correlation_id in str(data) for data in external_data.values() if data)):
                processing_updates.append(f"⚠️ Could not find correlation ID '{correlation_id}' in logs")
            
            # Step 4: Generate AI response
            processing_updates.append("💭 Generating intelligent response...")
            
            # Check if this is an informational question
            informational_patterns = [
                'help', 'what can you', 'how can you', 'what do you', 'tell me about',
                'what are your', 'what services', 'how do you work', 'what is your purpose',
                'capabilities', 'features', 'functionality', 'what help you provide'
            ]
            
            is_informational_query = any(pattern in message.lower() for pattern in informational_patterns)
            
            # Check if we have no data from any source
            no_knowledge_data = not knowledge_results.get('found_match', False)
            no_external_data = not any(external_data.values())
            no_similar_issues = not knowledge_results.get('similar_issues', [])
            
            # Only ask for more details if this appears to be a technical issue report
            if no_knowledge_data and no_external_data and no_similar_issues and not is_informational_query:
                # Check if this looks like a technical issue that needs more details
                technical_indicators = ['error', 'issue', 'problem', 'broken', 'failing', 'not working', 'down']
                seems_like_technical_issue = any(indicator in message.lower() for indicator in technical_indicators)
                
                if seems_like_technical_issue:
                    # No information found in any source - ask for more details
                    processing_updates.append("❌ No information found in any data source")
                    processing_updates.append("❓ Requesting additional details from user")
                    
                    response = {
                        "message": f"I searched our knowledge base, monitoring systems, and external data sources but couldn't find information about your issue.\n\n**To help you better, please provide:**\n\n• **Specific server name** (e.g., srv-api-01, srv-db-02)\n• **Complete error message** or error code\n• **Correlation ID** if available\n• **When the issue started** and frequency\n• **What you were trying to do** when the error occurred\n\n**Additional context that helps:**\n• Recent deployments or changes\n• Affected users or services\n• Error patterns or timing\n\nWith these details, I can provide accurate troubleshooting steps and check our monitoring systems effectively.",
                        "suggestions": [
                            "Provide exact server name",
                            "Share complete error message", 
                            "Include correlation ID",
                            "Describe when issue started",
                            "Mention recent changes"
                        ],
                        "incident_required": False,
                        "processing_updates": processing_updates,
                        "ai_service_used": "no_data_found"
                    }
                    return response
            
            response = await self._generate_ai_response(
                message, query_analysis, external_data, user_context, knowledge_results.get('similar_issues', [])
            )
            # Ensure category is in metadata if provided
            if category:
                if 'metadata' not in response:
                    response['metadata'] = {}
                response['metadata']['category'] = category
            
            # Step 5: Save new issue to knowledge base for future reference
            # Only save technical issues, not general information questions
            is_general_question = any(pattern in message.lower() for pattern in [
                'how to install', 'how to setup', 'how do i', 'what is', 'explain', 'guide for', 'tutorial'
            ])
            
            if query_analysis.get('query_type') != 'other' and not is_general_question:
                processing_updates.append("💾 Saving issue to knowledge base...")
                await self._save_to_knowledge_base(
                    message, query_analysis, server_name, correlation_id, user_context
                )
            
            response['processing_updates'] = processing_updates
            return response
            
        except Exception as e:
            print(f"Error in process_user_query: {e}")
            # Provide intelligent fallback response without AI
            return await self._generate_fallback_response(message, server_name, correlation_id, user_context)
    
    async def _analyze_query(self, message: str, server_name: str, correlation_id: str) -> Dict[str, Any]:
        """
        Analyze user query to determine type and extract key information
        """
        system_prompt = f"""
        You are DC AutoAssist, an AI assistant for the DC Automation Support Team.
        Analyze the user's query and categorize it into one of these types:
        - auth_issue: Authentication or authorization problems
        - payload_issue: Request payload or data format problems  
        - resource_lock: Resource locking or concurrency issues
        - performance_issue: Performance or timeout problems
        - configuration_issue: Configuration or setup problems
        - other: General questions or other issues
        
        Extract key information and return as JSON with:
        - query_type: One of the categories above
        - priority: low, medium, high, critical
        - keywords: List of important terms
        - requires_data_lookup: boolean if external API data is needed
        - suggested_actions: List of potential troubleshooting steps
        """
        
        try:
            if self.client and settings.OPENAI_API_KEY:
                response = self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Query: {message}\nServer: {server_name or 'Not provided'}\nCorrelation ID: {correlation_id or 'Not provided'}"}
                    ],
                    temperature=0.1,
                    response_format={"type": "json_object"}
                )
                
                return json.loads(response.choices[0].message.content)
            elif self.use_ollama_fallback:
                # Use Ollama as fallback
                return await self._analyze_query_with_ollama(message, server_name, correlation_id, system_prompt)
            else:
                raise Exception("No AI service available")
            
        except Exception as e:
            # Intelligent fallback analysis
            message_lower = message.lower()
            
            # Determine query type based on keywords
            if any(term in message_lower for term in ['auth', 'login', 'token', '401', '403']):
                query_type = "auth_issue"
            elif any(term in message_lower for term in ['payload', 'json', 'data', '400']):
                query_type = "payload_issue" 
            elif any(term in message_lower for term in ['timeout', 'slow', '500', '502', '503', '504']):
                query_type = "performance_issue"
            elif any(term in message_lower for term in ['config', 'setup', 'connection']):
                query_type = "configuration_issue"
            elif any(term in message_lower for term in ['lock', 'resource', 'concurrent']):
                query_type = "resource_lock"
            else:
                query_type = "other"
            
            # Set priority based on error codes and keywords
            if any(term in message_lower for term in ['critical', 'urgent', '500', '502', 'down']):
                priority = "high"
            elif any(term in message_lower for term in ['slow', 'timeout', 'performance']):
                priority = "medium"
            else:
                priority = "low"
            
            return {
                "query_type": query_type,
                "priority": priority,
                "keywords": [word for word in message.split()[:8] if len(word) > 2],
                "requires_data_lookup": bool(server_name or correlation_id),
                "suggested_actions": self._get_suggested_actions(query_type)
            }
    
    async def _gather_external_data(self, query_analysis: Dict[str, Any], processing_updates: List[str] = None) -> Dict[str, Any]:
        """
        Gather relevant data from external sources based on query analysis
        """
        external_data = {
            "splunk_data": None,
            "ansible_data": None,
            "data_sources_used": []
        }
        
        if not query_analysis.get("requires_data_lookup", False):
            return external_data
        
        try:
            # Query Splunk for logs and events
            if query_analysis["query_type"] in ["auth_issue", "payload_issue", "performance_issue"]:
                if processing_updates:
                    processing_updates.append("📊 Querying Splunk for relevant logs...")
                splunk_data = await self.splunk_service.search_logs(
                    query_analysis.get("keywords", []),
                    query_analysis["query_type"]
                )
                if splunk_data:
                    external_data["splunk_data"] = splunk_data
                    external_data["data_sources_used"].append("Splunk")
                    if processing_updates:
                        processing_updates.append("✅ Retrieved Splunk log data")
                elif processing_updates:
                    processing_updates.append("❌ No relevant Splunk data found")
            
            # Query Ansible for configuration and deployment info
            if query_analysis["query_type"] in ["configuration_issue", "resource_lock"]:
                if processing_updates:
                    processing_updates.append("🔧 Checking Ansible for system information...")
                ansible_data = await self.ansible_service.get_system_info(
                    query_analysis.get("keywords", [])
                )
                if ansible_data:
                    external_data["ansible_data"] = ansible_data
                    external_data["data_sources_used"].append("Ansible")
                    if processing_updates:
                        processing_updates.append("✅ Retrieved Ansible system data")
                elif processing_updates:
                    processing_updates.append("❌ No relevant Ansible data found")
                    
        except Exception as e:
            print(f"Error gathering external data: {e}")
            if processing_updates:
                processing_updates.append("⚠️ Error accessing external data sources")
        
        return external_data
    
    async def _generate_ai_response(
        self, 
        original_message: str, 
        query_analysis: Dict[str, Any], 
        external_data: Dict[str, Any],
        user_context: Dict[str, Any],
        similar_csv_issues: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate comprehensive response using GPT-4o
        """
        system_prompt = f"""
        You are DC AutoAssist, an AI-powered support assistant for the HSBC DC Automation Support Team.
        
        Your role:
        - Provide expert technical support for API issues
        - Analyze problems using available data sources
        - Offer clear, actionable solutions
        - Maintain professional, helpful tone
        - Escalate complex issues when needed
        
        Context:
        - User: {user_context.get('username', 'Unknown')} from {user_context.get('department', 'Unknown')}
        - Query Type: {query_analysis.get('query_type', 'unknown')}
        - Priority: {query_analysis.get('priority', 'medium')}
        - Data Sources: {', '.join(external_data.get('data_sources_used', ['None']))}
        
        Guidelines:
        1. Be concise but thorough
        2. Use technical terms appropriately
        3. Provide step-by-step solutions when possible
        4. Reference data sources when available
        5. Suggest escalation for critical or unresolvable issues
        """
        
        # Prepare context with external data
        context_message = f"""
        User Query: {original_message}
        
        Analysis Results: {json.dumps(query_analysis, indent=2)}
        
        External Data Available:
        {json.dumps(external_data, indent=2)}
        
        Please provide a helpful response with:
        1. Problem diagnosis
        2. Root cause analysis (if determinable)
        3. Step-by-step resolution steps
        4. Prevention recommendations
        5. When to escalate
        """
        
        try:
            ai_response = None
            ai_service_used = "fallback"
            
            if self.client and settings.OPENAI_API_KEY:
                try:
                    response = self.client.chat.completions.create(
                        model=settings.OPENAI_MODEL,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": context_message}
                        ],
                        temperature=0.3,
                        max_tokens=1000
                    )
                    ai_response = response.choices[0].message.content
                    ai_service_used = "openai"
                except Exception as openai_error:
                    print(f"OpenAI error: {openai_error}")
                    if self.use_ollama_fallback:
                        ai_response = await self._generate_ai_response_with_ollama(
                            system_prompt, context_message
                        )
                        ai_service_used = "ollama"
            elif self.use_ollama_fallback:
                ai_response = await self._generate_ai_response_with_ollama(
                    system_prompt, context_message
                )
                ai_service_used = "ollama"
            
            if ai_response:
                # Generate suggestions based on query type
                suggestions = self._generate_suggestions(query_analysis)
                
                # Only require incident for truly critical issues
                incident_required = query_analysis.get("priority") == "critical"
                
                return {
                    "message": ai_response,
                    "suggestions": suggestions,
                    "data_sources": external_data.get("data_sources_used", []),
                    "incident_required": incident_required,
                    "ai_service_used": ai_service_used,
                    "metadata": {
                        "query_analysis": query_analysis,
                        "external_data_summary": self._summarize_external_data(external_data)
                    }
                }
            else:
                raise Exception("No AI service available")
            
        except Exception as e:
            # Fallback to rule-based response
            return await self._generate_fallback_response(original_message, None, None, user_context, query_analysis)
    
    def _generate_suggestions(self, query_analysis: Dict[str, Any]) -> List[str]:
        """
        Generate contextual suggestions based on query type
        """
        query_type = query_analysis.get("query_type", "other")
        
        suggestion_map = {
            "auth_issue": [
                "Check API key validity and permissions",
                "Verify token expiration time",
                "Review authentication logs",
                "Confirm service account access"
            ],
            "payload_issue": [
                "Validate JSON payload format",
                "Check required fields and data types",
                "Review API documentation",
                "Test with minimal payload"
            ],
            "resource_lock": [
                "Check for concurrent processes",
                "Review system resource usage",
                "Identify long-running operations",
                "Consider increasing timeout values"
            ],
            "performance_issue": [
                "Monitor system performance metrics",
                "Check database connection pool",
                "Review recent deployments",
                "Analyze response time trends"
            ],
            "configuration_issue": [
                "Verify configuration files",
                "Check environment variables",
                "Review recent configuration changes",
                "Validate service dependencies"
            ]
        }
        
        return suggestion_map.get(query_type, [
            "Provide more specific details",
            "Check system logs",
            "Contact support if issue persists"
        ])
    
    def _summarize_external_data(self, external_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Create summary of external data for metadata
        """
        summary = {}
        
        if external_data.get("splunk_data"):
            summary["splunk"] = f"Found {len(external_data['splunk_data'].get('events', []))} relevant log events"
        
        if external_data.get("ansible_data"):
            summary["ansible"] = f"Retrieved system configuration and deployment information"
        
        return summary
    
    async def _generate_fallback_response(
        self, 
        message: str, 
        server_name: Optional[str] = None, 
        correlation_id: Optional[str] = None,
        user_context: Dict[str, Any] = None,
        query_analysis: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate intelligent fallback responses using rule-based logic
        """
        message_lower = message.lower()
        user_name = user_context.get('full_name', user_context.get('username', 'there')) if user_context else 'there'
        
        # Greeting responses
        if any(greeting in message_lower for greeting in ['hi', 'hello', 'hey', 'good morning', 'good afternoon']):
            return {
                "message": f"Hello {user_name}! 👋 Welcome to DC AutoAssist. I'm here to help you with API support and troubleshooting.\n\nSimply describe your issue and I'll help you resolve it. How can I assist you today?",
                "suggestions": [
                    "Check API authentication status",
                    "Validate API payload format", 
                    "Monitor system performance",
                    "Review recent error logs"
                ],
                "incident_required": False
            }
        
        # Authentication issues
        if any(term in message_lower for term in ['auth', 'authenticate', 'login', 'token', 'permission', 'access denied', '401', '403']):
            return {
                "message": f"I can help you troubleshoot authentication issues. Based on your query, here are the recommended steps:\n\n**Authentication Troubleshooting:**\n\n1. **Verify API Credentials**\n   - Check if your API key is valid and not expired\n   - Ensure correct username/password combination\n\n2. **Token Validation**\n   - Verify JWT token format and expiration\n   - Check token scope and permissions\n\n3. **Common Solutions**\n   - Regenerate API token if expired\n   - Verify service account permissions\n   - Check authentication headers format\n\n4. **Server-Specific Issues**\n   {f'- Server: {server_name}' if server_name else '- Provide server name for specific diagnostics'}\n   {f'- Correlation ID: {correlation_id}' if correlation_id else '- Include correlation ID for request tracking'}\n\nWould you like me to help you check any specific authentication component?",
                "suggestions": [
                    "Regenerate API token",
                    "Check service account permissions",
                    "Validate token expiration",
                    "Review authentication logs"
                ],
                "incident_required": False
            }
        
        # Payload/data issues  
        if any(term in message_lower for term in ['payload', 'json', 'xml', 'data', 'format', 'validation', '400', 'bad request']):
            return {
                "message": f"I'll help you resolve payload and data format issues. Here's a systematic approach:\n\n**Payload Troubleshooting:**\n\n1. **Data Format Validation**\n   - Ensure JSON/XML syntax is correct\n   - Verify all required fields are present\n   - Check data types match API specifications\n\n2. **Common Payload Issues**\n   - Missing or null required fields\n   - Incorrect data types (string vs number)\n   - Invalid date/time formats\n   - Special characters causing encoding issues\n\n3. **Debugging Steps**\n   - Use JSON validator tools\n   - Compare with API documentation\n   - Test with minimal payload first\n   - Check content-type headers\n\n4. **Request Details**\n   {f'- Server: {server_name}' if server_name else '- Specify target server for validation'}\n   {f'- Correlation ID: {correlation_id}' if correlation_id else '- Provide correlation ID for tracking'}\n\nCan you share the specific error message or payload structure you're working with?",
                "suggestions": [
                    "Validate JSON syntax",
                    "Check required fields",
                    "Verify data types",
                    "Test with minimal payload"
                ],
                "incident_required": False
            }
        
        # Performance/timeout issues
        if any(term in message_lower for term in ['timeout', 'slow', 'performance', 'latency', '500', '502', '503', '504']):
            return {
                "message": f"Let me help you diagnose performance and timeout issues:\n\n**Performance Troubleshooting:**\n\n1. **Timeout Analysis**\n   - Check if timeouts are consistent or intermittent\n   - Review timeout configuration values\n   - Monitor network connectivity\n\n2. **System Performance**\n   - CPU and memory usage on target servers\n   - Database connection pool status\n   - Network latency between services\n\n3. **Common Causes**\n   - Database query performance\n   - Large payload processing\n   - External service dependencies\n   - Resource contention\n\n4. **Investigation Steps**\n   - Check server logs for error patterns\n   - Monitor resource utilization\n   - Test during different time periods\n   - Verify recent deployments or changes\n\n{f'**Server Context:** {server_name}' if server_name else '**Note:** Providing server name helps with specific diagnostics'}\n{f'**Correlation ID:** {correlation_id}' if correlation_id else '**Tip:** Include correlation ID for request tracing'}\n\nWhat specific performance symptoms are you experiencing?",
                "suggestions": [
                    "Monitor server resources",
                    "Check database performance",
                    "Review timeout configurations",
                    "Analyze recent deployments"
                ],
                "incident_required": False
            }
        
        # Configuration issues
        if any(term in message_lower for term in ['config', 'setup', 'environment', 'deployment', 'connection']):
            return {
                "message": f"I'll guide you through configuration troubleshooting:\n\n**Configuration Analysis:**\n\n1. **Environment Settings**\n   - Verify environment variables\n   - Check configuration file syntax\n   - Validate service endpoints\n\n2. **Connection Issues**\n   - Test network connectivity\n   - Verify firewall rules\n   - Check DNS resolution\n\n3. **Service Configuration**\n   - Review service dependencies\n   - Validate database connections\n   - Check SSL/TLS certificates\n\n4. **Deployment Verification**\n   - Confirm latest deployment status\n   - Check configuration version consistency\n   - Validate service startup logs\n\n{f'**Target Server:** {server_name}' if server_name else '**Recommendation:** Specify server for targeted analysis'}\n\nWhat type of configuration issue are you experiencing?",
                "suggestions": [
                    "Verify environment variables",
                    "Check service connections",
                    "Validate configuration files",
                    "Review deployment status"
                ],
                "incident_required": False
            }
        
        # Generic helpful response
        return {
            "message": f"Thank you for contacting DC AutoAssist! I'm here to help you with API support and troubleshooting.\n\nI can assist you with authentication issues, payload problems, performance issues, configuration problems, and more.\n\n**To help you better, please:**\n- Describe the specific issue you're experiencing\n- Include error messages if available\n{f'- Server: {server_name}' if server_name else '- Mention the server name'}\n{f'- Correlation ID: {correlation_id}' if correlation_id else '- Provide correlation ID if available'}\n\nWhat can I help you troubleshoot today?",
            "suggestions": [
                "Describe your specific issue",
                "Share any error messages",
                "Provide server and correlation details",
                "Ask about authentication problems"
            ],
            "incident_required": False
        }
    
    def _handle_simple_messages(self, message: str, user_context: Dict[str, Any] = None, category_provided: bool = True) -> Optional[Dict[str, Any]]:
        """
        Handle simple greetings and casual messages without complex analysis
        """
        message_lower = message.lower().strip()
        user_name = user_context.get('full_name', user_context.get('username', 'there')) if user_context else 'there'
        
        # Simple greetings
        if message_lower in ['hi', 'hello', 'hey', 'hi there', 'hello there']:
            return {
                "message": f"Hi {user_name}! 👋 Welcome to DC AutoAssist. I'm here to help you with API support and troubleshooting. What can I assist you with today?",
                "suggestions": [
                    "Ask about API authentication issues",
                    "Report payload validation errors", 
                    "Check system performance problems",
                    "Get help with configuration issues"
                ],
                "incident_required": False,
                "ai_service_used": "simple_response"
            }
        
        # More detailed greetings
        if any(greeting in message_lower for greeting in ['good morning', 'good afternoon', 'good evening']):
            return {
                "message": f"Good day, {user_name}! Welcome to DC AutoAssist. I'm ready to help you resolve any API or system issues you're experiencing. How can I help you today?",
                "suggestions": [
                    "Describe your current issue",
                    "Share error messages you're seeing",
                    "Ask about system status",
                    "Get troubleshooting guidance"
                ],
                "incident_required": False,
                "ai_service_used": "simple_response"
            }
        
        # Thank you messages
        if message_lower in ['thanks', 'thank you', 'thanks!', 'thank you!', 'ty']:
            return {
                "message": f"You're very welcome, {user_name}! I'm glad I could help. If you need any further assistance with API issues or system troubleshooting, just let me know. Have a great day! 😊",
                "suggestions": [
                    "Ask another question",
                    "Report a new issue", 
                    "Check system status",
                    "Contact support team"
                ],
                "incident_required": False,
                "ai_service_used": "simple_response"
            }
        
        # Help requests - expanded to catch more variations
        help_patterns = [
            'help', 'help me', 'what can you do', 'what can you help with',
            'what help you provide', 'what services do you offer', 'how can you help',
            'what are your capabilities', 'what can you assist with', 'what do you do',
            'tell me about yourself', 'what is your purpose', 'how do you work'
        ]
        
        # General information/how-to questions - these should not be treated as technical issues
        how_to_patterns = [
            'how to install', 'how to setup', 'how to configure', 'how to use',
            'how do i install', 'how do i setup', 'how do i configure', 'how do i use',
            'what is python', 'what is docker', 'what is kubernetes', 'what is git',
            'what is api', 'what is rest', 'what is json', 'what is xml', 'what is http',
            'what is authentication', 'what is authorization', 'what is jwt', 'what is oauth',
            'what is ssl', 'what is tls', 'what is database', 'what is sql', 'what is nosql',
            'explain python', 'explain docker', 'explain kubernetes', 'explain api', 
            'explain rest', 'explain authentication', 'explain json', 'explain http',
            'guide for', 'tutorial for', 'steps to install', 'steps to setup',
            'definition of', 'meaning of', 'difference between'
        ]
        
        # Handle educational questions only when category is not provided
        if not category_provided and any(pattern in message_lower for pattern in how_to_patterns):
            return self._handle_general_information_question(message, user_context)
        
        if any(pattern in message_lower for pattern in help_patterns):
            return {
                "message": f"I'm DC AutoAssist, your technical support assistant! Here's how I can help you:\n\n🔧 **API Support:**\n• Authentication and authorization issues\n• Payload validation and format problems\n• Request/response troubleshooting\n\n⚡ **System Issues:**\n• Performance and timeout problems\n• Configuration and setup issues\n• Resource and connectivity problems\n\n📋 **Additional Services:**\n• Error message analysis\n• Step-by-step troubleshooting guides\n• Incident creation for complex issues\n\nSimply describe your issue and I'll provide targeted assistance!",
                "suggestions": [
                    "Tell me about your current problem",
                    "Share any error messages",
                    "Describe system behavior you're seeing",
                    "Ask about specific API endpoints"
                ],
                "incident_required": False,
                "ai_service_used": "simple_response"
            }
        
        # Only return None if this isn't a simple message
        return None
    
    def _is_hsbc_server_reference(self, message: str) -> bool:
        """
        Detect HSBC server naming patterns (country codes + descriptive names)
        """
        message_lower = message.lower()
        
        # HSBC country codes
        hsbc_country_codes = ['gb', 'cn', 'hk', 'vn', 'mx', 'us', 'ca', 'au', 'sg', 'my', 'in', 'ae', 'fr', 'de']
        
        # Check for country code patterns
        for country_code in hsbc_country_codes:
            if any(pattern in message_lower for pattern in [
                f'{country_code}-',
                f'{country_code}api',
                f'{country_code}db',
                f'{country_code}web',
                f'{country_code}app',
                f'{country_code}srv',
                f'server-{country_code}',
                f'host-{country_code}'
            ]):
                return True
        
        # Also check for generic server patterns
        server_patterns = [
            'server', 'srv', 'host', 'api-', 'db-', 'web-', 'app-',
            'service', 'endpoint', 'url', 'hostname'
        ]
        
        return any(pattern in message_lower for pattern in server_patterns)
    
    def _has_technical_issue_context(self, message: str) -> bool:
        """
        Determine if message describes a technical problem requiring troubleshooting
        """
        message_lower = message.lower()
        
        # Clear error indicators
        error_indicators = [
            'error', 'issue', 'problem', 'broken', 'failing', 'failed',
            'not working', 'timeout', 'connection', 'refused', 'denied',
            'slow', 'performance', 'crash', 'down', 'unavailable',
            'unauthorized', 'forbidden', 'internal server error',
            'bad request', 'not found', 'service unavailable'
        ]
        
        # HTTP status codes
        status_codes = ['400', '401', '403', '404', '500', '502', '503', '504']
        
        # Technical context indicators
        technical_indicators = [
            'response', 'request', 'payload', 'json', 'xml', 'ssl', 'certificate',
            'cors', 'database', 'query', 'connection', 'authentication',
            'correlation id', 'trace id', 'session', 'cache'
        ]
        
        # Check if message has error context
        has_errors = any(indicator in message_lower for indicator in error_indicators)
        has_status_code = any(code in message_lower for code in status_codes)
        has_technical_context = any(indicator in message_lower for indicator in technical_indicators)
        has_server_reference = self._is_hsbc_server_reference(message)
        
        # Technical issue if: (has errors OR status codes) AND (server reference OR technical context)
        return (has_errors or has_status_code) and (has_server_reference or has_technical_context)
    
    def _handle_general_information_question(self, message: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle general information and how-to questions
        """
        message_lower = message.lower()
        user_name = user_context.get('full_name', user_context.get('username', 'there')) if user_context else 'there'
        
        # API and technical concept questions
        if any(term in message_lower for term in ['what is api', 'api', 'what is rest', 'rest api']):
            return {
                "message": f"Hi {user_name}! I'd be happy to explain APIs for you.\n\n**What is an API?**\nAPI stands for Application Programming Interface. It's a set of protocols and tools that allows different software applications to communicate with each other.\n\n**Key API Concepts:**\n• **REST API**: Uses HTTP methods (GET, POST, PUT, DELETE) to interact with resources\n• **Endpoints**: Specific URLs where you send requests (e.g., `/api/users/123`)\n• **HTTP Methods**: GET (retrieve), POST (create), PUT (update), DELETE (remove)\n• **Status Codes**: 200 (success), 401 (unauthorized), 404 (not found), 500 (server error)\n• **Authentication**: Using API keys, JWT tokens, or OAuth for secure access\n\n**Example API Request:**\n```\nGET /api/users/123\nAuthorization: Bearer your-token-here\nContent-Type: application/json\n```\n\n**Common API Formats:**\n• JSON (JavaScript Object Notation) - most common\n• XML (eXtensible Markup Language)\n• Form data for file uploads\n\nNeed help with specific API implementation or troubleshooting API issues?",
                "suggestions": [
                    "Learn about API authentication",
                    "Understand HTTP status codes",
                    "Get help with API requests",
                    "Troubleshoot API errors"
                ],
                "incident_required": False,
                "ai_service_used": "educational_response"
            }
        
        # Authentication questions
        elif any(term in message_lower for term in ['what is authentication', 'what is auth', 'authentication', 'jwt', 'oauth']):
            return {
                "message": f"Hi {user_name}! Let me explain authentication concepts.\n\n**What is Authentication?**\nAuthentication verifies the identity of a user or system before granting access to resources.\n\n**Common Authentication Methods:**\n• **API Keys**: Simple token-based authentication\n• **JWT (JSON Web Tokens)**: Self-contained tokens with user claims\n• **OAuth 2.0**: Authorization framework for third-party access\n• **Basic Auth**: Username/password encoded in headers\n• **Bearer Tokens**: Token passed in Authorization header\n\n**JWT Token Structure:**\n```\nHeader.Payload.Signature\neyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\n```\n\n**Authentication vs Authorization:**\n• **Authentication**: \"Who are you?\" (login verification)\n• **Authorization**: \"What can you do?\" (permission checking)\n\n**Best Practices:**\n• Always use HTTPS for authentication\n• Implement token expiration\n• Store tokens securely (never in plain text)\n• Use refresh tokens for long sessions\n\nExperiencing authentication issues with a specific system?",
                "suggestions": [
                    "Report authentication errors",
                    "Learn about JWT tokens",
                    "Understand OAuth flow",
                    "Get help with API keys"
                ],
                "incident_required": False,
                "ai_service_used": "educational_response"
            }
        
        # Python installation questions
        elif any(term in message_lower for term in ['python', 'install python', 'setup python']):
            return {
                "message": f"Hi {user_name}! I'd be happy to help you with Python installation.\n\n**Python Installation Guide:**\n\n**For Windows:**\n1. Visit https://python.org/downloads/\n2. Download the latest Python installer\n3. Run the installer and check 'Add Python to PATH'\n4. Verify installation: `python --version`\n\n**For Linux (Ubuntu/Debian):**\n```bash\nsudo apt update\nsudo apt install python3 python3-pip\npython3 --version\n```\n\n**For macOS:**\n1. Install via Homebrew: `brew install python3`\n2. Or download from https://python.org/downloads/\n3. Verify: `python3 --version`\n\n**Next Steps:**\n• Install pip packages: `pip install package-name`\n• Set up virtual environment: `python -m venv myenv`\n• Activate environment: `source myenv/bin/activate` (Linux/Mac) or `myenv\\Scripts\\activate` (Windows)\n\nNeed help with specific Python tools or encountering installation errors? Let me know!",
                "suggestions": [
                    "Ask about specific Python version",
                    "Get help with pip installation", 
                    "Learn about virtual environments",
                    "Troubleshoot installation errors"
                ],
                "incident_required": False,
                "ai_service_used": "general_information"
            }
        
        # Docker questions
        elif any(term in message_lower for term in ['docker', 'install docker', 'setup docker']):
            return {
                "message": f"Hi {user_name}! Here's how to install Docker:\n\n**Docker Installation Guide:**\n\n**For Windows:**\n1. Download Docker Desktop from docker.com\n2. Run installer and enable WSL 2\n3. Restart computer\n4. Verify: `docker --version`\n\n**For Linux (Ubuntu):**\n```bash\nsudo apt update\nsudo apt install docker.io\nsudo systemctl start docker\nsudo usermod -aG docker $USER\ndocker --version\n```\n\n**For macOS:**\n1. Download Docker Desktop for Mac\n2. Install and start Docker Desktop\n3. Verify: `docker --version`\n\n**Basic Docker Commands:**\n• `docker run hello-world` - Test installation\n• `docker ps` - List running containers\n• `docker images` - List available images\n\nNeed help with specific Docker commands or containerization?",
                "suggestions": [
                    "Ask about Docker commands",
                    "Get help with Dockerfile creation",
                    "Learn about container management",
                    "Troubleshoot Docker issues"
                ],
                "incident_required": False,
                "ai_service_used": "general_information"
            }
        
        # Git questions
        elif any(term in message_lower for term in ['git', 'install git', 'setup git']):
            return {
                "message": f"Hi {user_name}! Here's your Git installation and setup guide:\n\n**Git Installation:**\n\n**For Windows:**\n1. Download from https://git-scm.com/downloads\n2. Run installer with recommended settings\n3. Verify: `git --version`\n\n**For Linux:**\n```bash\nsudo apt install git\ngit --version\n```\n\n**For macOS:**\n```bash\nbrew install git\n# or install Xcode Command Line Tools\n```\n\n**Initial Configuration:**\n```bash\ngit config --global user.name \"Your Name\"\ngit config --global user.email \"your.email@example.com\"\n```\n\n**Basic Git Commands:**\n• `git init` - Initialize repository\n• `git clone <url>` - Clone repository\n• `git add .` - Stage changes\n• `git commit -m \"message\"` - Commit changes\n• `git push` - Push to remote\n\nNeed help with specific Git workflows or commands?",
                "suggestions": [
                    "Learn Git branching",
                    "Get help with Git commands",
                    "Understand Git workflow",
                    "Troubleshoot Git issues"
                ],
                "incident_required": False,
                "ai_service_used": "general_information"
            }
        
        # General how-to questions
        else:
            return {
                "message": f"Hi {user_name}! I can help you with general information and how-to guides.\n\n**I can provide guidance on:**\n• Programming languages (Python, JavaScript, etc.)\n• Development tools (Git, Docker, etc.)\n• System administration basics\n• Software installation and setup\n• Best practices and tutorials\n\n**For specific technical issues with servers or applications, please provide:**\n• Server name (if applicable)\n• Error messages or codes\n• What you were trying to accomplish\n\nWhat specific topic would you like help with?",
                "suggestions": [
                    "Ask about Python installation",
                    "Get Docker setup guide",
                    "Learn Git basics",
                    "Get help with specific tools"
                ],
                "incident_required": False,
                "ai_service_used": "general_information"
            }
    
    async def _search_enhanced_knowledge_base(
        self, 
        message: str, 
        server_name: Optional[str] = None,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Search enhanced knowledge base including CSV, text files, and Confluence
        """
        try:
            # Search all knowledge sources
            results = self.enhanced_knowledge.search_all_knowledge_sources(message, server_name)
            
            if results:
                return {
                    'found_match': True,
                    'results': results,
                    'source_types': list(set(r.get('source', 'unknown') for r in results)),
                    'total_matches': len(results)
                }
            
            # Check for common HTTP error guidance
            common_error = self._get_common_error_guidance(message)
            if common_error:
                return {
                    'found_match': False,
                    'common_error_guidance': common_error,
                    'insufficient_info': False
                }
            
            # Check if we have insufficient information
            has_server = server_name or any(srv in message.lower() for srv in ['srv-', 'server', 'host'])
            has_error_code = any(code in message for code in ['401', '403', '404', '500', '502', '503', '504'])
            has_specific_issue = len(message.split()) > 3
            
            if not (has_server or has_error_code or has_specific_issue):
                return {
                    'found_match': False,
                    'insufficient_info': True
                }
            
            return {
                'found_match': False,
                'insufficient_info': False,
                'similar_issues': []
            }
            
        except Exception as e:
            logger.error(f"Error in enhanced knowledge search: {str(e)}")
            return {
                'found_match': False,
                'insufficient_info': False,
                'error': str(e)
            }

    async def _search_csv_knowledge_base(
        self, 
        message: str, 
        server_name: Optional[str] = None,
        user_context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Search CSV knowledge base for existing solutions
        """
        try:
            # Extract potential error codes from message
            import re
            error_codes = re.findall(r'\b[45]\d{2}\b', message)  # Find 4xx and 5xx error codes
            
            # Look for correlation IDs in message
            correlation_matches = re.findall(r'(?:correlation[_\s]?id|cid)[\s:=]*([a-zA-Z0-9]+)', message, re.IGNORECASE)
            correlation_id = correlation_matches[0] if correlation_matches else None
            
            # Check if this is an informational question rather than a technical issue
            informational_patterns = [
                'help', 'what can you', 'how can you', 'what do you', 'tell me about',
                'what are your', 'what services', 'how do you work', 'what is your purpose',
                'capabilities', 'features', 'functionality', 'how to install', 'how to setup',
                'how to configure', 'how do i', 'what is', 'explain', 'guide for', 'tutorial'
            ]
            
            is_informational = any(pattern in message.lower() for pattern in informational_patterns)
            
            # Check if we have insufficient information for proper troubleshooting
            # Skip this check for informational questions
            if not is_informational and len(message.split()) < 4 and not server_name and not error_codes and not correlation_id:
                return {
                    'found_match': False,
                    'exact_matches': [],
                    'search_criteria': {},
                    'insufficient_info': True
                }
            
            # Extract server name from message if not provided
            if not server_name:
                # Look for HSBC server patterns (country code based)
                hsbc_server_matches = re.findall(r'\b(?:gb|cn|hk|vn|mx|us|ca|au|sg|my|in|ae|fr|de)-[\w-]+', message, re.IGNORECASE)
                if hsbc_server_matches:
                    server_name = hsbc_server_matches[0].lower()
                else:
                    # Fallback to generic server patterns
                    server_matches = re.findall(r'srv-[\w-]+|server-[\w-]+|host-[\w-]+', message, re.IGNORECASE)
                    if server_matches:
                        server_name = server_matches[0].lower()
            
            # Determine issue type from message (be more specific)
            message_lower = message.lower()
            issue_type = None
            if any(term in message_lower for term in ['auth', 'authentication', 'login', 'token']) and ('401' in message or '403' in message or 'expired' in message_lower or 'invalid' in message_lower):
                issue_type = "auth_issue"
            elif any(term in message_lower for term in ['payload', 'json', 'data', 'format', 'validation']) and ('400' in message or '422' in message or 'invalid' in message_lower):
                issue_type = "payload_issue" 
            elif any(term in message_lower for term in ['timeout', 'slow', 'performance']) and any(code in message for code in ['500', '502', '503', '504', '504']):
                issue_type = "performance_issue"
            elif any(term in message_lower for term in ['config', 'configuration', 'setup', 'nginx']) and ('502' in message or '500' in message or 'connection' in message_lower):
                issue_type = "configuration_issue"
            elif any(term in message_lower for term in ['lock', 'locked', 'resource']) and ('423' in message or 'concurrent' in message_lower):
                issue_type = "resource_lock"
            
            # Check if we have common error codes that we can provide general guidance for
            common_error_guidance = None
            if error_codes and not server_name:
                common_error_guidance = self._get_common_error_guidance(error_codes[0])
            
            # Only search if we have meaningful technical criteria
            if not server_name and not issue_type and not error_codes:
                return {
                    'found_match': False,
                    'exact_matches': [],
                    'search_criteria': {}
                }
            
            # Search knowledge base
            results = await self.csv_knowledge.search_knowledge_base(
                server_name=server_name,
                issue_type=issue_type,
                username=user_context.get('username') if user_context else None,
                error_code=error_codes[0] if error_codes else None
            )
            
            # If no exact matches but we have a server name, try broader search
            if not results and server_name:
                # Search for all issues for this server
                server_issues = await self.csv_knowledge.search_knowledge_base(
                    server_name=server_name
                )
                
                # If we find server issues, return them as similar matches
                if server_issues:
                    return {
                        'found_match': False,  # Not exact match
                        'exact_matches': [],
                        'similar_issues': server_issues,
                        'search_criteria': {
                            'server_name': server_name,
                            'issue_type': issue_type,
                            'error_code': error_codes[0] if error_codes else None
                        }
                    }
            
            # Check if we should return common error guidance
            if not results and common_error_guidance:
                return {
                    'found_match': False,
                    'exact_matches': [],
                    'common_error_guidance': common_error_guidance,
                    'search_criteria': {
                        'server_name': server_name,
                        'issue_type': issue_type,
                        'error_code': error_codes[0] if error_codes else None
                    }
                }
            
            return {
                'found_match': len(results) > 0,
                'exact_matches': results,
                'search_criteria': {
                    'server_name': server_name,
                    'issue_type': issue_type,
                    'error_code': error_codes[0] if error_codes else None
                }
            }
            
        except Exception as e:
            print(f"Error searching CSV knowledge base: {e}")
            return {'found_match': False, 'exact_matches': [], 'search_criteria': {}}
    
    def _get_common_error_guidance(self, error_code: str) -> Dict[str, Any]:
        """
        Provide general troubleshooting guidance for common HTTP error codes
        """
        error_guides = {
            "400": {
                "title": "400 Bad Request Error",
                "description": "The server cannot process the request due to malformed syntax or invalid request message framing.",
                "common_causes": [
                    "Malformed request syntax",
                    "Invalid JSON payload",
                    "Missing required parameters",
                    "Incorrect Content-Type header"
                ],
                "troubleshooting_steps": [
                    "Validate request JSON syntax",
                    "Check all required fields are present",
                    "Verify Content-Type header is correct",
                    "Review API documentation for proper format",
                    "Test with a minimal valid request"
                ]
            },
            "401": {
                "title": "401 Unauthorized Error", 
                "description": "Authentication is required and has failed or has not been provided.",
                "common_causes": [
                    "Missing authentication token",
                    "Expired authentication token",
                    "Invalid API key",
                    "Incorrect authentication headers"
                ],
                "troubleshooting_steps": [
                    "Check if authentication token is present",
                    "Verify token expiration time",
                    "Regenerate API key if needed",
                    "Ensure correct Authorization header format",
                    "Test authentication with a fresh token"
                ]
            },
            "403": {
                "title": "403 Forbidden Error",
                "description": "The server understood the request but refuses to authorize it.",
                "common_causes": [
                    "Insufficient permissions",
                    "Resource access denied",
                    "IP address blocked",
                    "Rate limiting applied"
                ],
                "troubleshooting_steps": [
                    "Verify user permissions for the resource",
                    "Check if IP address is whitelisted",
                    "Review rate limiting policies",
                    "Confirm user role has required access",
                    "Contact administrator for permission review"
                ]
            },
            "404": {
                "title": "404 Not Found Error",
                "description": "The requested resource could not be found on the server.",
                "common_causes": [
                    "Incorrect URL or endpoint",
                    "Resource has been moved or deleted",
                    "Typo in request path",
                    "API version mismatch"
                ],
                "troubleshooting_steps": [
                    "Verify the correct URL/endpoint",
                    "Check for typos in the request path",
                    "Confirm API version is correct",
                    "Review API documentation for changes",
                    "Test with a known working endpoint"
                ]
            },
            "500": {
                "title": "500 Internal Server Error",
                "description": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
                "common_causes": [
                    "Server-side application error",
                    "Database connection issues",
                    "Configuration problems",
                    "Resource exhaustion"
                ],
                "troubleshooting_steps": [
                    "Check server logs for specific errors",
                    "Verify database connectivity",
                    "Review recent deployments or changes",
                    "Monitor server resource usage",
                    "Contact system administrator"
                ]
            },
            "502": {
                "title": "502 Bad Gateway Error",
                "description": "The server received an invalid response from an upstream server.",
                "common_causes": [
                    "Upstream server is down",
                    "Network connectivity issues",
                    "Load balancer configuration problems",
                    "Timeout from upstream server"
                ],
                "troubleshooting_steps": [
                    "Check upstream server status",
                    "Verify network connectivity",
                    "Review load balancer configuration",
                    "Check for upstream server timeouts",
                    "Monitor upstream server health"
                ]
            },
            "503": {
                "title": "503 Service Unavailable",
                "description": "The server is currently unable to handle the request due to temporary overload or maintenance.",
                "common_causes": [
                    "Server maintenance",
                    "High traffic overload",
                    "Resource exhaustion",
                    "Service temporarily disabled"
                ],
                "troubleshooting_steps": [
                    "Check if maintenance is scheduled",
                    "Monitor server resource usage",
                    "Review traffic patterns",
                    "Check service status page",
                    "Wait and retry the request"
                ]
            },
            "504": {
                "title": "504 Gateway Timeout",
                "description": "The server did not receive a timely response from an upstream server.",
                "common_causes": [
                    "Upstream server response timeout",
                    "Network latency issues",
                    "Long-running database queries",
                    "Gateway timeout configuration"
                ],
                "troubleshooting_steps": [
                    "Check upstream server response time",
                    "Review network latency",
                    "Optimize database queries",
                    "Adjust gateway timeout settings",
                    "Monitor upstream server performance"
                ]
            }
        }
        
        return error_guides.get(error_code, None)

    def _generate_common_error_response(
        self,
        message: str,
        error_guidance: Dict[str, Any],
        user_context: Dict[str, Any],
        processing_updates: List[str]
    ) -> Dict[str, Any]:
        """
        Generate response for common HTTP error codes with general troubleshooting
        """
        try:
            user_name = user_context.get('full_name', user_context.get('username', 'there')) if user_context else 'there'
            
            response_text = f"Hi {user_name}! I can help you troubleshoot this **{error_guidance['title']}**.\n\n"
            response_text += f"**What this means:** {error_guidance['description']}\n\n"
            
            response_text += f"**Common Causes:**\n"
            for cause in error_guidance['common_causes']:
                response_text += f"• {cause}\n"
            
            response_text += f"\n**Troubleshooting Steps:**\n"
            for i, step in enumerate(error_guidance['troubleshooting_steps'], 1):
                response_text += f"{i}. {step}\n"
            
            response_text += f"\n**For More Specific Help:**\n"
            response_text += f"If these general steps don't resolve your issue, please provide:\n"
            response_text += f"• **Server name** (e.g., srv-api-01, srv-web-02)\n"
            response_text += f"• **Complete error message** with any additional details\n"
            response_text += f"• **What you were trying to do** when the error occurred\n"
            response_text += f"• **Correlation ID** if available\n\n"
            response_text += f"This will help me search for specific solutions in our knowledge base and monitoring systems."
            
            suggestions = [
                "Try the troubleshooting steps above",
                "Provide server name for specific help",
                "Share complete error message",
                "Describe what action triggered the error",
                "Include correlation ID if available"
            ]
            
            return {
                "message": response_text,
                "suggestions": suggestions,
                "incident_required": False,
                "ai_service_used": "common_error_guidance",
                "error_code": error_guidance['title'].split()[0]
            }
            
        except Exception as e:
            print(f"Error generating common error response: {e}")
            return {
                "message": f"I can help you with this error, but encountered an issue generating the response. Please provide more specific details about your problem.",
                "suggestions": ["Share complete error message", "Provide server name", "Include correlation ID"],
                "incident_required": False,
                "ai_service_used": "common_error_guidance_error"
            }

    async def _find_similar_csv_issues(self, message: str, server_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Find similar issues in CSV knowledge base
        """
        try:
            similar_issues = await self.csv_knowledge.find_similar_issues(message, server_name)
            return similar_issues
        except Exception as e:
            print(f"Error finding similar issues: {e}")
            return []
    
    async def _generate_similar_issues_response(
        self,
        message: str,
        similar_issues: List[Dict[str, Any]],
        user_context: Dict[str, Any], 
        processing_updates: List[str],
        server_name: str = None
    ) -> Dict[str, Any]:
        """
        Generate response when we have similar issues but no exact match
        """
        try:
            # Filter issues for the specific server if provided
            if server_name:
                server_issues = [issue for issue in similar_issues if issue.get('server_name', '').lower() == server_name.lower()]
                if server_issues:
                    similar_issues = server_issues
            
            # Sort by status and priority
            similar_issues.sort(key=lambda x: (x.get('status') != 'resolved', x.get('priority') == 'low'))
            
            response_text = f"I found {len(similar_issues)} related issues for **{server_name}** in our knowledge base:\n\n"
            
            suggestions = []
            
            for i, issue in enumerate(similar_issues[:3], 1):  # Show top 3
                status_emoji = "✅" if issue.get('status') == 'resolved' else "🔍"
                priority_text = issue.get('priority', 'medium').upper()
                
                response_text += f"{status_emoji} **Issue #{i} - {issue.get('issue_type', 'Unknown').replace('_', ' ').title()}**\n"
                response_text += f"• **Error Code:** {issue.get('error_code', 'N/A')}\n"
                response_text += f"• **Description:** {issue.get('description', 'No description')}\n"
                response_text += f"• **Status:** {issue.get('status', 'unknown').title()} ({priority_text} priority)\n"
                
                if issue.get('resolution_steps'):
                    steps = issue.get('resolution_steps', '').split(' | ')
                    response_text += f"• **Resolution Steps:**\n"
                    for step in steps[:3]:  # Show first 3 steps
                        if step.strip():
                            response_text += f"  - {step.strip()}\n"
                
                response_text += f"• **Correlation ID:** {issue.get('correlation_id', 'N/A')}\n\n"
                
                suggestions.append(f"Try resolution for {issue.get('issue_type', 'issue').replace('_', ' ')}")
            
            if len(similar_issues) > 3:
                response_text += f"*...and {len(similar_issues) - 3} more related issues*\n\n"
            
            response_text += f"**Next Steps:**\n"
            response_text += f"• Review if any of these issues match your current problem\n"
            response_text += f"• Try the resolution steps for similar issues\n" 
            response_text += f"• Provide more specific error details for exact troubleshooting\n"
            
            suggestions.extend([
                "Provide specific error message",
                "Share error code if available", 
                "Describe exact symptoms",
                "Create incident if issues persist"
            ])
            
            return {
                "message": response_text,
                "suggestions": suggestions,
                "incident_required": False,
                "ai_service_used": "csv_similar_issues",
                "similar_issues_found": len(similar_issues)
            }
            
        except Exception as e:
            print(f"Error generating similar issues response: {e}")
            return {
                "message": f"I found some related issues for {server_name}, but had trouble formatting the response. Please provide more specific error details.",
                "suggestions": ["Share specific error message", "Provide error code", "Describe exact symptoms"],
                "incident_required": False,
                "ai_service_used": "csv_similar_issues_error"
            }

    async def _generate_knowledge_based_response(
        self,
        message: str,
        knowledge_results: Dict[str, Any], 
        user_context: Dict[str, Any],
        processing_updates: List[str]
    ) -> Dict[str, Any]:
        """
        Generate response based on enhanced knowledge base results
        """
        try:
            results = knowledge_results.get('results', [])
            source_types = knowledge_results.get('source_types', [])
            
            # Format results by source type
            formatted_content = []
            
            for result in results[:3]:  # Top 3 results
                source = result.get('source', 'unknown')
                
                if source == 'csv_knowledge':
                    formatted_content.append(
                        f"**📊 Server Issue Database**\n"
                        f"Server: {result.get('server_name', 'N/A')}\n"
                        f"Issue: {result.get('issue_description', 'N/A')}\n"
                        f"Resolution: {result.get('resolution_steps', 'N/A')}\n"
                        f"Reported by: {result.get('created_by', 'N/A')} on {result.get('created_at', 'N/A')}"
                    )
                elif source == 'text_knowledge':
                    formatted_content.append(
                        f"**📄 Documentation: {result.get('title', 'Unknown')}**\n"
                        f"{result.get('snippet', 'No content available')}\n"
                        f"*Source: {result.get('filename', 'N/A')} | Last modified: {result.get('last_modified', 'N/A')}*"
                    )
                elif source == 'confluence':
                    formatted_content.append(
                        f"**🌐 Confluence: {result.get('title', 'Unknown')}**\n"
                        f"{result.get('snippet', 'No content available')}\n"
                        f"*[View full page]({result.get('url', '#')}) | Last modified: {result.get('last_modified', 'N/A')}*"
                    )
            
            knowledge_content = "\n\n".join(formatted_content)
            
            # Create context for AI
            context = f"""
Based on our comprehensive knowledge base search across multiple sources:

{knowledge_content}

User Query: {message}
Sources Found: {', '.join(source_types)}
Total Matches: {len(results)}
"""
            
            # Use OpenAI if available, otherwise Ollama
            processing_updates.append("🤖 Generating AI response from knowledge...")
            system_prompt = f"""
            You are HSBC AutoAssist, an API support chatbot for HSBC DC Automation Support Team.
            Based on the following knowledge base information, provide a helpful response.
            
            Knowledge Context: {context}
            
            Be specific, actionable, and professional. If the knowledge provides steps, list them clearly.
            """
            
            ai_response = await self._generate_ai_response_with_ollama(system_prompt, f"User Query: {message}")
            ai_service = "ollama_llama32"
            
            return {
                "message": ai_response,
                "suggestions": self._extract_suggestions_from_knowledge(results),
                "incident_required": self._should_create_incident(message, results),
                "ai_service_used": ai_service,
                "knowledge_sources": source_types,
                "matches_found": len(results)
            }
            
        except Exception as e:
            logger.error(f"Error generating knowledge-based response: {str(e)}")
            return {
                "message": "I found relevant information in our knowledge base, but encountered an error processing it. Please try rephrasing your question.",
                "suggestions": ["Try being more specific about the issue", "Include server name if known"],
                "incident_required": True,
                "ai_service_used": "error_fallback"
            }

    async def _generate_csv_based_response(
        self,
        message: str,
        csv_results: Dict[str, Any], 
        user_context: Dict[str, Any],
        processing_updates: List[str]
    ) -> Dict[str, Any]:
        """
        Generate response based on CSV knowledge base results
        """
        try:
            exact_matches = csv_results.get('exact_matches', [])
            if not exact_matches:
                return None
            
            # Use the most recent or highest priority match
            best_match = max(exact_matches, key=lambda x: (
                x.get('priority') == 'critical',
                x.get('priority') == 'high', 
                x.get('reported_date', '2000-01-01')
            ))
            
            user_name = user_context.get('full_name', user_context.get('username', 'there')) if user_context else 'there'
            
            response_message = f"Great news, {user_name}! I found a solution for this issue in our knowledge base.\n\n"
            response_message += f"**Issue Details:**\n"
            response_message += f"• Server: {best_match.get('server_name', 'N/A')}\n"
            response_message += f"• Issue Type: {best_match.get('issue_type', 'N/A').replace('_', ' ').title()}\n"
            response_message += f"• Error Code: {best_match.get('error_code', 'N/A')}\n"
            response_message += f"• Description: {best_match.get('description', 'N/A')}\n\n"
            
            response_message += f"**Resolution Steps:**\n"
            resolution_steps = best_match.get('resolution_steps', '').replace('\\n', '\n')
            for i, step in enumerate(resolution_steps.split('\n'), 1):
                if step.strip():
                    response_message += f"{i}. {step.strip()}\n"
            
            response_message += f"\n**Previous Resolution:**\n"
            response_message += f"• Originally reported by: {best_match.get('username', 'Unknown')}\n"
            response_message += f"• Date: {best_match.get('reported_date', 'Unknown')}\n"
            response_message += f"• Status: {best_match.get('status', 'Unknown')}\n"
            response_message += f"• Correlation ID: {best_match.get('correlation_id', 'N/A')}\n"
            
            if len(exact_matches) > 1:
                response_message += f"\n*Note: Found {len(exact_matches)} similar cases. This solution has been effective before.*"
            
            processing_updates.append("✅ Response generated from knowledge base")
            
            return {
                "message": response_message,
                "suggestions": [
                    "Try the resolution steps above",
                    "Check if issue persists after applying fix",
                    "Contact previous resolver if needed",
                    "Mark as resolved when fixed"
                ],
                "incident_required": best_match.get('priority') == 'critical',
                "ai_service_used": "csv_knowledge_base",
                "data_sources": ["Internal Knowledge Base"],
                "knowledge_base_match": best_match,
                "total_matches": len(exact_matches)
            }
            
        except Exception as e:
            print(f"Error generating CSV-based response: {e}")
            return None
    
    async def _save_to_knowledge_base(
        self,
        message: str,
        query_analysis: Dict[str, Any],
        server_name: Optional[str],
        correlation_id: Optional[str],
        user_context: Dict[str, Any]
    ) -> bool:
        """
        Save new issue to knowledge base for future reference
        """
        try:
            # Extract error code from message
            import re
            error_codes = re.findall(r'\b[45]\d{2}\b', message)
            error_code = error_codes[0] if error_codes else "N/A"
            
            # Generate basic resolution steps based on issue type
            issue_type = query_analysis.get('query_type', 'other')
            basic_resolution = self._get_basic_resolution_steps(issue_type)
            
            success = await self.csv_knowledge.add_entry(
                server_name=server_name or "Unknown",
                issue_type=issue_type,
                error_code=error_code,
                description=message[:200] + "..." if len(message) > 200 else message,
                resolution_steps=basic_resolution,
                username=user_context.get('username', 'Anonymous') if user_context else 'Anonymous',
                priority=query_analysis.get('priority', 'medium'),
                correlation_id=correlation_id
            )
            
            return success
            
        except Exception as e:
            print(f"Error saving to knowledge base: {e}")
            return False
    
    async def _query_hsbc_internal_apis(self, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query internal HSBC APIs for real-time server status
        """
        try:
            # Mock implementation - replace with actual HSBC API calls
            if server_name:
                # Simulate server health check
                return {
                    "health_status": "healthy",
                    "current_load": "65%",
                    "response_time": "150ms",
                    "last_restart": "2024-11-15 08:30:00",
                    "uptime": "72 hours",
                    "region": self._get_server_region(server_name)
                }
            return {"status": "no_server_specified"}
            
        except Exception as e:
            logger.error(f"HSBC API query error: {e}")
            return {"error": f"API unavailable: {str(e)}"}
    
    async def _query_splunk_logs(self, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query Splunk API for log analysis
        """
        try:
            # Mock implementation - replace with actual Splunk API calls
            return {
                "errors": [
                    {"timestamp": "2024-11-18 14:30:00", "level": "ERROR", "message": "Authentication failed"},
                    {"timestamp": "2024-11-18 14:25:00", "level": "WARN", "message": "High response time"}
                ],
                "patterns": "JWT token expiration pattern detected",
                "time_range": "Last 24 hours",
                "total_events": 1247,
                "error_rate": "2.3%"
            }
            
        except Exception as e:
            logger.error(f"Splunk API query error: {e}")
            return {"error": f"Splunk unavailable: {str(e)}"}
    
    async def _query_ansible_status(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query Ansible API for automation data
        """
        try:
            # Mock implementation - replace with actual Ansible API calls
            return {
                "status": "successful",
                "last_deployment": "2024-11-18 12:00:00",
                "success_rate": "94.5%",
                "pending_jobs": 2,
                "last_job_id": "JOB_12345",
                "playbook": "deploy_api_updates.yml"
            }
            
        except Exception as e:
            logger.error(f"Ansible API query error: {e}")
            return {"error": f"Ansible unavailable: {str(e)}"}
    
    async def _query_performance_apis(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query performance monitoring APIs
        """
        try:
            # Mock implementation - replace with actual performance monitoring APIs
            return {
                "cpu_usage": "72%",
                "memory_usage": "84%",
                "disk_io": "45 MB/s",
                "network_throughput": "120 Mbps",
                "response_times": {"avg": "150ms", "p95": "300ms", "p99": "500ms"}
            }
            
        except Exception as e:
            logger.error(f"Performance API query error: {e}")
            return {"error": f"Performance monitoring unavailable: {str(e)}"}
    
    async def _query_alert_systems(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query alert and monitoring systems
        """
        try:
            # Mock implementation - replace with actual alert system APIs
            return {
                "active_alerts": [
                    {"severity": "warning", "message": "High CPU usage detected", "timestamp": "2024-11-18 14:20:00"},
                    {"severity": "info", "message": "Deployment completed", "timestamp": "2024-11-18 12:00:00"}
                ],
                "alert_count_24h": 15,
                "resolved_count_24h": 12
            }
            
        except Exception as e:
            logger.error(f"Alert system query error: {e}")
            return {"error": f"Alert system unavailable: {str(e)}"}
    
    async def _search_api_documentation(self, message: str) -> Dict[str, Any]:
        """
        Search API documentation for relevant information
        """
        try:
            # Mock implementation - replace with actual API documentation search
            return {
                "endpoints": [
                    {"endpoint": "/api/auth/login", "method": "POST", "description": "User authentication"},
                    {"endpoint": "/api/users/{id}", "method": "GET", "description": "Get user details"}
                ],
                "examples": [
                    {"title": "Authentication Example", "code": "curl -X POST /api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"user\", \"password\":\"pass\"}'"},
                ]
            }
            
        except Exception as e:
            logger.error(f"API documentation search error: {e}")
            return {"error": f"API documentation unavailable: {str(e)}"}
    
    def _get_server_region(self, server_name: str) -> str:
        """
        Determine server region from server name
        """
        if not server_name:
            return "Unknown"
            
        prefix = server_name.split('-')[0].lower()
        region_map = {
            'gb': 'UK', 'cn': 'China', 'hk': 'Hong Kong', 'vn': 'Vietnam',
            'mx': 'Mexico', 'us': 'United States', 'ca': 'Canada', 
            'au': 'Australia', 'sg': 'Singapore', 'my': 'Malaysia',
            'in': 'India', 'ae': 'UAE', 'fr': 'France', 'de': 'Germany'
        }
        return region_map.get(prefix, 'Unknown')
    
    async def _analyze_with_ollama(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any], analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Fallback LLM analysis using Ollama
        """
        try:
            # Prepare context for Ollama
            context = self._prepare_llm_context(message, server_name, collected_data, analysis_type)
            
            # Ollama API call
            ollama_prompt = f"""You are an HSBC technical support analyst. Analyze this data and provide comprehensive troubleshooting guidance.

User Query: {message}
Server: {server_name or 'Not specified'}
Analysis Type: {analysis_type}

Data Analysis:
{context}

Provide:
1. Root cause analysis
2. Step-by-step resolution steps
3. Prevention recommendations
4. Priority assessment

Be specific, actionable, and professional."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": ollama_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 800
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get('response', '')
                
                if ollama_response:
                    return {
                        "message": f"🔧 **Technical Analysis & Resolution (Llama 3.2)**\n\n{ollama_response}",
                        "ai_service_used": "ollama_technical_analysis",
                        "data_sources": list(collected_data.keys()),
                        "server_name": server_name,
                        "analysis_type": analysis_type,
                        "confidence_level": "medium"
                    }
            
        except Exception as e:
            logger.error(f"Ollama analysis error: {e}")
            
        return None
    
    def _generate_fallback_technical_response(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fallback response when both OpenAI and Ollama fail
        """
        # Use collected data to generate basic response
        csv_data = collected_data.get("csv_knowledge", [])
        
        if csv_data:
            best_match = csv_data[0]
            response = f"""🔧 **Technical Issue Analysis**

**Server**: {server_name or 'Not specified'}
**Issue**: {message}

**Based on Historical Data**:
- **Root Cause**: {best_match.get('root_cause', 'Analysis required')}
- **Resolution Steps**: 
{self._format_resolution_steps(best_match.get('resolution_steps', 'Contact support'))}

**Data Sources**: {', '.join(collected_data.keys())}

*Note: This response is based on knowledge base matching. For complex issues, consider creating an incident ticket.*"""
        else:
            response = f"""🔧 **Technical Issue Analysis**

**Server**: {server_name or 'Not specified'}
**Issue**: {message}

**Initial Assessment**:
1. Verify server connectivity
2. Check system logs for errors
3. Review recent changes or deployments
4. Contact support if issue persists

**Data Collection Status**: {len(collected_data)} sources queried
**Recommendation**: Create incident ticket for detailed investigation"""
        
        return {
            "message": response,
            "ai_service_used": "fallback_analysis",
            "data_sources": list(collected_data.keys()),
            "server_name": server_name,
            "incident_required": True,
            "confidence_level": "low"
        }
    
    def _get_basic_resolution_steps(self, issue_type: str) -> str:
        """
        Get basic resolution steps template based on issue type
        """
        templates = {
            "auth_issue": "1. Check API credentials and permissions\n2. Verify token expiration\n3. Review authentication headers\n4. Test with valid credentials",
            "payload_issue": "1. Validate JSON/XML format\n2. Check required fields\n3. Verify data types\n4. Test with minimal payload",
            "performance_issue": "1. Check system resources\n2. Monitor database performance\n3. Review recent changes\n4. Scale resources if needed",
            "configuration_issue": "1. Verify configuration files\n2. Check environment variables\n3. Test connectivity\n4. Restart affected services",
            "resource_lock": "1. Identify blocking processes\n2. Clear resource locks\n3. Retry operation\n4. Implement timeout handling"
        }
        return templates.get(issue_type, "1. Gather more information\n2. Check system logs\n3. Test basic functionality\n4. Contact support if needed")
    
    def _get_suggested_actions(self, query_type):
        """Get suggested actions based on query type for fallback analysis"""
        action_map = {
            "auth_issue": ["Check API credentials", "Verify token expiration", "Review permissions"],
            "payload_issue": ["Validate JSON format", "Check required fields", "Review API documentation"],
            "resource_lock": ["Check system resources", "Review concurrent operations", "Monitor process status"],
            "performance_issue": ["Monitor system metrics", "Check database performance", "Review recent changes"],
            "configuration_issue": ["Verify configuration files", "Check environment variables", "Review deployment status"]
        }
        return action_map.get(query_type, ["Contact support", "Check system logs", "Provide more details"])
    
    async def _analyze_query_with_ollama(self, message: str, server_name: str, correlation_id: str, system_prompt: str) -> Dict[str, Any]:
        """
        Analyze query using Ollama as fallback
        """
        try:
            prompt = f"{system_prompt}\n\nQuery: {message}\nServer: {server_name or 'Not provided'}\nCorrelation ID: {correlation_id or 'Not provided'}\n\nPlease respond with a JSON object containing query_type, priority, keywords, requires_data_lookup, and suggested_actions."
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get("response", "")
                
                # Try to parse JSON from response
                try:
                    # Extract JSON from response if it contains other text
                    import re
                    json_match = re.search(r'\{.*\}', ollama_response, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group())
                except:
                    pass
            
            # Fallback to rule-based analysis
            return self._fallback_query_analysis(message, server_name, correlation_id)
            
        except Exception as e:
            print(f"Ollama analysis error: {e}")
            return self._fallback_query_analysis(message, server_name, correlation_id)
    
    async def _generate_ai_response_with_ollama(self, system_prompt: str, context_message: str) -> str:
        """
        Generate AI response using Ollama
        """
        try:
            full_prompt = f"{system_prompt}\n\n{context_message}\n\nPlease provide a helpful, professional response for the DC AutoAssist system."
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "max_tokens": 1000
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "I apologize, but I'm experiencing technical difficulties. Please try again or contact support for assistance.")
            else:
                return "I'm currently experiencing connectivity issues with my AI service. Please try again in a moment."
                
        except Exception as e:
            print(f"Ollama generation error: {e}")
            return "I'm temporarily unable to provide AI assistance. Please use the suggested troubleshooting steps below or contact support."
    
    def _fallback_query_analysis(self, message: str, server_name: str, correlation_id: str) -> Dict[str, Any]:
        """
        Fallback query analysis using rule-based approach
        """
        message_lower = message.lower()
        
        # Determine query type based on keywords
        if any(term in message_lower for term in ['auth', 'login', 'token', '401', '403']):
            query_type = "auth_issue"
        elif any(term in message_lower for term in ['payload', 'json', 'data', '400']):
            query_type = "payload_issue" 
        elif any(term in message_lower for term in ['timeout', 'slow', '500', '502', '503', '504']):
            query_type = "performance_issue"
        elif any(term in message_lower for term in ['config', 'setup', 'connection']):
            query_type = "configuration_issue"
        elif any(term in message_lower for term in ['lock', 'resource', 'concurrent']):
            query_type = "resource_lock"
        else:
            query_type = "other"
        
        # Set priority based on error codes and keywords
        if any(term in message_lower for term in ['critical', 'urgent', '500', '502', 'down']):
            priority = "high"
        elif any(term in message_lower for term in ['slow', 'timeout', 'performance']):
            priority = "medium"
        else:
            priority = "low"
        
        return {
            "query_type": query_type,
            "priority": priority,
            "keywords": [word for word in message.split()[:8] if len(word) > 2],
            "requires_data_lookup": bool(server_name or correlation_id),
            "suggested_actions": self._get_suggested_actions(query_type)
        }
    
    def _extract_suggestions_from_knowledge(self, results: List[Dict]) -> List[str]:
        """Extract actionable suggestions from knowledge base results"""
        suggestions = []
        
        for result in results[:3]:
            source = result.get('source', '')
            
            if source == 'csv_knowledge':
                # Extract steps from resolution
                resolution = result.get('resolution_steps', '')
                if resolution and '|' in resolution:
                    steps = [step.strip() for step in resolution.split('|')]
                    suggestions.extend(steps[:2])  # First 2 steps
                    
            elif source in ['text_knowledge', 'confluence']:
                # Extract actionable items from content
                content = result.get('snippet', '') or result.get('content', '')
                # Look for numbered lists or bullet points
                if '1.' in content or '•' in content or '-' in content:
                    lines = content.split('\n')
                    for line in lines[:3]:
                        if any(marker in line for marker in ['1.', '2.', '•', '-']):
                            clean_line = line.strip('1234567890.•- ').strip()
                            if len(clean_line) > 10:
                                suggestions.append(clean_line)
        
        # Remove duplicates and limit
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in unique_suggestions and len(suggestion) > 10:
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Max 5 suggestions
    
    async def _handle_category_based_query(
        self, 
        message: str, 
        category: str, 
        server_name: Optional[str], 
        correlation_id: Optional[str], 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle queries based on selected category"""
        
        # Add debug logging
        logger.info(f"🔍 Category-based query handler called with category: '{category}', message: '{message[:50]}...'")
        
        if category == "general":
            logger.info("📚 Processing as General Educational Query")
            # General educational questions - use AI for comprehensive explanations
            return await self._handle_general_educational_query(message, user_context)
        
        elif category == "hsbc_internal":
            logger.info("🏦 Processing as HSBC Internal Issue - starting enhanced LLM analysis")
            # HSBC-specific server/API issues - search knowledge base + external APIs
            response = await self._handle_hsbc_internal_issue(message, server_name, correlation_id, user_context)
            if 'metadata' not in response:
                response['metadata'] = {}
            response['metadata']['category'] = category
            return response
        
        elif category == "monitoring":
            logger.info("📊 Processing as System Monitoring Query")
            # System monitoring - focus on Splunk, Ansible, performance data
            response = await self._handle_monitoring_query(message, server_name, correlation_id, user_context)
            if 'metadata' not in response:
                response['metadata'] = {}
            response['metadata']['category'] = category
            return response
        
        elif category == "knowledge_base":
            logger.info("📖 Processing as Knowledge Base Query")
            # Internal knowledge - Confluence, procedures, documentation
            response = await self._handle_knowledge_base_query(message, user_context)
            if 'metadata' not in response:
                response['metadata'] = {}
            response['metadata']['category'] = category
            return response
        
        else:
            logger.warning(f"⚠️ Unknown category '{category}' - falling back to standard processing")
            # Fallback to standard processing
            return await self._process_standard_query(message, server_name, correlation_id, user_context)

    async def _handle_general_educational_query(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general educational questions with comprehensive LLM responses"""
        
        try:
            # First, try OpenAI for comprehensive responses
            if self.api_key:
                client = OpenAI(api_key=self.api_key)
                
                educational_prompt = f"""
                Provide a comprehensive, educational response to this question: "{message}"
                
                Context: This is a general knowledge question from an HSBC DC team member.
                
                Please provide:
                1. A clear, detailed explanation suitable for technical professionals
                2. Practical examples where relevant
                3. Best practices if applicable
                4. Common use cases or implementations
                5. If comparing technologies, include pros/cons and when to use each
                
                Keep the response informative but concise (under 600 words).
                Format with markdown for better readability.
                """
                
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": educational_prompt}],
                    temperature=0.7,
                    max_tokens=800
                )
                
                ai_response = response.choices[0].message.content
                
                return {
                    "message": f"📚 **Educational Response**\n\n{ai_response}\n\n---\n*This response was generated using OpenAI GPT-4 to provide comprehensive educational content.*",
                    "suggestions": [
                        "Ask follow-up questions for clarification",
                        "Request specific examples or use cases",
                        "Ask about related concepts",
                        "Explore deeper technical details"
                    ],
                    "data_sources": ["OpenAI GPT-4", "Educational Knowledge"],
                    "incident_required": False,
                    "ai_service_used": "openai_educational",
                    "processing_updates": ["🤖 Generating comprehensive educational response using OpenAI..."]
                }
            
        except Exception as e:
            logger.error(f"Error in OpenAI educational query: {e}")
        
        # Try Llama fallback if OpenAI fails
        try:
            if self.use_ollama_fallback and self.ollama_url:
                ollama_response = await self._get_ollama_educational_response(message, user_context)
                if ollama_response:
                    return ollama_response
        except Exception as e:
            logger.error(f"Error in Ollama educational query: {e}")
        
        # Check for built-in responses as final fallback
        educational_response = self._get_built_in_educational_response(message)
        if educational_response:
            return educational_response
        
        # Final fallback - provide basic educational guidance
        return {
            "message": f"📚 **Educational Response**\n\nI'd be happy to help with your question: \"{message}\"\n\nFor the most comprehensive answer, I recommend:\n\n• **Consulting official documentation** for technical topics\n• **Asking specific sub-questions** to get targeted information\n• **Providing context** about your use case or requirements\n\nIf this is about programming languages, frameworks, or technical concepts, feel free to ask more specific questions like:\n• \"What are the main differences between X and Y?\"\n• \"When should I use X instead of Y?\"\n• \"What are the pros and cons of X?\"\n\nHow can I help you explore this topic further?",
            "suggestions": [
                "Ask more specific questions",
                "Provide context about your use case", 
                "Break down into smaller topics",
                "Ask for examples or comparisons"
            ],
            "data_sources": ["Built-in Knowledge", "Educational Guidance"],
            "incident_required": False,
            "ai_service_used": "educational_fallback"
        }

    def _get_built_in_educational_response(self, message: str) -> Optional[Dict[str, Any]]:
        """Provide built-in educational responses for common questions"""
        message_lower = message.lower()
        
        # Programming language comparisons
        if any(lang in message_lower for lang in ['python', 'java']) and any(word in message_lower for word in ['best', 'better', 'compare', 'vs', 'versus', 'difference']):
            return {
                "message": """📚 **Python vs Java: A Professional Comparison**

Both Python and Java are excellent programming languages, each with distinct strengths:

**🐍 Python Advantages:**
• **Rapid Development** - Concise syntax, faster prototyping
• **Data Science & AI** - Extensive libraries (pandas, numpy, tensorflow)
• **Automation & Scripting** - Perfect for DevOps, system administration
• **Learning Curve** - Easier for beginners, more readable code
• **Flexibility** - Dynamic typing, interactive development

**☕ Java Advantages:**
• **Enterprise Applications** - Robust, scalable, mature ecosystem
• **Performance** - Generally faster execution, better memory management  
• **Platform Independence** - "Write once, run anywhere" philosophy
• **Type Safety** - Static typing catches errors at compile time
• **Large-scale Systems** - Excellent for complex, distributed applications

**🎯 Choose Based on Context:**
• **Python for:** Data analysis, AI/ML, automation, rapid prototyping, web development (Django/Flask)
• **Java for:** Enterprise applications, Android development, large distributed systems, high-performance applications

**💼 In HSBC Context:**
Both are widely used - Java for core banking systems and enterprise applications, Python for data analytics, automation, and API integrations.

The "best" language depends on your specific project requirements, team expertise, and performance needs.""",
                "suggestions": [
                    "Ask about specific use cases (web development, data science, etc.)",
                    "Compare performance characteristics",
                    "Learn about ecosystem and libraries",
                    "Understand learning curve differences"
                ],
                "data_sources": ["Built-in Educational Knowledge"],
                "incident_required": False,
                "ai_service_used": "built_in_educational"
            }
        
        # API-related questions
        elif 'api' in message_lower and any(word in message_lower for word in ['what', 'explain', 'define']):
            return {
                "message": """📚 **API (Application Programming Interface) Explained**

An **API** is a set of rules and protocols that allows different software applications to communicate with each other.

**🔧 Key Concepts:**
• **Interface** - Defines how software components should interact
• **Abstraction** - Hides complex implementation details
• **Standardization** - Provides consistent communication methods
• **Integration** - Enables different systems to work together

**🌐 Types of APIs:**
• **REST API** - Uses HTTP methods (GET, POST, PUT, DELETE)
• **GraphQL** - Query language for APIs with flexible data fetching
• **SOAP** - Protocol-based, more structured and secure
• **WebSocket** - Real-time bidirectional communication

**💼 In Banking/HSBC:**
• **Account Services** - Balance inquiries, transaction history
• **Payment Processing** - Money transfers, payment initiation
• **Authentication** - Secure user verification
• **Third-party Integration** - Connecting with external services
• **Mobile Banking** - Mobile app backend communication

**🔒 Security Considerations:**
• Authentication (API keys, OAuth tokens)
• Rate limiting to prevent abuse
• Data encryption (HTTPS/TLS)
• Input validation and sanitization

APIs are the backbone of modern software architecture, enabling microservices, mobile applications, and system integrations.""",
                "suggestions": [
                    "Learn about REST vs GraphQL",
                    "Understand API authentication methods",
                    "Explore API security best practices", 
                    "Ask about specific API types or use cases"
                ],
                "data_sources": ["Built-in Educational Knowledge"],
                "incident_required": False,
                "ai_service_used": "built_in_educational"
            }
        
        # Microservices questions
        elif 'microservice' in message_lower and any(word in message_lower for word in ['what', 'explain', 'define']):
            return {
                "message": """📚 **Microservices Architecture Explained**

**Microservices** is an architectural pattern that structures an application as a collection of small, independent services.

**🏗️ Core Principles:**
• **Single Responsibility** - Each service handles one business capability
• **Independence** - Services can be developed, deployed, and scaled separately
• **Decentralized** - Each service manages its own data and business logic
• **Communication** - Services interact via well-defined APIs (REST, messaging)

**💡 Key Characteristics:**
• **Small & Focused** - Each service has a specific business purpose
• **Autonomous Teams** - Different teams can own different services
• **Technology Diversity** - Services can use different technologies
• **Fault Isolation** - Failure in one service doesn't crash the entire system

**🔄 vs Monolithic Architecture:**
• **Monolith:** Single deployable unit, shared database, tight coupling
• **Microservices:** Multiple deployable units, separate databases, loose coupling

**💼 In Banking/HSBC Context:**
• **Account Service** - Manages user accounts and profiles
• **Payment Service** - Handles transactions and transfers
• **Authentication Service** - User login and security
• **Notification Service** - Sends alerts and messages
• **Reporting Service** - Generates statements and reports

**⚖️ Trade-offs:**
• **Benefits:** Scalability, flexibility, technology diversity, team autonomy
• **Challenges:** Complexity, network latency, data consistency, monitoring

Microservices work well for large, complex applications with multiple teams, but may be overkill for simple applications.""",
                "suggestions": [
                    "Learn about microservices vs monolith trade-offs",
                    "Understand service communication patterns",
                    "Explore containerization and orchestration",
                    "Ask about specific microservices challenges"
                ],
                "data_sources": ["Built-in Educational Knowledge"],
                "incident_required": False,
                "ai_service_used": "built_in_educational"
            }
        
        return None

    async def _get_ollama_educational_response(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get educational response using Ollama/Llama"""
        try:
            educational_prompt = f"""
            Provide a comprehensive, educational response to this question: "{message}"
            
            Context: This is a general knowledge question from an HSBC DC team member.
            
            Please provide:
            1. A clear, detailed explanation suitable for technical professionals
            2. Practical examples where relevant
            3. Best practices if applicable
            4. Common use cases or implementations
            5. If comparing technologies, include pros/cons and when to use each
            
            Keep the response informative but concise (under 600 words).
            Format with markdown for better readability.
            """
            
            # Make request to Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": educational_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 800
                    }
                },
                timeout=5  # Shorter timeout to fail fast if Ollama not available
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '')
                
                if ai_response:
                    return {
                        "message": f"📚 **Educational Response**\n\n{ai_response}\n\n---\n*This response was generated using Llama 3.2 to provide comprehensive educational content.*",
                        "suggestions": [
                            "Ask follow-up questions for clarification",
                            "Request specific examples or use cases",
                            "Ask about related concepts",
                            "Explore deeper technical details"
                        ],
                        "data_sources": ["Llama 3.2", "Educational Knowledge"],
                        "incident_required": False,
                        "ai_service_used": "ollama_educational",
                        "processing_updates": ["🦙 Generating comprehensive educational response using Llama 3.2..."]
                    }
            
            logger.error(f"Ollama request failed: {response.status_code} - {response.text}")
            
        except requests.exceptions.ConnectTimeout:
            logger.info("Ollama connection timeout - service not available")
        except requests.exceptions.ReadTimeout:
            logger.info("Ollama read timeout - service taking too long")
        except requests.exceptions.ConnectionError:
            logger.info("Ollama connection error - service not running")
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            
        # Return None to trigger next fallback
        return None

    async def _handle_hsbc_internal_issue(self, message: str, server_name: Optional[str], correlation_id: Optional[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle HSBC internal technical issues with LLM-powered analysis of multiple data sources
        
        Enhanced Process:
        1. Extract server name and classify issue type
        2. Collect data from ALL available sources
        3. Send consolidated data to LLM for intelligent analysis
        4. Generate comprehensive resolution response
        """
        # Extract server name if not provided
        if not server_name:
            server_name = self._extract_server_name(message)
        
        # Phase 1: Comprehensive Data Collection from Multiple Sources
        collected_data = await self._collect_technical_data(message, server_name, correlation_id)
        
        # Phase 2: LLM Analysis of Consolidated Data
        return await self._analyze_with_llm(
            message=message,
            server_name=server_name,
            collected_data=collected_data,
            analysis_type="technical_troubleshooting",
            user_context=user_context
        )

    async def _handle_monitoring_query(self, message: str, server_name: Optional[str], correlation_id: Optional[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle system monitoring queries with LLM-powered analysis
        
        Enhanced Process:
        1. Collect monitoring data from multiple sources
        2. Send consolidated data to LLM for pattern analysis
        3. Generate intelligent insights and recommendations
        """
        # Phase 1: Comprehensive Monitoring Data Collection
        monitoring_data = await self._collect_monitoring_data(message, server_name, correlation_id)
        
        # Phase 2: LLM Analysis for Intelligent Monitoring Insights
        return await self._analyze_with_llm(
            message=message,
            server_name=server_name,
            collected_data=monitoring_data,
            analysis_type="monitoring_analysis",
            user_context=user_context
        )

    async def _handle_knowledge_base_query(self, message: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle knowledge base and documentation queries with LLM-powered analysis
        
        Enhanced Process:
        1. Search across all knowledge sources (Confluence, text files, CSV)
        2. Send consolidated documentation to LLM for analysis
        3. Generate comprehensive, contextual responses
        """
        # Phase 1: Comprehensive Knowledge Collection
        knowledge_data = await self._collect_knowledge_data(message, None)
        
        # Phase 2: LLM Analysis of Documentation and Knowledge
        return await self._analyze_with_llm(
            message=message,
            server_name=None,
            collected_data=knowledge_data,
            analysis_type="knowledge_synthesis",
            user_context=user_context
        )

    async def _process_standard_query(self, message: str, server_name: Optional[str], correlation_id: Optional[str], user_context: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback to standard query processing"""
        return await self._search_enhanced_knowledge_base(message, server_name, user_context)

    def _should_create_incident(self, message: str, results: List[Dict]) -> bool:
        """Determine if an incident should be created based on knowledge results"""
        # Check for critical keywords
        critical_keywords = ['down', 'outage', 'critical', 'urgent', 'production', 'error 5', 'timeout']
        has_critical = any(keyword in message.lower() for keyword in critical_keywords)
        
        # Check if no resolution found in results
        has_resolution = any(
            result.get('resolution_steps') or result.get('snippet', '').lower().count('solution') > 0 
            for result in results
        )
        
        # Create incident if critical issue or no clear resolution
        return has_critical or not has_resolution
    
    async def _collect_technical_data(self, message: str, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect data from multiple sources for LLM analysis
        
        Returns consolidated data from:
        - CSV knowledge base (historical solutions)
        - Internal HSBC APIs (real-time server status) 
        - Splunk APIs (log analysis)
        - Ansible APIs (automation data)
        - Confluence (documentation)
        """
        collected_data = {}
        
        try:
            # CSV Knowledge Base - Historical solutions
            csv_results = self.csv_knowledge.search_issues(message, server_name)
            collected_data["csv_knowledge"] = csv_results[:3] if csv_results else []
            
            # Internal HSBC APIs - Real-time data
            hsbc_data = await self._query_hsbc_internal_apis(server_name, correlation_id)
            collected_data["hsbc_apis"] = hsbc_data
            
            # Splunk APIs - Log analysis
            splunk_data = await self._query_splunk_logs(server_name, correlation_id)
            collected_data["splunk_logs"] = splunk_data
            
            # Ansible APIs - Automation data
            ansible_data = await self._query_ansible_status(server_name)
            collected_data["ansible_data"] = ansible_data
            
            # Enhanced knowledge (Confluence, text files)
            enhanced_data = await self.enhanced_knowledge.search_all_sources(message, server_name)
            collected_data["confluence_data"] = enhanced_data.get("confluence_matches", [])
            collected_data["text_data"] = enhanced_data.get("text_matches", [])
            
        except Exception as e:
            logger.error(f"Data collection error: {e}")
            # Ensure we always return some data structure
            collected_data = {
                "csv_knowledge": self.csv_knowledge.search_issues(message, server_name) or [],
                "error": f"Partial data collection due to: {str(e)}"
            }
        
        return collected_data
    
    async def _collect_monitoring_data(self, message: str, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect monitoring-specific data from multiple sources
        """
        monitoring_data = {}
        
        try:
            # Splunk logs - priority for monitoring
            splunk_data = await self._query_splunk_logs(server_name, correlation_id)
            monitoring_data["splunk_logs"] = splunk_data
            
            # Ansible automation data
            ansible_data = await self._query_ansible_status(server_name)
            monitoring_data["ansible_data"] = ansible_data
            
            # Performance metrics from internal APIs
            performance_data = await self._query_performance_apis(server_name)
            monitoring_data["performance_metrics"] = performance_data
            
            # Alert history
            alert_data = await self._query_alert_systems(server_name)
            monitoring_data["alert_history"] = alert_data
            
            # Historical monitoring patterns from CSV
            csv_patterns = self.csv_knowledge.search_monitoring_patterns(message, server_name)
            monitoring_data["historical_patterns"] = csv_patterns
            
        except Exception as e:
            logger.error(f"Monitoring data collection error: {e}")
            monitoring_data = {"error": f"Monitoring data collection failed: {str(e)}"}
        
        return monitoring_data
    
    async def _collect_knowledge_data(self, message: str, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Collect knowledge and documentation data
        """
        knowledge_data = {}
        
        try:
            # Enhanced knowledge search (Confluence, text files)
            enhanced_results = await self.enhanced_knowledge.search_all_sources(message, server_name)
            knowledge_data["confluence_data"] = enhanced_results.get("confluence_matches", [])
            knowledge_data["text_data"] = enhanced_results.get("text_matches", [])
            
            # CSV knowledge for procedures
            csv_procedures = self.csv_knowledge.search_procedures(message)
            knowledge_data["procedures"] = csv_procedures
            
            # API documentation if relevant
            if any(term in message.lower() for term in ['api', 'endpoint', 'request', 'response']):
                api_docs = await self._search_api_documentation(message)
                knowledge_data["api_docs"] = api_docs
            
        except Exception as e:
            logger.error(f"Knowledge data collection error: {e}")
            knowledge_data = {"error": f"Knowledge data collection failed: {str(e)}"}
        
        return knowledge_data
    
    async def _analyze_with_llm(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any], analysis_type: str, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Central LLM Analysis Engine
        
        Takes collected data from multiple sources and uses LLM to:
        1. Analyze patterns and correlations across data sources
        2. Generate intelligent troubleshooting steps
        3. Provide consolidated recommendations
        4. Format responses in user-friendly manner
        """
        try:
            # Prepare structured context for LLM analysis
            analysis_context = self._prepare_llm_context(message, server_name, collected_data, analysis_type)
            
            # Primary: OpenAI GPT-4 Analysis
            if self.api_key and self.client:
                system_prompt = self._get_system_prompt(analysis_type, server_name)
                user_prompt = f"""User Query: {message}

Collected Data Analysis:
{analysis_context}

Please provide a comprehensive technical resolution response with:
1. Root cause analysis
2. Step-by-step troubleshooting guide  
3. Prevention recommendations
4. Priority assessment"""
                
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
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
                    "confidence_level": "high",
                    "incident_required": self._assess_incident_requirement(collected_data),
                    "processing_updates": ["🔍 Collected multi-source data", "🧠 LLM analysis complete"]
                }
                
        except Exception as e:
            logger.error(f"OpenAI LLM analysis error: {e}")
        
        # Fallback: Ollama Analysis
        ollama_response = await self._analyze_with_ollama(message, server_name, collected_data, analysis_type)
        if ollama_response:
            return ollama_response
            
        # Final fallback: Enhanced knowledge base response
        return self._generate_fallback_technical_response(message, server_name, collected_data)
    
    def _prepare_llm_context(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any], analysis_type: str) -> str:
        """
        Prepare structured context for LLM analysis
        Formats collected data into structured context that LLM can analyze effectively
        """
        context_parts = []
        
        # CSV Knowledge Base Results
        if collected_data.get("csv_knowledge"):
            context_parts.append("## Historical Knowledge Base:")
            for item in collected_data["csv_knowledge"][:3]:  # Top 3 matches
                context_parts.append(f"- Issue: {item.get('description', 'N/A')}")
                context_parts.append(f"  Root Cause: {item.get('root_cause', 'N/A')}")
                context_parts.append(f"  Resolution: {item.get('resolution_steps', 'N/A')}")
                context_parts.append(f"  Priority: {item.get('priority', 'N/A')}")
        
        # Splunk Log Data
        if collected_data.get("splunk_logs"):
            context_parts.append("\n## Splunk Log Analysis:")
            splunk_data = collected_data["splunk_logs"]
            context_parts.append(f"- Recent errors: {len(splunk_data.get('errors', []))}")
            context_parts.append(f"- Error patterns: {splunk_data.get('patterns', 'None detected')}")
            context_parts.append(f"- Time range: {splunk_data.get('time_range', 'Last 24 hours')}")
        
        # Ansible Automation Data  
        if collected_data.get("ansible_data"):
            context_parts.append("\n## Automation Status:")
            ansible_data = collected_data["ansible_data"]
            context_parts.append(f"- Job status: {ansible_data.get('status', 'Unknown')}")
            context_parts.append(f"- Last deployment: {ansible_data.get('last_deployment', 'N/A')}")
            context_parts.append(f"- Success rate: {ansible_data.get('success_rate', 'N/A')}")
        
        # Internal HSBC API Data
        if collected_data.get("hsbc_apis"):
            context_parts.append("\n## Real-time Server Status:")
            api_data = collected_data["hsbc_apis"]
            context_parts.append(f"- Server health: {api_data.get('health_status', 'Unknown')}")
            context_parts.append(f"- Current load: {api_data.get('current_load', 'N/A')}")
            context_parts.append(f"- Response time: {api_data.get('response_time', 'N/A')}")
        
        # Documentation/Confluence Data
        if collected_data.get("confluence_data"):
            context_parts.append("\n## Documentation References:")
            for doc in collected_data["confluence_data"][:2]:  # Top 2 relevant docs
                context_parts.append(f"- {doc.get('title', 'Untitled')}: {doc.get('summary', 'N/A')}")
        
        # Performance Metrics (for monitoring analysis)
        if collected_data.get("performance_metrics"):
            context_parts.append("\n## Performance Metrics:")
            perf_data = collected_data["performance_metrics"]
            context_parts.append(f"- CPU usage: {perf_data.get('cpu_usage', 'N/A')}")
            context_parts.append(f"- Memory usage: {perf_data.get('memory_usage', 'N/A')}")
            context_parts.append(f"- Disk I/O: {perf_data.get('disk_io', 'N/A')}")
        
        # Error handling
        if collected_data.get("error"):
            context_parts.append(f"\n## Data Collection Notes:\n- {collected_data['error']}")
        
        return "\n".join(context_parts)
    
    def _get_system_prompt(self, analysis_type: str, server_name: Optional[str]) -> str:
        """
        Get appropriate system prompt based on analysis type
        """
        base_prompt = f"""You are an expert HSBC technical support analyst specializing in {analysis_type}.
Server Context: {server_name or 'Multiple servers'}
Your role is to provide comprehensive technical analysis and resolution guidance.

Analyze the provided data and deliver:
1. **Root Cause Analysis** - Clear explanation of what's causing the issue
2. **Step-by-step Troubleshooting Guide** - Actionable resolution steps
3. **Prevention Recommendations** - How to avoid similar issues
4. **Priority Assessment** - Urgency and business impact
5. **Supporting Evidence** - Reference the data sources that support your analysis

Format your response professionally with clear sections and actionable steps.
Use technical accuracy while remaining accessible to the support team."""
        
        return base_prompt
    
    def _assess_incident_requirement(self, collected_data: Dict[str, Any]) -> bool:
        """
        Assess if an incident ticket should be created based on collected data
        """
        # Check for high-priority indicators
        csv_data = collected_data.get("csv_knowledge", [])
        for item in csv_data:
            if item.get("priority") in ["high", "critical"]:
                return True
        
        # Check Splunk for multiple errors
        splunk_data = collected_data.get("splunk_logs", {})
        if len(splunk_data.get("errors", [])) > 10:
            return True
            
        # Check server health status
        api_data = collected_data.get("hsbc_apis", {})
        if api_data.get("health_status") in ["critical", "down", "error"]:
            return True
            
        return False
    
    async def _query_hsbc_internal_apis(self, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query internal HSBC APIs for real-time server status
        """
        try:
            # Mock implementation - replace with actual HSBC API calls
            if server_name:
                # Simulate server health check
                return {
                    "health_status": "healthy",
                    "current_load": "65%",
                    "response_time": "150ms",
                    "last_restart": "2024-11-15 08:30:00",
                    "uptime": "72 hours",
                    "region": self._get_server_region(server_name)
                }
            return {"status": "no_server_specified"}
            
        except Exception as e:
            logger.error(f"HSBC API query error: {e}")
            return {"error": f"API unavailable: {str(e)}"}
    
    async def _query_splunk_logs(self, server_name: Optional[str] = None, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query Splunk API for log analysis
        """
        try:
            # Mock implementation - replace with actual Splunk API calls
            return {
                "errors": [
                    {"timestamp": "2024-11-18 14:30:00", "level": "ERROR", "message": "Authentication failed"},
                    {"timestamp": "2024-11-18 14:25:00", "level": "WARN", "message": "High response time"}
                ],
                "patterns": "JWT token expiration pattern detected",
                "time_range": "Last 24 hours",
                "total_events": 1247,
                "error_rate": "2.3%"
            }
            
        except Exception as e:
            logger.error(f"Splunk API query error: {e}")
            return {"error": f"Splunk unavailable: {str(e)}"}
    
    async def _query_ansible_status(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query Ansible API for automation data
        """
        try:
            # Mock implementation - replace with actual Ansible API calls
            return {
                "status": "successful",
                "last_deployment": "2024-11-18 12:00:00",
                "success_rate": "94.5%",
                "pending_jobs": 2,
                "last_job_id": "JOB_12345",
                "playbook": "deploy_api_updates.yml"
            }
            
        except Exception as e:
            logger.error(f"Ansible API query error: {e}")
            return {"error": f"Ansible unavailable: {str(e)}"}
    
    async def _query_performance_apis(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query performance monitoring APIs
        """
        try:
            # Mock implementation - replace with actual performance monitoring APIs
            return {
                "cpu_usage": "72%",
                "memory_usage": "84%",
                "disk_io": "45 MB/s",
                "network_throughput": "120 Mbps",
                "response_times": {"avg": "150ms", "p95": "300ms", "p99": "500ms"}
            }
            
        except Exception as e:
            logger.error(f"Performance API query error: {e}")
            return {"error": f"Performance monitoring unavailable: {str(e)}"}
    
    async def _query_alert_systems(self, server_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Query alert and monitoring systems
        """
        try:
            # Mock implementation - replace with actual alert system APIs
            return {
                "active_alerts": [
                    {"severity": "warning", "message": "High CPU usage detected", "timestamp": "2024-11-18 14:20:00"},
                    {"severity": "info", "message": "Deployment completed", "timestamp": "2024-11-18 12:00:00"}
                ],
                "alert_count_24h": 15,
                "resolved_count_24h": 12
            }
            
        except Exception as e:
            logger.error(f"Alert system query error: {e}")
            return {"error": f"Alert system unavailable: {str(e)}"}
    
    async def _search_api_documentation(self, message: str) -> Dict[str, Any]:
        """
        Search API documentation for relevant information
        """
        try:
            # Mock implementation - replace with actual API documentation search
            return {
                "endpoints": [
                    {"endpoint": "/api/auth/login", "method": "POST", "description": "User authentication"},
                    {"endpoint": "/api/users/{id}", "method": "GET", "description": "Get user details"}
                ],
                "examples": [
                    {"title": "Authentication Example", "code": "curl -X POST /api/auth/login -H 'Content-Type: application/json' -d '{\"username\":\"user\", \"password\":\"pass\"}'"},
                ]
            }
            
        except Exception as e:
            logger.error(f"API documentation search error: {e}")
            return {"error": f"API documentation unavailable: {str(e)}"}
    
    def _get_server_region(self, server_name: str) -> str:
        """
        Determine server region from server name
        """
        if not server_name:
            return "Unknown"
            
        prefix = server_name.split('-')[0].lower()
        region_map = {
            'gb': 'UK', 'cn': 'China', 'hk': 'Hong Kong', 'vn': 'Vietnam',
            'mx': 'Mexico', 'us': 'United States', 'ca': 'Canada', 
            'au': 'Australia', 'sg': 'Singapore', 'my': 'Malaysia',
            'in': 'India', 'ae': 'UAE', 'fr': 'France', 'de': 'Germany'
        }
        return region_map.get(prefix, 'Unknown')
    
    async def _analyze_with_ollama(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any], analysis_type: str) -> Optional[Dict[str, Any]]:
        """
        Fallback LLM analysis using Ollama
        """
        try:
            # Prepare context for Ollama
            context = self._prepare_llm_context(message, server_name, collected_data, analysis_type)
            
            # Ollama API call
            ollama_prompt = f"""You are an HSBC technical support analyst. Analyze this data and provide comprehensive troubleshooting guidance.

User Query: {message}
Server: {server_name or 'Not specified'}
Analysis Type: {analysis_type}

Data Analysis:
{context}

Provide:
1. Root cause analysis
2. Step-by-step resolution steps
3. Prevention recommendations
4. Priority assessment

Be specific, actionable, and professional."""
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": ollama_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 800
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                ollama_response = result.get('response', '')
                
                if ollama_response:
                    return {
                        "message": f"🔧 **Technical Analysis & Resolution (Llama 3.2)**\n\n{ollama_response}",
                        "ai_service_used": "ollama_technical_analysis",
                        "data_sources": list(collected_data.keys()),
                        "server_name": server_name,
                        "analysis_type": analysis_type,
                        "confidence_level": "medium"
                    }
            
        except Exception as e:
            logger.error(f"Ollama analysis error: {e}")
            
        return None
    
    def _generate_fallback_technical_response(self, message: str, server_name: Optional[str], collected_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fallback response when both OpenAI and Ollama fail
        """
        # Use collected data to generate basic response
        csv_data = collected_data.get("csv_knowledge", [])
        
        if csv_data:
            best_match = csv_data[0]
            response = f"""🔧 **Technical Issue Analysis**

**Server**: {server_name or 'Not specified'}
**Issue**: {message}

**Based on Historical Data**:
- **Root Cause**: {best_match.get('root_cause', 'Analysis required')}
- **Resolution Steps**: 
{self._format_resolution_steps(best_match.get('resolution_steps', 'Contact support'))}

**Data Sources**: {', '.join(collected_data.keys())}

*Note: This response is based on knowledge base matching. For complex issues, consider creating an incident ticket.*"""
        else:
            response = f"""🔧 **Technical Issue Analysis**

**Server**: {server_name or 'Not specified'}
**Issue**: {message}

**Initial Assessment**:
1. Verify server connectivity
2. Check system logs for errors
3. Review recent changes or deployments
4. Contact support if issue persists

**Data Collection Status**: {len(collected_data)} sources queried
**Recommendation**: Create incident ticket for detailed investigation"""
        
        return {
            "message": response,
            "ai_service_used": "fallback_analysis",
            "data_sources": list(collected_data.keys()),
            "server_name": server_name,
            "incident_required": True,
            "confidence_level": "low"
        }
    
    def _extract_server_name(self, message: str) -> Optional[str]:
        """
        Extract HSBC server name from message using regex patterns
        """
        import re
        # HSBC server naming patterns (country-type-number)
        server_patterns = [
            r'\b(gb|cn|hk|vn|mx|us|ca|au|sg|my|in|ae|fr|de)-[a-zA-Z0-9-]+\b'
        ]
        
        for pattern in server_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(0).lower()
        
        return None
    
    async def _create_incident_if_required(self, response_data: Dict[str, Any], conversation_id: Optional[int], 
                                         message: str, server_name: Optional[str], correlation_id: Optional[str],
                                         category: Optional[str] = None, user_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create incident record if required by the response
        """
        if not response_data.get("incident_required", False) or not conversation_id:
            return response_data
        
        try:
            # Create database session
            db = SessionLocal()
            
            # Generate incident ID
            incident_count = db.query(QueryResolution).count()
            incident_id = f"INC-{incident_count + 1:06d}"
            
            # Determine query type from response metadata
            query_type = "other"
            if response_data.get("metadata", {}).get("query_analysis", {}).get("query_type"):
                query_type = response_data["metadata"]["query_analysis"]["query_type"]
            
            # Create incident record
            incident = QueryResolution(
                conversation_id=conversation_id,
                query_type=query_type,
                server_name=server_name,
                correlation_id=correlation_id,
                root_cause=response_data.get("metadata", {}).get("root_cause"),
                resolution_steps=response_data.get("message", ""),
                data_sources_used=response_data.get("data_sources", []),
                incident_created=True,
                incident_id=incident_id,
                resolved_automatically=False
            )
            
            db.add(incident)
            db.commit()
            db.refresh(incident)
            
            # Update response to include incident information
            response_data["incident_created"] = True
            response_data["incident_id"] = incident_id
            response_data["message"] = f"""🚨 **Incident Created: {incident_id}**

{response_data['message']}

---
**📋 Incident Details:**
- **Incident ID**: {incident_id}
- **Server**: {server_name or 'Not specified'}
- **Type**: {query_type.replace('_', ' ').title()}
- **Created By**: {user_context.get('full_name', 'Unknown') if user_context else 'Unknown'}

This incident has been logged for tracking and follow-up by the support team."""
            
            db.close()
            
        except Exception as e:
            logger.error(f"Failed to create incident: {e}")
            response_data["incident_creation_error"] = str(e)
        
        return response_data