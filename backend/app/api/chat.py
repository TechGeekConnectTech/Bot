from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage, QueryResolution, ResolutionFeedback
from app.api.auth import get_current_user
from app.services.gpt_service import GPTService
from app.services.api_integrations import SplunkService, AnsibleService
from app.core.logging_config import get_user_logger, get_chat_logger, get_api_logger
import logging

logger = logging.getLogger(__name__)
user_logger = get_user_logger()
chat_logger = get_chat_logger()
api_logger = get_api_logger()

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
    message_id: Optional[int] = None  # Bot message ID for feedback tracking
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
    requires_feedback: bool = True  # Always ask for feedback on bot responses

class ResolutionFeedbackCreate(BaseModel):
    conversation_id: int
    message_id: int
    was_resolved: bool
    resolution_rating: Optional[int] = None  # 1-5 stars
    feedback_comment: Optional[str] = None

class ResolutionFeedbackResponse(BaseModel):
    id: int
    conversation_id: int
    message_id: int
    was_resolved: bool
    resolution_rating: Optional[int]
    feedback_comment: Optional[str]
    response_time: Optional[int]
    category: Optional[str]
    ai_service_used: Optional[str]
    created_at: datetime

class ResolutionStatsResponse(BaseModel):
    total_queries: int
    resolved_queries: int
    resolution_rate: float  # Percentage
    average_rating: Optional[float]
    resolution_by_category: dict
    resolution_by_ai_service: dict
    recent_feedback: List[ResolutionFeedbackResponse]

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
    request: Request = None,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request else "unknown"
    
    # Log user activity
    user_logger.info(f"Message received - User: {current_user.full_name} ({current_user.username}), Category: {message_data.category}, Server: {message_data.server_name}, IP: {client_ip}")
    chat_logger.info(f"User message - [{current_user.username}] Category: {message_data.category or 'None'} | Message: {message_data.message[:200]}{'...' if len(message_data.message) > 200 else ''}")
    
    # Create or get conversation
    if message_data.conversation_id:
        conversation = db.query(ChatConversation).filter(
            ChatConversation.id == message_data.conversation_id,
            ChatConversation.user_id == current_user.id
        ).first()
        if not conversation:
            chat_logger.warning(f"Conversation not found - User: {current_user.username}, Conversation ID: {message_data.conversation_id}")
            raise HTTPException(status_code=404, detail="Conversation not found")
        chat_logger.info(f"Using existing conversation - ID: {conversation.id}, User: {current_user.username}")
    else:
        # Create new conversation
        conversation = ChatConversation(
            user_id=current_user.id,
            title=message_data.message[:50] + "..." if len(message_data.message) > 50 else message_data.message
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        chat_logger.info(f"New conversation created - ID: {conversation.id}, User: {current_user.username}, Title: {conversation.title}")
    
    # Save user message
    user_message = ChatMessage(
        conversation_id=conversation.id,
        sender_type="user",
        message_content=message_data.message,
        message_metadata={
            "server_name": message_data.server_name,
            "correlation_id": message_data.correlation_id,
            "category": message_data.category
        }
    )
    db.add(user_message)
    db.commit()
    
    chat_logger.info(f"User message saved - ID: {user_message.id}, Conversation: {conversation.id}, Length: {len(message_data.message)} chars")
    
    # Process message with AI and external APIs
    logger.info(f"Starting AI processing - User: {current_user.username}, Category: {message_data.category}, Message length: {len(message_data.message)}")
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
        category=message_data.category,
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
    db.refresh(bot_message)  # Get the message ID
    
    # Update conversation timestamp
    conversation.updated_at = datetime.utcnow()
    db.commit()
    
    # Log bot response
    ai_service = response_data.get("ai_service_used", "unknown")
    response_length = len(response_data["message"])
    incident_required = response_data.get("incident_required", False)
    
    chat_logger.info(f"Bot response generated - ID: {bot_message.id}, User: {current_user.username}, AI Service: {ai_service}, Length: {response_length} chars, Incident Required: {incident_required}")
    user_logger.info(f"Query processed - User: {current_user.full_name}, Category: {message_data.category}, AI Service: {ai_service}, Response Length: {response_length}")
    
    return ChatResponse(
        message=response_data["message"],
        conversation_id=conversation.id,
        message_id=bot_message.id,  # Include message ID for feedback tracking
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
    request: Request = None,
    db: Session = Depends(get_db)
):
    client_ip = request.client.host if request else "unknown"
    
    conversations = db.query(ChatConversation).filter(
        ChatConversation.user_id == current_user.id
    ).order_by(ChatConversation.updated_at.desc()).all()
    
    api_logger.info(f"Conversations accessed - User: {current_user.username}, Count: {len(conversations)}, IP: {client_ip}")
    
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

# Resolution Feedback Endpoints
@router.post("/resolution-feedback", response_model=ResolutionFeedbackResponse)
async def submit_resolution_feedback(
    feedback_data: ResolutionFeedbackCreate,
    current_user: User = Depends(get_current_user),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """
    Submit feedback on whether a bot response resolved the user's query
    """
    client_ip = request.client.host if request else "unknown"
    
    # Log feedback submission
    user_logger.info(f"Resolution feedback submitted - User: {current_user.full_name} ({current_user.username}), Conversation: {feedback_data.conversation_id}, Message: {feedback_data.message_id}, Resolved: {feedback_data.was_resolved}, Rating: {feedback_data.resolution_rating}, IP: {client_ip}")
    chat_logger.info(f"Feedback received - [{current_user.username}] Conv: {feedback_data.conversation_id}, Msg: {feedback_data.message_id}, Resolved: {feedback_data.was_resolved}, Rating: {feedback_data.resolution_rating or 'None'}")
    
    # Log the current user
    print(f"👤 Current user: {current_user.username} (ID: {current_user.id})")
    # Verify the conversation belongs to the user
    conversation = db.query(ChatConversation).filter(
        ChatConversation.id == feedback_data.conversation_id,
        ChatConversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Verify the message exists and is a bot message
    print(f"🔍 Looking for message: ID={feedback_data.message_id}, conversation_id={feedback_data.conversation_id}")
    
    # First check if message exists at all
    any_message = db.query(ChatMessage).filter(ChatMessage.id == feedback_data.message_id).first()
    if any_message:
        print(f"✅ Message {feedback_data.message_id} exists: sender_type={any_message.sender_type}, conversation_id={any_message.conversation_id}")
    else:
        print(f"❌ Message {feedback_data.message_id} does not exist in database")
    
    # Now check with all filters
    message = db.query(ChatMessage).filter(
        ChatMessage.id == feedback_data.message_id,
        ChatMessage.conversation_id == feedback_data.conversation_id,
        ChatMessage.sender_type == "bot"
    ).first()
    
    if not message:
        # More detailed error message
        error_details = f"Bot message not found. Message ID: {feedback_data.message_id}, Conversation ID: {feedback_data.conversation_id}"
        if any_message:
            error_details += f". Message exists but: sender_type='{any_message.sender_type}', actual_conversation_id={any_message.conversation_id}"
        print(f"❌ {error_details}")
        raise HTTPException(status_code=404, detail=error_details)
    
    # Check if feedback already exists for this message
    existing_feedback = db.query(ResolutionFeedback).filter(
        ResolutionFeedback.message_id == feedback_data.message_id,
        ResolutionFeedback.user_id == current_user.id
    ).first()
    
    if existing_feedback:
        # Update existing feedback
        existing_feedback.was_resolved = feedback_data.was_resolved
        existing_feedback.resolution_rating = feedback_data.resolution_rating
        existing_feedback.feedback_comment = feedback_data.feedback_comment
        db.commit()
        db.refresh(existing_feedback)
        
        feedback_obj = existing_feedback
    else:
        # Calculate response time (time between bot message and feedback)
        response_time = int((datetime.utcnow() - message.timestamp).total_seconds())
        
        # Get AI service used from message metadata
        ai_service_used = message.message_metadata.get("ai_service_used") if message.message_metadata else None
        
        # Get category from message metadata or conversation context
        category = message.message_metadata.get("category") if message.message_metadata else None
        
        # Create new feedback
        feedback_obj = ResolutionFeedback(
            conversation_id=feedback_data.conversation_id,
            message_id=feedback_data.message_id,
            user_id=current_user.id,
            was_resolved=feedback_data.was_resolved,
            resolution_rating=feedback_data.resolution_rating,
            feedback_comment=feedback_data.feedback_comment,
            response_time=response_time,
            category=category,
            ai_service_used=ai_service_used
        )
        
        db.add(feedback_obj)
        db.commit()
        db.refresh(feedback_obj)
    
    # If query was resolved, update conversation status
    if feedback_data.was_resolved:
        conversation.status = "resolved"
        conversation.resolved_at = datetime.utcnow()
        db.commit()
    
    # Log successful feedback processing
    logger.info(f"Resolution feedback processed successfully - Feedback ID: {feedback_obj.id}, User: {current_user.username}, Category: {feedback_obj.category}, Resolved: {feedback_obj.was_resolved}")
    
    return ResolutionFeedbackResponse(
        id=feedback_obj.id,
        conversation_id=feedback_obj.conversation_id,
        message_id=feedback_obj.message_id,
        was_resolved=feedback_obj.was_resolved,
        resolution_rating=feedback_obj.resolution_rating,
        feedback_comment=feedback_obj.feedback_comment,
        response_time=feedback_obj.response_time,
        category=feedback_obj.category,
        ai_service_used=feedback_obj.ai_service_used,
        created_at=feedback_obj.created_at
    )

@router.get("/resolution-stats", response_model=ResolutionStatsResponse)
async def get_resolution_statistics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_id: Optional[int] = None  # For admin to view specific user stats
):
    """
    Get resolution statistics and rates
    """
    # Base query - admin can view all stats, users can only see their own
    if current_user.role == "admin" and user_id:
        # Admin viewing specific user stats
        feedback_query = db.query(ResolutionFeedback).filter(ResolutionFeedback.user_id == user_id)
    elif current_user.role == "admin" and not user_id:
        # Admin viewing all stats
        feedback_query = db.query(ResolutionFeedback)
    else:
        # Regular user viewing their own stats
        feedback_query = db.query(ResolutionFeedback).filter(ResolutionFeedback.user_id == current_user.id)
    
    # Get all feedback records
    all_feedback = feedback_query.all()
    
    # Calculate basic stats
    total_queries = len(all_feedback)
    resolved_queries = len([f for f in all_feedback if f.was_resolved])
    resolution_rate = (resolved_queries / total_queries * 100) if total_queries > 0 else 0.0
    
    # Calculate average rating (only from resolved queries with ratings)
    rated_feedback = [f for f in all_feedback if f.was_resolved and f.resolution_rating]
    average_rating = sum(f.resolution_rating for f in rated_feedback) / len(rated_feedback) if rated_feedback else None
    
    # Resolution by category
    resolution_by_category = {}
    categories = set(f.category for f in all_feedback if f.category)
    for category in categories:
        category_feedback = [f for f in all_feedback if f.category == category]
        category_resolved = [f for f in category_feedback if f.was_resolved]
        resolution_by_category[category] = {
            "total": len(category_feedback),
            "resolved": len(category_resolved),
            "rate": (len(category_resolved) / len(category_feedback) * 100) if category_feedback else 0
        }
    
    # Resolution by AI service
    resolution_by_ai_service = {}
    ai_services = set(f.ai_service_used for f in all_feedback if f.ai_service_used)
    for service in ai_services:
        service_feedback = [f for f in all_feedback if f.ai_service_used == service]
        service_resolved = [f for f in service_feedback if f.was_resolved]
        resolution_by_ai_service[service] = {
            "total": len(service_feedback),
            "resolved": len(service_resolved),
            "rate": (len(service_resolved) / len(service_feedback) * 100) if service_feedback else 0
        }
    
    # Get recent feedback (last 10)
    recent_feedback = feedback_query.order_by(ResolutionFeedback.created_at.desc()).limit(10).all()
    recent_feedback_response = [
        ResolutionFeedbackResponse(
            id=f.id,
            conversation_id=f.conversation_id,
            message_id=f.message_id,
            was_resolved=f.was_resolved,
            resolution_rating=f.resolution_rating,
            feedback_comment=f.feedback_comment,
            response_time=f.response_time,
            category=f.category,
            ai_service_used=f.ai_service_used,
            created_at=f.created_at
        ) for f in recent_feedback
    ]
    
    return ResolutionStatsResponse(
        total_queries=total_queries,
        resolved_queries=resolved_queries,
        resolution_rate=round(resolution_rate, 2),
        average_rating=round(average_rating, 2) if average_rating else None,
        resolution_by_category=resolution_by_category,
        resolution_by_ai_service=resolution_by_ai_service,
        recent_feedback=recent_feedback_response
    )