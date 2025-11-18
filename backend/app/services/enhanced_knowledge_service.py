import pandas as pd
import logging
from typing import List, Dict, Optional
import os
import requests
import re
from datetime import datetime
import json
from bs4 import BeautifulSoup
import asyncio

logger = logging.getLogger(__name__)

class EnhancedKnowledgeService:
    def __init__(self):
        self.csv_file_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'knowledge_base.csv')
        self.text_kb_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'text_knowledge')
        self.confluence_config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'confluence_config.json')
        self.knowledge_data = None
        self.text_knowledge = []
        self.confluence_knowledge = []
        self.confluence_config = self.load_confluence_config()
        self.load_all_knowledge_sources()
    
    def load_confluence_config(self):
        """Load Confluence configuration"""
        try:
            if os.path.exists(self.confluence_config_path):
                with open(self.confluence_config_path, 'r') as f:
                    return json.load(f)
            else:
                # Create default config file
                default_config = {
                    "base_url": "https://your-company.atlassian.net",
                    "username": "your-email@company.com",
                    "api_token": "your-api-token",
                    "space_key": "DC",
                    "enabled": False,
                    "pages": [
                        {"title": "API Troubleshooting Guide", "id": ""},
                        {"title": "Server Management", "id": ""},
                        {"title": "Common Issues", "id": ""}
                    ]
                }
                os.makedirs(os.path.dirname(self.confluence_config_path), exist_ok=True)
                with open(self.confluence_config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info(f"Created default Confluence config at: {self.confluence_config_path}")
                return default_config
        except Exception as e:
            logger.error(f"Error loading Confluence config: {str(e)}")
            return {}
    
    def load_all_knowledge_sources(self):
        """Load knowledge from all sources: CSV, text files, and Confluence"""
        self.load_csv_knowledge_base()
        self.load_text_knowledge_base()
        if self.confluence_config.get('enabled', False):
            self.load_confluence_knowledge()
    
    def load_csv_knowledge_base(self):
        """Load the CSV knowledge base into memory"""
        try:
            if os.path.exists(self.csv_file_path):
                self.knowledge_data = pd.read_csv(self.csv_file_path)
                logger.info(f"CSV knowledge base loaded successfully with {len(self.knowledge_data)} entries")
            else:
                logger.warning(f"CSV knowledge base file not found: {self.csv_file_path}")
                self.knowledge_data = pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading CSV knowledge base: {str(e)}")
            self.knowledge_data = pd.DataFrame()
    
    def load_text_knowledge_base(self):
        """Load text-based knowledge files"""
        try:
            self.text_knowledge = []
            if not os.path.exists(self.text_kb_path):
                os.makedirs(self.text_kb_path, exist_ok=True)
                # Create sample text knowledge files
                self.create_sample_text_files()
                logger.info(f"Created text knowledge directory: {self.text_kb_path}")
            
            for filename in os.listdir(self.text_kb_path):
                if filename.endswith(('.txt', '.md')):
                    file_path = os.path.join(self.text_kb_path, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.text_knowledge.append({
                            'filename': filename,
                            'title': filename.replace('.txt', '').replace('.md', '').replace('_', ' ').title(),
                            'content': content,
                            'source': 'text_file',
                            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        })
            
            logger.info(f"Text knowledge base loaded with {len(self.text_knowledge)} documents")
        except Exception as e:
            logger.error(f"Error loading text knowledge base: {str(e)}")
            self.text_knowledge = []
    
    def create_sample_text_files(self):
        """Create sample text knowledge files for demonstration"""
        sample_files = {
            "api_authentication_guide.md": """# API Authentication Guide

## Overview
This guide covers common authentication issues and their resolutions.

## Common Authentication Errors

### 401 Unauthorized
- **Cause**: Invalid or expired API key
- **Solution**: 
  1. Verify API key format
  2. Check expiration date
  3. Regenerate key if needed
  4. Update client configuration

### 403 Forbidden
- **Cause**: Insufficient permissions
- **Solution**:
  1. Check user permissions
  2. Verify role assignments
  3. Contact admin for access

## Best Practices
- Rotate API keys regularly
- Use environment variables for keys
- Implement proper error handling
""",
            
            "server_maintenance_procedures.txt": """Server Maintenance Procedures

Load Balancer (srv-lb-01):
- Check connection pool status
- Monitor CPU and memory usage
- Verify upstream server health
- Check logs for connection errors

Database Servers (srv-db-01, srv-db-02):
- Monitor connection counts
- Check for deadlocks
- Verify replication status
- Review slow query logs

Web Servers (srv-web-01, srv-web-02):
- Check application logs
- Monitor response times
- Verify SSL certificates
- Review access logs

Cache Servers (srv-cache-01):
- Monitor memory usage
- Check cache hit rates
- Verify cache expiration policies
- Review eviction logs
""",
            
            "troubleshooting_playbook.md": """# Troubleshooting Playbook

## High CPU Usage
1. Identify top processes using htop or ps
2. Check for runaway processes
3. Review application logs
4. Scale horizontally if needed

## Memory Issues
1. Check memory usage with free -h
2. Identify memory leaks
3. Review application metrics
4. Restart services if necessary

## Network Problems
1. Test connectivity with ping/telnet
2. Check firewall rules
3. Verify DNS resolution
4. Monitor bandwidth usage

## Database Performance
1. Check active connections
2. Review slow queries
3. Analyze execution plans
4. Consider index optimization
"""
        }
        
        for filename, content in sample_files.items():
            file_path = os.path.join(self.text_kb_path, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def load_confluence_knowledge(self):
        """Load knowledge from Confluence pages"""
        try:
            self.confluence_knowledge = []
            if not all(key in self.confluence_config for key in ['base_url', 'username', 'api_token', 'space_key']):
                logger.warning("Confluence configuration incomplete")
                return
            
            # Get pages from Confluence space
            pages = self.get_confluence_pages()
            for page in pages:
                content = self.get_confluence_page_content(page['id'])
                if content:
                    self.confluence_knowledge.append({
                        'page_id': page['id'],
                        'title': page['title'],
                        'content': content,
                        'source': 'confluence',
                        'url': f"{self.confluence_config['base_url']}/wiki{page['_links']['webui']}",
                        'last_modified': page.get('version', {}).get('when', '')
                    })
            
            logger.info(f"Confluence knowledge base loaded with {len(self.confluence_knowledge)} pages")
        except Exception as e:
            logger.error(f"Error loading Confluence knowledge: {str(e)}")
            self.confluence_knowledge = []
    
    def get_confluence_pages(self):
        """Get pages from Confluence space"""
        try:
            auth = (self.confluence_config['username'], self.confluence_config['api_token'])
            url = f"{self.confluence_config['base_url']}/wiki/rest/api/content"
            params = {
                'spaceKey': self.confluence_config['space_key'],
                'expand': 'version',
                'limit': 50
            }
            
            response = requests.get(url, auth=auth, params=params, timeout=30)
            response.raise_for_status()
            
            return response.json().get('results', [])
        except Exception as e:
            logger.error(f"Error fetching Confluence pages: {str(e)}")
            return []
    
    def get_confluence_page_content(self, page_id: str):
        """Get content of a specific Confluence page"""
        try:
            auth = (self.confluence_config['username'], self.confluence_config['api_token'])
            url = f"{self.confluence_config['base_url']}/wiki/rest/api/content/{page_id}"
            params = {'expand': 'body.storage'}
            
            response = requests.get(url, auth=auth, params=params, timeout=30)
            response.raise_for_status()
            
            page_data = response.json()
            html_content = page_data.get('body', {}).get('storage', {}).get('value', '')
            
            # Convert HTML to plain text
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        except Exception as e:
            logger.error(f"Error fetching Confluence page content: {str(e)}")
            return None
    
    def search_all_knowledge_sources(self, query: str, server_name: str = None) -> List[Dict]:
        """Search across all knowledge sources: CSV, text files, and Confluence"""
        all_results = []
        
        # Search CSV knowledge base
        csv_results = self.search_csv_knowledge(query, server_name)
        all_results.extend(csv_results)
        
        # Search text knowledge base
        text_results = self.search_text_knowledge(query)
        all_results.extend(text_results)
        
        # Search Confluence knowledge (if enabled)
        if self.confluence_config.get('enabled', False):
            confluence_results = self.search_confluence_knowledge(query)
            all_results.extend(confluence_results)
        
        # Sort by relevance score and return top results
        all_results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
        return all_results[:10]  # Return top 10 results
    
    def search_csv_knowledge(self, query: str, server_name: str = None) -> List[Dict]:
        """Search the CSV knowledge base"""
        results = []
        
        try:
            if self.knowledge_data is None or self.knowledge_data.empty:
                return results
            
            query_lower = query.lower()
            
            for _, row in self.knowledge_data.iterrows():
                relevance_score = 0
                
                # Check server name match
                if server_name and str(row.get('server_name', '')).lower() == server_name.lower():
                    relevance_score += 3
                
                # Check description match
                if query_lower in str(row.get('description', '')).lower():
                    relevance_score += 2
                
                # Check resolution steps match
                if query_lower in str(row.get('resolution_steps', '')).lower():
                    relevance_score += 2
                
                # Check issue type match
                if query_lower in str(row.get('issue_type', '')).lower():
                    relevance_score += 1
                
                if relevance_score > 0:
                    results.append({
                        'source': 'csv_knowledge',
                        'server_name': row.get('server_name', 'N/A'),
                        'issue_description': row.get('description', 'N/A'),
                        'resolution_steps': row.get('resolution_steps', 'N/A'),
                        'created_by': row.get('username', 'N/A'),
                        'created_at': row.get('reported_date', 'N/A'),
                        'issue_type': row.get('issue_type', 'N/A'),
                        'relevance_score': relevance_score
                    })
        
        except Exception as e:
            logger.error(f"Error searching CSV knowledge: {str(e)}")
        
        return results
    
    def search_text_knowledge(self, query: str) -> List[Dict]:
        """Search through text-based knowledge files"""
        results = []
        query_lower = query.lower()
        
        for doc in self.text_knowledge:
            content_lower = doc['content'].lower()
            title_lower = doc['title'].lower()
            
            relevance_score = 0
            
            # Title matches are highly relevant
            if query_lower in title_lower:
                relevance_score += 3
            
            # Content matches
            content_matches = content_lower.count(query_lower)
            relevance_score += min(content_matches, 5)  # Cap at 5 points
            
            if relevance_score > 0:
                # Extract relevant snippet
                snippet = self._extract_relevant_snippet(doc['content'], query, max_length=300)
                
                results.append({
                    'source': 'text_knowledge',
                    'title': doc['title'],
                    'snippet': snippet,
                    'filename': doc['filename'],
                    'last_modified': doc['last_modified'],
                    'match_type': 'text_document',
                    'relevance_score': relevance_score
                })
        
        return results
    
    def search_confluence_knowledge(self, query: str) -> List[Dict]:
        """Search through Confluence pages"""
        results = []
        query_lower = query.lower()
        
        for page in self.confluence_knowledge:
            content_lower = page['content'].lower()
            title_lower = page['title'].lower()
            
            relevance_score = 0
            
            # Title matches are highly relevant
            if query_lower in title_lower:
                relevance_score += 3
            
            # Content matches
            content_matches = content_lower.count(query_lower)
            relevance_score += min(content_matches, 5)  # Cap at 5 points
            
            if relevance_score > 0:
                # Extract relevant snippet
                snippet = self._extract_relevant_snippet(page['content'], query, max_length=300)
                
                results.append({
                    'source': 'confluence',
                    'title': page['title'],
                    'snippet': snippet,
                    'page_id': page['page_id'],
                    'url': page['url'],
                    'last_modified': page['last_modified'],
                    'match_type': 'confluence_page',
                    'relevance_score': relevance_score
                })
        
        return results
    
    def _extract_relevant_snippet(self, content: str, query: str, max_length: int = 300) -> str:
        """Extract a relevant snippet from content around the query match"""
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find the position of the query in the content
        match_pos = content_lower.find(query_lower)
        if match_pos == -1:
            # If no exact match, return the beginning of the content
            return content[:max_length] + ('...' if len(content) > max_length else '')
        
        # Calculate snippet boundaries
        start_pos = max(0, match_pos - max_length // 2)
        end_pos = min(len(content), start_pos + max_length)
        
        # Adjust start_pos if end_pos reached content end
        start_pos = max(0, end_pos - max_length)
        
        snippet = content[start_pos:end_pos]
        
        # Add ellipsis if needed
        if start_pos > 0:
            snippet = '...' + snippet
        if end_pos < len(content):
            snippet = snippet + '...'
        
        return snippet
    
    def add_text_knowledge(self, title: str, content: str, format_type: str = 'md') -> bool:
        """Add new text-based knowledge"""
        try:
            filename = f"{title.lower().replace(' ', '_')}.{format_type}"
            file_path = os.path.join(self.text_kb_path, filename)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Reload text knowledge base
            self.load_text_knowledge_base()
            logger.info(f"Added new text knowledge: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding text knowledge: {str(e)}")
            return False
    
    def update_confluence_config(self, config: Dict) -> bool:
        """Update Confluence configuration"""
        try:
            with open(self.confluence_config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.confluence_config = config
            
            # Reload Confluence knowledge if enabled
            if config.get('enabled', False):
                self.load_confluence_knowledge()
            
            logger.info("Confluence configuration updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating Confluence config: {str(e)}")
            return False
    
    def get_knowledge_sources_status(self) -> Dict:
        """Get status of all knowledge sources"""
        return {
            'csv_knowledge': {
                'enabled': True,
                'entries': len(self.knowledge_data) if self.knowledge_data is not None else 0,
                'last_loaded': datetime.now().isoformat()
            },
            'text_knowledge': {
                'enabled': True,
                'documents': len(self.text_knowledge),
                'path': self.text_kb_path
            },
            'confluence': {
                'enabled': self.confluence_config.get('enabled', False),
                'pages': len(self.confluence_knowledge),
                'space_key': self.confluence_config.get('space_key', ''),
                'base_url': self.confluence_config.get('base_url', '')
            }
        }
    
    async def refresh_all_sources(self):
        """Refresh all knowledge sources"""
        try:
            self.load_all_knowledge_sources()
            logger.info("All knowledge sources refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Error refreshing knowledge sources: {str(e)}")
            return False