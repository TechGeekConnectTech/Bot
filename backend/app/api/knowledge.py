from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Dict, List, Optional
import json
from app.api.auth import get_current_user, get_admin_user as get_current_admin_user
from app.models.user import User
from app.services.enhanced_knowledge_service import EnhancedKnowledgeService

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Management"])

knowledge_service = EnhancedKnowledgeService()

@router.get("/sources/status")
async def get_knowledge_sources_status(current_user: User = Depends(get_current_user)):
    """Get status of all knowledge sources"""
    return knowledge_service.get_knowledge_sources_status()

@router.get("/search")
async def search_knowledge(
    query: str,
    server_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Search across all knowledge sources"""
    results = knowledge_service.search_all_knowledge_sources(query, server_name)
    return {
        "query": query,
        "server_name": server_name,
        "results": results,
        "total_matches": len(results)
    }

@router.post("/text/add")
async def add_text_knowledge(
    title: str = Form(...),
    content: str = Form(...),
    format_type: str = Form("md"),
    current_user: User = Depends(get_current_admin_user)
):
    """Add new text-based knowledge document"""
    success = knowledge_service.add_text_knowledge(title, content, format_type)
    if success:
        return {"message": "Text knowledge added successfully", "title": title}
    else:
        raise HTTPException(status_code=500, detail="Failed to add text knowledge")

@router.post("/text/upload")
async def upload_text_knowledge(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_admin_user)
):
    """Upload text knowledge file"""
    if not file.filename.endswith(('.txt', '.md')):
        raise HTTPException(status_code=400, detail="Only .txt and .md files are supported")
    
    try:
        content = await file.read()
        text_content = content.decode('utf-8')
        
        # Extract title from filename
        title = file.filename.replace('.txt', '').replace('.md', '').replace('_', ' ').title()
        format_type = 'md' if file.filename.endswith('.md') else 'txt'
        
        success = knowledge_service.add_text_knowledge(title, text_content, format_type)
        
        if success:
            return {"message": "File uploaded successfully", "filename": file.filename, "title": title}
        else:
            raise HTTPException(status_code=500, detail="Failed to save uploaded file")
            
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be valid text (UTF-8)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/confluence/config")
async def get_confluence_config(current_user: User = Depends(get_current_admin_user)):
    """Get current Confluence configuration (sensitive data masked)"""
    config = knowledge_service.confluence_config
    # Mask sensitive information
    if 'api_token' in config:
        config['api_token'] = '***masked***'
    return config

@router.post("/confluence/config")
async def update_confluence_config(
    config: Dict,
    current_user: User = Depends(get_current_admin_user)
):
    """Update Confluence configuration"""
    success = knowledge_service.update_confluence_config(config)
    if success:
        return {"message": "Confluence configuration updated successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to update Confluence configuration")

@router.post("/confluence/test")
async def test_confluence_connection(current_user: User = Depends(get_current_admin_user)):
    """Test Confluence connection"""
    try:
        pages = knowledge_service.get_confluence_pages()
        return {
            "status": "success" if pages else "no_pages_found",
            "pages_count": len(pages),
            "sample_pages": [{"id": p["id"], "title": p["title"]} for p in pages[:5]]
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

@router.post("/refresh")
async def refresh_knowledge_sources(current_user: User = Depends(get_current_admin_user)):
    """Refresh all knowledge sources"""
    success = await knowledge_service.refresh_all_sources()
    if success:
        return {
            "message": "All knowledge sources refreshed successfully",
            "status": knowledge_service.get_knowledge_sources_status()
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to refresh knowledge sources")

@router.get("/text/list")
async def list_text_knowledge(current_user: User = Depends(get_current_user)):
    """List all text knowledge documents"""
    return {
        "documents": knowledge_service.text_knowledge,
        "total_count": len(knowledge_service.text_knowledge)
    }

@router.get("/confluence/pages")
async def list_confluence_pages(current_user: User = Depends(get_current_user)):
    """List all Confluence pages in knowledge base"""
    if not knowledge_service.confluence_config.get('enabled', False):
        return {"message": "Confluence integration is disabled", "pages": []}
    
    return {
        "pages": knowledge_service.confluence_knowledge,
        "total_count": len(knowledge_service.confluence_knowledge)
    }

@router.get("/stats")
async def get_knowledge_statistics(current_user: User = Depends(get_current_user)):
    """Get knowledge base statistics"""
    status = knowledge_service.get_knowledge_sources_status()
    
    total_entries = (
        status['csv_knowledge']['entries'] +
        status['text_knowledge']['documents'] +
        status['confluence']['pages']
    )
    
    return {
        "total_entries": total_entries,
        "by_source": {
            "csv_entries": status['csv_knowledge']['entries'],
            "text_documents": status['text_knowledge']['documents'],
            "confluence_pages": status['confluence']['pages']
        },
        "confluence_enabled": status['confluence']['enabled'],
        "last_refresh": status['csv_knowledge']['last_loaded']
    }