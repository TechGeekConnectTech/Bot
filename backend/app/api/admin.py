from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage, QueryResolution, ResolutionFeedback
from app.api.auth import get_current_user, get_admin_user

router = APIRouter()

# Pydantic models
class IncidentCreate(BaseModel):
    server_name: Optional[str] = None
    correlation_id: Optional[str] = None
    job_id: Optional[str] = None
    affected_username: Optional[str] = None
    issue_description: str
    priority: str = "Medium"
    category: str = "API Issue"
    user_id: Optional[int] = None

class DashboardStats(BaseModel):
    total_users: int
    total_conversations: int
    total_queries_resolved: int
    active_conversations: int
    queries_today: int
    common_issues: List[dict]
    resolution_rate: float

class UserStats(BaseModel):
    id: int
    username: str
    full_name: str
    department: str
    total_conversations: int
    last_active: Optional[datetime]
    queries_resolved: int

class IncidentDetails(BaseModel):
    incident_id: str
    conversation_id: int
    created_by_username: str
    created_by_full_name: str
    created_by_department: str
    server_name: Optional[str] = None
    correlation_id: Optional[str] = None
    query_type: str
    created_at: datetime
    status: str = "Open"
    priority: str = "Medium"

def require_admin_user(current_user: User = Depends(get_current_user)):
    """Require full admin privileges - dashboard access, user management"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator privileges required")
    return current_user

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    today = datetime.utcnow().date()
    
    # Basic counts
    total_users = db.query(User).count()
    total_conversations = db.query(ChatConversation).count()
    active_conversations = db.query(ChatConversation).filter(
        ChatConversation.status == "active"
    ).count()
    
    # Queries today
    queries_today = db.query(ChatConversation).filter(
        func.date(ChatConversation.created_at) == today
    ).count()
    
    # Common issues by category (top 5)
    # First try to get data from resolution feedback (more accurate)
    common_issues_query = db.query(
        ResolutionFeedback.category,
        func.count(ResolutionFeedback.id).label('count')
    ).filter(
        ResolutionFeedback.category.isnot(None)
    ).group_by(ResolutionFeedback.category).order_by(desc('count')).limit(5).all()
    
    # If no category data, fall back to query_type
    if not common_issues_query:
        common_issues_query = db.query(
            QueryResolution.query_type,
            func.count(QueryResolution.id).label('count')
        ).group_by(QueryResolution.query_type).order_by(desc('count')).limit(5).all()
    
    # Format category names for display
    category_names = {
        'general': 'General Questions',
        'hsbc_internal': 'HSBC Internal Issues', 
        'monitoring': 'System Monitoring',
        'knowledge_base': 'Knowledge Base Queries'
    }
    
    common_issues = []
    for issue in common_issues_query:
        category_key = issue[0]
        display_name = category_names.get(category_key, category_key.replace('_', ' ').title() if category_key else 'Other')
        common_issues.append({"issue_type": display_name, "count": issue[1]})
    
    # Resolution rate from user feedback (more accurate than auto-resolved)
    total_feedback = db.query(ResolutionFeedback).count()
    resolved_feedback = db.query(ResolutionFeedback).filter(
        ResolutionFeedback.was_resolved == True
    ).count()
    
    # If no feedback yet, fall back to old calculation
    if total_feedback > 0:
        resolution_rate = (resolved_feedback / total_feedback * 100)
        total_queries_resolved = resolved_feedback  # Update to use actual user feedback
    else:
        # Fallback to old calculation if no feedback data
        total_queries = db.query(QueryResolution).count()
        resolved_queries = db.query(QueryResolution).filter(
            QueryResolution.resolved_automatically == True
        ).count()
        resolution_rate = (resolved_queries / total_queries * 100) if total_queries > 0 else 0
        total_queries_resolved = resolved_queries
    
    return DashboardStats(
        total_users=total_users,
        total_conversations=total_conversations,
        total_queries_resolved=total_queries_resolved,
        active_conversations=active_conversations,
        queries_today=queries_today,
        common_issues=common_issues,
        resolution_rate=round(resolution_rate, 2)
    )

@router.get("/users", response_model=List[UserStats])
async def get_user_statistics(
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db),
    page: int = 1,
    limit: int = 5
):
    users = db.query(User).all()
    user_stats = []
    
    for user in users:
        total_conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == user.id
        ).count()
        
        queries_resolved = db.query(QueryResolution).join(ChatConversation).filter(
            ChatConversation.user_id == user.id,
            QueryResolution.resolved_automatically == True
        ).count()
        
        user_stats.append(UserStats(
            id=user.id,
            username=user.username,
            full_name=user.full_name,
            department=user.department,
            total_conversations=total_conversations,
            last_active=user.last_login,
            queries_resolved=queries_resolved
        ))
    
    # Sort by total conversations (most active first)
    user_stats.sort(key=lambda x: x.total_conversations, reverse=True)
    
    # Apply pagination
    start_index = (page - 1) * limit
    end_index = start_index + limit
    
    return user_stats[start_index:end_index]

@router.get("/incidents", response_model=List[IncidentDetails])
async def get_all_incidents(
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    # Query incidents with user information
    incidents_query = db.query(
        QueryResolution.incident_id,
        QueryResolution.conversation_id,
        QueryResolution.query_type,
        QueryResolution.server_name,
        QueryResolution.correlation_id,
        QueryResolution.created_at,
        User.username,
        User.full_name,
        User.department
    ).join(
        ChatConversation, QueryResolution.conversation_id == ChatConversation.id
    ).join(
        User, ChatConversation.user_id == User.id
    ).filter(
        QueryResolution.incident_created == True,
        QueryResolution.incident_id.isnot(None)
    ).order_by(
        desc(QueryResolution.created_at)
    ).all()
    
    incidents = []
    for incident in incidents_query:
        incidents.append(IncidentDetails(
            incident_id=incident.incident_id,
            conversation_id=incident.conversation_id,
            created_by_username=incident.username,
            created_by_full_name=incident.full_name,
            created_by_department=incident.department,
            server_name=incident.server_name,
            correlation_id=incident.correlation_id,
            query_type=incident.query_type,
            created_at=incident.created_at,
            status="Open",
            priority="Medium"  # You can extend this to store priority in DB
        ))
    
    return incidents

class IncidentRequest(BaseModel):
    conversation_id: int
    incident_details: IncidentCreate

@router.post("/create-incident")
async def create_support_incident(
    request: IncidentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Generate mock incident ID for now
    incident_id = f"INC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    # This would integrate with your actual ticketing system
    # For now, we'll create a mock incident record
    
    # Update or create query resolution record
    query_resolution = db.query(QueryResolution).filter(
        QueryResolution.conversation_id == request.conversation_id
    ).first()
    
    if not query_resolution:
        # Map category to database enum value
        category_mapping = {
            "API Issue": "api_issue",
            "Auth Issue": "auth_issue", 
            "Payload Issue": "payload_issue",
            "Resource Lock": "resource_lock",
            "Performance Issue": "performance_issue",
            "Configuration Issue": "configuration_issue"
        }
        query_type = category_mapping.get(request.incident_details.category, "other")
        
        # Create new query resolution record
        query_resolution = QueryResolution(
            conversation_id=request.conversation_id,
            query_type=query_type,
            server_name=request.incident_details.server_name,
            correlation_id=request.incident_details.correlation_id,
            resolved_automatically=False,
            incident_created=True,
            incident_id=incident_id
        )
        db.add(query_resolution)
    else:
        query_resolution.incident_created = True
        query_resolution.incident_id = incident_id
        query_resolution.server_name = request.incident_details.server_name
        query_resolution.correlation_id = request.incident_details.correlation_id
    
    db.commit()
    
    # Mock response structure (replace with actual API integration)
    return {
        "message": "Incident created successfully",
        "incident_id": incident_id,
        "details": {
            "priority": request.incident_details.priority,
            "category": request.incident_details.category,
            "server_name": request.incident_details.server_name,
            "correlation_id": request.incident_details.correlation_id,
            "job_id": request.incident_details.job_id,
            "affected_username": request.incident_details.affected_username,
            "reporter": current_user.username,
            "status": "Open"
        }
    }

@router.delete("/conversations/user/{user_id}")
async def delete_user_conversations(
    user_id: int,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to delete all conversations for a specific user"""
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    try:
        # Get all user's conversations
        conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == user_id
        ).all()
        
        conversation_count = len(conversations)
        total_messages = 0
        
        # Delete query resolutions and messages for all conversations
        for conv in conversations:
            db.query(QueryResolution).filter(
                QueryResolution.conversation_id == conv.id
            ).delete()
            
            message_count = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).count()
            total_messages += message_count
            
            db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).delete()
        
        # Delete all conversations
        db.query(ChatConversation).filter(
            ChatConversation.user_id == user_id
        ).delete()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Deleted {conversation_count} conversations and {total_messages} messages for user {user.username}",
            "deleted_conversations": conversation_count,
            "deleted_messages": total_messages
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete user conversations: {str(e)}")

