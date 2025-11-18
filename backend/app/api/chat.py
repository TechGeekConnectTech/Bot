from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage, QueryResolution
from app.api.auth import get_current_user
from app.services.gpt_service import GPTService
from app.services.api_integrations import SplunkService, AnsibleService

router = APIRouter()

# Pydantic models
class MessageCreate(BaseModel):
    message: str
    conversation_id: Optional[int] = None
    server_name: Optional[str] = None
    correlation_id: Optional[str] = None
    category: Optional[str] = None

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    sender_type: str
    message_content: str
    timestamp: datetime
    message_metadata: Optional[dict] = None

class ConversationResponse(BaseModel):
    id: int
    title: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
    message_count: int

class ChatResponse(BaseModel):
    message: str
    conversation_id: int
    suggestions: Optional[List[str]] = None
    data_sources: Optional[List[str]] = None
    incident_required: bool = False
    processing_updates: Optional[List[str]] = None
    ai_service_used: Optional[str] = None
    knowledge_base_match: Optional[dict] = None
    total_matches: Optional[int] = None
    incident_created: Optional[bool] = None
    incident_id: Optional[str] = None
    incident_creation_error: Optional[str] = None

class DeleteResponse(BaseModel):
    success: bool
    message: str
    deleted_count: Optional[int] = None

class IncidentResponse(BaseModel):
    id: int
    incident_id: Optional[str]
    query_type: str
    server_name: Optional[str]
    correlation_id: Optional[str]
    root_cause: Optional[str]
    resolution_steps: Optional[str]
    incident_created: bool
    resolved_automatically: bool
    created_at: datetime
    conversation_title: str
    # Status and priority from conversation
    status: Optional[str] = "open"
    priority: Optional[str] = "medium"
    # Admin-only fields
    created_by_username: Optional[str] = None
    created_by_full_name: Optional[str] = None
    created_by_department: Optional[str] = None

class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total_count: int
    filtered_count: int

@router.post("/send-message", response_model=ChatResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Create or get conversation
    if message_data.conversation_id:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == message_data.conversation_id,
            ChatConversation.user_id == current_user.id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = ChatConversation(
            user_id=current_user.id,
            title=message_data.message[:50] + "..." if len(message_data.message) > 50 else message_data.message
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Save user message
    user_message = ChatMessage(
        conversation_id=conversation.id,
        sender_type="user",
        message_content=message_data.message,
        message_metadata={
            "server_name": message_data.server_name,
            "correlation_id": message_data.correlation_id
        }
    )
    db.add(user_message)
    db.commit()
    
    # Process message with AI and external APIs
    gpt_service = GPTService()
    response_data = await gpt_service.process_user_query(
        message=message_data.message,
        server_name=message_data.server_name,
        correlation_id=message_data.correlation_id,
        category=message_data.category,
        user_context={
            "user_id": current_user.id,
            "department": current_user.department,
            "username": current_user.username,
            "full_name": current_user.full_name
        },
        conversation_id=conversation.id
    )
    
    # Create incident if required
    response_data = await gpt_service._create_incident_if_required(
        response_data=response_data,
        conversation_id=conversation.id,
        message=message_data.message,
        server_name=message_data.server_name,
        correlation_id=message_data.correlation_id,
        user_context={
            "user_id": current_user.id,
            "department": current_user.department,
            "username": current_user.username,
            "full_name": current_user.full_name
        }
    )
    
    # Save bot response
    bot_message = ChatMessage(
        conversation_id=conversation.id,
        sender_type="bot",
        message_content=response_data["message"],
        message_metadata=response_data.get("metadata", {})
    )
    db.add(bot_message)
    db.commit()
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    db.commit()
    
    return ChatResponse(
        message=response_data["message"],
        conversation_id=conversation.id,
        suggestions=response_data.get("suggestions", []),
        data_sources=response_data.get("data_sources", []),
        incident_required=response_data.get("incident_required", False),
        processing_updates=response_data.get("processing_updates", []),
        ai_service_used=response_data.get("ai_service_used"),
        knowledge_base_match=response_data.get("knowledge_base_match"),
        total_matches=response_data.get("total_matches", 0),
        incident_created=response_data.get("incident_created"),
        incident_id=response_data.get("incident_id"),
        incident_creation_error=response_data.get("incident_creation_error")
    )

@router.get("/conversations", response_model=List[ConversationResponse])
async def get_user_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conversations = db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).order_by(ChatConversation.updated_at.desc()).all()
    
    result = []
    for conv in conversations:
        message_count = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conv.id
        ).count()
        
        result.append(ConversationResponse(
            id=conv.id,
            title=conv.title,
            status=conv.status,
            priority=conv.priority,
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            message_count=message_count
        ))
    
    return result

