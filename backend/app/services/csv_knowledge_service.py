import csv
import os
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

class CSVKnowledgeService:
    def __init__(self, csv_path: str = "/root/Bot/backend/data/knowledge_base.csv"):
        self.csv_path = csv_path
        self.ensure_csv_exists()
    
    def ensure_csv_exists(self):
        """Ensure the CSV file and directory exist"""
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path):
            # Create empty CSV with headers
            headers = [
                'server_name', 'issue_type', 'error_code', 'description', 
                'resolution_steps', 'username', 'reported_date', 'status', 
                'priority', 'correlation_id'
            ]
            with open(self.csv_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
    
    async def search_knowledge_base(
        self,
        server_name: Optional[str] = None,
        issue_type: Optional[str] = None,
        username: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge base with multiple criteria
        """
        try:
            df = pd.read_csv(self.csv_path)
            
            # Check if we have insufficient search criteria
            provided_criteria = sum([
                1 for param in [server_name, issue_type, username, error_code] 
                if param and str(param).lower() not in ['n/a', 'none', '']
            ])
            
            # Allow single criteria search if it's a server name (most specific identifier)
            if provided_criteria < 2 and not server_name:
                # Not enough criteria for reliable search (unless we have server_name)
                return []
            
            # Apply filters
            filtered_df = df.copy()
            
            # Count matching criteria to ensure we have enough specificity
            match_count = 0
            
            if server_name:
                filtered_df = filtered_df[
                    filtered_df['server_name'].str.lower() == server_name.lower()
                ]
                match_count += 1
            
            if issue_type:
                filtered_df = filtered_df[
                    filtered_df['issue_type'].str.lower() == issue_type.lower()
                ]
                match_count += 1
            
            if username:
                filtered_df = filtered_df[
                    filtered_df['username'].str.lower() == username.lower()
                ]
                match_count += 1
            
            if error_code and str(error_code) != 'N/A':
                filtered_df = filtered_df[
                    filtered_df['error_code'].astype(str) == str(error_code)
                ]
                match_count += 1
            
            # Only return results if we have at least 2 matching criteria
            # Exception: server_name alone is acceptable since it's a specific identifier
            if match_count < 2 and not (match_count == 1 and server_name):
                return []
            
            # Convert to list of dictionaries
            results = filtered_df.to_dict('records')
            
            return results
            
        except Exception as e:
            print(f"Error searching knowledge base: {e}")
            return []
    
    async def add_entry(
        self,
        server_name: str,
        issue_type: str,
        error_code: str,
        description: str,
        resolution_steps: str,
        username: str,
        priority: str = "medium",
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Add a new entry to the knowledge base
        """
        try:
            new_entry = {
                'server_name': server_name,
                'issue_type': issue_type,
                'error_code': error_code,
                'description': description,
                'resolution_steps': resolution_steps,
                'username': username,
                'reported_date': datetime.now().strftime('%Y-%m-%d'),
                'status': 'open',
                'priority': priority,
                'correlation_id': correlation_id or f"CID{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
            
            # Append to CSV
            with open(self.csv_path, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=new_entry.keys())
                writer.writerow(new_entry)
            
            return True
            
        except Exception as e:
            print(f"Error adding entry to knowledge base: {e}")
            return False
    
    async def update_status(self, correlation_id: str, status: str) -> bool:
        """
        Update the status of an existing entry
        """
        try:
            df = pd.read_csv(self.csv_path)
            
            # Update status where correlation_id matches
            df.loc[df['correlation_id'] == correlation_id, 'status'] = status
            
            # Save back to CSV
            df.to_csv(self.csv_path, index=False)
            
            return True
            
        except Exception as e:
            print(f"Error updating status: {e}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics from the knowledge base
        """
        try:
            df = pd.read_csv(self.csv_path)
            
            stats = {
                'total_entries': len(df),
                'open_issues': len(df[df['status'] == 'open']),
                'resolved_issues': len(df[df['status'] == 'resolved']),
                'by_issue_type': df['issue_type'].value_counts().to_dict(),
                'by_priority': df['priority'].value_counts().to_dict(),
                'by_server': df['server_name'].value_counts().head(10).to_dict(),
                'recent_entries': len(df[df['reported_date'] >= datetime.now().strftime('%Y-%m-%d')])
            }
            
            return stats
            
        except Exception as e:
            print(f"Error getting statistics: {e}")
            return {}
    
    async def find_similar_issues(
        self, 
        description: str, 
        server_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Find similar issues based on description keywords
        """
        try:
            df = pd.read_csv(self.csv_path)
            
            # Extract keywords from description
            keywords = [word.lower() for word in description.split() if len(word) > 3]
            
            # Score entries based on keyword matches
            def calculate_similarity(row):
                desc_lower = str(row['description']).lower()
                resolution_lower = str(row['resolution_steps']).lower()
                
                score = 0
                for keyword in keywords:
                    if keyword in desc_lower:
                        score += 2
                    if keyword in resolution_lower:
                        score += 1
                
                # Bonus for same server
                if server_name and server_name.lower() in str(row['server_name']).lower():
                    score += 3
                
                return score
            
            df['similarity_score'] = df.apply(calculate_similarity, axis=1)
            
            # Return top matches with score > 0
            similar_issues = df[df['similarity_score'] > 0].sort_values(
                'similarity_score', ascending=False
            ).head(5).to_dict('records')
            
            return similar_issues
            
        except Exception as e:
            print(f"Error finding similar issues: {e}")
            return []