@router.delete("/conversations/all")
async def delete_all_conversations(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Admin endpoint to delete ALL conversations in the system (use with extreme caution)"""
    try:
        # Delete all query resolutions
        query_resolution_count = db.query(QueryResolution).count()
        db.query(QueryResolution).delete()
        
        # Delete all messages
        message_count = db.query(ChatMessage).count()
        db.query(ChatMessage).delete()
        
        # Delete all conversations
        conversation_count = db.query(ChatConversation).count()
        db.query(ChatConversation).delete()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"System-wide deletion completed: {conversation_count} conversations, {message_count} messages, {query_resolution_count} query resolutions",
            "deleted_conversations": conversation_count,
            "deleted_messages": message_count,
            "deleted_query_resolutions": query_resolution_count
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete all conversations: {str(e)}")

@router.get("/conversations/stats")
async def get_conversation_stats(
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get conversation statistics for admin dashboard"""
    try:
        total_conversations = db.query(ChatConversation).count()
        total_messages = db.query(ChatMessage).count()
        total_users_with_conversations = db.query(ChatConversation.user_id).distinct().count()
        
        # Recent activity (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_conversations = db.query(ChatConversation).filter(
            ChatConversation.created_at >= thirty_days_ago
        ).count()
        
        return {
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "total_users_with_conversations": total_users_with_conversations,
            "recent_conversations_30_days": recent_conversations
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get conversation stats: {str(e)}")

@router.get("/resolution-analytics")
async def get_resolution_analytics(
    admin_user: User = Depends(require_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed resolution analytics for admin dashboard"""
    try:
        # Overall resolution statistics
        total_feedback = db.query(ResolutionFeedback).count()
        resolved_feedback = db.query(ResolutionFeedback).filter(
            ResolutionFeedback.was_resolved == True
        ).count()
        
        resolution_rate = (resolved_feedback / total_feedback * 100) if total_feedback > 0 else 0
        
        # Average rating for resolved queries
        avg_rating_result = db.query(
            func.avg(ResolutionFeedback.resolution_rating)
        ).filter(
            ResolutionFeedback.was_resolved == True,
            ResolutionFeedback.resolution_rating.isnot(None)
        ).scalar()
        
        avg_rating = round(float(avg_rating_result), 2) if avg_rating_result else None
        
        # Resolution by category
        category_stats = db.query(
            ResolutionFeedback.category,
            func.count(ResolutionFeedback.id).label('total'),
            func.sum(func.cast(ResolutionFeedback.was_resolved, db.Integer)).label('resolved')
        ).filter(
            ResolutionFeedback.category.isnot(None)
        ).group_by(ResolutionFeedback.category).all()
        
        resolution_by_category = {}
        for category, total, resolved in category_stats:
            rate = (resolved / total * 100) if total > 0 else 0
            resolution_by_category[category] = {
                "total": total,
                "resolved": resolved or 0,
                "rate": round(rate, 1)
            }
        
        # Resolution by AI service
        ai_service_stats = db.query(
            ResolutionFeedback.ai_service_used,
            func.count(ResolutionFeedback.id).label('total'),
            func.sum(func.cast(ResolutionFeedback.was_resolved, db.Integer)).label('resolved')
        ).filter(
            ResolutionFeedback.ai_service_used.isnot(None)
        ).group_by(ResolutionFeedback.ai_service_used).all()
        
        resolution_by_ai_service = {}
        for service, total, resolved in ai_service_stats:
            rate = (resolved / total * 100) if total > 0 else 0
            resolution_by_ai_service[service] = {
                "total": total,
                "resolved": resolved or 0,
                "rate": round(rate, 1)
            }
        
        # Recent feedback (last 10)
        recent_feedback = db.query(ResolutionFeedback).join(
            User, ResolutionFeedback.user_id == User.id
        ).order_by(ResolutionFeedback.created_at.desc()).limit(10).all()
        
        recent_feedback_data = []
        for feedback in recent_feedback:
            user = db.query(User).filter(User.id == feedback.user_id).first()
            recent_feedback_data.append({
                "id": feedback.id,
                "was_resolved": feedback.was_resolved,
                "resolution_rating": feedback.resolution_rating,
                "feedback_comment": feedback.feedback_comment,
                "category": feedback.category,
                "ai_service_used": feedback.ai_service_used,
                "created_at": feedback.created_at,
                "username": user.username if user else "Unknown"
            })
        
        return {
            "total_queries": total_feedback,
            "resolved_queries": resolved_feedback,
            "resolution_rate": round(resolution_rate, 2),
            "average_rating": avg_rating,
            "resolution_by_category": resolution_by_category,
            "resolution_by_ai_service": resolution_by_ai_service,
            "recent_feedback": recent_feedback_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get resolution analytics: {str(e)}")