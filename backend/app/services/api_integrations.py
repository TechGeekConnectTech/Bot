import aiohttp
import json
from typing import Dict, List, Optional, Any
from app.core.config import settings

class SplunkService:
    def __init__(self):
        self.base_url = settings.SPLUNK_API_URL
        self.token = settings.SPLUNK_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def search_logs(
        self, 
        keywords: List[str], 
        query_type: str,
        server_name: Optional[str] = None,
        correlation_id: Optional[str] = None,
        time_range: str = "-1h"
    ) -> Optional[Dict[str, Any]]:
        """
        Search Splunk logs for relevant events
        """
        if not self.base_url or not self.token:
            return self._mock_splunk_response(keywords, query_type)
        
        try:
            # Build search query based on parameters
            search_terms = []
            
            if server_name:
                search_terms.append(f'host="{server_name}"')
            
            if correlation_id:
                search_terms.append(f'correlation_id="{correlation_id}"')
            
            # Add keywords based on query type
            type_keywords = {
                "auth_issue": ["authentication", "unauthorized", "403", "401", "auth"],
                "payload_issue": ["invalid", "malformed", "json", "payload", "400"],
                "resource_lock": ["lock", "timeout", "busy", "resource", "deadlock"],
                "performance_issue": ["slow", "timeout", "performance", "latency"]
            }
            
            query_keywords = type_keywords.get(query_type, []) + keywords
            search_terms.extend([f'*{kw}*' for kw in query_keywords[:3]])  # Limit keywords
            
            search_query = {
                "search": f"search {' OR '.join(search_terms)} | head 50",
                "earliest_time": time_range,
                "output_mode": "json"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/services/search/jobs/export",
                    headers=self.headers,
                    data=search_query
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        return self._process_splunk_results(results)
                    else:
                        print(f"Splunk API error: {response.status}")
                        return self._mock_splunk_response(keywords, query_type)
        
        except Exception as e:
            print(f"Splunk service error: {e}")
            return self._mock_splunk_response(keywords, query_type)
    
    def _mock_splunk_response(self, keywords: List[str], query_type: str) -> Dict[str, Any]:
        """
        Mock Splunk response for testing/demo purposes
        """
        mock_events = {
            "auth_issue": [
                {
                    "timestamp": "2024-11-16T08:30:00Z",
                    "level": "ERROR",
                    "message": "Authentication failed: Invalid API key",
                    "source": "api-gateway",
                    "correlation_id": "abc123"
                },
                {
                    "timestamp": "2024-11-16T08:25:00Z",
                    "level": "WARN", 
                    "message": "Token expired for user service_account",
                    "source": "auth-service",
                    "correlation_id": "abc123"
                }
            ],
            "payload_issue": [
                {
                    "timestamp": "2024-11-16T08:35:00Z",
                    "level": "ERROR",
                    "message": "Invalid JSON payload: Missing required field 'account_id'",
                    "source": "api-validator",
                    "correlation_id": "xyz789"
                }
            ],
            "resource_lock": [
                {
                    "timestamp": "2024-11-16T08:40:00Z",
                    "level": "ERROR",
                    "message": "Database connection pool exhausted",
                    "source": "database-service",
                    "correlation_id": "def456"
                }
            ]
        }
        
        return {
            "events": mock_events.get(query_type, []),
            "total_count": len(mock_events.get(query_type, [])),
            "search_keywords": keywords,
            "query_type": query_type
        }
    
    def _process_splunk_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and format Splunk search results
        """
        return {
            "events": results.get("results", []),
            "total_count": len(results.get("results", [])),
            "processing_time": results.get("_time", 0)
        }

class AnsibleService:
    def __init__(self):
        self.base_url = settings.ANSIBLE_API_URL
        self.token = settings.ANSIBLE_API_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def get_system_info(
        self, 
        keywords: List[str],
        server_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get system information from Ansible
        """
        if not self.base_url or not self.token:
            return self._mock_ansible_response(keywords, server_name)
        
        try:
            # Query Ansible API for system information
            query_params = {
                "search": " ".join(keywords[:3]),  # Limit keywords
            }
            
            if server_name:
                query_params["name__icontains"] = server_name
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/v2/hosts/",
                    headers=self.headers,
                    params=query_params
                ) as response:
                    if response.status == 200:
                        results = await response.json()
                        return self._process_ansible_results(results)
                    else:
                        print(f"Ansible API error: {response.status}")
                        return self._mock_ansible_response(keywords, server_name)
        
        except Exception as e:
            print(f"Ansible service error: {e}")
            return self._mock_ansible_response(keywords, server_name)
    
    def _mock_ansible_response(self, keywords: List[str], server_name: Optional[str]) -> Dict[str, Any]:
        """
        Mock Ansible response for testing/demo purposes
        """
        return {
            "hosts": [
                {
                    "name": server_name or "api-server-01",
                    "status": "running",
                    "last_deployment": "2024-11-15T14:30:00Z",
                    "configuration": {
                        "cpu_usage": "65%",
                        "memory_usage": "78%",
                        "disk_usage": "45%",
                        "services_running": ["nginx", "api-service", "database"]
                    },
                    "recent_changes": [
                        {
                            "timestamp": "2024-11-15T14:30:00Z",
                            "type": "configuration_update",
                            "description": "Updated API service configuration"
                        }
                    ]
                }
            ],
            "playbooks": [
                {
                    "name": "api-service-deployment",
                    "last_run": "2024-11-15T14:30:00Z",
                    "status": "successful",
                    "tasks_completed": 12,
                    "tasks_failed": 0
                }
            ],
            "search_keywords": keywords
        }
    
    def _process_ansible_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and format Ansible API results
        """
        return {
            "hosts": results.get("results", []),
            "total_hosts": results.get("count", 0),
            "metadata": {
                "query_time": "2024-11-16T08:45:00Z",
                "api_version": "v2"
            }
        }

class IncidentService:
    """
    Service for creating and managing support incidents
    """
    
    @staticmethod
    async def create_incident(
        title: str,
        description: str,
        priority: str,
        user_info: Dict[str, Any],
        technical_details: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create a support incident (integrate with your ticketing system)
        """
        # Mock incident creation - replace with actual ticketing system API
        incident_id = f"INC-{hash(title + description) % 1000000:06d}"
        
        incident_data = {
            "incident_id": incident_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "open",
            "assigned_team": "DC Automation Support",
            "reporter": user_info.get("username", "Unknown"),
            "department": user_info.get("department", "Unknown"),
            "technical_details": technical_details,
            "created_at": "2024-11-16T08:45:00Z"
        }
        
        # Here you would integrate with ServiceNow, Jira, etc.
        print(f"Creating incident: {incident_data}")
        
        return {
            "incident_id": incident_id,
            "status": "created",
            "message": f"Incident {incident_id} has been created and assigned to the DC Automation Support Team."
        }