@router.get("/conversation/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify user owns this conversation
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conversation_id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    # Format messages for response
    formatted_messages = []
    for msg in messages:
        formatted_messages.append(MessageResponse(
            id=msg.id,
            conversation_id=msg.conversation_id,
            sender_type=msg.sender_type,
            message_content=msg.message_content,
            timestamp=msg.timestamp,
            message_metadata=msg.message_metadata
        ))
    
    return formatted_messages

@router.delete("/conversation/{conversation_id}", response_model=DeleteResponse)
async def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a specific conversation and all its messages"""
    # Verify user owns this conversation
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    try:
        # Delete associated query resolutions first (foreign key constraint)
        db.query(QueryResolution).filter(
            QueryResolution.conversation_id == conversation_id
        ).delete()
        
        # Delete all messages in the conversation
        message_count = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).count()
        
        db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).delete()
        
        # Delete the conversation
        db.delete(conversation)
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"Conversation '{conversation.title}' deleted successfully",
            deleted_count=message_count
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.delete("/conversations/all", response_model=DeleteResponse)
async def delete_all_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all conversations for the current user"""
    try:
        # Get all user's conversations
        conversations = db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id
        ).all()
        
        if not conversations:
            return DeleteResponse(
                success=True,
                message="No conversations to delete",
                deleted_count=0
            )
        
        conversation_count = len(conversations)
        total_messages = 0
        
        # Delete query resolutions for all conversations
        for conv in conversations:
            db.query(QueryResolution).filter(
                QueryResolution.conversation_id == conv.id
            ).delete()
            
            # Count messages before deletion
            message_count = db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).count()
            total_messages += message_count
            
            # Delete messages
            db.query(ChatMessage).filter(
                ChatMessage.conversation_id == conv.id
            ).delete()
        
        # Delete all conversations
        db.query(ChatConversation).filter(
            ChatConversation.user_id == current_user.id
        ).delete()
        
        db.commit()
        
        return DeleteResponse(
            success=True,
            message=f"All chat history deleted: {conversation_count} conversations, {total_messages} messages",
            deleted_count=conversation_count
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete conversations: {str(e)}")

@router.get("/incidents", response_model=IncidentListResponse)
async def get_user_incidents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    server_name: Optional[str] = None,
    query_type: Optional[str] = None,
    incident_status: Optional[str] = None,  # created, not_created
    limit: int = 50,
    offset: int = 0
):
    """
    Get user's past incidents with optional filtering
    """
    # Base query for user's incidents
    query = db.query(QueryResolution).join(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    )
    
    # Apply filters
    if server_name:
        query = query.filter(QueryResolution.server_name.ilike(f"%{server_name}%"))
    
    if query_type:
        query = query.filter(QueryResolution.query_type == query_type)
    
    if incident_status == "created":
        query = query.filter(QueryResolution.incident_created == True)
    elif incident_status == "not_created":
        query = query.filter(QueryResolution.incident_created == False)
    
    # Get total count for pagination
    total_count = db.query(QueryResolution).join(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).count()
    
    filtered_count = query.count()
    
    # Apply pagination and ordering
    incidents_data = query.order_by(QueryResolution.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response
    incidents = []
    for incident in incidents_data:
        conversation = db.query(ChatConversation).filter(ChatConversation.id == incident.conversation_id).first()
        incidents.append(IncidentResponse(
            id=incident.id,
            incident_id=incident.incident_id,
            query_type=incident.query_type,
            server_name=incident.server_name,
            correlation_id=incident.correlation_id,
            root_cause=incident.root_cause,
            resolution_steps=incident.resolution_steps,
            incident_created=incident.incident_created,
            resolved_automatically=incident.resolved_automatically,
            created_at=incident.created_at,
            conversation_title=conversation.title if conversation else "Unknown",
            # Status and priority from conversation
            status=conversation.status if conversation else "open",
            priority=conversation.priority if conversation else "medium"
        ))
    
    return IncidentListResponse(
        incidents=incidents,
        total_count=total_count,
        filtered_count=filtered_count
    )

@router.get("/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident_details(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific incident
    """
    incident = db.query(QueryResolution).join(ChatConversation).filter(
        QueryResolution.id == incident_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    conversation = db.query(ChatConversation).filter(ChatConversation.id == incident.conversation_id).first()
    
    return IncidentResponse(
        id=incident.id,
        incident_id=incident.incident_id,
        query_type=incident.query_type,
        server_name=incident.server_name,
        correlation_id=incident.correlation_id,
        root_cause=incident.root_cause,
        resolution_steps=incident.resolution_steps,
        incident_created=incident.incident_created,
        resolved_automatically=incident.resolved_automatically,
        created_at=incident.created_at,
        conversation_title=conversation.title if conversation else "Unknown",
        # Status and priority from conversation
        status=conversation.status if conversation else "open",
        priority=conversation.priority if conversation else "medium"
    )

# Admin-only incident management endpoints  
@router.get("/admin/incidents", response_model=IncidentListResponse)
async def get_all_incidents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = None,
    server_name: Optional[str] = None,
    query_type: Optional[str] = None,
    incident_status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    Get all incidents across all users (admin only)
    """
    # Check if user has admin privileges
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Base query for all incidents
    query = db.query(QueryResolution).join(ChatConversation).join(User)
    
    # Apply filters
    if user_id:
        query = query.filter(ChatConversation.user_id == user_id)
    
    if server_name:
        query = query.filter(QueryResolution.server_name.ilike(f"%{server_name}%"))
    
    if query_type:
        query = query.filter(QueryResolution.query_type == query_type)
    
    if incident_status == "created":
        query = query.filter(QueryResolution.incident_created == True)
    elif incident_status == "not_created":
        query = query.filter(QueryResolution.incident_created == False)
    
    # Get total count
    total_count = db.query(QueryResolution).join(ChatConversation).count()
    filtered_count = query.count()
    
    # Apply pagination and ordering
    incidents_data = query.order_by(QueryResolution.created_at.desc()).offset(offset).limit(limit).all()
    
    # Format response with user information
    incidents = []
    for incident in incidents_data:
        conversation = db.query(ChatConversation).filter(ChatConversation.id == incident.conversation_id).first()
        user = db.query(User).filter(User.id == conversation.user_id).first() if conversation else None
        
        incidents.append(IncidentResponse(
            id=incident.id,
            incident_id=incident.incident_id or f"INC-{incident.id:06d}",
            query_type=incident.query_type,
            server_name=incident.server_name,
            correlation_id=incident.correlation_id,
            root_cause=incident.root_cause,
            resolution_steps=incident.resolution_steps,
            incident_created=incident.incident_created,
            resolved_automatically=incident.resolved_automatically,
            created_at=incident.created_at,
            conversation_title=conversation.title if conversation else "Unknown",
            # Status and priority from conversation
            status=conversation.status if conversation else "open",
            priority=conversation.priority if conversation else "medium",
            # Additional admin fields
            created_by_username=user.username if user else "Unknown",
            created_by_full_name=user.full_name if user else "Unknown",
            created_by_department=user.department if user else "Unknown"
        ))
    
    return IncidentListResponse(
        incidents=incidents,
        total_count=total_count,
        filtered_count=filtered_count
    )

@router.get("/admin/incidents/{incident_id}", response_model=IncidentResponse)
async def get_incident_details_admin(
    incident_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about any incident (admin only)
    """
    # Check if user has admin privileges
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    incident = db.query(QueryResolution).filter(QueryResolution.id == incident_id).first()
    
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    conversation = db.query(ChatConversation).filter(ChatConversation.id == incident.conversation_id).first()
    user = db.query(User).filter(User.id == conversation.user_id).first() if conversation else None
    
    return IncidentResponse(
        id=incident.id,
        incident_id=incident.incident_id or f"INC-{incident.id:06d}",
        query_type=incident.query_type,
        server_name=incident.server_name,
        correlation_id=incident.correlation_id,
        root_cause=incident.root_cause,
        resolution_steps=incident.resolution_steps,
        incident_created=incident.incident_created,
        resolved_automatically=incident.resolved_automatically,
        created_at=incident.created_at,
        conversation_title=conversation.title if conversation else "Unknown",
        # Status and priority from conversation
        status=conversation.status if conversation else "open",
        priority=conversation.priority if conversation else "medium",
        # Additional admin fields
        created_by_username=user.username if user else "Unknown",
        created_by_full_name=user.full_name if user else "Unknown",
        created_by_department=user.department if user else "Unknown"
    )